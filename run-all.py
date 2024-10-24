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
    def __init__(self, content, root_folder, fps_family, fps:Fraction):
        self.content = content
        self.root_folder = root_folder
        self.fps_family = fps_family # video: frame_rate_family ; audio: audio_codec
        self.fps = fps
    
    def get_annotations(self, input_basename):
        # Extract copyright
        annotation_filename = input.root_folder + input_basename + ".json"
        if not os.path.exists(annotation_filename):
            errtxt = "Annotation file \"" + annotation_filename + "\" not found. Skipping entry."
            print(errtxt)
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


def iter_csv(input_csv):
    with open(input_csv) as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        for row in csv_reader:
            if row[0] == "Stream ID":
                continue
            yield row


def iter_test_streams(input_csv):
    csv_line_index = 0
    for row in iter_csv(input_csv):

        if row[0] == "Stream ID":
            continue

        # Decide which stream to process based on the media type and the WAVE media profile
        wave_profile = row[13]
        if PROFILES_TYPE[wave_profile] == "video":
            if row[0][0] == 'a':
                continue
            if row[0][0].isdigit():
                stream_id = "{0}{1}".format("t", row[0])
            else:
                stream_id = row[0]
        else:
            if row[0][0] != 'a':
                continue
            stream_id = row[0]
        
        # do CENC for 1st stream only
        csv_line_index += 1
        cenc_stream = csv_line_index == 1

        yield stream_id, wave_profile, row, cenc_stream


def process_mezzanine(input:InputContent, input_csv, local_output_folder, batch_folder, database={}, encode=True, cenc=True, zip=True, dry_run=False):
    
    if not (encode or cenc or zip):
        return

    output_folder_base = ""
    copyright_notice = ""
    source_notice = ""
    title_notice = ""

    for (stream_id, wave_profile, row) in iter_test_streams(input_csv):
            
            cmaf_profile = "avchd"
            if wave_profile == "cfhd":
                codec = "h264"
                cmaf_profile = "avchd"
            elif wave_profile == "chdf":
                codec = "h264"
                cmaf_profile = "avchdhf"
            elif wave_profile == "chh1":
                codec = "h265"
                cmaf_profile = "chh1"
            elif wave_profile == "chd1":
                codec = "h265"
                cmaf_profile = "chd1"
            elif wave_profile == "caac":
                codec = "aac"
                cmaf_profile = "caac"
            else:
                codec = "copy"
                cmaf_profile = wave_profile

            # test_stream.get_output_folder_base(input.fps_family)
            output_folder_base = "{0}_sets/{1}".format(wave_profile, input.fps_family)
            output_folder_complete = "{0}/{1}".format(local_output_folder, output_folder_base)
            test_stream_folder_suffix = stream_id + "/" + batch_folder

            test_stream_folder = "{0}/{1}".format(output_folder_complete, test_stream_folder_suffix)
            output_test_stream_folder = "{0}/{1}".format(output_folder_base, test_stream_folder_suffix)
            server_test_stream_access_url = SERVER_ACCESS_URL + output_test_stream_folder

            print("\n##### Processing test stream " + test_stream_folder + " #####\n")

            # 0: Stream ID, 1: mezzanine radius, 2: pic timing SEI, 3: VUI timing, 4: sample entry,
            # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate,
            # 10: bitrate, 11: duration
            fps = min(FRAMERATES, key=lambda x:abs(x-float(row[9])*input.fps))

            input_basename = ""
            if PROFILES_TYPE[wave_profile] == "video":
                input_basename = "{0}_{1}@{2}_{3}".format(input.content, row[1], fps, row[11])
            else:
                input_basename = "{0}{1}".format(input.content, row[1])
            input_filename = input_basename + ".mp4"
            copyright_notice, source_notice = None, None
            try:
                copyright_notice, source_notice = input.get_annotations(input_basename)
            except FileNotFoundError as e:
                continue

            seg_dur = Fraction(row[5])
            if input.fps.denominator == 1001:
                seg_dur = Fraction(row[5]) * Fraction(1001, 1000)
            reps = [{"resolution": row[8], "framerate": fps, "bitrate": row[10], "input": input_filename}]

            filename_v = input.root_folder + input_filename
            reps_command = "id:{0},type:{1},codec:{2},vse:{3},cmaf:{4},fps:{5}/{6},res:{7},bitrate:{8},input:\"{9}\",pic_timing:{10},vui_timing:{11},sd:{12},bf:{13}"\
                .format(row[0], PROFILES_TYPE[wave_profile], codec, row[4], cmaf_profile, int(float(row[9])*input.fps.numerator), input.fps.denominator, row[8], row[10],
                        filename_v, row[2].capitalize(), row[3].capitalize(), str(seg_dur), row[7])

            #if row[1].find(row[8]) == -1:
            #    mezzanine_par = row[1].split('_')[1].split('x')
            #    encoding_par = row[8].split('x')
            #    reps_command += ",sar:" + str(int(mezzanine_par[0])*int(encoding_par[1])) + "/" + str(int(mezzanine_par[1])*int(encoding_par[0]))

            # Finalize one-AdaptationSet formatting
            reps_command = "--reps=" + reps_command
                        
            if PROFILES_TYPE[wave_profile] == "video":
                title_notice = "{0}, {1}, {2}fps, {3}, Test Vector {4}".format(input.content, row[8], float(row[9])*input.fps.numerator/input.fps.denominator, wave_profile, row[0])
            else:
                title_notice = "{0}, Test Vector {1}".format(wave_profile, row[0])

            # Web exposed information
            database[wave_profile.upper()][output_test_stream_folder] = {
                'source': source_notice,
                'representations': reps,
                'segmentDuration': str(seg_dur),
                'fragmentType': row[7],
                'hasSEI': row[2].lower() == 'true',
                'hasVUITiming': row[3].lower() == 'true',
                'visualSampleEntry': row[4],
                'mpdPath': '{0}stream.mpd'.format(server_test_stream_access_url),
                'zipPath': '{0}{1}.zip'.format(server_test_stream_access_url, stream_id)
            }

            if encode:
                # Encode, package, and manifest generation (DASH-only)
                encode_dash_cmd = f"./encode_dash.py --path={GPAC_EXECUTABLE} --out=stream.mpd --outdir={test_stream_folder}"
                encode_dash_cmd += f" --dash=sd:{seg_dur},fd:{seg_dur},ft:{row[7]},fr:{input.fps},cmaf:{row[12]}"
                encode_dash_cmd += f" --copyright=\'{copyright_notice}\' --source=\'{source_notice}\' --title=\'{title_notice}\' --profile={wave_profile} {reps_command}"
                print("# Encoding:\n")
                if dry_run:
                    encode_dash_cmd += " --dry-run"
                print(encode_dash_cmd + "\n")
                result = subprocess.run(encode_dash_cmd, shell=True)

            if zip:
                zip_cmd = "zip -r " + output_test_stream_folder + stream_id + ".zip " + output_test_stream_folder + "*"
                print("# Creating archive (cwd=" + local_output_folder + "):\n")
                print(zip_cmd + "\n")
                if not dry_run:
                    result = subprocess.run(zip_cmd, shell=True, cwd=local_output_folder)


            # create an encrypted copy of the stream if requested
            cenc_stream = bool(row[14])

            if cenc and cenc_stream:
                
                output_test_stream_folder_cenc = "{0}/{1}-cenc/{2}".format(output_folder_base, stream_id, batch_folder)
                cenc_cmd = GPAC_EXECUTABLE + " -strict-error -i " + output_test_stream_folder + "/stream.mpd:forward=mani cecrypt:cfile=" + sys.path[0] + "/DRM.xml"
                cenc_cmd += " @ -o " + output_test_stream_folder_cenc + "/stream.mpd:pssh=mv"
                print("# Encrypting content:\n (cwd=" + local_output_folder + "):\n")
                print(cenc_cmd)
                if not dry_run:
                    result = subprocess.run(cenc_cmd, shell=True, cwd=local_output_folder)

                # Web exposed information
                server_test_stream_access_url_cenc = SERVER_ACCESS_URL + output_test_stream_folder_cenc
                database["CENC"][output_test_stream_folder_cenc] = {
                    'source': source_notice,
                    'representations': reps,
                    'segmentDuration': str(seg_dur),
                    'fragmentType': row[7],
                    'hasSEI': row[2].lower() == 'true',
                    'hasVUITiming': row[3].lower() == 'true',
                    'visualSampleEntry': row[4],
                    'mpdPath': '{0}stream.mpd'.format(server_test_stream_access_url_cenc),
                    'zipPath': '{0}{1}.zip'.format(server_test_stream_access_url_cenc, stream_id + "-cenc")
                }

                ########################################################################################################################
                # ZIP IT
                if zip:
                    zip_cmd = "zip -r " + output_test_stream_folder_cenc + stream_id + "-cenc.zip " + output_test_stream_folder_cenc + "*"
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
        csv_reader = csv.DictReader(fi, delimiter=',')
        for row in csv_reader:
            skips = getattr(row, 'skip', '')
            if skips != '':
                continue
            basename = row['basename']
            location = row['location']
            fps_family = row['fps_family']
            fps_num = int(row['fps_num'])
            fps_den = row['fps_den']
            fps_den = 1 if fps_den == '' else int(fps_den)
            res.append(InputContent(basename, location, fps_family, Fraction(fps_num, fps_den)))
    return res

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('MEZZANINE_CFG', help='a csv containing the list of mezzanine files to process')
    parser.add_argument('OUTPUT_CFG', help='the wave profile being batch processed (chh1, cud1, chd1, ...). a corresponding csv configuration file is expected in the profiles directory')
    parser.add_argument('-d', '--dry-run', action='store_true', help='do not process commands, just print them out')
    parser.add_argument('-b', '--batch-dir', help='batch directory, defaults to YYYY-MM-DD')
    parser.add_argument('-z', '--zip', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('-u', '--upload', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('--no-encode', action='store_true', help='upload content to public server over sftp')
    parser.add_argument('--no-cenc', action='store_true', help='create a cenc encryption variant of the first stream of the list')
    args = parser.parse_args()

    database = create_new_db()
    local_output_folder = "./output"
    batch_folder = f"{datetime.today().strftime('%Y-%m-%d')}"

    for input in get_mezzanine_list(args.MEZZANINE_CFG):
        output_folder_base = process_mezzanine(input, args.OUTPUT_CFG, local_output_folder, batch_folder, database, (not args.no_encode), (not args.no_cenc), args.zip, args.dry_run)
    
    if not args.dry_run:
        with open('./database.json', 'w') as outfile:
            json.dump(database, outfile)

    if args.upload:
        server_output_folder = "/129021/dash/WAVE/vectors/"
        upload_sequence(output_folder_base, server_output_folder, args.dry_run)
        