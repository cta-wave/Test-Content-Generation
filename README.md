# Test-Content-Generation

## Overview

This repository provides the information and scripts to generate the CTA Wave Test Content.

The ```run-all.py``` script gathers the data and content from input tables/parameters. Then it sends them for processing. Then it uploads the result.

The ```encode_dash.py``` script is primarily about the usage of GPAC leveraging libavcodec with x264 and x265 to encode the content.
The intent is to keep the size of the post-processing as small as possible.

## Workflow

* Download mezzanine content from https://dash.akamaized.net/WAVE/Mezzanine/. To be done manually.
* Encode mezzanine content:
  * Encode to conform to CTA Proposed Test content
  * Encode at least one option of source content according to media profile
* Package (markup) the content with an MPD according to the CTA Content Model format
  * NB: done manually right now, but could eventually an extension to GPAC to produce this
* Upload the proposed test content to the CTA-WAVE server using SFTP
 * **Setup Web page** This documentation will be developed under this github repository. Md to a website.
* TODO: Validate that the content conforms to:
  * its own constraints and flags
  * CMAF
  * CTA WAVE Test content format **needs to be extended to format validation**
 
## Encoding to test content
 
* Content and encoding options are documented here:
  * https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/edit#gid=0
  * https://github.com/cta-wave/Test-Content-Generation/issues/13
  * https://github.com/cta-wave/Test-Content-Generation/wiki/CFHD-Test-Streams
  
## How to generate the content

* Modify run-all.py to:
  * modify the [input files, framerates, resolutions, and bitrates)(switching_sets_single_track.csv) to match your own
  * modify GPAC's path to use your own, you need to use GPAC 1.0.1 or above
* Run ```./run-all.py```, and grab a cup of tea, or coffee

## Encrypt the content

This is done manually after generating the clear content:
```
for i in $(find . -type d) ; do /opt/bin/gpac -i $i/stream.mpd:forward=mani cecrypt:cfile=DRM.xml @ -o $i-cenc/stream.mpd:pssh=mv ; done
```

This means you also need to upload manually the [content table](http://dash.akamaized.net/WAVE/index.html) before uploading it.

## Validation

Validation is done manually. The validation should include a local phase checking that specific parameters are applied. Then another API call to the DASH-IF conformance validator could be done.

