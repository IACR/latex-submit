"""
This is for exporting a bundle of papers for an issue. The format consists of a zip file with
three components:
1. a file issue.json that contains metadata.
2. a subdirectory 'papers' that directories named by the paperid.
3. within each subdirectory it contains main.pdf, compilation.json, and all.zip
   with the LaTeX sources.
"""
from datetime import datetime
from flask import current_app as app
import json
from pathlib import Path
import zipfile

try:
    from .metadata.db_models import Issue, Journal, PaperStatus, Version
except Exception as e:
    from metadata.db_models import Issue, Journal, PaperStatus, Version

def export_issue(input_path: Path, output_path: Path, issue: Issue):
    """input_path is the DATA_DIR from app.config"""
    volume = issue.volume
    issuedata = {'issue': issue.name,
                 'volume': volume.name,
                 'year': datetime.now().year,
                 'paper_numbers': {}}
    # This assumes that all papers associated with the issue are ready to be published
    for paperstatus in issue.papers:
        if paperstatus.status == PaperStatusEnum.COPY_EDIT_ACCEPT:
            issuedata['paper_numbers'][paperstatus.paperid] = paperstatus.paperno
    if issue.description:
        issuedata['title'] = issue.description
    filename = '{}_{}.zip'.format(volume.name, issue.name)
    zip_path = output_path / Path(filename)
    zip_file = zipfile.ZipFile(zip_path, 'w')
    zip_file.writestr('issue.json', json.dumps(issuedata, indent=2))
    # This assumes that all papers associated with the issue are ready to be published
    for paperstatus in issue.papers:
        paper_path = input_path / Path(paperstatus.paperid) / Path(Version.FINAL.value)
        pdf_file = paper_path / Path('output/main.pdf')
        if not pdf_file.is_file():
            raise ValueError('missing PDF file {}'.format(str(pdf_file)))
        json_file = paper_path / Path('compilation.json')
        if not json_file.is_file():
            raise ValueError('missing JSON file {}'.format(str(json_file)))
        latex_zip_file = paper_path / Path('all.zip')
        if not latex_zip_file.is_file():
            raise ValueError('missing all.zip file {}'.format(str(latex_zip_file)))
        zip_file.write(str(pdf_file), arcname='papers/{}/main.pdf'.format(paperstatus.paperid))
        zip_file.write(str(json_file), arcname='papers/{}/compilation.json'.format(paperstatus.paperid))
        zip_file.write(str(latex_zip_file), arcname='papers/{}/latex.zip'.format(paperstatus.paperid))
    zip_file.close()

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
