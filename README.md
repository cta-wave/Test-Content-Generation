# Test-Content-Generation

## Overview

This repository provides the information and scripts to generate the CTA Wave Test Content.

The ```run-all.py profiles/csv_file``` script gathers the data and content from input tables/parameters. Then it sends them for processing. Then it uploads the result.

The processing happens mainly in ```encode_dash.py```. This script is primarily about the usage of [GPAC](http://gpac.io) leveraging [libavcodec](https://ffmpeg.org/libavcodec.html) with [x264](http://www.videolan.org/developers/x264.html) and [x265](https://www.x265.org/) to generate the CMAF content along with a DASH manifest. The intent is to keep the size of the post-processing (e.g. manifest manipulation) as small as possible.

## Workflow

* Download mezzanine content from https://dash.akamaized.net/WAVE/Mezzanine/. See section below.
* Launch scripts:
  * Encode mezzanine content:
    * Encode to conform to CTA Proposed Test content.
    * Encode at least one option of source content according to media profile.
    * NB; the codec value "copy" instructs to bypass the encoding. Useful for proprietary codecs such as DTS or Dolby.
  * Package (markup) the content with an MPD according to the CTA Content Model format.
    * NB: done in Python right now, but could eventually an extension to [GPAC](http://gpac.io) to produce this.
  * Encrypt the content in-place using [GPAC](http://gpac.io) encryption and manifest-forwarding capabilities.
  * Generate side streams: switching sets, spliced and chunked content, etc.. See sections below.
  * Upload the proposed test content to the CTA-WAVE server using SFTP.
  * Update the Webpage: update [database.json](https://github.com/cta-wave/Test-Content/blob/master/database.json).
    * NB: updates and merges are [done manually](https://github.com/cta-wave/Test-Content-Generation/issues/45).
    * NB: the Web page code is located at https://github.com/cta-wave/Test-Content/.
    * NB: when the JSON format needs to be updated, open an issue at https://github.com/cta-wave/dpctf-deploy/issues/.
* Validate that the content conforms to:
  * Its own constraints and flags. [Script](https://github.com/nicholas-fr/test-content-validation/).
  * CMAF: use the [DASH-IF hosted conformance tool](https://conformance.dashif.org/).
  * CTA WAVE Test content format **needs to be extended to format validation**.
 
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
  * https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao
  * https://github.com/cta-wave/Test-Content-Generation/issues/13
  * https://github.com/cta-wave/Test-Content-Generation/blob/master/Instructions/cfhd.md

* Content and encoding options are documented here for HEVC (chh1):
  * https://docs.google.com/spreadsheets/d/1Bmgv6-cfbWfgwn7l-z0McUUI1rMjaWEwrN_Q30jaWk4
  * https://github.com/cta-wave/Test-Content/issues/38
  * https://github.com/cta-wave/Test-Content-Generation/blob/master/Instructions/chh1.md

* Content and encoding options are documented here for DTS:
  * https://github.com/cta-wave/Test-Content/issues/26
  
## How to generate the content

### Main content (clear and encrypted)

* Modify ```run-all.py``` to:
  * Modify the [executable locations, input and output files location, codec media profile, framerate family](run-all.py) to match your own.
  * Make sure the DRM.xml file is accessible from the output folder.
  * Inspect the input list e.g. ([default](profiles/avc.csv)).
* Run ```./run-all.py csv_file``` (with optionally your custom csv file as an argument), and grab a cup of tea (or coffee).

### Switching Sets (ss1, ss2, etc.)

The generation of current [Switching Sets (ss1 for avc, ss2 for hevc/chh1)](https://github.com/cta-wave/Test-Content-Generation/issues/60) is done by executing ```switching_sets/gen_ss1.sh``` and ```switching_sets/gen_ss2.sh```.

### Splicing tests

The generation of current [splicing tests](https://github.com/cta-wave/Test-Content/issues/19) is done by executing ```splice/gen_avc.sh``` and ```splice/gen_hevc_chh1.sh```.

### Chunked tests

The generation of current [chunked tests](https://github.com/cta-wave/Test-Content/issues/41) is done by executing ```chunked/gen.sh cfhd t16``` and ```chunked/gen.sh chh1 t2```.

### Audio content (XPERI/DTS)

Comment/uncomment the ```inputs``` array entries in ```run-all.py```. Then ```./run-all.py profiles/dtsc.csv``` to generate the ```dtsc``` content.

## Validation

Validation as of today is done manually. 

The process of validation includes:

- A initial phase checking that required parameters according to the test content description are applied:
  - Media: https://github.com/nicholas-fr/test-content-validation
  - CMAF and manifests: TODO
- An API call to the [DASH-IF conformance validator](http://conformance.dashif.org) is [done](https://github.com/nicholas-fr/test-content-validation) to check against MPD and CMAF conformance for CTA WAVE test content. Some conformance [reported issues](https://github.com/cta-wave/Test-Content-Generation/issues/55) remain.
- The content should be amended with a conformance check output document: [TODO](https://github.com/cta-wave/Test-Content/issues/49).

---
### Audio content (AAC / AC-4 / E-AC-3)

The workflow to generate AAC / AC-4 / E-AC-3 audio content is essentially as described [here](https://github.com/cta-wave/Test-Content-Generation?tab=readme-ov-file#workflow):
1.	Download mezzanine content.
2.	Encode to test content.
3.	Generate DASH segments and manifest.
4.	Patch ISOBMFF.
5.	Patch MPD according to the CTA Content Model format.
6.	Validate content.
7.	Upload to CTA WAVE server and update the Webpage.

**Note**, steps 1 and 7 are the same as for video content so not repeated.

#### Prerequisites

1.	Mezzanine content.
2.	Encoding tool:
   * For AAC: **ffmpeg WITH libfdk_aac** available here: https://www.gyan.dev/ffmpeg/builds/  
   **Note**, the standard FFmpeg build available doesn't include the AAC library (libfdk). As this library is critical, you will need to build the FFmpeg from the source; instructions are available here: [FFmpeg: compilation_guide](https://trac.ffmpeg.org/wiki/CompilationGuide "compilation guide").
   * For AC-4/E-AC-3: **Dolby Hybrik** tool with AC-4 & E-AC-3 support
3.	Latest version of GPAC available here: https://gpac.io/downloads/gpac-nightly-builds/
 
#### 2. Encoding

Content and encoding options are documented for AAC & AC-4/E-AC-3 in this [Sparse Matrix](https://github.com/cta-wave/Test-Content/issues/58).

* AC-4/E-AC-3: use the **Dolby Hybrik** proprietary tool.

* AAC: use **ffmpeg** with the following command (depending on the required codec):

  a)	AAC-LC:

  `ffmpeg -i {source} -c:a libfdk_aac aac_lc -ar {Sample Rate} -b:a {Bitrate} {channel_config} -t {Duration} -use_editlist {elst_present} {output1}.mp4`

  b)	HE-AAC or HE-AAC-V2:

  `ffmpeg -i {source} -c:a libfdk_aac -profile:a {codec} -ar {Sample Rate} -frag_duration 1963000 -flags2 local_header -latm 1 -header_period 44 -signaling 1 -movflags empty_moov -movflags delay_moov -b:a {Bitrate} {channel_config} -t {Duration} -use_editlist {elst_present} {output1}.mp4`

  c)	Encrypted:

  If the content is to be encrypted, it should be done before generating DASH segments; MP4box (part of gpac) supports encrypting media.
 
#### 3.	Generate DASH segments and manifest

To DASH the content gpac is used with the following command:

`gpac -i {output1}.mp4:FID=A1 -o {output2}.mpd:profile=live:muxtype=mp4:segdur={segmentduration}:cmaf=cmf2:stl:tpl:template="1/$Time$":SID=A1'`

#### 4.	Patching ISOBMFF

This is required to fix metadata stored in some ISOBMFF boxes that make up the DASH segments, or fixing the structure/format. 

An example of what needs to be changed is: `styp` compatibility brands set to `["msdh", "msix", "cmfs", "cmff", "cmf2", "cmfc", "cmf2"]`

#### 5.	Patching MPD to CTA Content Model

The required changes to the MPD are defined in the [CTA WAVE Device Playback Capabilities Specification CTA-5003-A (current version: CTA-5003-A, Published September 2023)](https://cdn.cta.tech/cta/media/media/resources/standards/pdfs/cta-5003-a-final_1.pdf), section “5.3.4.2 Content Model Format for Single Media Profile”.

An example of a change to the MPD is adding the CTA copyright notice.

#### 6.	Validation

Content is validated to ensure conformity with:
* CMAF: using the [DASH-IF validator](https://conformance.dashif.org/)
* Specified content options, and the CTA WAVE Test Content Format: manually using the following tools:
  * ffprobe
  *	MP4box
  *	Mp4dump
  *	MediaInfo  
and by comparing the generated content to the Content and encoding options [Sparse Matrix](https://github.com/cta-wave/Test-Content/issues/58) / [CTA WAVE Content/Device Playback Specifications](https://www.cta.tech/Resources/Standards/WAVE-Project#specs).
