from pathlib import Path
import subprocess
import logging 
import json
import os
import re
from datetime import datetime
import requests
import click
import pysftp
import asyncio
import xml.etree.ElementTree as ET
import shutil

from tcgen.models import TestContent, FPS_FAMILY, locate_source_content, Mezzanine
from tcgen.database import Database, most_recent_batch
from tcgen.encode import encode_stream, encrypt_stream_cenc, patch_mpd, HR_SPLIT_LOG
from tcgen.validation import validate_test_vectors_async, JCCP_STAGING

@click.group()
@click.pass_context
def cli(ctx):
    """command line tools to work on CTA WAVE content generation."""
    ctx.ensure_object(dict)


###############################################################
# ENCODE
###############################################################

@cli.command()
@click.pass_context
@click.argument('mezzanine')
@click.argument('config')
@click.option('-v', '--vectors-dir', default='output', help='default: ./output')
@click.option('-b', '--batch-dir', default=datetime.today().strftime('%Y-%m-%d'), help='batch directory name. default value uses the current date, eg. 2024-12-31')
@click.option('--encode/--no-encode', default=True, help="encode content")
@click.option('--format-mpd/--no-format-mpd', default=True, help="patch mpd content to match CTA WAVE requirements")
@click.option('-t', '--test-id', help='process only vector with id "-', default=None)
@click.option('-f', '--fps-family', default='ALL', help='process only one of 14.985_29.97_59.94 - 12.5_25_50 - 15_30_60')
@click.option('--drm-config', default=(Path(__file__) / '../../../DRM.xml').resolve(), help='path to DRM.xml config file')
@click.option('--dry_run/--no-dry-run', default=False, help="dry run, usefull for debugging")
def encode(ctx, mezzanine, config, vectors_dir, batch_dir, encode, format_mpd, test_id, fps_family, drm_config, dry_run):
    """
    Encode content from MEZZANINE directory into test vectors using content options specified in CONFIG.
    """

    Mezzanine.root_dir = Path(mezzanine)
    framerates = FPS_FAMILY.all()
    
    if fps_family != 'ALL':
        if fps_family not in framerates:
            raise Exception(f'Invalid framerate configuration {fps_family}')
        framerates = [FPS_FAMILY.from_string(fps_family)]

    for tc in TestContent.iter_vectors_in_batch_config(config):
        if test_id != None and tc.test_id != test_id:
                continue
        
        for fps_family in framerates:
            try:
                m = locate_source_content(tc, fps_family)
                if tc.encryption:
                    test_stream_cenc_dir =  Path(vectors_dir) / Database.test_entry_location(fps_family, tc, batch_dir)
                    test_stream_dir =  Path(re.sub(r"[-_]c?enc/", "/", str(test_stream_cenc_dir)))
                    output_mpd = encrypt_stream_cenc(test_stream_cenc_dir, test_stream_dir, drm_config, dry_run)
                else:
                    test_stream_dir =  Path(vectors_dir) / Database.test_entry_location(fps_family, tc, batch_dir)
                    encode_dry_run = not encode
                    output_mpd = encode_stream(m, tc, test_stream_dir, encode_dry_run)
                if format_mpd:
                    if not dry_run:
                        patch_mpd(output_mpd, m, tc)
            
            except BaseException as e:
                print(e)


###############################################################
# DATABASE
###############################################################

@cli.command()
@click.pass_context
@click.argument('mezzanine')
@click.argument('config')
@click.option('-v', '--vectors-dir', default='output', help='default: ./output')
@click.option('-d', '--database', default=None, help='Path to create database file. If the database already exists, it will be patched.')
@click.option('--zip/--no-zip', default=True, help='generate individual .zip archive for test vectors. default: --zip')
def export(ctx, mezzanine, config, vectors_dir, database, zip):
    """
    Prepare for upload by generating a database file and zip archives for the test vectors listed in CONFIG. \
    MEZZANINE directory is required to provide source content metadata.
    """
    Mezzanine.root_dir = Path(mezzanine)
    db = Database()
    if database is None:
        database = Path('./export') / Path(config).with_suffix('.json').name
    elif Path(database).exists():
        db.load(database)

    for tv in TestContent.iter_vectors_in_batch_config(config):
        for fps in FPS_FAMILY.all():
            test_entry_key = Database.test_entry_key(fps, tv, '')
            try:
                vector_dir = vectors_dir / Database.test_entry_location(fps, tv, '')
                assert vector_dir.exists(), f'missing: {vector_dir}'
                batch_dir = most_recent_batch(vector_dir)
                stream_mpd = batch_dir / 'stream.mpd'
                assert stream_mpd.exists(), f'missing: {batch_dir.stem}/stream.mpd'
                batch_zip = batch_dir / f'{Database.test_id(tv)}.zip'
                if zip and not batch_zip.exists():
                    batch_rel_dir = batch_dir.relative_to(vectors_dir)
                    batch_zip = batch_rel_dir / f'{Database.test_id(tv)}.zip'
                    res = subprocess.run(f'zip -r {batch_zip} {str(batch_rel_dir)}', shell=True, cwd=vectors_dir)
                    res.check_returncode()
                elif zip:
                    assert batch_zip.exists(), f'missing: {batch_dir.stem}/{Database.test_id(tv)}.zip'
                m = locate_source_content(tv, fps)
                db.add_entry(tv, m, batch_dir.name)
            except BaseException as e:
                logging.warning(f'{test_entry_key} : {e}')

    if database is not None:
        db.save(database)


###############################################################
# SWITCHING SETS
###############################################################

def extract_representation_ids(xml_file):
    tree = ET.parse(xml_file)
    root = tree.getroot()
    ns = {"mpd": "urn:mpeg:dash:schema:mpd:2011"}
    representation_elements = root.findall(".//mpd:Representation", ns)
    ids = [rep.get("id") for rep in representation_elements if rep.get("id") is not None]
    return ids

@cli.command()
@click.pass_context
@click.argument('mpd')
@click.argument('vectors-dir')
@click.option('-b', '--batch-dir', default=None, help='if unspecified, %Y-%m-%d will be used.')
@click.option('--overwrite', is_flag=True, default=False, help='overwrite output directory.')
@click.option('-t', '--tmp-dir', default=None, help='if unspecified, VECTORS_DIR/tmp will be used.')
def archive_switching_set(ctx, mpd, vectors_dir, batch_dir, overwrite, tmp_dir):
    """
    Look up all representations from MPD switching set in VECTORS_DIR, \
        creates an archive containing the .mpd manifest and all representations, \
        and copy the result to VECTORS_DIR. Currently, the entry has to be added manually to the database.\n
    MPD             filename must be formated as: '$profile_$fpsFamily_$ssN_stream.mpd'\n
    VECTORS_DIR     directory must contain the represenations referenced by MPD
    """
    parts = Path(mpd).name.split('_')
    profile = parts[0]
    fps = '_'.join(parts[1:4])
    name = f'{parts[4]}_{profile}'
    rep_ids = extract_representation_ids(mpd)
    assert len(rep_ids) > 1, 'not a valid switching set playlist'

    vectors_dir = Path(vectors_dir)

    if batch_dir is None:
        batch_dir = datetime.now().strftime("%Y-%m-%d")

    ss_dir = Path("switching_sets") / fps / name / batch_dir
    ss_out_dir = vectors_dir / ss_dir
    # check for overwrite
    if ss_out_dir.exists():
        if overwrite:
            shutil.rmtree(ss_out_dir)
        else:
            raise Exception(f"Directory already exists: {ss_out_dir}")
    
    click.echo(f"Creating output directory: {ss_out_dir}")
    Path.mkdir(ss_out_dir, exist_ok=False, parents=True)

    if tmp_dir is None:
        tmp_dir = Path(vectors_dir) / 'tmp' / name 
    else:
        tmp_dir = Path(tmp_dir) / name

    if tmp_dir.exists():
        click.echo(f"Creating tmp directory: {tmp_dir}")
        shutil.rmtree(tmp_dir)

    click.echo(f"Copying mpd to tmp dir")
    Path.mkdir(tmp_dir / ss_dir, exist_ok=False, parents=True)
    shutil.copy(mpd, tmp_dir / ss_dir / 'stream.mpd')

    for rep_id in rep_ids:
        rep_path = Path(rep_id.replace("../", ""))
        src_path = vectors_dir / rep_path
        dst_path = tmp_dir / rep_path
        click.echo(f"Copying representation to tmp dir: {rep_path}")
        shutil.copytree(src_path, dst_path)

    click.echo(f"Creating archive: {tmp_dir}.zip")
    shutil.make_archive(tmp_dir, 'zip', tmp_dir.parent, name)

    click.echo(f"Copying to output directory")
    shutil.copy(mpd, ss_out_dir / 'stream.mpd')
    shutil.copy(tmp_dir.with_suffix('.zip'),  ss_out_dir / f'{name}.zip')
    
    if tmp_dir.exists():
        click.echo(f"Removing tmp directory")
        shutil.rmtree(tmp_dir)


###############################################################
# JCCP VALIDATION
###############################################################

@cli.command()
@click.pass_context
@click.argument('database')
@click.option('-j', '--jccp', default=JCCP_STAGING, help="DASH-IF's Joint Content Conformance Project. Can be one of: 1) API endpoint URI to call JCCP. 2) Docker container ID to execute JCCP on command line.")
@click.option('-v', '--vectors-dir', default=None, help="overide the location of test vector's mpdPath")
@click.option('-r', '--results-dir', default=None, help='optional directory to store the results')
@click.option('-p', '--port', default=8000, help='specifies port to serve content to JCCP when --vectors-dir is a local directory. default=8000')
@click.option('--summary/--no-summary', default=False, help='generates markdown summary in result directory')
def jccp_validation(ctx, database, jccp, vectors_dir, results_dir, port, summary):
    """
    Runs DASH-IF-Conformance software (jccp) on test content listed in DATABASE. 
    
    When --vectors-dir specifies a local directory:
    1) results are stored in each test vector directory unless --results-dir is set.
    2) a local HTTP server is automatically spawned to serve the content.
    3) a local JCCP container should be used to access the content.
    
    When --vectors-dir specifies an HTTP directory:
    1) results are stored in './validation' unless --results-dir is set. 
    """
    asyncio.run(validate_test_vectors_async(database, jccp, vectors_dir, results_dir, port, summary))


###############################################################
# UPLOAD
###############################################################

SERVER_OUTPUT_FOLDER = "/129021/dash/WAVE/vectors/"

def create_directory_structure(sftp, key, content_dir, dry_run):

    directory = SERVER_OUTPUT_FOLDER
    for part in key.split('/'):
        if part == '':
            continue
        directory += f'{part}/'
        if not sftp.isfile(directory):
            print(f'sftp.mkdir: {directory}')
            if not dry_run:
                sftp.mkdir(directory, mode=644)

    for root, dirs, _ in os.walk(content_dir / key, topdown=True):
        for name in dirs:
            batch_subdir = f'{SERVER_OUTPUT_FOLDER}{Path(root).relative_to(content_dir)}/{name}'
            if not sftp.isfile(batch_subdir):
                print(f'sftp.mkdir: {batch_subdir}')
                if not dry_run:
                    sftp.mkdir(batch_subdir, mode=644)
    

def upload_db_entry(sftp, key, entry, content_dir, dry_run):
    create_directory_structure(sftp, key, content_dir, dry_run)
    for p in (content_dir / key).glob("**/*"):
        rel_path = p.relative_to(content_dir)
        dst_path = SERVER_OUTPUT_FOLDER + str(rel_path)
        if p.is_file():
            print("sftp.put: " + str(p) + " >>> " + dst_path)
            if not dry_run:
                sftp.put(p, dst_path, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
            

def upload_db(sftp, db, content_dir, dry_run):
    for records in db.values():
        for key, entry in records.items():
            upload_db_entry(sftp, key, entry, content_dir, dry_run)


@cli.command()
@click.pass_context
@click.argument('database')
@click.option('-v', '--vectors-dir', default='output', help='path to the local directory containing the test vectors to be uploaded.')
@click.option('--dry-run/--no-dry-run', default=False)
def upload(ctx, database, vectors_dir, dry_run):
    """
    Upload test vectors listed in DATABASE to the cdn using sftp. \
    Upload of batch content to the server uses SFTP and requires a private key authorizing access. \
    The key is expected to be stored as a file, with its absolute path exported to the environment variable `CDN_PRIVATE_KEY`.
    """

    db = {}
    with open(database, 'r') as fo:
        db = json.load(fo)

    host = "dashstorage.upload.akamai.com"
    username = "sshacs"
    cnopts = pysftp.CnOpts(knownhosts=host)
    cnopts.hostkeys = None

    with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['CDN_PRIVATE_KEY']), cnopts=cnopts) as sftp:
        print("Connection successfully established ... ")
        sftp.cwd(SERVER_OUTPUT_FOLDER)
        # dirs = sftp.listdir()
        # print(dirs)
        upload_db(sftp, db, Path(vectors_dir), dry_run)


###############################################################
# DOWNLOAD
###############################################################


def download_file(url, dst):
    relpath = '/'.join(url.split('/')[-4:])
    local_filename = Path(dst) / relpath
    if not local_filename.parent.exists():
          local_filename.parent.mkdir(parents=True)
    if not local_filename.exists():
        with requests.get(url, stream=True) as r:
                r.raise_for_status()
                with open(local_filename, 'wb') as f:
                        for chunk in r.iter_content(chunk_size=8192): 
                                f.write(chunk)
    return relpath


@cli.command()
@click.pass_context
@click.argument('database')
@click.option('-v', '--vectors-dir', default='output', help='directory where vectors will be downloaded. default: ./output')
@click.option('-c', '--config', default=None, help='a csv config file normaly used for content geeration')
def download(ctx, database, vectors_dir, config):
    """
    Download content listed in DATABASE into the specified directory, optionaly processing only vectors listed in a config file
    """
    db = Database()
    db.load(database)
    if config is None:
        for k, v in db.iter_entries():
            zipPath = download_file(v["zipPath"], vectors_dir)
            subprocess.Popen(["unzip", zipPath], cwd=vectors_dir)
    else:
        for tc in TestContent.iter_vectors_in_batch_config(config):
            for k, v in db.find(tc).items():
                zipPath = download_file(v["zipPath"], vectors_dir)
                subprocess.Popen(["unzip", zipPath], cwd=vectors_dir)


if __name__ == '__main__':
    cli(obj={})