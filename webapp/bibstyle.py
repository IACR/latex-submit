"""
This file contains code for producing HTML from a parsed bibliography. This implements
something close to the alphaurl style in the standard texlive distribution.
"""
import calendar
from bibtexparser.model import Entry
try:
    from metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus
except:
    from .metadata.compilation import Compilation, ErrorType, CompileError, BibItem, PubType, CompileStatus
from typing import List, Dict

import re

    
# These abbreviations are built into many bibtex styles including alphaurl that we use.
_MONTH_ABBREV = {'1': 'January',
                 '2': 'February',
                 '3': 'March',
                 '4': 'April',
                 '5': 'May',
                 '6': 'June',
                 '7': 'July',
                 '8': 'August',
                 '9': 'September',
                 '10': 'October',
                 '11': 'November',
                 '12': 'December',
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
def _date(fields):
    """We assume fields has a year in it. We use issue_date if it exists."""
    if 'issue_date' in fields:
        return fields['issue_date'].value
    if 'year' not in fields:
        raise ValueError('no date fields')
    if 'month' not in fields:
        return fields['year'].value
    # 'month' is a peculiar field, because people have shoved all sorts of things
    # into it like jan # "\slash " # feb. We only recognize simple things like
    # an integer, a lower case abbreviation, or a string without #
    month = fields['month'].value
    if isinstance(month, int):
        month = calendar.month_name[month]
    elif month in _MONTH_ABBREV:
        month = _MONTH_ABBREV[month]
    elif '#' in month:
        # we ignore these
        return fields['year'].value
    if 'day' in fields:
        return '{} {} {}'.format(month, fields['day'].value, fields['year'].value)
    return '{} {}'.format(month, fields['year'].value)
            

class BibStyle:
    """
    This is used to transform a bibtex entry into HTML. This is  modeled
    on the alphaurl.bst file, but theoretically we could create other styles.
    """

    def __init__(self, compilation: Compilation):
        self.comp = compilation
        # Used to build up the HTML string.
        self._buf = []
        # This is the list of entry types that the style knows how to format.
        # misc is not listed here and is checked separately. It must have at least
        # one of author/editor, title, year/date.
        self._required_fields = {
            'article': ['author', 'title', 'journaltitle/journal', 'year/date'],
            'book': ['author/editor', 'title', 'year/date'],
            'booklet': ['title'],
            'collection': ['editor', 'title', 'year/date'],
            # inbook is a mess, and we should probably warn authors to use
            # @book or @incollection instead.
            'inbook': ['author/editor', 'title', 'chapter/pages', 'year/date'],
            'incollection': ['author', 'title', 'booktitle', 'year/date'],
            'inproceedings': ['author', 'title', 'booktitle/series', 'year/date'],
            'manual': ['title', 'year/date'],
            'online': ['author/editor', 'title', 'year/date', 'url'],
            'patent': ['author', 'title', 'number', 'year/date'],
            'proceedings': ['title', 'year/date'],
            'thesis': ['author', 'title', 'type', 'institution/school', 'year/date'],
            'phdthesis': ['author', 'title', 'institution/school', 'year/date'],
            'unpublished': ['author', 'title', 'note'],
            'mastersthesis': ['author', 'title', 'institution/school', 'year/date'],
            'online': ['title', 'url'],
            'techreport': ['author', 'title', 'institution/publisher', 'year/date'],
        }
        self._aliases = {
            'mvbook': 'book',
            'mvcollection': 'collection',
            'mvproceedings': 'proceedings',
            'conference': 'inproceedings',
            'report': 'techreport',
            'electronic': 'online',
            'www': 'online',
            'webpage': 'online'
        }

    def get_alias(self, entry: Entry) -> str:
        """An entry has a type, but a style only knows about the types it can
        format.  Moreover, some types are merely aliases for
        others. For example, bibtex was invented before the web, and
        there was never a standard for what type to use for a
        webpage. Different styles would call it different things, and
        we ended up with aliases for this type like 'online', 'www',
        'webpage, or 'electronic'. If there is no alias, a style can
        always try to treat it as 'misc'.

        """
        if entry.entry_type in self._required_fields:
            return entry.entry_type
        return self._aliases.get(entry.entry_type)


    @property
    def required_fields(self):
        return self._required_fields

    def check_required_fields(self, entry: Entry):
        """Check that entry has all required fields. 
        Return:
        alias; str saying what entry_type to treat this as. 
             Usually that is entry.entry_type, but it could be
             an alias or just 'misc'.
        errors: List[str] indicating errors in the entry for missing fields.
        # NOTE: we assume that entry_type is lower case.
        """
        key = entry.key
        fields = entry.fields_dict
        errors = []
        alias = self.get_alias(entry)
        if not alias:
            # We will treat it as misc.
            if ('author' not in fields and
                'title' not in fields and
                'howpublished' not in fields and
                'note' not in fields):
                errors.append('BibTeX entry {} must contain at least one of author,title,howpublished,note'.format(key))
            return errors
        required_fields = self._required_fields.get(alias)
        title = fields.get('title')
        if title:
            title = title.value
        else:
            title = 'No title'
        for field in required_fields:
            if '/' in field:
                alts = field.split('/')
                has_field = False
                for alt in alts:
                    if fields.get(alt, None):
                        has_field = True
                if not has_field:
                    errors.append('bibtex entry {} ({}) of type {} should have one of {} fields'.format(key,
                                                                                                        title,
                                                                                                        entry.entry_type,
                                                                                                        field))
            else:
                if not fields.get(field, None):
                    errors.append('bibtex entry {} ({}) requires {} field'.format(key, title, field))
        return errors

    def append(self, *strings):
        for s in strings:
            if s:
                self._buf.append(s)

    def output(self):
        return ''.join(self._buf)
    
    def _warning(self, entry: Entry, txt: str):
        self.comp.warning_log.append(CompileError(error_type=ErrorType.BIBTEX_WARNING,
                                                  logline=0,
                                                  text='Bibtex error: {}: {}'.format(entry.key,
                                                                                     txt)))
        
    def _join_names(self, names: List[str]):
        output = ''
        if len(names) == 0:
            return output
        elif len(names) == 1:
            output += names[0]
        elif len(names) == 2:
            output += names[0] + ' and ' + names[1]
        else:
            output += ', '.join(a for a in names[:-1]) + ', and ' + names[-1]
        return output

    def _format_doi(self, entry):
        val = entry.fields_dict['doi'].value
        if val.startswith('http:'):
            index = val.find('doi.org/')
            if index:
                val = val[index+8:]
            else:
                self._warning(entry, 'DOI in wrong format: {}'.format(val))
                return
        self.append(' DOI: <a href="https://doi.org/{}">{}</a>'.format(val, val))

    def _make_title(self, fields: Dict[str, Entry], italics: bool):
        """Make it a hyperlink if url field is present."""
        if 'title' in fields:
            value = fields['title'].value
        else:
            value = fields['booktitle'].value
        if 'href=' in value: # don't use url to mark it up.
            if italics:
                return ' <em>{}</em>'.format(value)
            else:
                return ' {}'.format(value)
        if 'url' in fields and 'doi.org/' not in fields['url'].value:
            if italics:
                return ' <em><a href="{}">{}</a></em>'.format(fields['url'].value,
                                                              value)
            else:
                return ' <a href="{}">{}</a>'.format(fields['url'].value,
                                                     value)
        else:
            if italics:
                return ' <em>{}</em>'.format(value)
            else:
                return ' {}'.format(value)
        
    def _format_editors(self, fields):
        if 'editor' in fields and len(fields['editor'].value):
            self.append(self._join_names(fields['editor'].value))
            if len(fields['editor'].value) == 1:
                self.append(', editor')
            else:
                self.append(', editors')

    def _format_booktitle(self, fields):
        self.append('In ')
        if 'editor' in fields:
            self._format_editors(fields)
            self.append(', ')
        self.append('<em>', fields['booktitle'].value, '</em>')
            
    def _format_bvolume(self, fields):
        if 'volume' in fields:
            self.append(', volume ')
            self.append(fields['volume'].value)
            if 'series' in fields:
                self.append(' of <em>{}</em>'.format(fields['series'].value))

    def _format_note(self, fields):
        if 'note' in fields:
            if not re.match(r'\\url{[^}]+}', fields['note'].value):
                self.append(' ')
                self.append(fields['note'].value)
    def _format_number_series(self, fields):
        if 'series' in fields:
            if 'number' in fields:
                self.append('Number ', fields['number'].value, ' in ')
            self.append(fields['series'].value, '. ')

    def _format_edition(self, fields):
        if 'edition' in fields:
            self.append(', ')
            self.append(fields['edition'].value)
            self.append(' edition.')

    def _article(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value))
            self.append('. ')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        else:
            self._warning(entry, 'Title is required for @article')
        if 'journal' in fields:
            self.append(' <em>', fields['journal'].value, '</em>')
            if 'volume' in fields:
                self.append(', ', fields['volume'].value)
                if 'number' in fields:
                    self.append('({})'.format(fields['number'].value))
                if 'pages' in fields:
                    self.append(':', fields['pages'].value)
        else:
            self._warning(entry, 'journal is required for @article')
        self.append(', ', _date(fields), '.')
        if 'doi' in fields:
            self._format_doi(entry)

    def _inproceedings(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value))
            self.append('. ')
        else:
            self._warning(entry, 'Author is required for @inproceedings')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        else:
            self._warning(entry, 'Title is required for @inproceedings')
        if 'booktitle' in fields:
            self._format_booktitle(fields)
        else:
            self._warning(entry, 'booktitle is expected for @article')
        self._format_bvolume(fields)
        if 'pages' in fields:
            self.append(', pages {}'.format(fields['pages'].value))
        if 'address' in fields:
            self.append(', ')
            self.append(fields['address'].value)
        self.append('. ')
        if 'year' in fields:
            self.append(_date(fields), '. ')
        if 'publisher' in fields:
            self.append(' ', fields['publisher'].value, '. ')
        elif 'organization' in fields:
            self.append(' ', fields['organization'].value, '. ')
        if 'doi' in fields:
            self._format_doi(entry)

    def _incollection(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value))
            self.append('. ')
        else:
            self._warning(entry, 'Author is required for @incollection')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        else:
            self._warning(entry, 'Title is required for @incollection')
        if 'booktitle' in fields:
            self._format_booktitle(fields)
        self._format_bvolume(fields)
        if 'pages' in fields:
            self.append(', pages {}.'.format(fields['pages'].value))
        else:
            self.append('.')
        if 'publisher' in fields:
            self.append(' ', fields['publisher'].value)
        elif 'organization' in fields:
            self.append(', ', fields['organization'].value)
        if 'address' in fields:
            self.append(', ')
            self.append(fields['address'].value)
        if 'edition' in fields:
            self.append(fields['edition'].value)
            self.append(' edition.')
        if 'year' in fields:
            self.append(' ', fields['year'].value, '.')
        elif 'date' in fields:
            self.append(' ', fields['date'].value, '.')
        else:
            self.append('.')
        if 'doi' in fields:
            self._format_doi(entry)

    def _inbook(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value))
            self.append('. ')
        elif 'editor' in fields:
            self.append(self._join_names(fields['editor'].value))
            if len(fields['editor'].value) > 1:
                self.append(', editors.')
            else:
                self.append(', editor.')
        if 'title' in fields:
            self.append(self._make_title(fields, True))
        elif 'booktitle' in fields:
            self._format_booktitle(fields)
        else:
            self._warning(entry, 'Title is required for @inbook')
        self._format_bvolume(fields)
        if 'chapter' in fields:
            self.append(', chapter ')
            self.append(fields['chapter'].value)
        if 'pages' in fields:
            pages = fields['pages'].value
            if '-' in pages or '–' in pages:
                self.append(', pages {}. '.format(pages))
            else:
                self.append(', page {}. '.format(pages))
        else:
            self.append('. ')
        if 'publisher' in fields:
            self.append(fields['publisher'].value)
        elif 'organization' in fields:
            self.append(fields['organization'].value)
        if 'address' in fields:
            self.append(', ', fields['address'].value)
        if 'edition' in fields:
            self.append(', ')
            self.append(fields['edition'].value)
            self.append(' edition.')
        if 'year' in fields:
            self.append(' ', fields['year'].value, '.')
        elif 'date' in fields:
            self.append(' ', fields['date'].value, '.')
        else:
            self.append('.')
        self._format_note(fields)
        if 'doi' in fields:
            self._format_doi(entry)

    def _book(self, entry):
        fields = entry.fields_dict
        if 'author' in fields and 'editor' in fields:
            self._warning(entry, '@book entry should not have both author and editor fields')
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value))
            self.append('. ')
        if 'editor' in fields:
            self.append(self._join_names(fields['editor'].value))
            if len(fields['editor'].value) > 1:
                self.append(', editors.')
            else:
                self.append(', editor.')
        self.append(self._make_title(fields, True))
        # if 'volume' in fields:
        #     self.append(', volume {}.'.format(fields['volume'].value))
        # else:
        #     self.append('. ')
        self._format_bvolume(fields)
        self.append('. ')
        self._format_number_series(fields)
        if 'publisher' in fields:
            self.append(fields['publisher'].value)
        elif 'organization' in fields:
            self.append(fields['organization'].value)
        if 'address' in fields:
            self.append(', ', fields['address'].value)
        self._format_edition(fields)
        if 'year' in fields:
            self.append(' ', fields['year'].value, '.')
        elif 'date' in fields:
            self.append(' ', fields['date'].value, '.')
        else:
            self.append('. ')
        self._format_note(fields)
        if 'doi' in fields:
            self._format_doi(entry)

    def _booklet(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value), '. ')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        if 'howpublished' in fields:
            self.append(fields['howpublished'].value, '. ')
        if 'address' in fields:
            self.append(fields['address'].value, '. ')
        if 'note' in fields:
            self._format_note(fields)
            self.append('. ')
        if 'year' in fields or 'issue_date' in fields:
            self.append(_date(fields), '.')
            
    def _manual(self, entry):
        fields = entry.fields_dict
        needscomma = False
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value), '.')
        if 'title' in fields:
            self.append(self._make_title(fields, True), '. ')
        else:
            self._warning(entry, 'title is required for bibtex type @manual')
            self.append(' ')
        if 'organization' in fields:
            self.append(fields['organization'].value)
            if 'address' in fields:
                self.append(', ', fields['address'].value)
        if 'year' in fields:
            self.append(', ', _date(fields))
        else:
            self._warning(entry, 'year is required for bibtex type @manual')
        self.append('.')
    def _athesis(self, entry, thesistype):
        """Used for phdthesis, mastersthesis, and just thesis with a type."""
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value), '. ')
        if 'title' in fields:
            self.append(self._make_title(fields, True), '. ')
        self.append(thesistype, ', ')
        if 'school' in fields:
            self.append(fields['school'].value, ', ')
        elif 'institution' in fields:
            self.append(fields['institution'].value, ', ')
        if 'address' in fields:
            self.append(fields['address'].value, ', ')
        self.append(_date(fields), '.')
    def _mastersthesis(self, entry):
        self._athesis(entry, 'Master\'s thesis')
    def _phdthesis(self, entry):
        self._athesis(entry, 'PhD thesis')
    def _thesis(self, entry):
        fields = entry.fields_dict
        if 'type' in fields:
            thesistype = fields['type'].value
            if thesistype == 'phdthesis':
                self._phdthesis(entry)
            elif thesistype == 'mathesis':
                self._mastersthesis(entry)
            else:
                self._misc(entry)
        else:
            self._misc(entry)
    def _new_sentence_a(self, fields, name):
        if 'name' in fields:
            self.append('. ')
            
    def _new_sentence_b(self, fields, name1, name2):
        if 'name1' in fields and 'name2' in fields:
            self.append('. ')
            
    def _proceedings(self, entry):
        fields = entry.fields_dict
        if 'editor' in fields:
            self.append(self._join_names(fields['editor'].value))
            if len(fields['editor'].value) > 1:
                self.append(', editors.')
            else:
                self.append(', editor.')
        elif 'organization' in fields:
            self.append(fields['organization'].value)
            self.append('. ')
        if 'title' in fields:
            self.append(self._make_title(fields, True))
        elif 'booktitle' in fields:
            self._format_booktitle(fields)
        else:
            self._warning(entry, 'Title is required for @inbook')
        self._format_bvolume(fields)
        self._format_number_series(fields)
        if 'address' not in fields:
            if not 'editor' in fields:
                self._new_sentence_a(fields, 'publisher')
            else:
                self._new_sentence_b(fields, 'publisher', 'organization')
                if 'organization' in fields:
                    self.append(fields['organization'].value)
            if 'publisher' in fields:
                self.append(' ', fields['publisher'].value)
            self.append(_date(fields))
        else: # has address
            self.append(' ', fields['address'].value, ', ')
            self.append(_date(fields), '. ')
            if not 'editor' in fields:
                if 'organization' in fields:
                    self.append(fields['organization'].value)
            if 'publisher' in fields:
                self.append(fields['publisher'].value)
        self.append('. ')
        self._format_note(fields)
        if 'doi' in fields:
            self._format_doi(entry)

    def _misc(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value), '. ')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        if 'note' in fields:
            self._format_note(fields)
            self.append('. ')
        if 'howpublished' in fields:
            self.append(fields['howpublished'].value, '. ')
        if 'year' in fields or 'issue_date' in fields:
            self.append(_date(fields), '.')

    def _techreport(self, entry):
        fields = entry.fields_dict
        if 'author' in fields:
            self.append(self._join_names(fields['author'].value), '. ')
        if 'title' in fields:
            self.append(self._make_title(fields, False), '. ')
        self.append('Technical report')
        if 'number' in fields:
            self.append(' number ', fields['number'].value, ', ')
        else:
            self.append(', ')
        if 'institution' in fields:
            self.append(fields['institution'].value, '. ')
        elif 'organization' in fields:
            self.append(fields['organization'].value, '. ')
        if 'note' in fields:
            self._format_note(fields)
            self.append('. ')
        self.append(_date(fields), '.')

    def _unpublished(self, entry):
        # TODO:finish this
        self._misc(entry)

    def _online(self, entry):
        # TODO:finish this
        self._misc(entry)
        
    def format_entry(self, entry):
        """Produces the html to be enclosed in a div. NOTE: this is not thread-safe."""
        self._buf = []
        alias = self.get_alias(entry)
        if not alias:
            alias = 'misc'
        self.append('<div id="ref-{}" class="bibitem">'.format(entry.key))
        if alias == 'article':
            self._article(entry)
        elif alias == 'book':
            self._book(entry)
        elif alias == 'booklet':
            self._booklet(entry)
        elif alias == 'inproceedings':
            self._inproceedings(entry)
        elif alias == 'inbook':
            self._inbook(entry)
        elif alias == 'incollection':
            self._incollection(entry)
        elif alias == 'manual':
            self._manual(entry)
        elif alias == 'misc':
            self._misc(entry)
        elif alias == 'mastersthesis':
            self._mastersthesis(entry)
        elif alias == 'phdthesis':
            self._phdthesis(entry)
        elif alias == 'thesis':
            self._thesis(entry)
        elif alias == 'patent':
            self._patent(entry)
        elif alias == 'proceedings':
            self._proceedings(entry)
        elif alias == 'techreport':
            self._techreport(entry)
        elif alias == 'unpublished':
            self._unpublished(entry)
        elif alias == 'online':
            self._online(entry)
        else:
            self._misc(entry)
        self.append('</div>')
        return self.output()
