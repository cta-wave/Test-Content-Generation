#!/bin/bash
set -eux

INPUT_DIR="$PWD/output/"
OUTPUT_DIR="$PWD/output_ss2/" # make it different of $INPUT_DIR to avoid collisions and deletions of input files
BATCH="2023-09-01"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

mkdir -p $OUTPUT_DIR
cd $OUTPUT_DIR

FRAMERATES=( '12.5_25_50' '15_30_60' '14.985_29.97_59.94' )
for FR in "${FRAMERATES[@]}" ; do
    SS2_OUTPUT_RELDIR=switching_sets/$FR/ss2/$BATCH
    mkdir -p $SS2_OUTPUT_RELDIR

    cp $SCRIPT_DIR/avc_"$FR"_ss2_stream.mpd $SS2_OUTPUT_RELDIR/stream.mpd

    REPS=("t10" "t11" "t12")
    for SINGLE in "${REPS[@]}" ; do
        SINGLE_DIR=chh1_sets/$FR/$SINGLE/$BATCH/1/
        mkdir -p $SINGLE_DIR
        cp -r $INPUT_DIR/$SINGLE_DIR/* $SINGLE_DIR
    done

    # delete old archives
    #find . -name '*.zip' | xargs rm

    # create archive
    zip -r $SS2_OUTPUT_RELDIR/ss2.zip chh1_sets $SS2_OUTPUT_RELDIR

    # delete duplicated files
    rm -rf chh1_sets
done
