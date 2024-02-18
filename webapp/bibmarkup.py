import re
import pybtex
from pybtex.database import parse_string

"""
The purpose of this is to insert <span id="bibtex:<key>... into bibtex
so that we can navigate to it with javascript. Note: the bibtex format
 is not well defined. It turns out that the key in

@article{key,

does not have to end with a comma, and bibtex entries can be on one line.
"""

"""
This pybtex bibtex style extends UnsrtStyle, but handles URLs
differently.  pybtex has its own template style.
"""

from pybtex.style.formatting.unsrt import Style as UnsrtStyle
from pybtex.style.template import href, join, field, sentence, optional
from pylatexenc.latex2text import LatexNodes2Text
from urllib.parse import urlencode

class BibStyle(UnsrtStyle):
    def format_title(self, e, which_field, as_sentence=True):
        formatted_title = field(
            which_field, apply_func=lambda text: text.capitalize()
        )
        if as_sentence:
            formatted_title = sentence [ formatted_title ]
        # Make the title clickable if there is a url field but no DOI field.
        if 'url' in e.fields and 'doi.org' not in e.fields['url']:
            ans = href [
                field('url', raw=False),
                formatted_title
            ]
        else:
            ans = formatted_title
        return ans

    def format_web_refs(self, e):
        return sentence [
            optional [ self.format_doi(e) ]
        ]

    def format_doi(self, e):
        # based on urlbst format.doi
        return href [
            join [
                'https://doi.org/',
                field('doi', raw=False)
                ],
            join [
                'https://doi.org/',
                field('doi', raw=False)
                ]
            ]

    def format_url(self, e):
        return href [
            join [
                'https://doi.org/',
                field('doi', raw=True)
            ],
            'DOI'
        ]


def mark_bibtex(bibstr):
    return re.sub(r'^@([^\s\{]+)\{\s*([^\s,]+),?\s*',
                  r'<span id="bibtex:\2">@\1{\2,</span>\n',
                  bibstr,
                  count=0,
                  flags=re.MULTILINE)

def get_links(entry):
    """Return scholar, eprint links for a bibtex entry."""
    eprint = {'relevance': 'on'}
    query = ''
    if 'author' in entry.persons:
        converter = LatexNodes2Text()
        names = [converter.latex_to_text(str(a)) for a in entry.persons['author']]
        if len(names) < 3:
            query += ' and '.join(names)
        else:
            query += ', '.join(names[:-1]) + ', and \n' + names[-1]
        eprint['authors'] = query
    if 'title' in entry.fields:
        query += ' ' + entry.fields['title']
        eprint['title'] = entry.fields['title']
    if 'year' in entry.fields:
        query += ' ' + entry.fields['year']
        eprint['submittedafter'] = int(entry.fields['year']) - 1
        eprint['submittedbefore'] = int(entry.fields['year']) + 1
    scholar = 'https://scholar.google.com/scholar?hl=en&' + urlencode({'q': query})
    eprint = 'https://eprint.iacr.org/search?' + urlencode(eprint)
    return scholar, eprint

def bibtex_to_html(bibstr):
    references = []
    data = {'errors': []}
    pybtex.errors.set_strict_mode(False)
    try:
        with pybtex.errors.capture() as captured_errors:
            bibdata = parse_string(bibstr, 'bibtex')
            if captured_errors:
                for e in captured_errors:
                    data['errors'].append('unable to parse bibtex {}'.format(str(e)))
            # We hide 'note' fields. It's easier to just delete them than to modify urlbst.py.
            for entry in bibdata.entries.values():
                if 'note' in entry.fields:
                    del entry.fields['note']
                if 'howpublished' in entry.fields:
                    del entry.fields['howpublished']
            style = BibStyle()
            backend = pybtex.plugin.find_plugin('pybtex.backends', 'html')()
            formatted = style.format_bibliography(bibdata)
            for entry in formatted:
                reference = {'text': entry.text.render(backend)}
                try:
                    scholar, eprint = get_links(bibdata.entries[entry.key])
                    reference['scholar'] = scholar
                    reference['eprint'] = eprint
                except Exception as e:
                    data['errors'].append('unable to generate scholar link: {}'.format(str(e)))
                references.append(reference)
    except Exception as e:
        data['errors'].append('Error processing bibtex: {}'.format(str(e)))
    data['references'] = references
    return data
    
