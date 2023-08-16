# srdine

/saar.**deen**/ A tool to finagle the [Dungeons and Dragons 5e Systems Reference Document](https://dnd.wizards.com/resources/systems-reference-document).

The original SRD from Wizards of the Coast is missing the table of contents, for now this tool generates that table of contents, but it can also serve as a base to do more processing.

## Features
- Generates a new pdf with the table of contents plus all the original content and monster thumbnails from dndbeyond
- Generates extra table of content monster sections indexed by size, CR, type
- Generates HTML monster pages using dndbeyond template
- Generates JSON file of monsters
- Generates JSON file of the document
- Generates markdown file of the document (preliminary)


## Screenshots

### Table of contents and document with monster thumbnails

![image](https://github.com/antoniotejada/srdine/assets/6446344/fa53fecb-d113-4f6d-9ccd-de6bc8e078ed)


### Table of contents with indices by monster attributes

![image](https://github.com/antoniotejada/srdine/assets/6446344/6fbfeed7-0af3-4101-b6ae-24f6329c5439)

### HTML monster page 

![image](https://github.com/antoniotejada/srdine/assets/6446344/9d12f590-7bb6-4d23-9e3b-10d316269429)


## Requirements
- Python 2.7
- PyMuPDF 1.16.17
- [Dungeons and Dragons 5e OGL SRD](http://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf) or [Dungeons and Dragons 5e CC SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf).

## Usage
1. Download the [Dungeons and Dragons SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf)
1. in order to generate monster thumbnails, place monsters.json in the same directory as the pdf
1. Invoke `srdine.py` with the location of the SRD pdf, eg
    ```bat
    >srdine.py _out\SRD-OGL_V5.1.pdf
    Reading pdf _out\SRD-OGL_V5.1.pdf
    Generating pdf with TOC _out\SRD-OGL_V5.1_TOC.pdf
    ```
    it will generate the file `_out\SRD-OGL_V5.1_TOC.pdf`
    
## Todo
- Better markdown output
- Spell parsing?