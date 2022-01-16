#!/bin/sh
set -eux
# tested with GPAC version 1.1.0-DEV-rev1153-g4ad9b4f20-master

export BATCH="2021-07-30

#TODO
#get https://dash-large-files.akamaized.net/WAVE/Mezzanine/under_review/2021-07-30/"

export GPAC="gpac"
# -threads=-1"
# -graph

export MPD=stream.mpd

export AD_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-07-29/splice_ad_bbb_AD-A1_1280x720@25_5.76.mp4:noedit
export MAIN_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-07-29/splice_main_croatia_A1_1280x720@25_10.mp4:noedit
export TID=$BATCH/splice/25
export AD_BASEURL=https://dash.akamaized.net/WAVE/vectors/$TID/
rm -rf $TID && \
export CMD="$GPAC \
  --xps_inband=no \
  -i $MAIN_CONTENT \
    @ reframer:raw=av:#ClampDur=5.76:xs=0,5.76::props=#PStart=0:#m=main1,#PStart=11.52:#m=main2 \
    @ enc:gfloc:c=aac:b=128k:FID=GEN1A \
    @1 enc:gfloc:c=avc:b=2000k:fintra=1.920:profile=high:color_primaries=1:color_trc=1:colorspace=1:x264-params=level=42:no-open-gop=1:scenecut=0 @ bsrw:novsi:FID=GEN1V \
  -i $AD_CONTENT \
    @ reframer:raw=av:#ClampDur=5.76:xs=0:#PStart=5.76:#m=ad:#BUrl=$AD_BASEURL \
    @ enc:gfloc:c=aac:b=128k:FID=GEN2A \
    @1 enc:gfloc:c=avc:b=2000k:fintra=1.920:profile=high:color_primaries=1:color_trc=1:colorspace=1:x264-params=level=42:no-open-gop=1:scenecut=0 @ bsrw:novsi:FID=GEN2V \
  -o output/$TID/$MPD:profile=live:tpl:stl:cdur=1.920:segdur=1.920:stl:cmaf=cmf2:SID=GEN1A,GEN1V,GEN2A,GEN2V --template=\$m\$_\$Type\$_\$Number\$"
echo $CMD
$CMD && code output/$TID/$MPD && ls -l output/$TID

export AD_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-07-29/splice_ad_bbb_AD-A1_1280x720@30_6.4.mp4:noedit
export MAIN_CONTENT=/home/rbouqueau/works/qualcomm/CTA-Wave/Test-Content-Generation/content_files/2021-07-29/splice_main_tos_B1_1920x1080@30_10.mp4:noedit
export TID=$BATCH/splice/30
export AD_BASEURL=https://dash.akamaized.net/WAVE/vectors/$TID/
rm -rf $TID && \
export CMD="$GPAC \
  --xps_inband=no \
  -i $MAIN_CONTENT \
    @ reframer:raw=av:#ClampDur=6.4:xs=0,6.4::props=#PStart=0:#m=main1,#PStart=12.8:#m=main2 \
    @ enc:gfloc:c=aac:b=128k:FID=GEN1A \
    @1 enc:gfloc:c=avc:b=2000k:fintra=32/15:profile=high:color_primaries=1:color_trc=1:colorspace=1:x264-params=level=42:no-open-gop=1:scenecut=0 @ bsrw:novsi:FID=GEN1V \
  -i $AD_CONTENT \
    @ reframer:raw=av:#ClampDur=6.4:xs=0:#PStart=6.4:#m=ad:#BUrl=$AD_BASEURL \
    @ enc:gfloc:c=aac:b=128k:FID=GEN2A \
    @1 enc:gfloc:c=avc:b=2000k:fintra=32/15:profile=high:color_primaries=1:color_trc=1:colorspace=1:x264-params=level=42:no-open-gop=1:scenecut=0 @ bsrw:novsi:FID=GEN2V \
  -o output/$TID/$MPD:profile=live:tpl:stl:cdur=32/15:segdur=32/15:stl:cmaf=cmf2:SID=GEN1A,GEN1V,GEN2A,GEN2V --template=\$m\$_\$Type\$_\$Number\$"
echo $CMD
$CMD && code output/$TID/$MPD && ls -l output/$TID
