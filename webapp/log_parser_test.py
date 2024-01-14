from collections import Counter
from pathlib import Path
import pytest
import re
import sys
from .log_parser import LatexLogParser, badbox_re, line_re, warning_re, error_re, citation_re, l3msg_re, BibTexLogParser
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
    assert len(parser.errors) == 216
    assert len(counter) == 5
    assert counter[ErrorType.REFERENCE_ERROR] == 185
    assert counter[ErrorType.LATEX_WARNING] == 14
    assert counter[ErrorType.OVERFULL_HBOX] == 5
    assert counter[ErrorType.UNDERFULL_HBOX] == 7
    assert counter[ErrorType.UNDERFULL_VBOX] == 5
    assert parser.errors[52].pageno == 7
    assert parser.errors[52].filepath == 'RelatedWork.tex'
    assert parser.errors[202].filepath == 'Experiments.tex'
    assert parser.errors[202].filepath_line == 11
    assert parser.errors[202].logline == 2336

    assert parser.errors[149].error_type == ErrorType.OVERFULL_HBOX
    assert parser.errors[149].logline == 2087
    assert parser.errors[149].filepath == 'FRand.tex'
    assert parser.errors[149].filepath_line == 72
    assert parser.errors[149].severity == 28.24112
    
    assert parser.errors[212].error_type == ErrorType.REFERENCE_ERROR
    assert parser.errors[212].logline == 2409
    assert parser.errors[212].pageno == 52
    assert parser.errors[212].filepath == 'Experiments.tex'
    assert parser.errors[212].filepath_line == 211
    
def test_working():
    parser = LatexLogParser(wrap_len=2000)
    parser.parse_file(Path('testdata/logs/working.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    counter = Counter()
    for e in parser.errors:
        counter.update([e.error_type])
    assert len(parser.errors) == 31
    assert len(counter) == 4
    assert counter[ErrorType.LATEX_WARNING] == 12
    assert counter[ErrorType.UNDERFULL_VBOX] == 8
    assert counter[ErrorType.OVERFULL_VBOX] == 0
    assert counter[ErrorType.OVERFULL_HBOX] == 4
    assert parser.errors[19].text == 'Overfull \\hbox (19.71275pt too wide) in paragraph at lines 246--247'
    assert parser.errors[19].package == None
    assert parser.errors[19].filepath == 'Relay.tex'
    assert parser.errors[19].filepath_line == 246
    assert parser.errors[19].logline == 1637
    assert parser.errors[19].pageno == 23

    assert parser.errors[30].text == '(\\end occurred inside a group at level 6)'
    assert parser.errors[30].package == None
    assert parser.errors[30].filepath == None
    assert parser.errors[30].filepath_line == 0
    assert parser.errors[30].logline == 1916
    assert parser.errors[30].pageno == 57
    
def test_working79():
    parser = LatexLogParser(wrap_len=79)
    parser.parse_file(Path('testdata/logs/working79.log'))
    #for i in range(len(parser.errors)):
    #    print(i, parser.errors[i].json(indent=2))
    counter = Counter()
    for e in parser.errors:
        counter.update([e.error_type])
    assert len(parser.errors) == 31
    assert len(counter) == 4
    assert counter[ErrorType.LATEX_WARNING] == 12
    assert counter[ErrorType.UNDERFULL_VBOX] == 8
    assert counter[ErrorType.OVERFULL_VBOX] == 0
    assert counter[ErrorType.OVERFULL_HBOX] == 4

    assert parser.errors[19].text == 'Overfull \\hbox (19.71275pt too wide) in paragraph at lines 246--247'
    assert parser.errors[19].package == None
    assert parser.errors[19].filepath == 'Relay.tex'
    assert parser.errors[19].filepath_line == 246
    assert parser.errors[19].logline == 2244
    assert parser.errors[19].pageno == 23

    assert parser.errors[14].text == 'Package amsfonts Warning: Obsolete command \\bold; \\mathbf should be used instead on input line 56.'
    assert parser.errors[14].package == 'amsfonts'
    assert parser.errors[14].filepath == 'Shamir.tex'
    assert parser.errors[14].filepath_line == 56
    assert parser.errors[14].logline == 2163
    assert parser.errors[14].pageno == 11

    assert parser.errors[27].text == r'Overfull \hbox (81.72266pt too wide) in paragraph at lines 54--67'
    assert parser.errors[27].logline == 2462
    assert parser.errors[27].severity == 81.72266
    assert parser.errors[27].filepath_line == 54
    
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
    assert len(parser.errors) == 2
    assert len(type_counter) == 1
    assert type_counter[ErrorType.OVERFULL_HBOX] == 2
    print(package_counter)
    assert len(package_counter) == 1
    assert package_counter['hyperref'] == 0

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
    assert len(parser.errors) == 18
    assert len(type_counter) == 3
    assert len(package_counter) == 2
    assert package_counter['hyperref'] == 0
    
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
    assert len(parser.errors) == 36

def test_bib_count():
    testcases = {'write$ -- 117\n(There was 1 warning)': ('1', 'warning'),
                 '(width$ -- 49\nwrite$ -- 592\n(There were 3 warnings)': ('3', 'warning'),
                 'foobar\nfeebar once error message\n(There was 1 error message)': ('1', 'error'),
                 '(There were 5 error messages)': ('5', 'error')}
    for testcase, result in testcases.items():
        print(testcase)
        m = re.search(BibTexLogParser.ERROR_COUNT_REGEX, testcase, re.MULTILINE)
        assert m is not None
        assert m.group(1) == result[0]
        assert m.group(2) == result[1]

def test_bib_singleline_warning():
    testdata = """STUFF here
Warning--there's a number but no volume in fukushima1983neocognitron
Warning--empty booktitle in gilbert2011testing
You've used 111 entries,
            2543 wiz_defined-function locations,
            12964 strings with 167403 characters,
"""
    matches = list(re.finditer(BibTexLogParser.SINGLELINE_WARNING_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 2
    assert matches[0].group(1) == "there's a number but no volume"
    assert matches[0].group(2) == 'fukushima1983neocognitron'
    assert matches[1].group(1) == 'empty booktitle'
    assert matches[1].group(2) == 'gilbert2011testing'
    
def test_bib_singleline_error():
    testdata = """STUFF here
Warning--empty booktitle in gilbert2011testing
Warning--I didn't find a database entry for "EC:BunFisSze20"
Warning--there's a number but no volume in fukushima1983neocognitron
You've used 111 entries,
            2543 wiz_defined-function locations,
            12964 strings with 167403 characters,
"""
    matches = list(re.finditer(BibTexLogParser.SINGLELINE_ERROR_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == ("I didn't find a database entry for "
                                   '"EC:BunFisSze20"')
    
def test_bib_multiline_regex():
    testdata = """This is a file
Warning--foobar occurred
--line 34 of file foobar.bib
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_WARNING_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == 'foobar occurred'
    assert matches[0].group(2) == '34'
    assert matches[0].group(3) == 'foobar.bib'
    
    multiline_data = """Some stuff
Warning--entry type for "thesis_axel-mathieu-mahias" isn't style-file defined
--line 48 of file add.bib
Some other line
Warning--string name "asiacrypt11addr" is undefined
--line 473 of file bib.bib
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_WARNING_REGEX, multiline_data, re.MULTILINE))
    assert len(matches) == 2
    assert matches[0].group(1) == """entry type for "thesis_axel-mathieu-mahias" isn't style-file defined"""
    assert matches[0].group(2) == '48'
    assert matches[0].group(3) == 'add.bib'
    assert matches[1].group(1) == 'string name "asiacrypt11addr" is undefined'
    assert matches[1].group(2) == '473'
    assert matches[1].group(3) == 'bib.bib'
   
def test_comma_error_regex():
    m = re.search(BibTexLogParser.COMMA_ERROR_REGEX, 'Too many commas in name 1 of "Kay, Kevin, Karma and Biden, Joseph" for entry DK:78-3_5', re.MULTILINE)
    assert m is not None
    assert m.group(1) == '1'
    assert m.group(2) == 'Kay, Kevin, Karma and Biden, Joseph'
    assert m.group(3) == 'DK:78-3_5'
    m = re.search(BibTexLogParser.COMMA_ERROR_REGEX, 'Too many commas in name 2 of "Biden, Joseph and Kay,, Kevin" for entry DK:zy78-3_5', re.MULTILINE)
    assert m is not None
    assert m.group(1) == '2'
    assert m.group(3) == 'DK:zy78-3_5'
    

def test_bib_multiline_warning():
    multiline_data = """Some stuff
Warning--entry type for "thesis_axel-mathieu-mahias" isn't style-file defined
--line 48 of file add.bib
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_WARNING_REGEX, multiline_data, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == """entry type for "thesis_axel-mathieu-mahias" isn't style-file defined"""
    assert matches[0].group(2) == '48'
    assert matches[0].group(3) == 'add.bib'

def test_bib_multiline_entry_error():
    testdata = """I'm skipping whatever remains of this entry
You're missing a field name---line 246 of file bib.bib
 :   
 :   %pages     = {296},
(Error may have been on previous line)
I'm skipping whatever remains of this entry
Repeated entry---line 1347 of file extra.bib
 : @misc{EPRINT:BIPPS22
 :                     ,
I'm skipping whatever remains of this entry
I was expecting a `,' or a `}'---line 1371 of file extra.bib
 :       howpublished = {In Eurocrypt 2023}
 :                                         .
I'm skipping whatever remains of this entry
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_ENTRY_WARNING_REGEX, testdata, re.MULTILINE))
    assert matches[0].group(1) == "You're missing a field name"
    assert matches[0].group(2) == "246"
    assert matches[0].group(3) == "bib.bib"
    assert len(matches) == 3
   
def test_bib_multiline_warning():
    multiline_data = """Some stuff
Warning--entry type for "thesis_axel-mathieu-mahias" isn't style-file defined
--line 48 of file add.bib
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_WARNING_REGEX, multiline_data, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == """entry type for "thesis_axel-mathieu-mahias" isn't style-file defined"""
    assert matches[0].group(2) == '48'
    assert matches[0].group(3) == 'add.bib'

def test_bib_multiline_command_error():
    testdata = r"""I'm skipping whatever remains of this command
Illegal, another \bibstyle command---line 197 of file main.aux
 : \bibstyle
 :          {splncs04}
I'm skipping whatever remains of this command
I was expecting a `,' or a `}'---line 1371 of file extra.bib
 :       howpublished = {In Eurocrypt 2023}
 :                                         .
I'm skipping whatever remains of this entry
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_COMMAND_ERROR_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == r"Illegal, another \bibstyle command"
    assert matches[0].group(2) == "197"
    assert matches[0].group(3) == "main.aux"
    # ------------------------------------------------------------------------
    testdata = """The style file: alphaurl.bst
I couldn't open database file cryptobib/abbrev3.bib
---line 147 of file main.aux
 : \bibdata{cryptobib/abbrev3
 :                           ,cryptobib/crypto,references}
I'm skipping whatever remains of this command
I found no database files---while reading file main.aux
Reallocated glb_str_ptr (elt_size=4) to 20 items from 10.
"""
    matches = list(re.finditer(BibTexLogParser.MULTILINE_COMMAND_ERROR_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 1
    assert matches[0].group(1) == r"I couldn't open database file cryptobib/abbrev3.bib"
    assert matches[0].group(2) == "147"
    assert matches[0].group(3) == "main.aux"

   
def test_bib_crossref_error():
    testdata = """
A bad cross reference---entry "DBLP:conf/cisc/MouhaWGP11"
refers to entry "DBLP:conf/cisc/2011", which doesn't exist
A bad cross reference---entry "DBLP:conf/crypto/KolblLT15"
refers to entry "DBLP:conf/crypto/2015-1", which doesn't exist
"""
    matches = list(re.finditer(BibTexLogParser.BAD_CROSS_REFERENCE_REGEX, testdata, re.MULTILINE))
    assert len(matches) == 2
    assert matches[0].group(1) == """A bad cross reference---entry "DBLP:conf/cisc/MouhaWGP11"
refers to entry "DBLP:conf/cisc/2011", which doesn't exist"""


def test_bib_badcross():
    with Path('testdata/biblogs/badcross.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 26
        warnings = parser.warnings()
        print(warnings)
        print('error_count=', parser.error_count)
        assert parser.error_count == 13
        assert parser.warning_count == 0

def test_bib_badtypes():
    with Path('testdata/biblogs/badtypes.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 6
        warnings = parser.warnings()
        assert len(warnings) == 6
        assert parser.error_count == len(parser.errors) - len(warnings)
    
def test_bib_badyears():
    with Path('testdata/biblogs/badyears.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 37
        for w in parser.errors:
            assert w.filepath == 'bib.bib'
        warnings = parser.warnings()
        assert len(warnings) == 37
        assert parser.error_count == 0
        assert parser.warning_count == 37
    
def test_bib_commas():
    with Path('testdata/biblogs/commas.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 11
        for w in parser.errors:
            assert w.filepath == 'references.bib'
        warnings = parser.warnings()
        assert len(warnings) == 7
        assert parser.error_count == 4
        assert parser.warning_count == 0
    
def test_bib_comments():
    with Path('testdata/biblogs/comments.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 4
        assert parser.errors[1].filepath == 'bib.bib'
        assert parser.errors[1].filepath_line == 246
        assert parser.errors[1].logline == 12
    
def test_bib_fieldname():
    with Path('testdata/biblogs/fieldname.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 2
        assert parser.errors[1].filepath == 'refs.bib'
        assert parser.errors[1].filepath_line == 407
        assert parser.errors[1].logline == 6
        assert parser.errors[0].filepath == 'bibdiffpriv.bib'
    
def test_bib_greg2():
    with Path('testdata/biblogs/greg2.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 1
        assert parser.errors[0].filepath == 'main.bib'
        assert parser.errors[0].filepath_line == 16
        assert parser.errors[0].logline == 11
    
def test_bib_main1():
    with Path('testdata/biblogs/main1.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 2
        assert parser.errors[0].filepath == 'misc_ref.bib'
        assert parser.errors[0].filepath_line == 0 # unknown
        assert parser.errors[0].logline == 19
    
def test_bib_missing():
    with Path('testdata/biblogs/missing.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 40
        for e in parser.errors:
            assert e.logline > 0
    
def test_bib_multiple():
    with Path('testdata/biblogs/multiple.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 3
        assert parser.errors[0].filepath_line == 38
        assert parser.errors[0].logline == 6
        assert parser.errors[1].logline == 10
        assert parser.errors[2].logline == 14
        for e in parser.errors:
            assert e.logline > 0
            assert e.filepath == 'MITM_bib.bib'
    
def test_bib_period():
    with Path('testdata/biblogs/period.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 3
        assert parser.errors[0].filepath_line == 1347
        assert parser.errors[0].logline == 10
        assert parser.errors[1].logline == 14
        assert parser.errors[2].logline == 18
        for e in parser.errors:
            assert e.logline > 0
            assert e.filepath == 'extra.bib'

def test_bib_strings():
    with Path('testdata/biblogs/strings.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 53
        assert parser.errors[-1].logline == 94
        assert len([e for e in parser.errors if 'booktitle' in e.text]) == 8
        assert len([e for e in parser.errors if 'undefined' in e.text]) == 45
        for i in range(8, len(parser.errors)):
            e = parser.errors[i]
            assert e.filepath_line > 0
            assert e.logline > 0
            assert e.filepath == 'bib.bib'
    
def test_bib_twostyles():
    with Path('testdata/biblogs/twostyles.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 2
    
def test_bib_whitespace():
    with Path('testdata/biblogs/whitespace.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 3
        assert parser.errors[1].filepath == 'main.aux'
        assert parser.errors[2].filepath == 'main.aux'
        assert parser.errors[1].filepath_line == 54
        assert parser.errors[2].filepath_line == 73
        assert 'to sort, need author or key' in parser.errors[0].text
    
def test_bib_nofile():
    with Path('testdata/biblogs/nofile.blg') as f:
        parser = BibTexLogParser()
        parser.parse_file(f, True)
        assert len(parser.errors) == 27
        assert parser.error_count == 2 # because we don't recognize "I found no database files---while reading file main.aux"
        warnings = parser.warnings()
        assert len(warnings) == 0
