"""Utility methods for paperid and DOIs.

We assume that paperid is a globally unique ID assigned by the review
system. This paperid must be constructed from a restricted alphabet in
order to make it safe for URLs, LaTeX, and filenames. This alphabet is
currently a-z0-9.- An example paperid might be 2023-1-14 to indicate
that it is paper #14, issue #1, in the year 2023. There are no
structural assumptions about paperids used here other than the fact
that they are formed from the restricted alphabet. paperids should be
short in order to keep short DOIs.

DOIs have a prefix assigned to the publisher, and a suffix assigned by
the publisher. The guidelines on DOI suffix don't impose many
restrictions on what may be used for the suffix. See
https://www.doi.org/doi_handbook/2_Numbering.html The suffix is
case-insensitive, but they are converted to upper case when they are
registered.

We may change how DOIs are assigned in the future, and in order to
distinguish different assignment schemes we use the first letter of
the suffix (which is 'a' in this implementation).  In order to make
them more compact in print, we use lower case for the suffix. We also
restrict them to the same alphabet used by paperids.

The suffix is supposed to be an opaque string that avoids visible
encoding of other metadata. See
https://www.crossref.org/documentation/member-setup/constructing-your-dois/
Both ToSC and TCHES violate this by including the page numbers in the
DOI.  In this implementation, the suffix after the first letter 'a' is
formed with an obfuscation of the paperid. This obfuscation is done
with a Vigenère cipher (oh the irony), and makes it unique if the
paperid is unique.

"""

import re
import string

from .compilation import CompileError, ErrorType
_prefix = '10.1729' # Any chance we can get a vanity prefix?

# _alphabet used for both paperid and DOI suffix.
# If you change the alphabet, make sure get_doi still works.
_alphabet = '-' + string.digits + string.ascii_lowercase

def validate_paperid(paperid):
    if re.match(r'^[-\.a-z0-9]+$', paperid):
        return True
    return False

def get_doi(paperid):
    if not validate_paperid(paperid):
        return None
    base_key = 'alan_turing'
    key = base_key
    while len(key) < len(paperid):
        key = key + base_key
    key = [_alphabet.find(key[i]) for i in range(len(key))]
    buffer = ''
    for i in reversed(range(len(paperid))):
        index = _alphabet.find(paperid[i])
        buffer += _alphabet[(index + key[i]) % len(_alphabet)]
    return _prefix + '/a' + buffer
