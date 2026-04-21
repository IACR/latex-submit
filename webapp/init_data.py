"""
This file holds pydantic schemas for some objects that are used
to initialize the database in both test and production. The InitData
object is specified in the config and loaded when initialize_data
is called from create_app.
"""

from pydantic import BaseModel, Field, ConfigDict, EmailStr
from typing import List, Optional

class InitJournal(BaseModel):
    hotcrp_key: str = Field(...,
                            title='Key by which the journal is known in hotcrp.',
                            description='This is a unique key used to identify the journal.')
    acronym: str = Field(...,
                         title='Acronym by which the journal is known.')
    name: str = Field(...,
                      title='Name of the journal')
    publisher: str = Field(...,
                           title='Name of the publisher')
    EISSN: str = Field(...,
                       title='Electronic ISSN of journal')
    DOI_PREFIX: str = Field(...,
                            title='DOI prefix for the journal')
    editors: List[EmailStr] = Field(...,
                                    min_length=1,
                                    title='List of user emails who are editors.')
    copyeditors: List[EmailStr] = Field([],
                                        title='List of user emails who are copy editors')
    viewers: List[EmailStr] = Field([],
                                    title='List of user emails who are just viewers')

class InitUser(BaseModel):
    email: EmailStr = Field(...,
                            title='Email of user. This is unique in the database.')
    name: str = Field(...,
                      title='Name of user')
    password: str = Field(default="mypowers",
                          title='Password of user')
    is_admin: bool = Field(default=False,
                           title='Whether the user is an admin.')
    confirmed: bool = Field(default=False,
                            title='Whether the email was already confirmed')

class InitData(BaseModel):
    """Used to initialize the system in debugging. It allows us to insert
    some data into the database prior to running tests or running it in
    debug mode."""
    users: List[InitUser] = Field(default=[],
                                  title='List of users')
    journals: List[InitJournal] = Field(default=[],
                                        title='List of journals')
    model_config = ConfigDict(extra='forbid')

if __name__ == '__main__':
    from pathlib import Path
    import sys
    initfile = Path(sys.argv[1])
    data = InitData.model_validate_json(initfile.read_text(encoding='UTF-8'))
    print(data.model_dump_json(indent=2))
    
