from pathlib import Path
import pytest
import sys
sys.path.insert(0, '../')
from compilation import Compilation, FileTree
from meta_parse import clean_abstract

def test_filetree():
    comp = Compilation.parse_raw(Path('testdata/compilation.json').read_text(encoding='UTF-8'))
    comp.output_tree = FileTree.from_path(Path('../'))
    assert comp.output_tree.name == '..'
    assert len(comp.output_tree.children) == 7

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
