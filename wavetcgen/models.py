from dataclasses import dataclass
from enum import Enum
import os
from fractions import Fraction
import json
import csv
from pathlib import Path

# on Apple's "Numbers", csv exports use ";"
CSV_DELIMITER = os.getenv("CSV_DELIMITER", ",")

PROFILES_TYPE = {
    "cfhd": ("video", "h264", "avchd"), # @FIXME: avchd ???
    "chdf": ("video", "h264", "avchdhf"), # @FIXME: deprecated ? not found in Device Playback Capabilities Specification
    "chh1": ("video", "h265", None),
    "cud1": ("video", "h265", None),
    "clg1": ("video", "h265", None),
    "chd1": ("video", "h265", None),
    "caac": ("audio", "aac", "caac"),
    "dts1": ("audio", "copy", None),
    "dts2": ("audio", "copy", None)
}


class VideoResolution:

	def __init__(self, w:int, h:int) -> None:
		self.h = h
		self.w = w

	def __str__(self) -> str:
		return f'{self.w}x{self.h}'
	
	@classmethod
	def from_string(cls, s):
		wh = [int(x) for x in s.split('x')]
		return cls(*wh)
	

class FPS(Fraction):

	@classmethod
	def from_string(cls, s):
		if s in ('25', '50', '15', '30', '60'):
			return cls(int(s)*1000, 1000)
		elif s == '12.5':
			return cls(12500, 1001)
		elif s == '14.985':
			return cls(15000, 1001)
		elif s == '29.97':
			return cls(30000, 1001)
		elif s == '59.94':
			return cls(60000, 1001)
		else:
			raise NotImplementedError(f'unknown framerate {s}')

	def to_lossy_string(self):
		if self.denominator == 1:
			return str(self.numerator)
		elif self == Fraction(25, 2):
			return '12.5'
		elif self == Fraction(30000, 1001):
			return '29.97'
		elif self == Fraction(60000, 1001):
			return '59.94'
		elif self == Fraction(15000, 1001):
			return '14.985'
		else:
			raise NotImplementedError(f'unknown framerate {self}')

	@property
	def family(self) -> 'FPS_SUITE':
		fps = str(self)
		for fam in (FPS_SUITE._12_25_50, FPS_SUITE._14_29_59, FPS_SUITE._15_30_60):
			if fps in fam.value:
				return fam


class FPS_SUITE(str, Enum):
	_14_29_59 = '14.985_29.97_59.94'
	_12_25_50 = '12.5_25_50'
	_15_30_60 = '15_30_60'
	
	@staticmethod
	def all():
		return [
			FPS_SUITE._12_25_50,
			FPS_SUITE._14_29_59,
			FPS_SUITE._15_30_60
		]

	@classmethod
	def from_string(cls, s):
		if s == cls._12_25_50.value:
			return cls._12_25_50
		if s == cls._14_29_59.value:
			return cls._14_29_59
		if s == cls._15_30_60.value:
			return cls._12_25_50
		

class Mezzanine:

	root_dir = Path()

	def __init__(self, basename:str, label:str, resolution:'VideoResolution', fps:FPS, duration:str, hdr:str):
		self.content = basename
		self.label = label
		self.resolution = resolution
		self.fps = fps
		self.duration = duration
		self.hdr = hdr
		self._properties = None
		self._md5 = None
	
	@staticmethod
	def fps_family(fps:FPS) -> FPS_SUITE:
		return fps.family

	@property
	def encoder_hdr_opts(self):
			raise NotImplementedError('encoder_hdr_opts not implemented')
		
	@property
	def filename(self) -> str:
		dur = str(self.duration)
		if dur.endswith(".0"):
			dur = dur[:-2]
		return f'{self.content}{self.label}_{self.resolution}@{self.fps.to_lossy_string()}_{dur}.mp4'

	@property
	def copyright_notice(self) -> str:
		if self._copyright_notice is None:
			self.load_annotations()
		return self._copyright_notice

	@property
	def source_notice(self) -> str:
			if self._source_notice is None:
				self.load_annotations()
			return self._source_notice

	@property
	def bit_depth(self) -> int:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("bit_depth", None)

	@property
	def mastering_display(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("mastering_display", None)

	@property
	def max_cll_fall(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("max_cll_fall", None)

	@property
	def pixel_format(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("pixel_format", None)

	@property
	def color_primaries(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("color_primaries", None)

	@property
	def matrix_coefficients(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("matrix_coefficients", None)

	@property
	def transfer_characteristics(self) -> str:
		if self._properties is None:
			self.load_annotations()
		return self._properties.get("transfer_characteristics", None)

	@property
	def md5(self) -> str:
		if self._md5 is None:
			self.load_annotations()
		return self._md5

	def load_annotations(self):
		annotation_filename = (self.root_dir / self.filename).with_suffix(".json")
		if not os.path.exists(annotation_filename):
			raise FileNotFoundError(f"Annotation file {annotation_filename} not found. Skipping entry.")
		with open(annotation_filename, 'r') as fo:
			data = json.load(fo)
			
			self._md5 = data["Mezzanine"]["md5"]

			self._properties = data["Mezzanine"]["properties"]
			assert self._properties["width"] == self.resolution.w, 'invalid mezzanine width found in metadata'
			assert self._properties["height"] == self.resolution.h, 'invalid mezzanine height found in metadata'
			assert str(self._properties["frame_rate"]) == str(self.fps.to_lossy_string()), 'invalid mezzanine frame_rate found in metadata'

			self._copyright_notice = data["Mezzanine"]["license"]
			self._source_notice = "" + data["Mezzanine"]["name"] + " version " + str(data["Mezzanine"]["version"]) + " (" + data["Mezzanine"]["creation_date"] + ")"
			return self._copyright_notice, self._source_notice

	@classmethod
	def from_filename(cls, fp:Path) -> 'Mezzanine':
		chunks = fp.stem.split('_')
		duration = chunks[-1]
		res, fps = chunks[-2].split('@')
		mezzanine_id = chunks[-3]
		hdr = chunks[-4]
		return Mezzanine(fp.name, mezzanine_id, VideoResolution.from_string(res), FPS.from_string(fps), duration, hdr)



class CmafBrand(str, Enum):
	
	CHH1: str = "chh1"
	CUD1: str = "cud1"
	CLG1: str = "clg1"
	CHD1: str = "chd1"

	@classmethod
	def from_string(cls, s):
		if s == "chh1" :
			return cls.CHH1
		elif s == "cud1" :
			return cls.CUD1
		elif s == "clg1" :
			return cls.CLG1
		elif s == "chd1" :
			return cls.CHD1


class CmafInitConstraints(str, Enum):
	SINGLE: str = 'single'
	MULTIPLE: str = 'multiple'

class CmafStructuralBrand(str, Enum):
	CMF2: str = 'cmf2'
	CMFC: str = 'cmfc'

# class CmafChunksPerFragment is used by validation script
class CmafFragmentType(str, Enum):
	NONE: str = ""
	DURATION: str = "duration"
	PFRAMES: str = "pframes"
	EVERY_FRAME: str = "every_frame" 


@dataclass
class Representation:
	resolution: 'VideoResolution'
	framerate: Fraction
	bitrate: int # o.bitrate
	input: str # input_filename

	def to_json(self):
		return {"resolution": self.resolution, "framerate": self.fps, "bitrate": self.bitrate, "input": self.input}


# PARSE TESTT CONTENT FROM MATRIX

@dataclass
class TestContent:
	"""
	class representing a stream parsed out of the csv matrix
	"""
	
	test_id:str
	summary:str
	picture_timing_sei:bool
	vui_timing:bool

	sample_entry:str
	parameter_sets_in_cmaf_header:bool
	parameter_sets_in_band:bool

	cmaf_fragment_duration:int
	cmaf_init_constraints:CmafInitConstraints
	fragment_type:CmafFragmentType
	sample_flags_in_track_boxes:bool
	resolution:VideoResolution
	aspect_ratio_idc:float
	fps_base:tuple[float]
	
	bitrate:int
	
	duration:float
	codec:str
	cmaf_media_profile:CmafBrand
	encryption:bool
	mezzanine_label:str
	mezzanine_prefix_25HZ:str
	mezzanine_prefix_30HZ:str

	@property
	def mpd_sample_duration_delta(self) -> float:
		raise NotImplementedError('')

	@property
	def cmaf_structural_brand(self) -> CmafStructuralBrand:
		# 10.2.3. Content Options : Compositions offsets and Timing
		if self.sample_flags_in_track_boxes:
			return CmafStructuralBrand.CMF2
		else:
			return CmafStructuralBrand.CMFC

	@staticmethod
	def get_fps_base(s):
		if s == 0.25:
			return ('12.5', '15')
		elif s == 0.5:
			return ('25', '29.97', '30')
		elif s == 1:
			return ('50', '59.94', '60')
		elif s == 2:
			return ('100', '120')

	def get_fps(self, fps_suite:FPS_SUITE) -> FPS:
		if fps_suite == FPS_SUITE._12_25_50:
			return FPS.from_string(self.fps_base[0])
		if fps_suite == FPS_SUITE._15_30_60:
			return FPS.from_string(self.fps_base[-1])
		if fps_suite == FPS_SUITE._14_29_59:
			if len(self.fps_base) < 3:
				raise NotImplementedError(f'fps_suite: {fps_suite} not found in {self.fps_base}')
			return FPS.from_string(self.fps_base[1])

	def get_mezzanine(self, fps_suite:FPS_SUITE) -> Mezzanine:
		hdr = None
		if self.cmaf_media_profile == 'cud1':
			hdr = 'sdr_bt2020'
		elif self.cmaf_media_profile == 'clg1':
			hdr = 'hlg10'
		elif self.cmaf_media_profile == 'chd1':
			hdr = 'hdr10'
		fps = self.get_fps(fps_suite)
		basename = self.mezzanine_prefix_25HZ if fps.to_lossy_string() in ('50', '25', '12.5') else self.mezzanine_prefix_30HZ
		return Mezzanine(
				basename=basename,
				label=self.mezzanine_label, 
				resolution=self.resolution, 
				fps=fps,
				duration=self.duration,
				hdr=hdr
			)

	def get_representation(self, m:Mezzanine):
		return Representation(self.resolution, m.fps, self.bitrate, m.filename)

	def get_seg_dur(self, m:Mezzanine):
		seg_dur = Fraction(t.cmaf_fragment_duration)
		if m.fps.denominator == 1001:
			seg_dur = Fraction(t.cmaf_fragment_duration) * Fraction(1001, 1000)
		return seg_dur

	def to_batch_config_row(self):
		if self.fps_base[0] == '12.5':
			framerate = '0.25'
		elif self.fps_base[0] == '25':
			framerate = '0.5'
		elif self.fps_base[0] == '50':
			framerate = '1'
		elif self.fps_base[0] == '100':
			framerate = '2'

		return {
			"Stream ID" : self.test_id,
			"mezzanine radius" : f'{self.mezzanine_label}_{self.resolution}',
			"pic timing" : self.picture_timing_sei,
			"VUI timing" : self.vui_timing,
			"sample entry" : self.sample_entry,
			"CMAF frag dur" : self.cmaf_fragment_duration,
			"init constraints" : self.cmaf_init_constraints,
			"frag_type" : self.fragment_type,
			"resolution" : self.resolution,
			"framerate" : framerate,
			"bitrate" : self.bitrate,
			"duration" : self.duration,
			"cmaf_profile" : self.cmaf_structural_brand,
			"wave_profile" : self.cmaf_media_profile,
			"cenc" : self.encryption,
			"sar": self.aspect_ratio_idc,
			"mezzanine_prefix_25HZ": self.mezzanine_prefix_25HZ,
			"mezzanine_prefix_30HZ": self.mezzanine_prefix_30HZ
		}
	

	@staticmethod
	def from_batch_config_row(**row) -> 'TestContent':
			parse_bool = lambda x: x.upper() == 'TRUE'
			test_id = row["Stream ID"]
			mr = str(row["mezzanine radius"]).split('_')
			mezzanine_label = mr[0]
			resolution = VideoResolution.from_string(mr[1])
			picture_timing_sei = parse_bool(row["pic timing"])
			vui_timing = parse_bool(row["VUI timing"])
			sample_entry = row["sample entry"]
			cmaf_fragment_duration = row["CMAF frag dur"]
			if row["init constraints"] == "single":
				cmaf_init_constraints = CmafInitConstraints.SINGLE 
			elif row["init constraints"] == "multiple":
				cmaf_init_constraints = CmafInitConstraints.MULTIPLE
			else:
				raise Exception('invalid CMAF init constraints')
			
			if row["frag_type"] == CmafFragmentType.EVERY_FRAME.value:
				fragment_type = CmafFragmentType.EVERY_FRAME
			elif row["frag_type"] == CmafFragmentType.DURATION.value:
				fragment_type = CmafFragmentType.DURATION
			elif row["frag_type"] == CmafFragmentType.PFRAMES.value:
				fragment_type = CmafFragmentType.PFRAMES
			else:
				raise Exception('invalid CMAF fragment type')

			fps_base = TestContent.get_fps_base(float(row["framerate"]))

			bitrate = int(row["bitrate"])
			duration = row["duration"].rstrip('s')
			if row["cmaf_profile"] == CmafStructuralBrand.CMF2.value:
				cmaf_structural_brand = CmafStructuralBrand.CMF2
			elif row["cmaf_profile"] == CmafStructuralBrand.CMFC.value:
				cmaf_structural_brand = CmafStructuralBrand.CMFC
			else:
				raise Exception(f'Invalid CMAF structural brand {row["cmaf_profile"]}')
			cmaf_media_profile = CmafBrand.from_string(row["wave_profile"])
			encryption = row["cenc"]
			aspect_ratio_idc = row.get("sar", 1.0)
			mezzanine_prefix_25HZ = row["mezzanine_prefix_25HZ"]
			mezzanine_prefix_30HZ = row["mezzanine_prefix_30HZ"]
			
			return TestContent(
				test_id,
				None,
				picture_timing_sei,
				vui_timing,
				sample_entry,
				None,
				None,
				cmaf_fragment_duration,
				cmaf_init_constraints,
				fragment_type,
				cmaf_structural_brand == CmafStructuralBrand.CMF2,
				resolution,
				aspect_ratio_idc,
				fps_base,
				bitrate,
				duration,
				None,
				cmaf_media_profile,
				encryption,
				mezzanine_label,
				mezzanine_prefix_25HZ,
				mezzanine_prefix_30HZ
			)

	
	@staticmethod
	def from_matrix_column(col) -> 'TestContent':
		"""
		extract stream properties from CSV rows
		- streams are stored as columns
		- matrix format on google drive may be modifed without notice by editors, 
			this is based on the format of the AVC matrix
		"""
		test_id = col[1]
		summary = col[2]

		# 4 - with and without picture timing SEI message.
		picture_timing_sei = not 'without' in col[3].lower()

		# 5 - with and without VUI timing information.
		vui_timing = not 'without' in col[4].lower()

		# 6 - Sample entry, see CMAF clause 9.4.1.2
		sample_entry = col[5].split(" ")[0]
		parameter_sets_in_cmaf_header = not 'without parameter sets within the CMAF header' in col[5]
		parameter_sets_in_band = 'in-band parameter sets' in col[5]
		
		# 7 - CMAF Fragment durations
		cmaf_fragment_duration = float(col[6])
		
		# 8 - Initialization Constraints
		cmaf_init_constraints = CmafInitConstraints.SINGLE if col[7].lower().startswith('single') else CmafInitConstraints.MULTIPLE
		
		# 9 - Fragments containing one or multiple moof/mdat pairs
		if 'fragment is 1 chunk' in col[8].lower():
			fragment_type = CmafFragmentType.DURATION # SINGLE
		elif 'fragment contains multiple chunks' in col[8].lower(): # with b-frames
			fragment_type = CmafFragmentType.PFRAMES # MULTIPLE
		elif 'each sample constitutes a chunk' in col[8].lower(): # p-frames only
			fragment_type = CmafFragmentType.EVERY_FRAME # MULTIPLE_CHUNKS_ARE_SAMPLES
		else:
			raise Exception(f'Invalid test matrix format on row 9 - CmafFragmentType')
		
		# 10 - Resolution
		resolution = VideoResolution.from_string(col[9])

		# 11 - Frame rate (2.0=100/120,1.0=50/59.94/60, 0.5=25/29.97/30, 0.25=12.5/15)
		s = float(col[10])
		fps_base = TestContent.get_fps_base(s)
	
		# 12 - Bit rate
		bitrate = col[11]
		
		# 13 - Duration of stream
		duration = float(col[12].rstrip('s')) if bool(col[12]) else -1

		# 14 - AVC/HEVC profile and level
		codec = col[13]

		# 15 - CMAF media profile
		cmaf_media_profile = CmafBrand.from_string(col[14])

		# 16 - Encryption
		encryption = 'cenc' in col[15].lower()
		
		# 17 - Mezzanine label
		mezzanine_label = col[16]

		# 18 - default_sample_flags, sample_flags and first_sample_flags in the TrackFragmentHeaderBox and TrackRunBox 
		assert 'set' in col[17].lower(), f'Invalid test matrix format on row 10' # AVC = resolution
		sample_flags_in_track_boxes = 'not set' in col[17].lower()

		# 19 - aspect_ratio_idc (sample aspect ratio 1=1:1, 14=4:3)
		aspect_ratio_idc = float(col[18])

		# 20 - Mezzanine prefix 25Hz family
		mezzanine_prefix_25HZ = col[19]
		# 21 - Mezzanine prefix 30Hz family including fractional rates
		mezzanine_prefix_30HZ = col[20]
				
		return TestContent(
			test_id,
			summary,
			picture_timing_sei,
			vui_timing,
			sample_entry,
			parameter_sets_in_cmaf_header,
			parameter_sets_in_band,
			cmaf_fragment_duration,
			cmaf_init_constraints,
			fragment_type,
			sample_flags_in_track_boxes,
			resolution,
			aspect_ratio_idc,
			fps_base,
			bitrate,
			duration,
			codec,
			cmaf_media_profile,
			encryption,
			mezzanine_label,
			mezzanine_prefix_25HZ,
			mezzanine_prefix_30HZ
		)


	@staticmethod
	def iter_vectors_in_batch_config(tcgen_config):
		with open(tcgen_config) as fo:
			for row in csv.DictReader(fo, delimiter=CSV_DELIMITER):
				yield TestContent.from_batch_config_row(**row)


	@staticmethod
	def iter_vectors_in_matrix(csv_matrix, start_col_idx=4):

		rows = None
		columns = []
		count = 0

		with open(csv_matrix) as fo:
			rows = [*csv.reader(fo, delimiter=CSV_DELIMITER)]
			count = max([len(r) for r in rows])

		columns = [[] for _ in range(count)]
		for c, col in enumerate(columns):
			for row in rows:
				col.append(row[c])

		for c, col in enumerate(columns):
			if c >= start_col_idx:
				yield TestContent.from_matrix_column(col)
