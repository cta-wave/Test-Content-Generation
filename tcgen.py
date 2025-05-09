import argparse
from pathlib import Path
from datetime import datetime
import sys
import subprocess
import re
import logging
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger("tc-gen")

from wavetcgen.models import TestContent, Mezzanine, FPS_FAMILY, PROFILES_TYPE, HlgSignaling, locate_source_content
from wavetcgen.database import Database
from wavetcgen.patch_mpd_info import ContentModel, title_notice


GPAC_EXECUTABLE = "/usr/local/bin/gpac"


def gen_encoder_cmd(m:Mezzanine, tc:TestContent, test_stream_dir:Path, dry_run=False):

    seg_dur = tc.get_seg_dur(m)
    
    # @TODO: remove 'codec_defaults', always infer config from test matrix
    media_type, codec, codec_defaults = PROFILES_TYPE[tc.cmaf_media_profile]
    if codec_defaults is None: 
         codec_defaults = tc.cmaf_media_profile

    reps_command = f"id:{tc.test_id},type:{media_type},codec:{codec},vse:{tc.sample_entry},cmaf:{codec_defaults.value}"
    reps_command += f",fps:{m.fps.numerator}/{m.fps.denominator},res:{tc.resolution},bitrate:{tc.bitrate}"
    reps_command += f",input:'{m.root_dir/m.filename}',pic_timing:{tc.picture_timing_sei},vui_timing:{tc.vui_timing},sd:{str(seg_dur)},bf:{tc.fragment_type.value}"
    if tc.hlg_signaling == HlgSignaling.VUI:
        reps_command += f",hlg:vui"
    if tc.aspect_ratio_idc != 1:
        reps_command += f",sar:{tc.aspect_ratio_idc}" # @TODO: not tested after refactoring
    if m.mastering_display:
        reps_command += f',"hdr_mastering_display:{m.mastering_display.replace(',','~')}"'
    if m.max_cll_fall:
        reps_command += f",max_cll_fall:{m.max_cll_fall.replace(',','~')}"
    # Finalize one-AdaptationSet formatting
    reps_command = "--reps=" + reps_command
    title = title_notice(m, tc)
    # Encode, package, and manifest generation (DASH-only)
    encode_dash_cmd = f"python3 ./wavetcgen/encode_dash.py --path={GPAC_EXECUTABLE} --out=stream.mpd --outdir={test_stream_dir}"
    encode_dash_cmd += f" --dash=sd:{seg_dur},fd:{seg_dur},ft:{tc.fragment_type.value},fr:{m.fps.numerator}/{m.fps.denominator},cmaf:{tc.cmaf_structural_brand.value}"
    encode_dash_cmd += f" --copyright=\'{m.copyright_notice}\' --source=\'{m.source_notice}\' --title=\'{title}\' --profile={tc.cmaf_media_profile.value}"
    encode_dash_cmd += f" {reps_command}"
    if dry_run:
        encode_dash_cmd += " --dry-run"
    sys.stdout.write(f"# Encoding {tc.test_id}:\n")
    sys.stdout.flush()
    if dry_run:
        print(encode_dash_cmd)
    else:
        subprocess.run(encode_dash_cmd, shell=True).check_returncode()
    return test_stream_dir / 'stream.mpd'


def gen_cenc_cmd(test_stream_cenc_dir:Path, test_stream_dir:Path, dry_run=False):
    stream_mpd = test_stream_dir / 'stream.mpd'
    stream_cenc_mpd = test_stream_cenc_dir / 'stream.mpd'
    cfile = Path(sys.path[0]) / 'DRM.xml'
    cenc_cmd = f'{GPAC_EXECUTABLE} -strict-error -i {stream_mpd}:forward=mani cecrypt:cfile={cfile} @ -o {stream_cenc_mpd}:pssh=mv'
    print(f"# Encrypting {tc.test_id}:\n{cenc_cmd}")
    if not dry_run:
        subprocess.run(cenc_cmd, shell=True, stdout=subprocess.STDOUT, stderr=subprocess.STDOUT).check_returncode()
    return stream_cenc_mpd
    

if __name__ == "__main__":

    parser = argparse.ArgumentParser()
    parser.add_argument('source_dir')
    parser.add_argument('output_dir')
    parser.add_argument('-c', '--config', help='test content generation config')
    parser.add_argument('-b', '--batch_dir', default=datetime.today().strftime('%Y-%m-%d'))
    parser.add_argument('-d', '--dry_run', action='store_true', default=False, help='print commands to stdout without processing them')
    # filter out only specific test vectors from matrix
    parser.add_argument('-p', '--profile', help='only test vectors for a specific profile')
    parser.add_argument('-s', '--splice', help='only test vectors needed for "splicing"')
    parser.add_argument('-t', '--test_id', help='only specific test vector')
    # process only a specific fps family, defaults to processing all
    parser.add_argument('-f', '--fps_family', default='ALL', help='one of 14.985_29.97_59.94 - 12.5_25_50 - 15_30_60')
    args = parser.parse_args()

    Mezzanine.root_dir = Path(args.source_dir)
    framerates = FPS_FAMILY.all()
    if args.fps_family != 'ALL':
        if args.fps_family not in framerates:
            raise Exception(f'Invalid framerate family {args.fps_family}')
        framerates = [FPS_FAMILY.from_string(args.fps_family)]

    # for tc in TestContent.iter_vectors_in_matrix(args.matrix):
    for tc in TestContent.iter_vectors_in_batch_config(args.config):
        if args.profile != None and tc.cmaf_media_profile != args.profile:
                continue
        if args.test_id != None and tc.test_id != args.test_id:
                continue
        
        for fps_family in framerates:
            try:
                m = locate_source_content(tc, fps_family)
                fps_family_dir = Path(args.output_dir) / f"{tc.cmaf_media_profile.value}_sets" / fps_family
                if tc.encryption:
                    test_stream_cenc_dir =  Path(args.output_dir) / Database.test_entry_location(fps_family, tc, args.batch_dir)
                    test_stream_dir =  Path(re.sub(r"[-_]c?enc/", "/", str(test_stream_cenc_dir)))
                    output_mpd = gen_cenc_cmd(test_stream_cenc_dir, test_stream_dir, args.dry_run)
                    if not args.dry_run:
                        ContentModel.patch_mpd(output_mpd, m, tc)
                else:
                    test_stream_dir =  Path(args.output_dir) / Database.test_entry_location(fps_family, tc, args.batch_dir)
                    output_mpd = gen_encoder_cmd(m, tc, test_stream_dir, args.dry_run)
                    if not args.dry_run:
                        ContentModel.patch_mpd(output_mpd, m, tc)

            except BaseException as e:
                logger.error(e)
