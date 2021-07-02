#!/usr/bin/env python3
import subprocess
import os
import csv
import sys
import os.path
import json
import pysftp

dry_run = False

gpac_executable = "/opt/bin/gpac"

# TODO: should be sync'ed, cf Thomas Stockhammer's requests
# Mezzanine characteristics:
class InputContent:
    def __init__(self, root_folder, set, fps_family, fps):
        self.root_folder = root_folder
        self.set = set
        self.fps_family = fps_family
        self.fps = fps

inputs = [
    InputContent("content_files/", "avc_sets", "15_30_60", 60),
    #InputContent("content_files/", "avc_sets", "12.5_25_50", 50),
    #InputContent("content_files/", "avc_sets", "14.985_29.97_59.94", 59.94),
]

# Output parameters
server_root_folder = '/129021/dash/WAVE/vectors/'

# Web database to be exported
database = { }
database_filepath = './database.json'


# Generate CMAF content: encode, package, annotate, and encrypt
with open('switching_sets_single_track.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    csv_line_index = 0

    switching_set_X1_IDs = [ "1", "20", "23", "24", "25", "28", "32", "34" ] # keep ordered
    switching_set_X1_command = ""
    switching_set_X1_reps = []

    for input in inputs:
        output_folder_base = "{0}/{1}".format(input.set, input.fps_family)
        local_folder_base = "./output"
        local_output_folder = "{0}/{1}".format(local_folder_base, output_folder_base)

        for row in csv_reader:
            csv_line_index = csv_line_index + 1
            if csv_line_index == 1:
                continue

            switching_set_folder_suffix = "{0}{1}".format("t", row[0])
            switching_set_folder = "{0}/{1}".format(local_output_folder, switching_set_folder_suffix)
            output_switching_set_folder = "{0}/{1}".format(output_folder_base, switching_set_folder_suffix)
            print("===== Processing single track Switching Set " + switching_set_folder + " =====")

            # 0: Stream ID, 1: mezzanine prefix, 2: pic timing, 3: VUI timing, 4: sample entry,
            # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate, 10: bitrate
            reps = [{"resolution": row[8], "framerate": float(row[9])*input.fps, "bitrate": row[10], "input": row[1]}]
            codec="h264"
            cmaf_profile="avchdhf"
            reps_command = "id:{0},type:video,codec:{1},vse:{2},cmaf:{3},fps:{4},res:{5},bitrate:{6},input:{7},sei:{8},vui_timing:{9}"\
                .format(row[0], codec, row[4], cmaf_profile, float(row[9])*input.fps, row[8], row[10], input.root_folder + row[1], row[2].capitalize(), row[3].capitalize())

            # SS-X1
            if row[0] in switching_set_X1_IDs:
                if row[0] != switching_set_X1_IDs[0]: # assumes orderness
                    switching_set_X1_command += "\|"
                switching_set_X1_command += reps_command
                switching_set_X1_reps += reps

            # Add audio
            audio_command = "id:{0},type:audio,codec:aac,bitrate:{1},input:{2}"\
                .format("a", "128k", input.root_folder + row[1])
            reps_command += "\|"
            reps_command += audio_command

            # SS-X1: select the first available audio
            if csv_line_index == 2:
                switching_set_X1_command += "\|"
                switching_set_X1_command += audio_command

            # Web exposed information
            database[switching_set_folder] = {
                'representations': reps,
                'segmentDuration': row[5],
                'fragmentType': row[7],
                'hasSEI': row[1].lower() == 'true',
                'hasVUITiming': row[2].lower() == 'true',
                'visualSampleEntry': row[3],
                'mpdPath': '{0}/stream.mpd'.format(output_switching_set_folder),
                'zipPath': '{0}.zip'.format(output_switching_set_folder)
            }

            reps_command = "--reps=" + reps_command
            command = "./encode_dash.py --path=/opt/bin/gpac --out=stream.mpd --outdir={0} --dash=sd:{1},ft:{2} {3}".format(switching_set_folder, row[5], row[7], reps_command)
            print("Executing " + command)
            if dry_run == False:
                result = subprocess.run(command, shell=True)

            # Create unencrypted archive
            command = "zip " + output_switching_set_folder + ".zip " + output_switching_set_folder + "/*"
            print("Executing " + command + " (cwd=" + local_folder_base + ")")
            if dry_run == False:
                result = subprocess.run(command, shell=True, cwd=local_folder_base)

            # CENC
            command = gpac_executable + " -i " + output_switching_set_folder + "/stream.mpd:forward=mani cecrypt:cfile=DRM.xml @ -o " + output_switching_set_folder + "-cenc/stream.mpd:pssh=mv"
            print("Executing " + command + " (cwd=" + local_folder_base + ")")
            if dry_run == False:
                result = subprocess.run(command, shell=True, cwd=local_folder_base)

            # Create CENC archive
            command = "zip " + output_switching_set_folder + "-cenc.zip " + output_switching_set_folder + "-cenc/*"
            print("Executing " + command + " (cwd=" + local_folder_base + ")")
            if dry_run == False:
                result = subprocess.run(command, shell=True, cwd=local_folder_base)


        print("===== " + "Switching Set " + output_folder_base + "X1 =====")
        switching_set_X1_command = "--reps=" + switching_set_X1_command
        command = "./encode_dash.py --path={0} --out=stream.mpd --outdir={1}/ss1 --dash=sd:2,ft:duration {2}".format(gpac_executable, local_output_folder, switching_set_X1_command)
        print("Executing " + command)
        if dry_run == False:
            result = subprocess.run(command, shell=True)

        # Web exposed information
        database[local_output_folder + "/ss1"] = {
            'representations': switching_set_X1_reps,
            'segmentDuration': row[5],
            'fragmentType': row[7],
            'hasSEI': row[1].lower() == 'true',
            'hasVUITiming': row[2].lower() == 'true',
            'visualSampleEntry': row[3],
            'mpdPath': '{0}/ss1/stream.mpd'.format(output_folder_base),
            'zipPath': '{0}/ss1.zip'.format(output_folder_base)
        }

        # Create unencrypted archive
        command = "zip {0}/ss1.zip {0}/ss1/*".format(output_folder_base)
        print("Executing " + command + " (cwd=" + local_folder_base + ")")
        if dry_run == False:
            result = subprocess.run(command, shell=True, cwd=local_folder_base)

        # CENC
        command = gpac_executable + " -i " + output_folder_base + "/stream.mpd:forward=mani cecrypt:cfile=DRM.xml @ -o " + output_folder_base + "-cenc/stream.mpd:pssh=mv"
        print("Executing " + command + " (cwd=" + local_folder_base + ")")
        if dry_run == False:
            result = subprocess.run(command, shell=True, cwd=local_folder_base)

        # Create CENC archive
        command = "zip {0}/ss1-cenc.zip {0}/ss1-cenc/*".format(output_folder_base)
        print("Executing " + command + " (cwd=" + local_folder_base + ")")
        if dry_run == False:
            result = subprocess.run(command, shell=True, cwd=local_folder_base)


# Write Web exposed information
with open(database_filepath, 'w') as outfile:
    json.dump(database, outfile)


# SFTP
host = "dashstorage.upload.akamai.com"
username = "sshacs"
cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None

with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    print("Connection successfully established ... ")

    # Switch to a remote directory and put the data base
    sftp.cwd(server_root_folder)
    sftp.put(database_filepath, server_root_folder + database_filepath)

    # Create the directory structure if it does not exist
    for root, dirs, files in os.walk(local_output_folder, topdown=True):
        for name in dirs:
            p =  os.path.join(root ,name).replace(local_output_folder, server_root_folder + output_folder_base)
            if not sftp.isfile(p): 
                print("Creating directory " + p)
                sftp.mkdir(p, mode=644)

    # Put the files
    for root, dirs, files in os.walk(local_output_folder, topdown=True):
        for name in files:
            dest = os.path.join(root ,name).replace(local_output_folder, server_root_folder + output_folder_base)
            print("Upload file " + os.path.join(root ,name) + " to " + dest)
            sftp.put(os.path.join(root ,name), dest, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
