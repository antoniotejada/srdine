# srdine

Pronounced sardine. A tool to finagle the [Dungeons and Dragons 5e Systems Reference Document](https://dnd.wizards.com/resources/systems-reference-document).

The original SRD from Wizards of the Coast is missing the table of contents, for now this tool generates that table of contents, but it can also serve as a base to do more processing.

## Features
- Generates a new pdf with the table of contents plus all the original content

## Requirements
- Python 2.7
- PyMuPDF 1.16.17
- [Dungeons and Dragons 5e OGL SRD](http://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf) or [Dungeons and Dragons 5e CC SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf).

## Usage
1. Download the [Dungeons and Dragons SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf)
1. Invoke `srdine.py` with the location of the SRD pdf, eg
    ```bat
    >srdine.py _out\SRD-OGL_V5.1.pdf
    Reading pdf _out\SRD-OGL_V5.1.pdf
    Generating pdf with TOC _out\SRD-OGL_V5.1_TOC.pdf
    ```
    it will generate the file `_out\SRD-OGL_V5.1_TOC.pdf`
    
## Todo
- Fix the algorithm to understand missing parents
- Export monsters to JSON?
- Add monster links to dndbeyond/5etools/roll20/other?
- Add monster thumbnails?