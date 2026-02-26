"""These routes are used for presenting information suitable for cut and paste
into the OJS quickSubmit plugin. It would have been better to export a format that
could be imported directly into OJS, but OJS has no working import path."""
from flask import Blueprint, render_template, send_file
from flask import current_app as app
try:
    from .admin import admin_required, admin_message
except Exception as e:
    from admin import admin_required, admin_message
from sqlalchemy import select
from flask_login import login_required, current_user
import logging
import re
from pathlib import Path
from . import db
from .metadata import validate_paperid
from .metadata.compilation import Compilation
from .metadata.db_models import PaperStatus, Version, Issue
from nameparser import HumanName

ojs_bp = Blueprint('ojs_file', __name__)

@ojs_bp.route('/admin/ojs/issue/<issue_id>')
@login_required
@admin_required
def show_ojs_issue(issue_id):
    issue = db.session.execute(select(Issue).where(Issue.id==issue_id)).scalar_one_or_none()
    if not issue:
        return admin_message('Unknown issue')
    if not issue.exported:
        return admin_message('Issue has not been exported')
    volume = issue.volume
    journal = volume.journal
    papers = db.session.execute(select(PaperStatus).where(PaperStatus.issue_id==issue_id)).scalars().all()
    data = {'title': 'Exported issue view for OJS',
            'journal': journal,
            'issue': issue,
            'volume': volume,
            'papers': papers}
    return render_template('admin/ojs/ojs_issue.html', **data)

_CLEANER = re.compile('<div .*?>')
def _clean_html(ref):
    return re.sub(_CLEANER, '', ref.body).replace('</div>', '')

@ojs_bp.route('/admin/ojs/paper/<paperid>')
@login_required
@admin_required
def show_ojs_paper(paperid):
    if not validate_paperid(paperid):
        return admin_message('Invalid paperid: {}'.format(paperid))
    paper = db.session.execute(select(PaperStatus).where(PaperStatus.paperid == paperid)).scalar_one_or_none()
    if not paper:
        return admin_message('Unknown paper: {}'.format(paperid))
    issue = paper.issue
    if not issue:
        return admin_message('Paper with no issue: {}'.format(paperid))
    volume = issue.volume
    journal = volume.journal
    paper_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path(Version.FINAL.value)
    if not paper_path.is_dir():
        return admin_message('Unable to open directory: ' + str(paper_path))
    comp_file = paper_path / Path('compilation.json')
    try:
        comp = Compilation.model_validate_json(comp_file.read_text(encoding='UTF-8'))
    except Exception as e:
        logging.error('Unable to read compilation {}:{}'.format(paperid, str(e)))
        return admin_message('Unable to read json file for paper')
    references = [_clean_html(ref) for ref in comp.bibhtml]
    authors = []
    for author in comp.meta.authors:
        aut = author.model_dump()
        hn = HumanName(author.name)
        parts = author.name.split()
        if hn.first:
            aut['given'] = hn.first
        else:
            aut['given'] = parts[0]
        if hn.last:
            aut['surname'] = hn.last
        else:
            aut['surname'] = parts[-1]
        aut['country'] = ''
        if author.affiliations:
            affs = [comp.meta.affiliations[i-1] for i in author.affiliations]
            affiliations = []
            for aff in affs:
                affiliation = aff.name
                if aff.city:
                    affiliation += ', ' + aff.city
                if aff.country:
                    affiliation += ', ' + aff.country
                affiliations.append(affiliation)
            aut['affiliations'] = ', '.join(affiliations)
            for aff in affs:
                if aff.country:
                    aut['country'] = aff.country
        else:
            aut['affiliations'] = ''
        authors.append(aut)
    data = {'title': 'Paper {}'.format(paperid),
            'paper': paper,
            'issue': issue,
            'volume': volume,
            'journal': journal,
            'references': references,
            'authors': authors,
            'comp': comp}
    return render_template('admin/ojs/ojs_paper.html', **data)

@ojs_bp.route('/admin/ojs/paper/pdf/<paperid>')
@login_required
@admin_required
def download_pdf(paperid):
    paper = db.session.execute(select(PaperStatus).where(PaperStatus.paperid == paperid)).scalar_one_or_none()
    if not paper:
        return admin_message('Unable to open paper')
    pdf_path = Path(app.config['DATA_DIR']) / Path(paperid) / Path('final') / Path('output/main.pdf')
    if not pdf_path.is_file():
        return admin_message('Unable to open file')
    issue = paper.issue
    volume = issue.volume
    download_name = f'{volume.name}_{issue.name}_{paper.paperno}_{paperid}.pdf'
    return send_file(str(pdf_path.absolute()), mimetype='application/pdf', as_attachment=True, download_name=download_name)
