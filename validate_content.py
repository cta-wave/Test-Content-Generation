import click
import subprocess
import logging
from pathlib import Path
import datetime
import io
import json
import csv

from wavetcgen.models import TestContent, Mezzanine, CmafBrand, FPS_FAMILY, PROFILES_TYPE, HlgSignaling, locate_source_content
from wavetcgen.patch_mpd_info import ContentModel, title_notice
from wavetcgen.database import Database


DEFAULT_BATCH_DIR = datetime.datetime.now().strftime("%Y-%m-%d")
DEFAULT_DRY_RUN = False


def test_duration(tc:TestContent, fps_family:FPS_FAMILY, ffmpeg_bsf_log:io.StringIO):
	lines = ffmpeg_bsf_log.readlines()
	# 'frame= 1500 fps=0.0 q=-1.0 Lsize=N/A time=00:00:29.96 bitrate=N/A speed=47.3x    \n'
	assert lines[-1].startswith('frame= ')
	frames = int(lines[-1].lstrip('frame=').lstrip().split(' ')[0])
	duration = frames / tc.get_fps(fps_family)
	if duration != float(tc.duration):
		return f'{float(duration):3.3f} != {tc.duration}'


def test_hevc_tier(tc:TestContent, ffmpeg_bsf_log:io.StringIO):
	ffmpeg_bsf_log.seek(0)
	for l in ffmpeg_bsf_log:
		# [trace_headers @ 0x12963be00] 50          general_tier_flag          0 = 0
		if 'general_tier_flag' in l:
			if bool(int(l.split("=")[-1].strip())):
				return 'High != Main'
			else:
				return 'ok'
	return 'undefined'


def test_pic_timing_sei(tc:TestContent, ffmpeg_bsf_log:io.StringIO):
	ffmpeg_bsf_log.seek(0)
	for l in ffmpeg_bsf_log:
		if 'Picture Timing' in l:
			return "ok" if tc.picture_timing_sei else "1 != 0"
	return "ok" if not tc.picture_timing_sei else "0 != 1"


def test_vui_timing(tc:TestContent, ffmpeg_bsf_log:io.StringIO):
	ffmpeg_bsf_log.seek(0)
	for l in ffmpeg_bsf_log:
		if "vui_timing_info_present_flag" in l:
			if bool(int(l.split("=")[-1].strip())):
				return "ok" if tc.vui_timing else '1 != 0'
			else:
				return "ok" if not tc.vui_timing else '0 != 1'


def test_bframes(tc:TestContent, ffprobe_output:dict):
	for f in ffprobe_output['frames']:
		if f['pict_type'] == 'B':
			return 1
	return 0


def test_color_vui(tc:TestContent, ffprobe_output:dict):
	s = ffprobe_output['streams'][0]
	try:
		if tc.cmaf_media_profile == CmafBrand.CUD1:
			assert s['color_space'] == 'bt2020nc'
			assert s['color_primaries'] == 'bt2020'
			assert s['color_transfer'] == 'bt2020-10'
		elif tc.cmaf_media_profile == CmafBrand.CLG1:
			assert s['color_space'] == 'bt2020nc'
			assert s['color_primaries'] == 'bt2020'
			if tc.hlg_signaling == HlgSignaling.VUI:
				assert s['color_transfer'] == 'arib-std-b67'
			else: 
				assert s['color_transfer'] == 'bt2020-10'
		elif tc.cmaf_media_profile == CmafBrand.CHD1:
			assert s['color_space'] == 'bt2020nc'
			assert s['color_primaries'] == 'bt2020'
			assert s['color_transfer'] == 'smtpe2084'
		else:
			assert s['color_space'] == 'bt709'
			assert s['color_primaries'] == 'bt709'
			assert s['color_transfer'] == 'bt709'
		return 'ok'
	except BaseException as e:
		return 'error'


def ffmpeg_bsf_inspect(test_stream_mpd:Path, dry_run=False):
	cmd = [
		'ffmpeg',
		'-i', str(test_stream_mpd.resolve()),
		'-c', 'copy',
		'-bsf:v', 'trace_headers',
		'-f', 'null', '-'
		]
	report_fp = test_stream_mpd.with_suffix('.ffmpeg.bsf.log')
	if not dry_run:
		with open(report_fp, "w") as report_fo:
			subprocess.run(cmd, stdout=report_fo, stderr=report_fo)
	return report_fp


def ffprobe_inspect(test_stream_mpd:Path, dry_run=False):
	cmd = [
		"ffprobe", 
		"-read_intervals", "%+1",
		"-v", "quiet",
		"-show_entries",
		"frame=pict_type:stream=color_space,color_transfer,color_primaries",
		"-of", 
		"json",
		str(test_stream_mpd.resolve())
	]
	report_fp = test_stream_mpd.with_suffix('.ffprobe.log')
	if not dry_run:
		with open(report_fp, "w") as report_fo:
			subprocess.run(cmd, stdout=report_fo)
	return report_fp


def validat_test_content(ctx, m, tc, fps_family):
	test_stream_mpd = test_stream_dir(ctx, tc, fps_family) / 'stream.mpd'	
	res = {}
	dry_run = ctx.obj['DRY_RUN']

	ffmpeg_bsf_log_fp = ffmpeg_bsf_inspect(test_stream_mpd, dry_run)
	if ffmpeg_bsf_log_fp.exists():
		with open(ffmpeg_bsf_log_fp, 'r') as ffmpeg_bsf_log_fo:
			res['duration'] = test_duration(tc, fps_family, ffmpeg_bsf_log_fo)
			res['hevc tier'] = test_hevc_tier(tc, ffmpeg_bsf_log_fo)
			res['pic timing sei'] = test_pic_timing_sei(tc, ffmpeg_bsf_log_fo)
			res['timing vui'] = test_vui_timing(tc, ffmpeg_bsf_log_fo)
	else:
		logging.warning(f'Not found: {ffmpeg_bsf_log_fp}')

	ffprobe_log_fp = ffprobe_inspect(test_stream_mpd, dry_run)
	if ffprobe_log_fp.exists():
		with open(ffprobe_log_fp, 'rb') as ffprobe_log_fo:
			ffprobe_output = json.load(ffprobe_log_fo)
			res['color vui'] = test_color_vui(tc, ffprobe_output)
			res['bframes'] = test_bframes(tc, ffprobe_output)
	else:
		logging.warning(f'Not found: {ffprobe_log_fp}')
	return res


def iter_test_vectors_in_config(ctx):
	for tc in TestContent.iter_vectors_in_batch_config(ctx.obj['CONFIG']):
		for fps_family in FPS_FAMILY.all():
			try:
				m = locate_source_content(tc, fps_family)
				yield (m, tc, fps_family)
			except BaseException as e:
				logging.warning(e)


def test_stream_dir(ctx, tc, fps_family):
	return ctx.obj['OUTPUT_DIR'] / Database.test_entry_location(fps_family, tc, ctx.obj['BATCH_DIR'])

@click.group()
@click.argument('config')
@click.option('-o', '--output', default='./vectors/')
@click.option('-s', '--source-dir', default='../mezzanine/5')
@click.option('-b', '--batch-dir', default=DEFAULT_BATCH_DIR)
@click.option('--dry-run/--run', default=DEFAULT_DRY_RUN)
@click.pass_context
def app(ctx, config, output, source_dir, batch_dir, dry_run):
	ctx.ensure_object(dict)
	ctx.obj['CONFIG'] = Path(config)
	ctx.obj['OUTPUT_DIR'] = Path(output)
	ctx.obj['SOURCE_DIR'] = Path(source_dir)
	Mezzanine.root_dir = ctx.obj['SOURCE_DIR']
	ctx.obj['BATCH_DIR'] = batch_dir
	ctx.obj['DRY_RUN'] = dry_run


@app.command()
@click.pass_context
def validate(ctx):
	rows = []
	for (m, tc, fps_family) in iter_test_vectors_in_config(ctx):
		row = validat_test_content(ctx, m, tc, fps_family)
		rows.append({
			'test_id': tc.test_id,
			'fps': tc.get_fps(fps_family).to_number(),
			**row
		})
	with open('validation.csv', 'w') as fo:
		writer = csv.DictWriter(fo, fieldnames=rows[0].keys())
		writer.writeheader()
		writer.writerows(rows)

@app.command()
@click.pass_context
def patch(ctx):
	for (m, tc, fps_family) in iter_test_vectors_in_config(ctx):
		test_stream_mpd = test_stream_dir(ctx, tc, fps_family) / 'stream.mpd'
		ContentModel.patch_mpd(test_stream_mpd, m, tc)

if __name__ == '__main__':
    app(obj={})