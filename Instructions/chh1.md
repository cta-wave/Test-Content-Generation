**Proposed CMAF Options (see clause 7 of CMAF \[CMAF\])**

-   Compositions offsets and Timing

    -   'cmfc'

        -   7.5.17 Track Run Box ('trun')

            -   v1 – combined with SAP type 1 (typically with P-Pictures
                only)

        -   7.5.13 Edit List Box ('elst')

            -   Absent

            -   Two options for default flags

                -   default_sample_flags, sample_flags and
                    first_sample_flags neither set in the
                    TrackFragmentHeaderBox nor TrackRunBox

                -   default_sample_flags, sample_flags and
                    first_sample_flags set in the TrackFragmentHeaderBox
                    and TrackRunBox

-   7.4.5 Event Message Box ('emsg')

    -   *absent*

**Source Content Options**

-   50Hz video

-   60Hz video, 60/1.001 Hz

-   *Priority is given to 1920x1080p25 and 1280x720p50*

-   16:9 picture aspect ratio square pixel \[CMAF\], clause 9.2.3 and
    9.4.2.2.2.

-   At least one source sequence with another picture aspect ratio,
    non-square pixel with conformance cropping following the example in
    Annex C.8 of \[CMAF\] specification.

**Encoding and Packaging options**

-   SEI and VUI

    -   without picture timing SEI message

    -   without VUI timing information

-   Sample entry, see CMAF clause 9.4.1.2. Two options

    -   'hvc1' sample entry type (parameter sets within the CMAF Header)

    -   'hev1' sample entry type (parameter sets within the movie
        fragment header)

-   Initialization Constraints.

    -   Regular Switching Set, do not apply CMAF clause 7.3.4.2 and
        9.2.11.4

-   CMAF Fragment durations

    -   *2 seconds*

-   Fragments containing one or multiple moof/mdat pairs – two options

    -   *Fragment is 1 chunk*

    -   *Fragment contains multiple chunks (p-frame to p-frame with
        b-frames)*

-   Switching Set encoding following CMAF, Annex C.9 recommendation. At
    least one of each of the following options

    -   Spatial subsampling of video according to CMAF, Annex C.2
        recommendation

    -   Spatial and temporal subsampling and scaling of video according
        to CMAF, Annex C.1 recommendation for each 50 Hz and 60 Hz
        family

    -   CMAF, Annex C.9.4 recommendation for low-latency live

-   B.2.4

    -   No SEI messages present

-   B.3.3.2

    -   Single VPS

-   B.3.3.3.2

    -   colour_description_flag set to 1

    -   vui_time_scale and vui_num_units_in_tick set to constant

-   B.5

    -   Settings according the requirements of the profile chh1 in Table
        B.1
        
**Proposed Test Content**

| Number | Default flags | Sample entry | chunks | Spatial and temporal supsampling |
|--------|---------------|--------------|--------|----------------------------------|
| hevc1  | yes           | hvc1         | 1      | no                               |
| hevc2  | no            | hev1         | 1      | no                               |
| hevc3  | yes           | hvc1         | 10     | no                               |
| hevc4  | Yes           | Hvc1         | 1      | 2 spatial and 2 temporal         |
