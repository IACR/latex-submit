#!/usr/bin/env python

"""
Main driver for the index build. Note that running this will not
overwrite an existing index specified in args.dbpath. If you are
replacing an existing database, then write it to a temporary location
and then move the directory to the production directory.

This is able to parse both crossref Funder registry and ROR data.

"""

import argparse
import json
from naya import tokenize, stream_array
from pathlib import Path
import os
import requests
import sys
import xapian
from xml.etree import ElementTree as ET
from zipfile import ZipFile

from model import Funder, FunderList, RelationshipType, DataSource
from rdf_parser import parse_rdf
from search_lib import index_funder

assert sys.version_info >= (3,0)

_REGISTRY_RDF = 'data/registry.rdf'
_REGISTRY_JSON = 'data/registry.json'
_RAW_ROR_JSON = 'data/raw_ror.json'
_ROR_JSON = 'data/ror.json'

def create_index(dbpath, funderlist, verbose=False):
    db = xapian.WritableDatabase(dbpath, xapian.DB_CREATE_OR_OPEN)

    # Set up a TermGenerator that we'll use in indexing.
    termgenerator = xapian.TermGenerator()
    termgenerator.set_database(db)
    # use Porter's 2002 stemmer
    termgenerator.set_stemmer(xapian.Stem("english")) 
    termgenerator.set_flags(termgenerator.FLAG_SPELLING);
    count = 0
    for funder in funderlist.funders.values():
        index_funder(funder, db, termgenerator)
        count += 1
        if count % 5000 == 0:
            print(f'{count} funders')
            db.commit()
    db.commit()
    print(f'Indexed {count} documents')

def fetch_fundreg():
    print('fetching {} file...'.format(_REGISTRY_RDF))
    url = 'https://gitlab.com/crossref/open_funder_registry/-/raw/master/registry.rdf?inline=false'
    response = requests.get(url)
    rdf_file = Path(_REGISTRY_RDF)
    rdf_file.write_text(response.text, encoding='UTF-8')
    print('updated registry.rdf file')

def fetch_ror():
    print('fetching ROR data')
    # Apparently we have to use the zenodo schema to determine the date on the latest ROR data.
    response = requests.get('https://zenodo.org/api/records/?communities=ror-data&sort=mostrecent').json()
    print(json.dumps(response, indent=2))
    version_data = response.get('hits').get('hits')[0]
    print(json.dumps(version_data, indent=2))
    publication_date = version_data.get('metadata').get('publication_date')
    print('ROR data from {}'.format(publication_date))
    latest_url = version_data.get('files')[0].get('links').get('self')
    latest_url = latest_url.replace('.json', '_schema_v2.json')
    print('fetching {}'.format(latest_url))
    # latest_url should be a zip file.
    with requests.get(latest_url, stream=True) as stream:
        stream.raise_for_status()
        with open('data/latest.ror.zip', 'wb') as f:
            for chunk in stream.iter_content(chunk_size=65536):
                f.write(chunk)
    with ZipFile('data/latest.ror.zip', 'r') as zipObj:
        namelist = zipObj.namelist()
        zipObj.extractall()
        for fname in namelist:
            if fname.endswith('_schema_v2.json'):
                os.rename(fname, _RAW_ROR_JSON)
            else:
                try:
                    Path(fname).unlink()
                except Exception as e:
                    pass

def extract_ror_id(uri):
    """Extract 0abcdefg12 from https://ror.org/0abcdefg12"""
    return uri.split('/')[-1]

def parse_ror(filename):
    """Return a map from id to potential Funder from ROR. This has
    been modified for v2 of the schema."""
    fp = open(filename, 'r')
    funderslist = FunderList(funders={})
    items = stream_array(tokenize(fp))
    count = 0
    for item in items:
        count += 1
        if count % 5000 == 0:
            print('read {} ror entries'.format(count))
        ror = item.get('id')
        id = extract_ror_id(ror)
        locations = item.get('locations')
        country = locations[0].get('geonames_details')
        names = item.get('names')
        name = None
        altnames = []
        for n in names:
            if 'ror_display' in n['types']:
                name = n['value']
            elif 'acronym' in n['types'] or 'alias' in n['types']:
                altnames.append(n['value'])
        if not name:
            print('missing name in item')
            print(json.dumps(item, indent=2))
            sys.exit(2)

        org = {'source_id': id,
               'source': 'ror',
               'name': name,
               'altnames': altnames,
               'country_code': country.get('country_code'),
               'country': country.get('country_name'),
               'children': [],
               'parents': [],
               'related': []
               }
        if len(item.get('types')) > 0:
            org['funder_type'] = item.get('types')[0].capitalize()
        else:
            org['funder_type'] = 'Other' 
        external_ids = item.get('external_ids')
        for i in external_ids:
            if i['type'] == 'fundref':
                preferred = i.get('preferred')
                if preferred:
                    org['preferred_fundref'] = preferred
        for rel in item['relationships']:
            cap = rel['type'].capitalize()
            if cap == RelationshipType.RELATED.value:
                org['related'].append({'source': DataSource.ROR.value,
                                       'source_id': extract_ror_id(rel['id']),
                                       'name': rel['label']})
            elif cap == RelationshipType.CHILD:
                org['children'].append({'source': DataSource.ROR.value,
                                       'source_id': extract_ror_id(rel['id']),
                                       'name': rel['label']})
            elif cap == RelationshipType.PARENT:
                org['parents'].append({'source': DataSource.ROR.value,
                                       'source_id': extract_ror_id(rel['id']),
                                       'name': rel['label']})
        funder = Funder(**org)
        funderslist.funders[funder.global_id()] = funder
    return funderslist

if __name__ == '__main__':
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--verbose',
                           action='store_true',
                           help='Whether to print debug info')
    arguments.add_argument('--exclude_fundreg',
                           action='store_true',
                           help='Whether to include fundreg (recommended)')
    arguments.add_argument('--fetch_fundreg',
                           action='store_true',
                           help='Whether to fetch a fresh copy with the crossref API')
    arguments.add_argument('--use_cache',
                           action='store_true',
                           help='Use pre-parsed documents')
    arguments.add_argument('--fetch_ror',
                           action='store_true',
                           help='Whether to refetch the json file for ROR')
    arguments.add_argument('--dbpath',
                           default='xapian.db',
                           help='Path to writable database directory.')
    arguments.add_argument('--exclude_dup_fundref',
                           action='store_true',
                           help='Whether to replace Fundref with corresponding ROR')
    arguments.add_argument('--easter_egg',
                           action='store_true',
                           help='Whether to add an easter egg.')
    args = arguments.parse_args()
    ror_file = Path(_ROR_JSON)
    country_map = json.loads(open('data/country_map.json', 'r').read())
    allfunders = FunderList(funders={})
    if args.easter_egg:
        obj = {'source': 'ror',
               'source_id': 'ror_0ohdarn00',
               'name': 'University of Second Choice',
               'country': 'Odarn',
               'funder_type': 'Education',
               'country_code': 'OO',
               'altnames': [],
               'children': [],
               'parents': [],
               'related': []}
        allfunders.funders['ror_0unreal13'] = Funder(**obj)
        print(allfunders.funders)
    if os.path.isfile(args.dbpath) or os.path.isdir(args.dbpath):
        print('CANNOT OVERWRITE dbpath')
        sys.exit(2)
    if args.fetch_fundreg:
        print('updating fundref.rdf...')
        fetch_fundreg()
    if args.fetch_ror:
        print('fetching ror data...')
        fetch_ror()
    if args.exclude_fundreg:
        print('excluding fundreg')
    else:
        funders_json_file = Path(_REGISTRY_JSON)
        if args.use_cache:
            print('reading {}'.format(_REGISTRY_JSON))
            allfunders = FunderList.model_validate_json(funders_json_file.read_text(encoding='UTF-8'))
        else:
            print('parsing {} for fundreg...'.format(_REGISTRY_RDF))
            rdf_file = Path(_REGISTRY_RDF)
            if not rdf_file.is_file():
                fetch_fundreg()
            allfunders = parse_rdf(_REGISTRY_RDF, country_map)
            funders_json_file.write_text(allfunders.model_dump_json(indent=2), encoding='UTF-8')
    ror_funders = FunderList(funders={})
    if args.use_cache:
        print('reading {}'.format(ror_file.name))
        ror_funders = FunderList.model_validate_json(ror_file.read_text(encoding='UTF-8'))
    else:
        if not Path(_RAW_ROR_JSON).is_file():
            fetch_ror()
        print('parsing {}...this is slow to parse 112000 entries...'.format(_ROR_JSON))
        ror_funders = parse_ror(_RAW_ROR_JSON)
        print('saving cache in {}'.format(_ROR_JSON))
        ror_file.write_text(ror_funders.model_dump_json(indent=2), encoding='UTF-8')
    # For now simply add them without merging.
    for key, value in ror_funders.funders.items():
        allfunders.funders[key] = value
        if value.preferred_fundref:
            preferred_fundreg_id = '{}_{}'.format(DataSource.FUNDREG.value, value.preferred_fundref)
            preferred_fundreg = allfunders.funders.get(preferred_fundreg_id)
            if preferred_fundreg and args.exclude_dup_fundref:
                if args.verbose:
                    print('deleting {}:{}'.format(preferred_fundreg_id,
                                                  preferred_fundreg.model_dump_json(indent=2)))
                    print('prefer {}'.format(value.model_dump_json(indent=2)))
                del allfunders.funders[preferred_fundreg_id]
    create_index(args.dbpath, allfunders, args.verbose)

