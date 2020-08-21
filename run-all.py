#!/usr/bin/env python3
import subprocess
from subprocess import PIPE
import os
import csv
import sys


with open('params.csv') as csv_file:
    csv_reader = csv.reader(csv_file, delimiter=',')
    line_count = 0

    for row in csv_reader:
        command = "./encode_dash.py --path=/usr/bin/ffmpeg --out=out_{0}.mpd --dash=sd:2 --reps=id:{0},type:v,codec:h264,vse:{1},cmaf:avchdhf,fps:30,res:{2},bitrate:{3},input:{4} --outdir=stream_{0}".format(row[0], row[3], row[8], int(row[10])/1000, sys.argv[1])
        print("Executing " + command)
        result = subprocess.run(command, shell=True)