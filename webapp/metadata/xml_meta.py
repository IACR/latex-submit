from datetime import datetime
from nameparser import HumanName
from pathlib import Path
from xml.etree import ElementTree as ET
import xmlschema
from pybtex.database import parse_string, Entry
from compilation import Compilation, Meta
import country_converter as coco
import sys
from db_models import Journal

# because of typing hints.
assert sys.version_info >= (3,9)

def _get_ref_attr(citation):
    attr = {'publication-format': 'print'}
    if citation.ptype == 'article':
        attr['publication-type'] = 'journal'
    else:
        attr['publication-type'] = 'book'
    if citation.ptype == 'online':
        attr['publication-format'] = 'online'
    elif citation.ptype == 'misc' and citation.url:
        attr['publication-format'] = 'online'
    return attr
        

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
            

def _add_crossref_citation(index: int, citation_list: ET.Element, entry: Entry):
    citation = ET.SubElement(citation_list, 'citation', attrib={'key': 'ref{}'.format(index)})
    if 'issn' in entry.fields:
        ET.SubElement(citation, 'issn', attrib={'media_type': 'electronic'}).text = entry.fields['issn']
    if entry.persons and 'author' in entry.persons:
        # Strangely only one author is accepted, even though the schema says minOccurs=0 and
        # has no maxOccurs. The documentation https://data.crossref.org/reports/help/schema_doc/5.3.1/index.html
        # says that it should be the first author.
        ET.SubElement(citation, 'author').text = str(entry.persons['author'][0])
    if 'journal' in entry.fields:
        ET.SubElement(citation, 'journal_title').text = entry.fields['journal']
    if 'volume' in entry.fields:
        ET.SubElement(citation, 'volume').text = entry.fields['volume']
    if 'issue' in entry.fields:
        ET.SubElement(citation, 'issue').text = entry.fields['issue']
    if 'pages' in entry.fields:
        parts = [a for a in entry.fields['pages'].split('-') if a]
        ET.SubElement(citation, 'first_page').text = parts[0]
    if 'year' in entry.fields:
        ET.SubElement(citation, 'cYear').text = str(entry.fields['year'])
    if 'doi' in entry.fields:
        ET.SubElement(citation, 'doi').text = entry.fields['doi']
    if 'isbn' in entry.fields:
        ET.SubElement(citation, 'isbn').text = entry.fields['isbn']
    if 'series' in entry.fields:
        ET.SubElement(citation, 'series_title').text = entry.fields['series']
    if 'booktitle' in entry.fields:
        ET.SubElement(citation, 'volume_title').text = entry.fields['booktitle']
    if 'title' in entry.fields:
        ET.SubElement(citation, 'article_title').text = entry.fields['title']

def get_jats(comp: Compilation) -> ET.Element:
    meta = comp.meta
    article = ET.Element('article', attrib={
        'xmlns:mml': 'http://www.w3.org/1998/Math/MathML',
        'xmlns:xlink': 'http://www.w3.org/1999/xlink',
        'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
        'article-type': 'research-article',
        'dtd-version': '1.3',
        'xml:lang': 'en'})
    front = ET.SubElement(article, 'front')
    journal_meta = ET.SubElement(front, 'journal-meta')
    ET.SubElement(journal_meta, 'journal-id', attrib={'journal-id-type': 'doi'}).text = '10.1234.5678'
    ET.SubElement(journal_meta, 'journal-id', attrib={'journal-id-type': 'publisher'}).text = 'IACR CiC'
    ET.SubElement(ET.SubElement(journal_meta, 'journal-title-group'),
                  'abbrev-journal-title').text = 'IACR Communications in Cryptology'
    ET.SubElement(journal_meta, 'issn', attrib={'publication-format': 'electronic'}).text = '1234.abcd'
    ET.SubElement(ET.SubElement(journal_meta, 'publisher'), 'publisher-name').text = 'International Association for Cryptologic Research'
    article_meta = ET.SubElement(front, 'article-meta')
    ET.SubElement(article_meta, 'article-id', attrib={'pub-id-type': 'publisher-id'}).text = '2022/197'
    ET.SubElement(article_meta, 'article-id', attrib={'pub-id-type': 'doi'}).text = '10.1233-23423'
    title_group = ET.SubElement(article_meta, 'title-group')
    ET.SubElement(title_group, 'article-title').text = meta.title
    if meta.subtitle:
        ET.SubElement(title_group, 'subtitle').text = meta.subtitle
    cg_elem = ET.SubElement(article_meta, 'contrib-group')
    for i in range(len(meta.affiliations)):
        aff = meta.affiliations[i]
        aff_elem = ET.SubElement(article_meta, 'aff', attrib={'id': 'aff{}'.format(i+1)})
        inst_wrap = ET.SubElement(aff_elem, 'institution-wrap')
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
            iso = coco.convert([aff.country], to='ISO2')
            if iso:
                country.set('country', iso)
        if aff.postcode:
            ET.SubElement(aff_elem, 'postal-code').text = aff.postcode
            
    for author in meta.authors:
        a_elem = ET.SubElement(cg_elem, 'contrib', attrib={'contrib-type': 'author'})
        if author.orcid:
            ET.SubElement(a_elem, 'contrib-id', attrib={'contrib-id-type': 'orcid',
                                                        'authenticated': 'false'}).text = 'https://orcid.org/' + author.orcid
        ET.SubElement(a_elem, 'string-name').text = author.name
        for i in author.affiliations:
            ET.SubElement(a_elem, 'xref', attrib={'ref-type': 'aff', 'rid': 'aff{}'.format(i)})
    permissions = ET.SubElement(article_meta, 'permissions')
    license = ET.SubElement(permissions, 'license', attrib={'license-type': 'open-access',
                                                            'xlink:href': meta.license.reference})
    ET.SubElement(license, 'license-p').text = meta.license.label
    abstract = ET.SubElement(article_meta, 'abstract')
    for paragraph in meta.abstract.split('\n\n'):
        ET.SubElement(abstract, 'p').text = paragraph
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
                iso = coco.convert([funder.country], to='ISO2')
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


def _add_crossref_article_meta(comp: Compilation,
                               journal_elem: ET.Element):
    """Add a journal_article element for an article."""
    journal_article = ET.SubElement(journal_elem, 'journal_article', attrib={'language': 'en',
                                                                             'publication_type': 'abstract_only',
                                                                             'reference_distribution_opts': 'any'})
    ET.SubElement(ET.SubElement(journal_article, 'titles'), 'title').text = comp.meta.title
    contributors = ET.SubElement(journal_article, 'contributors')
    for i in range(len(comp.meta.authors)):
        author = comp.meta.authors[i]
        person_name = ET.SubElement(contributors, 'person_name', attrib={'contributor_role': 'author'})
        if i == 0:
            person_name.set('sequence', 'first')
        else:
            person_name.set('sequence', 'additional')
        human_name = HumanName(author.name)
        if human_name:
            ET.SubElement(person_name, 'given_name').text = human_name.first
            ET.SubElement(person_name, 'surname').text = human_name.last
        else:
            parts = author.name.split(' ')
            ET.SubElement(person_name, 'given_name').text = parts[0]
            ET.SubElement(person_name, 'surname').text = parts[-1]
        affiliations = ET.SubElement(person_name, 'affiliations')
        for j in range(len(author.affiliations)):
            aff = comp.meta.affiliations[j]
            if aff.ror:
                ET.SubElement(ET.SubElement(affiliations, 'institution'), 'institution_id', attrib={'type': 'ror'}).text = 'https://ror.org/' + aff.ror
            else:
                institution = ET.SubElement(affiliations, 'institution')
                ET.SubElement(institution, 'institution_name').text = aff.name
                if aff.country:
                    location = []
                    if aff.street:
                        location.append(aff.street)
                    if aff.city:
                        location.append(aff.city)
                    if aff.postcode:
                        locationappend(aff.postcode)
                    if aff.country:
                        location.append(aff.country)
                    if location:
                        ET.SubElement(institution, 'institution_place').text = ', '.join(location)
                    if aff.department:
                        ET.SubElement(institution, 'institution_department').text = aff.department
        if author.orcid:
            ET.SubElement(person_name, 'ORCID',
                          attrib={'authenticated': 'false'}).text = 'https://orcid.org/' + author.orcid
    # I could not get the content to validate, perhaps because it needs at least one <p> element and one
    # <sec> element. By contrast, These abstracts work against the JATS schema.
    abstract = ET.SubElement(journal_article, 'abstract', attrib={'xmlns':'http://www.ncbi.nlm.nih.gov/JATS1'})
    for paragraph in comp.meta.abstract.split('\n\n'):
        ET.SubElement(abstract, 'p').text = paragraph
    publication_date = ET.SubElement(journal_article, 'publication_date', attrib={'media_type': 'online'})
    parts = datetime.now().strftime('%Y-%m-%d').split('-')
    ET.SubElement(publication_date, 'month').text = parts[1]
    ET.SubElement(publication_date, 'day').text = parts[2]
    ET.SubElement(publication_date, 'year').text = parts[0]
    acceptance_date = ET.SubElement(journal_article, 'acceptance_date', attrib={'media_type': 'online'})
    parts = comp.accepted.split(' ')[0].split('-')
    ET.SubElement(acceptance_date, 'month').text = parts[1]
    ET.SubElement(acceptance_date, 'day').text = parts[2]
    ET.SubElement(acceptance_date, 'year').text = parts[0]
    ET.SubElement(ET.SubElement(journal_article, 'publisher_item'), 'item_number', attrib={'item_number_type': 'article_number'}).text = comp.paperid
    # TODO: add crossmark with funders
    # TODO: add archive_locations
    doi_data = ET.SubElement(journal_article, 'doi_data')
    ET.SubElement(doi_data, 'doi').text = comp.meta.DOI
    ET.SubElement(doi_data, 'resource', attrib={'content_version': 'vor',
                                                'mime_type': 'text/html'}).text = comp.meta.URL
    if comp.bibtex:
        citation_list = ET.SubElement(journal_article, 'citation_list')
        bibdata = parse_string(comp.bibtex, 'bibtex')
        counter = 0
        for entry in bibdata.entries.values():
            counter += 1
            _add_crossref_citation(counter, citation_list, entry)


def get_crossref(batchid: str,
                 publisher_name: str,
                 publisher_email: str,
                 journal: Journal,
                 compilations: list[Compilation]) -> ET.Element:
    """Crossref XML file for registering a batch of DOIs."""
    
    doi_batch = ET.Element('doi_batch', attrib={'xmlns:xsi': 'http://www.w3.org/2001/XMLSchema-instance',
                                                'xsi:schemaLocation': 'http://www.crossref.org/schema/5.3.0 https://www.crossref.org/schemas/crossref5.3.1.xsd',
                                                'xmlns': 'http://www.crossref.org/schema/5.3.1',
                                                'xmlns:jats': 'http://www.ncbi.nlm.nih.gov/JATS1',
                                                'xmlns:fr': 'http://www.crossref.org/fundref.xsd',
                                                'xmlns:mml': 'http://www.w3.org/1998/Math/MathML',
                                                'version': '5.3.1'})
    head = ET.SubElement(doi_batch, 'head')
    ET.SubElement(head, 'doi_batch_id').text = batchid
    ET.SubElement(head, 'timestamp').text = datetime.now().strftime('%Y%m%d%H%M%S%f')
    depositor = ET.SubElement(head, 'depositor')
    ET.SubElement(depositor, 'depositor_name').text = publisher_name
    ET.SubElement(depositor, 'email_address').text = publisher_email
    ET.SubElement(head, 'registrant').text = publisher_name
    body = ET.SubElement(doi_batch, 'body')
    journal_elem = ET.SubElement(body, 'journal')
    journal_metadata = ET.SubElement(journal_elem, 'journal_metadata', attrib={'language': 'en',
                                                                               'reference_distribution_opts': 'any'})
    ET.SubElement(journal_metadata, 'full_title').text = journal.name
    ET.SubElement(journal_metadata, 'issn', attrib={'media_type': 'electronic'}).text = journal.EISSN
    # TOD: The Journal needs a DOI as well as the article?
    for comp in compilations:
        _add_crossref_article_meta(comp, journal_elem)
    return doi_batch

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
    compilation.meta.URL = 'https://example.com/thepaper'
    article = get_jats(compilation)
    #article = ET.parse('bmj_sample.xml').getroot()
    ET.indent(article, space='  ', level=1)
    #article_str = ET.tostring(article, encoding='utf-8', xml_declaration=True).decode('utf-8')
    article_str = ET.tostring(article, encoding='utf-8').decode('utf-8')
    jats_file = Path(args.jats_file)
    if args.overwrite or not jats_file.is_file():
        jats_file.write_text(article_str, encoding='utf-8')
    else:
        print('not saving jats file')
    #xsd = xmlschema.XMLSchema('tests/testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd')
    #for err in xsd.iter_errors(article):
    #    print(err)
    #    if not err.reason.startswith("'xlink:href' attribute not allowed for element"):
    #xsd.validate(article)
    #print(xsd.is_valid(article))

    from lxml import etree
    schema_root = etree.parse('tests/testdata/xml/schema/JATS-journalpublishing1-3-mathml3.xsd')
    schema = etree.XMLSchema(schema_root)
    root = etree.fromstring(article_str)
    try:
        schema.assertValid(root)
        print('jats was validated')
    except Exception as e:
        print('error in jats:' + str(e))
        print(schema.error_log)
    journal = Journal({'EISSN': '1234-5678',
                       'hotcrp_key': 'testkey',
                       'acronym': 'TJ',
                       'name': 'Test Journal',
                       'DOI_PREFIX': '10.1729'})
    crossref = get_crossref('testbatch',
                            'International Association for Cryptologic Research',
                            'crossref@iacr.org',
                            journal,
                            [compilation])
    ET.indent(crossref, space='  ', level=0)
    crossref_str = ET.tostring(crossref, encoding='utf-8').decode('utf-8')
    crossref_file = Path(args.crossref_file)
    if args.overwrite or not crossref_file.is_file():
        crossref_file.write_text(crossref_str,
                                 encoding='utf-8')
    else:
        print('not saving crossref file')
    schema_root = etree.parse('tests/testdata/xml/schema/crossref/schema-0.3.1/schemas/crossref5.3.1.xsd')
    schema = etree.XMLSchema(schema_root)
    root = etree.fromstring(crossref_str)
    try:
        schema.assertValid(root)
        print('crossref was validated')
    except Exception as e:
        print('error in crossref: ' + str(e))
        print(schema.error_log)
                            
