from pathlib import Path
from xml.etree import ElementTree as ET
import xmlschema
import pytest
import sys
from lxml import etree
sys.path.insert(0, '..')
from compilation import Compilation, Meta
from db_models import Journal
from xml_meta import get_jats, get_crossref
sys.path.insert(0, '../..')
from config import DebugConfig

_journal = Journal({'EISSN': '1234-5678',
                    'hotcrp_key': 'testhot',
                    'name': 'Test Journal',
                    'DOI_PREFIX': '10.1729',
                    'acronym': 'CiC',
                    'publisher': 'Association of Morons'})
def test_jats_creation1():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    json_file = Path('testdata/xml/compilation1.json')
    compilation = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8', errors='replace'))
    article = get_jats(_journal, '1/19', compilation)
    journal_meta = article.find('front').find('journal-meta')
    issn = journal_meta.find('journal-id')
    assert issn.text == '1234-5678'
    assert issn.attrib['journal-id-type'] == 'issn'
    issn = journal_meta.find('issn')
    assert issn.attrib['publication-format'] == 'electronic'
    assert issn.text == '1234-5678'
    assert journal_meta.find('journal-title-group').find('journal-title').text == 'Test Journal'
    assert journal_meta.find('journal-title-group').find('abbrev-journal-title').text == 'CiC'
    assert journal_meta.find('publisher').find('publisher-name').text == 'Association of Morons'
    authors = list(article.iter('contrib'))
    assert len(authors) == 5
    assert authors[0].attrib['contrib-type'] == 'author'
    assert authors[0].find('string-name').text == 'Mariana Gama'
    orcid = authors[0].find('contrib-id')
    assert orcid.attrib['contrib-id-type'] == 'orcid'
    assert orcid.text == 'https://orcid.org/0000-0002-2759-043X'
    xref = authors[0].find('xref')
    assert xref.attrib['ref-type'] == 'aff'
    assert xref.attrib['rid'] == 'aff1'
    affiliations = list(article.iter('aff'))
    assert len(affiliations) == 4
    first_aff = affiliations[0]
    inst_wrap = first_aff.find('institution-wrap')
    inst_id = inst_wrap.find('institution-id')
    assert inst_id.text == 'https://ror.org/05f950310'
    assert inst_id.attrib['institution-id-type'] == 'ror'
    country = first_aff.find('country')
    assert first_aff.find('city').text == 'Leuven'
    assert first_aff.find('postal-code').text == '3001'
    assert inst_wrap.find('institution').text == 'Computer Security and Industrial Cryptography, KU Leuven'
    assert country.attrib['country'] == 'BE'
    assert country.text == 'Belgium'
    # print(ET.tostring(article.find('front'), encoding='utf-8').decode('utf-8'))
    awards = list(article.iter('award-group'))
    assert len(awards) == 2
    funding_source = awards[0].find('funding-source')
    assert funding_source.attrib['country'] == 'US'
    assert funding_source.find('institution-wrap').find('institution').text == 'Institute for Advanced Study'
    institution_id = funding_source.find('institution-wrap').find('institution-id')
    assert institution_id.attrib['institution-id-type'] == 'doi'
    assert institution_id.attrib['vocab'] == 'open-funder-registry'
    assert institution_id.attrib['vocab-identifier'] == '10.13039/open_funder_registry'
    assert institution_id.text == '10.13039/100005235'
    assert awards[0].find('award-id').text == '29872-22'
    berkeley = awards[1].find('funding-source').find('institution-wrap').find('institution-id')
    assert berkeley.attrib['institution-id-type'] == 'ROR'
    assert berkeley.text == 'https://ror.org/01an7q238'
    article_meta = article.find('front').find('article-meta')
    abstr = article_meta.find('abstract')
    assert len(abstr.findall('p')) == 2
    license = article_meta.find('permissions').find('license')
    assert license.attrib['license-type'] == 'open-access'
    assert license.attrib['xlink:href'] == 'https://creativecommons.org/licenses/by/4.0/'
    assert license.find('license-p').text == 'Creative Commons Attribution'
    citations = list(article.iter('ref'))
    assert len(citations) == 33
    ET.indent(article, space=' ', level=1)
    article_bytes = ET.tostring(article, encoding='utf-8').decode('utf-8')
    root = etree.fromstring(article_bytes)
    try:
        schema.assertValid(root)
    except Exception as e:
        print('error:' + str(e))
        print(schema.error_log)
    assert schema.validate(root) == True

def test_jats_creation2():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    json_file = Path('testdata/xml/compilation2.json')
    compilation = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8', errors='replace'))
    article = get_jats(_journal, '3/5', compilation)
    ET.indent(article, space=' ', level=1)
    article_str = ET.tostring(article, encoding='utf-8').decode('utf-8')
    root = etree.fromstring(article_str)
    try:
        schema.assertValid(root)
    except Exception as e:
        print('error:' + str(e))
        print(schema.error_log)
    assert schema.validate(root) == True

def test_jats_example():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    # This example is supplied with the JATS 1.3 tagset.
    # See https://jats.nlm.nih.gov/publishing/tag-library/1.3d2/chapter/samples.html
    with open('testdata/xml/bmj_sample.xml', 'rb') as f:
        root = etree.parse(f)
        try:
            assert schema.assertValid(root)
        except Exception as e:
            print('error:' + str(e))
            print(schema.error_log)
        assert schema.validate(root) == True

        
def test_crossref_creation1():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/crossref/schema-0.3.1/schemas/crossref5.3.1.xsd'))
    json_file = Path('testdata/xml/compilation1.json')
    compilation = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8', errors='replace'))
    compilation.meta.URL = 'https://example.com/crossref'
    journal = Journal({'EISSN': '1234-5678',
                       'hotcrp_key': 'testkey',
                       'name': 'Test Journal',
                       'DOI_PREFIX': '10.1729',
                       'acronym': 'CiC',
                       'publisher': 'Society of Silly Books'})
    xml = get_crossref('testbatch',
                       'International Association for Testing',
                       'testing@example.com',
                       journal,
                       [compilation])
    authors = list(xml.iter('person_name'))
    assert len(authors) == 5
    affiliations = list(xml.iter('institution'))
    assert len(affiliations) == 7 # institutions are spread through person_name elements.
    citations = list(xml.iter('citation'))
    assert len(citations) == 33
    ET.indent(xml, space=' ', level=1)
    xml_bytes = ET.tostring(xml, encoding='utf-8').decode('utf-8')
    root = etree.fromstring(xml_bytes)
    try:
        schema.assertValid(root)
    except Exception as e:
        print('error:' + str(e))
        print(schema.error_log)
    assert schema.validate(root) == True
