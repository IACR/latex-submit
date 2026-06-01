"""These routes are used for presenting information suitable for cut and paste
into the OJS quickSubmit plugin. It would have been better to export a format that
could be imported directly into OJS, but OJS has no working import path."""
from flask import Blueprint, render_template, send_file
from flask import current_app as app
try:
    from .admin import admin_message, viewer_only
except Exception as e:
    from admin import admin_message, viewer_only
from sqlalchemy import select
from flask import flash
from flask_security import auth_required, current_user, roles_required
import logging
import re
from pathlib import Path
from . import db
from .metadata import validate_paperid
from .metadata.compilation import Compilation
from .metadata.db_models import PaperStatus, Version, Issue, Role, Journal
from nameparser import HumanName

ojs_bp = Blueprint('ojs_file', __name__)

@ojs_bp.context_processor
def inject_view_only():
    return {
        'view_only': viewer_only()
        }

def regex_replace(s, find, replace):
    """A non-optimal implementation of a regex filter"""
    return re.sub(find, replace, s)

@ojs_bp.route('/admin/ojs/journal/<hotcrp_key>')
@auth_required()
def show_ojs_journal(hotcrp_key):
    if not (Role.ADMIN in current_user.roles or
            Role.viewer_role(hotcrp_key) in current_user.roles or
            Role.editor_role(hotcrp_key) in current_user.roles or
            Role.copyeditor_role(hotcrp_key) in current_user.roles):
        flash('You are missing a role')
        return redirect(url_for('home_bp.show_admin_home'))
    journal = db.session.execute(select(Journal).where(Journal.hotcrp_key==hotcrp_key)).scalar_one_or_none()
    return render_template('admin/ojs/ojs_journal.html',
                           journal=journal)

@ojs_bp.route('/admin/ojs/issue/<issue_id>')
@auth_required()
def show_ojs_issue(issue_id):
    issue = db.session.execute(select(Issue).where(Issue.id==issue_id)).scalar_one_or_none()
    if not issue:
        return admin_message('Unknown issue')
    hotcrp_key = issue.volume.journal.hotcrp_key
    if not (Role.ADMIN in current_user.roles or
            Role.viewer_role(hotcrp_key) in current_user.roles or
            Role.editor_role(hotcrp_key) in current_user.roles or
            Role.copyeditor_role(hotcrp_key) in current_user.roles):
        flash('You are missing a role')
        return redirect(url_for('home_bp.show_admin_home'))
    if not issue.exported:
        flash('WARNING: issue has not been exported yet, and may still change. Make sure you communicate with the editor about this')
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
    """This is used to remove divs from bibhtml."""
    return re.sub(_CLEANER, '', ref.body).replace('</div>', '')

@ojs_bp.route('/admin/ojs/paper/<paperid>')
@auth_required()
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
    app.jinja_env.filters['regex_replace'] = regex_replace
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
@auth_required()
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
