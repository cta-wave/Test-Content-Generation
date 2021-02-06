#!/usr/bin/env python3
import subprocess
import os
import csv
import sys
import os.path
import json
import pysftp

# Output: SFTP credentials
host = "dashstorage.upload.akamai.com"
username = "sshacs"
cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None    
outputFolder = '/129021/dash/WAVE/vectors/'

# TODO: link to params.csv - currently only references Switching Set X1
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
    for row in csv_reader:
        line_count = line_count + 1
        if line_count == 1: 
            continue
        reps_command = "--reps="
        key = id.format("avc_sets", row[0])
        reps = []

        for i in range(len(resolutions[0])):
            reps += [{"resolution": resolutions[0][i][0], "framerate": resolutions[0][i][2], "bitrate": resolutions[0][i][1], "input": resolutions[0][i][3]}]
            codec="h264"
            cmaf_profile="avchdhf"
            reps_command += "id:{0},type:video,codec:{1},vse:{2},cmaf:{3},fps:{4},res:{5},bitrate:{6},input:{7},sei:{8},vui_timing:{9}"\
                .format(i, codec, row[3], cmaf_profile, resolutions[0][i][2], resolutions[0][i][0], resolutions[0][i][1], resolutions[0][i][3], row[1].capitalize(), row[2].capitalize())

            reps_command += "\|"

        #add audio
        reps_command += "id:{0},type:audio,codec:aac,bitrate:{1},input:{2}"\
            .format(len(resolutions[0])+1, resolutions[0][i][1], resolutions[0][i][3])

        database[key] = {
            'representations': reps,
            'segmentDuration': row[5],
            'fragmentType': row[7],
            'hasSEI': row[1].lower() == 'true',
            'hasVUITiming': row[2].lower() == 'true',
            'visualSampleEntry': row[3],
            'mpdPath': 'avc_sets/{0}/stream.mpd'.format(row[0])
        }

        command = "./encode_dash.py --path=/usr/bin/ffmpeg --out=stream.mpd --outdir=output/{0} --dash=sd:{1},ft:{2} {3}".format(row[0], row[5], row[7], reps_command)
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
