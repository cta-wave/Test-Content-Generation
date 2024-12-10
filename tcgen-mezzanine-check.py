import argparse
from pathlib import Path

from wavetcgen.models import TestContent, Mezzanine, FPS_SUITE
from wavetcgen.database import locate_source_content
from wavetcgen.transfer import md5_checksum

import logging
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger("tc-mezzanine")

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('source_dir')
    parser.add_argument('-m', '--matrix')
    parser.add_argument('-p', '--profile')
    args = parser.parse_args()

    Mezzanine.root_dir = Path(args.source_dir)

    framerates = [
        FPS_SUITE._12_25_50.value,
        FPS_SUITE._14_29_59.value,
        FPS_SUITE._15_30_60.value
    ]

    for tc in TestContent.iter_vectors_in_matrix(args.matrix):
        if args.profile != None and tc.cmaf_media_profile != args.profile:
                continue
        for fps_suite in framerates:
            try:
                m = locate_source_content(tc, fps_suite)
                md5 = md5_checksum(Mezzanine.root_dir / m.filename)
                assert m.md5 == md5, f'md5 mismatch "{m.filename}" - expected "{m.md5}" - got "{md5}"'
                logger.info(f'OK - {md5} - {m.filename}')
            except BaseException as e:
                logger.error(e)
