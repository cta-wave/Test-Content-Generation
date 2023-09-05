#!/usr/bin/bash
set -eux

export INPUT_BATCH="2023-09-01"
export OUTPUT_BATCH="2023-09-01"

export SET_NAME=$1
export INPUT_STREAM_ID=$2

export MPD=stream.mpd
export INPUT_DIR=output/$SET_NAME_sets/12.5_25_50/$INPUT_STREAM_ID/$INPUT_BATCH/
export OUTPUT_STREAM_ID=chunked
export OUTPUT=chunked
export OUTPUT_DIR=output/$SET_NAME_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/

readonly SCRIPT_DIR=$(dirname $(readlink -f $0))

# clean copy of input
mkdir -p $OUTPUT_DIR
rm -rf $OUTPUT_DIR/*
cp -r $INPUT_DIR/* $OUTPUT_DIR/

#######################################################
# chunking
pushd $OUTPUT_DIR/1

cp $SCRIPT_DIR/styp .

## chunk segments
for f in `ls *.m4s`; do
    $SCRIPT_DIR/isobmff_chunker.py 5 `basename $f .m4s`
    rm $f
done

rm styp

## modify MPD
cp $SCRIPT_DIR/stream.mpd ../stream.mpd

popd
#######################################################

# zip
pushd output
rm $SET_NAME_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/$INPUT_STREAM_ID.zip
zip -r $SET_NAME_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/$OUTPUT_STREAM_ID.zip $SET_NAME_sets/12.5_25_50/$OUTPUT_STREAM_ID/$OUTPUT_BATCH/*
popd
