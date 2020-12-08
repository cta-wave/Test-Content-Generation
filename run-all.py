#!/usr/bin/env python3
import subprocess
import os
import csv
import sys
import os.path
import json
import pysftp

host = "dashstorage.upload.akamai.com"
username = "sshacs"


cnopts = pysftp.CnOpts(knownhosts=host)
cnopts.hostkeys = None    
basePath = '/129021/dash/WAVE/vectors'
resolutions = [
    ['1920x1080',7800, 60, "content_files/tos_O1_3840x2160@60_60.mp4" ],['1920x1080',6000, 60, "content_files/tos_O2_3840x2160@60_60.mp4" ],
    ['1280x720',4500, 60, "content_files/tos_O3_3840x2160@60_60.mp4" ],['1280x720',3000, 60, "content_files/tos_N1_3200x1800@60_60.mp4" ],
    ['768x432',1100, 30, "content_files/tos_M1_2560x1440@60_60.mp4" ],['768x432',730, 30, "content_files/tos_L1_1920x1080@60_60.mp4" ]
    ]
database = { }
filepath = './database.json'
with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['PASSWORD']), cnopts=cnopts) as sftp:
    print("Connection succesfully stablished ... ")
    # Switch to a remote directory
    sftp.cwd(basePath)
    # Print data
    database = { }
    
    sftp.get('./database.json', filepath)

    if os.path.isfile(filepath): 
        with open(filepath) as json_file:
            database = json.load(json_file)

with open('params.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0
    id = "wave_{0}_{1}"  # contains 
    for row in csv_reader:
        line_count = line_count + 1
        if line_count == 1: 
            continue
        reps_command = "--reps="
        key = id.format("avc_sets", row[0])
        reps = []

        for i in range(len(resolutions)): 
            reps =reps + [{"resolution": resolutions[i][0], "framerate": resolutions[i][2], "bitrate": resolutions[i][1], "input": resolutions[i][3]}]
            reps_command += "id:{0},type:v,codec:h264,vse:{1},cmaf:avchdhf,fps:{2},res:{3},bitrate:{4},input:{5},sei:{6},vui_timing:{7}".format(i, row[3], resolutions[i][2], resolutions[i][0], resolutions[i][1], resolutions[i][3], row[1].capitalize(), row[2].capitalize())
            if i != len(resolutions) -1:
                reps_command += "\|"
        database[key] = {
            'representations': reps,
            'segmentDuration': row[5], 
            'fragmentType': row[7], 
            'hasSEI': row[1].lower() == 'true', 
            'hasVUITiming': row[2].lower()== 'true', 
            'visualSampleEntry':  row[3],
            'mpdPath': 'avc_sets/{0}/stream.mpd'.format(row[0])
        }
        command = "./encode_dash.py --path=/usr/local/bin/ffmpeg --out=stream.mpd  --outdir=output/{0} --dash=sd:{1},ft:{2} {3}".format(row[0],  row[5], row[7], reps_command)
        print("Executing " + command)
    #     result = subprocess.run(command, shell=True)
        
    with open(filepath, 'w') as outfile:
        json.dump(database, outfile)


with pysftp.Connection(host=host, username=username, private_key=os.path.expanduser(os.environ['AKAMAI_PRIVATE_KEY']), cnopts=cnopts) as sftp:
    print("Connection succesfully stablished ... ") 
    # Switch to a remote directory
    sftp.cwd(basePath)


    sftp.put(filepath, basePath + '/database.json')

    # Create the directory structure if it does not exist
    for  root, dirs, files  in os.walk('./output', topdown=True):
        for name in dirs:
            p =  os.path.join(root ,name).replace('./output',basePath + '/avc_sets')
            if not sftp.isfile(p): 
                print("Creating directory " + p)
                sftp.mkdir(p, mode=644)


    # Put the files
    for  root, dirs, files  in os.walk('./output', topdown=True):
        for name in files:
            dest = os.path.join(root ,name).replace('./output',basePath + '/avc_sets')
            print("upload file " + os.path.join(root ,name) + " to " + dest)
            sftp.put(os.path.join(root ,name), dest, callback=lambda x,y: print("{} transfered out of {}".format(x,y)))