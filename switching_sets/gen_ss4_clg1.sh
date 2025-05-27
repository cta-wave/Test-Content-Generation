#!/bin/bash
set -eux

SSi="ss4"
REPS=("t50" "t51" "t52" "t53")
PROFILE="clg1"
BATCH_IN="2025-01-15" # input batch
BATCH_OUT="2025-05-24" # change when you need to regenerate the output in a different batch folder

SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
INPUT_DIR="$SCRIPT_DIR/../output"
OUTPUT_DIR="$SCRIPT_DIR/../output_ss_$PROFILE" # make it different of $INPUT_DIR to avoid collisions and deletions of input files

# safety check
if ! grep $BATCH_IN $SCRIPT_DIR/"$PROFILE"_*.mpd >/dev/null 2>/dev/null; then
    echo "ERROR: you must replace the batch dates in the MPD files with \"$BATCH_IN\". Make sure these files exist first."
    exit 1
fi

mkdir -p $OUTPUT_DIR
cd $OUTPUT_DIR

FRAMERATES=( '12.5_25_50' '15_30_60' '14.985_29.97_59.94' )

for FR in "${FRAMERATES[@]}" ; do

    SS_OUTPUT_RELDIR=switching_sets/$FR/"$SSi"_"$PROFILE"/$BATCH_OUT
    mkdir -p $SS_OUTPUT_RELDIR
    cp $SCRIPT_DIR/"$PROFILE"_"$FR"_"$SSi"_stream.mpd $SS_OUTPUT_RELDIR/stream.mpd

    for SINGLE in "${REPS[@]}" ; do
        SINGLE_DIR="$PROFILE"_sets/$FR/$SINGLE/$BATCH_IN/1
        mkdir -p $SINGLE_DIR
        cp -r $INPUT_DIR/$SINGLE_DIR/* $SINGLE_DIR
    done

    # delete old archives
    #find . -name '*.zip' | xargs rm

    # create archive
    zip -r $SS_OUTPUT_RELDIR/"$SSi"_$PROFILE.zip "$PROFILE"_sets $SS_OUTPUT_RELDIR

    # delete duplicated files
    rm -rf $OUTPUT_DIR/"$PROFILE"_sets
done
