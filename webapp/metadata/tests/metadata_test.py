import json
from pathlib import Path
import pytest
import sys
sys.path.insert(0, '../')
from compilation import Compilation, FileTree, CompileStatus
from meta_parse import clean_abstract, check_bibtex
import datetime
from pathlib import Path

def test_filetree():
    comp = Compilation.parse_raw(Path('testdata/compilation.json').read_text(encoding='UTF-8'))
    comp.output_tree = FileTree.from_path(Path('testdata/bibtex'))
    assert comp.output_tree.name == 'bibtex'
    assert len(comp.output_tree.children) == 2

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
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(output_path, compilation)
    return compilation

def test_bibtex():
    compilation = _test_bibtex_entry('ex1')
    assert len(compilation.warning_log) == 34
    compilation = _test_bibtex_entry('cryptobib')
    print(json.dumps(compilation.error_log, indent=2))
    assert len(compilation.warning_log) == 1574
