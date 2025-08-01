import io
import json
import os
from pathlib import Path
import pytest
import sys
sys.path.insert(0, '../')
from compilation import Meta, LicenseEnum, VersionEnum
sys.path.insert(0, '../latex/iacrcc/parser')
from meta_parse import parse_meta

def test_meta1():
    tfile = Path('testdata/test1.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    data['abstract'] = 'This came from an abstract file'
    data['version'] = 'final'
    assert 'license' in data
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    print('test data=', data)
    with pytest.raises(ValueError):
        meta = Meta(**data)
    data['authors'][0]['email'] = 'alice@wonderland.com'
    meta = Meta(**data)
    assert meta.title == 'Thoughts about "binary" functions on $GF(p)$ by Fester Bestertester at 30°C'
    assert len(meta.authors) == 3
    assert meta.authors[0].email == 'alice@wonderland.com'
    assert meta.authors[0].name == 'Alice Accomplished'
    print('meta.authors[0]=', meta.authors[0])
    assert meta.authors[0].familyName == 'Accomplished'
    assert meta.authors[0].orcid == '0000-0003-1010-8157'
    assert meta.authors[1].orcid == None
    assert meta.authors[2].orcid == None
    assert meta.affiliations[0].state == 'California'
    assert meta.affiliations[2].city == 'Boğaziçi'
    assert meta.affiliations[2].street == 'Road to nowhere'
    assert meta.affiliations[2].department == 'Department of Mathematics'

def test_meta2():
    tfile = Path('testdata/test2.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    data['abstract'] = 'This came from an abstract file'
    data['version'] = 'preprint'
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    meta = Meta(**data)
    assert meta.title == 'How to Use the IACR Communications in Cryptology Class'
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
    tfile = Path('testdata/test3.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    data['abstract'] = 'This came from an abstract file'
    data['version'] = 'submission'
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    meta = Meta(**data)
    assert meta.title == 'Another example with biblatex'
    assert len(meta.authors) == 1
    assert meta.authors[0].email == 'nobody@example.com'
    assert meta.authors[0].name == 'Fester Bestertester'
    assert meta.authors[0].orcid == '0000-0002-0599-0192'
    assert len(meta.authors[0].affiliations) == 0
    assert len(meta.affiliations) == 0

def test_meta4():
    tfile = Path('testdata/test4.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    data['abstract'] = 'We added an abstract'
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    meta = Meta(**data)
    assert meta.title == 'How not to use the IACR Communications in Cryptology Clåss'
    assert len(meta.authors) == 2
    assert meta.authors[0].email == 'joppe.bos@nxp.com'
    assert meta.authors[0].name == 'Joppe W. Bös'
    assert meta.authors[0].orcid == '0000-0003-1010-8157'
    assert len(meta.authors[0].affiliations) == 1
    assert len(meta.affiliations) == 3
    assert len(meta.funders) == 3
    assert meta.funders[0].name == 'Horizon 2020 Framework Programme'
    assert meta.funders[0].country == 'Elbonia'
    assert meta.funders[0].ror == None
    assert meta.funders[0].grantid == '5211-2'
    assert meta.funders[0].fundref == '1241171'
    assert meta.funders[1].name == 'Just another foundation'
    assert meta.funders[1].country == 'United States'
    assert meta.funders[1].ror == '042c84f31'
    assert meta.funders[1].fundref == None
    assert meta.funders[2].name == 'National Fantasy Foundation'
    assert meta.funders[2].country == None
    assert meta.funders[2].ror == None
    assert meta.funders[2].fundref == '517622'
    assert meta.funders[2].grantid == '57821-3'

def test_meta5():
    tfile = Path('testdata/test5.meta').read_text(encoding='UTF-8')
    with pytest.raises(ValueError):
        # This is invalid because an index for affiliation is out of range.
        data = parse_meta(tfile)

def test_meta6():
    tfile = Path('testdata/test6.meta').read_text(encoding='UTF-8')
    with pytest.raises(ValueError):
        # This is invalid because an index for affiliation is out of range.
        data = parse_meta(tfile)

def test_meta7():
    ## This one has affil: 1, 2
    tfile = Path('testdata/test7.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    data['abstract'] = 'We added an abstract'
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    meta = Meta(**data)
    assert len(meta.authors) == 2
    assert len(meta.authors[0].affiliations) == 1
    assert len(meta.authors[1].affiliations) == 2
    assert meta.authors[1].affiliations[0] == 1
    assert meta.authors[1].affiliations[1] == 2
    assert len(meta.affiliations) == 2

def test_meta8():
    tfile = Path('testdata/test8.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    print(data)
    data['abstract'] = 'We added an abstract'
    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
    meta = Meta(**data)

def test_meta9():
    tfile = Path('testdata/test9.meta').read_text(encoding='UTF-8')
    data = parse_meta(tfile)
    print(data)
    data['abstract'] = 'We added an abstract'
    data['license'] = LicenseEnum.license_from_spdx(data['license'])
    meta = Meta(**data)
    assert meta.affiliations[0].countrycode == 'BE'
    assert meta.funders[0].countrycode == 'US'
    # set by default
    assert meta.version == VersionEnum.FINAL
    
