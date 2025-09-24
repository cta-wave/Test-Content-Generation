# Audio content 

## XPERI/DTS

1.	Download mezzanine content.
2.	Encode to test content using the `profiles/dtsc.csv` file 


## AAC / AC-4 / E-AC-3

The workflow to generate AAC / AC-4 / E-AC-3 audio content is essentially as described [here](https://github.com/cta-wave/Test-Content-Generation?tab=readme-ov-file#workflow):
1.	Download mezzanine content.
2.	Encode to test content.
3.	Generate DASH segments and manifest.
4.	Patch ISOBMFF.
5.	Patch MPD according to the CTA Content Model format.
6.	Validate content.
7.	Upload to CTA WAVE server and update the Webpage.

**Note**, steps 1 and 7 are the same as for video content so not repeated.

## Prerequisites

1.	Mezzanine content.

2.	Encoding tool:

  a) For **AC-4/E-AC-3**: **Dolby Hybrik** tool with AC-4 & E-AC-3 support available here: https://davp.dolby.hybrik.com  
**Note**, you need to upload the Pseudo-Noise mezzanine files here first: http://dolby.ibmaspera.com/; sign in using your IBM ID and the login details for the Hybrik online encoder (provided by Dolby). You may be prompted to download a plugin to support upload/download, if so, install the plugin.

  b) For **AAC**: **ffmpeg WITH libfdk_aac** available here: https://www.gyan.dev/ffmpeg/builds/  
**Note**, the standard FFmpeg build available doesn't include the AAC library (libfdk). As this library is critical, you will need to build the FFmpeg from the source; instructions are available here: [FFmpeg: compilation_guide](https://trac.ffmpeg.org/wiki/CompilationGuide "compilation guide").
 
3.	Latest version of GPAC available here: https://gpac.io/downloads/gpac-nightly-builds/
 
## 2. Encoding

Content and encoding options are documented for AAC & AC-4/E-AC-3 in this [Sparse Matrix](https://github.com/cta-wave/Test-Content/issues/58).

* **AC-4/E-AC-3**: use the **Dolby Hybrik** online encoder tool.

Ensure you have uploaded the Pseudo-Noise mezzanine files as per the pre-requisites. Log in to Hybrik [here](https://davp.dolby.hybrik.com).

a) **AC-4**  
  i.	Select `Jobs – Create`, fill in the form with the following details, then click `Submit job`.
```
Template: Encode.wav to AC-4

Job Name: <to confirm when encoding is complete>
Source: <path to PN.wav file>
Destination Path: <folder in which to put encoded content>
Output file (.mp4): <name of encoded file>

Channel Mode: 2.0
Audio Bitrate: 64
Frame rate: 30
I-Frame interval: 60
Language: eng
2nd CM/AD Language Tage: spa
Loudness Regulation Type: EBU R128
```
  ii.	Go to `Jobs – All jobs` to monitor the job.  

b) **E-AC-3**  
  i.	You need to create a JSON file for each audio track you wish to encode, an example is as follows:

```
{
    "definitions": {
        "job_name": "<insert job name>",
        "source_file": "<insert source file path>/PN01.wav",
        "destination_path": "<insert destination path>",
        "destination_file": "<insert output filename>"
    },
    "name": "{{job_name}}",
    "task_tags": [
        "<insert tags>"
    ],
    "payload": {
        "elements": [
            {
                "uid": "source_file_a",
                "kind": "source",
                "payload": {
                    "kind": "asset_url",
                    "payload": {
                        "storage_provider": "s3",
                        "url": "{{source_file}}",
                        "access": {
                            "credentials_key": "<insert key>"
                        }
                    }
                }
            },
            {
                "uid": "transcode_task",
                "kind": "transcode",
                "task": {
                    "retry_method": "fail"
                },
                "payload": {
                    "location": {
                        "storage_provider": "s3",
                        "path": "{{destination_path}}",
                        "access": {
                            "credentials_key": "<insert key>"
                        }
                    },
                    "targets": [
                        {
                            "file_pattern": "{{destination_file}}",
                            "container": {
                                "kind": "mp4"
                            },
                            "audio": [
                                {
                                    "codec": "eac3",
                                    "channels": 2,
                                    "sample_rate": 48000,
                                    "bitrate_kb": 128,
                                    "language": "eng"
                                }
                            ]
                        }
                    ]
                }
            }
        ],
        "connections": [
            {
                "from": [
                    {
                        "element": "source_file_a"
                    }
                ],
                "to": {
                    "success": [
                        {
                            "element": "transcode_task"
                        }
                    ]
                }
            }
        ]
    }
}
```

ii.	Go to `Jobs – All jobs`, then click `Submit Job JSON` to upload file. Any errors with the JSON file will be given at upload.
 
3. Download content
i.	File are downloaded from: http://dolby.ibmaspera.com/ (note, there may be a slight delay in the file appearing).
ii.	Right click a file and select `Download to`.

b) **AAC**: use **ffmpeg** with the following command (depending on the required codec):

  a)	**AAC-LC**:

  `ffmpeg -i {source} -c:a libfdk_aac aac_lc -ar {Sample Rate} -b:a {Bitrate} {channel_config} -t {Duration} -use_editlist {elst_present} {output1}.mp4`

  b)	**HE-AAC** or **HE-AAC-V2**:

  `ffmpeg -i {source} -c:a libfdk_aac -profile:a {codec} -ar {Sample Rate} -frag_duration 1963000 -flags2 local_header -latm 1 -header_period 44 -signaling 1 -movflags empty_moov -movflags delay_moov -b:a {Bitrate} {channel_config} -t {Duration} -use_editlist {elst_present} {output1}.mp4`

  c)	**Encrypted**:

  If the content is to be encrypted, it should be done before generating DASH segments; MP4box (part of gpac) supports encrypting media.
 
## 3.	Generate DASH segments and manifest

To DASH the content gpac is used with the following command:

`gpac -i {output1}.mp4:FID=A1 -o {output2}.mpd:profile=live:muxtype=mp4:segdur={segmentduration}:cmaf=cmf2:stl:tpl:template="1/$Time$":SID=A1'`

## 4.	Patching ISOBMFF

This is required to fix metadata stored in some ISOBMFF boxes that make up the DASH segments, or fixing the structure/format. 

An example of what needs to be changed is: `styp` compatibility brands set to `["msdh", "msix", "cmfs", "cmff", "cmf2", "cmfc", "cmf2"]`

## 5.	Patching MPD to CTA Content Model

The required changes to the MPD are defined in the [CTA WAVE Device Playback Capabilities Specification CTA-5003-A (current version: CTA-5003-A, Published September 2023)](https://cdn.cta.tech/cta/media/media/resources/standards/pdfs/cta-5003-a-final_1.pdf), section “5.3.4.2 Content Model Format for Single Media Profile”.

An example of a change to the MPD is adding the CTA copyright notice.

## 6.	Validation

Content is validated to ensure conformity with:
* CMAF: using the [DASH-IF validator](https://conformance.dashif.org/)
* Specified content options, and the CTA WAVE Test Content Format: manually using the following tools:
  * ffprobe
  *	MP4box
  *	Mp4dump
  *	MediaInfo  
and by comparing the generated content to the Content and encoding options [Sparse Matrix](https://github.com/cta-wave/Test-Content/issues/58) / [CTA WAVE Content/Device Playback Specifications](https://www.cta.tech/Resources/Standards/WAVE-Project#specs).

# About AAC / AC-4 / E-AC-3 Audio

The initial set of audio test vectors as defined in the [Sparse Matrix](https://github.com/cta-wave/Test-Content/issues/58) were created by Resillion on behalf of [Fraunhofer IIS](https://www.iis.fraunhofer.de/en.html) for AAC, and on behalf of [Dolby](https://www.dolby.com) for AC-4/E-AC-3.
Any future requests for content should be addressed to Dolby or Fraunhofer IIS, respectively.
