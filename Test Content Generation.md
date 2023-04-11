# Test Content Generation

## Setup
The following setup is proposed for generating the content:

* [python3.6](https://www.python.org/downloads/)
* [xml.dom.minidom](https://docs.python.org/3.6/library/xml.dom.minidom.html)
* [ffmpeg4.2.2](https://ffmpeg.org/) (Note: 4.2.2 is used for the generation of the mezzanine content)

## Code Flow
CTA Test content generation consists of three steps:

1. Encoding
2. DASHing
3. Content Modeling

All the steps are provided in the encode_dash.py script. The process flow is as follows:
* Script is run by providing input parameters:
    * --out: The desired MPD name for to-be-generated MPD after running this script. It is mandatory to be provided in the command line.
    * --path: Path to the ffmpeg executable. It is mandatory to be provided in the command line.
    * --reps: Collection of Representation configurations that is used to encode the input files. Each Representation configuration is separated by space character. At least one Representation configuration is mandatory to be provided in the command line.
    * --dash: DASHing information. It is optional to be provided in the command line.
* Representation class is used to form the encoding portion of the overall ffmpeg command for each representation configuration
    * rep_config = *<*config_parameter_1*>*:*<*config_parameter_value_1*>*,*<*config_parameter_2*>*:*<*config_parameter_value_2*>*,…
    * *<*config_parameter*>* can be:
        * __id:__ Representation ID
        * __type:__ Media type. Can be “v” or “video” for video media and “a” or “audio” for audio media type
        * __input:__ Input file name. The media type mentioned in “type” will be extracted from this input file for the Representation
        * __codec:__ codec value for the media. Can be “h264”, “h265” or “aac”
        * __bitrate:__ encoding bitrate for the media in kbits/s
        * __cmaf:__ cmaf profile that is desired. Supported ones are:
             * AVC/H264: avcsd, avchd, avchdhf (taken from 23000-19 A.1), and
             * HEVC/H265: hhd8 (taken from 23000-19 B.5)
        * vse: visual sample entry. Supported video sample entries for AVC are "avc1" and "avc3" and for HEVC "hev1" and "hvc1"
        * res: resolution width and resolution height provided as “wxh”
        * fps: frame rate
        * sar: aspect ratio provided as “x/y”
        * profile: codec profile (such as high, baseline, main, etc.)
        * level: codec level (such as 32, 40, 42, etc.)
        * color: color primary (1 for bt709, etc.)
    * The boldconfiguration parameters are mandatory to be provided. The rest can be filled according to the specified CMAF profile.  If the rest is also given, these will override the default values for the specified CMAF profile.
* DASH class is used to form the DASHing portion of the overall ffmpeg command for all the representation configurations
    * dash_config=*<*config_parameter_1*>*:*<*config_parameter_value_1*>*,*<*config_parameter_2*>*:*<*config_parameter_value_2*>*
    * *<*config_parameter*>* can be:
        * sd: Segment duration
        * ss: Segment signaling. Can be either “template” for SegmentTemplate or “timeline” for SegmentTimeline
        * ft: Fragment type. Can be either "none", "duration", "pframes" or "every_frame"
        * fd: Fragment duration
    * It is defaulted to segment duration of 2 seconds and segment signaling of SegmentTimeline. If parameters are provided, these override the default settings.
* Content is generated.
    * Using the FFMpeg path, formed encoding and DASHing command portions and the output MPD file name, a single line FFMPEG command is formed and executed.
    * Resulting initialization and media segments as well as the MPD file are output to this projects' directory.
* ContentModel class is used to comply the generated content to with CTA Content Model.
    * The content generated from the above step is used as input in this step.
    * MPD is modified according to the CTA Content Model
    * Initialization and media segment files are renamed and stored properly.
    * It should be noted that only MPD-level changes are performed. The requirements regarding ISO BMFF parsing is not included.
* Log is generated to store the information on the generated content and setup environment.
    * Collected logs include:
        * Content generation date and time,
        * ffmpeg version,
        * ffmpeg command that is run,
        * the python script code (encode_dash.py)
