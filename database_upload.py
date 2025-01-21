import json
import pysftp
import os
from pathlib import Path

LOCAL_OUTPUT_FOLDER = Path("./output")
# depending on the AKAMAI_PRIVATE_KEY permissions, this may be relative to the /vectors dir ...
SERVER_OUTPUT_FOLDER = "/"
#  or relative to the server root
# SERVER_OUTPUT_FOLDER = "/129021/dash/WAVE/vectors/"


def create_directory_structure(sftp, key, dry_run):

    directory = SERVER_OUTPUT_FOLDER
    for part in key.split('/'):
        if part == '':
            continue
        directory += f'{part}/'
        if not sftp.isfile(directory):
            print(f'sftp.mkdir: {directory}')
            if not dry_run:
                sftp.mkdir(directory, mode=644)

    for root, dirs, _ in os.walk(LOCAL_OUTPUT_FOLDER / key, topdown=True):
        for name in dirs:
            batch_subdir = f'{SERVER_OUTPUT_FOLDER}{Path(root).relative_to(LOCAL_OUTPUT_FOLDER)}/{name}'
            if not sftp.isfile(batch_subdir):
                print(f'sftp.mkdir: {batch_subdir}')
                if not dry_run:
                    sftp.mkdir(batch_subdir, mode=644)
    

def upload_db_entry(sftp, key, entry, dry_run):
    
    create_directory_structure(sftp, key, dry_run)

    for p in (LOCAL_OUTPUT_FOLDER / key).glob("**/*"):
        rel_path = p.relative_to(LOCAL_OUTPUT_FOLDER)
        dst_path = SERVER_OUTPUT_FOLDER + str(rel_path)
        if p.is_file():
            print("sftp.put: " + str(p) + " >>> " + dst_path)
            if not dry_run:
                sftp.put(p, dst_path, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
            

def upload_db(sftp, db, dry_run):
    for records in db.values():
        for key, entry in records.items():
            upload_db_entry(sftp, key, entry, dry_run)


if __name__ == "__main__":

    db = {}
    dry_run = False

    with open('./database.json', 'r') as fo:
        db = json.load(fo)

    host = "dashstorage.upload.akamai.com"
    username = "sshacs"
    cnopts = pysftp.CnOpts(knownhosts=host)
    cnopts.hostkeys = None
    
    with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
        print("Connection successfully established ... ")
        # dirs = sftp.listdir()
        # print(dirs)
        sftp.cwd(SERVER_OUTPUT_FOLDER)
        upload_db(sftp, db, dry_run)
