"""This is for exporting a bundle of papers for an issue. The format consists of a zip file with
three components:
1. a file issue.json that contains metadata.
2. a subdirectory named `paperno` for each paper.
3. within each subdirectory it contains main.pdf, compilation.json, jats.xml, and all.zip
   with the LaTeX sources.

The compilation.json file is exported from
metadta/compilation.py::Compilation, and there is a JSON schema to
describe this as well as a python file to validate them. The jats.xml
file is included because it has a well-established JATS 1.3 publishing
tag set schema (see
https://jats.nlm.nih.gov/publishing/tag-library/1.3/chapter/journal-tag-set-intro.html). It
is derived from other metadata including the issue, and includes only
the <front> and <back> elements of an article (not the content). Note
that some metadata elements such as submission date and acceptance
date are only in the compilation.json file.
"""

from datetime import datetime
from flask import current_app as app
import json
from pathlib import Path
from xml.etree import ElementTree as ET
import zipfile
from .metadata.compilation import Compilation
from .metadata.xml_meta import get_jats
from . import db

try:
    from .metadata.db_models import Issue, PaperStatusEnum, Version
except Exception as e:
    from metadata.db_models import Issue, PaperStatusEnum, Version

def _datetime_serialize(obj):
    if isinstance(obj, datetime):
        return obj.strftime('%Y-%m-%d %H-%M-%S')
    raise TypeError('Type {} is not serializable'.format(str(type(obj))))

def export_issue(data_path: Path, output_path: Path, issue: Issue) -> datetime:
    """data_path is the DATA_DIR from app.config"""
    volume = issue.volume
    now = datetime.now()
    issuedata = {'exported': now,
                 'issue_name': issue.name,
                 'volume_name': volume.name,
                 'year': now.year,
                 'paper_numbers': {}}
    if issue.hotcrp:
        issuedata['hotcrp'] = issue.hotcrp
    if issue.description:
        issuedata['issue_description'] = issue.description
    # This assumes that all papers associated with the issue are ready to be published
    for paperstatus in issue.papers:
        if paperstatus.status == PaperStatusEnum.COPY_EDIT_ACCEPT:
            issuedata['paper_numbers'][paperstatus.paperid] = paperstatus.paperno
    if issue.description:
        issuedata['title'] = issue.description
    filename = '{}_{}.zip'.format(volume.name, issue.name)
    zip_path = output_path / Path(filename)
    zip_file = zipfile.ZipFile(zip_path, 'w')
    zip_file.writestr('issue.json', json.dumps(issuedata, indent=2, default=_datetime_serialize))
    # This assumes that all papers associated with the issue are ready to be published
    for paperstatus in issue.papers:
        paper_path = data_path / Path(paperstatus.paperid) / Path(Version.FINAL.value)
        pdf_file = paper_path / Path('output/main.pdf')
        if not pdf_file.is_file():
            raise ValueError('missing PDF file {}'.format(str(pdf_file)))
        json_file = paper_path / Path('compilation.json')
        if not json_file.is_file():
            raise ValueError('missing JSON file {}'.format(str(json_file)))
        latex_zip_file = paper_path / Path('all.zip')
        if not latex_zip_file.is_file():
            raise ValueError('missing all.zip file {}'.format(str(latex_zip_file)))
        zip_file.write(str(pdf_file), arcname='{}/main.pdf'.format(paperstatus.paperno))
        zip_file.write(str(latex_zip_file), arcname='{}/latex.zip'.format(paperstatus.paperno))
        comp = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
        # Remove some fields from the compilation.
        data = comp.model_dump(exclude={'email': True,
                                        'status': True,
                                        'exit_code': True,
                                        'error_log': True,
                                        'warning_log': True,
                                        'zipfilename': True,
                                        'output_files': True,
                                        'meta': {'version': True}})
        zip_file.writestr('{}/meta.json'.format(paperstatus.paperno),
                          json.dumps(data, indent=2, default=_datetime_serialize))
        jats_elem = get_jats(issue.volume.journal, '{}/{}/{}'.format(issue.volume.name,
                                                                     issue.name,
                                                                     paperstatus.paperno), comp)
        ET.indent(jats_elem, space='  ', level=0)
        jats_str = ET.tostring(jats_elem, encoding='utf-8').decode('utf-8')
        zip_file.writestr('{}/jats.xml'.format(paperstatus.paperno), jats_str)
    zip_file.close()
    return now

if __name__ == '__main__':
    """This is just for testing."""
    from sqlalchemy import create_engine, select
    from sqlalchemy.orm import Session
    import argparse
    argparser = argparse.ArgumentParser(description='exportor')
    argparser.add_argument('--issue_id',
                           type=int,
                           required=True)
    argparser.add_argument('--sqlalchemy_uri',
                           required=True)
    args = argparser.parse_args()
    engine = create_engine(args.sqlalchemy_uri)
    with Session(engine) as session:
        issue = session.execute(select(Issue).where(Issue.id == args.issue_id)).scalar_one_or_none()
        export_issue(Path('data/'),
                     Path('/tmp'),
                     issue)
