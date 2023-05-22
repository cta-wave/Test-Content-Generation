#!/usr/bin/bash
set -eux

export INPUT_BATCH="2023-04-28"
export OUTPUT_BATCH="2023-05-21"

export MPD=stream.mpd
export INPUT_STREAM_ID=t16
export INPUT_DIR=output/cfhd_sets/12.5_25_50/$INPUT_STREAM_ID/$INPUT_BATCH/
export OUTPUT_STREAM_ID=chunked
export OUTPUT=chunked
export OUTPUT_DIR=output/cfhd_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/

# clean copy of input
mkdir -p $OUTPUT_DIR
rm -rf $OUTPUT_DIR/*
cp -r $INPUT_DIR/* $OUTPUT_DIR/

#######################################################
# chunking
pushd $OUTPUT_DIR/1

cp $(dirname $0)/styp .

## chunk segments
for f in `ls *.m4s`; do
    $(dirname $0)/isobmff_chunker.py 5 `basename $f .m4s`
    rm $f
done

rm styp

## modify MPD
cp $(dirname $0)/stream.mpd ../stream.mpd

popd
#######################################################

# zip
pushd output
rm cfhd_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/$INPUT_STREAM_ID.zip
zip -r cfhd_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/$OUTPUT_STREAM_ID.zip cfhd_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/*
popd
