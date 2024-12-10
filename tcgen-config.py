import argparse
from wavetcgen.models import TestContent
import csv

if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument('-m', '--matrix', help='test matrix exported in csv')
    parser.add_argument('-o', '--output', help='output tcgen.py config')
    parser.add_argument('-p', '--profile', help='only test vectors for a specific cmaf media profile')
    args = parser.parse_args()

    fieldnames = None
    rows = []
    for tc in TestContent.iter_vectors_in_matrix(args.matrix):
        if args.profile != None and tc.cmaf_media_profile != args.profile:
                continue
        row = tc.to_batch_config_row()
        if not fieldnames:
            fieldnames = [*row.keys()]
        rows.append(row)

    with open(args.output, 'w') as fo:
        writer = csv.DictWriter(fo, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)