# Test-Content-Generation
Provides all information and scripts how the CTA Wave Test Content is generated. This is primarily about the usage of FFMPEG with x264 and x265 to generate the content.

* Download mezzanine content from folder 2)
* Encode mezzanine content (from folder 2)
  * Encode to conform to CTA Proposed Test content.
  * Encode at least one option of source content according to media profile.
* Package (markup) the content with an MPD according to the CTA Content Model format
  * needs likely to be done manually right now, but could eventually an extension to FFMPEG to produce this
* Upload the proposed test content to folder 3) from above
* Document the detailed procedures from above
* Validate that the content conforms to
  * CMAF
  * CTA WAVE Test content format
  * Uses the proper mezzanine
  * Revise mezzanine test content if needed and repeat tasks 9-13 as needed
* If valid, move content to folder 4)
