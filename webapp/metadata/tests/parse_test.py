import glob
import io
import json
import os
from pathlib import Path
import pytest
import sys
sys.path.insert(0, '../')
from meta_parse import read_meta
from compilation import Meta

def test_meta1():
    tfile = Path('testdata/test1.meta')
    data = read_meta(tfile)
    meta = Meta(**data)
    assert meta.title == 'Thoughts about "binary" functions on $GF(p^2)$ by Fester Bestertester\\ at 30°C'
    assert len(meta.citations) == 12
    assert len(meta.authors) == 3
    assert meta.authors[0].email == 'alice@wonderland.com'
    assert meta.authors[0].name == 'Alice Accomplished'
    assert meta.authors[0].orcid == '0000-0003-1010-8157'
    assert meta.authors[1].orcid == None
    assert meta.authors[2].orcid == None

def test_meta2():
    tfile = Path('testdata/test2.meta')
    data = read_meta(tfile)
    meta = Meta(**data)
    assert meta.title == 'How to Use the {IACR} Communications in Cryptology Class'
    assert len(meta.citations) == 6
    assert len(meta.authors) == 2
    assert meta.authors[0].email == 'joppe.bos@nxp.com'
    assert meta.authors[0].name == 'Joppe W. Bos'
    assert meta.authors[0].orcid == '0000-0003-1010-8157'
    assert meta.authors[1].email == 'mccurley@digicrime.com'
    assert meta.authors[1].name == 'Kevin S. McCurley'
    assert meta.authors[1].orcid == '0000-0001-7890-5430'
    assert len(meta.affiliations) == 2
    assert meta.affiliations[0].name == 'NXP Semiconductors'
    assert meta.affiliations[0].ror == '031v4g827'
    assert meta.affiliations[0].street == 'Interleuvenlaan 80'
    assert meta.affiliations[0].city == 'Leuven'
    assert meta.affiliations[0].postcode == '3001'
    assert meta.affiliations[0].country == 'Belgium'


def test_meta3():
    tfile = Path('testdata/test3.meta')
    data = read_meta(tfile)
    meta = Meta(**data)
    assert meta.title == 'Another example with biblatex'
    assert len(meta.citations) == 79
    assert len(meta.authors) == 1
    assert meta.authors[0].email == 'nobody@example.com'
    assert meta.authors[0].name == 'Fester Bestertester'
    assert meta.authors[0].orcid == '0000-0002-0599-0192'
    assert len(meta.authors[0].affiliations) == 0
    assert len(meta.affiliations) == 0
