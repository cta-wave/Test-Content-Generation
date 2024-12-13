import argparse
from pathlib import Path
from wavetcgen.models import TestContent, Mezzanine, FPS_FAMILY
from wavetcgen.database import locate_source_content
from wavetcgen.transfer import md5_checksum

import logging
logging.basicConfig(level=logging.NOTSET)
logger = logging.getLogger("tc-mezzanine")


def check(tc, fps_family):
    m = locate_source_content(tc, fps_family)
    md5 = md5_checksum(Mezzanine.root_dir / m.filename)
    assert m.md5 == md5, f'md5 mismatch "{m.filename}" - expected "{m.md5}" - got "{md5}"'
    logger.info(f'OK - {md5} - {m.filename}')


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
         description="""Given the a sparse matrix csv file,\
                            iterate test vectors and check if the\
                            mezzanine file in source_dir has a matching md5 checksum.
                        """
    )
    parser.add_argument('source_dir')
    parser.add_argument('matrix')
    parser.add_argument('-p', '--profile')
    args = parser.parse_args()

    Mezzanine.root_dir = Path(args.source_dir)

    for tc in TestContent.iter_vectors_in_matrix(args.matrix):
        if args.profile != None and tc.cmaf_media_profile != args.profile:
                continue
        for fps_family in FPS_FAMILY.all():
            try:
                check(tc, fps_family)
            except BaseException as e:
                logger.error(e)
