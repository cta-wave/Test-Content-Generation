### Content Options

The content options are based on clause 10.2.2, but only a subset is
recommended to be tested as general constraints are expected to be
covered by the tests in clause 10.2.

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

-   *Priority is given to 1920x1080p50 and 1920x1080p60*

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

### Test Content

https://github.com/cta-wave/Test-Content-Generation/blob/master/Instructions/chh1.md

<table>
<colgroup>
<col style="width: 9%" />
<col style="width: 11%" />
<col style="width: 12%" />
<col style="width: 8%" />
<col style="width: 28%" />
<col style="width: 28%" />
</colgroup>
<thead>
<tr class="header">
<th>Number</th>
<th>Default flags</th>
<th>Sample entry</th>
<th>chunks</th>
<th>Spatial and temporal supsampling</th>
<th>Source content</th>
</tr>
</thead>
<tbody>
<tr class="odd">
<td>hevc1</td>
<td>yes</td>
<td>hvc1</td>
<td>1</td>
<td>no</td>
<td><em>1920x1080p50</em></td>
</tr>
<tr class="even">
<td>hevc2</td>
<td>no</td>
<td>hev1</td>
<td>1</td>
<td>no</td>
<td><em>1920x1080p50</em></td>
</tr>
<tr class="odd">
<td>hevc3</td>
<td>yes</td>
<td>hvc1</td>
<td>10</td>
<td>no</td>
<td><em>1920x1080p50</em></td>
</tr>
<tr class="even">
<td>hevc4</td>
<td>yes</td>
<td>hvc1</td>
<td>1</td>
<td>2 spatial (1080 &amp; 720)<br />
2 temporal (50 &amp; 25)</td>
<td><em>1920x1080p50</em></td>
</tr>
<tr class="odd">
<td>hevc5</td>
<td>yes</td>
<td>hvc1</td>
<td>1</td>
<td>2 spatial (1080 &amp; 720)<br />
2 temporal (30 &amp; 60)</td>
<td><em>1920x1080p @ 60/1.001</em></td>
</tr>
</tbody>
</table>
