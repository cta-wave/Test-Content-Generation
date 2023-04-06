#!/bin/sh
set -eux

# tested with GPAC version 2.3-DEV-rev124-g6c77c0307-master
export MEZZANINE_VERSION="4"
export BATCH="2023-04-06"

export GPAC="/opt/bin/gpac -strict-error \
 -threads=-1"
# -graph

export MPD=stream.mpd

# see https://github.com/cta-wave/mezzanine/issues/40
export SEGDUR=1.92

#available contents:
#  releases/4/splice_ad_bbb_AD-A1_1280x720@25_5.76.mp4
#  releases/4/splice_ad_bbb_AD-A1_1280x720@29.97_21.255.mp4
#  releases/4/splice_ad_bbb_AD-A1_1280x720@30_6.4.mp4
#  releases/4/splice_ad_bbb_AD-B1_1920x1080@25_5.76.mp4
#  releases/4/splice_ad_bbb_AD-B1_1920x1080@29.97_21.255.mp4
#  releases/4/splice_ad_bbb_AD-B1_1920x1080@30_6.4.mp4
#  releases/4/splice_main_croatia_A1_1280x720@25_10.mp4
#  releases/4/splice_main_croatia_B1_1920x1080@25_10.mp4
#  releases/4/splice_main_tos_A1_1280x720@29.97_10.mp4
#  releases/4/splice_main_tos_A1_1280x720@30_10.mp4
#  releases/4/splice_main_tos_B1_1920x1080@29.97_10.mp4
#  releases/4/splice_main_tos_B1_1920x1080@30_10.mp4

#these command-lines are copied from the traces of the 'avc_sets' generation (run-all.py):

#discussed in 2022-01-18 call: specific stream_id of avc_sets
export STREAM_ID=splice_main
export CONTENT_MAIN=content_files/releases/$MEZZANINE_VERSION/splice_main_croatia_A1_1280x720@25_10.mp4
export COPYRIGHT='© Croatia (2019), credited to EBU, used and licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) (https://creativecommons.org/licenses/by/4.0/) by the Consumer Technology Association (CTA)® / annotated, encoded and compressed from original.'
export SOURCE='splice_main_croatia_A1_1280x720@25_10 version $MEZZANINE_VERSION (2022-10-03)'
export TITLE='Croatia, 1280 x 720, 25fps, splice_main, Test Vector 1'
rm -rf output/avc_sets/15_30_60/$STREAM_ID/$BATCH/
./encode_dash.py --path="$GPAC" --out="$MPD" --outdir=output/avc_sets/15_30_60/$STREAM_ID/$BATCH/ --dash=sd:$SEGDUR,fd:$SEGDUR,ft:duration,fr:25: --copyright="$COPYRIGHT" --source="$SOURCE" --title="$TITLE" --profile="cfhd" \
  --reps=id:1,type:video,codec:h264,vse:avc1,cmaf:avchdhf,fps:25/1,res:1280x720,bitrate:2000,input:$CONTENT_MAIN,pic_timing:True,vui_timing:False,sd:$SEGDUR,bf:2

#encrypt
$GPAC -i output/avc_sets/15_30_60/$STREAM_ID/$BATCH/$MPD:forward=mani cecrypt:cfile=DRM.xml @ -o output/avc_sets/15_30_60/$STREAM_ID-cenc/$BATCH/$MPD:pssh=mv

export STREAM_ID=splice_ad
export CONTENT_AD=content_files/releases/$MEZZANINE_VERSION/splice_ad_bbb_AD-A1_1280x720@25_5.76.mp4
export COPYRIGHT='© Croatia (2019), credited to EBU, used and licensed under Creative Commons Attribution 4.0 International (CC BY 4.0) (https://creativecommons.org/licenses/by/4.0/) by the Consumer Technology Association (CTA)® / annotated, encoded and compressed from original.'
export SOURCE='splice_ad_bbb_AD-A1_1280x720@25_5.76 version MEZZANINE_VERSION (2021-08-05)'
export TITLE='Big Buck Bunny, 1280 x 720, 25fps, splice_ad, Test Vector 1'
rm -rf output/avc_sets/15_30_60/$STREAM_ID/$BATCH/
./encode_dash.py --path="$GPAC" --out="$MPD" --outdir=output/avc_sets/15_30_60/$STREAM_ID/$BATCH/ --dash=sd:$SEGDUR,fd:$SEGDUR,ft:duration,fr:25: --copyright="$COPYRIGHT" --source="$SOURCE" --title="$TITLE" --profile="cfhd" \
  --reps=id:1,type:video,codec:h264,vse:avc1,cmaf:avchdhf,fps:25/1,res:1280x720,bitrate:2000,input:$CONTENT_AD,pic_timing:True,vui_timing:False,sd:$SEGDUR,bf:2

#encrypt
$GPAC -i output/avc_sets/15_30_60/$STREAM_ID/$BATCH/$MPD:forward=mani cecrypt:cfile=DRM.xml @ -o output/avc_sets/15_30_60/$STREAM_ID-cenc/$BATCH/$MPD:pssh=mv

