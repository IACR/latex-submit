"""
This contains the data model for indexed entities. The main classes
are Funder and FunderList. Both Relationship and Funder inherit from
GlobalEntity because they have a data source and id within that source.

The FunderType below is a union of types found in both ROR and FundReg
(but mostly ROR). The distribution of types that we found in FundReg are:
   7503 Trusts, charities, foundations (both public and private) => NONPROFIT
   5666 Universities (academic only) => EDU
   4774 Local government => GOV
   3251 National government => GOV
   2860 Associations and societies (private and public) => OTHER
   2813 Research institutes and centers => INSTITUTE
   2497 Other non-profit organizations => NONPROFIT
   2590 For-profit companies (industry) => COMPANY
    263 International organizations => OTHER
     31 Libraries and data archiving organizations => ARCHIVE

Funder types in ROR have the following distribution:
  29547 Company => COMPANY
  19972 Education => EDU
  13872 Nonprofit => NONPROFIT
  13024 Healthcare => HEALTH
   9406 Facility => FAC
   8150 Other => OTHER
   6138 Government => GOV
   2853 Archive => ARCHIVE
"""

from enum import Enum
from pydantic import StringConstraints, ConfigDict, BaseModel, Field, conint, conlist, validator, AnyUrl
from typing import List, Dict, Optional, Union, Literal
from typing_extensions import Annotated

class StrEnum(str, Enum):
    @classmethod
    def from_str(cls, val):
        """Convert string to enum value."""
        for e in cls:
            if e.value == val:
                return e
        return None

class DataSource(StrEnum):
    """We index two types of organizations."""
    FUNDREG = 'fundreg'
    ROR     = 'ror'
    MERGED  = 'merged' # merged from FUNDREG and ROR.
    
class FunderType(StrEnum):
    """These are from ROR, and we map FundReg to these."""
    EDU = "Education",       # ROR and FundReg
    HEALTH = "Healthcare",   # ROR only
    COMPANY = "Company",     # ROR and FundReg
    ARCHIVE = "Archive",     #  ROR and FundReg
    NONPROFIT = "Nonprofit", # ROR and FundReg
    GOV = "Government",      # ROR and FundReg
    FAC = "Facility",        # ROR and FundReg
    INSTITUTE = 'Institute'  # FundReg only.
    OTHER = "Other"          # ROR and FundReg
    
class RelationshipType(StrEnum):
    RELATED     = 'Related'
    PARENT      = 'Parent'
    CHILD       = 'Child'
    SUCCESSOR   = 'Successor'   # currently unused.
    PREDECESSOR = 'Predecessor' # currently unused

class GlobalEntity(BaseModel):
    """GlobalEntity has a source and source_id."""
    source: DataSource = Field(...,
                                    title='Original source of data',
                                    description='We prefer fundref, but this is not complete')
    source_id: str = Field(...,
                           title='Unique ID within the data source',
                           description=('See global_id() for a global ID. '
                                        'This is the ROR suffix for ROR entities, and '
                                        'the Funding Registry ID for FundReg entities.'))
    def global_id(self):
        return '{}_{}'.format(self.source.value, self.source_id)


class Relationship(GlobalEntity):
    """This picks up source, source_id, and global_id() from GlobalEntity."""
    name: str = Field(...,
                      title='Name of entity.',
                      description='May not be the same as other names.')

class Funder(GlobalEntity):
    """Funder may come from Funder's Registry or ROR.  This picks up
       source, source_id, and global_id() from GlobalEntity.
    """
    name: Annotated[str, StringConstraints(min_length=2)] = Field(...,
                                       title='The main name of the organization',
                                       description='Other names are in altnames')
    country: str = Field(...,
                         title='Country of affiliation',
                         description='May be any string')
    country_code: Optional[str] = Field(default=None,
                                        title='ISO 3-letter country code.',
                                        description='Optional')
    funder_type: FunderType = Field(...,
                                    title='The type of funding agency',
                                    description='May be from ROR.')
    preferred_fundref: Optional[str] = Field(default=None,
                                             title='ROR may stipulate a preferred FundRef value',
                                             description='We use this to merge ROR records')
    altnames: List[str] = Field(...,
                                title='List of alternative names',
                                description='May be in a language other than English')
    children: List[Relationship] = Field(...,
                                         title='Child entities',
                                         description='From FundReg and ROR.')
    parents: List[Relationship] = Field(...,
                                        title='Parent entities',
                                        description='From FundReg and ROR.')
    related: List[Relationship] = Field(...,
                                        title='Related entities',
                                        description='From FundReg and ROR.')
    model_config = ConfigDict(title='Funder entity that sponsors Research', validate_default=True, validate_assignment=True, extra="forbid")

class FunderList(BaseModel):
    """This is really a dict rather than a list. It facilitates easy lookup by global_id."""
    funders: Dict[str, Funder] = Field(...,
                                       title='Map from global_id to Funder objects',
                                       description='Useful for serialization and lookup')

def add_names_to_relationships(funderlist):
    """When ROR entities are read in, they contain relationships specified by ID
           without names. This propagates the names to the relationships by looking them
           up.
        """
    for funder in funderlist.funders.values():
        # lookup the names for all relationships.
        for rel in funder.children:
            if not rel.name:
                rel.name = funderlist.funders.get(rel.global_id()).name
        for rel in funder.parents:
            if not rel.name:
                rel.name = funderlist.funders.get(rel.global_id()).name
        for rel in funder.related:
            if not rel.name:
                rel.name = funderlist.funders.get(rel.global_id()).name

    
if __name__ == '__main__':
    print(Funder.schema_json(indent=2))
