#!/usr/bin/env python3
import sys, os, glob, getopt
from pathlib import Path
from enum import Enum
import subprocess
from subprocess import PIPE
from datetime import datetime
import struct
from xml.dom.minidom import parse
import xml.dom.minidom
from fractions import Fraction


# Content Model
# Modify the generated content to comply with CTA Content Model
# TODO: keep this post-processing as minimal as possible (e.g. move in tooling)
class Mode(Enum):
    FRAGMENTED = 1
    CHUNKED = 2

class ContentModel:
    m_filename = ""
    m_wave_media_profile = ""
    m_mode = Mode.FRAGMENTED.value

    def __init__(self, filename, wave_media_profile, mode=None):
        self.m_filename = filename
        self.m_wave_media_profile = wave_media_profile
        if mode is not None:
            self.m_mode = mode

    def process(self, copyright_notice, source_notice, title_notice):
        DOMTree = xml.dom.minidom.parse(self.m_filename)
        mpd = DOMTree.documentElement
        self.process_mpd(DOMTree, mpd, copyright_notice, source_notice, title_notice)
        with open(self.m_filename, 'w') as f:
            prettyOutput = '\n'.join([line for line in DOMTree.toprettyxml(indent=' '*2).split('\n') if line.strip()])
            f.write(prettyOutput)

    def process_mpd(self, DOMTree, mpd, copyright_notice, source_notice, title_notice):
        # @profiles
        profiles = mpd.getAttribute('profiles')
        # TODO: could be added from the packager command-line
        cta_profile1 = "urn:cta:wave:test-content-media-profile:2022"
        if cta_profile1 not in profiles:
            profiles += "," + cta_profile1
        cta_profile2 = "urn:mpeg:dash:profile:cmaf:2019"
        if cta_profile2 not in profiles:
            profiles += "," + cta_profile2
        mpd.setAttribute('profiles', profiles)

        # ProgramInformation
        program_informations = mpd.getElementsByTagName("ProgramInformation")
        self.remove_element(program_informations)
        program_information = DOMTree.createElement("ProgramInformation")
        title = DOMTree.createElement("Title")
        title_txt = DOMTree.createTextNode(title_notice)
        title.appendChild(title_txt)
        source = DOMTree.createElement("Source")
        source_txt = DOMTree.createTextNode(source_notice)
        source.appendChild(source_txt)
        copyright = DOMTree.createElement("Copyright")
        copyright_txt = DOMTree.createTextNode(copyright_notice)
        copyright.appendChild(copyright_txt)
        program_information.appendChild(title)
        program_information.appendChild(source)
        program_information.appendChild(copyright)

        # Period
        period = mpd.getElementsByTagName("Period").item(0)
        mpd.insertBefore(program_information, period)
        self.process_period(DOMTree, mpd, period)

    def process_period(self, DOMTree, mpd, period):
        # Adaptation Set
        self.process_adaptation_sets(period.getElementsByTagName('AdaptationSet'))

    def process_adaptation_sets(self, adaptation_sets):
        adaptation_set_index = 0
        representation_index = 0
        for adaptation_set in adaptation_sets:
            id = adaptation_set.getAttribute('id')

            content_type = adaptation_set.getAttribute('contentType')
            if  content_type == "":
                representations = adaptation_set.getElementsByTagName('Representation')
                mime_type = representations.item(0).getAttribute('mimeType') if representations.item(0).getAttribute('mimeType') != '' \
                    else adaptation_set.getAttribte('mimeType')

                if 'video' in mime_type:
                    content_type = 'video'
                    adaptation_set.setAttribute('contentType', content_type)
                elif 'audio' in mime_type:
                    content_type = 'audio'
                    adaptation_set.setAttribute('contentType', content_type)

                adaptation_set.setAttribute('containerProfiles', 'cmf2 ' + self.m_wave_media_profile)

            representations = adaptation_set.getElementsByTagName('Representation')
            for representation in representations:
                self.process_representation(representation, adaptation_set_index, representation_index, id, content_type)
                representation_index += 1

            adaptation_set_index += 1

    def process_representation(self, representation, adaptation_set_index, representation_index, id, content_type):
        rep_id = content_type + id + "/" + str(representation_index)

    def remove_element(self, nodes):
        for node in nodes:
            parent = node.parentNode
            parent.removeChild(node)


# Supported codecs
class VideoCodecOptions(Enum):
    AVC = "h264"
    HEVC = "h265"

class AudioCodecOptions(Enum):
    AAC = "aac"
    COPY = "copy"


# Supported visual sample entries
class VisualSampleEntry(Enum):
    AVC1 = "avc1"
    AVC3 = "avc3"
    AVC1p3 = "avc1+3"
    HVC1 = "hvc1"
    HEV1 = "hev1"


# CMAF Profiles
# AVC: ISO/IEC 23000-19 Annex A.1
class AVCSD:
    m_profile = "high"
    m_level = "31"
    m_color_primary = "1"
    m_resolution_w = "864"
    m_resolution_h = "576"
    m_frame_rate = 60

class AVCHD:
    m_profile = "high"
    m_level = "40"
    m_color_primary = "1"
    m_resolution_w = "1920"
    m_resolution_h = "1080"
    m_frame_rate = 60

class AVCHDHF:
    m_profile = "high"
    m_level = "42"
    m_color_primary = "1"
    m_resolution_w = "1920"
    m_resolution_h = "1080"
    m_frame_rate = 60

# HEVC: ISO/IEC 23000-19 Annex B.5
class HEVCCHHD:
    m_profile = "main"
    m_level = "41"
    m_color_primary = "1"
    m_resolution_w = "1920"
    m_resolution_h = "1080"
    m_frame_rate = 60


# DASHing
class DASH:
    m_segment_duration = "2"
    m_segment_signaling = "timeline"
    m_fragment_type = "duration"
    m_fragment_duration = "2"
    m_num_b_frames = 2 # necessary for p-to-p fragmentation, see https://github.com/cta-wave/Test-Content-Generation/issues/54
    m_frame_rate = None

    def __init__(self, dash_config=None):
        if dash_config is not None:
            config = dash_config.split(',')
            for i in range(0, len(config)):
                config_opt = config[i].split(":")
                name = config_opt[0]
                value = config_opt[1]

                if name == "sd":
                    self.m_segment_duration = value
                elif name == "ss":
                    if value != "template" and value != "timeline":
                        print("Segment Signaling can either be Segment Template denoted by \"template\" or "
                              "SegmentTemplate with Segment Timeline denoted by \"timeline\".")
                        exit(1)
                    else:
                        self.m_segment_signaling = value
                elif name == "ft":
                    if value != "none" and value != "duration" and value != "pframes" and value != "every_frame":
                        print("Fragment Type can be \"none\", \"duration\", \"pframes\" or \"every_frame\".")
                        exit(1)
                    else:
                        self.m_fragment_type = value
                        if value == "every_frame":
                            self.m_num_b_frames = 0 # only P-frames
                elif name == "fd":
                    self.m_fragment_duration = value
                elif name == "fr":
                    self.m_frame_rate = value

    def dash_package_command(self, index_v, index_a, output_file):
        dash_command = "-o " + output_file
        dash_command += ":profile=live" + \
                        ":cmaf=cmf2" + \
                        ":segdur=" + self.m_segment_duration + \
                        ":tpl" # segment template

        # Segment naming
        # Note: this requirement may actually create chunk name collision when multiple streams are present
        dash_command += ":template=\$Init=1/init\$\$Segment=1/\$"

        if self.m_segment_signaling == "timeline":
            dash_command += ":stl"

        if self.m_fragment_type == "duration":
            dash_command += ":cdur=" + self.m_fragment_duration
        elif self.m_fragment_type == "pframes":
            frag_dur = (self.m_num_b_frames + 1) / Fraction(self.m_frame_rate)
            dash_command += ":cdur=" + str(frag_dur)
        elif self.m_fragment_type == "every_frame":
            frag_dur = Fraction(Fraction(self.m_frame_rate).denominator, Fraction(self.m_frame_rate).numerator)
            dash_command += ":cdur=" + str(frag_dur)

        dash_command += ":SID="
        if index_a > 0:
            dash_command += "A" + str(index_a - 1) + ","
        for i in range(index_v):
            dash_command += "V" + str(i)
            if i + 1 != index_v:
                dash_command += ","

        if dash_command[-1] == ",":
            dash_command = dash_command[:-1]

        return dash_command


# Encoding
# Encoding is done based on the representation configuration given in
# the command line. The syntax for configuration for each Representation is as follows:
#### rep_config = <config_parameter_1>:<config_parameter_value_1>,<config_parameter_2>:<config_parameter_value_2>,…
# <config_parameter> can be:
#### id: Representation ID
#### type: Media type. Can be “v” or “video” for video media and “a” or “audio” for audio media type
#### input: Input file name. The media type mentioned in “type” will be extracted from this input file for the Representation
#### codec: codec value for the media. Can be “h264”, “h265”, “aac”, or "copy" to disable transcoding.
#### bitrate: encoding bitrate for the media in kbits/s
#### cmaf: cmaf profile that is desired. Supported ones are avcsd, avchd, avchdhf, chh1 (taken from 23000-19 A.1)
#### res: resolution width and resolution height provided as “wxh”
#### fps: framerate
#### sar: aspect ratio provided as “x/y”
#### profile: codec profile (such as high, baseline, main, etc.)
#### level: codec level (such as 32, 40, 42, etc.)
#### color: color primary (1 for bt709, etc.)
#### bframes: duration or pframes (2 B-Frames), every_frame (no B-Frames)
# The first six configuration parameters shall be provided. The rest can be filled according to the specified
# cmaf profile. When optional parameters are present these will override the default values for the specified CMAF profile
class Representation:
    m_id = None
    m_input = None
    m_media_type = None
    m_codec = None
    m_video_sample_entry = None
    m_cmaf_profile = None
    m_bitrate = None
    m_resolution_w = None
    m_resolution_h = None
    m_frame_rate = None
    m_aspect_ratio_x = None
    m_aspect_ratio_y = None
    m_profile = None
    m_level = None
    m_color_primary = None
    m_pic_timing = None
    m_vui_timing = None
    m_segment_duration = None
    m_num_b_frames = None

    def __init__(self, representation_config):
        config = representation_config.split(",")
        for i in range(0, len(config)):
            config_opt = config[i].split(":")
            name = config_opt[0]
            value = config_opt[1]

            if name == "id":
                self.m_id = value
            elif name == "input":
                self.m_input = value
            elif name == "type":
                self.m_media_type = value
            elif name == "codec":
                if value != VideoCodecOptions.AVC.value and value != VideoCodecOptions.HEVC.value \
                   and value != AudioCodecOptions.AAC.value and value != AudioCodecOptions.COPY.value:
                    print("Supported codecs are AVC denoted by \"h264\" and HEVC denoted by \"h265\" for video, and "
                          "AAC denoted by \"aac\" or the special value \"copy\" disables the audio transcoding.")
                    sys.exit(1)
                self.m_codec = value
            elif name == "vse":
                if value != VisualSampleEntry.AVC1.value and value != VisualSampleEntry.AVC3.value and \
                   value != VisualSampleEntry.AVC1p3.value and \
                   value != VisualSampleEntry.HEV1.value and value != VisualSampleEntry.HVC1.value:
                    print("Supported video sample entries for AVC are \"avc1\", \"avc3\", \"avc1+3\" and"
                          " for HEVC \"hev1\" and \"hvc1\".")
                    sys.exit(1)
                else:
                    self.m_video_sample_entry = value
            elif name == "cmaf":
                self.m_cmaf_profile = value
                if value == "avcsd":
                    if self.m_profile is None:
                        self.m_profile = AVCSD.m_profile
                    if self.m_level is None:
                        self.m_level = AVCSD.m_level
                    if self.m_frame_rate is None:
                        self.m_frame_rate = AVCSD.m_frame_rate
                    if self.m_color_primary is None:
                        self.m_color_primary = AVCSD.m_color_primary
                    if self.m_resolution_w is None and self.m_resolution_h is None:
                        self.m_resolution_w = AVCSD.m_resolution_w
                        self.m_resolution_h = AVCSD.m_resolution_h
                elif value == "avchd":
                    if self.m_profile is None:
                        self.m_profile = AVCHD.m_profile
                    if self.m_level is None:
                        self.m_level = AVCHD.m_level
                    if self.m_frame_rate is None:
                        self.m_frame_rate = AVCHD.m_frame_rate
                    if self.m_color_primary is None:
                        self.m_color_primary = AVCHD.m_color_primary
                    if self.m_resolution_w is None and self.m_resolution_h is None:
                        self.m_resolution_w = AVCHD.m_resolution_w
                        self.m_resolution_h = AVCHD.m_resolution_h
                elif value == "avchdhf":
                    if self.m_profile is None:
                        self.m_profile = AVCHDHF.m_profile
                    if self.m_level is None:
                        self.m_level = AVCHDHF.m_level
                    if self.m_frame_rate is None:
                        self.m_frame_rate = AVCHDHF.m_frame_rate
                    if self.m_color_primary is None:
                        self.m_color_primary = AVCHDHF.m_color_primary
                    if self.m_resolution_w is None and self.m_resolution_h is None:
                        self.m_resolution_w = AVCHDHF.m_resolution_w
                        self.m_resolution_h = AVCHDHF.m_resolution_h
                elif value == "chh1":
                    if self.m_profile is None:
                        self.m_profile = HEVCCHHD.m_profile
                    if self.m_level is None:
                        self.m_level = HEVCCHHD.m_level
                    if self.m_frame_rate is None:
                        self.m_frame_rate = HEVCCHHD.m_frame_rate
                    if self.m_color_primary is None:
                        self.m_color_primary = HEVCCHHD.m_color_primary
                    if self.m_resolution_w is None and self.m_resolution_h is None:
                        self.m_resolution_w = HEVCCHHD.m_resolution_w
                        self.m_resolution_h = HEVCCHHD.m_resolution_h
                else:
                    print("Unknown CMAF profile: " + name)
            elif name == "bitrate":
                self.m_bitrate = value
            elif name == "res":
                resolution_w_h = value.split('x')
                self.m_resolution_w = resolution_w_h[0]
                self.m_resolution_h = resolution_w_h[1]
            elif name == "fps":
                self.m_frame_rate = value
            elif name == "sar":
                sar_x_y = value.split(':')
                self.m_aspect_ratio_x = sar_x_y[0]
                self.m_aspect_ratio_y = sar_x_y[1]
            elif name == "profile":
                self.m_profile = value
            elif name == "level":
                self.m_level = value
            elif name == "bf":
                if value == "every_frame":
                    self.m_num_b_frames = 0
                else:
                    self.m_num_b_frames = 2
            elif name == "color":
                self.m_color_primary = value
            elif name == "pic_timing":
                self.m_pic_timing = value
            elif name == "vui_timing":
                self.m_vui_timing = value
            elif name == "sd":
                self.m_segment_duration = value
            else:
                print("Unknown configuration option for representation: " + name + " , it will be ignored.")

        # Sanity checks
        if self.m_id is None or self.m_input is None or self.m_media_type is None or self.m_codec is None or \
            self.m_bitrate is None and self.m_cmaf_profile:
            print("For each representation at least the following 6 parameters must be provided: " +
                "<representation_id>{0},<input_file>{1},<media_type>{2},<codec>{3},<bitrate>{4},<cmaf_profile>{5}"\
                    .format(self.m_id, self.m_input, self.m_media_type, self.m_codec, self.m_bitrate, self.m_cmaf_profile))
            sys.exit(1)

        if Fraction(self.m_frame_rate) < 14:
            print("Low framerate detected: disabling B-Frames.")
            self.m_num_b_frames = 0

    def form_command(self, index):
        input_file_command = "-i \"" + self.m_input + "\""
        input_file_command += ":#StartNumber=-2000000" + ":#Representation=1"

        if self.m_cmaf_profile == "avchd":
            input_file_command +=  ":#IsoBrand=cfhd"
        elif self.m_cmaf_profile == "avchdhf":
            input_file_command +=  ":#IsoBrand=chdf"
        else:
            input_file_command +=  ":#IsoBrand=" + self.m_cmaf_profile
        # other media need to have the brand embedded in the source

        input_file_command +=  ":FID=" + "GEN" + self.m_id

        command = ""
        if self.m_media_type in ("v", "video"):
            # Resize
            command += "ffsws:osize=" + self.m_resolution_w + "x" + self.m_resolution_h
            if self.m_cmaf_profile == "chh1":
                command += ":ofmt=yuv420_10"
            command += ":SID=" + "GEN" + self.m_id

            # Encode
            command += " @ "
            command += "enc:gfloc"
            command += ":c=" + self.m_codec
            command += ":b=" + self.m_bitrate + "k"
            command += ":bf=" + str(self.m_num_b_frames)
            if self.m_num_b_frames != 0:
                 command += ":b_strategy=0"
            command += ":fintra=" + self.m_segment_duration
            if self.m_cmaf_profile == "chh1":
                command += ":profile=" + self.m_profile + "10"
            else:
                command += ":gop=" + str(Fraction(self.m_segment_duration) * Fraction(self.m_frame_rate))
                command += ":profile=" + self.m_profile
            command += ":color_primaries=" + self.m_color_primary
            command += ":color_trc=" + self.m_color_primary
            command += ":colorspace=" + self.m_color_primary

            if self.m_codec == VideoCodecOptions.AVC.value:
                command += "::x264-params=\""
            elif self.m_codec == VideoCodecOptions.HEVC.value:
                command += "::x265-params=\""

            command += "level=" + self.m_level + ":" \
                       "no-open-gop=1" + ":" \
                       "scenecut=0"

            if self.m_pic_timing == "True":
                command +=  ":" \
                       "nal-hrd=vbr" + ":" \
                       "vbv-bufsize=" + str(int(self.m_bitrate) * 3) + ":" \
                       "vbv-maxrate=" + str(int(int(self.m_bitrate) * 3 / 2))

            command += "\":" #closing codec-specific parameters

            if self.m_vui_timing == "False":
                command += " @ bsrw:novuitiming"

            if self.m_aspect_ratio_x is not None and self.m_aspect_ratio_y is not None:
                command += " @ bsrw:setsar=" + self.m_aspect_ratio_x + "/" + self.m_aspect_ratio_y + ""

            command += ":FID=V" + index

        elif self.m_media_type in ("a", "audio"):
            if self.m_codec != "copy":
                command += "enc:gfloc" + \
                        ":c=" + self.m_codec + \
                        ":b=" + "128" + "k" #FIXME: self.m_bitrate

                command += ":SID=" + "GEN" + self.m_id
                command += ":FID=A" + index
            else:
                input_file_command += ":FID=A" + index

        #TODO: move: this is a video-only muxing option, not an encoding option. Setting as global.
        if self.m_video_sample_entry is not None:
            if self.m_video_sample_entry == "avc1" or self.m_video_sample_entry == "hvc1": #Romain: call them inband, outband, both
                command += " --bs_switch=off"
            elif self.m_video_sample_entry == "avc3" or self.m_video_sample_entry == "hev1":
                command += " --bs_switch=inband"
            elif self.m_video_sample_entry == "avc1+3" or self.m_video_sample_entry == "hevc1+3":
                command += " --bs_switch=both"
            else:
                print("Supported video sample entries are \"avc1\", \"avc3\", and \"avc1+3\".")
                sys.exit(1)

        return [input_file_command, command]

# Collect logs regarding the generated content. The collected logs are as follows:
#### Content generation date and time,
#### Tool version and executed commands,
#### this python script (encode_dash.py)
def generate_log(gpac_path, command):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date = now.split(" ")[0]
    time = now.split(" ")[1]

    result = subprocess.run(gpac_path + " -version", shell=True, stdout=PIPE, stderr=PIPE)

    script = ""
    with open('encode_dash.py', mode='r', encoding='utf-8') as file:
        script = file.read()

    filename = "CTATestContentGeneration_Log_" + date + "_" + time.replace(':','-') + ".txt"
    f = open(filename, "w+")

    f.write("CTA Test Content Generation Log (Generated at: " + "'{0}' '{1}'".format(date, time) + ")\n\n\n\n")

    f.write("-----------------------------------\n")
    f.write("GPAC Information:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % result.stderr.decode('ascii'))

    f.write("-----------------------------------\n")
    f.write("Command run:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % command)

    f.write("-----------------------------------\n")
    f.write("encode_dash.py:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % script)
    f.close()


# Parse input arguments
# Output MPD: --out="<desired_mpd_name>"
# GPAC binary path: -–path="path/to/gpac"
# Representation configuration: --reps="<rep1_config rep2_config … repN_config>"
# DASHing configuration: --dash="<dash_config>"
def parse_args(args):
    gpac_path = None
    output_file = None
    representations = None
    dashing = None
    outDir = None
    copyright_notice = None
    source_notice = None
    bframes = None
    wave_media_profile = None
    for opt, arg in args:
        if opt == '-h':
            print('test.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-p", "--path"):
            gpac_path = arg
        elif opt in ("-o", "--out"):
            output_file = arg
        elif opt in ("-r", "--reps"):
            representations = arg.split("|")
        elif opt in ("-d", "--dash"):
            dashing = arg
        elif opt in ("-od", "--outdir"):
            outDir = arg
        elif opt in ("-c", "--copyright"):
            copyright_notice = arg
        elif opt in ("-s", "--source"):
            source_notice = arg
        elif opt in ("-t", "--title"):
            title_notice = arg
        elif opt in ("-pf", "--profile"):
            wave_media_profile = arg

    print(representations)
    return [gpac_path, output_file, representations, dashing, outDir, copyright_notice, source_notice, title_notice, wave_media_profile]


# Check if the input arguments are correctly given
def assert_configuration(configuration):
    gpac_path = configuration[0]
    output_file = configuration[1]
    representations = configuration[2]
    dashing = configuration[3]
    out_dir = configuration[4]
    result = subprocess.run(gpac_path + " -version", shell=True, stdout=PIPE, stderr=PIPE)
    if "gpac - GPAC command line filter engine - version" not in result.stderr.decode('ascii'):
        print("gpac binary is checked in the \"" + gpac_path + "\" path, but not found.")
        sys.exit(1)

    if output_file is None:
        print("Output file name must be provided")
        sys.exit(1)

    if representations is None:
        print("Representations description must be provided.")
        sys.exit(1)

    if dashing is None:
        print("Warning: DASHing information is not provided, as a default setting, segment duration of 2 seconds and "
              "segment signaling of SegmentTemplate will be used.")

    if out_dir is None:
        print("Warning: Output directory wasn't specified, it will output everything into cwd")


if __name__ == "__main__":
    # Read input, parse and assert
    try:
        arguments, values = getopt.getopt(sys.argv[1:], 'ho:r:d:p:od:c:s:t:pf', ['out=', 'reps=', 'dash=', 'path=', 'outdir=', 'copyright=', 'source=', 'title=', 'profile='])
    except getopt.GetoptError:
        sys.exit(2)
    configuration = parse_args(arguments)
    assert_configuration(configuration)

    gpac_path = configuration[0]
    output_file = configuration[1]
    representations = configuration[2]
    dash = configuration[3]
    out_dir = configuration[4]
    copyright_notice = configuration[5]
    source_notice = configuration[6]
    title_notice = configuration[7]
    wave_media_profile = configuration[8]

    if out_dir is not None:
        output_file = out_dir + "/" + output_file
        Path(out_dir).mkdir(parents=True, exist_ok=True)
        print("Checking that the output directory exists")

    # Prepare the encoding for each Representation
    options = []
    index_v = 0
    index_a = 0
    for representation_config in representations:
        representation = Representation(representation_config)
        if representation.m_media_type in ("v", "video"):
            options.append(representation.form_command(str(index_v)))
            index_v += 1
        elif representation.m_media_type in ("a", "audio"):
            options.append(representation.form_command(str(index_a)))
            index_a += 1
        else:
            print("Media type for a representation denoted by <type> can either be \"v\" or \"video\" for video media"
                  "or \"a\" or \"audio\" for audio media.")
            exit(1)

    input_command = ""
    encode_command = ""
    for i in range(0, len(options)):
        option_i = options[i]
        input_command += option_i[0] + " "
        encode_command += option_i[1] + " "

    # Prepare the DASH formatting
    dash_options = DASH(dash)
    dash_package_command = dash_options.dash_package_command(index_v, index_a, output_file)

    # Run the command
    command = gpac_path + " " + \
              input_command + " " + \
              encode_command + " " + \
              dash_package_command
    print(command)
    subprocess.run(command, shell=True)

    # Content Model
    content_model = ContentModel(output_file, wave_media_profile)
    content_model.process(copyright_notice, source_notice, title_notice)

    # Save the log
    generate_log(gpac_path, command)
