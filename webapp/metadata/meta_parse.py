"""
Library for handling output meta file from compiling latex.
"""

from nameparser import HumanName
from pylatexenc.latex2text import LatexNodes2Text

def get_key_val(line):
    """If line has form key: value, then return key, value."""
    colon = line.find(':')
    if colon < 0:
        raise Exception('Exception: missing colon: {}'.format(line))
    key = line[:colon].strip()
    val = line[colon+1:].strip()
    return key, val
    
def read_meta(metafile):
    """Read the meta file line by line. When we encounter author: or affiliation: or title: or
       citation: we know how to process subsequent lines that start with two spaces.
    args:
       metafile: pathlib.Path pointing at metafile.
    Returns:
        a dict with authors, affiliations, citations and (optionally) editors
    # TODO: define a JSON schema for this file, or return a pydantic object.
    """
    # This is used to decode lines with TeX character macros like \'e.
    decoder = LatexNodes2Text()
    data = {'authors': [],
            'affiliations': [],
            'citations': []}

    with metafile.open() as f:
        line = f.readline().rstrip()
        while line:
            if line.startswith('author:'):
                author = {'affiliations': []}
                data['authors'].append(author)
                line = f.readline().rstrip()
                while line.startswith('  '): # associated with author
                    k,v = get_key_val(line)
                    if k == 'name':
                        author[k] = v
                        v = decoder.latex_to_text(v)
                        parsed = HumanName(v)
                        if parsed:
                            author[k] = str(parsed) # canonicalize name
                            if parsed.last:
                                author['surname'] = parsed.last
                            if parsed.first:
                                author['given'] = parsed.first
                        else: # surname is required, so guess if the parser fails.
                            parts = author[k].split()
                            author['surname'] = parts[-1]
                    elif k == 'email':
                        author['email'] = v
                    elif k == 'affil':
                        author['affiliations'] = [a for a in v.split(',' ) if a.isnumeric()]
                    elif k == 'orcid':
                        author['orcid'] = v.rstrip()
                    line = f.readline().rstrip()
            elif line.startswith('affiliation:'):
                affiliation = {}
                data['affiliations'].append(affiliation)
                line = f.readline().rstrip()
                while line.startswith('  '): # associated with affiliation
                    k,v = get_key_val(line)
                    affiliation[k] = decoder.latex_to_text(v)
                    line = f.readline().rstrip()
            elif line.startswith('version:'):
                data['version'] = line[8:].strip()
                line = f.readline().rstrip()
            elif line.startswith('title:'):
                data['title'] = line[6:].strip() # decoder.latex_to_text(line[6:].strip())
                line = f.readline().rstrip()
                if line.startswith('  '):
                    k,v = get_key_val(line)
                    if k == 'subtitle':
                        data['subtitle'] = v
                        line = f.readline().rstrip()
            elif line.startswith('keywords:'):
                data['keywords'] = line[9:].strip().split('\\and')
                line = f.readline().rstrip()
            elif line.startswith('citation:'):
                parts = line.split()
                assert(len(parts) == 3)
                citation = {'type': parts[1].strip(),
                            'id': parts[2].strip(),
                            'authorlist': []}
                data['citations'].append(citation)
                line = f.readline().rstrip()
                while line.startswith('  '): # associated with citation:
                    k,v = get_key_val(line)
                    if k == 'authors': # Original BibTeX form.
                        citation['authors'] = decoder.latex_to_text(v)
                        line = f.readline().rstrip()
                    elif k == 'author': # separated out by bst
                        author = {'name': decoder.latex_to_text(v)}
                        citation['authorlist'].append(author)
                        line = f.readline().rstrip()
                        k,v = get_key_val(line)
                        if k == 'surname':
                            author['surname'] = decoder.latex_to_text(v)
                            line = f.readline().rstrip()
                    elif k == 'editor':
                        if 'editors' not in citation:
                            citation['editors'] = []
                        editor = {'name': v}
                        citation['editors'].append(editor)
                        line = f.readline().rstrip()
                        k,v = get_key_val(line)
                        if k == 'surname':
                            editor['surname'] = v
                            line = f.readline().rstrip()
                    else:
                        citation[k] = v
                        line = f.readline().rstrip()
            else:
                raise Exception('unexpected line {}'.format(line))
    return data

