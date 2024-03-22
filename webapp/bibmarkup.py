"""This file contains code for processing bibtex. The bibtex input from
authors is used for three things:
1. validate the bibtex to check for required fields and warn authors about
   missing optional but desirable fields like DOI.
2. convert to HTML for the web page.
3. convert to XML for reporting citations.

For this we require a bibtex parser. Ideally we would like to have a
parser that is faithful to the behavior of the bibtex binary (or
biber).  When the compiler runs bibtex or biber, it does some error
checking on the bibtex inputs, but this is fairly weak. We use a
bibtex log parser in log_parser.py as one way to provide feedback to
authors, but this is fairly weak and insufficient.

Unfortunately, the grammar for bibtex files is only defined in the
source code for the bibtex binary, and there are extensions like
nonstandard fields (e.g, from biblatex) that are recognized by
biblatex but not by standard bibtex styles. Thus it's not clear what
constitutes a valid bibtex file, since it depends on what tools are
used to process it.

All of the python parsers have problems. We started out using pybtex,
but this one is fairly unforgiving because it fails on a file as soon
as it encounters an error in an entry (e.g., a biber comment in a
field).  In order to get around this, we now use a two-phase form of
parsing. The first phase uses the 2.0 version of bibtexparser. Note
that this is not currently the default from pip, but must be installed
with

python3 -m pip install bibtexparser --pre

This first pass of parsing extracts all of the entries, but will flag
some "Blocks" that are not recognized (potentially a malformed entry
or a duplicate key). We extract some errors from this part of the parse.
The second pass of parsing is to provide each entry from the first pass
to pybtex.

HTML formatting in pybtex suffers from the same problem, namely that
if an entry has a missing field, then the formatting of the entire
bibliography fails. For this reason we format HTML from entries one at
a time.

"""

import datetime
import re
import logging
from pathlib import Path
import pybtex
from pybtex.database import BibliographyData, Entry
from pybtex.style.formatting.unsrt import Style as UnsrtStyle
from pybtex.style.template import href, join, field, sentence, optional
from pylatexenc.latex2text import LatexNodes2Text
from urllib.parse import urlencode
import bibtexparser
from bibtexparser.model import ParsingFailedBlock, DuplicateBlockKeyBlock, DuplicateFieldKeyBlock
import warnings
try:
    from metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus
except:
    from .metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus

import logging
from io import StringIO

class LogCapture:
    def __init__(self):
        self.buffer = StringIO()
        # self.buffer.write("Log output:\n")
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

class BibTeXParser:
    """This is a two-phase parser using bibtexparser and pybtex. You instantiate
       the parser and call parse_bibtex(bibstr). Errors and warnings may be
       retrieved from the parser after the parse."""
    def __init__(self):
        self.errors = []
        self.warnings = []

    def parse_bibtex(self, bibstr):
        """
        args:
          bibstr the string to be parsed.
        returns:
          pybtex.database.BibliographyData
        """
        db = BibliographyData()
        try:
            # Note that error handling in bibtexparser is a combination of
            # python logging and the warnings package. We capture logging errors
            # with LogCapture, and we capture warnings with warnings.catch_warnings.
            log_capture = LogCapture()
            with warnings.catch_warnings(record=True) as w:
                warnings.simplefilter('always')
                library = bibtexparser.parse_string(bibstr)
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
                                               text='Unable to parse region of bibtex: {}:{}'.format(str(block),
                                                                                                     block.raw))
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
                for entry in library.entries:
                    try:
                        entrydb = pybtex.database.parse_string(entry.raw, 'bibtex')
                        for key, e in entrydb.entries.items():
                            db.add_entry(key, e)
                    except Exception as ex:
                        warning = CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                               logline=0,
                                               text='Error processing entry {}:{}'.format(entry.key,
                                                                                          str(ex)))
                        if entry.start_line:
                            warning.filepath_line = entry.start_line
                        self.warnings.append(warning)
        except Exception as e:
            self.errors.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                            logline=0,
                                            text='Unknown bibtex parse failure: {}'.format(str(e))))
        finally:
            lines = log_capture.stopCapture().splitlines()
            loglines = []
            for line in lines:
                if (line != "Unknown block type <class 'bibtexparser.model.DuplicateBlockKeyBlock'>" and
                    line != "Unknown block type <class 'bibtexparser.model.DuplicateFieldKeyBlock'>" and
                    line != "Unknown block type <class 'bibtexparser.model.ParsingFailedBlock'>"):
                    loglines.append(line)
                    self.warnings.append(CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                                      logline=0,
                                                      text='\n'.join(loglines)))
        return db

_required_fields = {
    "article": ["author", "title", "journaltitle/journal", "year/date", "doi/url"],
    "book": ["author", "title", "year/date"],
    "booklet": ["author/editor", "title", "year/date"],
    "inbook": ["author", "title", "booktitle", "year/date"],
    "incollection": ["author", "title", "booktitle", "year/date"],
    "manual": ["author/editor", "title", "year/date"],
    "misc": ["author/editor", "title", "year/date"],
    "online": ["author/editor", "title", "year/date", "url"],
    "patent": ["author", "title", "number", "year/date"],
    "proceedings": ["title", "year/date"],
    "inproceedings": ["author", "title", "booktitle", "year/date", "doi/url"],
    "thesis": ["author", "title", "type", "institution", "year/date"],
    "phdthesis": ["author", "title", "school", "year/date"],
    "unpublished": ["author", "title", "year/date"],
    "mastersthesis": ["author", "title", "school", "year/date"],
    "techreport": ["author", "title", "institution", "year/date"],
}

def check_bib_entry(key: str, entry: Entry):
    errors = []
    if entry.persons:
        for k in entry.persons:
            entry.fields[k] = entry.persons[k]
    typ = entry.type.lower()
    if 'title' in entry.fields:
        title = entry.fields['title']
    else:
        title = 'Unknown title'
    if typ not in _required_fields:
        errors.append('unrecognized bibtex type for {}: @{}'.format(key, typ))
    else:
        for field in _required_fields.get(typ):
            if '/' in field:
                alts = field.split('/')
                if not entry.fields.get(alts[0], None) and not entry.fields.get(alts[1], None):
                    errors.append('bibtex entry {} ({}) should have {} field or {} field'.format(key,
                                                                                                 title,
                                                                                                 alts[0],
                                                                                                 alts[1]))
                    # If this doesn't get fixed, it can cause problems downstream when
                    # there is an empty entry.
                    entry.fields[alts[0]] = '?'
            else:
                if not entry.fields.get(field, None):
                    errors.append('bibtex entry {} ({}) requires {} field'.format(key,
                                                                                  title,
                                                                                  field))
                    # If this doesn't get fixed, it can cause problems downstream when
                    # there is an empty entry.
                    entry.fields[field] = '?'
    return errors

# pybtex produces exceptions for parse errors and missing required fields.
def _format_pybtex_exception(e):
    context = e.get_context()
    if not context:
        context = 'Unknown error'
    return 'BibTeX parse error: {}: {}'.format(context, str(e))

def check_bibtex(compilation: Compilation):
    """Check aux and bibtex files for invalid references, and add
       CompileErrors to compilation.
    Returns:
      parsed BibliographyData.
    """
    if not compilation.bibtex:
        compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                  logline=0,
                                                  text='No bibtex extracted'))
        return
    parser = BibTeXParser()
    bibdata = parser.parse_bibtex(compilation.bibtex)
    for e in parser.errors:
        compilation.error_log.append(e)
    for e in parser.warnings:
        compilation.warning_log.append(e)
    for key, entry in bibdata.entries.items():
        try:
            warnings = check_bib_entry(key, entry)
            for warning in warnings:
                compilation.warning_log.append(CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                                            logline=0,
                                                            text=warning))
        except Exception as e:
            compilation.warning_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                        logline=0,
                                                        text='error checking bibtex entry {}: {}. This may be a bug.'.format(key, str(e))))
    return bibdata

"""This pybtex bibtex style extends UnsrtStyle, but handles URLs
differently.  pybtex has its own template style.
"""

class BibStyle(UnsrtStyle):
    def format_title(self, e, which_field, as_sentence=True):
        formatted_title = field(
            which_field, apply_func=lambda text: text.capitalize()
        )
        if as_sentence:
            formatted_title = sentence [ formatted_title ]
        # Make the title clickable if there is a url field but no DOI field.
        if 'url' in e.fields and 'doi.org' not in e.fields['url']:
            ans = href [
                field('url', raw=False),
                formatted_title
            ]
        else:
            ans = formatted_title
        return ans

    def format_web_refs(self, e):
        return sentence [
            optional [ self.format_doi(e) ]
        ]

    def format_doi(self, e):
        # based on urlbst format.doi
        return href [
            join [
                'https://doi.org/',
                field('doi', raw=False)
                ],
            join [
                'https://doi.org/',
                field('doi', raw=False)
                ]
            ]

    def format_url(self, e):
        return href [
            join [
                'https://doi.org/',
                field('doi', raw=True)
            ],
            'DOI'
        ]


# The purpose of this is to insert <span id="bibtex:<key>... into bibtex
# so that we can navigate to it with javascript. 
def mark_bibtex(bibstr):
    return re.sub(r'^@([^\s\{]+)\{\s*([^\s,]+),?\s*',
                  r'<span id="bibtex:\2">@\1{\2,</span>\n',
                  bibstr,
                  count=0,
                  flags=re.MULTILINE)

def get_links(entry):
    """Return scholar, eprint links for a bibtex entry."""
    eprint = {'relevance': 'on'}
    query = ''
    if 'author' in entry.persons:
        converter = LatexNodes2Text()
        names = [converter.latex_to_text(str(a)) for a in entry.persons['author']]
        if len(names) < 3:
            query += ' and '.join(names)
        else:
            query += ', '.join(names[:-1]) + ', and \n' + names[-1]
        eprint['authors'] = query
    if 'title' in entry.fields:
        query += ' ' + entry.fields['title']
        eprint['title'] = entry.fields['title']
    if 'year' in entry.fields:
        query += ' ' + entry.fields['year']
        try:  # in case year is not an int.
            eprint['submittedafter'] = int(entry.fields['year']) - 1
            eprint['submittedbefore'] = int(entry.fields['year']) + 1
        except Exception as e:
            pass
    scholar = 'https://scholar.google.com/scholar?hl=en&' + urlencode({'q': query})
    eprint = 'https://eprint.iacr.org/search?' + urlencode(eprint)
    return scholar, eprint

BIBCITE_PATT = r'^\\bibcite{([^}]+)}{(.+)}$'
BIBLATEX_PATT = r'\\entry{([^}]+)}.*?\\field{labelalpha}{([^}]+)}$'

def bibtex_to_html(compilation, bibdata, output_dir):
    """This populates bibhtml in compilation using input from bibdata and output_dir.
       It will potentially modify error_log, warning_log, and bibhtml in compilation.
    params:
      compilation: Compilation to populate
      bibdata: pybtex.database.BibliographyData
      output_dir: pathlib Path to main.aux and main.bbl
    """
    style = BibStyle()
    backend = pybtex.plugin.find_plugin('pybtex.backends', 'html')()
    # a map from bibtex key to BibItem so we can assign labels.
    lookup = {}
    for key, entry in bibdata.entries.items():
        if 'note' in entry.fields:
            del entry.fields['note']
        if 'howpublished' in entry.fields:
            del entry.fields['howpublished']
        entrydb = BibliographyData()
        entrydb.add_entry(key, entry)
        bibitemdata = {'key': entry.key}
        try:
            formatted = style.format_bibliography(entrydb)
            for ent in formatted:
                bibitemdata['body'] = ent.text.render(backend)
                scholar, eprint = get_links(bibdata.entries[ent.key])
                bibitemdata['links'] = [
                    {
                        'label': 'Google Scholar',
                        'url': scholar
                    },
                    {
                        'label': 'ePrint',
                        'url': eprint
                    }]
        except Exception as e:
            compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                      logline=0,
                                                      text='Error producing HTML from bibtex: {}'.format(str(e))))
            bibitemdata['body'] = '<pre class="text-danger">{}\nBibTeX entry {} cannot be formatted</pre>'.format(str(e), key)
        import json
        bibitem = BibItem(**bibitemdata)
        lookup[entry.key] = bibitem
    references = []
    # first look in the main.aux file for \bibcite to match key to label.
    aux_file = output_dir / Path('main.aux')
    aux_str = aux_file.read_text(encoding='UTF-8')
    for m in re.finditer(BIBCITE_PATT, aux_str, re.MULTILINE):
        bibitem = lookup.get(m.group(1))
        if bibitem:
            bibitem.label = m.group(2).replace('{$^{+}$}', '<sup>+</sup>')
            references.append(bibitem)
    if not len(references): # in this case it's biblatex, so look in main.bbl
        bbl_file = output_dir / Path('main.bbl')
        bbl_str = bbl_file.read_text(encoding='UTF-8')
        try:
            for m in re.finditer(BIBLATEX_PATT,
                                 bbl_str,
                                 re.DOTALL|re.MULTILINE):
                bibitem = lookup.get(m.group(1))
                if bibitem:
                    bibitem.label = m.group(2).replace('{$^{+}$}', '<sup>+</sup>')
                    references.append(bibitem)
        except Exception as e:
            compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                      logline = 0,
                                                      text='Unable to parse bbl file {} This is a bug.'.format(str(e))))
    if len(references) != len(bibdata.entries):
        compilation.error_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                  logline = 0,
                                                  text='Mismatch in number of bibliographic references {} != {}. This is a bug.'.format(len(references), len(bibdata.entries))))
    compilation.bibhtml = references
    
if __name__ == '__main__':
    import argparse
    from pathlib import Path
    argparser = argparse.ArgumentParser(description='bibtex parser')
    argparser.add_argument('--bibtex_file',
                           default = 'testdata/bibtex/output2/extracted.bib')
    args = argparser.parse_args()
    bibtex_file = Path(args.bibtex_file)
    bibtex_parser = BibTeXParser()
    bibstr = bibtex_file.read_text(encoding='UTF-8')
    db = bibtex_parser.parse_bibtex(bibstr)
    print('parsed entries follow -------------------------')
    for key, entry in db.entries.items():
        print(key, entry)
    print('warnings follow -------------------------')
    for error in bibtex_parser.warnings:
        print('warning: {}'.format(error.text))
    print('errors follow -------------------------')
    for error in bibtex_parser.errors:
        print('error: {}'.format(error.text))
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
    path = Path('testdata/bibtex/output2')
    bibtex_to_html(compilation, db, path)
    print(compilation.model_dump_json(indent=2))
