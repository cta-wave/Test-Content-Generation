# Test-Content-Generation

## Overview

This repository provides the information and scripts to generate the CTA Wave Test Content.

The ```run-all.py``` script gathers the data and content from input tables/parameters. Then it sends them for processing. Then it uploads the result.

The ```encode_dash.py``` script is primarily about the usage of [GPAC](http://gpac.io) leveraging libavcodec with x264 and x265 to generate the CMAF content with some DASH annotations.
The intent is to keep the size of the post-processing as small as possible.

## Workflow

* Download mezzanine content from https://dash.akamaized.net/WAVE/Mezzanine/. To be done manually.
* Encode mezzanine content:
  * Encode to conform to CTA Proposed Test content.
  * Encode at least one option of source content according to media profile.
* Package (markup) the content with an MPD according to the CTA Content Model format.
  * NB: done manually right now, but could eventually an extension to [GPAC](http://gpac.io) to produce this.
* Encrypt the content in-place using [GPAC](http://gpac.io) encryption and manifest-forwarding capabilities.
* Upload the proposed test content to the CTA-WAVE server using SFTP.
* Update the Webpage: update ```database.json``` at https://github.com/cta-wave/Test-Content/blob/master/database.json.
  * NB: the Web page code is at https://github.com/cta-wave/Test-Content/.
  * NB: when the JSON format needs to be updated, open an issue at https://github.com/cta-wave/dpctf-deploy/issues/.
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
  * Modify the [executable locations, input and output files location, codec media profile, framerate family](run-all.py) to match your own.
  * Make sure the DRM.xml file is accessible from the output folder.
  * Inspect the [input list](switching_sets_single_track.csv).
* Run ```./run-all.py```, and grab a cup of tea, or coffee.

## Validation

Validation is done manually. The validation should include a local phase checking that specific parameters are applied. Then another API call to the DASH-IF conformance validator could be done.

