import glob
import io
import json
import os
from pathlib import Path
import pytest
import shutil
import sys
import tempfile

sys.path.insert(0, '../')

from runner import run_latex

def test_compile1():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('../../metadata/latex/iacrcc/tests/test1', output_path)
        assert output.get('exit_code') == 0

def test_compile2():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('../../metadata/latex/iacrcc/tests/test2', output_path)
        assert output.get('exit_code') == 0

def test_compile3():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('../../metadata/latex/iacrcc/tests/test3', output_path)
        assert output.get('exit_code') == 0

def test_compile4():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('../../metadata/latex/iacrcc/tests/test4', output_path)
        assert output.get('exit_code') == 12

def test_passing():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('passing', output_path)
        assert output.get('exit_code') == 0

def test_failing():
    with tempfile.TemporaryDirectory() as tmpdirpath:
        output_path = tmpdirpath + '/output'
        output = run_latex('failing', output_path)
        assert output.get('exit_code') == 12
        
