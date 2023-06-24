"""
Library for handling output meta file from compiling latex.
"""

from nameparser import HumanName
from pylatexenc.latex2text import LatexNodes2Text
from arxiv_latex_cleaner import arxiv_latex_cleaner
from pybtex.database import parse_string, BibliographyData, BibliographyDataError
import pybtex.errors
try:
    from .compilation import CompileError, ErrorType
except Exception as e:
    from compilation import CompileError, ErrorType

from pathlib import Path
import re

def get_key_val(line):
    """If line has form key: value, then return key, value."""
    colon = line.find(':')
    if colon < 0:
        raise Exception('Exception: missing colon: {}'.format(line))
    key = line[:colon].strip()
    val = line[colon+1:].strip()
    return key, val
    
def read_meta(metafile):
    """Read the meta file line by line. When we encounter author: or affiliation: or title: or
       citation: we know how to process subsequent lines that start with two spaces.
    args:
       metafile: pathlib.Path pointing at metafile.
    Returns:
        a dict with authors, affiliations, citations and (optionally) editors
    # TODO: define a JSON schema for this file, or return a pydantic object.
    """
    # This is used to decode lines with TeX character macros like \'e.
    decoder = LatexNodes2Text()
    data = {'authors': [],
            'affiliations': [],
            'citations': []}

    lines = metafile.read_text(encoding='UTF-8').splitlines()
    numlines = len(lines)
    index = 0
    while index < numlines:
        line = lines[index].rstrip()
        if line.startswith('author:'):
            author = {'affiliations': []}
            data['authors'].append(author)
            index = index + 1
            while index < numlines and lines[index].startswith('  '):
                k,v = get_key_val(lines[index].rstrip())
                if k == 'name':
                    author[k] = v
                    v = decoder.latex_to_text(v)
                    parsed = HumanName(v)
                    if parsed:
                        author[k] = str(parsed) # canonicalize name
                        if parsed.last:
                            author['surname'] = parsed.last
                        if parsed.first:
                            author['given'] = parsed.first
                    else: # surname is required, so guess if the parser fails.
                        parts = author[k].split()
                        author['surname'] = parts[-1]
                elif k == 'email':
                    author['email'] = v
                elif k == 'affil':
                    author['affiliations'] = [a for a in v.split(',' ) if a.isnumeric()]
                elif k == 'orcid':
                    author['orcid'] = v.rstrip()
                index += 1
        elif line.startswith('affiliation:'):
            affiliation = {}
            data['affiliations'].append(affiliation)
            index += 1
            while index < numlines and lines[index].startswith('  '): # associated with affiliation
                k,v = get_key_val(lines[index])
                affiliation[k] = decoder.latex_to_text(v)
                index += 1
        elif line.startswith('version:'):
            data['version'] = line[8:].strip()
            index += 1
        elif line.startswith('title:'):
            data['title'] = line[6:].strip() # decoder.latex_to_text(line[6:].strip())
            index += 1
            if index < numlines and lines[index].startswith('  '):
                k,v = get_key_val(lines[index])
                if k == 'subtitle':
                    data['subtitle'] = v
                    index += 1
        elif line.startswith('keywords:'):
            data['keywords'] = [k.strip() for k in line[9:].strip().split(',')]
            index += 1
        elif line.startswith('citation:'):
            parts = line.split()
            assert(len(parts) == 3)
            citation = {'ptype': parts[1].strip(),
                        'id': parts[2].strip(),
                        'authorlist': []}
            data['citations'].append(citation)
            index += 1
            while index < numlines and lines[index].startswith('  '): # associated with citation:
                k,v = get_key_val(lines[index])
                if k == 'authors': # Original BibTeX form.
                    citation['authors'] = decoder.latex_to_text(v)
                    index += 1
                elif k == 'author': # separated out by bst
                    author = {'name': decoder.latex_to_text(v)}
                    citation['authorlist'].append(author)
                    index += 1
                    k,v = get_key_val(lines[index])
                    if k == 'surname':
                        author['surname'] = decoder.latex_to_text(v)
                        index += 1
                elif k == 'editor':
                    if 'editors' not in citation:
                        citation['editors'] = []
                    editor = {'name': v}
                    citation['editors'].append(editor)
                    index += 1
                    k,v = get_key_val(lines[index])
                    if k == 'surname':
                        editor['surname'] = v
                        index += 1
                else:
                    citation[k] = v
                    index += 1
        else:
            raise Exception('unexpected line {}'.format(line))
    return data

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
    "phdthesis": ["author", "title", "type", "institution", "year/date"],
    "unpublished": ["author", "title", "year/date"],
    "mastersthesis": ["author", "title", "institution", "year/date"],
    "techreport": ["author", "title", "institution", "year/date"],
}

def check_bib_entry(key, entry):
    errors = []
    if entry.persons:
        for k in entry.persons:
            entry.fields[k] = entry.persons[k]
    typ = entry.type.lower()
    if typ not in _required_fields:
        errors.append('unrecognized bibtex type for {}: @{}'.format(key, typ))
    else:
        for field in _required_fields.get(typ):
            if '/' in field:
                alts = field.split('/')
                if alts[0] not in entry.fields and alts[1] not in entry.fields:
                    errors.append('bibtex entry {} should have {} field or {} field'.format(key, alts[0], alts[1]))
            else:
                if field not in entry.fields:
                    errors.append('bibtex entry {} requires {} field'.format(key, field))
    return errors

def check_bibtex(output_path, compilation):
    """Check aux and bibtex files for invalid references."""
    try:
        aux_file = Path(output_path) / Path('main.aux')
        if not aux_file.is_file():
            compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_ERROR,
                                                      logline=0,
                                                      text='Missing aux file'))
            return
        aux_lines = aux_file.read_text(encoding='UTF-8', errors='replace').splitlines()
        # These identify the occurrences of \cite in the document. All
        # should have references.
        citation_pat = re.compile(r'\\citation{([^}]+)}')
        bibfile_pat = re.compile(r'\\bibdata{([^}]+)}')
        cite_keys = set()
        bibfiles = []
        for line in aux_lines:
            res = citation_pat.search(line)
            if res and res.group(1):
                for key in res.group(1).split(','):
                    cite_keys.add(key)
            res = bibfile_pat.search(line)
            if res and res.group(1):
                bibfiles.extend([b+'.bib' for b in res.group(1).split(',')])
        # now read all of the bibtex files and grab the entries for
        # these keys. We merge them all into a single database since
        # each file must be parsed separately. See
        # https://github.com/sciunto-org/python-bibtexparser/issues/186
        # bibdatabase = bibtexparser.bibdatabase.BibDatabase()
        # parser = bibtexparser.bparser.BibTexParser()
        # parser.interpolate_strings = False
        pybtex.errors.set_strict_mode(False)
        bibstring = ''
        for bibfile in bibfiles:
            bib_path = Path(output_path) / Path(bibfile)
            bibstring += '\n' + bib_path.read_text(encoding='UTF-8')
        bibdata = parse_string(bibstring, 'bibtex')
        used_entries = {}
        for key in cite_keys:
            if key not in bibdata.entries:
                compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_ERROR,
                                                          logline=0,
                                                          text='missing reference {}'.format(key)))
            else:
                used_entries[key] = bibdata.entries.get(key)
        for key, entry in used_entries.items():
            try:
                warnings = check_bib_entry(key, entry)
                for warning in warnings:
                    compilation.warning_log.append(CompileError(error_type=ErrorType.LATEX_WARNING,
                                                                logline=0,
                                                                text=warning))
            except Exception as e:
                compilation.warning_log.append(CompileError(error_type=ErrorType.LATEX_WARNING,
                                                            logline=0,
                                                            text='error checking bibtex entry {}: {}. This may be a bug.'.format(key, str(e))))
    except Exception as e:
        compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_WARNING,
                                                  logline=0,
                                                  text='Error checking for bibtex problems: {}. This may be a bug'.format(str(e))))

def clean_abstract(text):
    """Remove comments, todos, \begin{comment} from abstract."""
    lines = text.splitlines(keepends=True)
    # There is some doubt about whether to include things like \textrm
    # in the commands_only_to_delete. It depends on how mathjax or
    # katex is configured.
    args = {'commands_only_to_delete': [],
            'commands_to_delete': ['todo', 'footnote']}
    clean_lines = arxiv_latex_cleaner._remove_comments_and_commands_to_delete(lines, args)
    return ''.join(clean_lines)
