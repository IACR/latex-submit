"""
This contains the data model for indexed documents.
"""

from pydantic import StringConstraints, BaseModel, Field
from typing import List
from typing_extensions import Annotated

class Document(BaseModel):
    """The model of a bibtex entry to be indexed."""
    key: str = Field(...,
                     title='Globally unique document ID from cryptobib')
    title: Annotated[str, StringConstraints(min_length=2)] = Field(...,
                                                                   title='The title of the document')
    authors: List[str] = Field(default=[],
                               title='bibtex author names')
    venue: str = Field(...,
                       title='booktitle or journal name')
    year: int
    pubtype: str = Field(...,
                         title='The bibtex entry type')
    doi: str = Field(default=None,
                     title='Optional DOI for reference')
    raw: str = Field(...,
                     title='Raw bibtex document')


if __name__ == '__main__':
    import json
    print(json.dumps(Document.model_json_schema(), indent=2))
