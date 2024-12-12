from argparse import ArgumentParser
from wavetcgen.models import TestContent, FPS_SUITE, CSV_DELIMITER
from wavetcgen.database import Database, most_recent_batch
from pathlib import Path
from datetime import datetime
import csv
import subprocess

def iter_vectors(args):
    if args.config:
        for tc in TestContent.iter_vectors_in_batch_config(args.config):
            yield tc
    else:    
        for tc in TestContent.iter_vectors_in_matrix(args.matrix):
            yield tc


if __name__ == "__main__":
    
    parser = ArgumentParser()
    parser.add_argument('-m', '--matrix', help='Sparse matrix csv file listing test vectors, ignored when --config is used.')
    parser.add_argument('-c', '--config', help='Optional tcgen.py config file listing test vectors.')
    parser.add_argument('-v', '--vectors_dir', help='Check for missing content in local vectors directory.')
    parser.add_argument('-d', '--database', help='If --vectors_dir is set, add new entries to database. Otherwise check for missing entries in database.')
    parser.add_argument('-z', '--zip', help='create missing zip archives.')
    parser.add_argument('-o', '--output_csv', help='export result in csv format.')
    args = parser.parse_args()

    db_updated = False
    if args.database:
        db = Database.load(args.database)

    if args.config or args.matrix:
        status = {}
        for tv in iter_vectors(args):
            
            # cross check matrix/config with local dir, find and process the latest batch
            local_vector_checked = False
            if args.vectors_dir:
                
                for fps in FPS_SUITE.all():
                    test_entry_key = Database.test_entry_key(fps, tv, '')
                    vector_dir = args.vectors_dir / Database.test_entry_location(fps, tv, '')
                    try:
                        assert vector_dir.exists(), f'missing: {vector_dir}'
                        batch_dir = most_recent_batch(vector_dir)

                        stream_mpd = batch_dir / 'stream.mpd'
                        assert stream_mpd.exists(), f'missing: {batch_dir.stem}/stream.mpd'

                        batch_zip = batch_dir / f'{Database.test_id(tv)}.zip'
                        if args.zip and not batch_zip.exists():
                            zip_cmd = f'zip -r {batch_zip} {str(batch_dir/"*")}'
                            _ = subprocess.run(zip_cmd, shell=True, cwd=args.vectors_dir)
                        else:
                            assert batch_zip.exists(), f'missing: {batch_dir.stem}/{Database.test_id(tv)}.zip'

                        local_vector_checked = True
                        ## add local vectors to db
                        status[test_entry_key] = test_entry_key

                        if args.database:
                            db.add_entry(tv)
                            db_updated = True
                    
                    except AssertionError as e:
                        status[test_entry_key] = str(e)
                        
            ## cross check matrix/config with db, list missing test content
            elif args.database:
                    results = db.find(tv)
                    # list missing vectors in local directory
                    for key in [Database.test_entry_key(fps, tv, '') for fps in FPS_SUITE.all()]:
                        for test_entry_key in results:
                            if test_entry_key.startswith(key):
                                status[key] = test_entry_key
                                continue
                        if not key in status:
                            status[key] = 'Not found in db'

        if args.output_csv:
            with open(args.output_csv, 'w') as fo:
                writer = csv.writer(fo, delimiter=CSV_DELIMITER)
                writer.writerows([*status.items()])
        else:
            for key, value in status.items():
                print(key + '\n  - ' + value)
    else:
        parser.print_help()
    
    if db_updated:
        db.save()
