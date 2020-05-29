# Test-Content-Generation

## Overview
Provides all information and scripts how the CTA Wave Test Content is generated. This is primarily about the usage of FFMPEG with x264 and x265 to generate the content.

* Download mezzanine content from folder 2)
* Encode mezzanine content (from folder 2)
  * Encode to conform to CTA Proposed Test content.
  * Encode at least one option of source content according to media profile.
* Package (markup) the content with an MPD according to the CTA Content Model format
  * needs likely to be done manually right now, but could eventually an extension to FFMPEG to produce this
  * **Script** Ece can write script to modify to conform to the content model formating
* Upload the proposed test content to folder <add> from above
* Document the detailed procedures from above
 * **Setup Web page** This documentation will developed under this github repository. Md to a website.
* Validate that the content conforms to
  * CMAF
  * CTA WAVE Test content format **needs to be extended to format validation**
  * Uses the proper mezzanine
  * Revise mezzanine test content if needed and repeat tasks 9-13 as needed
* If valid, move content to folder 4) <add>
 
 ## Encoding to test content
 
 * Content options are documented here: https://1drv.ms/w/s!AiNJEPgowJnWgbpZesbLvglzCXVlSg?e=4ZFRyB
 
 * for the first test content
   * pick on mezzanine, for example 720p @ 50Hz
   * Ece to check on picture timing what is default
   * avc1
   * 2 seconds of CMAF Fragments
   * no chunking
   * spatial sub-sampling for different Representations
     * note that we need to use different mezzanine version (A,B,C) for each Representation 
   * unencrypted
  * write a script/command line for FFMPEG to generate the above content, might also include a repackaging script.
  
 
