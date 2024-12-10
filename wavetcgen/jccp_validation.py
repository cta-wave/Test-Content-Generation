#!/Users/ndvx/code/venv/bin/python3

from pathlib import Path
import aiohttp
from aiohttp import web
import asyncio
import json
import csv
import os
import click

from tqdm.asyncio import tqdm_asyncio

from dataclasses import dataclass
from functools import wraps


WAVE_ROOT = "https://dash.akamaized.net/WAVE/"
WAVE_VECTORS = "https://dash.akamaized.net/WAVE/vectors/"
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


@click.group()
@click.option('--matrix', default='vectors.csv', help='[vectors.csv] test matrix')
@click.option('--content-dir', help=f'test vectors root directory')
@click.pass_context
def cli(ctx, matrix, content_dir):
    ctx.ensure_object(dict)
    ctx.obj['csv_matrix'] = matrix
    ctx.obj['content_dir'] = content_dir



##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####


@cli.command()
@click.pass_context
def serve(ctx):
    async def serve_async():
        await start_content_server(ctx.obj['content_dir'])
        await wait_for_sigtrap()
    asyncio.run(serve_async())


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####

import re

@dataclass
class TestVector:
    
    filename: str
    jccp_validation_report: bool = False

    @classmethod
    def from_db_entry(self, data) -> 'TestVector':
        return TestVector(data["mpdPath"])

    @classmethod
    def from_validation_csv(self, row) -> 'TestVector':
        mpdPath = row[0]
        passed = len(row) > 1 and row[1] != 'False' and row[1] != '0' and bool(row[1])
        return TestVector(mpdPath, passed)

    def to_validation_csv_row(self) -> list:
        return (self.filename, 1 if self.jccp_validation_report else 0)

    @property
    def path(self):
        if self.filename.startswith(WAVE_VECTORS):
           return self.filename.replace(WAVE_VECTORS, '')
        return self.filename

    @property
    def json(self) -> Path:
        return Path(self.path).with_suffix('.json')


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


async def validate_stream(session, jccp, tv, output_dir, semaphore):
    async with semaphore:
        uri = validation_request_uri(jccp, tv)
        fp = Path(output_dir) / tv.json
        os.makedirs(fp.parent, exist_ok=True)
        try:
            async with session.get(uri) as response:
                txt = await response.text()
                res = json.loads(txt)
                with open(fp, 'w') as fo:
                    json.dump(res, fo)
                tv.jccp_validation_report = True
                return tv, None
        except BaseException as e:
            tv.jccp_validation_report = False
            return tv, e


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####


async def validate_streams_async(jccp, csv_matrix, validation_dir, content_dir=None):

    server = None
    tasks = []
    report = []
    errors = 0
    semaphore = asyncio.Semaphore(1)

    if jccp == 'staging':
        jccp = JCCP_STAGING

    # spawn a local server to server local content
    if content_dir and Path(content_dir).exists():
        server, _ = await start_content_server(content_dir, '0.0.0.0', 8000)

    tm = [*iter_csv_matrix(csv_matrix)]
    
    async with aiohttp.ClientSession() as session:
        print('\n')
        for tv in tm:
            if tv.jccp_validation_report:
                report.append(tv)
            else:
                tasks.append(validate_stream(session, jccp, tv, validation_dir, semaphore))
                
        res = await tqdm_asyncio.gather(*tasks)
        if server:
            await server.cleanup()

        for [tv, e] in res:
            report.append(tv)
            if e:
                errors += 1

    checked_count = len(tasks)
    skipped_count = len(report) - checked_count
    print(f"\n\tchecked:{checked_count} | errors:{errors} | skipped_count:{skipped_count}\n")

    with open(Path(validation_dir).with_suffix('.csv'), 'w') as fo:
        writer = csv.writer(fo)
        writer.writerows([tv.to_validation_csv_row() for tv in report])


def iter_csv_matrix(csv_matrix):
    with open(csv_matrix, mode='r') as fo:
        reader = csv.reader(fo)
        for row in reader:
            yield TestVector.from_validation_csv(row)


@cli.command()
@click.option('--jccp', default='http://0.0.0.0:80', help=f'jccp api endpoint, staging={JCCP_STAGING}')
@click.argument('validation_dir', default='./validation')
@click.pass_context
def validate_streams(ctx, jccp, validation_dir):
    asyncio.run(validate_streams_async(jccp, ctx.obj['csv_matrix'], validation_dir, ctx.obj['content_dir']))


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####
# CREATE STREAM LISTING
##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####


async def list_database_content(ctx):
    uri = "https://raw.githubusercontent.com/cta-wave/Test-Content/refs/heads/master/database.json"
    vectors = []

    async with aiohttp.ClientSession() as session:
        async with session.get(uri) as response:
            txt = await response.text()
            res = json.loads(txt)
            for _, entries in res.items():
                for _, entry in entries.items():
                    vectors.append(TestVector.from_db_entry(entry).to_validation_csv_row())

    with open(ctx.obj['csv_matrix'], mode='w', newline='') as fo:
        writer = csv.writer(fo)
        writer.writerows(vectors)


@cli.command
@click.pass_context
def list_cta_wave_content(ctx):
    asyncio.run(list_database_content(ctx))


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####


@cli.command()
@click.pass_context
def list_vectors_directory(ctx):
    asyncio.run(list_content_directory(ctx.obj['content_dir'], ctx.obj['csv_matrix']))


async def iter_http_directory(session, root, path, BeautifulSoup):
    html = ''
    async with session.get(root+path) as resp:
        html = await resp.text()
    
    parsed = BeautifulSoup(html, features="html.parser")
    for a in parsed.body.find_all('a'):
        if a.string != 'Parent Directory':
            yield a.text, path + a.text

async def iter_mpd_in_tree(session, root, dirpath, BS):
    async for txt, href in iter_http_directory(session, root, dirpath, BS):
        if txt.endswith('.mpd'):
            yield href
        elif txt.endswith('/'):
            async for mpd in iter_mpd_in_tree(session, root, href, BS):
                yield mpd
            
async def iter_remote_content_directory(root_dir, profile=None):
    try: 
        from BeautifulSoup import BeautifulSoup as BS
    except ImportError:
        from bs4 import BeautifulSoup as BS

    async with aiohttp.ClientSession() as session:
        V = 'vectors/'
        async for href in iter_mpd_in_tree(session, root_dir, V, BS):
            filename = href.lstrip(V)
            print(filename)
            yield TestVector(filename)


async def list_content_directory(content_dir, csv_matrix):
    if not bool(csv_matrix):
        csv_matrix = Path(content_dir).with_suffix('.csv')
    rows = []
    if Path(content_dir).exists():
        for tv in iter_local_content_directory(content_dir):
            rows.append(tv.to_validation_csv_row())
    else:
        async for tv in iter_remote_content_directory(content_dir):
            rows.append(tv.to_validation_csv_row())
            
    with open(csv_matrix, mode='w', newline='') as fo:
        writer = csv.writer(fo)
        writer.writerows(rows)


def iter_local_content_directory(content_dir):
    for mpd in Path(content_dir).glob("**/*.mpd"):
        yield TestVector(mpd, False)


##### ##### ##### ##### ##### ##### ##### ##### ##### ##### #####

@cli.command
@click.argument('validation_dir', default='./validation')
@click.pass_context
def inspect_validation_reports(ctx, validation_dir):
    
    data = {}
    vectors = [*iter_csv_matrix(ctx.obj['csv_matrix'])]
    
    for tv in vectors:
        fp = Path(validation_dir) / tv.json
        if not fp.exists():
            print(f"NOT FOUND: {tv.json}")
            continue
        with open(fp, 'r') as fo:
            r = json.load(fo)
            data[tv.path] = r

    result = Path(validation_dir).with_suffix('.json')
    with open(result, 'w') as fo:
        print(data)
        json.dump(data, fo)


if __name__ == "__main__":
    cli(obj={})
