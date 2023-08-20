# srdine

/saar.**deen**/ A tool to finagle the [Dungeons and Dragons 5e Systems Reference Document](https://dnd.wizards.com/resources/systems-reference-document).

The original SRD from Wizards of the Coast is missing the table of contents, for now this tool generates that table of contents, but it can also serve as a base to do more processing.

## Screenshots

### Table of contents and document with monster thumbnails

![image](https://github.com/antoniotejada/srdine/assets/6446344/fa53fecb-d113-4f6d-9ccd-de6bc8e078ed)


### Table of contents with indices by monster attributes

![image](https://github.com/antoniotejada/srdine/assets/6446344/60542985-e886-418c-ae21-efc85b4fc5ba)

### HTML monster page 

![image](https://github.com/antoniotejada/srdine/assets/6446344/9d12f590-7bb6-4d23-9e3b-10d316269429)


## Features
- Generates a new pdf with the table of contents plus all the original content and monster thumbnails from dndbeyond
- Generates extra table of content monster sections indexed by size, CR, type
- Generates HTML monster pages using dndbeyond template
- Generates JSON file of monsters
- Generates JSON file of the document
- Generates markdown file of the document (preliminary)

## Requirements
- Python 2.7
- PyMuPDF 1.16.17
- [Dungeons and Dragons 5e OGL SRD](http://media.wizards.com/2016/downloads/DND/SRD-OGL_V5.1.pdf) or [Dungeons and Dragons 5e CC SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf).

## Usage
1. Download the [Dungeons and Dragons SRD](https://media.wizards.com/2023/downloads/dnd/SRD_CC_v5.1.pdf)
1. In order to generate monster thumbnails, download `monster.json` from releases and place it in the same directory as the pdf
1. Invoke `srdine.py` with the location of the SRD pdf, eg
    ```bat
    >srdine.py _out\SRD-OGL_V5.1.pdf
    Reading json _out\monsters.json
    Loaded 317 monsters
    Reading pdf _out\SRD_CC_v5.1.pdf
    Generating TOC
    Generating pdf with TOC _out\SRD_CC_v5.1_TOC.pdf
    Adding monster thumbnails to _out\SRD_CC_v5.1_TOC.pdf
    Writing pdf _out\SRD_CC_v5.1_TOC.pdf
    Writing _out\SRD_CC_v5.1.json
    Writing _out\SRD_CC_v5.1.md
    Generating 317 monster _out\monsters.json
    Downloading resources for html monster pages
    Downloading template resources
    Generating 317 html monster pages at _out\html
    ```
    it will generate the file `_out\SRD-OGL_V5.1_TOC.pdf`
    
## Todo
- Better markdown output
- Spell parsing?