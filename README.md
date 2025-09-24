# Test-Content-Generation

## Introduction

This repository provides the information and scripts to generate the CTA Wave Test Content according to [CTa-5003-B](https://shop.cta.tech/products/web-application-video-ecosystem-device-playback-capabilities-cta-5003-b) . 


## scripts installation

clone the repository:
```
# clone the code
git clone https://github.com/cta-wave/Test-Content-Generation.git
cd Test-Content-Generation

# create/activate a python virtual environment (recommended) - docs.python.org/3/library/venv.html
python -m venv .venv
source venv/bin/activate

# install the content generation scripts 
pip install -e .

# now this should work 
tcgen --help
```

Note: Once installed in a [python environment](https://docs.python.org/3/library/venv.html#creating-virtual-environments), the functions and classes defined in the `tcgen` package can be used in any python script, making it easy to build upon.


## Workflow

1. Download Mezzanine content
2. Create a batch configuration file
3. Batch encode/package content
4. Content post-processing (creating chunked fragments, switching sets, )
5. Batch conformance testing
6. Create zip archives and generate a database from batch configuration
7. Upload batch content
8. Download database content

*_Important_*: the following workflow has been implemented while generating HEVC test content. Although it hasn't been tested with AVC content, it is expected to work exactly the same. **For audio content, a separate set of instructions is available**. It is suggested that this worflow be used for all content future generation. 


### 1. Donwload mezzanine content

Test vectors are generated from mezzanine content.

Mezzanine content is generated with the [cta-wave mezzanine software](https://github.com/cta-wave/mezzanine). It can be downloaded preferably over SFTP, or alternatively over [HTTP](https://dash.akamaized.net/WAVE/Mezzanine/releases). 

Make sure to check mezzanine file's md5 checksum after downloading. It should match the one in the sidecar json metadata.


### 2. Create a batch configuration file

Configuration files are used by several `tcgen` commands such as `tcgen encode` to process batches of test vectors.
A configuration file is a `.csv` file declaring the encoder and/or packager options, with each csv row declaring a test vector. For details on the configuration files, refer to the [./profiles/README.md](profiles/README.md).

Batch files used to produce reference content is stored in the [./profiles](profiles) directory.

### 3. Batch encode/package content


#### 3.1 Video content

typical usage of `tcgen encode`:
```
tcgen encode -v ./output -b 2024-01-31 /path/to/mazzanine/dir ./profiles/config.csv
```

Note the batch id. When unspecified, the current date will be used as batch id.

For detail on each available options use : `tcgen encode --help`



The encoding and packaging is performed using [GPAC](http://gpac.io), leveraging [libavcodec](https://ffmpeg.org/libavcodec.html) with [x264](http://www.videolan.org/developers/x264.html) and [x265](https://www.x265.org/) to generate the CMAF content along with a DASH manifest. The intent is to keep the size of the post-processing (e.g. manifest manipulation) as small as possible.



#### 3.2 Audio content

##### 3.1 - AAC / AC-4 / E-AC-3

See detailed instructions for AAC / AC-4 / E-AC-3 : [Encoding and packaging Audio content (AAC / AC-4 / E-AC-3)](Instructions/audio.md)


### 5. Batch conformance testing

#### 5.1 DASH-IF Conformance validation (JCCP)

...


#### 5.2 CTA WAVE validation reports

A separate set of test content validation scripts may be used to cross-check the results:
- check that test vectors match CTA WAVE specific format, and content options defined in sparse matrices.
- checks CMAF conformance using the [DASH-IF conformance validator](http://conformance.dashif.org).

Please refer to [that repository](https://github.com/nicholas-fr/test-content-validation) for details.



### 6. Create zip archives and generate a database from batch configuration

In order to contribute content, test content archives and database should be generated:

```
tcgen export -v ./output -d ./database.json /path/to/mazzanine/dir ./profiles/config.csv
```
the command does the following:
- for all test vectors listed in `./profiles/batch-config.csv`, find the most recent batch in the `./output` directory.
- generate a zip archive of each test vector, in the test vector directory itself
- generate a `./database.json`. If `./database.json` already exists, it is patched

For details on available options use : `tcgen export --help`

Note: While it can patch an existing database, this command is not intended to update the [reference test content database](https://github.com/cta-wave/Test-Content) because it doesn't remove deprecated database entries.


### 7. Upload batch content

Uploading a batch uses the database file created at step 5:
```
tcgen upload -v ./output ./database.json
```

To instructions to **configure credentials**, and details on available options use : `tcgen upload --help`


After [uploading](https://dash.akamaized.net/WAVE/vectors/), a pull request should be opened to [update the test content database](https://github.com/cta-wave/Test-Content).


### 8. Download database content

To download test vectors listed in a database file, such as the [reference test content database](https://github.com/cta-wave/Test-Content):

```
tcgen download -v ./output ./database.json
```

For details on available options use : `tcgen download --help`


