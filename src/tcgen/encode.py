import sys
import subprocess
import xml.dom.minidom
from pathlib import Path

from tcgen.models import TestContent, Mezzanine, CmafStructuralBrand, CmafBrand, PROFILES_TYPE, HlgSignaling
from tcgen.run_encode import HR_SPLIT_LOG

GPAC_EXECUTABLE = "/usr/local/bin/gpac"
TCGEN_RUN_ENCODE = Path(__file__).parent / 'run_encode.py'
    
def encode_stream(m:Mezzanine, tc:TestContent, test_stream_dir:Path, dry_run=False):
    """
    Encode, package, and manifest generation (DASH-only)
    """
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
    # TODO: this needs to be integrated as a tcgen function instead of being called as an external script. 
    # the extra parameter to arguments conversion is error prone and makes debugging difficult. 
    encode_dash_cmd = f"python3 {TCGEN_RUN_ENCODE} --path={GPAC_EXECUTABLE} --out=stream.mpd --outdir={test_stream_dir}"
    encode_dash_cmd += f" --dash=sd:{seg_dur},fd:{seg_dur},ft:{tc.fragment_type.value},fr:{m.fps.numerator}/{m.fps.denominator},cmaf:{tc.cmaf_structural_brand.value}"
    encode_dash_cmd += f" --copyright=\'{m.copyright_notice}\' --source=\'{m.source_notice}\' --title=\'{title}\' --profile={tc.cmaf_media_profile.value}"
    encode_dash_cmd += f" {reps_command}"
    print(f'\nprocessing: {test_stream_dir}')
    if dry_run:
        encode_dash_cmd += " --dry-run"
        subprocess.run(encode_dash_cmd, shell=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT).check_returncode()
    else:
        logfile = Path(test_stream_dir) / 'log.txt'
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with open(logfile, 'w') as fo:
            subprocess.run(encode_dash_cmd, shell=True, stdout=fo, stderr=subprocess.STDOUT).check_returncode()
    return test_stream_dir / 'stream.mpd'


def encrypt_stream_cenc(test_stream_cenc_dir:Path, test_stream_dir:Path, drm_config:Path, dry_run=False):
    stream_mpd = test_stream_dir / 'stream.mpd'
    stream_cenc_mpd = test_stream_cenc_dir / 'stream.mpd'
    assert Path(drm_config).exists(), f'DRM config file not found: {drm_config}'
    cenc_cmd = f'{GPAC_EXECUTABLE} -strict-error -i {stream_mpd}:forward=mani cecrypt:cfile={drm_config} @ -o {stream_cenc_mpd}:pssh=mv'
    print(f'\nprocessing: {test_stream_cenc_dir}')
    if dry_run:
        print(cenc_cmd + '\n')
    else:
        logfile = Path(test_stream_cenc_dir) / 'log.txt'
        logfile.parent.mkdir(parents=True, exist_ok=True)
        with open(logfile, 'w') as fo:
            fo.write(HR_SPLIT_LOG)
            fo.write(cenc_cmd + '\n\n')
            fo.write(HR_SPLIT_LOG)
            fo.flush()
            subprocess.run(cenc_cmd, shell=True, stdout=fo, stderr=subprocess.STDOUT).check_returncode()
    return stream_cenc_mpd



def patch_mpd(output_file, m:Mezzanine, tc:TestContent):
    """
    Modify the generated content to comply with CTA Content Model
    """
    return ContentModel.patch_mpd(output_file, m, tc)

def title_notice(m:Mezzanine, tc:TestContent):
    media_type, _, _ = PROFILES_TYPE[tc.cmaf_media_profile]
    n = f"{tc.cmaf_media_profile.value}, Test Vector {tc.test_id}"
    if media_type == "video":
        n = f"{m.content.rstrip('_').capitalize()}, {tc.resolution}, {m.fps.to_number()}fps, " + n
    return n

class ContentModel:

    @classmethod
    def patch_mpd(cls, output_file, m:Mezzanine, tc:TestContent):
        cm = ContentModel(output_file, tc.cmaf_structural_brand.value, tc.cmaf_media_profile)
        cm.process(m.copyright_notice, m.source_notice, title_notice(m, tc))
    
    def __init__(self, filename, structural_brand:CmafStructuralBrand, wave_media_profile:CmafBrand):
        self.m_filename = filename
        self.m_structural_brand = structural_brand
        self.m_wave_media_profile = wave_media_profile

    def process(self, copyright_notice, source_notice, title_notice):
        DOMTree = xml.dom.minidom.parse(str(self.m_filename))
        mpd = DOMTree.documentElement
        self.process_mpd(DOMTree, mpd, copyright_notice, source_notice, title_notice)
        with open(self.m_filename, 'w') as f:
            prettyOutput = '\n'.join([line for line in DOMTree.toprettyxml(indent=' '*2).split('\n') if line.strip()])
            f.write(prettyOutput)

    def process_mpd(self, DOMTree, mpd, copyright_notice, source_notice, title_notice):
        profiles = mpd.getAttribute('profiles')
        # TODO: add to the packager command-line
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
                    else adaptation_set.getAttribute('mimeType')
                if 'video' in mime_type:
                    content_type = 'video'
                    adaptation_set.setAttribute('contentType', content_type)
                elif 'audio' in mime_type:
                    content_type = 'audio'
                    adaptation_set.setAttribute('contentType', content_type)

            adaptation_set.setAttribute('containerProfiles', f'{self.m_structural_brand} {self.m_wave_media_profile.value}')

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
