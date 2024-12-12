from .models import Mezzanine, TestContent, FPS_SUITE
import json
from pathlib import Path
from datetime import datetime

SERVER_ACCESS_URL = "https://dash-large-files.akamaized.net/WAVE/vectors/"


def locate_source_content(tc:TestContent, fps_suite:FPS_SUITE):
    m = tc.get_mezzanine(fps_suite)
    if not (Mezzanine.root_dir / m.filename).exists():
        # splice_ test vectors have no duration in the test matrix,
        # try figuring out the duration from source content filename
        if 'splice_' in m.filename and Path(m.filename).stem.endswith('-1'):
            splice_sequence = [*Mezzanine.root_dir.glob(m.filename.replace('-1', '*'))]
            if len(splice_sequence) == 1:
                m.duration = splice_sequence[0].stem.split('_')[-1]
                return m
        raise Exception(f'test content "{tc.test_id}" - mezzanine file not found "{m.filename}"')
    return m

def most_recent_batch(vector_dir:Path):
    return vector_dir / sorted([datetime.strptime(p.stem, '%Y-%m-%d') for p in vector_dir.iterdir() if p.is_dir()])[-1].strftime('%Y-%m-%d')

class Database:

    @staticmethod
    def root_key(tc:TestContent):
        if 'splice' in tc.test_id:
            return f'{tc.cmaf_media_profile.value.upper()}_SPLICING'
        elif tc.encryption:
            return 'CENC'
        else:
            return tc.cmaf_media_profile.value.upper()

    @staticmethod
    def test_id(tc:TestContent):
        if 'splice_main' in tc.test_id:
            return 'splice_main-cenc' if tc.encryption else 'splice_main'
        elif 'splice_ad' in tc.test_id:
            return 'splice_ad-cenc' if tc.encryption else 'splice_ad'
        else:
            return f't{tc.test_id.replace('_cenc', '-cenc')}' if tc.encryption else f't{tc.test_id}'

    @staticmethod
    def test_entry_key(fps:FPS_SUITE, t:TestContent, batch_dir:str):
        return f'{t.cmaf_media_profile.value}_sets/{fps.value}/{Database.test_id(t)}/{batch_dir}'

    @staticmethod
    def test_entry_location(fps:FPS_SUITE, t:TestContent, batch_dir:str):
        return Path(f'{t.cmaf_media_profile.value}_sets') / fps.value / Database.test_id(t) / batch_dir

    @staticmethod
    def format_entry(m:Mezzanine, t:TestContent, batch_dir:str):
        public_stream_url = SERVER_ACCESS_URL + Database.test_entry_key(m.fps.family, t, batch_dir)
        test_id = Database.test_id(t)
        return {
            'source': m.source_notice,
            'representations': [t.get_representation(m)],
            'segmentDuration': str(t.get_seg_dur(m)),
            'fragmentType': t.fragment_type,
            'hasSEI': t.picture_timing_sei,
            'hasVUITiming': t.vui_timing,
            'visualSampleEntry': t.sample_entry,
            'mpdPath': f'{public_stream_url}/stream.mpd',
            'zipPath':  f'{public_stream_url}/{test_id}.zip'
        }
    
    def __init__(self, data = {}) -> None:
        self.data = data

    def load(self, filename):
        with open(filename) as fo:
            self.data = json.loads(fo)

    def save(self, filename):
        with open(filename, 'w') as fo:
            json.dumps(self.data, fo)

    def add_entry(self, t:TestContent, m:Mezzanine, batch_dir:str):
        root_key = Database.root_key(t)
        if root_key not in self.data:
            self.data[root_key] = {}
        test_entry_key, test_entry = self.format_entry(m, t, batch_dir)
        self.data[root_key][test_entry_key] = test_entry
    
    def find(self, tc:TestContent):
        result = {}
        for test_entry_key, test_entry in self.data[Database.root_key(tc)].items():
            if not test_entry_key.startswith(f'{tc.cmaf_media_profile.value}_sets'):
                continue
            if test_entry_key.split('/')[2] == Database.test_id(tc):
                assert test_entry_key not in result, 'duplicate "test_id" detected'
                result[test_entry_key] = test_entry
        return result

    def iter_entries(self, profile=None):
        for _, data in self.data.items():
            for test_entry_key, test_entry in data.items():
                if profile and not test_entry_key.startswith(profile):
                    continue
                yield test_entry_key, test_entry