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
# XXX Any other thumbnails/links for other sections?
# XXX Export spells to JSON?
# XXX Export dndbeyond-style html monsters to PDF with a toc indexed by multiple stats

import time
import errno
import io
import json
import os
import random
import re
import string
import sys
import time
import urllib2
import urlparse

import fitz


# Lifted from cgi.escape, no need to bring the whole module for just this
# function
def escape_html(s, quote=None):
    '''Replace special characters "&", "<" and ">" to HTML-safe sequences.
    If the optional flag quote is true, the quotation mark character (")
    is also translated.'''
    s = s.replace("&", "&amp;") # Must be done first!
    s = s.replace("<", "&lt;")
    s = s.replace(">", "&gt;")
    if (quote):
        s = s.replace('"', "&quot;")
    return s


def makedirs(dirpath):
    try:
        os.makedirs(dirpath)

    except OSError as e:
        if (e.errno != errno.EEXIST):
            raise


def parse_int(s):
    i = None
    try:
        i = int(s)
    except (TypeError, ValueError):
        pass

    return i

all_cookies = {}

def http_get(url, filepath, referrer=None, overwrite=False, throttle=False):
    ## print "http_get", repr(url)
    # Note urlretrieve will download and save the body in the cases of servers
    # that fill the body with some error message when returning a 404.
    # Don't use urllretrieve, use urlopen, check the code and download. This has
    # the disadvantage that it will always hit the network for missing content
    if (overwrite or (not os.path.exists(filepath))):
        # Throttle otherwise requests get blacklisted for spamming the server
        # 1.25 is known to throttle after a bunch of requests, same as 1.5
        if (throttle):
            time.sleep(2)

        req = urllib2.Request(url)
        # dndbeyond will respond 403 without user agent, note user-agents can be
        # blacklisted for hours, need to do some change to the user-agent string
        # although it doesn't help that much and still gets blacklisted after a
        # few downloads
        user_agent_header = 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/%d.0.0.%d Safari/%d.%d' % (
            random.randint(80, 120), random.randint(0, 255), 
            random.randint(200, 600), random.randint(1, 25)
        )
        ##print "user_agent_header", user_agent_header
        req.add_header('user-agent', user_agent_header)
        #req.add_header('accept-encoding', "accept-encoding: gzip, deflate, br")
        req.add_header('accept-language', "accept-language: en-US,en;q=0.9")
        req.add_header('accept', 'text/html,application/xhtml+xml,application/xml;q=0.9,image/webp,image/apng,*/*;q=0.8,application/signed-exchange;v=b3;q=0.7')
        
        
        parsed_url = urlparse.urlparse(url)
        # Send referrer to appease the blacklisting, not clear it helps
        if (referrer is None):    
            referrer = parsed_url.scheme + "://" + parsed_url.hostname + parsed_url.path
        ## print "referer_header", referer_header
        req.add_header('referer', referrer)
        
        # Send cookies to appease the blacklisting, not clear it helps but it
        # doesn't hurt
        try:
            cookies = all_cookies[parsed_url.hostname]

        except KeyError:
            cookies = {}
            all_cookies[parsed_url.hostname] = cookies
        if (len(cookies) > 0):
            cookie_header = string.join(["%s=%s" % (name, value) for name, value in cookies.iteritems()], "; ")
            ## print "cookie_header", cookie_header
            req.add_header('cookie', cookie_header)
        
        f_in = urllib2.urlopen(req)
        if (f_in.getcode() == 200):
            # Set-Cookie: Geo=...; path=/; domain=.dndbeyond.com; SameSite=None; Secure;\r\n
            for cookie_header in f_in.info().getallmatchingheaders("set-cookie"):
                ## print "jarring cookie", cookie_header
                _, cookie_content = cookie_header.split(":", 1)
                cookie_name_value, _ = cookie_content.split(";", 1)
                cookie_name, cookie_value = cookie_name_value.split("=", 1)
                cookies[cookie_name] = cookie_value
            ## print "current cookies", cookies
            
            # Set-Cookie:  AWSELB=17A59...;PATH=/;MAX-AGE=3600
            print "Downloading", repr(url), "to", repr(filepath)
            # XXX Ignoring the url when naming the file will replicate images
            #     that are the same for all monsters (eg ancient vs. adult
            #     dragons), fix?
            with open(filepath, "wb") as f_out:
                f_out.write(f_in.read())

        else:
            print "Skipping error", f_in.getcode(), url
        
        f_in.close()

    else:
        ## print "Skipping already downloaded", url, "to", filepath
        pass

def filename_from_monster_name(name):
    return urllib2.quote(name.encode("utf-8"), "")

def download_monster_images(monster, force = False):
    """
    https://www.dndbeyond.com/monsters/16925-hobgoblin
    https://www.dndbeyond.com/avatars/thumbnails/30788/731/1000/1000/638062180460224402.png
    https://www.dndbeyond.com/avatars/thumbnails/0/388/100/100/636252781431307548.jpeg
    https://www.dndbeyond.com/monsters?filter-search=hobgoblin
    https://www.dndbeyond.com/monsters?filter-search=hobgoblin&filter-source=1
    It has a jpg avatar and a full png image

    <div class="info" data-isopen="false" data-isloading="false" data-isloaded="false" data-type="monsters" data-slug="16925-hobgoblin">
    <div class="row monster-icon">
            <a href="https://www.dndbeyond.com/avatars/thumbnails/30788/731/1000/1000/638062180460224402.png" data-lightbox="16925-hobgoblin" data-title="&lt;a target=&#x27;_blank&#x27; href=&#x27;https://www.dndbeyond.com/avatars/thumbnails/30788/731/1000/1000/638062180460224402.png&#x27; class=&#x27;link link-full&#x27;&gt;View Full Image&lt;/a&gt;">
                <div class="image" style="background-image: url('https://www.dndbeyond.com/avatars/thumbnails/0/388/100/100/636252781431307548.jpeg');"></div>
            </a>
    </div>
    """
    ##print "download_monster_images", repr(monster["name"])

    name = monster["name"]
    safe_name = filename_from_monster_name(name)
    query_url = "https://www.dndbeyond.com/monsters?filter-search=%s&filter-source=1&_=%d" % (
        urllib2.quote(name.encode("utf-8"), ""), random.randint(1, 999999))

    # This can cause 403 forbidden and cause the local ip/user-agent to be
    # blacklisted until using a browser to dndbeyond.com and click on I'm not a
    # robot button
    if ("link" not in monster) and force:
        filepath = os.path.join(out_cache_dir, "%s.html" % safe_name)
        http_get(query_url, filepath, throttle=True)
        with open(filepath, "r") as f:
            page = f.read()
            # There can be multiple monsters returned by the query above and they
            # are sorted by name so a straight search for the first thumb/image can
            # return the wrong results (eg Ogre Zombie instead of Zombie).
            # Split the page into each monster and search for the one that has the
            # strict name, pick the first otherwise.
            monster_info = page
            infos = page.split('<div class="info"')
            # The first split is the start of the page upto the first monster
            # information exclusive, skip
            if (len(infos) > 1):
                for candidate_info in infos[1:]:
                    # <a class="link" href="/monsters/17077-zombie"  >Zombie</a>
                    m = re.search(r'<a class="link" href="([^"]*)".*>%s<' % name, candidate_info, re.IGNORECASE)
                    if (m is not None):
                        monster_info = candidate_info
                        monster["link"] = "https://www.dndbeyond.com%s" % m.group(1)
                        break

            m = re.search(r"url\('(https://www.dndbeyond.com/avatars/thumbnails[^']+)'\)", monster_info)
            if (m is not None):
                img_url = m.group(1)
                monster["thumbnail"] = img_url

            m = re.search(r"(https://www.dndbeyond.com/avatars/thumbnails[^\"]*)", monster_info)
            if (m is not None):
                img_url = m.group(1)
                monster["image"] = img_url
        
    # Images don't need to be throttled as they always return 200 OK even if the
    # html returned 403 forbidden
    if ("image" in monster):
        img_url = monster["image"]
        img_filepath = os.path.join(out_cache_dir, ("%s_img" % safe_name) + os.path.splitext(img_url)[1])
        http_get(img_url, img_filepath, referrer=query_url)

    if ("thumbnail" in monster):
        img_url = monster["thumbnail"]
        img_filepath = os.path.join(out_cache_dir, ("%s_thumb" % safe_name) + os.path.splitext(img_url)[1])
        http_get(img_url, img_filepath, referrer=query_url)


def download_template_resources():
    urls_dirnames = [
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/css/compiled.css", "css"),
        
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/images/expanded-listing-item-bottom-border.png", "images"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/images/background_texture.png", "images"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/images/mon-summary/stat-bar-book.png", "images/mon-summary"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/images/mon-summary/paper-texture.png", "images/mon-summary"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/images/mon-summary/stat-block-top-texture.png", "images/mon-summary"),
        
        ("https://www.dndbeyond.com/file-attachments/0/579/stat-block-header-bar.svg", "images"),
        
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/fonts/MrsEavesSmallCaps.ttf", "fonts"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/fonts/ScalaSansOffc-Ita.ttf", "fonts"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/fonts/ScalaSansOffc-Bold.ttf", "fonts"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/fonts/ScalaSansOffc.ttf", "fonts"),
        ("https://www.dndbeyond.com/content/1-0-2552-0/skins/waterdeep/fonts/ScalaSansOffc-BoldIta.ttf", "fonts"),
    ]
    print "Downloading template resources"

    for url, dirname in urls_dirnames:
        dirpath = os.path.join(out_html_dir, dirname)
        makedirs(dirpath)
        http_get(url, os.path.join(dirpath, os.path.basename(url)))
    
    # make google fonts reference absolute since trying to hit the local
    # filesystem and failing causes stalls of seconds
    css_filepath = os.path.join(out_html_dir, "css", "compiled.css")
    with open(css_filepath, "r") as f:
        data = f.read()
        data = data.replace("//fonts.googleapis.com", "https://fonts.googleapis.com")

    with open(css_filepath, "w") as f:
        f.write(data)

def cleanup_text(text, strictly_necessary = True):
    # Remove non-breaking space marker which renders incorrectly as a visible
    # symbol char on the toc, leave spaces next to the non-breaking space marker
    # since they separate words
    # Additionally, the CC SRD "Legal Information" section is
    #       "Legal\xa0Information\xa0"
    # where the non-breaking space doesn't have regular spaces around, so first
    # replace entries with spaces around with a space and then replace any
    # remaining entries (probably just Legal Information) without space with a
    # space too
    # Remove carriage return
    # Remove tabs
    text = text.replace(u" \u00a0", " ").replace(u"\u00a0", " ").replace("\r", "").replace("\t", "")
    # Replace the sequence <hyphen minus, soft hyphen, hyphen minus> with just
    # hyphen minus in eg
    #   "Half-\u00ad\u2010Red\t\r \u00a0Dragon\t\r \u00a0Veteran\t\r \u00a0",
    #   "Saber-\u00ad\u2010Toothed\t\r \xa0Tiger\t\r \xa0'
    # Those render as single hyphen on the document's body but show as three
    # hyphens on the toc and in HTML (not clear this is a bug in PyMuPDF not
    # supporting tocs with those or SumatraPDF not showing those properly in the
    # toc)
    text = text.replace(u"-\u00ad\u2010", "-")
    if (not strictly_necessary):
        text = text.replace(u"\u2019","'")
        # Left/right double quotation
        text = text.replace(u"\u201c", '"').replace(u"\u201d", '"')
        # Non breaking hyphen
        text = text.replace(u"\u2011", "-")
        text = text.replace(u"\u2212", "-")
        # bullet
        text = text.replace(u"\u2022", "-")
        # m-dash
        text = text.replace(u"\u2014", "-")
    # Strip trailing chars left when removing non-break space at the end of
    # line    
    text = text.strip()
    return text


def generate_html_from_template(templatepath, data, filepath):
    """
    Small template engine with
    - single-pass parsing
    - loops
    - conditionals
    - control flow nesting (conditionals, loops, mixed)
    - struct-like expressions

    <!--$ expr -->    If expr is an iterator over a dict, return the value
    <!--$ #expr -->   If expr is an iterator over a dict, return the key
    <!--$ %expr -->   If expr is not an aggregate (list, dict) return None, otherwise return len(expr)
    
    where expr can be a nested dict dereferencing expression eg, name.key1.key2.key3
    <!--$ name.key1.key2 ->     Equivalent to name[key1][key2] in python

    <!--$ if lhs op rhs --> where 
        op one of ==, !=, <,<=,>,>?, startswith
        lhs is expr
        rhs is one of expr, number or string literal inside double quotation marks
    <!--$ else -->
    <!--$ endif -->

    <!--$ for it:expr -->  where
        expr is a list or a dict
        it can be used in the loop body to access the iterator value
        #it can be used in the loop body the iterator key/index
    <!--$ endfor -->

    """
    
    def deref(s, locals):
        if (s.startswith("#")):
            quantifier = "#"
            s = s[1:]
        elif (s.startswith("%")):
            quantifier = "%"
            s = s[1:]
        else:
            quantifier = None

        names = s.split(".")
        
        ret = None
        for local in reversed(locals):
            
            if (names[0] not in local):
                continue

            ret = local
            for name in names:
                ret = ret.get(name, None)
                
                if (ret is None):
                    break
                
                elif (isinstance(ret, tuple) and (name is names[-1]) and (quantifier is None)):
                    # Return the item of iteritems
                    ret = ret[1]
            break
            
        if ((ret is not None) and (quantifier is not None)):
            assert quantifier in ["#", "%"]
            if (quantifier == "#"):
                # Return the key of iteritems
                ret = ret[0]

            elif (quantifier == "%"):
                
                if (isinstance(ret, tuple)):
                    # If it's an iteritems, return the number of elements of
                    # the item, but return None for eg strings
                    if (isinstance(ret[1], (list, dict))):
                        ret = len(ret[1])

                    else:
                        ret = None

                else:
                    ret = len(ret)

        return ret

    def output(f, o, do_html_escaping=False):
        # Both strings and numbers come through here, make sure they are strings
        # as needed by functions below
        s = unicode(o)
        
        # XXX The template is producing one empty line due to the indentation of
        #     a directive that disables the output. If multiple of such
        #     directives follow each other, you can have gaps in the produced
        #     HTML
        #     Ideally those should be removed, but can't tell the difference
        #     between that kind of indentation and the separation necessary for
        #     layout between directives and html (ie can't remove the carriage
        #     return or space between a directive and text in the html or
        #     between directives).
        #     Another option is to collapse all whitespace into a single one but
        #     it's more trouble than it's worth
        
        if (do_html_escaping):
            s = escape_html(s)
        # Assume output is utf-8
        f.write(s)

    with io.open(templatepath, "r", encoding="utf-8") as f:
        template = f.read()

    with io.open(filepath, "w", encoding="utf-8") as f:
        # stack of scopes, first element is the fields of the data variable
        # passed in, later elements store the loop iterator and loop information
        # of different loop nesting levels
        locals = [{ key: value for key, value in data.iteritems() }]

        # Add a few beautified versions of existing fields
        if ("xp" in locals[0]):
            xp = unicode(locals[0]["xp"])[::-1]
            locals[0]["xp"] = string.join([xp[i*3:i*3+3] for i in xrange((len(xp) + 2) / 3)], ",")[::-1]

        if ("cr" in locals[0]):
            cr = locals[0]["cr"]
            locals[0]["cr"] = "1/%d" % int(1 / cr) if (0 < cr < 1) else int(cr)

        locals[-1]["header"] = {
            "author": os.path.basename(sys.argv[0]), 
            "date": time.strftime("%a, %d %b %Y %H:%M:%S +0000", time.gmtime())
 }
        
        start = 0
        t = template
        # Counters for the current level and the last enabled level. This allows
        # keeping track of whether output should be ignored because of
        # traversing the false branch of an if/else. This is also used in order
        # to ignore the output on the first iteration of a for loop over an
        # empty list.
        # A level is essentially the number of nested ifs at a given point in 
        # the execution of the template:
        # - The current level is incremented on every if and decremented on
        #   every endif
        # - The enabled level is incremented if:
        #   - an if is found and the current level is enabled and the if
        #     condition is true 
        #   - an else is found and the if condition was false, this can be found
        #     because the delta between the current level and the last enabled
        #     level is 1 (ie the level was enabled before executing the if and 
        # This works for as many nesting levels as the range of Python numbers

        # XXX Note this counter scheme doesn't support "elif" because when an
        #     "elif" is found, in the general case it cannot tell if there was a
        #     previous if/elif condition at this enable level whose condition
        #     was true (and the information needs to be preserved when nesting
        #     levels). In order to support elif:
        #     - a stack scheme could be used (so the information is preserved
        #       when nesting)
        #     - The number of elifs in a given level could be limited to N, so
        #       the counter would be incremented by N instead of 1 and, if the
        #       last enabled level is less than a distance of from the current,
        #       it means that there was an if/elif enabled in this if/elif/else
        #       block (essentially the current method is this method with N=1 or
        #       a single "elif" ie an else)
        last_enabled_level = 0
        current_level = 0
        r = re.compile(r"""
            <!--\$
                \s*
                (
                    # returns keys if iterating over a dict, index otherwise
                    # access the key/index with "#name", access the value with
                    # just "name"
                    (?P<for>for)\s+(?P<item>\w+)\s*:\s*(?P<list>\w+(\.\w+)?)
                    |
                    endfor
                    |
                    # No operation is equivalent to left_reference != None
                    (?P<if>if)\s+
                        (?P<left_reference>[#%]?\w+(\.\w+)*)
                        (\s*
                            (?P<operation>==|!=|<=|>=|<|>|startswith)\s*
                            (
                                (?P<right_string>\"[^"]*\")|
                                (?P<right_number>(\d+(\.\d+))*)|
                                (?P<right_reference>[#%]?\w+(\.\w+)*)
                            )
                        )?
                    |
                    else
                    |
                    endif
                    |
                    # name, name.field1.field2, #name (key), %name (length)
                    ([#%]?\w+(\.\w+)*)
                )
                \s*
            -->
            """, re.VERBOSE)

        while (True):
            m = r.search(t)
            if (m is None):
                break
            
            # Write whatever non-matching template text 
            if (last_enabled_level == current_level):
                output(f, t[:m.start()])

            # Skip over matched text 
            start += m.end()

            if (m.group("for") is not None):
                # Since it's a single pass parser, there's no way to jump to the
                # end of a for loop if there are no elements in the list, create
                # an enable level so lines can be ignored as they are read
                current_level += 1
                last_enabled_level += 1
                if (last_enabled_level == current_level):
                    list_name = m.group("list")
                    l = deref(list_name, locals)

                    if (len(l) == 0):
                        last_enabled_level -= 1

                    else:
                        iterator_name = m.group("item")
                        iterator = l.iteritems()
                        # Note start has already been incremented by m.end()
                        
                        # Isolate variables in this scope from the current scope
                        locals.append({})
                        for_info = { "start": start, "frame" : locals[-1], "iterator": iterator, "iterator_name": iterator_name }
                        locals[-1][iterator_name] = next(iterator)
                        # Using "for" to store the loop information is safe wrt
                        # variable name collisions since it could be regarded as a
                        # reserved word
                        locals[-1]["for"] = for_info
                    
            elif (m.group(1) == "endfor"):
                if (last_enabled_level == current_level):
                    # Increment the iterator, jump to start of loop
                    for_info = deref("for", locals)
                    iterator_name = for_info["iterator_name"]
                    iterator_value = next(for_info["iterator"], None)
                    
                    if (iterator_value is not None):
                        # Loop to the first instruction of the loop
                        for_info["frame"][iterator_name] = iterator_value
                        start = for_info["start"]
                    
                    else:
                        # Done with the loop, undo scope and enable level
                        locals.pop()
                        last_enabled_level -= 1
                        current_level -= 1

            elif (m.group("if") is not None):
                # Don't deref if not enabled
                enabled = (last_enabled_level == current_level)
                current_level += 1
                if (enabled):
                    left_reference = m.group("left_reference")
                    operation = m.group("operation")
                    left_value = deref(left_reference, locals)
                    if (operation is None):
                        condition = (left_value is not None)
                    
                    else:

                        right_reference = m.group("right_reference")
                        right_number = m.group("right_number")
                        right_string = m.group("right_string")
                        if (right_reference is not None):
                            right_value = deref(right_value, locals)
                        elif (right_number is not None):
                            right_value = float(right_number)
                        elif (right_string is not None):
                            right_value = right_string[1:-1]

                        if (operation == "=="):
                            condition = (left_value == right_value)
                        elif (operation == "!="):
                            condition = (left_value != right_value)
                        elif (operation == ">"):
                            condition = (left_value > right_value)
                        elif (operation == "<"):
                            condition = (left_value < right_value)
                        elif (operation == ">="):
                            condition = (left_value >= right_value)
                        elif (operation == "<="):
                            condition = (left_value <= right_value)
                        elif (operation == "startswith"):
                            condition = left_value.startswith(right_value)

                    if (condition):
                        last_enabled_level += 1


            elif (m.group(1) == "else"):
                assert current_level > 0, "else without if"
                
                if ((current_level - last_enabled_level) == 1):
                    last_enabled_level = current_level
                
                elif (current_level == last_enabled_level):
                    last_enabled_level -= 1

            elif (m.group(1) == "endif"):
                assert current_level > 0, "endif without if"
                
                current_level -= 1
                last_enabled_level = min(current_level, last_enabled_level)

            else:
                # Output expression
                if (last_enabled_level == current_level):
                    output(f, deref(m.group(1), locals), True)

            # Refresh the template substring after processing in case start was
            # updated eg by for loop
            t = template[start:]

        output(f, t)

def create_span_tokenizer(pages):
    state = {}
    
    state["next_token"] = next_span

    state["pages"] = pages
    state["page_index"] = state["block_index"] = state["line_index"] = state["span_index"] = 0
    d = pages[0].getText("dict")
    state["blocks"]  = d["blocks"]

    return state

def create_parser(tokenizer, grammar_filepath, process_token):
    state = {}

    # Tokenizing state
    state["tokenizer"] = tokenizer
    state["token"] = tokenizer["next_token"](tokenizer)

    # Parsing state
    state["process_token"] = process_token
    prods = load_grammar(grammar_filepath)
    state["prods"] = prods

    # User data for process_token
    state["data"] = { }
    
    return state


def load_grammar(filepath):
    """
    Grammar

    # comment
    prod :
        | subrule10 subrule11
        | subrule20 subrule21
        | { text == "string1" }
        | { text == "string2" }*

    quantifiers: * + ? 
    terminal symbols: { conditions } or {} (matches any)
    conditions: field == "string" or field == 1.0
    operations: == != > < >= <= startswith endswith 
    

    Tips

    - Do lists using the one or none quantifier "?"
        list: 
            | item list?

    - Since there's no tail recursion optimization / flattening, having lists
      with thousands of may cause stack overflow since every new element is a
      nested function call

    - If two rules in the same production intersect, put the specific rule first
      and the generic rule second (placing the specific second will cause to
      never hit)
        prod:
            | { text == "abcdefgh" }
            | { text startswith "abc" }
            | {}

    "abcdefgh" will trigger the first rule, while "abcdefghi" and "abcdefg" will
    both trigger the second rule, "ab" will trigger the third
    """
    prods = {}
    with open(filepath, "r") as f:
        def readline(f):
            while (True):
                l = f.readline()
                ll = l.strip()
                if ((l == "") or ((ll != "") and (not ll.startswith("#")))):
                    break
                ##print "empty", repr(ll)
                    
            ##print "readline", repr(l)
            return l, ll
            
        l, ll = readline(f)
        while (l != ""):
            prod_name = ll
            ##print "read prod", repr(prod_name)
            assert not prod_name.startswith("|")
            assert prod_name.endswith(":")
            prod_name = prod_name[:-1].strip()
            assert prod_name not in prods, "Duplicated production name " + prod_name
            
            l, ll = readline(f)
            rule = None
            rules = []
            prods[prod_name] = rules
            assert ll.startswith("|")
            while (True):
                if ((l == "") or (ll.endswith(":"))):
                    ##print "read rule", rule
                    break

                if (ll.startswith("|")):
                    if (rule is not None):
                        ##print "read rule", rule
                        pass
                    
                    rule = {}
                    rule["raw"] = ll[1:]
                    rules.append(rule)
                    
                else:
                    rule["raw"] += " " + ll

                l, ll = readline(f)

            for rule in rules:
                ##print "parsing rule" , rule
                subrules = []
                rule["subrules"] = subrules
                # XXX Needs proper quotation mark, colon and brace escaping
                #     (replace all those with the unicode-escaping, xml or
                #     such?)
                prev_subrule_end = 0
                for m in re.finditer(r"""
                    (
                        \s*
                        (
                            ({(?P<conditions>[^}]*)})|
                            (?P<prod>\w+)
                        )(?P<quant>\d+(-\d+)?|[*+?])?
                    )
                    """, rule["raw"], re.VERBOSE):

                    # Make sure there are no skips due to finditer skipping over
                    # an unmatched subrule
                    assert m.start() == prev_subrule_end, "Invalid subrule " + repr(rule["raw"][prev_subrule_end:m.start()])
                    prev_subrule_end = m.end()
                    
                    subrule = {}
                    ##print "parsing subrule", m.groupdict()

                    subrule["prod"] = m.group("prod")

                    # quant can be *+? or \d+ or \d+-\d+
                    quant = m.group("quant")
                    i = parse_int(quant)
                    # XXX Missing supporting ranges
                    if (i is not None):
                        quant = i
                    subrule["quant"] = quant

                    subrule["conditions"] = None
                    if (m.group("conditions") is not None):
                        conditions = []
                        # XXX Also allow value first and field second?
                        # XXX Allow operations between conditions 
                        # XXX Allow parenthesis
                        # XXX Allow escaped double quotes
                        # XXX Allow bitwise & operation for flags
                        prev_condition_end = 0
                        all_conditions = m.group("conditions")
                        for m in re.finditer(r"""
                            \s*
                            (?P<field>\w+)
                            \s*
                            (?P<op>startswith|endswith|notendswith|==|!=|>|<|<=|>=)
                            \s*
                            (?P<value>"[^"]*"|[+-]?\d+(\.\d+)?)
                            \s*
                            """, all_conditions, re.VERBOSE):

                            # Make sure there are no skips due to finditer
                            # skipping over an unmatched condition
                            assert m.start() == prev_condition_end, "Invalid condition " + repr(all_conditions[prev_condition_end:m.start()])
                            prev_condition_end = m.end()

                            condition = m.groupdict()
                            value = condition["value"]
                            if (value.startswith('"')):
                                value = value[1:-1]
                                condition["value"] = unicode(value, "unicode-escape")

                            else:
                                condition["value"] = float(value)
                            conditions.append(condition)
                        assert prev_condition_end == len(all_conditions), "Invalid condition " + repr(all_conditions[prev_condition_end:])
                        
                        subrule["conditions"] = conditions

                    ##print "parsed subrule", subrule
                    subrules.append(subrule)
                assert prev_subrule_end == len(rule["raw"]), "Invalid subrule " + repr(rule["raw"][prev_subrule_end:])

                ##print "parsed rule", rule

    # Perform some sanity checks
    for prod in prods.values():
        ##print "prod", prod
        for rule in prod:
            ##print "rule", rule
            for subrule in rule["subrules"]:
                p = subrule.get("prod")
                assert p is None or (p == "lambda") or p in prods, "Prod %s not in prods" % p

    return prods

def next_span(state):
    """
    Tokenizer frontend for the pdf's getText function, returns the next
    available span in the document or None if no more available.

    Takes care of moving to the next line, block or page to get to the next
    span, skipping any "whitespace"
    """
    pages = state["pages"]
    page_index = state["page_index"]
    page = pages[page_index]
    block_index = state["block_index"]
    line_index = state["line_index"]
    span_index = state["span_index"]
    
    skip_next_spans = 0
    while (True):
        # Consume whitespace spans and return the first nonwhitespace

        # .blocks [ .lines [ .spans [ { .color, .text, .font, .size } ] ] ]
        blocks = state["blocks"]
        block = blocks[block_index]
        lines = block["lines"]
        line = lines[line_index]
        spans = line["spans"]

        if (span_index >= len(spans)):
            span_index = 0
            line_index += 1

            if (line_index >= len(lines)):
                line_index = 0
                block_index += 1

                if (block_index >= len(blocks)):
                    block_index = 0
                    page_index += 1

                    if (page_index >= len(pages)):
                        span = None
                        break

                    page = pages[page_index]
                    d = page.getText("dict")
                    state["blocks"] = d["blocks"]
                    state["page_index"] = page_index
                
                state["block_index"] = block_index

            state["line_index"] = line_index

        span = state["blocks"][block_index]["lines"][line_index]["spans"][span_index]

        if (span["text"] == u"System\t\r \u00a0Reference\t\r \u00a0Document\t\r \u00a05.1\t\r \u00a0"):
            # Skip footer and page number, note the footer is one line and the
            # page number and some whitespace in another, it's easier to skip
            # the next two spans than fiddling with the indices here that can
            # cause out of index access because it's at the end of the block for
            # this page
            # "color": 0, "flags": 4, "font": "LUFRKP+Calibri", "size": 10.800000190734863, "text": "System\t\r \u00a0Reference\t\r \u00a0Document\t\r \u00a05.1\t\r \u00a0"
            # "color": 0, "flags": 20, "font": "DXJJCX+GillSans-SemiBold", "size": 10.800000190734863, "text": "3"
            # "color": 0, "flags": 4, "font": "LUFRKP+Calibri", "size": 10.800000190734863, "text": "\t\r \u00a0"
            skip_next_spans = 2
            span_index += 1
            continue

        if (skip_next_spans > 0):
            skip_next_spans -= 1
            span_index += 1
            continue

        # Sometimes there's empty text like
        # "font": "WWROEK+Calibri-Bold", "size": 9.84000015258789,  "text": "\t\r \u00a0"
        # ignore
        if (span["text"].strip() == ""):
            span_index += 1
            continue
    
        # Somne have garbage spaces or dot 
        # But keep it for Kraken, Mummy and Unicorn since they need the comma separator
        # have garbage text with this font after the
        # size, ignore
        if ((span["font"] == "XPUSJH+ScalaSansOffc-BoldIta") and (span["text"] != ", ")):
            span_index += 1
            continue
        
        # Place text in raw, cleanup the text in text
        span["raw"] = span["text"]
        span["text"] = cleanup_text(span["text"])
        span["page"] = page_index + 1

        span_index += 1
        state["span_index"] = span_index
        
        
        break

    ##print "next_span", repr(span)
    return span

def token_matches(token, conditions):
    if (token is None):
        return False

    match = True
    for condition in conditions:
        field, op, value = condition["field"], condition["op"], condition["value"]
        
        token_value = token[field]

        if (op == "=="):
            match = match and (token_value == value)
        elif (op == "!="):
            match = match and (token_value != value)
        elif (op == ">="):
            match = match and (token_value >= value)
        elif (op == ">"):
            match = match and (token_value > value)
        elif (op == "<="):
            match = match and (token_value <= value)
        elif (op == "<"):
            match = match and (token_value < value)
        elif (op == "startswith"):
            match = match and (token_value.startswith(value))
        elif (op == "endswith"):
            match = match and (token_value.endswith(value))
        elif (op == "notendswith"):
            match = match and (not token_value.endswith(value))

        # XXX Missing some inter condition operation (and, or, parenthesis)
        # XXX Missing "not" unary operator so things like not endswith can
        #     be done
        if (not match):
            break

    return match

def parse(state, prod_name):
    """
    Given the grammar and the tokenizer, performs recursive descent parsing
    """
    prods = state["prods"]
    process_token = state["process_token"]
    next_token = state["tokenizer"]["next_token"]
    prod = prods[prod_name]
    rules = prod
    
    accepted = False
    for rule in rules:
        subrules = rule["subrules"]
        for subrule in subrules:
            new_prod_name = subrule.get("prod", None)
            quant = subrule.get("quant", None)

            accepted = True
            accept_number = 0
            while (accepted):
                token = state["token"]
                if (new_prod_name is None):
                    # Terminal symbol, try to match against token
                    conditions = subrule.get("conditions", None)
                    # Field None means {} which matches anything
                    match = token_matches(token, conditions)
                    accepted = ((token is not None) and match)
                    
                    if ((token is not None) and (len(conditions) > 0) and match):
                        ##print "real match", prod_name
                        process_token(prod_name, token, state["data"])
                    
                    if (accepted):
                        state["token"] = next_token(state["tokenizer"])
                        accept_number += 1

                elif (new_prod_name == 'lambda'):
                    # Accept with no token consumption, this is equivalent to
                    # using the "?" quantifier plus some non-accepting state, eg
                    # "{text != text}?"

                    # XXX Remove since it's redundant with the ? quantifier? but
                    #     there's no trivial way of expressing a universal
                    #     non-accepting state, allow None as token expression
                    #     and then lambda will be equivalent to "{ None }?"
                    accepted = True

                else:
                    # Non terminal, recurse
                    # XXX This should flatten tail recursion

                    # XXX Even without flattening, doing manual stack handling
                    #     would help enough to not overflow the stack/memory?
                    
                    # XXX Should be able to flatten last subrule from the last
                    #     rule, still needs to push accept_number and quant?
                    
                    # XXX What about if the recursion is to a different
                    #     production?
                    
                    # XXX May be able to flatten last subrule of any rule by 
                    #     pushing the rule index into a stack?
                       
                    ## if ((rule is rules[-1]) and (subrule is subrules[-1]) and (prod_name == new_prod_name)):
                    ##    print "tail recursion", prod_name
                        
                    accepted = parse(state, new_prod_name)
                
                if (quant is None):
                    break

                elif ((quant == "*") and (not accepted)):
                    # "*" quantifier accepts with no matching, without token
                    # consumption, otherwise done with this subrule
                    accepted = True
                    break
                
                elif ((quant == "+") and (accept_number >= 1) and (not accepted)):
                    # "+" quantifier accepts with at least one matching
                    accepted = True
                    break

                elif ((quant == "?") and ((accept_number == 1) or (not accepted))):
                    # "?" quantifiers accepts with one or none matching
                    accepted = True
                    break
            
                elif (isinstance(quant, int) and (accept_number == quant)):
                    # numeric quantifier accepts with exactly the number of
                    # matches
                    break
                
            # Part of the subrule fails, go to the next rule
            if (not accepted):
                break

        # Rule was accepted, done
        if (accepted):
            ##print "accepted", prod_name
            break

    return accepted

def parse_wrapper(state):
    # XXX Temporary solution for stack overflow while there's no tail recursion
    #     flattening
    while (state["token"] is not None):
        parse(state, "start")

def process_span(prod_name, token, data):
    
    def upsert(d, field, value, separator=" "):
        # Update appending to d[field] or insert if field doesn't exist in d
        
        # This is necessary since
        # - process gets called once per terminal symbol, receiving the token
        #   accepted by that terminal symbol 
        # - description types can be split across lines/blocks/spans (ie across
        #   terminal symbols)
        # - this needs to accumulate the description type in case it was split
        # - process doesn't get called for non-terminal, so it's hard to collect
        #   the called for terminal symbols, but  when there's a quantifier,
        #   should it return all the spans?
        # - Should process be called for non-terminal symbols?

        # Another option would be for process to receive an array of spans
        # (necessary for productions with multiple terminal symbols or for
        # terminal symbols with a quantifier) but sounds expensive and, if
        # applied to non terminal symbols, that would make the initial
        # non-terminal symbol receive all the spans)

        try:
            d[field] += separator + value
        except KeyError:
            d[field] = value

    span = token
    monsters = data.get("monsters", None)
    
    if (monsters is None):
        monsters = []
        data["monsters"] = []

    if (prod_name == "monster_name"):
        monsters.append({ "name" : cleanup_text(span["text"]), "page" : span["page"], "bbox" : span["bbox"] })
        data.pop("acc_monster_size", None)
        data.pop("acc_armor_class", None)

    elif (prod_name == "monster_size"):
        # Parse "size type (subtype), alignment" eg
        #   Large beast, unaligned
        #   Medium monstrosity, neutral evil
        #   Medium swarm of Tiny beasts, unaligned 
        #   Medium humanoid (human, shapechanger), neutral good
        #   Medium humanoid (goblinoid), chaotic evil
        monster = monsters[-1]
        
        upsert(data, "acc_monster_size", cleanup_text(span["text"]))
        text = data["acc_monster_size"]

        size_type_alignment = text.rsplit(",", 1)
        if (len(size_type_alignment) > 1):
            monster["alignment"] =  size_type_alignment[1].strip()

        size_type = size_type_alignment[0].split(" ", 1)
        if (len(size_type) > 1):
            monster["size"], monster["type"] = [s.strip() for s in size_type]

        else:
            monster["type"] = size_type[0]

    elif (prod_name == "monster_scores"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        scores = {}
        for score_name, score in zip("STR DEX CON INT WIS CHA".split(), re.split("  ", text)):
            scores[score_name] = score
        monster["scores"] = scores

    elif (prod_name.startswith("monster_legendary_")):

        monster = monsters[-1]
        text = cleanup_text(span["text"])

        if (prod_name == "monster_legendary_actions"):
            monster["legendary_actions"] = {}

        elif (prod_name == "monster_legendary_actions_blurb"):
            upsert(monster["legendary_actions"], "description", text)
        
        elif (prod_name == "monster_legendary_action_name"):
            upsert(data, "acc_legendary_action", text)

        elif (prod_name == "monster_legendary_action_description"):
            acc_legendary_action = data.pop("acc_legendary_action", None)
            
            if (acc_legendary_action is not None):
                # Create the legendary action description only once
                data["last_legendary_action"] = acc_legendary_action
                monster["legendary_actions"][acc_legendary_action] = ""
            
            last_legendary_action = data["last_legendary_action"]
            upsert(monster["legendary_actions"], last_legendary_action, text)

    elif (prod_name.startswith("monster_action") or prod_name.startswith("monster_reaction")):
        monster = monsters[-1]
        text = cleanup_text(span["text"])
        if (prod_name == "monster_actions"):
            monster["actions"] = {}
            data["action_reaction"] = "actions"

        elif (prod_name == "monster_reactions"):
            monster["reactions"] = {}
            data["action_reaction"] = "reactions"
        
        elif (prod_name.endswith("_action_name")):
            data["last_action_name"] = text
            data["last_action_type"] = ""
        
        elif (prod_name.endswith("_action_description_type")):
            # Collect the type, since it can be split across spans, don't do 
            # anything until the description body
            upsert(data, "acc_action_type", text)
            
        elif (prod_name.endswith("_action_description_body") or 
              prod_name.endswith("_action_description_type_body")):
            
            acc_action_type = data.pop("acc_action_type", None)
            if (acc_action_type is not None):
                # The current grammar can put italized body text into the type,
                # move it back to the body by using the heuristic that type ends
                # in colon
                # XXX Fix the grammar so it stops doing that?
                if (acc_action_type.endswith(":")):
                    data["last_action_type"] = acc_action_type[:-1]

                else:
                    # Probably body data instead of type, add to body and don't
                    # update type
                    text = acc_action_type + " " + text
                
            last_action_type = data["last_action_type"]
            last_action_name = data["last_action_name"]
            
            actions = monster[data["action_reaction"]]
            
            if (last_action_type == ""):
                # There's no type, it's all description
                upsert(actions, last_action_name, text)
            else:
                last_action = actions.get(last_action_name, None)
                if (last_action is None):
                    actions[last_action_name] = {}
                    last_action = actions[last_action_name]

                upsert(last_action, last_action_type, text)

    elif (prod_name == "monster_special_trait"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        # XXX In theory this should accumulate, but there doesn't seem to be any
        #     real case of it and the grammar doesn't allow it anyway, so both
        #     here and the grammar would need to be fixed
        if ("special_traits" not in monster):
            monster["special_traits"] = {}
        data["last_special_trait"] = text

        assert text != "Challenge"
        
    elif (prod_name == "monster_special_trait_description"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])
        last_special_trait = data["last_special_trait"]
        special_traits = monster["special_traits"]

        upsert(special_traits, last_special_trait, text)

    elif (prod_name == "monster_final_blurb"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        upsert(monster, "description", text)

    elif (prod_name == "monster_challenge_data"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        # CR/CR (NNN,NNN XP)
        m = re.match(r"(?P<cr_num>\d+)(\/(?P<cr_denom>\d+))?\s*\((?P<xp>\d+(,\d{3})*) XP\)", text)
        monster["cr"] = float(m.group("cr_num"))
        monster["cr"] = monster["cr"] / (1.0 if m.group("cr_denom") is None else float(m.group("cr_denom")))
        monster["xp"] = int(m.group("xp").replace(",", ""))
        
        # XXX CR and XP needs beautifying for the template (convert to int, put
        #     thousand comma separator)

    elif (prod_name == "monster_hp_data"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        if (text.startswith("s")):
            # Spy has a dummy "s" from hit point_s_, remove
            text = text[1:].strip()

        # HP (HD)
        monster["hp"], monster["hd"]= text.split(" ", 1)
        monster["hp"] = int(monster["hp"])
        monster["hd"] = monster["hd"].replace("(", "").replace(")", "").strip()

    elif (prod_name == "monster_ac_data"):
        monster = monsters[-1]
        text = cleanup_text(span["text"])

        upsert(data, "acc_armor_class", text)
        text = data["acc_armor_class"]

        # AC (armor)
        # XXX Needs fixing for archmage, druid, wereXXXX, ankheg
        #   12 (15 with mage armor)
        #   11 (16 with barkskin)
        #   10 in humanoid form, 11 (natural armor) in bear and hybrid form
        #   14 (natural armor), 11 while prone
        # Water Elemental has "class" 
        if (text.startswith("Class ")):
            text = text.replace("Class ", "")
        l = text.split(" ", 1)
        monster["ac"] = l[0]
        monster["ac"] = int(monster["ac"])
        if (len(l) > 1):
            monster["armor"] = l[1]
            monster["armor"] = monster["armor"].replace("(", "").replace(")", "").strip()

    elif (prod_name.endswith("_data")):
        monster = monsters[-1]
        text = cleanup_text(span["text"])
        key = prod_name[len("monster_"):-len("_data")]
        upsert(monster, key, text)

    # The header is read before the monster so the there's no access to the next
    # monster, only to the previous, ignore
    do_raw = False
    if ((len(monsters) > 0) and (prod_name != "monster_group_header")) and do_raw:
        monster_raw = monsters[-1].get("raw", None)
        if (monster_raw is None):
            monsters_raw = {}
            monsters[-1]["raw"] = monsters_raw
        text = cleanup_text(span["text"])
        upsert(monster_raw, prod_name, text)


if (len(sys.argv) > 1):
    filepath = sys.argv[1]
    out_dir = os.path.dirname(filepath)

else:
    out_dir = "_out"
    filepath = os.path.join(out_dir, "SRD_CC_v5.1.pdf")

out_cache_dir = os.path.join(out_dir, "cache")
makedirs(out_cache_dir)
out_html_dir = os.path.join(out_dir, "html")
makedirs(out_html_dir)

out_monsters_filepath = os.path.join(out_dir, "monsters.json")
if (os.path.exists(out_monsters_filepath)):
    print "Reading json", out_monsters_filepath
    with open(out_monsters_filepath, "r") as f: 
        monsters = json.load(f)
        monsters = monsters.values()
        
        print "Loaded", len(monsters), "monsters"

else:
    print "Reading pdf", filepath
    with fitz.open(filepath) as pdf:
        print "Parsing monsters"
        tokenizer = create_span_tokenizer(pdf)
        state = create_parser(tokenizer, "monsters.grammar", process_span)
        parse_wrapper(state)

        print "found", len(state["data"]["monsters"]), "monsters"
        monsters = state["data"]["monsters"]

# font_size, name, 0-based page number
toc = []
# From visual inspection of a dump of the pdf, the section titles have a minimum
# font size of 12, smaller sizes are used for normal text, footers, etc, ignore
# the latter when looking for toc entries (could also hook on the text color
# instead of the font size, sections seem to be color 9712948)
font_sizes = set()

markdown = []
prev_span_font_size = None
prev_span_font_name = None
last_section = None
print "Reading pdf", filepath
with fitz.open(filepath) as pdf:
    tokenizer = create_span_tokenizer(pdf)
    print "Generating TOC"
    while (True):
        span = next_span(tokenizer)
        if (span is None):
            break

        font_size = span["size"]
        font_name = span["font"]
        
        # The same size is used for two subsection levels, eg
        #   Ancient Green Dragon is "WWROEK+Calibri-Bold"
        #   Green Dragon is "DXJJCX+GillSans-SemiBold"
        # The same size is also used for tables, which are "WWROEK+Calibri-Bold"
        # size 12.0 but color 0
        # Create some fake font sizes so tables are the lowest size and monster
        # groups are the highest size
        if (font_size == 12.0):
            if (font_name == "DXJJCX+GillSans-SemiBold"):
                font_size += 0.1
            elif (span["color"] == 0):
                font_size -= 0.1

        # XXX There's a layout bug here for which all H monsters
        #     after "Half-Dragon Template" (Hell Hound, Hobgoblin,
        #     etc) are nested inside "Half-Dragon Template":
        #       Monsters (H) {"text":"Monsters (H) ", "color":9712948, "size":18.0 }
        #           Half-Dragon Template { "text":"Half-Dragon Template ", "color":9712948, "size":13.920000076293945 }
        #               Hobgoblin { "text":"Hobgoblin\t\r \u00a0", "color":9712948, "size":12.0 }
        #     Also happens with other sections at "half-Dragon Template" level
        #     others like Mephits, Nagas, Oozes, etc Could be spot fixed or
        #     ignore the offending section? (but then the toc appears to no
        #     longer sorted alphabetically, although that's probably better than
        #     inside the wrong section)
        
        # XXX This can be detected because it breaks the alphabetic order, but
        #     for Ancient->Adult->Young->Wyrmling in dragons, or because the
        #     letter goes back to the monsters(X), patch?


        # There are two font layout issues 
        # 1) Three levels of dragons
        #    { "text": "Dragons, Chromatic ", "font": "DXJJCX+GillSans-SemiBold", "size": 13.920000076293945 "color": 9647668, }
        #    { "text": "Black Dragon ", "font": "DXJJCX+GillSans-SemiBold", "size": 12.0,  "color": 9647668, }
        #    { "text": "Ancient\t\r \u00a0Black\t\r \u00a0Dragon\t\r \u00a0", "font": "WWROEK+Calibri-Bold", "size": 12.0,  "color": 9647668 }          
        # 2) Two levels of Nagas, Oozes, etc
        #    { "text": "Oozes ", "font": "DXJJCX+GillSans-SemiBold", "size": 13.920000076293945,  "color": 9647668 }
        #    { "text": "Black\t\r \u00a0Pudding\t\r \u00a0", "font": "WWROEK+Calibri-Bold", "size": 12.0,  "color": 9647668, 
        
        # Use a mixture of heuristic and spot check. The heuristic is to move up
        # in the font hierarchy if there's a monser subsection and this monster
        # is out of alphabetical order wrt the previous one. In addition,
        # special case the monsters where the heuristic fails (eg Oozes/Ochre
        # Jelly followed by Orc)
        
        if ((font_size == 13.920000076293945) and (font_name == "DXJJCX+GillSans-SemiBold")):
            last_section = span["text"]
            last_candidate = None
        
        elif ((last_section is not None) and (font_size >=13.920000076293945)):
            last_section = None
        
        elif ((last_section is not None) and (font_size == 12.0)):
            if (last_candidate is None):
                last_candidate = span["text"]

            if (
                (
                    (last_candidate > span["text"]) or
                    (span["text"] in ["Harpy", "Orc", "Sprite"])
                ) and (span["text"] not in ["Ogre Zombie", "Minotaur Skeleton"]) and 
                    # Leave chromatic/metallic dragon section (3 levels)
                    # untouched, resume on Dragon Turtle inclusive, since it
                    # should be out of the Dragon section
                    (("Dragon" not in span["text"]) or (span["text"] == "Dragon Turtle"))
                ):
                font_size = 13.920000076293945
                # Move up all until the next section
                last_candidate = "z"

            else:
                last_candidate = span["text"]

        font_sizes.add(font_size)

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
        if ((prev_span_font_size == font_size) and (prev_span_font_name == font_name)):
            # Merge with the previously inserted section
            merged_text += " " + span_text
            toc[-1][1] = merged_text

        else:
            # Start a new section
            prev_span_font_size = font_size
            prev_span_font_name = font_name
            
            merged_text = span_text
            # font size, name, 0-based page number
            entry = [font_size, merged_text, span["page"]-1, font_name]
            toc.append(entry)

    basename, fileext  = os.path.splitext(os.path.basename(filepath))
    out_filedir = os.path.dirname(filepath)
    out_filepath = os.path.join(out_filedir, basename + "_TOC" + fileext)
    print "Generating pdf with TOC", out_filepath
    # Ignore the existing TOC, the CC version has dummy filename entries, the
    # OGL version is empty
    pdf_toc = []
    font_size_to_level = { font_size:level for level, font_size in enumerate(sorted(list(font_sizes), reverse=True)) }
    ## print len(font_size_to_level), font_size_to_level
    prev_level = 0
    level_stack = []
    # The document doesn't always have contiguous levels, eg
    #   Monsters (M)->Kobold 
    # but
    #   Monsters (H)->Hags->Green Hag
    # Also happens in the character classes where
    #   Druid -> Class Features -> <missing> -> Hit Points
    #   Druid -> Class Features -> Spellcasting -> Cantrips
    # So Hit Points should be at the same level as Cantrips but it ends at the
    # same level as Spellcasting
    # In addition PDF errors out when starting with a non-one level or skipping
    # levels so the options are:
    # - insert dummy empty sections
    # - rebase the level
    # - remove entry from toc
    # Removing entries from the toc is not ver very useful since it removes most
    # monsters due to almost all monsters having a missing unless they belong to
    # some class (Angel, Dragons, etc) and inserting emtpy sections is not
    # visually appealing, so the best is "rebase"
    on_missing_level = "rebase"
    # How many levels to discard from the toc, smallest font size first
    # - With 4 you get the footer font size
    # - With 5 You get the deepest subsection (in red)
    # - With 6 you get tables (in black)
    # XXX Discarding levels means that the loop merging text is doing a lot of
    #     idle work for entries that belong to discarded levels. Unfortunately
    #     the final font size to level association is not known is not known
    #     until the whole file has been read, so that loop cannot do early
    #     discarding (unless on_missing_level is "rebase" in which case a
    #     similar code could be put there since rebasing doesn't really depend
    #     on the final level, just on the font size)
    # XXX Generate multiple toc appendix hierarchies with monsters sorted and
    #     grouped by name, CR, type, size... 
    discarded_levels = 6
    markdown_line = None
    line_font_size = None
    line_level = None
    output_markdown = True
    for entry in toc:
        font_size, text, page, font_name = entry
        level = font_size_to_level[font_size] + 1

        if (output_markdown):
            # XXX Markdown needs escaping for # * , _, ` xml, html, etc
            # XXX Markdown needs proper handling of tables
            # XXX Markdown needs proper paragraph separation
            markdown_text = cleanup_text(text)

            if (level >= 5):
                # XXX These should use PyMuPdf flags type instead of substring
                #     match
                #     See https://pymupdf.readthedocs.io/en/latest/textpage.html#structure-of-dictionary-outputs
                #     bit 0: superscripted (20) not a font property, detected by MuPDF code.
                #     bit 1: italic (21)
                #     bit 2: serifed (22)
                #     bit 3: monospaced (23)
                #     bit 4: bold (24)
                if (font_name.lower().endswith("italic")):
                    markdown_text = "*" + markdown_text + "*"

                elif (font_name.lower().endswith("bold")):
                    markdown_text = "**" + markdown_text + "**"

            if (font_size != line_font_size):
                # Spill and restart accumulation
                if (markdown_line is not None):
                    if (line_level < 5):
                        markdown_line = "#" * (line_level + 1) + " " + markdown_line
                    markdown.append(markdown_line)

                markdown_line = markdown_text
                line_font_size = font_size
                line_level = level

            else:
                # Accumulate
                markdown_line += markdown_text + " "
            
        # Drop lowest levels
        if (level >= len(font_size_to_level) - discarded_levels):
            continue
        
        ## print repr(entry)
        
        if (on_missing_level == "rebase"):
            while ((len(level_stack) > 0) and (level <= level_stack[-1])):
                level_stack.pop()
            level_stack.append(level)
            level = len(level_stack)

        elif (on_missing_level == "insert"):
            for i in xrange(level - prev_level - 1):
                pdf_toc.append([i + prev_level + 1, "", page + 1])

            prev_level = level

        else:
            if (level - prev_level > 1):
                continue
            prev_level = level

        # 1-based level, name, 1-based page
        pdf_toc.append([level, text, page + 1])

    if (output_markdown and (markdown_line is not None)):
        markdown.append(markdown_line)

    # Create indices per monster attribute, then alphabetically inside the same
    # attribute
    for field, title in [
        ("cr", "Index I: Monsters by CR"), 
        ("type", "Index II: Monsters by Type"),
        ("alignment", "Index III: Monsters by Alignment"),
        ("size", "Index IV: Monsters by Size"),
        ("hp", "Index V: Monsters by HP"), 
        ("ac", "Index VI: Monsters by AC"), 
        ("armor", "Index VII: Monsters by Armor"), 
        ("senses", "Index VIII: Monsters by Sense"), 
        ("languages", "Index IX: Monsters by Language"), 
        # XXX xp (ranges?)
        # XXX hp (ranges?)
        # XXX ac (ranges?)
        # XXX special_traits? Needs split by special trait
        # XXX speed (ranges / mediums?)
        ]:
        monster_attrib_to_monster = {}
        for monster in monsters:
            monster_attrib = monster.get(field, "Missing")
            monster_attrib = monster_attrib.lower() if isinstance(monster_attrib, unicode) else monster_attrib
            
            # Some attributes needs splitting and the monster will appear in all
            # split sections
            if (field in ["languages", "senses", "armor"]):
                monster_attribs = monster_attrib.split(",")
                monster_attribs = [monster_attrib.strip() for monster_attrib in monster_attribs]

            else:
                monster_attribs = [monster_attrib]

            for monster_attrib in monster_attribs:
                try:
                    monster_attrib_to_monster[monster_attrib].append(monster)

                except KeyError:
                    monster_attrib_to_monster[monster_attrib] = [ monster ]
        
        sub_toc = [ [1, title, None] ]
        for monster_attrib in sorted(monster_attrib_to_monster.keys()):
            first_entry = len(sub_toc)
            if (field == "cr"):
                # Display as fraction or int
                if (0 < monster_attrib < 1):
                    monster_attrib_title = "1/%d" % int(1.0/monster_attrib) 
                else:
                    monster_attrib_title = unicode(int(monster_attrib))
            elif (isinstance(monster_attrib, unicode)):
                # Capitalize words
                monster_attrib_title = []
                for word in monster_attrib.split():
                    monster_attrib_title.append(word[0].upper() + word[1:])
                monster_attrib_title = string.join(monster_attrib_title, " ")

            else:
                monster_attrib_title = unicode(monster_attrib)
                
            sub_toc.append([2, monster_attrib_title, None])
            for monster in sorted(monster_attrib_to_monster[monster_attrib], key= lambda m:  m["name"].lower()):
                sub_toc.append([3, monster["name"], monster["page"]])
            sub_toc[first_entry][2] = sub_toc[first_entry + 1][2]
        sub_toc[0][2] = sub_toc[1][2]
        pdf_toc.extend(sub_toc)
    
    ## print pdf_toc
    pdf.setToC(pdf_toc)

    print "Adding monster thumbnails to", out_filepath
    force_monster_download = False
    for monster in monsters:
        ## print monster
        name, page_index, bbox = monster["name"], monster["page"]-1, monster["bbox"]
        name = cleanup_text(name)

        try:
            download_monster_images(monster, force_monster_download)

        except urllib2.HTTPError as e:
            print e
            print "Forbidden error downloading monster images, aborting downloads"
            #break
        except Exception as e:
            print e
            
        col_width = 235
        image_width = 75
        #image_width = 90
        bbox = list(bbox)
        bbox[0] = bbox[0] + col_width - image_width 
        bbox[2] = bbox[0] + image_width
        bbox[3] = bbox[1] + image_width
        rect = fitz.Rect(bbox)
        use_hi_res_thumbnail = True
        if (use_hi_res_thumbnail):
            img_filepath = os.path.join(out_cache_dir, filename_from_monster_name(name) + "_img")
        else:
            img_filepath = os.path.join(out_cache_dir, filename_from_monster_name(name) + "_thumb")
        
        # Most full images are png but some are jpeg
        # Most (all?) thumbnails are jpeg
        if (os.path.exists(img_filepath + ".png")):
            pix = fitz.Pixmap(img_filepath + ".png")

        elif (os.path.exists(img_filepath + ".jpeg")):
            pix = fitz.Pixmap(img_filepath + ".jpeg")

        else:
            ## print "Missing image", img_filepath
            continue
        
        # Scale down the image to make the pdf smaller but make it so the
        # smallest dimension is full resolution and add some fudge factor so it
        # also looks nice when zooming
        # XXX This causes a gray lower/right border on some images, looks like
        #     PyMuPDF is rasterizing outside of the image when downscaling.
        #     Doesn't happen when using scale_factor = 1.0, but that bloats the
        #     pdf size. This happens even with 1/2, 1/4 sizes
        scale_factor = max((bbox[2] - bbox[0]) / pix.width, (bbox[3]-bbox[1]) / pix.height) * 1.5
        # XXX This could also alpha tint?
        # XXX Blend a negative overlay/mask so when text is over it's visible?
        pix = fitz.Pixmap(pix, pix.width * scale_factor, pix.height * scale_factor, True)
        pdf[page_index].insertImage(rect, pixmap=pix, overlay=False)
        ## pdf[page_index].drawRect(rect)

    print "Writing pdf", out_filepath
    pdf.save(out_filepath, deflate=True)
    
    out_filepath = os.path.join(out_dir, basename + ".json")
    print "Writing", out_filepath
    dicts = []
    with fitz.open(filepath) as pdf:
        for page in pdf:
            d = page.getText("dict")
            dicts.append(d)
    with open(out_filepath, "w") as f:
        json.dump({ "pages" : dicts }, f, indent=2, sort_keys=True)

    out_filepath = os.path.join(out_dir, basename + ".md")
    print "Writing", out_filepath
    with open(out_filepath, "w") as f:
        for l in markdown:
            # XXX Open the file in unicode mode, don't cleanup/encode
            f.write(l.encode("ascii", "xmlcharrefreplace"))
            f.write("\n\n")

    print "Generating", len(monsters), "monster", out_monsters_filepath
    with open(out_monsters_filepath, "w") as f:
        json.dump({ m["name"]: m  for m in monsters}, f, indent = 2, sort_keys=True) 

    print "Downloading resources for html monster pages"
    download_template_resources()

    print "Generating", len(monsters), "html monster pages at", out_html_dir
    for monster in monsters:
        safe_name = filename_from_monster_name(monster["name"]) + ".html"
        ## print "generating html for", safe_name
        # XXX This could generate data urls or local urls for the images
        generate_html_from_template(R"template.html", monster, os.path.join(out_html_dir, safe_name))
