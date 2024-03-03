"""
This is for exporting a bundle of papers for an issue. The format
 consists of a zip file with several components:
1. a issue.json file with metadata about the issue itself.
2. a subdirectory named `paperno` for each paper.
4. within each subdirectory it contains main.pdf, compilation.json, jats.xml, and all.zip
   with the LaTeX sources.

The issue.json file will contain:
  export: datetime
  issue_number: name of the issue
  volume_number: name of the volume
  issn: issn of journal
  journal_name:
The export schema for meta.json is an extension of the `compilation::Meta` object
in which some elements of `Compilation` itself are pushd down:
1. submitted
2. accepted
3. compiled
4. paperid
5. bibtex
6. email as 'corresponding_author'
7. pubtype
8. errata_doi (if present)

The jats.xml file is included because it has a well-established JATS
1.3 publishing tag set schema (see
https://jats.nlm.nih.gov/publishing/tag-library/1.3/chapter/journal-tag-set-intro.html).
It is derived from other metadata including the issue, and includes only
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
        return obj.strftime('%Y-%m-%d %H:%M:%S')
    raise TypeError('Type {} is not serializable'.format(str(type(obj))))

def export_issue(data_path: Path, output_path: Path, issue: Issue) -> datetime:
    """data_path is the DATA_DIR from app.config"""
    volume = issue.volume
    journal = volume.journal
    now = datetime.now()
    issuedata = {'exported': now,
                 'issue_number': issue.name,
                 'volume_number': volume.name,
                 'journal_name': journal.name,
                 'journal_acronym': journal.acronym,
                 'publisher': journal.publisher,
                 'year': now.year,
                 'paper_numbers': {}}
    if journal.EISSN:
        issuedata['EISSN'] = journal.EISSN
    if issue.hotcrp:
        issuedata['hotcrp'] = issue.hotcrp
    if issue.description:
        issuedata['issue_description'] = issue.description
    filename = '{}_{}.zip'.format(volume.name, issue.name)
    zip_path = output_path / Path(filename)
    zip_file = zipfile.ZipFile(zip_path, 'w')
    # We only export papers in the issue that have status of COPY_EDIT_ACCEPT
    # The UI should only show the export feature if this is true, but we check anyway.
    export_papers = []
    for paperstatus in issue.papers:
        if paperstatus.status == PaperStatusEnum.COPY_EDIT_ACCEPT:
            issuedata['paper_numbers'][paperstatus.paperid] = paperstatus.paperno
            export_papers.append(paperstatus)
    for paperstatus in export_papers:
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
        # build a json object from compilation. The schema for this is in the
        # IACR/cicjournal repository as PaperMeta, and tha tmust be kept in sync with
        # what we export here. Ideally we would share the code for these, but I hate
        # git submodules. We essentially create an extended Meta class that contains
        # elements of Compilation.
        data = comp.meta.model_dump(exclude={'version': True})
        data['submitted'] = comp.submitted
        data['accepted'] = comp.accepted
        data['compiled'] = comp.compiled.strftime('%Y-%m-%d %H:%M:%S')
        data['pubtype'] = comp.pubtype.name
        data['errata_doi'] = comp.errata_doi
        data['paperid'] = comp.paperid
        data['bibtex'] = comp.bibtex
        data['corresponding_author'] = comp.email
        zip_file.writestr('{}/meta.json'.format(paperstatus.paperno),
                          json.dumps(data, indent=2, default=_datetime_serialize))
        jats_elem = get_jats(issue.volume.journal, '{}/{}/{}'.format(issue.volume.name,
                                                                     issue.name,
                                                                     paperstatus.paperno), comp)
        ET.indent(jats_elem, space='  ', level=0)
        jats_str = ET.tostring(jats_elem, encoding='utf-8').decode('utf-8')
        zip_file.writestr('{}/jats.xml'.format(paperstatus.paperno), jats_str)
    zip_file.writestr('issue.json', json.dumps(issuedata, indent=2, default=_datetime_serialize))
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
