# Test-Content-Generation

## Overview

This repository provides the information and scripts to generate the CTA Wave Test Content.

The ```run-all.py [optional_csv_file]``` script gathers the data and content from input tables/parameters. Then it sends them for processing. Then it uploads the result.

The ```encode_dash.py``` script is primarily about the usage of [GPAC](http://gpac.io) leveraging libavcodec with x264 and x265 to generate the CMAF content with some DASH manifest. The intent is to keep the size of the post-processing (e.g. manifest manipulation) as small as possible.

## Workflow

* Download mezzanine content from https://dash.akamaized.net/WAVE/Mezzanine/. See section below for a script.
* Launch scripts:
  * Encode mezzanine content:
    * Encode to conform to CTA Proposed Test content.
    * Encode at least one option of source content according to media profile.
    * Special codec value "copy" to bypass the encoding. Useful for proprietary codecs such as DTS or Dolby.
  * Package (markup) the content with an MPD according to the CTA Content Model format.
    * NB: done in Python right now, but could eventually an extension to [GPAC](http://gpac.io) to produce this.
  * Encrypt the content in-place using [GPAC](http://gpac.io) encryption and manifest-forwarding capabilities.
  * Upload the proposed test content to the CTA-WAVE server using SFTP.
  * Update the Webpage: update [database.json](https://github.com/cta-wave/Test-Content/blob/master/database.json).
    * NB: updates and merges are [done manually](https://github.com/cta-wave/Test-Content-Generation/issues/45).
    * NB: the Web page code is located at https://github.com/cta-wave/Test-Content/.
    * NB: when the JSON format needs to be updated, open an issue at https://github.com/cta-wave/dpctf-deploy/issues/.
* Validate that the content conforms to:
  * Its own constraints and flags. [Script](https://github.com/nicholas-fr/test-content-validation/).
  * CMAF: use the [DASH-IF hosted conformance tool](https://conformance.dashif.org/).
  * CTA WAVE Test content format **needs to be extended to format validation**
 
## Downloading mezzanine

Sample script for mezzanine v4:
```
mkdir -p releases/4
cd releases/4
curl http://dash.akamaized.net/WAVE/Mezzanine/releases/4/| sed -n 's/^<IMG SRC=\"\/icons\/generic.gif\" ALT=\"\[FILE\]\"> <A HREF=\"\(.*\)\".*$/\1/p' | grep -v croatia_M1 | grep -v croatia_N1 | grep -v croatia_O1 | xargs -I % wget http://dash.akamaized.net/WAVE/Mezzanine/releases/4/%
cd ..
```

## Encoding to test content
 
* Content and encoding options are documented here for AVC:
  * https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/edit#gid=0
  * https://github.com/cta-wave/Test-Content-Generation/issues/13
  * https://github.com/cta-wave/Test-Content-Generation/wiki/CFHD-Test-Streams
  
## How to generate the content

### Main content (clear and encrypted)

* Modify ```run-all.py``` to:
  * Modify the [executable locations, input and output files location, codec media profile, framerate family](run-all.py) to match your own.
  * Make sure the DRM.xml file is accessible from the output folder.
  * Inspect the input list ([default](switching_sets_single_track.csv)).
* Run ```./run-all.py``` (with optionally your custom csv file as an argument), and grab a cup of tea (or coffee).

### Switching Set X1 (ss1)

The generation of current [Switching Set X1 (ss1)](https://github.com/cta-wave/Test-Content-Generation/issues/60) is done by executing ```ss1/gen.sh```

### Splicing tests

The generation of current [splicing tests](https://github.com/cta-wave/Test-Content/issues/19) is done by executing ```splice/gen.sh ```.

### Chunked tests

The generation of current [chunked tests](https://github.com/cta-wave/Test-Content/issues/41) is done by executing ```chunked/gen.sh ```.

### Audio content (XPERI/DTS)

Comment/uncomment the ```inputs``` array entries in ```run-all.py```. Then ```./run-all.py dtsc.csv``` to generate the ```dtsc``` content.

## Validation

Validation as of today is done manually. (NOTE: an improved more automated process may be available later). 

The process of validation includes:

- The validation should include initial phase checking that required parameters according to the test content description are applied:
  - Media: https://github.com/nicholas-fr/test-content-validation
  - CMAF and manifests: TODO
- An API call to the [DASH-IF conformance validator](http://conformance.dashif.org) should be done to check against MPD and CMAF conformance for CTA WAVE test content.
- The content should be amended with a conformance check output document. At this stage it is recommended to use the output for the DASH-IF conformance validator.
