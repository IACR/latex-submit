from pathlib import Path
from xml.etree import ElementTree as ET
import xmlschema
import pytest
import sys
from lxml import etree
sys.path.insert(0, '..')
from compilation import Compilation, Meta
from db_models import Journal
from meta_parse import clean_abstract
from xml_meta import get_jats, text_with_texmath, get_jats_abstract, validate_abstract
sys.path.insert(0, '../..')
from config import DebugConfig

_journal = Journal({'EISSN': '3006-5496',
                    'hotcrp_key': 'testhot',
                    'name': 'IACR Communications in Cryptology',
                    'DOI_PREFIX': '10.62056',
                    'acronym': 'CiC',
                    'publisher': 'International Association for Cryptologic Research'})
def test_with_texmath():
    input = "<p>This has $a&lt;b$ and </p><ul><li>first item</li><li>second item</li></ul><p> was a list.</p>"
    output = text_with_texmath(input)
    assert output.count('<p>') == 2
    assert '<tex-math><![CDATA[$a<b$]]></tex-math>' in output

def test_get_jats_abstract():
    input = "<p>This has $a&lt;b$ and </p><ul><li>first item</li><li>second item</li></ul><p> was a list with $$a=b$$ and \\[c=\\alpha\\].</p>"
    elem = get_jats_abstract(input)
    print(ET.tostring(elem))
    children = list(elem.iter())
    assert len(children) == 12
    assert children[0].tag == 'abstract'
    assert children[1].tag == 'p'
    assert children[2].tag == 'tex-math'
    assert children[2].text == '$a<b$'
    assert children[3].tag == 'p'
    assert children[4].tag == 'list'
    assert children[4].attrib['list-type'] == 'bullet'
    assert children[5].tag == 'list-item'
    assert children[6].tag == 'p'
    assert children[6].text == 'first item'
    assert children[7].tag == 'list-item'
    assert children[8].tag == 'p'
    assert children[9].tag == 'p'
    assert children[10].tag == 'tex-math'
    assert children[11].tag == 'tex-math'
    assert children[11].text == r'$$c=\alpha$$'

def test_jats_abstract2():
    input = Path('testdata/abstracts/abstract2.txt').read_text(encoding='UTF-8')
    clean = clean_abstract(input)
    elem = get_jats_abstract(clean)
    tags = list(elem.iter())
    assert len(tags) == 17
    for i in range(len(tags)):
        print(i,tags[i].tag)
    assert tags[0].tag == 'abstract'
    assert tags[1].tag == 'p'
    assert tags[2].tag == 'p'
    assert tags[3].tag == 'tex-math'
    assert tags[4].tag == 'tex-math'
    assert tags[5].tag == 'tex-math'
    assert tags[6].tag == 'tex-math'
    assert tags[7].tag == 'tex-math'
    assert tags[8].tag == 'p'
    assert tags[9].tag == 'p'
    assert tags[10].tag == 'list'
    assert tags[11].tag == 'list-item'
    assert tags[12].tag == 'p'
    assert tags[13].tag == 'list-item'
    assert tags[14].tag == 'p'
    assert tags[15].tag == 'p'
    assert tags[16].tag == 'span'

def test_jats_abstract3():
    input = Path('testdata/abstracts/abstract3.txt').read_text(encoding='UTF-8')
    clean = clean_abstract(input)
    elem = get_jats_abstract(clean)
    tags = list(elem.iter())
    assert len(tags) == 23
    assert tags[3].tag == 'list'
    assert tags[4].tag == 'list-item'
    assert tags[5].tag == 'p'
    assert tags[6].tag == 'list-item'
    assert tags[12].tag == 'tex-math'
    assert tags[13].tag == 'p'
    assert tags[14].tag == 'p'
    assert tags[15].tag == 'list'
    assert tags[16].tag == 'list-item'
    assert tags[17].tag == 'p'
    assert tags[17].text == 'items are ordered when '
    assert tags[18].tag == 'tex-math'
    assert tags[19].tag == 'list-item'
    assert tags[20].tag == 'p'
    assert tags[21].tag == 'list-item'
    assert tags[22].tag == 'p'

def test_jats_creation1():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    json_file = Path('testdata/xml/compilation1.json')
    compilation = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8', errors='replace'))
    article = get_jats(_journal, '1/4/19', compilation)
    journal_meta = article.find('front').find('journal-meta')
    issn = journal_meta.find('journal-id')
    assert issn.text == '3006-5496'
    assert issn.attrib['journal-id-type'] == 'issn'
    issn = journal_meta.find('issn')
    assert issn.attrib['publication-format'] == 'electronic'
    assert issn.text == '3006-5496'
    assert journal_meta.find('journal-title-group').find('journal-title').text == 'IACR Communications in Cryptology'
    assert journal_meta.find('journal-title-group').find('abbrev-journal-title').text == 'CiC'
    assert journal_meta.find('publisher').find('publisher-name').text == 'International Association for Cryptologic Research'
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
    paperids = list(article_meta.iter('article-id'))
    # Should have articleid and doi
    assert len(paperids) == 3
    assert paperids[0].attrib['pub-id-type'] == 'publisher-id'
    assert paperids[0].text == '1/4/19'
    assert paperids[1].attrib['pub-id-type'] == 'custom'
    assert paperids[1].text == 'qcbpxph3'
    assert paperids[2].attrib['pub-id-type'] == 'doi'
    assert paperids[2].text == '10.1729/1234'
    #abstr = article_meta.find('abstract')
    #print(ET.tostring(abstr).decode('utf-8'))
    #assert len(abstr.findall('p')) == 3
    pub_history = article_meta.find('pub-history')
    events = list(pub_history.iter('event'))
    assert len(events) == 2
    assert events[0].find('event-desc').text == 'Received: '
    date = events[0].find('event-desc').find('date')
    assert date.find('year').text == '2022'
    assert date.find('month').text == '08'
    assert date.find('day').text == '03'
    assert events[1].find('event-desc').text == 'Accepted: '
    date = events[1].find('event-desc').find('date')
    assert date.find('year').text == '2022'
    assert date.find('month').text == '09'
    assert date.find('day').text == '30'
    license = article_meta.find('permissions').find('license')
    assert license.attrib['license-type'] == 'open-access'
    assert license.attrib['xlink:href'] == 'https://creativecommons.org/licenses/by/4.0/'
    assert license.find('license-p').text == 'Creative Commons Attribution'
    citations = list(article.iter('ref'))
    assert len(citations) == 33
    ET.indent(article, space=' ', level=1)
    article_bytes = ET.tostring(article, encoding='utf-8').decode('utf-8')
    root = etree.fromstring(article_bytes)
    # with open('testdata/xml/schema/JATS-journalpublishing1-3.dtd', 'r') as schemafile:
    #     dtd = etree.DTD(schemafile)
    #     res = dtd.validate(root)
    #     print(res)
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

def test_jats_creation3():
    schema = etree.XMLSchema(etree.parse('testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd'))
    json_file = Path('testdata/xml/compilation3.json')
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
