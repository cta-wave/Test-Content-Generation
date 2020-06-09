
import subprocess
from enum import Enum
import sys, os, getopt

class VideoCodecOptions(Enum):
    AVC = "h264"
    HEVC = "h265"


class AudioCodecOptions(Enum):
    AAC = "aac"


class Video:
    m_resolution_w = "1280"
    m_resolution_h = "720"
    m_frame_rate = "50"
    m_aspect_ratio_x = "3"
    m_aspect_ratio_y = "2"
    m_codec = VideoCodecOptions.AVC.value
    m_bitrate = "30000"
    m_profile = "high"
    m_level = "40"
    m_color_primary = "1"

    def __init__(self, resolution=None, fps=None, sar=None, codec=None, bw=None, profile=None, level=None):
        if resolution is not None:
            resolution_w_h = resolution.split('x')
            self.m_resolution_w = resolution_w_h[0]
            self.m_resolution_h = resolution_w_h[1]
        if fps is not None:
            self.m_frame_rate = fps
        if sar is not None:
            sar_x_y = sar.split(':')
            self.m_aspect_ratio_x = sar_x_y[0]
            self.m_aspect_ratio_y = sar_x_y[1]
        if codec is not None:
            if codec is not VideoCodecOptions.AVC.value and codec is not VideoCodecOptions.HEVC.value:
                print("Supported video codecs are AVC denoted by \"h264\" and "
                      "HEVC denoted by \"h265\"")
                exit(1)
            self.m_codec = codec
        if bw is not None:
            self.m_bitrate = bw
        if profile is not None:
            self.m_profile = profile
        if level is not None:
            self.m_level = level

    def encode_video_command(self):
        # Add more than one video rep option
        video_command = "-c:v " + self.m_codec + " " + \
                  "-b:v " + self.m_bitrate + "k " + \
                  "-s:v " + self.m_resolution_w + "x" + self.m_resolution_h + " " + \
                  "-vf \"setsar=" + self.m_aspect_ratio_x + "/" + self.m_aspect_ratio_y + "\" " + \
                  "-r:v " + self.m_frame_rate + " " + \
                  "-profile:v:0 " + self.m_profile + " " + \
                  "-color_primaries " + self.m_color_primary + " " + \
                  "-color_trc " + self.m_color_primary + " " + \
                  "-colorspace 1 " #+ self.m_color_primary + " "

        if self.m_codec is VideoCodecOptions.AVC.value:
            video_command += "-x264-params "
        elif self.m_codec is VideoCodecOptions.HEVC.value:
            video_command += "-x265-params"

        video_command += "no-open-gop=1" + ":"\
                   "min-keyint=" + self.m_frame_rate + ":" \
                   "keyint=" + self.m_frame_rate + ":" \
                   "scenecut=0"

        return video_command


class Audio:
    m_codec = AudioCodecOptions.AAC.value
    m_bitrate = "64"

    def __init__(self, codec=None, bw=None):
        if codec is not None:
            if codec is not AudioCodecOptions.AAC.value:
                print("Supported video codec is AAC denoted by \"aac\"")
                exit(1)
            self.m_codec = codec
        if bw is not None:
            self.m_bitrate = bw

    def encode_audio_command(self):
        # Add more than one audio rep option
        audio_command = "-c:a:0 " + self.m_codec + " " + \
                  "-b:a:0 " + self.m_bitrate

        return audio_command


class DASH:
    m_adaptation_sets = {}
    m_representations = {}
    m_segment_duration = "2"
    m_segment_signaling = "template"

    def __init__(self, as_list=None, rep_list=None, seg_dur=None, seg_sig=None):
        self.m_adaptation_sets = as_list
        self.m_representations = rep_list
        if seg_dur is not None:
            self.m_segment_duration = seg_dur
        if seg_dur is not None:
            if seg_sig is not "template" and seg_sig is not "timeline":
                print("Segment Signaling can either be Segment Template denoted by \"template or "
                      "SegmentTemplate with Segment Timeline denoted by \"timeline\".")
                exit(1)
            else:
                self.m_segment_signaling = seg_sig

    def dash_package_command(self):
        dash_command = "-adaptation_sets \"id=0,streams=v id=1,streams=a\" " + \
                  "-format_options \"movflags=cmaf\" " + \
                  "-seg_duration " + self.m_segment_duration + " " + \
                  "-use_template 1 "
        if self.m_segment_signaling is "timeline":
            dash_command += "-use_timeline 1 "
        else:
            dash_command += "-use_timeline 0 "

        dash_command += "-f dash"

        return dash_command


if __name__ == "__main__":
    # Add the input reading part
    try:
        arguments, values = getopt.getopt(sys.argv[1:], 'hi:o:m:p', ['in=','out=','mode=','path='])
    except getopt.GetoptError:
        sys.exit(2)

    input_file = "tos-30sec-final.mp4"
    output_file = "output.mpd"

    video_options = Video()
    video_encode_command = video_options.encode_video_command()

    audio_options = Audio()
    audio_encode_command = audio_options.encode_audio_command()

    dash_options = DASH()
    dash_package_command = dash_options.dash_package_command()

    command = "/usr/bin/ffmpeg -i " + input_file + " " + \
              video_encode_command + " " + \
              audio_encode_command + " " + \
              dash_package_command + " " + \
              output_file

    print(command)
    subprocess.run(command, shell=True)
