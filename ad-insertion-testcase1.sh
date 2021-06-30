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
    @ resample:osr=48k \
    @1 ffsws:osize=1280x720 \
    @ @1 reframer:#ClampDur=9.6:xs=0,9.6::props=#PStart=0:#m=m1,#PStart=19.2:#m=m3 \
    @ enc:c=aac:FID=GEN1A \
    @1 enc:c=avc:fintra=1.920:FID=GEN1V \
  -i $AD_CONTENT \
    @ resample:osr=48k \
    @1 ffsws:osize=1280x720 \
    @ @1 reframer:#ClampDur=9.6:xs=0:#PStart=9.6:#m=m2:#BUrl=$AD_BASEURL \
    @ enc:c=aac:FID=GEN2A \
    @1 enc:c=avc:fintra=1.920:FID=GEN2V \
  -o $TID/$MPD:segdur=1.920:stl:cmaf=cmf2:SID=GEN1A,GEN1V,GEN2A,GEN2V --template=\$m\$_\$Type\$_\$Number\$"
echo $CMD
$CMD && code $TID/$MPD && ls -l $TID
