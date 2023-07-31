#!/usr/bin/env python
"""
PDF wrangler for the Dungeons and Dragons 5 Edition Systems Reference Document

Doc for PyMuPDF v1.17.4 at 
https://web.archive.org/web/20200724120551/https://pymupdf.readthedocs.io/en/latest/intro.html

D&D 5E SRD at
https://dnd.wizards.com/resources/systems-reference-document
"""

# XXX Link monster to roll20? (no images)
#     See https://roll20.net/compendium/dnd5e/Monsters:Hobgoblin#content
# XXX Link monster to dndbeyond?
#     See https://www.dndbeyond.com/monsters/16925-hobgoblin
# XXX Add monster thumbnail? / token?
#     See https://www.dndbeyond.com/avatars/thumbnails/30788/731/1000/1000/638062180460224402.png
#     See https://5etools-mirror-1.github.io/bestiary.html#hobgoblin_mm  
#     See https://5etools-mirror-1.github.io/img/MM/Hobgoblin.png (token)
#     See https://5etools-mirror-1.github.io/img/bestiary/MM/Hobgoblin.jpg (from the images tab)
# XXX Any other thumbnails/links for other sections?

import os
import sys

import fitz

if (len(sys.argv) > 1):
    filepath = sys.argv[1]
    out_dir = os.path.dirname(filepath)

else:
    out_dir = "_out"
    filepath = os.path.join(out_dir, "SRD_CC_v5.1.pdf")

# Stack to keep track of the current section nesting level
font_size_stack = []
# 0-based level, name, 0-based page number, font size
toc = []
# From visual inspection of a dump of the pdf, the section titles have a minimum
# font size of 12, smaller sizes are used for normal text, footers, etc, ignore
# the latter when looking for toc entries (could also hook on the text color
# instead of the font size, sections seem to be color 9712948)
print "Reading pdf", filepath
section_title_min_font_size = 12
merged_text = ""
font_sizes = {}
with fitz.open(filepath) as pdf:
    for page in pdf:
        d = page.getText("dict")
        # .blocks [ .lines [ .spans [ { .color, .text, .font, .size } ] ] ]
        for block in d["blocks"]:
            line_font_size = None
            for line in block["lines"]:
                for span in line["spans"]:
                    
                    font_size = span["size"]
                    if (font_size < section_title_min_font_size):
                        line_font_size = font_size
                        continue

                    span_text = span["text"]

                    # Some section titles are split into several lines, eg
                    #   lines[0]["spans"][0]["text"] = "Using Ability "
                    #   lines[1]["spans"][0]["text"] = "Scores "
                    #
                    # Merge the text into a single toc entry by detecting
                    # contiguous lines with the same font size
                    #
                    # Note the trailing spaces on each line, the one at the end
                    # of the merged line needs to be removed, but not the ones
                    # in the middle
                    if (line_font_size == font_size):
                        # Merge with the previously inserted section
                        merged_text += span_text
                        toc[-1][1] = merged_text

                    else:
                        # Start a new section
                        line_font_size = font_size
                        # Undo section nesting levels by popping until font size
                        # in font_size_stack is greater or empty
                        while ((len(font_size_stack) > 0) and (font_size >= font_size_stack[-1])):
                            font_size_stack.pop()

                        merged_text = span_text
                        # 0-based level, name, 0-based page number, font size
                        
                        # XXX Using len(font_size_stack) as the nesting level
                        #     fails for sections that have missing parent
                        #     sections, eg 
                        #       Monsters (M)->Kobold 
                        #     but
                        #       Monsters (H)->Hags->Green Hag
                        #     Also happens in the character classes where
                        #       Druid -> Class Features -> <missing> -> Hit Points
                        #       Druid -> Class Features -> Spellcasting -> Cantrips
                        #     So Hit Points should be at the same level as
                        #     Cantrips but it ends at the same level as 
                        #     Spellcasting
                        #
                        #     Another option would be to examine the document
                        #     and find out the font size for each nesting level
                        entry = [len(font_size_stack), merged_text, page.number, font_size]
                        toc.append(entry)

                        font_size_stack.append(font_size)

    out_filename, out_ext  = os.path.splitext(os.path.basename(filepath))
    out_filedir = os.path.dirname(filepath)
    out_filepath = os.path.join(out_filedir, out_filename + "_TOC" + out_ext)
    print "Generating pdf with TOC", out_filepath
    # Ignore the existing TOC, the CC version has dummy filename entries, the
    # OGL version is empty
    pdf_toc = []
    for entry in toc:
        # Do text cleanup of chars that don't show properly on the toc
        text = entry[1]
        ## print repr(text)
        for needle, replacement in [
            # Remove non-breaking space marker which renders incorrectly as a
            # visible symbol char on the toc, leave spaces next to the
            # non-breaking space marker since they separate words
            # Additionally, the CC SRD "Legal Information" section is
            #       "Legal\xa0Information\xa0"
            # where the non-breaking space doesn't have regular spaces around,
            # so first replace entries with spaces around with a space and then
            # replace any remaining entries (probably just Legal Information)
            # without space with a space too
            (u" \u00a0", " "), 
            (u"\u00a0", " "), 
            # Remove carriage return
            (u"\r", ""),
            # Remove tabs
            ("\t", ""),
            # Replace the sequence <hyphen minus, soft hyphen, hyphen minus> 
            # with just hyphen minus in eg
            #   "Half-\u00ad\u2010Red\t\r \u00a0Dragon\t\r \u00a0Veteran\t\r \u00a0",
            #   "Saber-\u00ad\u2010Toothed\t\r \xa0Tiger\t\r \xa0'
            # Those render as single hyphen on the document's body but show as
            # three hyphens on the toc (not clear this is a bug in PyMuPDF not
            # supporting tocs with those or SumatraPDF not showing those
            # properly in the toc)
            (u"-\u00ad\u2010", "-"),
        ]:
            text = text.replace(needle, replacement)
        
        # Strip trailing chars left when removing non-break space at the end of
        # line
        entry[1] = text.strip()
        
        # entry[1] = entry[1].replace(u"\u00a0", "").replace("\r", "").replace("\t", "").strip()
        # 1-based level, name, 1-based page
        ## print repr(entry)
        pdf_toc.append([entry[0]+1, entry[1], entry[2]+1])

    pdf.setToC(pdf_toc)
    pdf.save(out_filepath, deflate=True)