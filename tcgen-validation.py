#!/Users/ndvx/code/venv/bin/python3

from pathlib import Path
import aiohttp
from aiohttp import web
import asyncio
import json
import csv

from argparse import ArgumentParser

from tqdm.asyncio import tqdm_asyncio

from functools import wraps

from wavetcgen.database import Database, most_recent_batch
from wavetcgen.models import TestContent, FPS_FAMILY


JCCP_STAGING = "https://staging.conformance.dashif.org/"


def coro(f):
    @wraps(f)
    def wrapper(*args, **kwargs):
        return asyncio.run(f(*args, **kwargs))
    return wrapper


async def start_content_server(content_dir, host, port):
    app = web.Application()
    app.add_routes([web.static('/', content_dir)])
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, host, port)
    await site.start()
    return runner, site


async def wait_for_sigtrap():
    try:
        print("\n\tCtrl+C to exit")
        while True:
            await asyncio.sleep(0.1)
    except BaseException as e:
        print(e)


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####
# RUN STREAM VALIDATION & DUMP RESULT
##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####

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


async def xhr_validate_stream(session, semaphore, jccp_xhr_endpoint, test_entry_key, test_vector_uri):
    async with semaphore:
        uri = validation_request_uri(jccp_xhr_endpoint, test_vector_uri)
        try:
            async with session.get(uri) as response:
                txt = await response.text()
                res = json.loads(txt)
                return test_entry_key, res, None
        except BaseException as e:
            return test_entry_key, None, e
    

async def cli_validate_stream(semaphore, jccp_container_id, test_entry_key, test_vector_uri):
    jccp_cli = ['podman', 'exec', '-w', '/var/www/html/Utils/', jccp_container_id,
        'php', 'Process_cli.php', '--cmaf', '--ctawave', '--segments', test_vector_uri]
    async with semaphore:
        p = await asyncio.create_subprocess_exec(
            *jccp_cli, 
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE
        )   
        stdout_data, stderr_data = await p.communicate()
        if p.returncode == 0:
            return test_entry_key, json.loads(stdout_data), None
        else:
            return test_entry_key, None, stderr_data
    

##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####

def _iter_vectors(args):
    if args.config:
        for tc in TestContent.iter_vectors_in_batch_config(args.config):
            yield tc
    else:    
        for tc in TestContent.iter_vectors_in_matrix(args.matrix):
            yield tc

def iter_vectors(args):
    if args.database:
        db = Database()
        db.load(args.database)
        for test_entry_key, test_entry in db.iter_entries():
            yield test_entry_key, test_entry["mpdPath"]
    else:
        for tv in _iter_vectors(args):
            for fps in FPS_FAMILY.all():
                test_entry_key = Database.test_entry_key(fps, tv, '')
                vector_dir = args.vectors_dir / Database.test_entry_location(fps, tv, '')
                if not vector_dir.exists():
                    print(f'missing test vector directory: {vector_dir}')
                    continue
                batch_dir = most_recent_batch(vector_dir)
                test_vector_uri = f'{args.host}/{test_entry_key}{batch_dir.stem}/stream.mpd'
                yield test_entry_key, test_vector_uri


async def validate_test_vectors(args):

    server = None
    report = {}
    semaphore = asyncio.Semaphore(1)

    if args.vectors_dir and Path(args.vectors_dir).exists():
        server, _ = await start_content_server(args.vectors_dir, '0.0.0.0', 8000)
    
    if args.jccp.startswith("http"):
        async with aiohttp.ClientSession() as session:
            tasks = [xhr_validate_stream(session, semaphore, args.jccp, test_entry_key, test_vector_uri) 
                for test_entry_key, test_vector_uri in iter_vectors(args)]
            res = await tqdm_asyncio.gather(*tasks)
    else:
        tasks = [cli_validate_stream(semaphore, args.jccp, test_entry_key, test_vector_uri) 
            for test_entry_key, test_vector_uri in iter_vectors(args)]
        res = await tqdm_asyncio.gather(*tasks)
    
    if server:
        await server.cleanup()
    
    for test_stream_key, result, err in res:
        if err:
            report[test_stream_key] = str(err)
        else:
            report[test_stream_key] = result
    
    print(f'validation results: {args.output}')
    with open(args.output, 'w') as fo:
        json.dump(report, fo, indent=4)
    
    rows = []
    print(f'validation errors: {args.output}.md')
    with open(args.output + ".md", 'w') as fomd:
        for test_key, test_validation in report.items():
            failures = get_validation_failures(test_validation)
            if len(failures):
                write_validation_report(fomd, test_key, failures)
            rows.append([test_key, len(failures)])

    with open(args.output + ".csv", 'w') as focsv:
        writer = csv.writer(focsv)
        writer.writerow(["test id", "failures"])
        writer.writerows(rows)


def write_validation_report(fo, test_key, failures):
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

def get_validation_failures(test_validation):
    fieldnames = (
        "Schematron",
        "MPEG-DASH Common",
        "CMAF",
        "CTA-WAVE",
        "SEGMENT_VALIDATION",
        "HEALTH"
    )
    if not isinstance(test_validation, dict):
        return test_validation
    entries = test_validation["entries"]
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


async def serve_test_vectors(args):
    server, _ = await start_content_server(args.vectors_dir, '0.0.0.0', 8000)


if __name__ == "__main__":
    import socket
    host = f'http://{socket.gethostbyname(socket.gethostname())}:8000'
    parser = ArgumentParser()
    parser.add_argument('-m', '--matrix', help='Sparse matrix csv file listing test vectors, ignored when --config is used.')
    parser.add_argument('-c', '--config', help='Optional, tcgen.py config file listing test vectors.')
    parser.add_argument('-d', '--database', help='Optional, validates test vectors in database.')
    parser.add_argument('-v', '--vectors_dir', help='Check for missing content in local vectors directory.')
    parser.add_argument('-j', '--jccp', default=JCCP_STAGING, help='JCCP HTTP endpoint.')
    parser.add_argument('-o', '--output', help='dump validation result to json file.')
    parser.add_argument('--host', default=host, help='host/ip for test vectors')
    args = parser.parse_args()
    asyncio.run(validate_test_vectors(args))
