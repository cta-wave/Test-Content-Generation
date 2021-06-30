#!/bin/sh
set -eux
# tested with GPAC version 1.1.0-DEV-rev943-g2ad1a5ec-master-x64.exe
# TODO: add period id to all periods (reported for case 1/2.b)
# Derived from https://github.com/Dash-Industry-Forum/Test-Content/issues/1

export BATCH=batch1

export GPAC="gpac"
# -threads=-1"
# -graph

export MPD=ad-insertion-testcase1.mpd

export AD_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-06-26/croatia_J1_1280x720@25_60.mp4
export MAIN_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-06-30/ad_bbb_AD-A1_1280x720@25_30.mp4

export TID=splice-testcase1/$BATCH/
#export AD_BASEURL=https://www.gpac-licensing.com/downloads/CTA-Wave/$TID
export AD_BASEURL=https://dash.akamaized.net/WAVE/vectors/$TID
rm -rf $TID && \
export CMD="$GPAC \
  -i $MAIN_CONTENT \
    @ reframer:FID=GEN1:#ClampDur=9.6:xs=0,9.6::props=#PStart=0:#m=m1,#PStart=19.2:#m=m3 \
  -i $AD_CONTENT \
    @ reframer:FID=GEN2:#ClampDur=9.6:xs=9.6:#PStart=9.6:#m=m2:#BUrl=$AD_BASEURL \
  -o $TID/$MPD:segdur=1.920:stl:cmaf=cmf2:SID=GEN1,GEN2 --template=\$m\$_\$Type\$_\$Number\$"
echo $CMD
$CMD && code $TID/$MPD && ls -l $TID
