"""Create JATS content for a paper. We used to create the crossref
XML in this server, but we have now moved it to the hosting server
that knows about the URLS being served.
"""
from datetime import datetime
from io import BytesIO
from nameparser import HumanName
from pathlib import Path
import latex2mathml.converter
import re
from xml.etree import ElementTree as ET
from xml.sax.saxutils import unescape
import xmlschema
from pybtex.database import parse_string, Entry
try:
    from .compilation import Compilation, Meta, PubType
except Exception as e:
    from compilation import Compilation, Meta, PubType
    
try:
    from .countries import country_lookup
except Exception as e:
    from countries import country_lookup
import sys
try:
    from .db_models import Journal
except Exception as e:
    from db_models import Journal

# because of typing hints.
assert sys.version_info >= (3,9)

def _add_jats_citation(index: int, ref_list: ET.Element, entry: Entry):
    ref = ET.SubElement(ref_list, 'ref', attrib={'id': 'ref{}'.format(index)})
    ET.SubElement(ref, 'label').text = entry.key
    citation = ET.SubElement(ref, 'element-citation')
    if entry.persons:
        if 'author' in entry.persons:
            person_group = ET.SubElement(citation, 'person-group', attrib={'person-group-type': 'author'})
            for person in entry.persons['author']:
                name_el = ET.SubElement(person_group, 'name')
                if person.last_names:
                    if person.prelast_names:
                        last_name = ' '.join(person.prelast_names) + ' ' + ' '.join(person.last_names)
                        ET.SubElement(name_el, 'surname').text = last_name
                    else:
                        ET.SubElement(name_el, 'surname').text = ' '.join(person.last_names)
                if person.first_names:
                    ET.SubElement(name_el, 'given-names').text = ' '.join(person.first_names)
        if 'editor' in entry.persons:
            person_group = ET.SubElement(citation, 'person-group', attrib={'person-group-type': 'editor'})
            for person in entry.persons['editor']:
                name_el = ET.SubElement(person_group, 'name')
                if person.last_names:
                    if person.prelast_names:
                        last_name = ' '.join(person.prelast_names) + ' ' + ' '.join(person.last_names)
                        ET.SubElement(name_el, 'surname').text = last_name
                    else:
                        ET.SubElement(name_el, 'surname').text = ' '.join(person.last_names)
                if person.first_names:
                    ET.SubElement(name_el, 'given-names').text = ' '.join(person.first_names)
    if 'year' in entry.fields:
        ET.SubElement(citation, 'year', attrib={'iso-8601-date': str(entry.fields['year'])}).text = str(entry.fields['year'])
    if 'month' in entry.fields:
        ET.SubElement(citation, 'month').text = entry.fields['month']
    if 'doi' in entry.fields:
        doi = entry.fields['doi']
        ET.SubElement(citation, 'pub-id', attrib={'pub-id-type': 'doi',
                                                  'xlink:href': 'https://doi.org/' + doi}).text = doi
    if 'url' in entry.fields:
        ET.SubElement(citation, 'uri').text = entry.fields['url']
        #comment = ET.SubElement(citation, 'comment')
        #ET.SubElement(comment, 'ext-link', attrib={'ext-link-type': 'url',
        #                                           'xlink:href': entry.fields['url']}).text = entry.fields['url']
    if 'pages' in entry.fields:
        parts = [a for a in entry.fields['pages'].split('-') if a]
        ET.SubElement(citation, 'fpage').text = parts[0]
        if len(parts) > 1:
            ET.SubElement(citation, 'lpage').text = parts[1]
    ctype = entry.type.lower() # InProceedings same as inproceedings.
    if ctype == 'article':
        citation.set('publication-type', 'journal')
        if 'title' in entry.fields:
            ET.SubElement(citation, 'article-title').text = entry.fields['title']
        if 'journal' in entry.fields:
            ET.SubElement(citation, 'source').text = entry.fields['journal']
        if 'volume' in entry.fields:
            ET.SubElement(citation, 'volume').text = entry.fields['volume']
        if 'number' in entry.fields:
            ET.SubElement(citation, 'issue').text = entry.fields['number']
    elif ctype == 'inproceedings' or ctype == 'proceedings':
        # see https://jats.nlm.nih.gov/publishing/tag-library/1.3d1/chapter/tag-cite-conf.html
        citation.set('publication-type', 'conference')
        if 'title' in entry.fields:
            ET.SubElement(citation, 'article-title').text = entry.fields['title']
        if 'booktitle' in entry.fields:
            ET.SubElement(citation, 'source').text = entry.fields['booktitle']
        if 'publisher' in entry.fields:
            ET.SubElement(citation, 'conf-sponsor').text = entry.fields['publisher']
        elif 'organization' in entry.fields:
            ET.SubElement(citation, 'conf-sponsor').text = entry.fields['organization']
        if 'series' in entry.fields:
            ET.SubElement(citation, 'series').text = entry.fields['series']
        if 'volume' in entry.fields:
            ET.SubElement(citation, 'volume').text = entry.fields['volume']
        if 'address' in entry.fields:
            ET.SubElement(citation, 'conf-loc').text = entry.fields['address']
    elif ctype == 'book' or ctype == 'booklet':
        citation.set('publication-type', 'book')
        if 'title' in entry.fields:
            ET.SubElement(citation, 'source').text = entry.fields['title']
        if 'publisher' in entry.fields:
            ET.SubElement(citation, 'publisher-name').text = entry.fields['publisher']
        if 'address' in entry.fields:
            ET.SubElement(citation, 'publisher-loc').text = entry.fields['address']
    elif ctype == 'inbook' or ctype == 'incollection':
        citation.set('publication-type', 'book')
        if 'title' in entry.fields:
            ET.SubElement(citation, 'article-title').text = entry.fields['title']
        if 'booktitle' in entry.fields:
            ET.SubElement(citation, 'source').text = entry.fields['booktitle']
        if 'publisher' in entry.fields:
            ET.SubElement(citation, 'publisher-name').text = entry.fields['publisher']
        if 'address' in entry.fields:
            ET.SubElement(citation, 'publisher-loc').text = entry.fields['address']
    else:
        citation.set('publication-type', entry.type)
        if 'title' in entry.fields:
            ET.SubElement(citation, 'source').text = entry.fields['title']
            
def get_jats_abstract(abstr: str) -> str:
    """Take HTML abstract and parse to return JATS abstract element.
    This may throw an exception if it cannot be parsed as XML."""
    abstract_string = '<abstract>' + text_with_texmath(abstr) + '</abstract>'
    abstract_string = abstract_string.replace('<ol>', '<p><list list-type="order">').replace('</ol>', '</list></p>')
    abstract_string = abstract_string.replace('<ul>', '<p><list list-type="bullet">').replace('</ul>', '</list></p>')
    abstract_string = abstract_string.replace('<li>', '<list-item><p>').replace('</li>', '</p></list-item>')
    return ET.parse(BytesIO(abstract_string.encode('UTF-8'))).getroot()

def get_jats(journal: Journal, public_paper_id: str, comp: Compilation) -> ET.Element:
    """TODO: tex-math contents should be CDATA to protect against < inside."""
    article = ET.Element('article', attrib={
        'xmlns:mml': 'http://www.w3.org/1998/Math/MathML',
        'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'article-type': 'correction' if comp.pubtype == PubType.ERRATA else 'research-article',
        'dtd-version': '1.3',
        'xml:lang': 'en'})
    front = ET.SubElement(article, 'front')
    journal_meta = ET.SubElement(front, 'journal-meta')
    if journal.EISSN:
        ET.SubElement(journal_meta, 'journal-id', attrib={'journal-id-type': 'issn'}).text = journal.EISSN
    journal_title_group = ET.SubElement(journal_meta, 'journal-title-group')
    ET.SubElement(journal_title_group, 'journal-title').text = journal.name
    ET.SubElement(journal_title_group, 'abbrev-journal-title').text = journal.acronym
    if journal.EISSN:
        ET.SubElement(journal_meta, 'issn', attrib={'publication-format': 'electronic'}).text = journal.EISSN
    ET.SubElement(ET.SubElement(journal_meta, 'publisher'), 'publisher-name').text = journal.publisher
    meta = comp.meta
    article_meta = ET.SubElement(front, 'article-meta')
    ET.SubElement(article_meta, 'article-id', attrib={'pub-id-type': 'publisher-id'}).text = public_paper_id
    ET.SubElement(article_meta, 'article-id', attrib={'pub-id-type': 'doi'}).text = meta.DOI
    title_group = ET.SubElement(article_meta, 'title-group')
    ET.SubElement(title_group, 'article-title').text = meta.title
    if meta.subtitle:
        ET.SubElement(title_group, 'subtitle').text = meta.subtitle
    cg_elem = ET.SubElement(article_meta, 'contrib-group')
    for author in meta.authors:
        a_elem = ET.SubElement(cg_elem, 'contrib', attrib={'contrib-type': 'author'})
        if author.orcid:
            ET.SubElement(a_elem, 'contrib-id', attrib={'contrib-id-type': 'orcid',
                                                        'authenticated': 'false'}).text = 'https://orcid.org/' + author.orcid
        ET.SubElement(a_elem, 'string-name').text = author.name
        for i in author.affiliations:
            ET.SubElement(a_elem, 'xref', attrib={'ref-type': 'aff', 'rid': 'aff{}'.format(i)})
    for i in range(len(meta.affiliations)):
        aff = meta.affiliations[i]
        aff_elem = ET.SubElement(article_meta, 'aff', attrib={'id': 'aff{}'.format(i+1)})
        inst_wrap = ET.SubElement(aff_elem, 'institution-wrap')
        if aff.department:
            ET.SubElement(inst_wrap, 'institution').text = '{}, {}'.format(aff.department, aff.name)
        else:
            ET.SubElement(inst_wrap, 'institution').text = aff.name
        if aff.ror:
            ET.SubElement(inst_wrap, 'institution-id', attrib={'institution-id-type': 'ror'}).text = 'https://ror.org/' + aff.ror
        if aff.street:
            ET.SubElement(aff_elem, 'addr-line').text = aff.street
        if aff.city:
            ET.SubElement(aff_elem, 'city').text = aff.city
        if aff.country:
            country = ET.SubElement(aff_elem, 'country')
            country.text = aff.country
            iso = country_lookup(aff.country)
            if iso:
                country.set('country', iso)
        if aff.postcode:
            ET.SubElement(aff_elem, 'postal-code').text = aff.postcode
            
    permissions = ET.SubElement(article_meta, 'permissions')
    license = ET.SubElement(permissions, 'license', attrib={'license-type': 'open-access',
                                                            'xlink:href': meta.license.reference})
    ET.SubElement(license, 'license-p').text = meta.license.label
    if comp.pubtype == PubType.ERRATA and comp.errata_doi:
        ET.SubElement(article_meta,
                      'related-article',
                      attrib={'xlink:href': comp.errata_doi,
                              'related-article-type': 'corrected-article',
                              'ext-link-type': 'doi',
                              'xlink:type': 'simple'})
    try:
        abstract_elem = get_jats_abstract(comp.meta.abstract)
        article_meta.append(abstract_elem)
    except Exception as e:
        print(comp.meta.abstract)
        raise ET.ParseError('unable to parse abstract: {}'.format(comp.meta.abstract))
    if meta.keywords:
        kwd_group = ET.SubElement(article_meta, 'kwd-group', attrib={'kwd-group-type': 'author'})
        for kw in meta.keywords:
            ET.SubElement(kwd_group, 'kwd').text = kw
    if meta.funders:
        funding_group = ET.SubElement(article_meta, 'funding-group')
        for funder in meta.funders:
            award_group = ET.SubElement(funding_group, 'award-group')
            funding_source = ET.SubElement(award_group, 'funding-source')
            if funder.country:
                iso = country_lookup(funder.country)
                if iso:
                    funding_source.set('country', iso)
                else:
                    funding_source.set('country', funder.country)
            inst_wrap = ET.SubElement(funding_source, 'institution-wrap')
            if funder.name:
                ET.SubElement(inst_wrap, 'institution').text = funder.name
            if funder.fundref:
                ET.SubElement(inst_wrap, 'institution-id', attrib={'institution-id-type': 'doi',
                                                                   'vocab': 'open-funder-registry',
                                                                   'vocab-identifier': '10.13039/open_funder_registry'}).text = '10.13039/' + funder.fundref
            if funder.ror:
                ET.SubElement(inst_wrap, 'institution-id', attrib={'institution-id-type': 'ROR'}).text = 'https://ror.org/' + funder.ror
            if funder.grantid:
                ET.SubElement(award_group, 'award-id').text = funder.grantid
    ref_list = ET.SubElement(ET.SubElement(article, 'back'), 'ref-list')
    if comp.bibtex:
        bibdata = parse_string(comp.bibtex, 'bibtex')
        counter = 0
        for entry in bibdata.entries.values():
            counter += 1
            _add_jats_citation(counter, ref_list, entry) # this is complicated
    return article


def _to_texmath(mathpart, disp):
    if disp == 'block':
        delim = '$$'
    else:
        delim = '$'
    return '<tex-math><![CDATA[{}{}{}]]></tex-math>'.format(delim,
                                                            mathpart.replace('&lt;', '<').replace('&gt;', '>'),
                                                            delim)

def _to_mathml(mathpart, disp):
    r"""Convert a latex math segment to mathml.
    Args:
       mathpart: latex math-mode segment (without delimiters such as $, $$, or \(
          Note that we expect mathpart to contain &lt; instead of <, and &gt; instead of >.
       disp: 'inline' or 'block' to indicate whether the math is inline or display.
    Returns:
       mathml equivalent, with mml namespace identifier on all XML elements.
    """
    mathpart = mathpart.replace('&lt;', '>').replace('&gt;', '>')
    elem = latex2mathml.converter.convert_to_element(mathpart, display=disp)
    if 'xmlns' in elem.attrib:
        del elem.attrib['xmlns']
    if 'display' in elem.attrib and disp == 'inline':
        del elem.attrib['display']
    output = unescape(ET.tostring(elem, encoding='unicode'))
    return re.sub(r'<(/?)([a-z ="]+)>', r'<\1mml:\2>', output)

def text_with_mathml(input):
    """Input is an abstract with <p> tags only and some HTML-safe latex. In particular
    this means that < was converted to &lt; and > was converted to &gt;, so we need
    to convert those back before running latex
Convert parts in
    LaTeX math mode to mathml. Note that we have to convert &lt; and &gt; back to
    < and > before converting to mathml."""
    input = input.replace('&lt;', '<').replace('&gt;', '>')
    # Break apart at start and end of math mode.
    matches = re.finditer(r'\$\$|\$|\\\(|\\\)|\\\[|\\\]', input)
    last = 0
    start = 0
    end = 0
    output = ''
    in_math = None
    for m in matches:
        se = m.span()
        start = se[0]
        end = se[1]
        previous = input[last:start]
        delim = m.group()
        if in_math:
            output += _to_mathml(previous, in_math)
        else:
            output += previous
        if delim == r'$$':
            if in_math:
                in_math = None
            else:
                in_math = 'block'
        elif delim == r'$':
            if in_math:
                in_math = None
            else:
                in_math = 'inline'
        elif delim == r'\(':
            if in_math:
                raise ValueError('invalid math mode: ' + previous)
            else:
                in_math = 'inline'
        elif delim == r'\[':
            if in_math:
                raise ValueError('invalid math mode: ' + previous)
            else:
                in_math = 'block'
        elif delim == r'\]' or delim == r'\)':
            in_math = None
        last = end
    output += input[last:]
    return output

def text_with_texmath(input):
    """Input is an abstract with HTML-safe LaTex and a few allowed HTML tags, namely <p>,
    <ol>, <ul>, and <li>. In particular this means that mathematical uses of < and > were
    converted to their HTML equivalents &lt; and &gt;. We convert those back to math operators
    before converting the math blocks to <tex-math> blocks that can be used in JATS.
    """
    # Break apart at start and end of math mode.
    matches = re.finditer(r'\$\$|\$|\\\(|\\\)|\\\[|\\\]', input)
    last = 0
    start = 0
    end = 0
    output = ''
    in_math = None
    for m in matches:
        se = m.span()
        start = se[0]
        end = se[1]
        previous = input[last:start]
        delim = m.group()
        if in_math:
            output += _to_texmath(previous, in_math)
        else:
            output += previous
        if delim == r'$$':
            if in_math:
                in_math = None
            else:
                in_math = 'block'
        elif delim == r'$':
            if in_math:
                in_math = None
            else:
                in_math = 'inline'
        elif delim == r'\(':
            if in_math:
                raise ValueError('invalid math mode: ' + previous)
            else:
                in_math = 'inline'
        elif delim == r'\[':
            if in_math:
                raise ValueError('invalid math mode: ' + previous)
            else:
                in_math = 'block'
        elif delim == r'\]' or delim == r'\)':
            in_math = None
        last = end
    output += input[last:]
    return output

def validate_abstract(input: str):
    if '</span>' in input:
        return False
    try:
        elem = get_jats_abstract(input)
    except Exception as e:
        return False
    return True

if __name__ == '__main__':
    import argparse
    argparser = argparse.ArgumentParser(description='xml creator')
    argparser.add_argument('--crossref_file',
                           default = 'crossref.xml')
    argparser.add_argument('--jats_file',
                           default = 'jats.xml')
    argparser.add_argument('--overwrite',
                           action='store_true')
    args = argparser.parse_args()
    json_file = Path('tests/testdata/xml/compilation1.json')
    compilation = Compilation.model_validate_json(json_file.read_text(encoding='UTF-8', errors='replace'))
    journal = Journal({'EISSN': '1234-5678',
                       'hotcrp_key': 'testkey',
                       'acronym': 'TJ',
                       'name': 'Test Journal',
                       'publisher': 'Society of Nonsense',
                       'DOI_PREFIX': '10.1729'})
    from lxml import etree
    article = get_jats(journal, '17/5', compilation)
    ET.indent(article, space='  ', level=1)
    article_str = ET.tostring(article, encoding='utf-8').decode('utf-8')
    jats_file = Path(args.jats_file)
    if args.overwrite or not jats_file.is_file():
        jats_file.write_text(article_str, encoding='utf-8')
    else:
        print('not saving jats file')

    schema_root = etree.parse('tests/testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd')
    schema = etree.XMLSchema(schema_root)
    root = etree.fromstring(article_str)
    try:
        schema.assertValid(root)
        print('jats was validated')
    except Exception as e:
        print('error in jats:' + str(e))
        print(schema.error_log)
                            
