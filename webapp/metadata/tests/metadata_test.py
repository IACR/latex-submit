import json
from pathlib import Path
import pytest
import random
import sys
sys.path.insert(0, '../')
from compilation import Compilation, CompileStatus
from meta_parse import clean_abstract, check_bibtex
import datetime
from pathlib import Path
sys.path.insert(0, '../../')
from metadata import _alphabet, _scramble, _unscramble

def test_clean_abstract():
    input = """This is an abstract
that has comments. %% this should be removed
% comments may start a line

% blank line above should survive.
 %% multi-line commments are removed
 %% along with spaces lines, which are just glue.
This is the second paragraph. \\begin{comment}
within comment environment.
\\end{comment}
You may still~\\footnote{Go bye bye} use percentages like 10\\% of the content.
We remove \\todo{this is a removable todo} and \\todo[inline]{so is this} but
the last one is not removed because arxiv_latex_cleaner does not recognize it.
\\iffalse
This is also false so should be removed.
\\fi
"""
    output = clean_abstract(input)
    print(output)
    assert 'should be removed' not in output
    assert '\n\n' in output
    assert '\n \n' not in output
    assert '\\begin{comment}' not in output
    assert 'comment environment' not in output
    # \footnote is removed.
    assert 'bye not in output'
    assert '%' in output
    # \todo is removed.
    assert 'removable' not in output
    # We might wish to catch this in the future.
    assert 'so is this' in output
    assert 'false' not in output

def _test_bibtex_entry(case):
    output_path = Path('testdata/bibtex/{}'.format(case))
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': output_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    return compilation

def test_bibtex():
    output_path = Path('testdata/bibtex/ex1/bibitem.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': output_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    assert len(compilation.warning_log) == 56
    output_path = Path('testdata/bibtex/cryptobib/bibexport.bib')
    compilation_data = {'paperid': 'abcdefg',
                        'status': CompileStatus.COMPILING,
                        'email': 'foo@example.com',
                        'venue': 'eurocrypt',
                        'submitted': '2023-01-02 01:02:03',
                        'accepted': '2023-01-03 01:02:55',
                        'compiled': datetime.datetime.now(),
                        'command': 'dummy command',
                        'error_log': [],
                        'warning_log': [],
                        'bibtex': output_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    assert len(compilation.warning_log) == 1665
    assert len(compilation.error_log) == 0

def test_scramble():
    for l in range(3, 12):
        for i in range(100):
            id = ''.join(random.choices(_alphabet, k=l))
            assert _unscramble(_scramble(id)) == id
