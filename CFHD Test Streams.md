This is an updated version of the list in the Word file attached to [#9](https://github.com/cta-wave/Test-Content-Generation/issues/9).

The content options are all taken verbatim from the CFHD section of the WAVE device playback capabilities spec.

Please raise an issue to notify of any problems with these test content definitions.

It is built up as follows;
* Stream 1 is the base stream.
* Streams 2 and 3 are for testing AVC content options. Stream 2 differs from the base as much as possible. Every content option is different.
* Stream 3 is for the content options that have 3 possibilities and differs from the base only for those content options. It is of course possible to re-balance streams 2 and 3 & make stream 2 closer to the base and stream 3 further away.
* Streams 4 through 11 are for debugging if either streams 2 or 3 fail to play. Each of them differs from the base by exactly one content option.
* Streams 1 and 12 through 23 are a simple content ladder for testing CMAF switching sets.
* Stream 1 should have content options that are representative of existing industry practice. 
* The resolutions and bitrates in the simple content ladder in streams 12 through 23 should also be representative of existing practice.

| Stream ID | picture timing SEI message | VUI timing information | Sample entry (CMAF 9.4.1.2) | CMAF fragment duration | Initialization constraints | Fragments containing one or multiple moof/mdat pairs | resolution | frame rate | bitrate | length |
|----------|:-------------:|------:|-------|------|-----|-----|-----|-----|----|---|
|1 = base stream|present|present|avc1 sample entry type (parameter sets within the CMAF Header)|2s|Regular Switching Set, do not apply CMAF clause 7.3.4.2 and 9.2.11.4|Fragment is 1 chunk|1920x1080|25Hz, 29.97Hz, 30Hz, 50Hz, 59.94Hz or 60Hz|A bps (note 1)|60s|
|2|not present|not present|avc3 sample entry type (in-band parameter sets) without parameter sets within the CMAF header|5s|Single initialization constraints, see CMAF clause 7.3.4.2 and 9.2.11.4|Fragment contains multiple chunks (p-frame to p-frame with b-frames)|as 1|as 1|as 1|as 1|
|3|as 1|as 1|avc3 sample entry type (in-band parameter sets) with parameter sets within the CMAF header|as 1|as 1|Each sample constitutes a chunk (p-frame only)|as 1|as 1|as 1|as 1|
|4|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|5|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|6|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|7|as 1|as 1|as 3|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|8|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|
|9|as 1|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|
|10|as 1|as 1|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|
|11|as 1|as 1|as 1|as 1|as 1|as 3|as 1|as 1|as 1|as 1|
|12|as 1|as 1|as 1|as 1|as 1|as 1|1920x1080|as 1|B bps < A (note 1)|as 1|
|13|as 1|as 1|as 1|as 1|as 1|as 1|1600x900|as 1|(note 1)|as 1|
|14|as 1|as 1|as 1|as 1|as 1|as 1|1280x720|as 1|(note 1)|as 1|
|15|as 1|as 1|as 1|as 1|as 1|as 1|1024x576|as 1|(note 1)|as 1|
|16|as 1|as 1|as 1|as 1|as 1|as 1|960x540|as 1|(note 1)|as 1|
|17|as 1|as 1|as 1|as 1|as 1|as 1|852x480|as 1|(note 1)|as 1|
|18|as 1|as 1|as 1|as 1|as 1|as 1|768x432|as 1|(note 1)|as 1|
|19|as 1|as 1|as 1|as 1|as 1|as 1|720x404|as 1|(note 1)|as 1|
|20|as 1|as 1|as 1|as 1|as 1|as 1|704x396|as 1|(note 1)|as 1|
|21|as 1|as 1|as 1|as 1|as 1|as 1|640x360|as 1|(note 1)|as 1|
|22|as 1|as 1|as 1|as 1|as 1|as 1|512x288|as 1|(note 1)|as 1|
|23|as 1|as 1|as 1|as 1|as 1|as 1|480x270|as 1|(note 1)|as 1|

Note 1: A bitrate ladder representative of existing practices should be used.
