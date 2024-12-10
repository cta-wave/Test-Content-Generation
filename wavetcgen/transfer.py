import hashlib

def md5_checksum(fp):
    with open(fp, "rb") as f:
        file_hash = hashlib.md5()
        while chunk := f.read(8192):
            file_hash.update(chunk)
    return file_hash.hexdigest()

"""
import pysftp

def upload_sequence(output_folder_base, server_output_folder, dry_run):
    
    host = "dashstorage.upload.akamai.com"
    username = "sshacs"
    cnopts = pysftp.CnOpts(knownhosts=host)
    cnopts.hostkeys = None
    
    # with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    
    try:
        sftp = None if dry_run else pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.getenv('AKAMAI_PRIVATE_KEY')), cnopts=cnopts)
        
        if not dry_run:
            print("Connection successfully established ... ")
            sftp.cwd(server_output_folder)

        # Create the directory structure if it does not exist
        for root, dirs, _ in os.walk(local_output_folder, topdown=True):
            for name in dirs:
                p =  os.path.join(root, name).replace(local_output_folder, server_output_folder + output_folder_base)
                print("# Creating remote directory " + p)
                if not dry_run:
                    if not sftp.isfile(p):
                        sftp.mkdir(p, mode=644)

        # Put the files
        for root, _, files in os.walk(local_output_folder, topdown=True):
            for name in files:
                dest = os.path.join(root ,name).replace(local_output_folder, server_output_folder + output_folder_base)
                print("# Uploading file " + os.path.join(root ,name) + " to " + dest)
                if not dry_run:
                    sftp.put(os.path.join(root ,name), dest, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
    
        if not dry_run:
            sftp.close()

    except BaseException as e:
        print(e)
"""


