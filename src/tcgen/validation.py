import asyncio
import socket
import json
from pathlib import Path

import aiohttp
from aiohttp import web
from tqdm.asyncio import tqdm_asyncio

from tcgen.database import Database, PUBLIC_VECTORS_DIRECTORY

DOCKER_EXE = "podman"
JCCP_STAGING = "https://staging.conformance.dashif.org/"
CDN_PREFIX_LEN = len(PUBLIC_VECTORS_DIRECTORY)

def jccp_validation_report_location(db_entry):
    return Path(db_entry["mpdPath"][CDN_PREFIX_LEN:]).with_name('jccp-validation.json')

def iter_jccp_validation_results(database, results_dir):
    db = Database()
    db.load(database)
    for test_entry_key, db_entry in db.iter_entries():
        yield test_entry_key, Path(results_dir) / jccp_validation_report_location(db_entry)

def test_vector_location(db_entry, vectors_location=None):
    if vectors_location is None:
        return db_entry["mpdPath"]
    elif str(vectors_location).startswith('http'):
        return str(vectors_location) + db_entry["mpdPath"][CDN_PREFIX_LEN:]
    else:
        return Path(vectors_location) / Path(db_entry["mpdPath"][CDN_PREFIX_LEN:])

async def start_content_server(content_dir, host, port):
    app = web.Application()
    app.add_routes([web.static('/', content_dir)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner, site

######################################################
# Validation routines
######################################################

def validation_query_string():
    '''
    From : https://github.com/Dash-Industry-Forum/DASH-IF-Conformance/wiki/REST-Interface
        cmaf=1 : Enable CMAF checking
        ctawave=1: Enable CTA WAVE checking
        hbbtv=1: Enable HbbTV Checking
        dvb=1: Enable DVB checking (2018 xsd)
        dvb_2019=1: Enable DVB checking (2019 xsd)
        lowlatency=1 : Enable DASH-IF IOP Low Latency checking
        iop=1 : Enable DASH-IF IOP checking
        dolby=1 : Enable Dolby checking
        segments=1 : Enable Segment validation
        compact=1 : Provide compact JSON output
        latest_xsd=1: Use the latest xsd files for verification
        silent=1: Do not output JSON to stdout
        autodetect=1: Automatically detect profiles
        disable_detailed_segment_output=1: Disables the detailed segment validation output to reduce the size of the final JSON
    '''
    return "cmaf=1&ctawave=1&segments=1"


def validation_request_uri(jccp, tv):
    q = validation_query_string()
    return f"{jccp}/Utils/Process_cli.php?url={tv}&{q}"


async def xhr_validate_stream(session, semaphore, jccp_xhr_endpoint, test_entry_key, test_entry, vectors_hostname, results_dir):
    async with semaphore:
        uri = validation_request_uri(jccp_xhr_endpoint, test_vector_location(test_entry, vectors_hostname))
        try:
            async with session.get(uri) as response:
                txt = await response.text()
                res = json.loads(txt)
                with open(Path(results_dir) / jccp_validation_report_location(test_entry), 'w') as fo:
                    json.dump(res, fo)
                return test_entry_key, None
        except BaseException as e:
            return test_entry_key, e


async def cli_validate_stream(semaphore, jccp_container_id, test_entry_key, test_entry, vectors_hostname, results_dir):
    jccp_cli = [DOCKER_EXE, 'exec', '-w', '/var/www/html/Utils/', jccp_container_id,
        'php', 'Process_cli.php', '--cmaf', '--ctawave', '--segments', test_vector_location(test_entry, vectors_hostname)]
    async with semaphore:
        p = await asyncio.create_subprocess_exec(
            *jccp_cli, 
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )   
        stdout_data, stderr_data = await p.communicate()
        if p.returncode == 0:
            fp = Path(results_dir) / jccp_validation_report_location(test_entry)
            if not fp.parent.exists():
                fp.parent.mkdir(parents=True, exist_ok=True)
            with open(fp, 'wb') as fo:
                fo.write(stdout_data)
            return test_entry_key, None
        else:
            return test_entry_key, stderr_data


######################################################
# Summary
######################################################

def get_validation_failures(test_result_file):
    
    def iter_test_failures(test):
        for t in test:
            if t["state"] != "PASS":
                yield t
    
    def get_entry_failures(entry):
        if entry["verdict"] == "PASS":
            return None
        result = {}
        for k, v in entry.items():
            if isinstance(v, dict):
                if v.get("verdict", "PASS") != "PASS":
                    result[k] = [*iter_test_failures(v["test"])]
        return result
    
    fieldnames = (
        "Schematron",
        "MPEG-DASH Common",
        "CMAF",
        "CTA-WAVE",
        "SEGMENT_VALIDATION",
        "HEALTH"
    )
    with open(test_result_file) as fo:
        data = json.load(fo)
        entries = data["entries"]
        failures = {}
        if len(entries):
            for k in fieldnames:
                if k in entries:
                    r = get_entry_failures(entries[k])
                    if r:
                        failures[k] = r
                else:
                    failures[k] = f'{k} - entry not found'
        else:
            failures["error"] = "validation entries is not a valid array"
        return failures


def append_validation_summary(fo, test_key, failures):
    fo.write(f'\n# {test_key} \n')
    if not isinstance(failures, dict):
        fo.write(f'### {test_key} - {failures} \n\n')
        return
    for k, v in failures.items():
        fo.write(f'## {test_key} - {k} \n')
        if not isinstance(v, dict):
            fo.write(f'### {test_key} - {k} - {v} \n\n')
            return
        for section, tests in v.items():
            fo.write(f'### {test_key} - {k} - {section} \n')
            for t in tests:
                fo.write(f'##### {t["test"]} \n')
                for m in t["messages"]:
                    fo.write(f'\t- {m} \n')
    fo.write(f'\n')


def validation_report_summary(database, results_dir):
    with open(Path(results_dir) / 'jccp-validation-summary.md', 'w') as fo:
        for test_entry_key, jccp_result_path in iter_jccp_validation_results(database, results_dir):
            failures = get_validation_failures(jccp_result_path)
            append_validation_summary(fo, test_entry_key, failures)


######################################################
# Entrypoint
######################################################

async def validate_test_vectors_async(database, jccp, vectors_dir, results_dir, port, summary):
    
    semaphore = asyncio.Semaphore(1)
    
    db = Database()
    db.load(database)
    
    process_local_content = (vectors_dir is not None) and (not vectors_dir.startswith('http'))
    vectors_hostname = None 

    if results_dir is not None:
        assert Path(results_dir).is_dir(), f'--results-dir directory not found: {results_dir}'

    if process_local_content:
        assert Path(vectors_dir).exists(), f'--vectors-dir directory not found: {vectors_dir}'
        server, _ = await start_content_server(vectors_dir, '0.0.0.0', port)
        vectors_hostname = f'http://{socket.gethostbyname(socket.gethostname())}:{port}/'
        if results_dir is None:
            results_dir = vectors_dir
    else:
        if vectors_dir is not None:
            vectors_hostname = vectors_dir if vectors_dir.endswith('/') else f'{vectors_dir}/'
        results_dir = Path(results_dir) if results_dir is not None else Path('./validation')
        if not results_dir.exists():
            results_dir.mkdir(parents=True, exist_ok=True)

    # run jccp through http request
    if jccp.startswith("http"):
        async with aiohttp.ClientSession() as session:
            tasks = []
            for test_entry_key, test_entry in db.iter_entries():
                tasks.append(
                    xhr_validate_stream(session, semaphore, jccp, test_entry_key, test_entry, vectors_hostname, results_dir)
                )
            res = await tqdm_asyncio.gather(*tasks)
    
    # run jccp through command line
    else:
        tasks = []
        for test_entry_key, test_entry in db.iter_entries():
            tasks.append(
                cli_validate_stream(semaphore, jccp, test_entry_key, test_entry, vectors_hostname, results_dir)
            )
        res = await tqdm_asyncio.gather(*tasks)
    
    if process_local_content:
        await server.cleanup()
    
    for test_stream_key, err in res:
        if err:
            print(f'Error while processing {test_stream_key}:\n{err}')

    if summary:
        validation_report_summary(database, results_dir)
