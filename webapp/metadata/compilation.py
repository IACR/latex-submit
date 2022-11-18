"""This is used to encapsulate the data about a paper's compilation.
The metadata should eventually appear here if the LaTeX class is
used properly.
"""

from pydantic import BaseModel, Field, EmailStr, Extra, constr, conint, conlist, validator, root_validator, validate_model, AnyUrl
from typing import List, Optional, Union, Literal
from typing_extensions import Annotated

import packaging.version
from datetime import datetime, timezone
from enum import Enum

class SchemaVersion(packaging.version.Version, Enum):
    VERSION1 = '1.0'

class StrEnum(str, Enum):
    @classmethod
    def from_str(cls, val):
        """Convert string to enum value."""
        for e in cls:
            if e.value == val:
                return e
        return None

class StatusEnum(StrEnum):
    """Used to categorize current status of a paper. Only shown to author and editor."""
    PENDING = 'pending'   # Submitted, but pending compilation
    MALFORMED_ZIP = 'malformed zipfile' # missing main.tex at top level.
    COMPILATION_FAILED = 'compilation_failed' # Compilation failed.
    MISSING_ABSTRACT = 'missing_abstract'
    METADATA_FAIL = 'metadata_fail' # failed to produce .meta
    METADATA_PARSE_FAIL = 'metadata_parse_fail' # failed to parse the .meta file.
    WRONG_VERSION = 'wrong_version' # not compiled with [version=final]
    COMPILATION_SUCCESS = 'compilation_success' # metadata extracted from successful compilation.
    AUTHOR_ACCEPTED = 'author_accepted' # author viewed metadata and PDF and accepted
    WITHDRAWN = 'withdrawn' # Withdrawn by author
    EDITOR_ACCEPTED = 'editor_accepted' # copy editor approved paper

class Affiliation(BaseModel):
    name: constr(min_length=3)
    ror: constr(regex='^0[0-9a-zA-HJKMNP-Z]{6}[0-9]{2}$') = Field(
        None,
        title='ROR ID of institution',
        description=('See https://ror.org/facts/ for format. The last two digits are supposed '
                     'to be a checksum based on ISO/IEC 7064, but since that is proprietary '
                     'we do not implement validation on it.'))
    street: str = Field(None,
                      title='Street of affiliation',
                      description='May be any string')
    city: str = Field(None,
                      title='City of affiliation',
                      description='May be any string')
    country: str = Field(None,
                         title='Country of affiliation',
                         description='May be any string')
    postcode: str = Field(None,
                         title='Postal code of affiliation',
                         description='May be any string')

    class Config:
        title = 'Affiliation for a paper',
        validate_all = True
        validate_assignment = True
        extra = Extra.forbid

class AuthorName(BaseModel):
    name: str = Field(...,
                      title='Full name of author',
                      description=('Preferred format is "First Last", but see '
                                   'https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/'))
    familyName: Optional[str] = Field(None,
                                      title='Family name or surname',
                                      description='Captured upon submission. Both Datacite and Crossref use these.')

class Author(AuthorName):
    email: EmailStr = Field(None,
                            title='Email address of this author',
                            description='Authors may not have them')
    orcid: Optional[constr(regex=r'^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')] = Field(None,
                                                                                          title='ORCID ID',
                                                                                          description='Must have the form dddd-dddd-dddd-dddd')
    affiliations: List[int] = Field(...,
                                    title='List of indices into affiliations array',
                                    description='This references affiliations from an external array of Affiliation objects in Paper.')

    class Config:
        title = 'Author model for Paper'
        validate_all = True
        validate_assignment = True

class License(BaseModel):
    name: str = Field(...,
                      title='Commonly used external identifier, e.g., "CC BY"',
                      description='This is a commonly used identifier but may have a version with it.',
                      allow_mutation=False)
    label: str = Field(...,
                       title='A more descriptive name like "Creative Commons Attribution"',
                       description='These have no predefined vocabulary',
                       allow_mutation=False)
    reference: str = Field(...,
                           title='Location of a definition for the license',
                           description='An example is https://creativecommons.org/licenses/by/4.0/',
                           allow_mutation=False)
    class Config:
        validate_assignment = True


class LicenseEnum(Enum):
    """These are immutable."""
    CC_BY =       License(name='CC BY',
                          label= 'Creative Commons Attribution',
                          reference = 'https://creativecommons.org/licenses/by/4.0/')
    CC_BY_SA =    License(name='CC BY-SA',
                          label='Creative Commons Attribution-ShareAlike',
                          reference='https://creativecommons.org/licenses/by-sa/4.0/')
    CC_BY_ND =    License(name='CC BY-ND',
                          label= 'Creative Commons Attribution-NoDerivs',
                          reference= 'https://creativecommons.org/licenses/by-nd/4.0/')
    CC_BY_NC =    License(name='CC BY-NC',
                          label='Creative Commons Attribution-NonCommercial',
                          reference='https://creativecommons.org/licenses/by-nc/4.0/')
    CC_BY_NC_SA = License(name='CC BY-NC-SA',
                          label='Creative Commons Attribution-NonCommercial-ShareAlike',
                          reference='https://creativecommons.org/licenses/by-nc-sa/4.0/')
    CC_BY_NC_ND = License(name='CC BY-NC-ND',
                          label='Creative Commons Attribution-NonCommercial-NoDerivs',
                          reference='https://creativecommons.org/licenses/by-nc-nd/4.0/')
    CC0 = License(name='CC0',
                  label='No rights reserved',
                  reference='https://creativecommons.org/publicdomain/zero/1.0/')
    @classmethod
    def from_str(cls, val):
        """Convert string to enum value."""
        for e in cls:
            if e.name == val:
                return e
        return None

class VersionEnum(StrEnum):
    """Values from documentclass[version=<version>]."""
    FINAL = 'final'
    SUBMISSION = 'submission'
    PREPRINT = 'preprint'


class Citation(BaseModel):
    ptype: str = Field(None,
                       title='BibTeX publication type',
                       description='Article, inproceedings, etc.')
    authors: str = Field(None,
                         title='BibTeX-style author list as a string',
                         description='Authors are joined with \\and')
    authorlist: List[AuthorName] = Field(...,
                                         title='Parsed list of author names',
                                         description='Parsed from authors string.')
    address: str = Field(None,
                         title='BibTeX field address of conference or publisher',
                         description='Unclear semantics.')
    booktitle: str = Field(None,
                           title='BibTeX booktitle field',
                           description='For inproceedings or incollection')
    chapter: str = Field(None,
                         title='BibTeX chapter field',
                         description='For inbook or incollection')
    doi: str = Field(None,
                     title='DOI field',
                     description='Not a URL')
    edition: str = Field(None,
                         title='BibTeX edition field',
                         description='For inbook, book, incollection, manual')
    editor: str = Field(None,
                        title='BibTeX editor field',
                        description='Is not parsed to separate differen entries')
    howpublished: str = Field(None,
                              title='BibTeX howpublished field',
                              description='May contain anything.')
    institution: str = Field(None,
                             title='BibTeX institution field',
                             description='Often used for tech report or misc type')
    isbn: str = Field(None,
                      title='BibTeX isbn field',
                      description='May be present for books')
    issn: str = Field(None,
                      title='BibTeX issn field',
                      description='May be present for article to indicate journal ISSN')
    journal: str = Field(None,
                         title='BibTeX journal field',
                         description='Should be present for article type')
    key: str = Field(None,
                     title='BibTeX key field',
                     description='No clear semantics, but used for sorting')
    month: str = Field(None,
                       title='BibTeX month field',
                       description='Often a three-letter abbreviation, e.g., Jun')
    note: str = Field(None,
                      title='BibTeX note field',
                      description='No clear semantics.')
    number: str = Field(None,
                        title='BibTeX number field',
                        description='Unclear semantics. May not be a number.')
    organization: str = Field(None,
                        title='BibTeX organization field',
                        description='Often used for techreport or manual.')
    pages: str = Field(None,
                       title='BibTeX pages field',
                       description='A page range, e.g., 5--7')
    publisher: str = Field(None,
                       title='BibTeX publisher field',
                       description='Name of publisher')
    school: str = Field(None,
                        title='BibTeX school field',
                        description='Institution for a thesis')
    series: str = Field(None,
                        title='BibTeX series field',
                        description='Series for books, e.g., LNCS')
    title: str = Field(None,
                       title='BibTeX title field',
                       description='Title of article, book, etc.')
    url: AnyUrl = Field(None,
                        title='BibTeX url field',
                        description='May not be official')
    volume: str = Field(None,
                        title='BibTeX volume field',
                        description='Often present in article')
    year: conint(ge=1000,le=9999) = Field(None,
                                          title='BibTeX year field',
                                          description='Should be 4-digit integer')
    class Config:
        extra = Extra.ignore

class Meta(BaseModel):
    """Metadata encoded in LaTeX files using iacrcc.cls."""
    schema_version: SchemaVersion = Field(default=SchemaVersion.VERSION1,
                                          title='Data format may evolve over time.',
                                          description=('The schema is serialized to disk, so that future versions can migrate '
                                                       'data to new schemas. Not to be confused with the version of json schema '
                                                       'specified in $schema.'))
    version: VersionEnum = Field(...,
                                 title='Version used in documentclass[version=...]',
                                 description='Should be final.')
    DOI: Optional[str] = Field(None,
                               title='The DOI of the official publication',
                               description='This should always be shown if it exists')
    authors: conlist(Author, min_items=1) = Field(...,
                                                  title='List of authors of the paper',
                                                  description='Affiliations are specified externally.')
    affiliations: List[Affiliation] = Field(None,
                                            title='List of affiliations for all authors.')
    keywords: List[str] = Field(None,
                                title='Author-supplied keywords',
                                description='This is pretty useless, but is preserved for posterity')
    title: constr(min_length=1) = Field(...,
                                        title='Title of paper',
                                        description='May contain LaTeX or HTML entities')
    subtitle: str = Field(None,
                          title='Subtitle of paper',
                          description='May contain LaTeX or HTML entities')
    abstract: str = Field(...,
                          title='Abstract of paper',
                          description='This is an abstract of the paper. May contain minimal LaTeX but should not contain HTML.')
    license: LicenseEnum = Field(LicenseEnum.CC_BY,
                                 title='License granted by authors',
                                 description='When a paper is submitted, a license must be chosen. This field is required.')


    citations: List[Citation] = Field(...,
                                      title='List of references',
                                      description='Derived from BibTeX')
    class Config:
        """$schema specifies the JSON schema version; not the version of this object."""
        schema_extra = {
            '$schema': 'http://json-schema.org/draft-07/schema#'
        }
        validate_all = True
        validate_assignment = True
        extra = Extra.ignore

    @root_validator()
    @classmethod
    def root_validate(cls, values):
        """Validate field dependencies. If not withdrawn, then authors should be non-empty."""
        if 'schema_version' not in values:
            raise ValueError('missing schema_version')
        if 'abstract' not in values:
            raise ValueError('Missing abstract')
        ver = values['schema_version']
        if 'authors' not in values or not values['authors']:
            raise ValueError('Paper must contain authors')
        if len(values['authors']) == 0:
            raise ValueError('Authors must be nonempty')
        if 'affiliations' not in values:
            raise ValueError('Paper must contain affiliations')
        num_affiliations = len(values['affiliations'])
        authorcount_withemail = sum(1 for a in values['authors'] if a.email)
        if authorcount_withemail == 0:
            raise ValueError('At least one author must have an email.')
        for author in values['authors']:
            if 'affiliations' in author:
                for aff_index in author['affiliations']:
                    if aff_index not in range(num_affiliations):
                        raise ValueError('Affiliation index {} out of range {}'.format(aff_index, num_affiliations))
        return values

    def is_valid(self):
        """Called to validate the data, in case it was constructed with construct().

           It's possible to bypass validation in pydantic using construct(), but this
           is a way to validate a model via a function rather than a constructor.
           We should only use this in tests, because it depends on some semi-documented 
           behavior of pydantic introduced in v0.26, namely that validate_model returns
           a triple (Tuple[Dict[str, Any], Set[str], Optional[ValidationError]])
        """
        values, fields_set, validation_error = validate_model(self.__class__, self.__dict__)
        if validation_error:
            return False
        return True
        
class Compilation(BaseModel):
    paperid: constr(min_length=3) = Field(...,
                                          title='Globally unique paper ID derived from venue and id in review system',
                                          description='ID must be globally unique.')
    doccls: str = Field(...,
                        title='LaTeX document class',
                        description='Intended target to compile for.')
    status: StatusEnum = Field(StatusEnum.PENDING,
                               title='Current status',
                               description='Indicates what stage the paper is at')
    email: EmailStr = Field(...,
                            title='Email for submitting author',
                            description='Who submitted the paper')
    submitted: datetime = Field(...,
                                title='When paper was submitted for publications',
                                description='Authenticated upon submission.')
    accepted: datetime = Field(...,
                               title='When the paper was accepted for publications',
                               description = 'Authenticated upon acceptance')
    compiled: datetime = Field(...,
                               title='When the article was last compiled',
                               description='Last compilation date')
    compile_time: float = Field(None,
                                title='Number of seconds for compilation',
                                description='May be none before it is compiled')
    log: str = Field(None,
                     title='Log from running latexmk',
                     description='Will be absent until latex is attempted.')
    error_log: List[str] = Field(...,
                                 title='Error messages if some step failed',
                                 description='Used in the UI if necessary. See status')
    exit_code: int = Field(-1,
                            title='Exit code from running latexmk',
                            description='These are not well defined.')
    meta: Meta = Field(None,
                       title='Parsed metadata',
                       description='Present once status passes COMPILATION_SUCCESS')
    

if __name__ == '__main__':
    print(Compilation.schema_json(indent=2))
