# CFHD Test Streams

The content options are all taken verbatim from the CFHD section of the WAVE device playback capabilities spec.

It is built up as follows;

* Stream 1 is the base stream.
* Streams 2 and 3 are for testing AVC content options. Stream 2 differs from the base as much as possible. Every content option is different. It may of course not be possible to generate this using ffmpeg.
* Stream 3 is for the content options that have 3 possibilities and differs from the base only for those content options. It is of course possible to re-balance streams 2 and 3 & make stream 2 closer to the base and stream 3 further away.
* Streams 4 through 11 are for debugging if either streams 2 or 3 fail to play. Each of them differs from the base by exactly one content option.
* Streams 1 and 12 through 15 are a simple content ladder for testing CMAF switching sets.

https://docs.google.com/spreadsheets/d/1hxbqBdJEEdVIDEkpjZ8f5kvbat_9VGxwFP77AXA_0Ao/edit#gid=0
