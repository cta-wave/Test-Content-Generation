#!/bin/zsh
set -eux


export SET_NAME=$1
export FRAMERATES=$2 # eg. "12.5_25_50"
export INPUT_STREAM_ID=$3
export INPUT_BATCH=$4 # eg. "2023-09-01"
export OUTPUT_BATCH=$4 # eg. "2023-09-01"

export VECTORS_DIR="output"
export OUTPUT_STREAM_ID="chunked"
export MPD="stream_$SET_NAME.mpd"

export INPUT_REL_DIR="$SET_NAME"_sets/$FRAMERATES/$INPUT_STREAM_ID/$INPUT_BATCH
export INPUT_DIR=$VECTORS_DIR/$INPUT_REL_DIR
export OUTPUT_REL_DIR="$SET_NAME"_sets/$FRAMERATES/$OUTPUT_STREAM_ID/$OUTPUT_BATCH
export OUTPUT_DIR=$VECTORS_DIR"_chunked"/$OUTPUT_REL_DIR

readonly SCRIPT_DIR=$(dirname $(readlink -f $0))

# clean copy of input
if [[ -d "$OUTPUT_DIR" ]]; then
    echo "$OUTPUT_DIR exists"
    rm -Rf $OUTPUT_DIR
fi
mkdir -p $OUTPUT_DIR
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
cp $SCRIPT_DIR/$MPD ../stream.mpd

popd
#######################################################

# zip
pushd $VECTORS_DIR
export ARCHIVE=$OUTPUT_REL_DIR/$OUTPUT_STREAM_ID.zip
if [[ -f "$ARCHIVE" ]]; then
    rm -f $ARCHIVE
fi
zip -r $ARCHIVE $OUTPUT_REL_DIR/*
popd
