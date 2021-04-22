# Test-Content-Generation

## Overview

This repository provides the information and scripts to generate the CTA Wave Test Content.

The ```run-all.py``` script gathers the data and content from input tables/parameters. Then it sends them for processing. Then it uploads the result.
TODO: continue to map input parameters.
TODO: rename uploaded content according to https://github.com/cta-wave/Test-Content-Generation/issues/22
TODO: add a validation phase.

The ```encode_dash.py```script is primarily about the usage of GPAC leveraging libavcodec with x264 and x265 to encode the content.
The intent is to keep the size of the post-processing as small as possible.
TODO: split and rename script as it does several things at once.
TODO: support encryption.

* Download mezzanine content from folder 2)
* Encode mezzanine content (from folder 2)
  * Encode to conform to CTA Proposed Test content.
  * Encode at least one option of source content according to media profile.
* Package (markup) the content with an MPD according to the CTA Content Model format
  * TODO: needs likely to be done manually right now, but could eventually an extension to GPAC to produce this
* Upload the proposed test content to folder <add> from above
* Document the detailed procedures from above
 * **Setup Web page** This documentation will be developed under this github repository. Md to a website.
* Validate that the content conforms to:
  * CMAF
  * CTA WAVE Test content format **needs to be extended to format validation**
  * Uses the proper mezzanine
  * Revise mezzanine test content if needed and repeat tasks 9-13 as needed
* If valid, move content to folder 4) <add>
 
## Encoding to test content
 
* Content options are documented here: https://1drv.ms/w/s!AiNJEPgowJnWgbpZesbLvglzCXVlSg?e=4ZFRyB / https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/edit#gid=0 / https://github.com/cta-wave/Test-Content-Generation/issues/13 / https://github.com/cta-wave/Test-Content-Generation/wiki/CFHD-Test-Streams
  
## How to generate the content

* Download the files from https://1drv.ms/w/s!AiNJEPgowJnWgbpZesbLvglzCXVlSg?e=4ZFRyB, be sure to pick different fingerprints
* Modify run-all.py to:
  * use different resolutions, and bitrate you may find [here](https://developer.apple.com/documentation/http_live_streaming/hls_authoring_specification_for_apple_devices)
  * modify the framerates to match the framerate of your input sample
  * modify the input files to match your owm
  * modify GPAC's path to use your own, you need to use GPAC 1.0.1 or above
* Run ```./run-all.py```, and grab a cup of tea, or coffee
