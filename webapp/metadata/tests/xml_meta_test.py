from pathlib import Path
from xml.etree import ElementTree as ET
import xmlschema
import pytest
import sys
from lxml import etree
sys.path.insert(0, '..')
from xml_meta import get_jats, get_crossref
from compilation import Compilation, Meta
from db_models import Journal
sys.path.insert(0, '../..')
from config import DebugConfig

def test_jats_creation1():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    json_file = Path('testdata/xml/compilation1.json')
    compilation = Compilation.parse_raw(json_file.read_text(encoding='UTF-8', errors='replace'))
    article = get_jats(compilation)
    authors = list(article.iter('contrib'))
    assert len(authors) == 5
    affiliations = list(article.iter('aff'))
    assert len(affiliations) == 4
    awards = list(article.iter('award-group'))
    assert len(awards) == 2
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
    compilation = Compilation.parse_raw(json_file.read_text(encoding='UTF-8', errors='replace'))
    article = get_jats(compilation)
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
    compilation = Compilation.parse_raw(json_file.read_text(encoding='UTF-8', errors='replace'))
    compilation.meta.URL = 'https://example.com/crossref'
    journal = Journal({'ISSN': '1234-5678',
                       'key': 'testkey',
                       'name': 'Test Journal',
                       'DOI_PREFIX': '10.1729'})
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
