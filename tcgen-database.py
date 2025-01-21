from argparse import ArgumentParser
from wavetcgen.models import TestContent, FPS_FAMILY, locate_source_content
from wavetcgen.database import Database, most_recent_batch
import subprocess
import sys

from pathlib import Path

if __name__ == "__main__":
    
    parser = ArgumentParser()
    parser.add_argument('-c', '--config', required=True, help='config file listing test vectors to add to db')
    parser.add_argument('-v', '--vectors_dir', required=True, help='vectors directory')
    parser.add_argument('-d', '--database', required=True, help='output database file')
    parser.add_argument('-z', '--zip', action='store_true', help='create zip archives for each test vector')
    parser.add_argument('-e', action='store_true', help='exit on errors')
    args = parser.parse_args()

    db = Database()
    if Path(args.database).exists():
        db.load(args.database)

    errors = {}

    for tv in TestContent.iter_vectors_in_batch_config(args.config):
        for fps in FPS_FAMILY.all():
            test_entry_key = Database.test_entry_key(fps, tv, '')
            try:
                vector_dir = args.vectors_dir / Database.test_entry_location(fps, tv, '')
                assert vector_dir.exists(), f'missing: {vector_dir}'
                batch_dir = most_recent_batch(vector_dir)
                stream_mpd = batch_dir / 'stream.mpd'
                assert stream_mpd.exists(), f'missing: {batch_dir.stem}/stream.mpd'
                batch_zip = batch_dir / f'{Database.test_id(tv)}.zip'
                if args.zip and not batch_zip.exists():
                    batch_rel_dir = batch_dir.relative_to(args.vectors_dir)
                    batch_zip = batch_rel_dir / f'{Database.test_id(tv)}.zip'
                    res = subprocess.run(f'zip -r {batch_zip} {str(batch_rel_dir)}', shell=True, cwd=args.vectors_dir)
                    res.check_returncode()
                elif args.zip:
                    assert batch_zip.exists(), f'missing: {batch_dir.stem}/{Database.test_id(tv)}.zip'
                m = locate_source_content(tv, fps)
                db.add_entry(tv, m, batch_dir.name)
            except BaseException as e:
                if args.e:
                    raise e
                errors[test_entry_key] = e
    
    for k, e in errors.items():
        print(f'{k} : {e}')

    db.save(args.database)
