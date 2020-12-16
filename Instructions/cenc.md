# CENC Test Streams

This is a version of the list in the [Word file documenting content options](https://1drv.ms/w/s!AiNJEPgowJnWgqozHN_loWOUe9t51A?e=Q08VH9) for encrypted content.

The content options are all taken verbatim from section 10.5 of the WAVE device playback capabilities spec.

The legend is as follows
* base stream: the unencrypted stream, please provide reference to CFHD/CAAC and stream number
* 8.2.1 TrackEncryptionBox: provides the version of the Track Encryption Box
* 8.2.2.1 SampleEncryptionBox: present/absent
* 8.2.2.1 Sample Auxiliary Information: present/absent
* 8.2.2.1 SampleAuxiliaryInformationSizesBox: present/absent
* 8.2.2.1 Per_Sample_IV_Size: zero or non-zero
* 8.2.2.3 pssh options: 
  1.   Absent from CMAF Header and CMAF Fragments
  1.   Version 0 present in CMAF Header
  1.   Version 1 present in CMAF Header
  1.   Version 1 present in CMAF Fragments
  1.   Presence on multiple levels
  1.   Presence of multiple pssh boxes
* 8.2.3.1  key storage: Any additional keys described by sample groups may be stored in version 1 ProtectionSystemSpecificHeaderBoxes in CMAF fragments, identifying the contained KID(s), protected by DRM specific methods.
* 8.2.3.2 Clear Samples
  1. Sample groups not indicating unprotected media samples, as specified in ISO/IEC 23001-7. 
  1. Sample groups indicating unprotected media samples, as specified in ISO/IEC 23001-7.
* DRM System
  * test
  * clear
  * other


| number | base stream | TrackEncryptionBox | SampleEncryptionBox | Sample Auxiliary Information | SampleAuxiliaryInformationSizesBox | Per_Sample_IV_Size | pssh | key storage | clear samples | DRM |
|----------|:-------------:|------:|-------|------|-----|-----|-----|-----|----|----|
|1|CFHD1|v1|present|present|present|non-zero|Option 1|no keys stored|no indication|test| 
|2|as 1|v0|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|3|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|4|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|5|as 1|as 1|as 3|as 1|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|6|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|as 1|
|7|as 1|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|as 1|
|8|as 1|as 1|as 1|as 1|as 1|as 2|as 1|as 1|as 1|as 1|as 1|
|9|as 1|as 1|as 1|as 1|as 1|as 3|as 1|as 1|as 1|as 1|as 1|
