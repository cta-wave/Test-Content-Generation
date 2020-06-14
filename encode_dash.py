import sys, os, getopt
from enum import Enum
import subprocess
from subprocess import PIPE
from datetime import datetime


class VideoCodecOptions(Enum):
    AVC = "h264"
    HEVC = "h265"


class AudioCodecOptions(Enum):
    AAC = "aac"


class AVCSD:
    m_profile = "high"
    m_level = "31"
    m_color_primary = "1"
    m_resolution_w = "864"
    m_resolution_h = "576"
    m_frame_rate = "60"


class AVCHD:
    m_profile = "high"
    m_level = "40"
    m_color_primary = "1"
    m_resolution_w = "1920"
    m_resolution_h = "1080"
    m_frame_rate = "60"


class AVCHDHF:
    m_profile = "high"
    m_level = "42"
    m_color_primary = "1"
    m_resolution_w = "1920"
    m_resolution_h = "1080"
    m_frame_rate = "60"


class DASH:
    m_segment_duration = "2"
    m_segment_signaling = "template"

    def __init__(self, dash_config=None):
        if dash_config is not None:
            config = dash_config.split(',')
            for i in range(0, len(config)):
                config_opt = config[i].split(":")
                name = config_opt[0]
                value = config_opt[1]

                if name == "d":
                    self.m_segment_duration = value
                elif name == "s":
                    if value != "template" and value != "timeline":
                        print("Segment Signaling can either be Segment Template denoted by \"template or "
                              "SegmentTemplate with Segment Timeline denoted by \"timeline\".")
                        exit(1)
                    else:
                        self.m_segment_signaling = value

    def dash_package_command(self, index_v, index_a):
        dash_command = "-adaptation_sets "
        if index_v > 0 and index_a>0:
            dash_command += "\"id=0,streams=v id=1,streams=a\" "
        elif index_v > 0 and index_a == 0:
            dash_command += "\"id=0,streams=v\" "
        elif index_v == 0 and index_a > 0:
            dash_command += "\"id=0,streams=a\" "
        else:
            print("At least one Represetation must be provided to be DASHed")
            sys.exit(1)

        dash_command += "-format_options \"movflags=cmaf\" " + \
                  "-seg_duration " + self.m_segment_duration + " " + \
                  "-use_template 1 "
        if self.m_segment_signaling is "timeline":
            dash_command += "-use_timeline 1 "
        else:
            dash_command += "-use_timeline 0 "

        dash_command += "-f dash"

        return dash_command


class Representation:
    m_id = None
    m_input = None
    m_media_type = None
    m_codec = None
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
                if value != VideoCodecOptions.AVC.value and value != VideoCodecOptions.HEVC.value and value != AudioCodecOptions.AAC.value:
                    print("Supported codecs are AVC denoted by \"h264\" and HEVC denoted by \"h265\" for video and"
                          "AAC denoted by \"aac\".")
                    sys.exit(1)
                self.m_codec = value
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
            elif name == "color":
                self.m_color_primary = value
            else:
                print("Unknown configuration option for representation: " + name + " , it will be ignored.")

        if self.m_id is None or self.m_input is None or self.m_media_type is None or self.m_codec is None or \
           self.m_bitrate is None or self.m_cmaf_profile is None:
            print("For each representation at least the following 6 parameters must be provided: " +
                  "<representation_id>,<input_file>,<media_type>,<codec>,<bitrate>,<cmaf_profile>")
            sys.exit(1)

    def form_command(self, index):
        input_file_command = "-i " + self.m_input
        command = ""

        if self.m_media_type in ("v", "video"):
            command += "-map " + index + ":v:0" + " " \
                       "-c:v:" + index + " " + self.m_codec + " " + \
                       "-b:v:" + index + " " + self.m_bitrate + "k " + \
                       "-s:v:" + index + " " + self.m_resolution_w + "x" + self.m_resolution_h + " " + \
                       "-r:v:" + index + " " + self.m_frame_rate + " " + \
                       "-profile:v:" + index + " " + self.m_profile + " " + \
                       "-color_primaries:v:" + index + " " + self.m_color_primary + " " + \
                       "-color_trc:v:" + index + " " + self.m_color_primary + " " + \
                       "-colorspace:v:" + index + " " + self.m_color_primary + " "
            if self.m_aspect_ratio_x is not None and self.m_aspect_ratio_y is not None:
                command += "-vf:v:" + index + " " + "\"setsar=" + self.m_aspect_ratio_x + "/" + self.m_aspect_ratio_y + "\" "

            if self.m_codec == VideoCodecOptions.AVC.value:
                command += "-x264-params:v:" + index + " "
            elif self.m_codec == VideoCodecOptions.HEVC.value:
                command += "-x265-params:v:" + index + " "

            command += "level=" + self.m_level + ":" \
                       "no-open-gop=1" + ":" \
                       "min-keyint=" + self.m_frame_rate + ":" \
                       "keyint=" + self.m_frame_rate + ":" \
                       "scenecut=0"

        elif self.m_media_type in ("a", "audio"):
            command += "-map " + index + ":a:0" + " " \
                       "-c:a:" + index + " " + self.m_codec + " " + \
                       "-b:a:" + index + " " + self.m_bitrate + "k"

        return [input_file_command, command]


def generate_log(ffmpeg_path, command):
    now = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    date = now.split(" ")[0]
    time = now.split(" ")[1]

    result = subprocess.run(ffmpeg_path + " -version", shell=True, stdout=PIPE, stderr=PIPE)

    script = ""
    with open('encode.py', 'r') as file:
        script = file.read()

    filename = "CTATestContentGeneration_Log_" + date + "_" + time
    f = open(filename, "w+")

    f.write("CTA Test Content Generation Log (Generated at: " + "'{0}' '{1}'".format(date, time) + ")\n\n\n\n")

    f.write("-----------------------------------\n")
    f.write("FFMPEG Information:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % result.stdout.decode('ascii'))

    f.write("-----------------------------------\n")
    f.write("Command run:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % command)

    f.write("-----------------------------------\n")
    f.write("Encode.py:\n")
    f.write("-----------------------------------\n")
    f.write("%s\n\n\n\n" % script)
    f.close()


def parse_args(args):
    ffmpeg_path = None
    output_file = None
    representations = None
    dashing = None
    for opt, arg in args:
        if opt == '-h':
            print('test.py -i <inputfile> -o <outputfile>')
            sys.exit()
        elif opt in ("-p", "--path"):
            ffmpeg_path = arg
        elif opt in ("-o", "--out"):
            output_file = arg
        elif opt in ("-r", "--reps"):
            representations = arg.split(" ")
        elif opt in ("-d", "--dash"):
            dashing = arg

    return [ffmpeg_path, output_file, representations, dashing]


def assert_configuration(configuration):
    ffmpeg_path = configuration[0]
    output_file = configuration[1]
    representations = configuration[2]
    dashing = configuration[3]

    result = subprocess.run(ffmpeg_path + " -version", shell=True, stdout=PIPE, stderr=PIPE)
    if "ffmpeg version" not in result.stdout.decode('ascii'):
        print("FFMPEG binary is checked in the \"" + ffmpeg_path + "\" path, but not found.")
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


if __name__ == "__main__":
    # Read input and parse
    try:
        arguments, values = getopt.getopt(sys.argv[1:], 'ho:r:d:p', ['out=', 'reps=', 'dash=', 'path='])
    except getopt.GetoptError:
        sys.exit(2)

    configuration = parse_args(arguments)
    assert_configuration(configuration)

    ffmpeg_path = configuration[0]
    output_file = configuration[1]
    representations = configuration[2]
    dash = configuration[3]

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
            print("Media type for a representation denoted by <type> can either be \"v\" or \"video\" fro video media"
                  "or \"a\" or \"audio\" for audio media.")
            exit(1)

    input_command = ""
    encode_command = ""
    for i in range(0,len(options)):
        option_i = options[i]
        input_command += option_i[0] + " "
        encode_command += option_i[1] + " "

    # Prepare the DASH formatting
    dash_options = DASH(dash)
    dash_package_command = dash_options.dash_package_command(index_v, index_a)

    command = ffmpeg_path + " " + \
              input_command + " " + \
              encode_command + " " + \
              dash_package_command + " " + \
              output_file

    subprocess.run(command, shell=True)
    generate_log(ffmpeg_path, command)
