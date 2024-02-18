import json
from pathlib import Path
import pytest
from .bibmarkup import mark_bibtex, bibtex_to_html

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
    print(marked)
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

def test_html():
    bibfile = Path('testdata/test.bib')
    bibstr = bibfile.read_text(encoding='UTF-8')
    data = bibtex_to_html(bibstr)
    print(json.dumps(data, indent=2))
    assert len(data['errors']) == 0
    assert len(data['references']) == 86
