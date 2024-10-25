from pathlib import Path
import csv
import os
import subprocess
import pysftp

root = Path('output')

FPS_FAMILIES = set()

class TestVector:

    @staticmethod
    def csv_headers():
         return ['stream_id', 'profile', *FPS_FAMILIES]

    def __init__(self, stream_id, profile) -> None:
        self.stream_id = stream_id
        self.profile = profile
        self.fps_variants = {}
    
    @property
    def sort_key(self):
        k = 0
        if self.profile.startswith('chh1'):
            k = 0
        elif self.profile.startswith('chd1'):
            k = 1000
        id = self.stream_id
        if self.stream_id.endswith('-cenc'):
            k += 0.5
            id = self.stream_id.split('-')[0]
        if id.startswith('t'):
            k += int(id[1:])
        else:
            k += len(id) + 100
        return k

    def csv_row(self):
        row = {
            'stream_id': self.stream_id,
            'profile': self.profile.split('_')[0]
        }
        for ff in FPS_FAMILIES:
            row[ff] = self.fps_variants.get(ff, '')
        return row


def is_meta(fp):
    return fp.name == '.DS_Store'


def _iter_dir(d):
    for fp in d.iterdir():
        if is_meta(fp):
            os.remove(fp)
            continue
        yield fp

def csv_report(batch):
    rows = []
    for cmaf_set in _iter_dir(root):
        if not cmaf_set.is_dir():
            continue

        cmaf_set_rows = {}

        for fps_family_dir in _iter_dir(cmaf_set):
            
            fps_family = fps_family_dir.name
            FPS_FAMILIES.add(fps_family)
            
            for test_vector in _iter_dir(fps_family_dir):
                
                if is_meta(test_vector):
                        os.remove(test_vector)
                
                if test_vector.name not in cmaf_set_rows:
                    cmaf_set_rows[test_vector.name] = TestVector(test_vector.name, cmaf_set.name)                
                
                tv = cmaf_set_rows[test_vector.name]

                try:
                    batch_dir = test_vector / batch
                    assert len([*_iter_dir(batch_dir)]) == 2, f'unexpected content: {batch_dir}'
                    
                    stream_mpd = batch_dir / 'stream.mpd'
                    assert stream_mpd.exists(), f'not found: {stream_mpd}'
                    
                    segments_dir = batch_dir / '1'
                    assert segments_dir.is_dir(), f'not a directory: {segments_dir}'
                    
                    cmaf_init = segments_dir / 'init.mp4'
                    assert cmaf_init.exists(), f'not found: {cmaf_init}'

                    segments_count = len([*_iter_dir(segments_dir)]) - 1
                    tv.fps_variants[fps_family] = segments_count

                except BaseException as e:
                    print(e)
                    tv.fps_variants[fps_family] = e


        for tv in cmaf_set_rows.values():
            rows.append(tv)

    csv_out = root / f'report_{batch}.csv'
    with open(csv_out, 'w', newline='') as csvfile:
        writer = csv.DictWriter(csvfile, fieldnames=TestVector.csv_headers())
        writer.writeheader()
        for r in sorted(rows, key=lambda tv: tv.sort_key):
            writer.writerow(r.csv_row())


def _iter_batch(batch, skip_missing=True):
    for cmaf_set in _iter_dir(root):
        if not cmaf_set.is_dir():
            continue
        for fps_family_dir in _iter_dir(cmaf_set):
            for test_vector in _iter_dir(fps_family_dir):
                res = test_vector / batch
                if skip_missing and not res.exists():
                    continue
                yield test_vector / batch


def remove_batch(batch):
    trashbin = Path('./trash')
    for batch_item in _iter_batch(batch):
        target = trashbin / batch_item.relative_to(root)
        os.makedirs(target.parent)
        batch_item.rename(target)


def merge_batch(target, *batches, dry_run=False):
    for batch in batches:
        for batch_item in _iter_batch(batch):
            target_dir = batch_item.parent / target
            if (not dry_run) and (not target_dir.exists()):
                os.makedirs(target_dir)
            for fp in _iter_dir(batch_item):
                dst = target_dir/fp.name
                if dry_run:
                    assert not dst.exists()
                else:
                    fp.rename(dst)


def zip_batch(batch, dry_run=False, remove=False):
    print(f"CWD={root}")
    for batch_item in _iter_batch(batch):

        stream_id = batch_item.parent.name
        content_dir = batch_item.relative_to(root)
        archive = content_dir / f'{stream_id}.zip'
        zip_cmd = f"zip -r {archive} {content_dir}*"
        if remove:
            if archive.exists() and not dry_run:
                os.remove(archive)
                continue
        print(zip_cmd)
        if not dry_run:
            result = subprocess.run(zip_cmd, shell=True, cwd=root)
            print(result)


def upload_batch(batch, dry_run=False):

    host = "dashstorage.upload.akamai.com"
    username = "sshacs"
    cnopts = pysftp.CnOpts(knownhosts=host)
    cnopts.hostkeys = None
    remote_vectors_dir = "/129021/dash/WAVE/vectors/"

    try:
        sftp = None if dry_run else pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.getenv('AKAMAI_PRIVATE_KEY')), cnopts=cnopts)

        if sftp is not None:
            print("Connection successfully established ... ")
            sftp.cwd(remote_vectors_dir)

        for batch_item in _iter_batch(batch):
            # eg. output/chh1_sets/14.985_29.97_59.94/splice_ad-cenc/2024-10-25
            print(f"\n##### {batch_item} ####################\n")
            for r, _, files in batch_item.walk(top_down=True):

                remote_dir = remote_vectors_dir + str(r.relative_to(root))
                print(f"Create remote directory: {remote_dir}")
                if not dry_run:
                    if not sftp.isfile(remote_dir):
                        sftp.makedirs(remote_dir, mode=644)
                
                for f in files:
                    local_file = r / f
                    remote_file = f"{remote_dir}/{f}"
                    print(f"Upload '{local_file}' to: '{remote_file}'")
                    if not dry_run:
                        sftp.put(local_file, remote_file, callback=lambda x,y: print(f"{x} transferred out of {y}"))

        if not dry_run:
            sftp.close()

    except BaseException as e:
        print(e)




if __name__ == "__main__":

    # remove_batch('2024-10-24')

    # merge_batch('2024-10-25', '2024-10-23')
    # remove_batch('2024-10-23')

    # csv_report('2024-10-25')

    # zip_batch('2024-10-25')
    upload_batch('2024-10-25')
