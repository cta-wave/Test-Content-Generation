#!/bin/bash
set -eux

INPUT_DIR="$PWD/output/"
OUTPUT_DIR="$PWD/output_ss1/"
BATCH="2022-09-30"
SCRIPT_DIR=$( cd -- "$( dirname -- "${BASH_SOURCE[0]}" )" &> /dev/null && pwd )

cd $OUTPUT_DIR

FRAMERATES=( '12.5_25_50' '15_30_60' '14.985_29.97_59.94' )
for FR in "${FRAMERATES[@]}" ; do
    mkdir -p cfhd_sets/$FR/ss1/$BATCH
    pushd cfhd_sets/$FR/ss1/$BATCH
    cp $SCRIPT_DIR/ss1_$FR.mpd stream.mpd

    mkdir -p cfhd_sets/$FR/
    pushd cfhd_sets/$FR/
    REPS=("t19" "t23" "t24" "t25" "t28" "t32" "t34")
    for SINGLE in "${REPS[@]}" ; do
        mkdir $SINGLE
        cp -r $INPUT_DIR/cfhd_sets/$FR/$SINGLE/$BATCH/1/* $SINGLE
    done
    popd

    mkdir -p chdf_sets/$FR/
    pushd chdf_sets/$FR/
    cp -r $INPUT_DIR/chdf_sets/$FR/t20 .
    popd

    # delete old archives
    find . -name '*.zip' | xargs rm

    # create archive
    zip -r ss1.zip .

    popd
done

#TODO: manipulate manifest: replace old batch with new + take gpac version/generation date from another MPD
#      MPD could be stored in this repo?

