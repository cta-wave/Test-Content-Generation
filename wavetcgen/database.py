from .models import Mezzanine, TestContent, FPS_SUITE
import json
from pathlib import Path

# SERVER_ACCESS_URL = "https://dash.akamaized.net/WAVE/vectors/"
SERVER_ACCESS_URL = "https://dash-large-files.akamaized.net/"


def locate_source_content(tc:TestContent, fps_suite:FPS_SUITE):
    m = tc.get_mezzanine(fps_suite)
r    if not (Mezzanine.root_dir / m.filename).exists():
        # splice_ test vectors have no duration in the test matrix,
        # try figuring out the duration from source content filename
        if 'splice_' in m.filename and Path(m.filename).stem.endswith('-1'):
            splice_sequence = [*Mezzanine.root_dir.glob(m.filename.replace('-1', '*'))]
            if len(splice_sequence) == 1:
                m.duration = splice_sequence[0].stem.split('_')[-1]
                return m
        raise Exception(f'test content "{tc.test_id}" - mezzanine file not found "{m.filename}"')
    return m


class Database:
    def __init__(self, data = {}) -> None:
        self.data = data

    @classmethod
    def load(cls, filename):
        with open(filename) as fo:
            return json.loads(fo)

    def save(self, filename):
        with open(filename, 'w') as fo:
            return json.dumps(self.data, fo)
    
    """
    @staticmethod
    def format_entry(m:Mezzanine, o:OutputContent, reps, seg_dur, mpdPath, zipPath):
        return {
            'source': m.source_notice,
            'representations': reps,
            'segmentDuration': str(m.seg_dur(2)),
            'fragmentType': o.frag_type,
            'hasSEI': o.pic_timing,
            'hasVUITiming': o.vui_timing,
            'visualSampleEntry': o.sample_entry,
            'mpdPath': mpdPath,
            'zipPath': zipPath
        }
    """ 
    
    def test_content_directory(m, batch_dir, cenc):
        pass

    
    """
    def set_test_vector(self, m:Mezzanine, o:OutputContent, batch_dir:str, cenc=False):
        collection = 'CENC' if cenc else o.wave_profile.upper()
        o.test_content_directory(m, batch_dir, cenc)
        public_stream_url = SERVER_ACCESS_URL + output_test_stream_folder
        self.data[collection][batch_dir] = format_db_entry(
            o,
            source_notice,
            reps,
            str(seg_dur),
            f'{public_stream_url}/stream.mpd',
            f'{public_stream_url}/{o.stream_id}.zip'
        )
    """