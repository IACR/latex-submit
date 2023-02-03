from pathlib import Path
import pytest
import sys
sys.path.insert(0, '../')
from compilation import Compilation, FileTree

def test_filetree():
    comp = Compilation.parse_raw(Path('testdata/compilation.json').read_text(encoding='UTF-8'))
    comp.output_tree = FileTree.from_path(Path('../'))
    print(comp.output_tree)
    assert comp.output_tree.name == '..'
    assert len(comp.output_tree.children) == 7
