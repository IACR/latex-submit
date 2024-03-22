import json
from pathlib import Path
import pytest
from .bibmarkup import mark_bibtex, bibtex_to_html, BibTeXParser, check_bibtex, BIBCITE_PATT, BIBLATEX_PATT
from .metadata.compilation import CompileStatus, Compilation, PubType
import datetime
import re

def _get_compilation(bibstr):
    data = {'paperid': 'abcdefg',
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
    return Compilation(**data)

def test_markup():
    bibtex = r"""
@article{firstkey,
  title = {This is a title},
  year = 2024,
  booktitle = @crypto2024,
}

@InProceedings{inproc:key,
  title = {The paper title},
}

@manual{oneline title={This is the title} year=2024}

@book{onebook
title="This is the title"
year=1842
}

@misc{ patashnik-bibtexing,
       author = "Oren Patashnik",
       title = "BIBTEXing",
       year = "1988" }

@phdthesis{DBLP:phd/dnb/Fitzi03,
author =        {Matthias Fitzi},
  school =        {{ETH} Zurich, Z{\"{u}}rich, Switzerland},
  title =         {Generalized communication and security models in
                   {Byzantine} agreement},
  year =          {2003},
  biburl =        {https://dblp.org/rec/phd/dnb/Fitzi03.bib},
  bibsource =     {dblp computer science bibliography, https://dblp.org},
  isbn =          {978-3-89649-853-3},
  timestamp =     {Wed, 07 Dec 2016 14:16:47 +0100},
  url =           {http://d-nb.info/967397375},
}

@inproceedings{FOCS:Yao82b,
  author =        {Andrew Chi-Chih Yao},
  booktitle =     {23rd FOCS},
  pages =         {160--164},
  publisher =     {{IEEE} Computer Society Press},
  title =         {Protocols for Secure Computations (Extended
                   Abstract)},
  year =          {1982},
}

"""
    marked = mark_bibtex(bibtex)
    assert '<span id="bibtex:firstkey">@article{firstkey,</span>' in marked
    assert '<span id="bibtex:inproc:key">@InProceedings{inproc:key,</span>' in marked
    # The comma is optional after the key. Who knew?
    assert """<span id="bibtex:oneline">@manual{oneline,</span>
title=""" in marked
    # Notice that we insert a comma when none exists.
    assert """<span id="bibtex:onebook">@book{onebook,</span>
title="This is the title"
""" in marked
    assert '<span id="bibtex:patashnik-bibtexing">@misc{patashnik-bibtexing,</span>' in marked
    assert '<span id="bibtex:DBLP:phd/dnb/Fitzi03">@phdthesis{DBLP:phd/dnb/Fitzi03,</span>' in marked
    assert '<span id="bibtex:FOCS:Yao82b">@inproceedings{FOCS:Yao82b,</span>' in marked

def test_markup_file():
    bibfile = Path('testdata/test.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    marked = mark_bibtex(bibstr)
    print(marked)
    entries = marked.count('@')
    assert entries == 86
    assert entries == bibstr.count('@')
    assert marked.count('<span') == entries

def test_parse():
    bibfile = Path('testdata/test.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0
    assert len(db.entries) == 86

def test_custom():
    bibfile = Path('testdata/bibtex/custom.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 35
    # missing author
    assert len(parser.errors) == 0
    # bad authors tag is not noticed here.
    assert len(parser.warnings) == 0
    comp = _get_compilation(bibstr)
    check_bibtex(comp)
    # print(comp.model_dump_json(indent=2))
    assert len(comp.warning_log) == 13
    assert len(comp.error_log) == 0
    
def test_bibliography():
    bibfile = Path('testdata/bibtex/bibliography.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 38
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0

def test_dana_bib():
    bibfile = Path('testdata/bibtex/dana_bib.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 20
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 0

def test_duplicate():
    bibfile = Path('testdata/bibtex/duplicate.bib')
    bibstr = bibfile.read_text(encoding='utf-8')
    parser = BibTeXParser()
    db = parser.parse_bibtex(bibstr)
    assert len(db.entries) == 525
    assert len(parser.errors) == 0
    assert len(parser.warnings) == 1
    assert parser.warnings[0].text == 'Duplicate bibtex entry: @inproceedings{pcf,'
    bib_path = Path('testdata/bibtex/duplicate.bib')
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
                        'bibtex': bib_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    assert len(compilation.error_log) == 0
    assert compilation.warning_log[4].text == 'bibtex entry parallelhash (Unknown title) requires title field'
    print(compilation.warning_log[4])
    assert len(compilation.warning_log) == 562
    

def test_bibitem():
    bib_path = Path('testdata/bibtex/ex1/bibitem.bib')
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
                        'bibtex': bib_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    for i in range(len(compilation.warning_log)):
        print(i, compilation.warning_log[i].text)
    assert len(compilation.warning_log) == 55
    assert compilation.warning_log[0].text == 'Duplicate bibtex entry: @inproceedings{abed2006vlsi,'

def test_bibitems():
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
    for i in range(len(compilation.warning_log)):
        print(i, compilation.warning_log[i].text)
    count = sum([1 for warning in compilation.warning_log if 'should have year field or date field' in warning.text])
    assert count == 1
    count = sum([1 for warning in compilation.warning_log if 'should have author field' in warning.text])
    assert count == 5
    assert len(compilation.warning_log) == 1591
    assert len(compilation.error_log) == 0

    
def test_html():
    output_path = Path('testdata/bibtex/output2/extracted.bib')
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
    bibdata = check_bibtex(compilation)
    assert len(compilation.error_log) == 0
    assert len(compilation.warning_log) == 2
    bibtex_to_html(compilation, bibdata, Path('testdata/bibtex/output2'))
    assert len(compilation.warning_log) == 2
    assert len(bibdata.entries) == 33
    assert len(compilation.bibhtml) == 33
    

def test_html2():
    output_path = Path('testdata/bibtex/output3/extracted.bib')
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
    bibdata = check_bibtex(compilation)
    assert len(compilation.error_log) == 0
    assert len(compilation.warning_log) == 1
    assert len(bibdata.entries) == 50 # many were dropped
    bibtex_to_html(compilation, bibdata, Path('testdata/bibtex/output3'))
    for entry in compilation.warning_log:
        print(entry)
    assert len(compilation.error_log) == 0
    assert len(compilation.warning_log) == 1
    assert len(compilation.bibhtml) == 50

def test_output1():
    """Test biblatex output looking for labels."""
    aux_str = Path('testdata/bibtex/output1/main.aux').read_text(encoding='UTF-8')
    matches = list(re.finditer(BIBCITE_PATT, aux_str, re.MULTILINE))
    # we don't find \bibcite from bibtex.
    assert len(matches) == 0
    bbl_str = Path('testdata/bibtex/output1/main.bbl').read_text(encoding='UTF-8')
    print(bbl_str)
    matches =list(re.finditer(BIBLATEX_PATT,
                              bbl_str,
                              re.DOTALL|re.MULTILINE))
    # Note: there are two references that did not generate an alpha label
    # under biblatex due to only having a title and no author.
    assert len(matches) == 30

def test_output2():
    aux_str = Path('testdata/bibtex/output2/main.aux').read_text(encoding='UTF-8')
    matches = list(re.finditer(BIBCITE_PATT, aux_str, re.MULTILINE))
    assert len(matches) == 33

def test_output3():
    aux_str = Path('testdata/bibtex/output3/main.aux').read_text(encoding='UTF-8')
    matches = list(re.finditer(BIBCITE_PATT, aux_str, re.MULTILINE))
    # no bibtex \bibcite entries.
    assert len(matches) == 50
    bbl_str = Path('testdata/bibtex/output3/main.bbl').read_text(encoding='UTF-8')
