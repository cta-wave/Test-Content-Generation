#!/usr/bin/env python3
import subprocess
import os
import csv
import sys


resolutions = [
    ['1920x1080',7800, 60, "content_files/tos_O1_3840x2160@60_60.mp4" ],['1920x1080',6000, 60, "content_files/tos_O2_3840x2160@60_60.mp4" ],
    ['1280 x 720',4500, 60, "content_files/tos_O3_3840x2160@60_60.mp4" ],['1280x720',3000, 60, "content_files/tos_N1_3200x1800@60_60.mp4" ],
    ['768x432',1100, 30, "content_files/tos_M1_2560x1440@60_60.mp4" ],['768x432',730, 30, "content_files/tos_L1_1920x1080@60_60.mp4" ]
    ]
with open('params.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0

    for row in csv_reader:
        line_count = line_count + 1
        if line_count == 1: 
            continue
        for i in range(len(resolutions)): 
            reps_command = "--reps="
            reps_command += "id:{0},type:v,codec:h264,vse:{1},cmaf:avchdhf,fps:{2},res:{3},bitrate:{4},input:{5},sei:{6},vui_timing:{7}".format(i, row[3], resolutions[i][2], resolutions[i][0], resolutions[i][1], resolutions[i][3], row[1].capitalize(), row[2].capitalize())

            command = "./encode_dash.py --path=/usr/local/bin/ffmpeg --out=rep_{0}-stream_{4}.mpd  --outdir=output/{0}/stream_{4} --dash=sd:{1},ft:{2} {3}".format(row[0],  row[5], row[7], reps_command, i)
            print("Executing " + command)
            result = subprocess.run(command, shell=True)