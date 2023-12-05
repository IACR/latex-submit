"""This is used to encapsulate the data about a paper's compilation.
The metadata should eventually appear here if the LaTeX class is
used properly.
"""
import json
from pydantic import model_validator, StringConstraints, ConfigDict, BaseModel, Field, EmailStr, AnyUrl, PositiveInt
from typing import List, Optional
from typing_extensions import Annotated

from datetime import datetime, timezone
from enum import Enum

class StrEnum(str, Enum):
    @classmethod
    def from_str(cls, val):
        """Convert string to enum value."""
        for e in cls:
            if e.value == val:
                return e
        return None

class SchemaVersion(StrEnum):
    VERSION1 = '1.0'

class CompileStatus(StrEnum):
    """Used to categorize current status of a paper. Only shown to author and editor."""
    COMPILING = 'compiling'   # Submitted, but pending compilation
    MALFORMED_ZIP = 'malformed zipfile' # missing main.tex at top level.
    COMPILATION_FAILED = 'compilation_failed' # Compilation failed.
    COMPILATION_ERRORS = 'compilation_errors' # it compiled, but with serious errors (e.g., undefined references)
    MISSING_ABSTRACT = 'missing_abstract'
    METADATA_FAIL = 'metadata_fail' # failed to produce .meta
    METADATA_PARSE_FAIL = 'metadata_parse_fail' # failed to parse the .meta file.
    WRONG_VERSION = 'wrong_version' # not compiled with [version=final]
    COMPILATION_SUCCESS = 'compilation_success' # metadata extracted from successful compilation.
    AUTHOR_ACCEPTED = 'author_accepted' # author viewed metadata and PDF and accepted
    WITHDRAWN = 'withdrawn' # Withdrawn by author
    EDITOR_ACCEPTED = 'editor_accepted' # copy editor approved paper
    DOI_FAILED = 'doi_failed' # registration of DOI failed
    PUBLISHED = 'published' # approved by executive editor

_ror_pattern = '^0[0-9a-zA-HJKMNP-Z]{6}[0-9]{2}$'

class Funder(BaseModel, extra='forbid'):
    name: Annotated[str, StringConstraints(min_length=3)] = Field(title='Name of organization',
                                                                  description = 'Only requirement is minimum length of three characters')
    ror: Optional[str] = Field(default=None,
                               pattern=_ror_pattern,
                               title='ROR ID of institution',
                               description=('See https://ror.org/facts/ for format. The last two digits are supposed '
                                            'to be a checksum based on ISO/IEC 7064, but since that is proprietary '
                                            'we do not implement validation on it.'))
    fundref: Optional[Annotated[str, StringConstraints(min_length=3)]
                      ] = Field(default=None,
                                title = 'Optional fundreg id',
                                description = 'ID from Crossref Funder registry. ror is preferred now.')
    country: Optional[Annotated[str, StringConstraints(min_length=2)]
                      ] = Field(default=None,
                                title='Country of organization',
                                description=' Any identifier is acceptable')
    grantid: Optional[str] = Field(default=None,
                                   title = 'Grant ID from funding agency',
                                   description = 'This optional field can be any string')

class Affiliation(BaseModel):
    name: Annotated[str, StringConstraints(min_length=3)]
    ror: Optional[Annotated[str, StringConstraints(pattern=_ror_pattern)]
                  ] = Field(default=None,
                            title='ROR ID of institution',
                            description=('See https://ror.org/facts/ for format. The last two digits are supposed '
                                         'to be a checksum based on ISO/IEC 7064, but since that is proprietary '
                                         'we do not implement validation on it.'))
    department: Optional[str] = Field(default=None,
                                      title='department of affiliation',
                                      description='May be any string')
    street: Optional[str] = Field(default=None,
                                  title='Street of affiliation',
                                  description='May be any string')
    city: Optional[str] = Field(default=None,
                                title='City of affiliation',
                                description='May be any string')
    state: Optional[str] = Field(default=None,
                                 title='State or province',
                                 description='May be any string')
    country: Optional[Annotated[str, StringConstraints(min_length=2)]
                      ] = Field(default=None,
                                title='Country of affiliation',
                                description='May be any string')
    postcode: Optional[str] = Field(default=None,
                                    title='Postal code of affiliation',
                                    description='May be any string')
    model_config = ConfigDict(title='Affiliation for a paper', validate_default=True, validate_assignment=True, extra="forbid")

class AuthorName(BaseModel):
    name: str = Field(...,
                      title='Full name of author',
                      description=('Preferred format is "First Last", but see '
                                   'https://www.kalzumeus.com/2010/06/17/falsehoods-programmers-believe-about-names/'))
    familyName: Optional[str] = Field(default=None,
                                      title='Family name or surname',
                                      description='Captured upon submission. Both Datacite and Crossref use these.')

class Author(AuthorName):
    email: Optional[EmailStr] = Field(default=None,
                                      title='Email address of this author',
                                      description='Authors may not have them')
    orcid: Optional[Annotated[str, StringConstraints(pattern=r'^[0-9]{4}-[0-9]{4}-[0-9]{4}-[0-9]{3}[0-9X]$')]
                    ] = Field(default=None,
                              title='ORCID ID',
                              description='Has the form xxxx-xxxx-xxxx-xxxx')
    affiliations: Optional[List[PositiveInt]] = Field(default=None,
                                                      title='List of 1-based indices into affiliations array',
                                                      description='This references affiliations from an external array of Affiliation objects in Paper.')
    model_config = ConfigDict(title='Author model for Paper', validate_default=True, validate_assignment=True)

class License(BaseModel):
    name: str = Field(title='Commonly used external identifier, e.g., "CC BY"',
                      description='This is a commonly used identifier but may have a version with it.')
    label: str = Field(title='A more descriptive name like "Creative Commons Attribution"',
                       description='These have no predefined vocabulary')
    reference: str = Field(title='Location of a definition for the license',
                           description='An example is https://creativecommons.org/licenses/by/4.0/')
    model_config = ConfigDict(validate_assignment=True, frozen=True)


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
    def license_from_iacrcc(cls, val):
        """Convert iacrcc license key to an enum value."""
        key = 'CC' + val[2:].replace('-', '_').upper()
        for e in cls:
            if e.name == key:
                return e.value.model_dump()
        raise ValueError('Unknown license key {}'.format(key))

class VersionEnum(StrEnum):
    """Values from documentclass[version=<version>]."""
    FINAL = 'final'
    SUBMISSION = 'submission'
    PREPRINT = 'preprint'

class Meta(BaseModel):
    """Metadata encoded in LaTeX files using iacrcc.cls."""
    schema_version: SchemaVersion = Field(default=SchemaVersion.VERSION1,
                                          title='Data format may evolve over time.',
                                          description=('The schema is serialized to disk, so that future versions can migrate '
                                                       'data to new schemas. Not to be confused with the version of json schema '
                                                       'specified in $schema.'))
    version: VersionEnum = Field(title='Version used in documentclass[version=...]',
                                 description='Should be final.')
    DOI: Optional[str] = Field(default=None,
                               title='The DOI of the official publication',
                               description='Omits any URL resolver part.')
    URL: Optional[str] = Field(default=None,
                               title='The permanent URL assigned to the paper after publication.',
                               description='This should remain permanent.')
    authors: List[Author] = Field(...,
                                  min_length=1,
                                  title='List of authors of the paper',
                                  description='Affiliations are linked from authors individually.')
    affiliations: List[Affiliation] = Field(default=[],
                                            title='List of affiliations for all authors.')
    funders: List[Funder] = Field(default=[],
                                  title='List of funding agencies')
    keywords: List[str] = Field(default=[],
                                title='Author-supplied keywords',
                                description='This is pretty useless, but is preserved for posterity')
    title: Annotated[str, StringConstraints(min_length=1)] = Field(...,
                                        title='Title of paper',
                                        description='May contain LaTeX or HTML entities')
    subtitle: Optional[str] = Field(default=None,
                                    title='Subtitle of paper',
                                    description='May contain LaTeX or HTML entities')
    abstract: str = Field(...,
                          title='Abstract of paper',
                          description='This is an abstract of the paper. May contain minimal LaTeX but should not contain HTML.')
    license: License = Field(...,
                             title='License granted by authors',
                             description='When a paper is submitted, a license must be chosen. This field is required.')
    model_config = ConfigDict(json_schema_extra={
        '$schema': 'http://json-schema.org/draft-07/schema#'
    }, validate_default=True, validate_assignment=True, use_enum_values=True, extra="ignore")

    @model_validator(mode='after')
    def check_authors(self) -> 'Meta':
        """Validate field inter-dependencies."""
        authorcount_withemail = sum(1 for a in self.authors if a.email)
        if authorcount_withemail == 0:
            raise ValueError('At least one author must have an email.')
        last_affiliation_index = 1 + len(self.affiliations)
        for author in self.authors:
            if author.affiliations:
                for aff_index in author.affiliations:
                    if aff_index not in range(1, last_affiliation_index):
                        raise ValueError('Affiliation index {} out of range 1-{}'.format(aff_index, last_affiliation_index))
        return self

# A retricted form of ISO date format.
dt_regex = '^[0-9]{4}-[0-9]{2}-[0-9]{2} [0-9]{2}:[0-9]{2}:[0-9]{2}$'

# The type can be used to guide decisions by authors and copy editors.
# Errors almost certainly need attention, but warnings are a judgement
# call.
class ErrorType(StrEnum):
    METADATA_ERROR = 'metadata error'
    METADATA_WARNING = 'metadata warning'
    LATEX_ERROR = 'Latex error'
    REFERENCE_ERROR = 'reference error'
    DUPLICATE_LABEL = 'duplicate label'
    LATEX_WARNING = 'Latex warning'
    OVERFULL_HBOX = 'overfull hbox'
    UNDERFULL_HBOX = 'underfull hbox'
    OVERFULL_VBOX = 'overfull vbox'
    UNDERFULL_VBOX = 'underfull vbox'
    SERVER_WARNING = 'server warning' # produced by the server and not LaTeX itself.
    SERVER_ERROR = 'server error' # produced by the server and not LaTeX itself.


class CompileError(BaseModel):
    error_type: ErrorType = Field(...,
                                  title='type of error',
                                  description='This tells you which fields should be populated')
    text: str = Field(...,
                      title = 'Description of problem',
                      description = 'Textual description of problem for author. A required field.')
    logline: int = Field(...,
                         title='Line in log where it occurs',
                         description='This is the start of where the error occurs, but there may be lines after it.')
    package: Optional[str] = Field(default=None,
                                   title='LaTeX package name',
                                   description='Populated when we find it. Not required')
    pageno: int = Field(default=0,
                        title = 'Page number in PDF',
                        description = 'Page number where problem appears. May required.')
    pdf_line: int = Field(default=0,
                          title = 'Line number in PDF',
                          description = 'Line number in copyedit version. Not required.')
    filepath: Optional[str] = Field(default=None,
                                    title='path to LaTeX file',
                                    description = 'Location of LaTeX error or warning. Not required.')
    filepath_line: int = Field(default=0,
                               title = 'Line number location for LaTeX warning',
                               description = 'Line number in filepath where LaTeX warning occurred. Not required.')
    severity: float = Field(default=0,
                            title='Severity of overfull or underfull hbox or vbox.',
                            description='For overfull boxes, it is the size in pts. For underfull boxes it is badness.')
    help: Optional[str] = Field(default=None,
                                title='Help for authors',
                                description='The parser may have more to say about an error')


class Compilation(BaseModel):
    paperid: Annotated[str, StringConstraints(min_length=3)] = Field(...,
                                          title='Globally unique paper ID constructed in review system',
                                          description='ID must be globally unique.')
    venue: Annotated[str, StringConstraints(min_length=3)] = Field(...,
                                        title='The venue for the publication',
                                        description='This determines which cls to use. It\'s the hotcrp_key in the Journal object db_models.py.')
    status: CompileStatus = Field(default=CompileStatus.COMPILING,
                                  title='Current status',
                                  description='Indicates what stage the paper is at')
    email: EmailStr = Field(...,
                            title='Email for submitting author',
                            description='Who submitted the paper')
    submitted: Annotated[str, StringConstraints(pattern=dt_regex)] = Field(...,
                                              title='When paper was submitted for publication',
                                              description='Authenticated upon submission.')
    accepted: Annotated[str, StringConstraints(pattern=dt_regex)] = Field(...,
                                               title='When the paper was accepted for publication',
                                               description = 'Authenticated upon acceptance.')
    compiled: datetime = Field(...,
                               title='When the article was last compiled',
                               description='Last compilation date')
    compile_time: Optional[float] = Field(default=None,
                                          title='Number of seconds for compilation',
                                          description='May be none before it is compiled')
    engine: str = Field(default='pdflatex',
                        title='latex engine used',
                        description='Choices are currently pdflatex, lualatex, xelatex')
    command: str = Field(title='latexmk command that was run')
    log: Optional[str] = Field(default=None,
                     title='Log from running latexmk',
                     description='Will be absent until latex is attempted.')
    error_log: List[CompileError] = Field(...,
                                          title='Error messages if some step failed',
                                          description='Used in the UI if necessary. See status')
    warning_log: List[CompileError] = Field(...,
                                            title='Warning messages',
                                            description='May be used to warn author of overfull hbox, missing DOI in bibtex, etc')
    exit_code: int = Field(default=-1,
                            title='Exit code from running latexmk',
                            description='These are not well defined.')
    zipfilename: str = Field(...,
                             title='Name of uploaded zipfile',
                             description='Useful for authors to know what they uploaded.')
    meta: Optional[Meta] = Field(default=None,
                                 title='Parsed metadata',
                                 description='Present once status passes COMPILATION_SUCCESS')
    output_files: List[str] = Field(default=[],
                                    title='List of file paths in output directory',
                                    description='Paths are relative to the output directory')
    bibtex: Optional[str] = Field(default=None,
                                  title='BibTeX entries that are cited',
                                  description='List of references cited from the paper in BibTeX format. These are not guaranteed to be valid, but are what the author supplied.')
    

if __name__ == '__main__':
    print(LicenseEnum.license_from_iacrcc('CC-by'))
    print(json.dumps(Compilation.model_json_schema(), indent=2))
