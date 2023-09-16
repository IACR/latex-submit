"""Utility functions for 
1. inserting and updating the database
2. performing a search on the database.

This is imported from the UI as well as create_index.py
"""

import argparse
from datetime import datetime, timezone
from enum import Enum
import json
import math
import sys
import xapian
#from flask import current_app as app

# where we store the source for sorting.
SLOT_NUMBER = 0
# We give extra weight to terms in name
NAME_WEIGHT = 10

class SearchPrefix(str, Enum):
    NAME = 'S'
    LOCATION = 'K'
    ORGTYPE = 'O'
    ID = 'Q'
    SOURCE = 'XS'

def index_funder(funder, writable_db=None, termgenerator=None):
    """Index the funder. It returns no value. It is used by create_index.py.
       args:
          funder: a Funder from model.py
          writable_db: a xapian database. If this is not provided, then
                  the database is opened and closed at the end. This is
                  only useful for indexing individual items that are updated.
          termgenerator: a xapian TermGenerator
    """
    if not termgenerator:
        termgenerator = xapian.TermGenerator()
        termgenerator.set_database(writable_db)
        termgenerator.set_stemmer(xapian.Stem("en"))
        termgenerator.set_flags(termgenerator.FLAG_SPELLING);

    doc = xapian.Document()
    docid = funder.global_id()
    doc.add_boolean_term(docid)
    doc.add_boolean_term(SearchPrefix.SOURCE.value + funder.source.value)
    # We sort on SLOT_NUMBER
    slot_value = '1' if funder.source.value == 'fundreg' else '0'
    doc.add_value(SLOT_NUMBER, slot_value)
    termgenerator.set_document(doc)

    name = funder.name
    termgenerator.index_text(name, 1, SearchPrefix.NAME.value)
    termgenerator.index_text(name, NAME_WEIGHT)

    termgenerator.increase_termpos()
    for altname in funder.altnames:
        termgenerator.index_text(altname, 1, SearchPrefix.NAME.value)
        termgenerator.index_text(altname, NAME_WEIGHT)
    for child in funder.children:
        termgenerator.index_text(child.name, 1, SearchPrefix.NAME.value)
        termgenerator.index_text(child.name, NAME_WEIGHT)
    
    termgenerator.increase_termpos()
    location = funder.country
    termgenerator.index_text(location, 1, SearchPrefix.LOCATION.value)
    termgenerator.increase_termpos()

    termgenerator.increase_termpos()
    orgtype = funder.funder_type.value
    termgenerator.index_text(orgtype, 1, SearchPrefix.ORGTYPE.value)

    termgenerator.increase_termpos()
    termgenerator.index_text(docid, 1, SearchPrefix.ID.value)

    data = funder.dict()
    data['id'] = docid
    data['source_id']
    doc.set_data(json.dumps(data, indent=2))
    writable_db.replace_document(docid, doc)

def search(db_path, offset=0, limit=1000, textq=None, locationq=None, source=None, app=None):
    """Execute a query on the index. At least one of textq or locationq
    must be non-None.

    Args:
       db_path: path to database
       offset: starting offset for paging of results
       textq: raw query string from the user to be applied to any text field
       locationq: raw query for location field
    Returns: dict with the following:
       error: string if an error occurs (no other fields in this case)
       parsed_query: debug parsed query
       estimated_results: number of total results available
       results: an array of results
    """
    if (not textq and not locationq):
        return {'estimated_results': 0,
                'parsed_query': '',
                'spell_corrected_query': '',
                'sort_order': '',
                'results': []}
    db = None
    try:
        # Open the database we're going to search.

        db = xapian.Database(db_path)

        # Set up a QueryParser with a stemmer and suitable prefixes
        queryparser = xapian.QueryParser()
        queryparser.set_database(db)
        queryparser.set_stemmer(xapian.Stem("en"))
        queryparser.set_stemming_strategy(queryparser.STEM_SOME)
        # Allow users to type id:1001022
        queryparser.add_prefix('id', SearchPrefix.ID.value)

        # flags are described here: https://getting-started-with-xapian.readthedocs.io/en/latest/concepts/search/queryparser.html
        # FLAG_BOOLEAN enables boolean operators AND, OR, etc in the query
        # FLAG_LOVEHATE enables + and -
        # FLAG_PHRASE enables enclosing phrases in "
        # FLAG_WILDCARD enables things like * signature scheme to expand the *
        flags = queryparser.FLAG_SPELLING_CORRECTION | queryparser.FLAG_BOOLEAN | queryparser.FLAG_LOVEHATE | queryparser.FLAG_PHRASE | queryparser.FLAG_WILDCARD
        # we build a list of subqueries and combine them later with AND.
        if not textq and not locationq:
            return {'error': 'missing query'}
        query_list = []
        if textq:
            query_list.append(queryparser.parse_query(textq, flags))
        if locationq:
            location_query = queryparser.parse_query(locationq, flags, SearchPrefix.LOCATION.value)
            query_list.append(location_query)
        query = xapian.Query(xapian.Query.OP_AND, query_list)
        if source: # filter on this source value.
            source_query = xapian.Query(SearchPrefix.SOURCE.value + source)
            query = xapian.Query(xapian.Query.OP_FILTER, query, source_query)
        # Use an Enquire object on the database to run the query
        enquire = xapian.Enquire(db)
        enquire.set_query(query)
        res = {'parsed_query': str(query)}
        # Use source then relevance score.
        # enquire.set_sort_by_value_then_relevance(SLOT_NUMBER, True)
        enquire.set_sort_by_relevance()
        res['sort_order'] = 'sorted by relevance'
        matches = []
        # Retrieve the matched set of documents.
        mset = enquire.get_mset(offset, limit, 1000)
        for match in mset:
            item = {'docid': match.docid,
                    'rank': match.rank,
                    'weight': match.weight,
                    'percent': match.percent}
            fields = json.loads(match.document.get_data().decode())
            for k,v in fields.items():
                item[k] = v
            matches.append(item)
        res['estimated_results'] = mset.get_matches_estimated()
        res['results'] = matches
        spell_corrected = queryparser.get_corrected_query_string()
        if spell_corrected:
            res['spell_corrected_query'] = spell_corrected.decode('utf-8')
        else:
            res['spell_corrected_query'] = ''
        db.close()
        return res
    except Exception as e:
        if app:
            app.logger.critical('Error in search: {}'.format(str(e)))
        if db:
            db.close()
        return {'error': 'Error in server:' + str(e)}
                            
            
if __name__ == '__main__':
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--dbpath',
                           default='./xapian.db',
                           help='Path to writable database directory.')
    arguments.add_argument('--name',
                           help='basic query')
    arguments.add_argument('--location',
                           help='query restricted to location')
    arguments.add_argument('--source',
                           help='ror or fundreg or None')
    args = arguments.parse_args()
    if not args.name and not args.location:
        print('one of --name or --location is required')
        sys.exit(2)
    results = search(args.dbpath, 0, 100, args.name, args.location, args.source)
    print(json.dumps(results, indent=2))
