import copy
import json
from pathlib import Path
from pydantic import ValidationError
import pytest
import random
import sys
sys.path.insert(0, '../')
from compilation import Compilation, CompileStatus, Author, Affiliation, Meta, Funder, LicenseEnum, License
from meta_parse import clean_abstract, check_bibtex
import datetime
from pathlib import Path
sys.path.insert(0, '../../')
from metadata import _alphabet, _scramble, _unscramble

def test_abstract1():
    input = Path('testdata/abstracts/abstract1.txt').read_text(encoding='UTF-8')
    output = clean_abstract(input)
    assert 'should be removed' not in output
    assert output.count('</p><p>') == 1 # just two paragraphs.
    assert '\n\n' not in output
    assert '\n \n' not in output
    assert '\\begin{comment}' not in output
    assert 'comment environment' not in output
    # \footnote is removed.
    assert 'bye not in output'
    assert '%' in output
    assert ' %' not in output
    # \todo is removed.
    assert 'removable' not in output
    # We might wish to catch this in the future.
    assert 'so is this' in output
    assert 'false' not in output

def test_abstract2():
    output = clean_abstract(Path('testdata/abstracts/abstract2.txt').read_text(encoding='UTF-8'))
    assert 'just a comment' not in output
    assert output.count('</p><p>') == 3 # four paragraphs
    paragraphs = output.split('</p><p>')
    print(json.dumps(paragraphs, indent=2))
    assert len(paragraphs) == 4
    assert '\n\n' not in output
    assert 'a<b' not in output
    assert 'a&lt;b' in output
    assert 'a>b' not in output
    assert 'a&gt;b' in output
    assert r'\begin{comment}' not in output

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
                        'bibtex': output_path.read_text(encoding='UTF-8'),
                        'zipfilename': 'submit.zip'}
    compilation = Compilation(**compilation_data)
    check_bibtex(compilation)
    return compilation

def test_bibtex():
    output_path = Path('testdata/bibtex/ex1/bibitem.bib')
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
    assert len(compilation.warning_log) == 56
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
    assert len(compilation.warning_log) == 1665
    assert len(compilation.error_log) == 0

def test_scramble():
    for l in range(3, 12):
        for i in range(100):
            id = ''.join(random.choices(_alphabet, k=l))
            assert _unscramble(_scramble(id)) == id

def test_author():
    author = Author(name='Fester Bestertester', email='me@example.com')
    assert author.email == 'me@example.com'
    assert author.affiliations == None
    assert author.orcid == None
    assert author.familyName == None
    author2 = Author(name='Neville Nobody', affiliations=[])
    with pytest.raises(ValidationError):
        author = Author(name='Miss Failure',
                        orcid='https://orcid.org/0009-0008-7481-8450')
    with pytest.raises(ValidationError):
        author = Author(name='Miss Failure',
                        orcid='0009000874818450')
    author = Author(name='Miss Failure',
                    orcid='0009-0008-7481-8450',
                    familyName='Failure',
                    affiliations=[1,2])

def test_funder():
    funder = Funder(name='Institute of Idiocy',
                    ror=None,
                    country='US')
    assert funder.fundref == None
    assert funder.ror == None
    assert funder.country == 'US'
    with pytest.raises(ValidationError):
        funder = Funder(name='University of San Carlos',
                        ror='https://ror.org/041jw5813',
                        country='Elbonia')
    funder = Funder(name='University of San Carlos',
                    ror='041jw5813',
                    country='Elbonia',
                    grantid='234119-2023')
    with pytest.raises(ValidationError):
        funder = Funder(name='I')

def test_affiliation():
    affiliation = Affiliation(name='UCLA',
                              ror='012345600',
                              department = 'Department of Mathematics',
                              country='US')
    assert affiliation.name == 'UCLA'
    assert affiliation.ror == '012345600'
    assert affiliation.country == 'US'
    with pytest.raises(ValidationError):
        affiliation = Affiliation(name='UCLA',
                                  ror='https://ror.org/012345600',
                                  department = 'Department of Mathematics',
                                  country='US')
_meta_data = {
    'version': 'final',
    'DOI': '10.1729/az2lkj',
    'URL': 'https://cic.iacr.org/p/1/44',
    'authors': [
        {
            'name': 'Fester Bestertester',
            'affiliations': [1,2]
        },
        {
            'name': 'Miss Failure',
            'orcid': '0009-0008-7481-8450',
            'email': 'failure@iacr.org',
            'affiliations': [3]
        }
    ],
    'affiliations': [
        {
            'name': 'UCLA',
            'country': 'USA'
        },
        {
            'name': 'UCSD',
            'country': 'USA',
            'ror': '012345600'
        },
        {
            'name': 'USC',
            'city': 'Los Angeles',
            'postcode': '90089',
            'country': 'Elbonia'
        }
    ],
    'funders': [
        {
            'name': 'University of San Carlos',
            'ror': '041jw5813',
            'country': 'Elbonia',
            'grantid': '234119-2023'
        }
    ],
    'keywords': ['This', 'that', 'the other'],
    'title': 'The end of the world as we know it',
    'subtitle': 'Film at 11',
    'abstract': 'This is a bogus abstract, but at least it has math: $\\zeta(s)$.',
    'license': {
        'name': 'CC BY-ND',
        'label': 'Creative Commons Attribution-NoDerivs',
        'reference': 'https://creativecommons.org/licenses/by-nd/4.0/'
    }
}

def test_meta():
    meta = Meta(**_meta_data)
    assert meta.license == LicenseEnum.CC_BY_ND.value
    assert meta.subtitle == 'Film at 11'
    assert meta.abstract == 'This is a bogus abstract, but at least it has math: $\\zeta(s)$.'
    assert len(meta.authors) == 2
    assert len(meta.affiliations) == 3
    assert len(meta.funders) == 1
    assert len(meta.keywords) == 3
    assert meta.keywords[1] == 'that'
    with pytest.raises(ValidationError):
        meta1 = copy.deepcopy(_meta_data)
        del meta1['license']
        print(meta1)
        meta = Meta(**meta1)
    meta2 = copy.deepcopy(_meta_data)
    del meta2['title']
    with pytest.raises(ValidationError):
        meta = Meta(**meta2)
    meta2['title'] = 'a'
    meta = Meta(**meta2)
    meta2['title'] = ''
    with pytest.raises(ValidationError):
        meta = Meta(**meta2)
    meta2['title'] = 'asd'
    meta = Meta(**meta2)
    del meta2['license']
    with pytest.raises(ValidationError):
        meta = Meta(**meta2)

_compile_data = {
    'paperid':'foobar',
    'venue': 'cic',
    'email': 'me@example.com',
    'submitted': '2023-10-02 22:13:02',
    'accepted': '2022-01-22 15:05:33',
    'compiled': datetime.datetime(2023, 9, 10, 17, 45, 0),
    'compile_time': 47.2,
    'command': 'lualatex',
    'meta': {
        'version': 'final',
        'title': 'This is the title',
        'authors': [
            {
                'name': 'Fester Bestertester',
                'email': 'fester@example.com'
            },
            {
                'name': 'Gerald Geriatric',
                'orcid': '0000-1111-2222-3333'
            }
        ],
        'affiliations': [
            {
                'name': 'UCLA',
                'ror': '012345600',
                'department': 'Department of Mathematics',
                'country': 'US'
            },
            {
                'name': 'UCSD',
                'country': 'USA'
            }
        ],
        'funders': [
            {
                'name': 'NSF',
                'ror': None,
                'country': 'US'
            },
            {
                'name': 'NIH'
            }
        ],
        'keywords': ['foo', 'fee'],
        'abstract': 'This is an abstract that needs to be sufficiently long',
        'license': {
            'name': 'CC BY-ND',
            'label': 'Creative Commons Attribution-NoDerivs',
            'reference': 'https://creativecommons.org/licenses/by-nd/4.0/'
        }
    },
    'warning_log': [],
    'error_log': [],
    'zipfilename': 'main.zip',
}

def test_compilation():
    comp = Compilation(**_compile_data)
    jsn = comp.model_dump_json(indent=2)
    comp2 = Compilation.model_validate_json(jsn)
    assert comp == comp2
    with pytest.raises(ValidationError):
        compile2 = copy.deepcopy(_compile_data)
        del compile2['command']
        comp = Compilation(**compile2)
    with pytest.raises(ValidationError):
        compile2 = copy.deepcopy(_compile_data)
        del compile2['paperid']
        comp = Compilation(**compile2)
    with pytest.raises(ValidationError):
        compile2 = copy.deepcopy(_compile_data)
        del compile2['warning_log']
        comp = Compilation(**compile2)
    with pytest.raises(ValidationError):
        compile2 = copy.deepcopy(_compile_data)
        del compile2['email']
        comp = Compilation(**compile2)
    with pytest.raises(ValidationError):
        compile2 = copy.deepcopy(_compile_data)
        # check for a valid email.
        compile2['email'] = 'me at iacr.org'
        comp = Compilation(**compile2)
        
def test_license():
    license = LicenseEnum.license_from_iacrcc('CC-by')
    assert license['name'] == 'CC BY'
    assert license['reference'] == 'https://creativecommons.org/licenses/by/4.0/'
    for key in ['CC-by', 'CC-by-sa', 'CC-by-nd', 'CC-by-nc-sa', 'CC-by-nc-nd', 'CC0']:
        assert LicenseEnum.license_from_iacrcc(key) is not None
    with pytest.raises(ValueError):
        license = LicenseEnum.license_from_iacrcc('PD')

