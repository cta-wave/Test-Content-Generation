#!/usr/bin/env python3
import subprocess
import os
import csv
import sys
import os.path
import json
import pysftp

# TODO: should be sync'ed, cf Thomas Stockhammer's requests
content_folder = "content_files/"

# Output parameters: SFTP credentials
host = "dashstorage.upload.akamai.com"
username = "sshacs"
cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None    
outputFolder = '/129021/dash/WAVE/vectors/'
database = { }
wwwfilepath = './database.json'

with open('switching_sets_single_track.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0

    switching_set_X1_IDs = [ "1", "20", "23", "24", "25", "28", "32", "34" ] # keep ordered
    switching_set_X1_command = ""

    #TODO: fps multiples should be a parameter
    content = "avc/15_30_60/{0}{1}"
    fps_base = 60

    for row in csv_reader:
        line_count = line_count + 1
        if line_count == 1:
            continue

        key = content.format("t", row[0])
        print("===== Processing single track Switching Set " + key + " =====")

        # 0: Stream ID, 1: mezzanine prefix, 2: pic timing, 3: VUI timing, 4: sample entry,
        # 5: CMAF frag dur, 6: init constraints, 7: frag_type, 8: resolution, 9: framerate, 10: bitrate
        reps = [{"resolution": row[8], "framerate": float(row[9])*fps_base, "bitrate": row[10], "input": row[1]}]
        codec="h264"
        cmaf_profile="avchdhf"
        reps_command = "id:{0},type:video,codec:{1},vse:{2},cmaf:{3},fps:{4},res:{5},bitrate:{6},input:{7},sei:{8},vui_timing:{9}"\
            .format(row[0], codec, row[4], cmaf_profile, float(row[9])*fps_base, row[8], row[10], content_folder + row[1], row[2].capitalize(), row[3].capitalize())

        # SS-X1
        if row[0] in switching_set_X1_IDs:
            if row[0] != switching_set_X1_IDs[0]: # assumes orderness
                switching_set_X1_command += "\|"
            switching_set_X1_command += reps_command

        # Add audio
        audio_command = "id:{0},type:audio,codec:aac,bitrate:{1},input:{2}"\
            .format("a", "128k", content_folder + row[1])
        reps_command += "\|"
        reps_command += audio_command

        # SS-X1: add the first available audio
        if line_count == 2:
            switching_set_X1_command += "\|"
            switching_set_X1_command += audio_command

        #TODO: update the Web exposed information
        database[key] = {
            'representations': reps,
            'segmentDuration': row[5],
            'fragmentType': row[7],
            'hasSEI': row[1].lower() == 'true',
            'hasVUITiming': row[2].lower() == 'true',
            'visualSampleEntry': row[3],
            'mpdPath': 'avc/15_30_60/t{0}/stream.mpd'.format(row[0])
        }

        reps_command = "--reps=" + reps_command
        command = "./encode_dash.py --path=/opt/bin/gpac --out=stream.mpd --outdir=output/t{0} --dash=sd:{1},ft:{2} {3}".format(row[0], row[5], row[7], reps_command)
        print("Executing " + command)
        #result = subprocess.run(command, shell=True)

    print("===== " + "Switching Set " + content.format("X", 1) + " =====")
    switching_set_X1_command = "--reps=" + switching_set_X1_command
    command = "./encode_dash.py --path=/opt/bin/gpac --out=stream.mpd --outdir=output/ss1 --dash=sd:2,ft:duration {0}".format(switching_set_X1_command)
    print("Executing " + command)
    result = subprocess.run(command, shell=True)

with open(wwwfilepath, 'w') as outfile:
    json.dump(database, outfile)

with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    print("Connection successfully established ... ")

    # Switch to a remote directory and put the data base
    sftp.cwd(outputFolder)
    sftp.put(wwwfilepath, outputFolder + wwwfilepath)

    # Create the directory structure if it does not exist
    for root, dirs, files in os.walk('./output', topdown=True):
        for name in dirs:
            p =  os.path.join(root ,name).replace('./output', outputFolder + 'avc_sets')
            if not sftp.isfile(p): 
                print("Creating directory " + p)
                sftp.mkdir(p, mode=644)

    # Put the files
    for root, dirs, files in os.walk('./output', topdown=True):
        for name in files:
            dest = os.path.join(root ,name).replace('./output', outputFolder + 'avc_sets')
            print("Upload file " + os.path.join(root ,name) + " to " + dest)
            sftp.put(os.path.join(root ,name), dest, callback=lambda x,y: print("{} transferred out of {}".format(x,y)))
