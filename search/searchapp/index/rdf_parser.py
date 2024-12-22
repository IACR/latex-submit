"""This parses the RDF for the Funders Registry, and produces a FunderMap.
"""

from enum import Enum
import json
import sys
from xml.sax import parse
from xml.sax.handler import ContentHandler
from model import Funder, RelationshipType, DataSource, StrEnum, FunderType, FunderList
from model import add_names_to_relationships
from countries import iso_codes
# This is a map from the values of svf:fundingBodySubType to the
# associated FunderType.  We don't have a schema to define the values
# of svf:fundingBodySubType. They were apparently provided by
# Elsevier.

funderTypeMap = {
    'Associations and societies (private and public)': FunderType.OTHER.value,
    'For-profit companies (industry)': FunderType.COMPANY.value,
    'International organizations': FunderType.OTHER.value,
    'Libraries and data archiving organizations': FunderType.ARCHIVE.value,
    'Local government': FunderType.GOV.value,
    'National government': FunderType.GOV.value,
    'Other non-profit organizations': FunderType.NONPROFIT.value,
    'Research institutes and centers': FunderType.INSTITUTE.value,
    'Trusts, charities, foundations (both public and private)': FunderType.NONPROFIT.value,
    'Universities (academic only)': FunderType.EDU.value}
      
class Tag(str, Enum):
    """XML Tags that we recognize and act on in SAX parser."""
    Concept            = 'skos:Concept'
    literalForm        = 'skosxl:literalForm'
    prefLabel          = 'skosxl:prefLabel'
    altLabel           = 'skosxl:altLabel'
    broader            = 'skos:broader'
    narrower           = 'skos:narrower'
    fundingBodyType    = 'svf:fundingBodyType'
    fundingBodySubType = 'svf:fundingBodySubType'
    addressCountry     = 'schema:addressCountry'
            
class FunderHandler(ContentHandler):
    """Sax parser Handler for parsing registry.rdf."""
    def __init__(self, funderlist, country_map):
        self.funderlist = funderlist
        self.country_map = country_map
        self.item = None
        # Keep track of current tag for characters()
        self.current_tag = None
        self.in_altLabel = False
        self.in_prefLabel = False
        self.content = ''

    def id_from_uri(self, uri):
        return uri.split('/')[-1]

    def startElement(self, name, attrs):
        self.current_tag = name
        if name == Tag.Concept:
            docid = self.id_from_uri(attrs.get('rdf:about'))
            self.item = {'source_id': docid,
                         'source': DataSource.FUNDREG.value,
                         'altnames': [],
                         'children': [],
                         'parents': [],
                         'related': []}
        elif name == Tag.broader:
            self.item['parents'].append({'name': '', # don't know yet
                                         'source': DataSource.FUNDREG.value,
                                         'source_id': self.id_from_uri(attrs.get('rdf:resource'))})
        elif name == Tag.narrower:
            self.item['children'].append({'name': '', # don't know yet
                                          'source': DataSource.FUNDREG.value,
                                          'source_id': self.id_from_uri(attrs.get('rdf:resource'))})
        elif name == Tag.prefLabel:
            self.in_prefLabel = True
        elif name == Tag.altLabel:
            self.in_altLabel = True

    # This is annoying because if you have <foo>This &ampl; that</foo>
    # then it calls characters() three times inside the foo tag. Because
    # of that we simply accumulate the strings inside a tag as self.content
    # and then strip() it in endElement
    def characters(self, content):
        self.content += content

    def endElement(self, name):
        self.content = self.content.strip()
        if name == 'skos:Concept':
            funder = Funder.parse_obj(self.item)
            self.funderlist.funders[funder.global_id()] = funder
            self.item = None
        elif name == Tag.prefLabel:
            self.in_prefLabel = False
        elif name == Tag.altLabel:
            self.in_altLabel = False
        if self.current_tag == Tag.literalForm and self.in_altLabel:
            self.item['altnames'].append(self.content)
        elif self.current_tag == Tag.literalForm and self.in_prefLabel:
            self.item['name'] = self.content
        elif self.current_tag == Tag.fundingBodyType:
            if self.content == 'gov':
                self.item['funder_type'] = FunderType.GOV.value
            elif self.content == 'pri':
                self.item['funder_type'] = FunderType.OTHER.value
            else:
                raise ValueError('unexpected fundingBodyType:' + self.content)
        elif self.current_tag == Tag.fundingBodySubType:
            try:
                self.item['funder_type'] = funderTypeMap[self.content]
            except:
                raise ValueError('unrecognized funder type: ' + self.content)
        elif self.current_tag == Tag.addressCountry:
            self.item['country_code'] = iso_codes[self.content.lower()]['code']
            self.item['country'] = self.country_map.get(self.content, 'unknown')
        self.current_tag = None
        self.content = '' # reset at end of tag.

def parse_rdf(registry_rdf_file, country_map):
    """Parse the registry.rdf file and return a dict.
       args:
          country_map: a dict from iso3 country codes to names
       return:
          a dict with items.
    """
    funderlist = FunderList(funders={})
    handler = FunderHandler(funderlist, country_map)
    parse(registry_rdf_file, handler)
    add_names_to_relationships(funderlist)
    return funderlist

if __name__ == '__main__':
    country_map = json.loads(open('data/country_map.json', 'r').read())
    funderlist = parse_rdf(country_map)
    print(funderlist.model_dump_json(indent=2))
