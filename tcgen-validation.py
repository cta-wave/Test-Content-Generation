#!/Users/ndvx/code/venv/bin/python3

from pathlib import Path
import aiohttp
from aiohttp import web
import asyncio
import json

from argparse import ArgumentParser

from tqdm.asyncio import tqdm_asyncio

from functools import wraps

from wavetcgen.database import SERVER_ACCESS_URL as WAVE_VECTORS
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
    return f"{jccp}/Utils/Process_cli.php?url={tv.filename}?{q}"


async def validate_stream(session, semaphore, jccp, test_entry_key, test_vector_uri):
    async with semaphore:
        uri = validation_request_uri(jccp, test_vector_uri)
        try:
            async with session.get(uri) as response:
                txt = await response.text()
                res = json.loads(txt)
                return test_entry_key, res, None
        except BaseException as e:
            return test_entry_key, None, e


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####

def iter_vectors(args):
    if args.config:
        for tc in TestContent.iter_vectors_in_batch_config(args.config):
            yield tc
    else:    
        for tc in TestContent.iter_vectors_in_matrix(args.matrix):
            yield tc


async def validate_local_strings(args):

    server = None
    tasks = []
    report = {}
    semaphore = asyncio.Semaphore(1)

    if Path(args.vectors_dir).exists():
        server, _ = await start_content_server(args.vectors_dir, '0.0.0.0', 8000)
    
    async with aiohttp.ClientSession() as session:
        for tv in iter_vectors(args):
            for fps in FPS_FAMILY.all():
                test_entry_key = Database.test_entry_key(fps, tv, '')
                vector_dir = args.vectors_dir / Database.test_entry_location(fps, tv, '')
                batch_dir = most_recent_batch(vector_dir)
                test_vector_uri = f'{args.hostname}/{test_entry_key}/{batch_dir.stem}/stream.mpd'
                tasks.append(validate_stream(session, semaphore, args.jccp, test_entry_key, test_vector_uri))

        res = await tqdm_asyncio.gather(*tasks)
        if server:
            await server.cleanup()

        for test_stream_key, result, err in res:
            if err:
                report[test_stream_key] = err
            else:
                report[test_stream_key] = result
    
    with open(args.output, 'w') as fo:
        json.dumps(fo, report)


if __name__ == "__main__":
    parser = ArgumentParser()
    parser.add_argument('-m', '--matrix', help='Sparse matrix csv file listing test vectors, ignored when --config is used.')
    parser.add_argument('-c', '--config', help='Optional tcgen.py config file listing test vectors.')
    parser.add_argument('-v', '--vectors_dir', help='Check for missing content in local vectors directory.')
    parser.add_argument('-o', '--output', help='dump validation result to json file.')
    parser.add_argument('-j', '--jccp', default=JCCP_STAGING, help='JCCP HTTP endpoint.')
    args = parser.parse_args()
    asyncio.run(validate_local_strings(args))
