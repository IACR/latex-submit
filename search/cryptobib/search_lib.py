"""Underlying utility functions for 
1. inserting and updating the database
2. performing a search on the database.

"""

import argparse
from datetime import datetime, timezone, date
from enum import Enum
import json
import sys
import xapian

try:
    from model import Document
except:
    from .model import Document

TITLE_WEIGHT = 5
AUTHOR_WEIGHT = 3
KEYWORD_WEIGHT = 3

class SearchPrefix(Enum):
    TITLE = 'S'
    AUTHOR = 'A'
    NAME = 'P'
    YEAR = 'Y'
    ID = 'Q'

class SlotNumber(Enum):
    SORT_KEY = 0 # sorts by year
    AGE_WEIGHT = 1

def index_document(paper: Document,
                   writable_db,
                   termgenerator=None):
    """Index the paper. It returns no value. It is used by create_index.py.
       args:
          paper: a model.Document
          writable_db: a xapian database. If this is not provided, then
                  app is used to determine the database, open it, and 
                  close it at the end.
          termgenerator: a xapian TermGenerator
    """
    if not termgenerator:
        termgenerator = xapian.TermGenerator()
        termgenerator.set_database(writable_db)
        termgenerator.set_stemmer(xapian.Stem("en"))
        termgenerator.set_flags(termgenerator.FLAG_SPELLING);

    doc = xapian.Document()
    docid = paper.key
    doc.add_boolean_term(docid)
    termgenerator.set_document(doc)

    termgenerator.index_text(paper.title, 1, SearchPrefix.TITLE.value)
    termgenerator.index_text(paper.title, TITLE_WEIGHT)
    termgenerator.increase_termpos()
    termgenerator.index_text(paper.venue)
    termgenerator.increase_termpos()
    termgenerator.index_text(docid, 1, SearchPrefix.ID.value)
    for author in paper.authors:
        termgenerator.increase_termpos()
        termgenerator.index_text(author, 1, SearchPrefix.AUTHOR.value)
        termgenerator.index_text(author, AUTHOR_WEIGHT)
    if paper.year:
        termgenerator.increase_termpos()
        year = paper.year
        termgenerator.index_text(str(year))
        termgenerator.index_text(str(year), 1, SearchPrefix.YEAR.value)
    
    data = paper.model_dump(exclude_unset=True,exclude_none=True)
    # This is a heuristic designed to favor recent papers. I've
    # experimented with different techniques but this one is simple.
    # If you change it, a good rule of thumb is to keep the values
    # below 10 or so; otherwise it will dominate any relevance score.
    current_year = date.today().year
    if paper.year:
        years = current_year + 1 - paper.year
    else:
        years = current_year - 1700
    # One alternative score that worked OK.
    # age_weight = math.sqrt(years)
    # age_weight = 10 * age_weight / (1 + age_weight)
    age_weight = 5 * (1 + years) / (5 + years)
    data['age_weight'] = age_weight
    # Add values in their slots. These are used for scoring and sorting
    doc.add_value(SlotNumber.AGE_WEIGHT.value, xapian.sortable_serialise(round(age_weight, 3)))
    doc.add_value(SlotNumber.SORT_KEY.value, str(paper.year))
    doc.set_data(json.dumps(data, indent=2))
    writable_db.replace_document(docid, doc)
            
if __name__ == '__main__':
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--dbpath',
                           default='./xapian.db',
                           help='Path to writable database directory.')
    arguments.add_argument('--q',
                           help='basic query')
    args = arguments.parse_args()
    if not args.q:
        print('--q is required')
        sys.exit(2)
    results = search(args.dbpath, 0, 100, args.q)
    print(json.dumps(results, indent=2))
