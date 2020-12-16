# CAAC test streams

This is a version of the list in the [Word file documenting content options](https://1drv.ms/w/s!AiNJEPgowJnWgqozHN_loWOUe9t51A?e=Q08VH9) for CMAF content for CAAC media profile, but also for generic options.

The content options are all taken verbatim from section 10.3 of the WAVE device playback capabilities spec (see above).

The legend is as follows
* mezzanine: refers to the mezzanine to be used for the test vector
* structural brand: cmfc or cmf2
* trun: 7.5.17	Track Run Box ('trun') v0 or v1
* elst: 7.5.13	Edit List Box ('elst')
* defaults_ default_sample_flags, sample_flags and first_sample_flags set 
  * TrackFragmentHeaderBox
  * TrackRunBox
  * _Needs checking_
* emsg: 7.4.5	Event Message Box ('emsg')
  * absent
  * present
* Profiles:
  * AAC-LC
  * HE-AAC
  * HE-AACv2
* Sampling frequency in kHz
* dynamic range/loudness control
  * absent
  * present
* program_config_element (PCE) element 
  * absent
  * present
* CMAF Fragment duration in milliseconds
  * 2000
  * 5000
  * 500
* CMAF Chunks
  * none
  * 500ms
  * per frame

| number | mezzanine | brand | trun |  elst | defaults | emsg  | codec | sampling frequency | drc | PCE | CMAF Fragment duration | chunks | 
|--------|:---------:|:-----:|------|-------|----------|-------|-------|----------|----|----|--------|----|
|1|tbd|cmfc|v0|present|trun|absent|AAC-LC|48000|absent|absent|2000|1 chunk | 
|2|as 1|cmf2|v1|absent|tfhd|absent|AAC-LC|48000|absent|absent|2000|1 chunk | 
|test|tbd|cmf2|v1|present|tfhd|absent|HE-AAC|48000|present|present|2000|1 chunk |

