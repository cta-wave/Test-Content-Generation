#!/usr/bin/env python3
import subprocess
import os
import csv
import sys
import os.path
import json
import pysftp

# output: SFTP credentials
host = "dashstorage.upload.akamai.com"
username = "sshacs"
cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None    
outputFolder = '/129021/dash/WAVE/vectors/'

resolutions = [
    [
        ['1920x1080', 4500, 30, "content_files/tos_L1_1920x1080@30_60.mp4" ],
        ['1024x576' , 1500, 30, "content_files/tos_I1_1024x576@30_60.mp4"  ],
        ['1024x576' , 1200, 30, "content_files/tos_I2_1024x576@30_60.mp4"  ],
        ['768x432'  , 900 , 30, "content_files/tos_F1_768x432@30_60.mp4"   ],
        ['512x288'  , 450 , 30, "content_files/tos_B1_512x288@30_60.mp4"   ]
    ]
]

database = { }
filepath = './database.json'

# Open the input parameter params
with open('params.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    id = "wave_{0}_{1}"
    has_audio = False # we only support one audio for now
    for row in csv_reader:
        line_count = line_count + 1
        if line_count == 1: 
            continue
        reps_command = "--reps="
        key = id.format("avc_sets", row[0])
        reps = []

        for i in range(len(resolutions[0])):
            reps += [{"resolution": resolutions[0][i][0], "framerate": resolutions[0][i][2], "bitrate": resolutions[0][i][1], "input": resolutions[0][i][3]}]
            if row[1] == "audio":
                if has_audio == False:
                    codec="aac"
                    audio_rep_command = "id:{0},type:{1},codec:{2},bitrate:{3},input:{4}"\
                        .format(i, row[1], codec, resolutions[0][i][1], resolutions[0][i][3])
                    has_audio=True
            else:
                codec="h264"
                cmaf_profile="avchdhf"
                reps_command += "id:{0},type:{1},codec:{2},vse:{3},cmaf:{4},fps:{5},res:{6},bitrate:{7},input:{8},sei:{9},vui_timing:{10}"\
                    .format(i, row[1], codec, row[4], cmaf_profile, resolutions[0][i][2], resolutions[0][i][0], resolutions[0][i][1], resolutions[0][i][3], row[2].capitalize(), row[3].capitalize())

            reps_command += "\|"

        if has_audio == False:
            print("Audio is mandatory. Make sure the audio stream is the first listed stream in the input csv.")
            exit(1)

        if reps_command == None:
            print("Audio only streams are not processed (but the audio will be then attached to video streams) - skipping")
        else:
            database[key] = {
                'representations': reps,
                'segmentDuration': row[6], 
                'fragmentType': row[8], 
                'hasSEI': row[2].lower() == 'true', 
                'hasVUITiming': row[3].lower()== 'true', 
                'visualSampleEntry': row[4],
                'mpdPath': 'avc_sets/{0}/stream.mpd'.format(row[0])
            }

            # add audio
            reps_command += audio_rep_command

            command = "./encode_dash.py --path=/usr/bin/ffmpeg --out=stream.mpd --outdir=output/{0} --dash=sd:{1},ft:{2} {3}".format(row[0], row[6], row[8], reps_command)
            print("Executing " + command)
            result = subprocess.run(command, shell=True)

# Write the database to a file
with open(filepath, 'w') as outfile:
    json.dump(database, outfile)

with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    print("Connection successfully established ... ")

    # Switch to a remote directory and put the data base
    sftp.cwd(outputFolder)
    sftp.put(filepath, outputFolder + filepath)

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
