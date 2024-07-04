from pathlib import Path
from pylatexenc.latex2text import LatexNodes2Text
import bibtexparser
from bibtexparser.model import Entry, Field, String
from bibtexparser.middlewares import BlockMiddleware, LibraryMiddleware, RemoveEnclosingMiddleware
import re
from bibtexparser.middlewares.interpolate import _value_is_nonstring_or_enclosed
from model import Document
from search_lib import index_document

class StringExpansionMiddleware(LibraryMiddleware):
    """Replace string references in Strings and values. We split on the # character inside both."""
    def __init__(self):
        """We use _strings to keep track of strings we have seen and expand them further.
        This splits strings by the concatenation operator '#' and replaces things successively."""
        self._months = {
            'jan': 'January',
            'feb': 'February',
            'mar': 'March',
            'apr': 'April',
            'may': 'May',
            'jun': 'June',
            'jul': 'July',
            'aug': 'August',
            'sep': 'September',
            'oct': 'October',
            'nov': 'November',
            'dec': 'December'}
        super().__init__()
    def transform(self, library):
        # expand strings inside strings.
        for key, value in self._months.items():
            library.add(String(key, value))
        string_dict = library.strings_dict
        for s in library.strings:
            parts = re.split(r' # ', s.value)
            vals = []
            for part in parts:
                spart = part.strip('"')
                if spart in string_dict:
                    vals.append(string_dict[spart].value)
                else:
                    vals.append(spart)
            s._value = ''.join(vals)
        for entry in library.entries:
            resolved_fields = list()
            for field in entry.fields:
                if _value_is_nonstring_or_enclosed(field.value):
                    continue
                vals = []
                parts = re.split(r' # ', field.value)
                expanded = False
                for part in parts:
                    spart = part.strip('"')
                    if spart in string_dict:
                        expanded = True
                        vals.append(string_dict[spart].value.strip('"'))
                    else:
                        vals.append(spart)
                if expanded:
                    field.value = ''.join(vals)
                if field.value not in library.strings_dict:
                    continue
                field.value = library.strings_dict[field.value].value
                resolved_fields.append(field.key)

            if resolved_fields:
                entry.parser_metadata[self.metadata_key()] = resolved_fields

        return library
                                
class CrossrefMiddleware(LibraryMiddleware):
    def __init__(self):
        super().__init__()
       
    def transform(self, library):
        entries = library.entries_dict
        for entry in library.entries:
            fields_dict = entry.fields_dict
            crossref = fields_dict.get('crossref')
            if crossref:
                crossref_entry = entries[crossref.value]
                for f in crossref_entry.fields:
                    if f.key != 'key' and f.key not in fields_dict:
                        entry.set_field(f)
        return library
        

class LatexMiddleware(BlockMiddleware):
    """This creates UTF-8 fields s_title, s_author, and s_venue."""
    def __init__(self):
        super().__init__()
        self.decoder =  LatexNodes2Text()
        self.wspatt = re.compile(r'\s+and\s+')

    def transform_entry(self, entry, *args, **kwargs):
        fields = entry.fields_dict
        if 'title' in fields:
            title_field = Field(key='s_title',
                                value = self.decoder.latex_to_text(fields['title'].value))
            entry.set_field(title_field)
        if 'author' in fields:
            authors = self.wspatt.split(self.decoder.latex_to_text(fields['author'].value))
            # authors = [a.strip() for a in self.decoder.latex_to_text(fields['author'].value).replace('\n', ' ').split(' and ')]
            author_field = Field(key='s_author',
                                 value = authors)
            entry.set_field(author_field)
            fields['author']._value = self.wspatt.sub(' and\n            ', fields['author'].value)
        if 'booktitle' in fields:
            venue_field = Field(key='s_venue',
                                value = self.decoder.latex_to_text(fields['booktitle'].value))
            entry.set_field(venue_field)
        elif 'journal' in fields:
            venue_field = Field(key='s_venue',
                                value = self.decoder.latex_to_text(fields['journal'].value))
            entry.set_field(venue_field)
        else:
            venue_field = Field(key='s_venue',
                                value = '')
            entry.set_field(venue_field)
        return entry


def convert_entry(entry: Entry) -> Document:
    """Convenience method to convert a bibtex entry into the Document format."""
    fields = entry.fields_dict
    if 'year' in fields:
        year = fields['year'].value
    else:
        year = None
    if 's_author' in fields:
        authors = fields['s_author'].value
    else:
        authors = []
    doc = Document(key=entry.key,
                   title = fields['s_title'].value,
                   authors = authors,
                   raw = expand_entry(entry),
                   venue = fields['s_venue'].value,
                   year=year)
    return doc

def expand_entry(entry:Entry) -> str:
    parts = []
    parts.append('@' + entry.entry_type + '{' + entry.key + ',')
    for k, f in entry.fields_dict.items():
        if not k.startswith('s_') and k != 'crossref' and f.value:
            if isinstance(f.value, int) or (isinstance(f.value, str) and f.value.isdigit()):
                parts.append('  {} = {},'.format(k, f.value))
            else:
                parts.append('  {} = "{}",'.format(k, f.value))
    parts.append('}')
    return '\n'.join(parts)

    
if __name__ == '__main__':
    import argparse
    import sys
    import xapian
    arguments = argparse.ArgumentParser()
    arguments.add_argument('--verbose',
                           action='store_true',
                           help='Whether to print debug info')
    arguments.add_argument('--input_dir',
                           default='../../webapp/metadata/latex/iacrcc/cryptobib',
                           help='Path to cryptobib/export checked out.')
    arguments.add_argument('--dbpath',
                           default='xapian.db',
                           help='Path to writable database directory.')
    args = arguments.parse_args()
    dbpath = Path(args.dbpath)
    if dbpath.is_file() or dbpath.is_dir():
        print('CANNOT OVERWRITE dbpath')
        sys.exit(2)
    input_dir = Path(args.input_dir)
    if not input_dir.is_dir():
        print('missing cryptobib')
        sys.exit(3)
    abbrev0_file = input_dir / Path('abbrev0.bib')
    crypto_db_file = input_dir / Path('crypto.bib')
    if not abbrev0_file.is_file():
        print('unable to find cryptobib file')
        sys.exit(3)
    parse_stack = (StringExpansionMiddleware(),
                   RemoveEnclosingMiddleware(),
                   CrossrefMiddleware(),
                   LatexMiddleware())
    bibstr = abbrev0_file.read_text(encoding='UTF-8')
    bibstr += crypto_db_file.read_text(encoding='UTF-8')
    print('parsing bibtex...')
    bibdb = bibtexparser.parse_string(bibstr, parse_stack = parse_stack)
    db = xapian.WritableDatabase(args.dbpath, xapian.DB_CREATE_OR_OPEN)
    termgenerator = xapian.TermGenerator()
    termgenerator.set_database(db)
    # use Porter's 2002 stemmer
    termgenerator.set_stemmer(xapian.Stem("english")) 
    termgenerator.set_flags(termgenerator.FLAG_SPELLING);
    count = 0
    for entry in bibdb.entries:
        if entry.entry_type == 'inproceedings' or entry.entry_type == 'article':
            doc = convert_entry(entry)
            if args.verbose:
                print('indexing {} {}'.format(entry.key, entry.entry_type))
            index_document(doc, db, termgenerator)
            count += 1
            if count % 5000 == 0:
                print(f'{count} documents')
                db.commit()
    db.commit()
    db.close()
    print(f'Indexed {count} documents')

