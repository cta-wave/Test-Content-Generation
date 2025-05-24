#!/bin/bash
set -eux

SSi="ss3"
PROFILE="cud1"
BATCH_OUT="2025-05-24"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )
INPUT_DIR="$SCRIPT_DIR/../output"
OUTPUT_DIR="$SCRIPT_DIR/../output_ss_$PROFILE" # make it different of $INPUT_DIR to avoid collisions and deletions of input files

mkdir -p $OUTPUT_DIR
cd $OUTPUT_DIR

FRAMERATES=( '12.5_25_50' '15_30_60' '14.985_29.97_59.94' )

for FR in "${FRAMERATES[@]}" ; do

    SS_OUTPUT_RELDIR=switching_sets/$FR/"$SSi"_"$PROFILE"/$BATCH_OUT
    mkdir -p $SS_OUTPUT_RELDIR
    cp $SCRIPT_DIR/"$PROFILE"_"$FR"_"$SSi"_stream.mpd $SS_OUTPUT_RELDIR/stream.mpd

    t30_dir="cud1_sets/$FR/t30/2025-01-15/1/" 
    mkdir -p $t30_dir
    cp -r $INPUT_DIR/$t30_dir* $t30_dir

    t31_dir="cud1_sets/$FR/t31/2025-04-15/1/"
    mkdir -p $t31_dir
    cp -r $INPUT_DIR/$t31_dir* $t31_dir

    t32_dir="cud1_sets/$FR/t32/2025-04-15/1/"
    mkdir -p $t32_dir
    cp -r $INPUT_DIR/$t32_dir* $t32_dir

    # delete old archives
    #find . -name '*.zip' | xargs rm

    # create archive
    zip -r $SS_OUTPUT_RELDIR/"$SSi"_$PROFILE.zip "$PROFILE"_sets $SS_OUTPUT_RELDIR

    # delete duplicated files
    rm -rf $OUTPUT_DIR/"$PROFILE"_sets
done
