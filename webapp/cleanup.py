"""This is used only if config.DEMO_INSTANCE is True, and is
used to remove old articles.
"""

from datetime import datetime, timedelta
from pathlib import Path
import shutil

from sqlalchemy import create_engine, select
from sqlalchemy.orm import Session
from . import scheduler
from .metadata.db_models import PaperStatus

def cleanup_task():
    with scheduler.app.app_context():
        if scheduler.app.config['DEBUG']:
            scheduler.app.logger.warning('skipping cleanup of existing papers')
            return
        if scheduler.app.config['DEMO_INSTANCE']:
            scheduler.app.logger.warning('cleanup should not be configured')
            return
        scheduler.app.logger.warning('cleaning up papers')
        submit_deadline = datetime.now() - timedelta(days=1)
        copyedit_deadline = datetime.now() - timedelta(days=4)
        engine = create_engine(scheduler.app.config['SQLALCHEMY_DATABASE_URI'])
        deleted_ids = set()
        with Session(engine) as session:
            papers = session.execute(select(PaperStatus)).scalars().all()
            for paper in papers:
                if paper.status == PaperStatus.PENDING.value and paper.lastmodified < submit_deadline:
                    deleted_ids.add(paper.paperid)
                    session.delete(paper)
                elif paper.lastmodified < copyedit_deadline:
                    deleted_ids.add(paper.paperid)
                    session.delete(paper)
            session.commit()
        engine.dispose(True)
        for paperid in deleted_ids:
            dir = Path(scheduler.app.config['DATA_DIR']) / Path(paperid)
            try:
                shutil.rmtree(dir)
                scheduler.app.logger.warning('Deleted {}'.format(dir.name))
            except Exception as e:
                scheduler.app.logger.warning('Unable to delete the directory for the paper {}. ({})'.format(str(dir.absolute()), str(e)))
            
