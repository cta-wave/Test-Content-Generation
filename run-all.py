#!/usr/bin/env python3
import subprocess
import os
import csv
import os.path
import json
import pysftp
from fractions import Fraction

################################################################################
# This file implements dpctf-s00001-v033-WAVE-DPC-v1.21
# and uses 2021-04-21 mezzanine (merge with symlinks from releases/2/ for the 60s content):
#   for i in `ls ../releases/2` ; do if [ -f $i ] ; then echo "exists $i" ; else ln -s ../releases/2/$i $i ; fi ; done
################################################################################

gpac_executable = "/opt/bin/gpac"

# NB: dry_run generates a local json database
dry_run = False

# Output file structure: <media_type>_sets/<sub_media_type (frame_rate_family|audio_codec)>/<stream_id>/<upload_date> e.g.
#   cfhd_sets/15_30_60/ss1/2021-10-22/
#   caac_sets/aac_lc/at1/2021-12-04/
#   caaa_sets/he_aac_v2/at1/2021-12-04/
#
# More at https://github.com/cta-wave/dpctf-tests/issues/59

# Current subfolder
batch_folder = "2022-06-28/"

# Mezzanine characteristics:
class InputContent:
    def __init__(self, content, root_folder, set, fps_family, fps):
        self.content = content
        self.root_folder = root_folder
        self.set = set
        self.fps_family = fps_family # video: frame_rate_family ; audio: audio_codec

        # Video only
        self.fps = fps

inputs = [
    # Video
    InputContent("croatia", "content_files/2022-04-21/", "cfhd_sets", "12.5_25_50",         Fraction(50)),
    InputContent("tos", "content_files/2022-04-21/", "cfhd_sets", "15_30_60",           Fraction(60)),
    InputContent("tos", "content_files/2022-04-21/", "cfhd_sets", "14.985_29.97_59.94", Fraction(60000, 1001)),

    # Audio
    #TODO: replace with http://dash-large-files.akamaized.net/WAVE/Mezzanine/under_review/2022-04-01/ when validated
    #InputContent("tos", "content_files/2022-04-21/", "caac_sets", "AAC-LC", Fraction(60000, 1001)),
]

profiles_type = {
    "cfhd": "video",
    "caac": "audio",
    "cenc": "encrypted"
}

# Used for computing folder names only
framerates = [12.5, 25, 50, 15, 30, 60, 14.985, 29.97, 59.94, 23.976]

# Output parameters
local_output_folder = "./output"
server_output_folder = "/129021/dash/WAVE/vectors/"

# Web database to be exported
server_access_url = "https://dash.akamaized.net/WAVE/vectors/"
database_filepath = './database.json'
database = { }
for profile in profiles_type:
    database[profile.upper()] = { }

# Generate CMAF content: encode, package, annotate, and encrypt
for input in inputs:
    wave_profile = input.set[:4]

    copyright_notice = ""
    source_notice = ""
    output_folder_base = "{0}/{1}".format(input.set, input.fps_family)
    output_folder_complete = "{0}/{1}".format(local_output_folder, output_folder_base)

    switching_set_X1_IDs = [ "19", "20", "23", "24", "25", "28", "32", "34", "audio" ]
    switching_set_X1_command = ""
    switching_set_X1_reps = []

    with open('switching_sets_single_track.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        csv_line_index = 0
        for row in csv_reader:
            if row[0] == "Stream ID":
                continue;

            # Decide which stream to process based on the media type and the WAVE media profile
            if profiles_type[wave_profile] == "video":
                if row[0] == "audio":
                    continue;
                stream_id = "{0}{1}".format("t", row[0])
            else:
                if row[0] != "audio":
                    continue;
                stream_id = row[0]

            # Count index for index-based processing (e.g. CENC)
            csv_line_index = csv_line_index + 1

            switching_set_folder_suffix = stream_id + "/" + batch_folder
            switching_set_folder = "{0}/{1}".format(output_folder_complete, switching_set_folder_suffix)
            output_switching_set_folder = "{0}/{1}".format(output_folder_base, switching_set_folder_suffix)
            server_switching_set_access_url = server_access_url + output_switching_set_folder
            print("===== Processing single track Switching Set " + switching_set_folder + " =====")

            # 0: Stream ID, 1: mezzanine radius, 2: pic timing, 3: VUI timing, 4: sample entry,
            # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate,
            # 10: bitrate, 11: duration
            fps = min(framerates, key=lambda x:abs(x-float(row[9])*input.fps))
            input_basename = "{0}_{1}@{2}_{3}".format(input.content, row[1], fps, row[11])
            input_filename = input_basename + ".mp4"
            seg_dur = Fraction(row[5])
            if input.fps.denominator == 1001:
                seg_dur = Fraction(row[5]) * Fraction(1001, 1000)
            reps = [{"resolution": row[8], "framerate": fps, "bitrate": row[10], "input": input_filename}]

            # TODO: these should be input parameters
            cmaf_profile = "avchd"
            if profiles_type[wave_profile] == "video":
                codec = "h264"
            else:
                codec = "aac"

            filename_v=input.root_folder + input_filename
            reps_command = "id:{0},type:{1},codec:{2},vse:{3},cmaf:{4},fps:{5}/{6},res:{7},bitrate:{8},input:\"{9}\",sei:{10},vui_timing:{11},sd:{12}"\
                .format(row[0], profiles_type[wave_profile], codec, row[4], cmaf_profile, int(float(row[9])*input.fps.numerator), input.fps.denominator, row[8], row[10],
                        filename_v, row[2].capitalize(), row[3].capitalize(), str(seg_dur))

            # SS-X1
            if row[0] in switching_set_X1_IDs:
                if switching_set_X1_command:
                    switching_set_X1_command += "\|"
                switching_set_X1_command += reps_command
                switching_set_X1_reps += reps
                switching_set_X1_seg_dur = seg_dur

            # Finalize one-AdaptationSet formatting
            reps_command = "--reps=" + reps_command

            # Extract copyright
            annotation_filename = input.root_folder + input_basename + ".json"
            with open(annotation_filename, 'r') as annotations:
                 data = annotations.read()
                 copyright_notice = json.loads(data)["Mezzanine"]["license"]
                 source_notice = "" + json.loads(data)["Mezzanine"]["name"] + " version " + str(json.loads(data)["Mezzanine"]["version"]) + " (" + json.loads(data)["Mezzanine"]["creation_date"] + ")"

            title_notice = "{0}, {1}, {2}fps, {3}, Test Vector {4}".format(input.content, row[8], float(row[9])*input.fps.numerator/input.fps.denominator, cmaf_profile, row[0])

            # Web exposed information
            database[wave_profile.upper()][output_switching_set_folder] = {
                'source': source_notice,
                'representations': reps,
                'segmentDuration': str(seg_dur),
                'fragmentType': row[7],
                'hasSEI': row[2].lower() == 'true',
                'hasVUITiming': row[3].lower() == 'true',
                'visualSampleEntry': row[4],
                'mpdPath': '{0}stream.mpd'.format(server_switching_set_access_url),
                'zipPath': '{0}{1}.zip'.format(server_switching_set_access_url, stream_id)
            }

            # Encode, package, and annotate (DASH-only)
            command = "./encode_dash.py --path=/opt/bin/gpac --out=stream.mpd --outdir={0} --dash=sd:{1},fd:{1},ft:{2},fr:{3} --copyright='{4}' --source='{5}' --title='{6}' {7}"\
                .format(switching_set_folder, seg_dur, row[7], input.fps, copyright_notice, source_notice, title_notice, reps_command)
            print("Executing " + command)
            if dry_run == False:
                result = subprocess.run(command, shell=True)
            exit(1) #Romain
            # Create unencrypted archive
            command = "zip " + output_switching_set_folder + stream_id + ".zip " + output_switching_set_folder + "*"
            print("Executing " + command + " (cwd=" + local_output_folder + ")")
            if dry_run == False:
                result = subprocess.run(command, shell=True, cwd=local_output_folder)

            print("")

            # Special case for first encoding: create side CENC streams
            if csv_line_index == 1:
                output_switching_set_folder_cenc = "{0}/{1}-cenc/{2}".format(output_folder_base, stream_id, batch_folder)
                command = gpac_executable + " -i " + output_switching_set_folder + "stream.mpd:forward=mani cecrypt:cfile=DRM.xml @ -o " + output_switching_set_folder_cenc + "stream.mpd:pssh=mv"
                print("Executing " + command + " (cwd=" + local_output_folder + ")")
                if dry_run == False:
                    result = subprocess.run(command, shell=True, cwd=local_output_folder)

                # Web exposed information
                server_switching_set_access_url_cenc = server_access_url + output_switching_set_folder_cenc
                database["CENC"][output_switching_set_folder_cenc] = {
                    'source': source_notice,
                    'representations': reps,
                    'segmentDuration': str(seg_dur),
                    'fragmentType': row[7],
                    'hasSEI': row[2].lower() == 'true',
                    'hasVUITiming': row[3].lower() == 'true',
                    'visualSampleEntry': row[4],
                    'mpdPath': '{0}stream.mpd'.format(server_switching_set_access_url_cenc),
                    'zipPath': '{0}{1}.zip'.format(server_switching_set_access_url_cenc, stream_id + "-cenc")
                }

                # Create CENC archive
                command = "zip " + output_switching_set_folder_cenc + stream_id + "-cenc.zip " + output_switching_set_folder_cenc + "*"
                print("Executing " + command + " (cwd=" + local_output_folder + ")")
                if dry_run == False:
                    result = subprocess.run(command, shell=True, cwd=local_output_folder)

                print("")

    # Generate a SwitchingSet when there is more than 1 stream (i.e. more than 0 "\|" separator) in it
    if switching_set_X1_command.count("\|") > 0:
        #TODO: the Switching Set chould be derived from the representations with a MPD construction
        #      (e.g. GPAC manifest writing from existing segments)
        output_switching_set_folder_ss1 = "{0}/{1}/{2}".format(output_folder_complete, "ss1", batch_folder)
        print("===== " + "Switching Set " + output_switching_set_folder_ss1 + " =====")
        switching_set_X1_command = "--reps=" + switching_set_X1_command
        command = "./encode_dash.py --path={0} --out=stream.mpd --outdir={1} --dash=sd:{2},ft:duration --copyright='{3}' --source='{4}' {5}"\
            .format(gpac_executable, output_switching_set_folder_ss1, switching_set_X1_seg_dur, copyright_notice, source_notice, switching_set_X1_command)
        print("Executing " + command)
        if dry_run == False:
            result = subprocess.run(command, shell=True)

        # Web exposed information
        database["CFHD"][output_folder_base + "/ss1"] = {
            'source': "CTA WAVE",
            'representations': switching_set_X1_reps,
            'segmentDuration': str(switching_set_X1_seg_dur),
            'fragmentType': row[7],
            'hasSEI': row[2].lower() == 'true',
            'hasVUITiming': row[3].lower() == 'true',
            'visualSampleEntry': row[4],
            'mpdPath': '{0}/ss1/stream.mpd'.format(server_access_url + output_folder_base),
            'zipPath': '{0}/ss1.zip'.format(server_access_url + output_folder_base)
        }

        # Create unencrypted archive
        command = "zip {0}ss1.zip {0}*".format(output_folder_base + "/ss1/" + batch_folder)
        print("Executing " + command + " (cwd=" + local_output_folder + ")")
        if dry_run == False:
            result = subprocess.run(command, shell=True, cwd=local_output_folder)

        print("")

# Write Web exposed information
with open(database_filepath, 'w') as outfile:
    json.dump(database, outfile)

if dry_run == True:
    exit(1)

# SFTP
host = "dashstorage.upload.akamai.com"
username = "sshacs"
cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None

with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    print("Connection successfully established ... ")

    # Switch to a remote directory
    sftp.cwd(server_output_folder)

    # Create the directory structure if it does not exist
    for root, dirs, files in os.walk(local_output_folder, topdown=True):
        for name in dirs:
            p =  os.path.join(root ,name).replace(local_output_folder, server_output_folder + output_folder_base)
            if not sftp.isfile(p): 
                print("Creating directory " + p)
                if dry_run == False:
                    sftp.mkdir(p, mode=644)

    # Put the files
    for root, dirs, files in os.walk(local_output_folder, topdown=True):
        for name in files:
            dest = os.path.join(root ,name).replace(local_output_folder, server_output_folder + output_folder_base)
            print("Upload file " + os.path.join(root ,name) + " to " + dest)
            if dry_run == False:
                sftp.put(os.path.join(root ,name), dest, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
