#!/usr/bin/env python3
import subprocess
import os
import csv
import os.path
import sys
import json
import pysftp
from fractions import Fraction
from pathlib import Path
from datetime import datetime
import argparse

################################################################################
# This file implements dpctf-s00001-v033-WAVE-DPC-v1.21
# and uses releases/4/ mezzanine.

# Output file structure: <media_type>_sets/<sub_media_type (frame_rate_family|audio_codec)>/<stream_id>/<upload_date> e.g.
#   cfhd_sets/15_30_60/ss1/2021-10-22/
#   caac_sets/aac_lc/at1/2021-12-04/
#   caaa_sets/he_aac_v2/at1/2021-12-04/
#   See https://github.com/cta-wave/dpctf-tests/issues/59

################################################################################

CSV_DELIMITER = ";"

GPAC_EXECUTABLE = "/usr/local/bin/gpac"

PROFILES_TYPE = {
    "cfhd": "video",
    "chdf": "video",
    "chh1": "video",
    "cud1": "video",
    "chd1": "video",
    "caac": "audio",
    "dts1": "audio",
    "dts2": "audio",
    "cenc": "encrypted"
}

FRAMERATES = [12.5, 25, 50, 15, 30, 60, 14.985, 29.97, 59.94, 23.976]

SERVER_ACCESS_URL = "https://dash.akamaized.net/WAVE/vectors/"


# Mezzanine characteristics:
class InputContent:
    def __init__(self, *args, **row):
        self.content = row['basename']
        self.root_folder = row['location']
        self.fps_family = row['fps_family']
        fps_num = int(row['fps_num'])
        fps_den = row['fps_den']
        fps_den = 1 if fps_den == '' else int(fps_den)
        self.fps = Fraction(fps_num, fps_den)
        self.encoder_hdr_opts = row.get('encoder_hdr_opts', '')
    
    def get_annotations(self, input_basename):
        # Extract copyright
        annotation_filename = input.root_folder + input_basename + ".json"
        if not os.path.exists(annotation_filename):
            errtxt = "Annotation file \"" + annotation_filename + "\" not found. Skipping entry."
            raise FileNotFoundError(errtxt)
        with open(annotation_filename, 'r') as fo:
            data = json.load(fo)
            copyright_notice = data["Mezzanine"]["license"]
            source_notice = "" + data["Mezzanine"]["name"] + " version " + str(data["Mezzanine"]["version"]) + " (" + data["Mezzanine"]["creation_date"] + ")"
            return copyright_notice, source_notice



def create_new_db():
    database = {}
    for profile in PROFILES_TYPE:
        database[profile.upper()] = {}
    return database


class OutputContent:
    
    @staticmethod
    def _parse_csv_bool(value):
        return True if value == 'TRUE' else False

    @staticmethod
    def iter_test_streams(input_csv):
        with open(input_csv) as csv_file:
            csv_reader = csv.DictReader(csv_file, delimiter=CSV_DELIMITER)
            for row in csv_reader:
                stream = OutputContent(**row)
                if not stream.skip:                
                    yield stream

    def __init__(self, *args, **row):
        # required
        self.stream_id = row['Stream ID']
        if self.stream_id.isdigit():
            self.stream_id = f't{self.stream_id}'
        self.mezzanine_radius = row['mezzanine radius']
        self.pic_timing = self._parse_csv_bool(row['pic timing'])
        self.vui_timing = self._parse_csv_bool(row['VUI timing'])
        self.sample_entry = row['sample entry']
        self.cmaf_frag_dur = row['CMAF frag dur']
        self.init_constraints = row['init constraints']
        self.frag_type = row['frag_type']
        self.resolution = row['resolution']
        self.framerate = row['framerate']
        self.bitrate = row['bitrate']
        self.duration = row['duration']
        self.cmaf_profile = row['cmaf_profile']
        self.wave_profile = row['wave_profile']
        self.cenc = self._parse_csv_bool(row['cenc'])
        # optinal
        self.sar = row.get('sar', '')
        self.enc_opts = row.get('enc_opts', '')
        self.skip = bool(row.get('skip', ''))

def format_db_entry(o:OutputContent, source_notice, reps, seg_dur, mpdPath, zipPath):
    return {
        'source': source_notice,
        'representations': reps,
        'segmentDuration': str(seg_dur),
        'fragmentType': o.frag_type,
        'hasSEI': o.pic_timing,
        'hasVUITiming': o.vui_timing,
        'visualSampleEntry': o.sample_entry,
        'mpdPath': mpdPath,
        'zipPath': zipPath
    }


def process_mezzanine(input:InputContent, input_csv, local_output_folder, batch_folder, database={}, encode=True, cenc=True, zip=True, dry_run=False, quiet=False):
    
    if not (encode or cenc or zip):
        return

    output_folder_base = ""
    copyright_notice = ""
    source_notice = ""
    title_notice = ""

    for o in OutputContent.iter_test_streams(input_csv):
            if o.wave_profile == "cfhd":
                codec = "h264"
                cmaf_profile = "avchd"
            elif o.wave_profile == "chdf":
                codec = "h264"
                cmaf_profile = "avchdhf"
            elif o.wave_profile == "chh1":
                codec = "h265"
                cmaf_profile = "chh1"
            elif o.wave_profile == "chd1":
                codec = "h265"
                cmaf_profile = "chd1"
            elif o.wave_profile == "caac":
                codec = "aac"
                cmaf_profile = "caac"
            else:
                codec = "copy"
                cmaf_profile = o.wave_profile

            output_folder_base = f"{o.wave_profile}_sets/{input.fps_family}"
            output_folder_complete = f"{local_output_folder}/{output_folder_base}"
            test_stream_folder_suffix = f"{o.stream_id}/{batch_folder}"

            test_stream_folder = f"{output_folder_complete}/{test_stream_folder_suffix}"
            output_test_stream_folder = f"{output_folder_base}/{test_stream_folder_suffix}"
            server_test_stream_access_url = SERVER_ACCESS_URL + output_test_stream_folder

            # 0: Stream ID, 1: mezzanine radius, 2: pic timing SEI, 3: VUI timing, 4: sample entry,
            # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate,
            # 10: bitrate, 11: duration
            fps = min(FRAMERATES, key=lambda x:abs(x-float(o.framerate)*input.fps))

            input_basename = ""
            if PROFILES_TYPE[o.wave_profile] == "video":
                input_basename = f"{input.content}_{o.mezzanine_radius}@{fps}_{o.duration}"
            else:
                input_basename = f"{input.content}{o.mezzanine_radius}"
            input_filename = input_basename + ".mp4"
            copyright_notice, source_notice = None, None
            try:
                copyright_notice, source_notice = input.get_annotations(input_basename)
            except FileNotFoundError as e:
                if not quiet:
                    print("\n##### Error while processing " + test_stream_folder + " #####\n")
                    print(e)
                continue

            print("\n##### Processing test stream " + test_stream_folder + " #####\n")

            seg_dur = Fraction(o.cmaf_frag_dur)
            if input.fps.denominator == 1001:
                seg_dur = Fraction(o.cmaf_frag_dur) * Fraction(1001, 1000)
            reps = [{"resolution": o.resolution, "framerate": fps, "bitrate": o.bitrate, "input": input_filename}]

            filename_v = input.root_folder + input_filename

            reps_command = f"id:{o.stream_id},type:{PROFILES_TYPE[o.wave_profile]},codec:{codec},vse:{o.sample_entry},cmaf:{cmaf_profile}"
            reps_command += f",fps:{int(float(o.framerate)*input.fps.numerator)}/{input.fps.denominator},res:{o.resolution},bitrate:{o.bitrate}"
            reps_command += f",input:\"{filename_v}\",pic_timing:{o.pic_timing},vui_timing:{o.vui_timing},sd:{str(seg_dur)},bf:{o.frag_type}"

            if o.sar:
                reps_command += f",sar:{o.sar}"

            if input.encoder_hdr_opts:
                reps_command += f",enc_opts:{input.encoder_hdr_opts}"

            # Finalize one-AdaptationSet formatting
            reps_command = "--reps=" + reps_command
                        
            if PROFILES_TYPE[o.wave_profile] == "video":
                title_notice = "{0}, {1}, {2}fps, {3}, Test Vector {4}".format(input.content, o.bitrate, float(o.framerate)*input.fps.numerator/input.fps.denominator, o.wave_profile, o.stream_id)
            else:
                title_notice = "{0}, Test Vector {1}".format(o.wave_profile, o.stream_id)

            # Web exposed information
            database[o.wave_profile.upper()][output_test_stream_folder] = format_db_entry(
                o,
                source_notice,
                reps,
                str(seg_dur),
                '{0}/stream.mpd'.format(server_test_stream_access_url),
                '{0}/{1}.zip'.format(server_test_stream_access_url, o.stream_id)
            )

            if encode:
                # Encode, package, and manifest generation (DASH-only)
                encode_dash_cmd = f"./encode_dash.py --path={GPAC_EXECUTABLE} --out=stream.mpd --outdir={test_stream_folder}"
                encode_dash_cmd += f" --dash=sd:{seg_dur},fd:{seg_dur},ft:{o.frag_type},fr:{input.fps},cmaf:{o.cmaf_profile}"
                encode_dash_cmd += f" --copyright=\'{copyright_notice}\' --source=\'{source_notice}\' --title=\'{title_notice}\' --profile={o.wave_profile} {reps_command}"
                print("# Encoding:\n")
                if dry_run:
                    encode_dash_cmd += " --dry-run"
                print(encode_dash_cmd + "\n")
                result = subprocess.run(encode_dash_cmd, shell=True)

            if zip:
                zip_cmd = "zip -r " + output_test_stream_folder + o.stream_id + ".zip " + output_test_stream_folder + "*"
                print("# Creating archive (cwd=" + local_output_folder + "):\n")
                print(zip_cmd + "\n")
                if not dry_run:
                    result = subprocess.run(zip_cmd, shell=True, cwd=local_output_folder)


            # create an encrypted copy of the stream if requested
            if cenc and o.cenc:
                
                output_test_stream_folder_cenc = "{0}/{1}-cenc/{2}".format(output_folder_base, o.stream_id, batch_folder)
                cenc_cmd = GPAC_EXECUTABLE + " -strict-error -i " + output_test_stream_folder + "/stream.mpd:forward=mani cecrypt:cfile=" + sys.path[0] + "/DRM.xml"
                cenc_cmd += " @ -o " + output_test_stream_folder_cenc + "/stream.mpd:pssh=mv"
                print("\n# Encrypting content (cwd=" + local_output_folder + "):\n")
                print(cenc_cmd)
                if not dry_run:
                    result = subprocess.run(cenc_cmd, shell=True, cwd=local_output_folder)

                # Web exposed information
                server_test_stream_access_url_cenc = SERVER_ACCESS_URL + output_test_stream_folder_cenc
                database["CENC"][output_test_stream_folder_cenc] = format_db_entry(
                    o,
                    source_notice,
                    reps,
                    str(seg_dur),
                    '{0}/stream.mpd'.format(server_test_stream_access_url_cenc),
                    '{0}/{1}.zip'.format(server_test_stream_access_url_cenc, o.stream_id + "-cenc")
                )

                ########################################################################################################################
                # ZIP IT
                if zip:
                    zip_cmd = "zip -r " + output_test_stream_folder_cenc + o.stream_id + "-cenc.zip " + output_test_stream_folder_cenc + "*"
                    print("# Executing (cwd=" + local_output_folder + "):\n")
                    print(zip_cmd)
                    if not dry_run:
                        result = subprocess.run(zip_cmd, shell=True, cwd=local_output_folder)
        # end foreach csv row
    return output_folder_base


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
    

def get_mezzanine_list(mezzanine_cfg):
    res = []
    with open(mezzanine_cfg, 'r') as fi:
        csv_reader = csv.DictReader(fi, delimiter=CSV_DELIMITER)
        for row in csv_reader:
            res.append(InputContent(**row))
        return res

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('MEZZANINE_CFG', help='a csv containing the list of mezzanine files to process')
    parser.add_argument('OUTPUT_CFG', help='csv configuration for test content to be encoded')
    parser.add_argument('-d', '--dry-run', action='store_true', help='do not process commands, just print them out')
    parser.add_argument('-b', '--batch-dir', help='batch directory, defaults to YYYY-MM-DD')
    parser.add_argument('-z', '--zip', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('-u', '--upload', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('-q', '--quiet', action='store_true', help='do not print mezzanine files not found')
    parser.add_argument('--no-encode', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('--no-cenc', action='store_true', help='create a cenc encryption variant of the first stream of the list')
    args = parser.parse_args()

    database = create_new_db()
    local_output_folder = "./output"
    batch_folder = f"{datetime.today().strftime('%Y-%m-%d')}"

    for input in get_mezzanine_list(args.MEZZANINE_CFG):
        output_folder_base = process_mezzanine(input, args.OUTPUT_CFG, local_output_folder, batch_folder, database, (not args.no_encode), (not args.no_cenc), args.zip, args.dry_run, args.quiet)
    
    if not args.dry_run:
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile)

    if args.upload:
        server_output_folder = "/129021/dash/WAVE/vectors/"
        upload_sequence(output_folder_base, server_output_folder, args.dry_run)
        