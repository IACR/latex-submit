r"""This file contains code for processing bibtex. The bibtex input from
authors is used for three things:
1. validate the bibtex to check for required fields and warn authors about
   missing optional but desirable fields like DOI. These requirements are
   part of a bibliography style.
2. convert to HTML for the web page using a bibliography style.
3. convert to XML for reporting citations.

Ideally we would like to have a bibtex file parser that is faithful to
the behavior of the bibtex binary (or biber). Unfortunately even these
two parsers are not 100% compatible. When the compiler runs
bibtex or biber, it does some error checking on the bibtex inputs, but
this is fairly weak. We use a bibtex log parser in log_parser.py as
one way to provide feedback to authors, but this is fairly weak and
insufficient.

Unfortunately, the grammar for bibtex files is only defined in the
source code for the bibtex binary, and there are extensions like
nonstandard fields (e.g, from biblatex) that are recognized by
biblatex but not by standard bibtex styles. It's not clear what
constitutes a valid bibtex file, since it depends on what tools are
used to process it.

Moreover, all of the python parsers have problems. We started out
using pybtex, but it's unforgiving because it fails on a file as soon
as it encounters an error in an entry (e.g., a biber comment in a
field or "month = ,").  It also includes html conversion, but the 
quality is not good. For this reason, we chose to use a wrapper 
around the bibtexparser package. Note that we use the 2.0 version of
bibtexparser, and this must currently be installed with

python3 -m pip install bibtexparser --pre

A lot of the code in the parser is designed to handle errors, and
there can be a LOT of them. To list a few:
* the file itself may be incorrectly formatted, which can produce
  blocks that are unrecognized. This can happen if @article{ is unclosed
  before the next entry starts.
* entries may be lacking in 'required' fields (like journal for @article).
* entries may have repeated fields.
* entries may have duplicate keys and get ignored.
* some entry types are unrecognized (e.g, @software or @data). If an
  entry type is unrecognized by our style then we treat it as @misc.
* Some files are encoded in non-UTF8.
* Authors may use nonstandard LaTeX macros in their bibtex entries and
  depend upon a @preamble. We do not support this.
* There are quite a few nonstandard entry fields such as 'annote' that
  show up in bibtex files but are unrecognized by the alphaurl style
  that we use.
* the semantics of bibtex fields are ill-defined and authors use them
  in different ways. For example, some may use both
  note = {\url{https://theonion.com}}
  and
  url = {https://theonion.com}
  Some people put a DOI url into the url field. Some people put the
  same url in multiple places. Some people will use @misc instead of
  @webpage or @online, and others will use @unpublished. Some people
  just jam everything into @misc because they are lazy and don't want
  to hunt down missing required fields. Some people use the "year"
  field to enclose a string rather than an integer. Many people have
  gotten in the habit of excluding DOIs because they take space in a
  publishing environment that is constrained by the number of pages.
  We strongly urge authors to include DOIs in their references.

We classify problems in the bibtex input into either an 'error' which
is supposed to be fatal, vs a 'warning' that just turns into a warning
to the author. Those are collected in the Compilation.error_log and
Compilation.warning_log. At the current time we treat missing "required fields"
like 'journal' in 'article' and 'booktitle' in inproceedings as fatal.

Note that the bibtex parser we use is intended to transform a bibtex database
into a form useful for subsequent processing, but it should not be written
back to disk because it would then contain HTML constructs and lose information
from LaTeX macros in some bibtex fields.
"""

from collections import OrderedDict
import datetime
import re
import logging
from pathlib import Path
import string
from typing import List, Dict
from pylatexenc import macrospec
from pylatexenc.latex2text import LatexNodes2Text, get_default_latex_context_db, MacroTextSpec, EnvironmentTextSpec, SpecialsTextSpec
from urllib.parse import urlencode
import bibtexparser
from bibtexparser.model import Entry
from bibtexparser.middlewares import BlockMiddleware, SeparateCoAuthors, SplitNameParts, MonthIntMiddleware, MergeNameParts, LatexDecodingMiddleware
from bibtexparser.model import ParsingFailedBlock, DuplicateBlockKeyBlock, DuplicateFieldKeyBlock, MiddlewareErrorBlock
import warnings
try:
    from metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus
    from metadata.xml_meta import RemoveEmptyMiddleware
except:
    from .metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus
    from .metadata.xml_meta import RemoveEmptyMiddleware

try:
    from bibstyle import BibStyle
except Exception as e:
    from .bibstyle import BibStyle

import logging
from io import StringIO
import sys

# The purpose of this is to insert <span id="bibtex:<key>... into raw bibtex
# so that we can navigate to it with javascript.
def mark_bibtex(bibstr: str):
    return re.sub(r'^@([^\s\{]+)\{\s*([^\s,]+),?\s*',
                  r'<span id="bibtex:\2">@\1{\2,</span>\n',
                  bibstr,
                  count=0,
                  flags=re.MULTILINE)

class LogCapture:
    def __init__(self):
        self.buffer = StringIO()
        rootLogger = logging.getLogger()
        self.logHandler = logging.StreamHandler(self.buffer)
        #formatter = logging.Formatter("%(asctime)s - %(name)s - %(levelname)s - %(message)s")
        #self.logHandler.setFormatter(formatter)
        rootLogger.addHandler(self.logHandler)
    def stopCapture(self):
        """Return the string accumulated buffer."""
        rootLogger = logging.getLogger()
        rootLogger.removeHandler(self.logHandler)
        self.logHandler.flush()
        self.buffer.flush()
        return self.buffer.getvalue()

class LowerCaseFieldNamesMiddleware(BlockMiddleware):
    """Make sure all entry types and (optionally) field keys are lower
    case. The constructor takes a value 'which_key' which can be one
    of 'all', 'first', or 'last'. If 'all' is specified, then field
    names are not modified (this is the default). If 'first' is
    specified, then when the names of two fields collide in lower
    case, the first one that is encountered is kept.  This is the same
    behavior as the bibtex binary. If 'last' is specified, then we
    keep the last one. This is the behavior of the biblatex package.

    """
    def __init__(self, which_key='all'):
        if which_key not in {'all', 'first', 'last'}:
            raise ValueError('which_key in LowerCaseFieldNamesMiddleware must be one of all, first, or last')
        self.which_key = which_key
        super().__init__()

    def transform_entry(self, entry, *args, **kwargs):
        if not entry.entry_type.islower():
            entry.entry_type = entry.entry_type.lower()
        for field in entry.fields:
            if isinstance(field.value, str):
                field.value = re.sub(r'\s+', ' ', field.value, flags=re.MULTILINE)
        if self.which_key == 'all':
            return entry
        pending_removals = [] # a list of indices for fields to remove
        field_dict = {} # a map from new field name to integer index of field seen.
        for i in range(len(entry.fields)):
            field = entry.fields[i]
            newkey = field.key.lower()
            if newkey in field_dict:
                if self.which_key == 'first':
                    pending_removals.insert(0, i)
                else:
                    pending_removals.insert(0, field_dict[newkey])
                    field_dict[newkey] = i # keep track of last one seen.
            else:
                field_dict[newkey] = i
            field._key = newkey # set the key to lower case on the one we keep.
        for i in pending_removals:
            field = entry._fields.pop(i)
        return entry


def _illegal_handler(n):
    """output <span> to show that conversion failed."""
    raise ValueError('<span class="text-danger">Illegal macro: {}</span>'.format(n.latex_verbatim()))
#if n.isNodeType(latexwalker.LatexMacroNode):
#        return "<span class='text-danger'>Illegal macro in bibtex: '\\{}'</span>".format(n.macroname)
#    elif n.isNodeType(latexwalker.LatexEnvironmentNode):
#        return "<span class='text-danger'>Illegal environment in bibtex: '\\begin{{{}}}'</span>".format(n.environmentname)
#    return "<span class='text-danger'>Illegal latex construct in bibtex: '{}'</span>".format(n.latex_verbatim())

def _handle_textcommabelow(n):
    return 'This had a textcommabelow'
def _get_decoder():
    """Return a LatexNodes2Text to operate on bibtex fields."""
    lt_context_db = get_default_latex_context_db().filter_context(exclude_categories=[
        #'latex-placeholders',
        'natbib'])
    lt_context_db.add_context_category('bibtex',
                                       macros=[MacroTextSpec('cal', ''),
                                               macrospec.MacroSpec('textcommabelow', '{'),
                                               MacroTextSpec('textcommabelow', simplify_repl=_handle_textcommabelow),
                                               MacroTextSpec('gcd', 'gcd'),
                                               MacroTextSpec('mbox', ''),
                                               MacroTextSpec('slash', '/'),
                                               MacroTextSpec('bmod', 'mod'),
                                               MacroTextSpec('pmod', 'mod'),
                                               MacroTextSpec('texttt', '%s'),
                                               MacroTextSpec('ell', 'ℓ'),
                                               MacroTextSpec('sc', ''),
                                               MacroTextSpec('boldmath', ''),
                                               MacroTextSpec('bm', ''),
                                               MacroTextSpec('sl', ''),
                                               # These should be removed by the
                                               # HyperrefMiddleware before they hit
                                               # the LatexMiddleware
                                               MacroTextSpec('cite', '(unresolved citation)'),
                                               MacroTextSpec('href', 'href:'),
                                               MacroTextSpec('url', 'url:'),
                                               ],
                                       environments=[EnvironmentTextSpec('math', discard=False)],
                                       specials= [
                                           # leave these alone since they may
                                           # occur inside character entities like &gt;
                                           SpecialsTextSpec('&', '&'),
                                       ],
                                       prepend=True)
    lt_context_db.set_unknown_macro_spec(MacroTextSpec('', simplify_repl=_illegal_handler))
    return LatexNodes2Text(math_mode='verbatim',
                           latex_context=lt_context_db)

# These patterns are used in HyperrefMiddleware in the parser before they are
# seen by the LaTeX converter. We use them to turn \cite, \url, and \href into
# HTML equivalents.
URL_PATT = re.compile(r'\\url{([^}]+)}', re.MULTILINE)
CITE_PATT = re.compile(r'\\cite{([^}]+)}', re.MULTILINE)
HREF_PATT = re.compile(r'\\href{([^}]+)}{([^}]+)}', re.MULTILINE)

class HyperrefMiddleware(BlockMiddleware):
    def __init__(self, cite_map):
        self.cite_map = cite_map
        super().__init__()

    def _do_rewrite(self, field):
        field.value = HREF_PATT.sub(r'<a href="\1">\2</a>',
                                    field.value)
        m = CITE_PATT.search(field.value)
        while m:
            citekey = m.group(1)
            if citekey in self.cite_map:
                repl = '<a href="#ref-{}">{}</a>'.format(citekey,
                                                         self.cite_map[citekey])
                field.value = field.value.replace(m.group(0), repl)
                m = CITE_PATT.search(field.value)
            else: # if we hit a citation for an unknown key, then we abort.
                m = None
        field.value = URL_PATT.sub(r'<a href="\1">\1</a>', field.value)

    def transform_entry(self, entry, *args, **kwargs):
        fields_dict = entry.fields_dict
        if 'title' in fields_dict:
            self._do_rewrite(fields_dict['title'])
        if 'note' in fields_dict:
            self._do_rewrite(fields_dict['note'])
        if 'howpublished' in fields_dict:
            self._do_rewrite(fields_dict['howpublished'])
        if 'url' in fields_dict:
            field = fields_dict['url']
            field.value = URL_PATT.sub(r'\1', field.value)
        return entry

class LatexMiddleware(LatexDecodingMiddleware):
    def __init__(self):
        super().__init__(decoder=_get_decoder())
    def transform_entry(self, entry, *args, **kwargs):
        try:
            block = super().transform_entry(entry, args)
            if isinstance(block, MiddlewareErrorBlock):
                return ParsingFailedBlock(error=block.error,
                                          start_line=block.start_line,
                                          raw=block.raw)
            return block
        except Exception as e:
            logging.error('Error in parsing: {}'.format(str(e)))
            return entry

class BibTeXParser:
    r"""This parser is based on the bibtexparser package. The proper usage is to
        instantiate the parser and call parse_bibtex(bibstr). The constructor for
        the parser takes a cite_map that maps bibtex keys to labels, and is used
        to order the entries and rewrite \cite macros. Errors and warnings may be
        retrieved from the parser after the parse. This does not capture all possible
        errors, and it may falsely flag things that are acceptable in LaTeX.

        The parser performs several cleanup steps, namely:
        1. separate out the entries with bibtexparser. Some blocks may fail.
        2. canonicalize months to an integer.
        3. field names and entry_types are converted to lower case (they are case-insensitive
           in LaTeX).
        4. convert \url, \href, and \cite to appropriate HTML equivalents. These may fail
           in XML since we use the <a> tag.
        5. convert (most) LaTeX strings to UTF-8. Math blocks are left verbatim
           inside inline or display blocks.
        6. author and editor names are separated out and canonicalized as First Last.
    """
    errors: List[CompileError]
    warnings: List[CompileError]

    def __init__(self, cite_map = {}):
        self.cite_map = cite_map
        self.errors = []
        self.warnings = []

    def parse_bibtex(self, bibstr):
        """
        args:
          bibstr the string to be parsed.
        returns:
          bibtexparser.Library object.
        Note: in addition to the return value, the caller should look at self.errors and self.warnings.
        """
        # The order is important here. HyperrefMiddleware has to be
        # before LatexMiddleware because it rewrites \cite, \href, and \url before the LaTeX
        # converter sees them.
        bibtexmiddleware = (LowerCaseFieldNamesMiddleware(which_key='first'),
                            MonthIntMiddleware(),
                            HyperrefMiddleware(self.cite_map),
                            LatexMiddleware(),
                            SeparateCoAuthors(),
                            SplitNameParts(),
                            MergeNameParts(style='first'),
                            RemoveEmptyMiddleware())

        logging.captureWarnings(True)
        try:
            # Note that error handling in bibtexparser is an annoying combination
            # of python logging and the warnings package. We capture logging errors
            # with LogCapture, and we capture warnings with warnings.catch_warnings.
            library = None
            log_capture = LogCapture()
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                library = bibtexparser.parse_string(bibstr, append_middleware=bibtexmiddleware)
                for block in library.failed_blocks:
                    if isinstance(block, DuplicateBlockKeyBlock):
                        warning = CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                               logline=0,
                                               text='Duplicate bibtex entry: {}'.format(block.raw.splitlines()[0]))
                        if block.start_line:
                            warning.filepath_line = block.start_line
                        self.warnings.append(warning)
                    elif isinstance(block, DuplicateFieldKeyBlock):
                        warning = CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                               logline=0,
                                               text='Duplicate field in bibtex entry: {}:{}'.format(str(block),
                                                                                                    block.raw))
                        if block.start_line:
                            warning.filepath_line = block.start_line
                        self.warnings.append(warning)
                    elif isinstance(block, ParsingFailedBlock):
                        warning = CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                               logline=0,
                                               text='Unable to parse region of bibtex: {}'.format(block.raw))
                        if block.start_line:
                            warning.filepath_line = block.start_line
                        self.warnings.append(warning)
                    else:
                        warning = CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                               logline=0,
                                               text='Unknown bibtex parse error: {}:{}'.format(str(block),
                                                                                               block.raw))
                        if block.start_line:
                            warning.filepath_line = block.start_line
                        self.warnings.append(warning)
        except Exception as e:
            self.errors.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                            logline=0,
                                            text='Unknown bibtex parse failure: {}'.format(str(e))))
        finally:
            lines = log_capture.stopCapture().splitlines()
            loglines = []
            for line in lines:
                if (line != "Unknown block type <class 'bibtexparser.model.MiddlewareErrorBlock'>" and
                    line != "Unknown block type <class 'bibtexparser.model.DuplicateBlockKeyBlock'>" and
                    line != "Unknown block type <class 'bibtexparser.model.DuplicateFieldKeyBlock'>" and
                    line != "Unknown block type <class 'bibtexparser.model.ParsingFailedBlock'>"):
                    loglines.append(line)
                    self.warnings.append(CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                                      logline=0,
                                                      text='\n'.join(loglines)))
        return library

def get_links(entry: Entry):
    """Return scholar, eprint links for a bibtex entry."""
    eprint = {'relevance': 'on'}
    query = ''
    fields = entry.fields_dict
    if 'author' in fields:
        query = ' '.join(fields['author'].value)
        eprint['authors'] = query
    if 'title' in fields:
        query += ' ' + fields['title'].value
        eprint['title'] = fields['title'].value
    if 'year' in fields:
        query += ' ' + fields['year'].value
        try:  # in case year is not an int.
            eprint['submittedafter'] = int(fields['year'].value) - 1
            eprint['submittedbefore'] = int(fields['year'].value) + 1
        except Exception as e:
            pass
    scholar = 'https://scholar.google.com/scholar?hl=en&' + urlencode({'q': query})
    eprint = 'https://eprint.iacr.org/search?' + urlencode(eprint)
    return scholar, eprint

# these are used in the construction of the map from cite key to label.
BIBCITE_PATT = r'^\\bibcite{([^}]+)}{(.+)}$'
BIBLATEX_PATT = r'\\entry{([^}]+)}(?:.*\\field{labelalpha}{([^}]+)})?(?:.*\\field{extraalpha}{([^}]+)})?'

def get_citation_map(output_dir):
    """Look in the main.aux and main.bbl files to map citation keys to labels.
       returns: OrderedDict with key => label. The order is the order in which
       the bibtex style says they should be.
    """
    mapping = OrderedDict()
    # first look in the main.aux file for \bibcite to match key to label.
    aux_file = output_dir / Path('main.aux')
    aux_str = aux_file.read_text(encoding='UTF-8')
    for m in re.finditer(BIBCITE_PATT, aux_str, re.MULTILINE):
        mapping[m.group(1)] = m.group(2).replace('{$^{+}$}', '<sup>+</sup>')
    if not len(mapping): # in this case it's biblatex, so look in main.bbl
        bbl_file = output_dir / Path('main.bbl')
        bbl_str = bbl_file.read_text(encoding='UTF-8')
        bbl_str = ' '.join(bbl_str.splitlines())
        entryparts = re.split(r'\\endentry', bbl_str)
        for part in entryparts:
            m = re.search(BIBLATEX_PATT, part)
            if m:
                label = ''
                if m.group(2):
                    label = m.group(2).replace('{$^{+}$}', '<sup>+</sup>')
                    if m.group(3):
                        try:
                            index = int(m.group(3))-1
                            label += string.ascii_lowercase[index]
                        except Exception as e:
                            logging.warning('unable to convert extraalpha {} to int'.format(m.group(3)))
                            label += m.group(3)
                mapping[m.group(1)] = label
    return mapping

def bibtex_to_html(compilation, cite_map: OrderedDict):
    r"""This populates bibhtml in compilation using input from the raw extracted bibtex
    and the citation map from cite_key to label. We only include references in
    the cite_map. As it parses things it will replace \\cite with the correct label
    reference, and it will replace \\href and \\url with the appropriate HTML
    representations. If it encounters errors like missing required fields, then
    it will update error_log, warning_log from compilation.
    params:
      compilation: Compilation to populate
      cite_map: an ordered map from cite key to bibitem label.
    """
    if not compilation.bibtex:
        compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                  logline=0,
                                                  text='No bibtex extracted'))
        return
    parser = BibTeXParser(cite_map)
    bibdata = parser.parse_bibtex(compilation.bibtex)
    style = BibStyle(compilation)
    # a map from bibtex key to BibItem so we can assign labels.
    lookup = {}
    for e in parser.errors:
        compilation.error_log.append(e)
    for e in parser.warnings:
        compilation.warning_log.append(e)
    for entry in bibdata.entries:
        errors = style.check_required_fields(entry)
        for error in errors:
            compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                      logline=0,
                                                      text=error))
        if (entry.entry_type == 'article' or
            entry.entry_type == 'inproceedings'):
            if 'doi' not in entry.fields_dict and 'url' not in entry.fields_dict:
                compilation.warning_log.append(
                    CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                 logline=0,
                                 text='bibtex entry {} of type @{} should probably have a doi or url field.'.format(entry.key,
                                                                                                                   entry.entry_type)))
        bibitemdata = {'key': entry.key,
                       'label': cite_map.get(entry.key, 'BUG!')}
        if errors:
            body = '<span class="text-danger">BibTeX entry {} could not be formatted.'
            for error in errors:
                body += '<br>' + error
            body += '</span>'
            bibitemdata['body'] = body
        else:
            scholar, eprint = get_links(entry)
            bibitemdata['links'] = [
                {
                    'label': 'Google Scholar',
                    'url': scholar
                },
                {
                    'label': 'ePrint',
                    'url': eprint
                }]
            bibitemdata['body'] = style.format_entry(entry)
        bibitem = BibItem(**bibitemdata)
        lookup[entry.key] = bibitem
    bibhtml = []
    for key in cite_map.keys():
        bibitem = lookup.get(key)
        if bibitem:
            bibhtml.append(bibitem)
        else:
            compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                      logline = 0,
                                                      text='Error looking up bibtex entry {}. This is a bug'.format(key)))
    if len(bibhtml) != len(cite_map):
        compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                  logline = 0,
                                                  text='Mismatch in number of bibliographic references {} != {}. This is a bug.'.format(len(bibhtml), len(bibdata.entries))))
    compilation.bibhtml = bibhtml
    
if __name__ == '__main__':
    import argparse
    from pathlib import Path
    argparser = argparse.ArgumentParser(description='bibtex parser')
    argparser.add_argument('--text')
    argparser.add_argument('--bibtex_file',
                           default = 'testdata/bibtex/missing/missing.bib')
    argparser.add_argument('--output_dir',
                           default = 'testdata/bibtex/missing')
    args = argparser.parse_args()
    if args.text:
        print(args.text)
        decoder = _get_decoder()
        print(decoder.latex_to_text(args.text))
        sys.exit(2)
    bibtex_file = Path(args.bibtex_file)
    output_dir = Path(args.output_dir)
    cite_map = get_citation_map(output_dir)
    print('cite_map follows -------------------------')
    import json
    print(json.dumps(cite_map, indent=2))
    bibtex_parser = BibTeXParser(cite_map)
    bibstr = bibtex_file.read_text(encoding='UTF-8')
    db = bibtex_parser.parse_bibtex(bibstr)
    print('warnings follow -------------------------')
    for error in bibtex_parser.warnings:
        print('warning: {}'.format(error.text))
    print('errors follow -------------------------')
    for error in bibtex_parser.errors:
        print('error: {}'.format(error.text))
    print('parsed entries follow -------------------------')
    for entry in db.entries:
        print(entry.key, entry)
    print('end of errors -------------------------')
    compdata = {'paperid': 'abcdefg',
                'status': CompileStatus.COMPILING,
                'email': 'foo@example.com',
                'venue': 'eurocrypt',
                'submitted': '2023-01-02 01:02:03',
                'accepted': '2023-01-03 01:02:55',
                'pubtype': PubType.RESEARCH.name,
                'compiled': datetime.datetime.now(),
                'command': 'dummy command',
                'error_log': [],
                'warning_log': [],
                'bibtex': bibstr,
                'zipfilename': 'submit.zip'}
    compilation = Compilation(**compdata)
    bibtex_to_html(compilation, cite_map)
    print(compilation.model_dump_json(indent=2))
