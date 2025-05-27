#!/bin/bash
set -eux

INPUT_DIR="$PWD/output/"
OUTPUT_DIR="$PWD/output_ss1/" # make it different of $INPUT_DIR to avoid collisions and deletions of input files
BATCH_IN="2023-09-01" # input batch
BATCH_OUT="2025-05-24" # Romain: $BATCH_IN # change when you need to regenerate the output in a different batch folder
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

# safety check
if ! grep $BATCH_IN $SCRIPT_DIR/avc_*.mpd >/dev/null 2>/dev/null; then
    echo "ERROR: you must replace the batch dates in the MPD files with \"$BATCH_IN\". Make sure these files exist first."
    exit 1
fi

mkdir -p $OUTPUT_DIR
cd $OUTPUT_DIR

FRAMERATES=( '12.5_25_50' '15_30_60' '14.985_29.97_59.94' )
for FR in "${FRAMERATES[@]}" ; do
    SS1_OUTPUT_RELDIR=switching_sets/$FR/ss1/$BATCH_OUT
    mkdir -p $SS1_OUTPUT_RELDIR

    cp $SCRIPT_DIR/avc_"$FR"_ss1_stream.mpd $SS1_OUTPUT_RELDIR/stream.mpd

    REPS=("t19" "t23" "t24" "t25" "t28" "t32" "t34")
    for SINGLE in "${REPS[@]}" ; do
        SINGLE_DIR=cfhd_sets/$FR/$SINGLE/$BATCH_IN/1/
        mkdir -p $SINGLE_DIR
        cp -r $INPUT_DIR/$SINGLE_DIR/* $SINGLE_DIR
    done

    mkdir -p chdf_sets/$FR/t20/$BATCH_IN/1/
    cp -r $INPUT_DIR/chdf_sets/$FR/t20/$BATCH_IN/1/* chdf_sets/$FR/t20/$BATCH_IN/1/

    # delete old archives
    #find . -name '*.zip' | xargs rm

    # create archive
    zip -r $SS1_OUTPUT_RELDIR/ss1.zip cfhd_sets chdf_sets $SS1_OUTPUT_RELDIR

    # delete duplicated files
    rm -rf cfhd_sets chdf_sets
done
