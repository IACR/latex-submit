"""
Library for handling output meta file from compiling latex.
"""

from nameparser import HumanName
from arxiv_latex_cleaner import arxiv_latex_cleaner
from pybtex.database import parse_string, BibliographyData, BibliographyDataError, Entry
import pybtex.errors
import random
import re
import string
import tempfile
import xml.etree.ElementTree as ET

try:
    from .compilation import CompileError, ErrorType, Compilation
except Exception as e:
    from compilation import CompileError, ErrorType, Compilation

from pathlib import Path
import os
import re
import subprocess

def get_key_val(line):
    """If line has form key: value, then return key, value."""
    colon = line.find(':')
    if colon < 0:
        raise Exception('Exception: missing colon: {}'.format(line))
    key = line[:colon].strip()
    val = line[colon+1:].strip()
    return key, val

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
                if alts[0] not in entry.fields and alts[1] not in entry.fields:
                    errors.append('bibtex entry {} ({}) should have {} field or {} field'.format(key,
                                                                                                 title,
                                                                                                 alts[0],
                                                                                                 alts[1]))
            else:
                if field not in entry.fields:
                    errors.append('bibtex entry {} ({}) requires {} field'.format(key,
                                                                                  title,
                                                                                  field))
    return errors

def check_bibtex(compilation: Compilation):
    """Check aux and bibtex files for invalid references, and add
       CompileErrors to compilation."""
    if not compilation.bibtex:
        compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                  logline=0,
                                                  text='No bibtex extracted'))
        return
    try:
        pybtex.errors.set_strict_mode(False)
        bibdata = parse_string(compilation.bibtex, 'bibtex')
        for key, entry in bibdata.entries.items():
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

def extract_bibtex(output_path: Path, compilation: Compilation):
    """This is used to populate the bibtex field of compilation.
     This implementation uses bibexport, which is only supported
     under bibtex (not biber). In order to overcome this, we create a
     temporary aux file that can be processed by bibexport. An
     alternative implementation could be built by parsing the aux
     file to extract the \bibcite entries, and then use pybtex or
     another parser to parse the bibtex files and extract the
     entries. We chose to use bibexport because it is the fastest and
     most reliable parser of bibtex.
    """
    try:
        auxfilename = 'main.aux'
        aux_file = output_path / Path('main.aux')
        if not aux_file.is_file():
            compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_ERROR,
                                                      logline=0,
                                                      text='Missing aux file'))
            return
        bcf_file = output_path / Path('main.bcf')
        if bcf_file.is_file():
            # In this case the author used biblatex/biber, so we
            # create a temporary auxfile to use for bibexport.
            cite_keys = set()
            bibsources = []
            tree = ET.parse(str(bcf_file))
            root = tree.getroot()
            for child in root.iter('{https://sourceforge.net/projects/biblatex}citekey'):
                cite_keys.add(child.text)
            for child in root.iter('{https://sourceforge.net/projects/biblatex}datasource'):
                bibsources.append(child.text)
            bibsources = ','.join([a[:-4] for a in bibsources])
            auxfilename = 'tmp_' + ''.join(random.choices(string.ascii_uppercase, k=10)) + '.aux'
            aux_file = output_path / Path(auxfilename)
            cite_keys = list(cite_keys)
            tmpauxlines = ['\\citation{' + key + '}' for key in cite_keys]
            tmpauxlines.append('\\bibstyle{plain}')
            tmpauxlines.append('\\bibdata{' + bibsources + '}')
            tmpauxlines.extend(['\\bibcite{' + cite_keys[i] + '}{' + str(i) + '}' for i in range(len(cite_keys))])
            tmpauxcontents = '\n'.join(tmpauxlines) + '\n'
            aux_file.write_text(tmpauxcontents, encoding='UTF-8', errors='replace')
        with tempfile.TemporaryDirectory() as tmpdir:
            bibfile = tmpdir / Path('main.bib')
            args = ['bibexport', '-o', str(bibfile.resolve()), auxfilename]
            process = subprocess.run(args,
                                     cwd=output_path.resolve(),
                                     encoding='UTF-8',
                                     errors='replace',
                                     stdout=subprocess.PIPE,
                                     stderr=subprocess.STDOUT)
            if auxfilename != 'main.aux':
                aux_file.unlink()
            if process.returncode:
                compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                          logline=0,
                                                          text='Error in bibexport {}:{}'.format(process.returncode,
                                                                                                 process.stdout)))
            if bibfile.is_file():
                compilation.bibtex = bibfile.read_text(encoding='UTF-8', errors='replace')
            else:
                compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                          logline=0,
                                                          text='No output from bibexport: {}'.format(process.stdout)))
    except Exception as e:
        compilation.error_log.append(CompileError(error_type=ErrorType.LATEX_WARNING,
                                                  logline=0,
                                                  text='Error checking in extract_bibtex: {}. This may be a bug'.format(str(e))))


def clean_abstract(text):
    """Remove comments, todos, \begin{comment} from abstract. Convert
     dangerous characters like <, >,  and & by their entity equivalents.
     Convert \n\n to </p><p>. We could have used pylatexenc to convert
     text entities to UTF-8 equivalents, but this destroys some inline
    mathematics."""
    lines = text.splitlines(keepends=True)
    # There is some doubt about whether to include things like \textrm
    # in the commands_only_to_delete. It depends on how mathjax or
    # katex is configured.
    args = {'commands_only_to_delete': [],
            'commands_to_delete': ['todo', 'footnote']}
    # This is an internal command, so we may have to change to our own code
    # or using it through subprocess.
    clean_text = arxiv_latex_cleaner._remove_comments_and_commands_to_delete(lines, args)
    # for some reason, arxiv_latex_cleaner leaves % at end of line in order
    # to preserve LaTeX spacing. We remove it unless it is \%
    clean_text = re.sub(r'[^\\]%', '', clean_text)
    clean_text = clean_text.replace('&', '&amp;').replace('<', '&lt;').replace('>', '&gt;')
    # If we were to use the text as an attribute, then we would need to replace
    # single and double quotes. We leave them for now.
    # clean_text = clean_text.replace('"', '&quot;').replace("'", '&apos;')
    clean_text = re.sub(r'\n\n', '</p><p>', clean_text)
    clean_text = re.sub(r'\n', ' ', clean_text)
    return '<p>' + clean_text + '</p>'

if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(description='abstract cleaner')
    argparser.add_argument('--file',
                           default = 'abstract.txt')
    args = argparser.parse_args()
    abstract = Path(args.file).read_text(encoding='UTF-8')
    print(abstract)
    print('====================================================================')
    print(clean_abstract(abstract))
