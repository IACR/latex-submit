from collections import Counter
from pathlib import Path
import pytest
import sys
from .log_parser import LatexLogParser, badbox_re, line_re, warning_re, error_re, citation_re, l3msg_re
from .metadata.compilation import ErrorType

def test_overfull():
    m = badbox_re.search('Overfull \\hbox (50.8957pt too wide) in paragraph at lines 98--182')
    assert m.group(1) == 'Over'
    assert m.group(2) == 'h'
    assert m.group(3) == None
    assert m.group(4) == '50.8957'
    assert m.group(5) == '98'
    assert m.group(6) == '182'
    assert m.group(7) == None
    m = badbox_re.search('Overfull \\hbox (5.44096pt too wide) in alignment at lines 160--163')
    assert m.group(1) == 'Over'
    assert m.group(2) == 'h'
    assert m.group(3) == None
    assert m.group(4) == '5.44096'
    assert m.group(5) == '160'
    assert m.group(6) == '163'
    assert m.group(7) == None
    m = badbox_re.search('Overfull \\hbox (154.71477pt too wide) detected at line 146')
    assert m.group(1) == 'Over'
    assert m.group(2) == 'h'
    assert m.group(3) == None
    assert m.group(4) == '154.71477'
    assert m.group(5) == None
    assert m.group(6) == None
    assert m.group(7) == '146'
    m = badbox_re.search('Overfull \\vbox (4.18698pt too high) has occurred while \\output is active []')
    assert m.group(1) == 'Over'
    assert m.group(2) == 'v'
    assert m.group(3) == None
    assert m.group(4) == '4.18698'
    assert m.group(5) == None
    assert m.group(6) == None
    assert m.group(7) == None

def test_underfull():
    m = badbox_re.search('Underfull \\vbox (badness 10000) has occurred while \\output is active []')
    assert m.group(1) == 'Under'
    assert m.group(2) == 'v'
    assert m.group(3) == '10000'
    assert m.group(4) == None
    assert m.group(5) == None
    assert m.group(6) == None
    assert m.group(7) == None
    m = badbox_re.search('Underfull \\hbox (badness 4000) in paragraph at lines 19--23')
    assert m.group(1) == 'Under'
    assert m.group(2) == 'h'
    assert m.group(3) == '4000'
    assert m.group(4) == None
    assert m.group(5) == '19'
    assert m.group(6) == '23'
    assert m.group(7) == None
    m = badbox_re.search('Underfull \\vbox (badness 5000) detected at line 1175')
    assert m.group(1) == 'Under'
    assert m.group(2) == 'v'
    assert m.group(3) == '5000'
    assert m.group(4) == None
    assert m.group(5) == None
    assert m.group(6) == None
    assert m.group(7) == '1175'
    m = badbox_re.search('Underfull \\hbox (badness 4000) in alignment at lines 311--317')
    assert m.group(1) == 'Under'
    assert m.group(2) == 'h'
    assert m.group(3) == '4000'
    assert m.group(4) == None
    assert m.group(5) == '311'
    assert m.group(6) == '317'
    assert m.group(7) == None

def test_warning_re():
    line = "Package hyperref Warning: No autoref name for `Theorem' on input line 770."
    m = warning_re.search(line)
    assert m.group(1) == 'Package'
    assert m.group(2) == 'hyperref'
    mm = line_re.search(m.group(3))
    assert mm.group('line') == '770'
    line = 'LaTeX Warning: Command \\i invalid in math mode on input line 468.'
    m = warning_re.search(line)
    assert m.group(1) == 'LaTeX'
    assert m.group(2) == None
    assert m.group(3) == ' Command \\i invalid in math mode on input line 468.'
    mm = line_re.search(m.group(3))
    assert mm.group('line') == '468'

def test_error_re():
    m = error_re.search("! Package hyperref Error: Wrong DVI mode driver option `dvipdfmx',")
    assert m.group(1) == 'Package'
    assert m.group(2) == 'hyperref'
# def test_latex_warning():

def test_citations():
    m = citation_re.search("LaTeX Warning: Citation `hafiz_bit_2019' on page 1 undefined on input line 5.")
    assert m.group(1) == 'Citation'
    assert m.group(2) == 'hafiz_bit_2019'
    assert m.group(3) == '1'
    assert m.group(4) == '5'
    
def test_examples():
    """This tests a bunch of random lines, some of which we expect to recognize
       as errors, and some of which we do not recognize."""
    parser = LatexLogParser(wrap_len=2000)
    datafile = Path('testdata/logs/example_lines')
    lines = datafile.read_text(encoding='UTF-8').splitlines()
    parser.parse_lines(lines)
    errs = parser.errors
    assert len(errs) == 51 # first 51 are errors.
    for i in range(49):
        assert errs[i].text == lines[i]
        assert errs[i].logline == i+1
        if i < 22:
            assert errs[i].error_type == ErrorType.LATEX_WARNING
        elif i < 43:
            assert errs[i].error_type == ErrorType.LATEX_ERROR
        elif i == 44:
            assert errs[i].error_type == ErrorType.UNDERFULL_HBOX
        elif i == 45:
            assert errs[i].error_type == ErrorType.UNDERFULL_VBOX
        elif i == 46:
            assert errs[i].error_type == ErrorType.OVERFULL_VBOX
        elif i == 47:
            assert errs[i].error_type == ErrorType.OVERFULL_HBOX
        elif i == 48:
            assert errs[i].error_type == ErrorType.LATEX_ERROR
        elif i == 50:
            assert errs[i].error_type == ErrorType.LATEX_WARNING
        if errs[i].error_type == 'Latex warning':
            if 'on input line' in errs[i].text:
                assert errs[i].filepath_line != 0
            if 'Package' in errs[i].text:
                assert errs[i].package is not None

def test_no_citations():
    parser = LatexLogParser(wrap_len=2000)
    parser.parse_file(Path('testdata/logs/citations.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    counter = Counter()
    for e in parser.errors:
        counter.update([e.error_type])
    assert len(parser.errors) == 219
    assert len(counter) == 5
    assert counter[ErrorType.REFERENCE_ERROR] == 185
    assert counter[ErrorType.LATEX_WARNING] == 17
    assert counter[ErrorType.OVERFULL_HBOX] == 5
    assert counter[ErrorType.UNDERFULL_HBOX] == 7
    assert counter[ErrorType.UNDERFULL_VBOX] == 5
    assert parser.errors[52].pageno == 7
    assert parser.errors[52].filepath == 'RelatedWork.tex'
    assert parser.errors[202].filepath == 'opti.tex'
    assert parser.errors[202].filepath_line == 49
    assert parser.errors[202].logline == 2321

    assert parser.errors[152].error_type == ErrorType.OVERFULL_HBOX
    assert parser.errors[152].logline == 2087
    assert parser.errors[152].filepath == 'FRand.tex'
    assert parser.errors[152].filepath_line == 72
    assert parser.errors[152].severity == 28.24112
    
    assert parser.errors[202].error_type == ErrorType.REFERENCE_ERROR
    assert parser.errors[215].logline == 2409
    assert parser.errors[215].pageno == 52
    assert parser.errors[215].filepath == 'Experiments.tex'
    assert parser.errors[215].filepath_line == 211
    
def test_working():
    parser = LatexLogParser(wrap_len=2000)
    parser.parse_file(Path('testdata/logs/working.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    counter = Counter()
    for e in parser.errors:
        counter.update([e.error_type])
    assert len(parser.errors) == 53
    assert len(counter) == 4
    assert counter[ErrorType.LATEX_WARNING] == 34
    assert counter[ErrorType.UNDERFULL_VBOX] == 8
    assert counter[ErrorType.OVERFULL_VBOX] == 0
    assert counter[ErrorType.OVERFULL_HBOX] == 4

    assert parser.errors[22].text == 'Overfull \\hbox (19.71275pt too wide) in paragraph at lines 246--247'
    assert parser.errors[22].package == None
    assert parser.errors[22].filepath == 'Relay.tex'
    assert parser.errors[22].filepath_line == 246
    assert parser.errors[22].logline == 1637
    assert parser.errors[22].pageno == 23

    assert parser.errors[29].text == 'Package hyperref Warning: Token not allowed in a PDF string (Unicode):'
    assert parser.errors[29].package == 'hyperref'
    assert parser.errors[29].filepath == 'FRand.tex'
    assert parser.errors[29].filepath_line == 0
    assert parser.errors[29].logline == 1686
    assert parser.errors[29].pageno == 27
    
def test_working79():
    parser = LatexLogParser(wrap_len=79)
    parser.parse_file(Path('testdata/logs/working79.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    counter = Counter()
    for e in parser.errors:
        counter.update([e.error_type])
    assert len(parser.errors) == 53
    assert len(counter) == 4
    assert counter[ErrorType.LATEX_WARNING] == 34
    assert counter[ErrorType.UNDERFULL_VBOX] == 8
    assert counter[ErrorType.OVERFULL_VBOX] == 0
    assert counter[ErrorType.OVERFULL_HBOX] == 4

    assert parser.errors[22].text == 'Overfull \\hbox (19.71275pt too wide) in paragraph at lines 246--247'
    assert parser.errors[22].package == None
    assert parser.errors[22].filepath == 'Relay.tex'
    assert parser.errors[22].filepath_line == 246
    assert parser.errors[22].logline == 2244
    assert parser.errors[22].pageno == 23

    assert parser.errors[29].text == 'Package hyperref Warning: Token not allowed in a PDF string (Unicode):'
    assert parser.errors[29].package == 'hyperref'
    assert parser.errors[29].filepath == 'FRand.tex'
    assert parser.errors[29].filepath_line == 0
    assert parser.errors[29].logline == 2296
    assert parser.errors[29].pageno == 27

    assert parser.errors[49].text == r'Overfull \hbox (81.72266pt too wide) in paragraph at lines 54--67'
    assert parser.errors[49].logline == 2462
    assert parser.errors[49].severity == 81.72266
    assert parser.errors[49].filepath_line == 54
    
def test_iacrdoc():
    parser = LatexLogParser(wrap_len=79)
    parser.parse_file(Path('testdata/logs/iacrdoc.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    type_counter = Counter()
    package_counter = Counter()
    for e in parser.errors:
        type_counter.update([e.error_type])
        package_counter.update([e.package])
    assert len(parser.errors) == 42
    assert len(type_counter) == 2
    assert type_counter[ErrorType.LATEX_WARNING] == 40
    assert type_counter[ErrorType.OVERFULL_HBOX] == 2
    assert len(package_counter) == 2
    assert package_counter['hyperref'] == 38

def test_lualatex():
    parser = LatexLogParser(wrap_len=79)
    parser.parse_file(Path('testdata/logs/lualatex.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    type_counter = Counter()
    package_counter = Counter()
    for e in parser.errors:
        type_counter.update([e.error_type])
        package_counter.update([e.package])
    assert len(parser.errors) == 56
    assert len(type_counter) == 3
    assert len(package_counter) == 3
    assert package_counter['hyperref'] == 36
    
def test_file_stack():
    parser = LatexLogParser(wrap_len=200)
    parser.parse_file(Path('testdata/logs/iacrtrans.log'))
    assert len(parser.opened_files) == 1
    
def test_undefined_control():
    parser = LatexLogParser()
    parser.parse_file(Path('testdata/logs/undefined_control.log'))
    assert len(parser.errors) == 1

def test_fontspec_error():
    parser = LatexLogParser()
    for line in Path('testdata/logs/fontawesome.log2').read_text(encoding='utf-8').splitlines():
        m = l3msg_re.search(line)
        assert len(m.groups()) == 5
    parser = LatexLogParser()
    parser.parse_file(Path('testdata/logs/fontawesome.log2'))
    assert len(parser.errors) == 3
    parser = LatexLogParser()
    parser.parse_file(Path('testdata/logs/fontawesome'))
    assert len(parser.errors) == 48
