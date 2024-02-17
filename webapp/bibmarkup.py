import re

"""
The purpose of this is to insert <span id="bibtex:<key>... into bibtex
so that we can navigate to it with javascript. Note: the bibtex format
 is not well defined. It turns out that the key in

@article{key,

does not have to end with a comma, and bibtex entries can be on one line.
"""
def mark_bibtex(bibstr):
    return re.sub(r'^@([^\s\{]+)\{\s*([^\s,]+),?\s*',
                  r'<span id="bibtex:\2">@\1{\2,</span>\n',
                  bibstr,
                  count=0,
                  flags=re.MULTILINE)

