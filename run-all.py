#!/usr/bin/env python3
import subprocess
import os
import csv
import os.path
import json
import pysftp
from fractions import Fraction

# NB: dry_run generates the json database
dry_run = False

# Current run:
batch_folder = "2022-01-17/" # uses mezzanine v2

gpac_executable = "/opt/bin/gpac"

dts_profile = "dtsx_51_t1cc"

# TODO: should be sync'ed, cf Thomas Stockhammer's requests
# Mezzanine characteristics:
class InputContent:
    def __init__(self, content, root_folder, set, fps_family, fps):
        self.content = content
        self.root_folder = root_folder
        self.set = set
        self.fps_family = fps_family
        self.fps = fps

inputs = [
    InputContent("tos",     "content_files/dts/fixed/", "dts_sets/" + dts_profile, "23.976", Fraction(24000, 1001)),
]

# Used for folder names only
framerates = [12.5, 25, 50, 15, 30, 60, 14.985, 29.97, 59.94, 23.976]

# Output parameters
local_output_folder = "./output"
server_output_folder = "/129021/dash/WAVE/vectors/" + batch_folder

# Web database to be exported
server_access_url = "https://dash.akamaized.net/WAVE/vectors/" + batch_folder
database = { }
database["CFHD"] = { }
database["CENC"] = { }
database_filepath = './database.json'


# Generate CMAF content: encode, package, annotate, and encrypt
for input in inputs:
    copyright_notice = ""
    output_folder_base = "{0}/{1}".format(input.set, input.fps_family)
    output_folder_complete = "{0}/{1}".format(local_output_folder, output_folder_base)

    switching_set_X1_IDs = [ "1", "20", "23", "24", "25", "28", "32", "34" ] # keep ordered
    switching_set_X1_command = ""
    switching_set_X1_reps = []

    with open('switching_sets_single_track.csv') as csv_file:
        csv_reader = csv.reader(csv_file, delimiter=',')
        csv_line_index = 0
        for row in csv_reader:
            csv_line_index = csv_line_index + 1
            if csv_line_index == 1:
                continue

            switching_set_folder_suffix = "{0}{1}".format("t", row[0])
            switching_set_folder = "{0}/{1}".format(output_folder_complete, switching_set_folder_suffix)
            output_switching_set_folder = "{0}/{1}".format(output_folder_base, switching_set_folder_suffix)
            server_switching_set_access_url = server_access_url + output_switching_set_folder
            print("===== Processing single track Switching Set " + switching_set_folder + " =====")

            # 0: Stream ID, 1: mezzanine radius, 2: pic timing, 3: VUI timing, 4: sample entry,
            # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate, 10: bitrate
            fps = min(framerates, key=lambda x:abs(x-float(row[9])*input.fps))
            #Romain: input_basename = "{0}_{1}@{2}_60".format(input.content, row[1], fps)
            input_basename = dts_profile
            input_filename = input_basename + ".mp4"
            seg_dur = Fraction(row[5])
            if input.fps.denominator == 1001:
                seg_dur = Fraction(row[5]) * Fraction(1001, 1000)
            reps = [{"resolution": row[8], "framerate": fps, "bitrate": row[10], "input": input_filename}]
            codec_v="h264"
            cmaf_profile="avchdhf"
            #Romain: filename_v=input.root_folder + input_filename
            filename_v="/home/rbouqueau/works/dts/202106_cta-wave/CMAF Assets/Transient_UHD_SDR_422HQ_Stereo.mov"
            reps_command = "id:{0},type:video,codec:{1},vse:{2},cmaf:{3},fps:{4}/{5},res:{6},bitrate:{7},input:\"{8}\",sei:{9},vui_timing:{10},sd:{11}"\
                .format(row[0], codec_v, row[4], cmaf_profile, int(float(row[9])*input.fps.numerator), input.fps.denominator, row[8], row[10],
                        filename_v, row[2].capitalize(), row[3].capitalize(), str(seg_dur))

            # SS-X1
            if row[0] in switching_set_X1_IDs:
                if row[0] != switching_set_X1_IDs[0]: # assumes orderness
                    switching_set_X1_command += "\|"
                switching_set_X1_command += reps_command
                switching_set_X1_reps += reps
                switching_set_X1_seg_dur = seg_dur

            # Add audio
            #Romain: codec_a="aac"
            codec_a="copy"
            filename_a=input.root_folder + input_filename
            audio_command = "id:{0},type:audio,codec:{1},bitrate:{2},input:\"{3}\""\
                .format("a", codec_a, "128k", filename_a)
            reps_command += "\|"
            reps_command += audio_command

            reps_command = "--reps=" + reps_command

            # SS-X1: select the first available audio
            if csv_line_index == 2:
                switching_set_X1_command += "\|"
                switching_set_X1_command += audio_command

            # Web exposed information
            database["CFHD"][output_switching_set_folder] = {
                'representations': reps,
                'segmentDuration': str(seg_dur),
                'fragmentType': row[7],
                'hasSEI': row[2].lower() == 'true',
                'hasVUITiming': row[3].lower() == 'true',
                'visualSampleEntry': row[4],
                'mpdPath': '{0}/stream.mpd'.format(server_switching_set_access_url),
                'zipPath': '{0}.zip'.format(server_switching_set_access_url)
            }

            # Extract copyright
            #Romain: annotation_filename = input.root_folder + input_basename + ".json"
            annotation_filename = filename_v + ".json"
            with open(annotation_filename, 'r') as annotations:
                 data = annotations.read()
                 copyright_notice = json.loads(data)["Mezzanine"]["license"]

            command = "./encode_dash.py --path=/opt/bin/gpac --out=stream.mpd --outdir={0} --dash=sd:{1},fd:{1},ft:{2},fr:{3} --copyright='{4}' {5}"\
                .format(switching_set_folder, seg_dur, row[7], input.fps, copyright_notice, reps_command)
            print("Executing " + command)
            if dry_run == False:
                result = subprocess.run(command, shell=True)

            # Create unencrypted archive
            command = "zip " + output_switching_set_folder + ".zip " + output_switching_set_folder + "/*"
            print("Executing " + command + " (cwd=" + local_output_folder + ")")
            if dry_run == False:
                result = subprocess.run(command, shell=True, cwd=local_output_folder)

            # Special case for first encoding: create side streams
            if csv_line_index == 2:
                # CENC
                command = gpac_executable + " -i " + output_switching_set_folder + "/stream.mpd:forward=mani cecrypt:cfile=DRM.xml @ -o " + output_switching_set_folder + "-cenc/stream.mpd:pssh=mv"
                print("Executing " + command + " (cwd=" + local_output_folder + ")")
                if dry_run == False:
                    result = subprocess.run(command, shell=True, cwd=local_output_folder)

                # Web exposed information
                database["CENC"][output_switching_set_folder + "-cenc"] = {
                    'representations': reps,
                    'segmentDuration': str(seg_dur),
                    'fragmentType': row[7],
                    'hasSEI': row[2].lower() == 'true',
                    'hasVUITiming': row[3].lower() == 'true',
                    'visualSampleEntry': row[4],
                    'mpdPath': '{0}-cenc/stream.mpd'.format(server_switching_set_access_url),
                    'zipPath': '{0}-cenc.zip'.format(server_switching_set_access_url)
                }

                # Create CENC archive
                command = "zip " + output_switching_set_folder + "-cenc.zip " + output_switching_set_folder + "-cenc/*"
                print("Executing " + command + " (cwd=" + local_output_folder + ")")
                if dry_run == False:
                    result = subprocess.run(command, shell=True, cwd=local_output_folder)

    #TODO: the Switching Set should not be regenerated but derived from the representations with a MPD construction (e.g. GPAC manifest writing from existing segments)
    print("===== " + "Switching Set " + output_folder_base + "X1 =====")
    switching_set_X1_command = "--reps=" + switching_set_X1_command
    command = "./encode_dash.py --path={0} --out=stream.mpd --outdir={1}/ss1 --dash=sd:{2},ft:duration --copyright='{3}' {4}"\
        .format(gpac_executable, output_folder_complete, switching_set_X1_seg_dur, copyright_notice, switching_set_X1_command)
    print("Executing " + command)
    if dry_run == False:
        result = subprocess.run(command, shell=True)

    # Web exposed information
    database["CFHD"][output_folder_base + "/ss1"] = {
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
    command = "zip {0}/ss1.zip {0}/ss1/*".format(output_folder_base)
    print("Executing " + command + " (cwd=" + local_output_folder + ")")
    if dry_run == False:
        result = subprocess.run(command, shell=True, cwd=local_output_folder)


# Write Web exposed information
with open(database_filepath, 'w') as outfile:
    json.dump(database, outfile)

#Romain
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
