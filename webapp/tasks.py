"""This defines the tasks to be run in executor.
"""
import json
import logging
import os
import re
from pathlib import Path
from urllib.parse import urlencode
import time
from .compiler import runner
from . import db, task_queue
#from .metadata import meta_parse
from .metadata.latex.iacrcc.parser import meta_parse
from .metadata.meta_parse import clean_abstract, validate_abstract, check_bibtex, extract_bibtex
from .metadata.compilation import Compilation, Meta, CompileStatus, VersionEnum, CompileError, ErrorType, LicenseEnum
from .log_parser import LatexLogParser, BibTexLogParser
from .metadata.db_models import CompileRecord, TaskStatus, PaperStatus
from sqlalchemy import select

def is_fatal(err):
    """This is used to classify log messages as "fatal" meaning they need to
       be corrected by the author. Some are indications that the compilation
       failed, but others like missing references are deemed fatal by this
       implementation. This is a policy decision."""
    if err.error_type in (ErrorType.METADATA_ERROR,
                          ErrorType.LATEX_ERROR,
                          ErrorType.REFERENCE_ERROR,
                          ErrorType.SERVER_ERROR,
                          ErrorType.BIBTEX_ERROR):
        return True
    # if err.error_type == ErrorType.OVERFULL_HBOX and err.severity > 40:
    #     return True
    # if err.error_type == ErrorType.OVERFULL_VBOX and err.severity > 100:
    #     return True
    if err.text == 'LaTeX Warning: There were undefined references.':
        return True
    return False

def run_latex_task(cmd, paper_path, paperid, doi, version, task_key):
    """Execute latex on input_path contents, writing into output_path.
    args:
       cmd: latex command to run
       paper_path: absolute string path to directory containing compilation.json
       paperid: unique id for paper
       version: a value of Version enum
       task_key: string from paper_key(paperid, version)
    returns:
       an array with possible 'error' strings.
    raises an exception if it cannot proceed.
    """
    # The contract from compile.runner is that output may
    # eventually contain exit_code, log, and an array of warnings.
    # We may add fatal errors.
    output = {'errors': []}
    try:
        task_status = TaskStatus.FINISHED
        execution_time = -1
        paper_path = Path(paper_path)
        input_path = paper_path / Path('input')
        output_path = paper_path / Path('output')
        try:
            start_time = time.time()
            output = runner.run_latex(cmd, input_path, output_path)
            # The contract is that output may contain exit_code, log, and
            # an array of warnings.
            end_time = time.time()
            execution_time = round(end_time - start_time, 2)
        except Exception as e:
            logging.error('Exception running latex: ' + str(e))
            output['errors'].append('Exception running latex: ' + str(e))
            task_status = TaskStatus.FAILED_EXCEPTION
        json_file = Path(paper_path) / Path('compilation.json')
        compilation = None
        comprec = CompileRecord.query.filter_by(paperid=paperid,version=version).first()
        try:
            if not comprec:
                logging.error('no CompileRecord for {}'.format(paperid))
                raise Exception('no CompileRecord')
            compilation = Compilation.model_validate_json(comprec.result)
            compilation.compile_time = execution_time
            compilation.log = output.get('log', 'no log')
            compilation.output_files = sorted([str(p.relative_to(str(output_path))) for p in output_path.rglob('*') if p.is_file()])
            for warning in output.get('warnings', []):
                compilation.warning_log.append(CompileError(error_type=ErrorType.SERVER_WARNING,
                                                            logline=0,
                                                            text=warning))
            for error in output.get('errors', []):
                compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                          logline=0,
                                                          text=error))
            logfile = output_path / 'main.log'
            if logfile.is_file():
                # Note: the class_file will be updated when it runs.
                logparser = LatexLogParser(main_file='main.tex', class_file='iacrcc.cls')
                logparser.parse_file(logfile)
                for error in logparser.errors:
                    if is_fatal(error):
                        compilation.error_log.append(error)
                        compilation.status = CompileStatus.COMPILATION_ERRORS
                    else:
                        compilation.warning_log.append(error)
                biblogfile = output_path / Path('main.blg')
                if biblogfile.is_file():
                    biblog_parser = BibTexLogParser()
                    biblog_parser.parse_file(biblogfile)
                    for error in biblog_parser.errors:
                        if is_fatal(error):
                            compilation.error_log.append(error)
                            compilation.status = CompileStatus.COMPILATION_ERRORS
                        else:
                            compilation.warning_log.append(error)
                else:
                    compilation.warning_log.append(CompileError(error_type=ErrorType.BIBTEX_ERROR,
                                                                logline=0,
                                                                text='Unable to parse bibtex/biber log'))
            if output.get('errors', []):
                compilation.status = CompileStatus.COMPILATION_FAILED
            compilation.exit_code = output.get('exit_code', -1)
            if compilation.exit_code != 0:
                compilation.status = CompileStatus.COMPILATION_FAILED
                compilation.error_log.insert(0, CompileError(error_type=ErrorType.LATEX_ERROR,
                                                             logline=0,
                                                             text='Exit code of {} because the compilation failed'.format(compilation.exit_code)))
            elif compilation.venue != 'cic':
                compilation.status = CompileStatus.COMPILATION_SUCCESS
            if compilation.status != CompileStatus.COMPILATION_FAILED:
                extract_bibtex(output_path, compilation)
                check_bibtex(compilation)
                if compilation.venue == 'cic':
                    # Look for stuff we need for iacrcc.
                    metafile = output_path / Path('main.meta')
                    if metafile.is_file():
                        try:
                            metastr = metafile.read_text(encoding='UTF-8', errors='replace')
                            data = meta_parse.parse_meta(metastr)
                            abstract_file = Path(output_path) / Path('main.abstract')
                            if not abstract_file.is_file():
                                compilation.status = CompileStatus.MISSING_ABSTRACT
                                compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                          logline=0,
                                                                          text='An abstract is required.'))
                            else:
                                data['abstract'] = clean_abstract(abstract_file.read_text(encoding='UTF-8', errors='replace'))
                                if not validate_abstract(data['abstract']):
                                    compilation.status = CompileStatus.MISSING_ABSTRACT
                                    compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                              logline=0,
                                                                              text='The textabstract environment contains illegal macros or environments. See the HTML tab.'))
                            if 'license' not in data:
                                compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                          logline=0,
                                                                          text='A license is required.'))
                            else:
                                try:
                                    # Translate license keys from iacrcc.cls to keys in LicenseEnum.
                                    data['license'] = LicenseEnum.license_from_iacrcc(data['license'])
                                except ValueError as e:
                                    data['license'] = LicenseEnum.CC_BY.value.model_dump()
                                    logging.error('License assigned by default as CC_BY')
                            compilation.meta = Meta(**data)
                            compilation.meta.DOI = doi
                            # Check authors to see if they have ORCID and affiliations.
                            for author in compilation.meta.authors:
                                if not author.orcid:
                                    compilation.warning_log.insert(0, CompileError(error_type=ErrorType.METADATA_WARNING,
                                                                                   logline=0,
                                                                                   help='See <a target="_blank" href="https://orcid.org/orcid-search/search?{}">ORCID search</a>'.format(urlencode({'searchQuery': author.name})),
                                                                                   text='author {} is lacking an ORCID. They are strongly recommended for all authors.'.format(author.name)))
                                if not author.affiliations:
                                    compilation.warning_log.insert(0, CompileError(error_type=ErrorType.METADATA_WARNING,
                                                                                   logline=0,
                                                                                   text='author {} is lacking an affiliation'.format(author.name)))
                                else:
                                    for affindex in author.affiliations:
                                        aff = compilation.meta.affiliations[affindex-1]
                                        if not aff.ror:
                                            compilation.warning_log.insert(0, CompileError(error_type=ErrorType.METADATA_WARNING,
                                                                                           logline=0,
                                                                                           text='affiliation {} may have a ROR ID'.format(aff.name),
                                                                                           help='See <a href="https://ror.org/search?{}" target="_blank">ROR search</a>'.format(urlencode({'query': aff.name}))))
                            if compilation.meta.version != VersionEnum.FINAL:
                                compilation.status = CompileStatus.WRONG_VERSION
                                compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                          logline=0,
                                                                          text='Paper should use documentclass[version=final]',
                                                                          help='See <a href="/iacrcc">the documentation for iacrcc.cls</a>'))
                            elif compilation.error_log:
                                compilation.status = CompileStatus.COMPILATION_ERRORS
                            else:
                                compilation.status = CompileStatus.COMPILATION_SUCCESS
                        except Exception as me:
                            compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                      logline=0,
                                                                      text='Failure to extract metadata: ' + str(me)))
                            compilation.status = CompileStatus.METADATA_PARSE_FAIL
                    else:
                        compilation.status = CompileStatus.METADATA_FAIL
                        compilation.error_log.append(CompileError(error_type=ErrorType.METADATA_ERROR,
                                                                  logline=0,
                                                                  text='No metadata file. Are you sure you used iacrcc?'))
            # This is a legacy to attempt to fix issue #12. I gave up and
            # made it dependent on the value in the database, but we still
            # store the compilation.json file.
            # We do not use pathlib functions here in order to use
            # os.fsync to flush data from this write all the way
            # through the OS buffers. Otherwise the other thread
            # may not see the output from this file. As it turns out,
            # it still isn't seen so we switched to the database.
            jfile = open(str(json_file.resolve()), 'w', encoding='UTF-8')
            jfile.write(compilation.model_dump_json(indent=2, exclude_none=True))
            jfile.flush()
            os.fsync(jfile.fileno())
            jfile.close()
        except Exception as e:
            compilation.error_log.append(CompileError(error_type=ErrorType.SERVER_ERROR,
                                                      logline=0,
                                                      text='exception someplace: ' + str(e)))
        # Update the database record with the compilation and status.
        comprec.result = compilation.model_dump_json(indent=2, exclude_none=True)
        comprec.task_status = TaskStatus.FINISHED.value
        db.session.add(comprec)
        if compilation.meta:
            sql = select(PaperStatus).where(PaperStatus.paperid==paperid)
            paper_status = db.session.execute(sql).scalar_one_or_none()
            paper_status.title = compilation.meta.title
            if compilation.meta.authors:
                paper_status.authors = ', '.join([a.name for a in compilation.meta.authors])
            db.session.add(paper_status)
        db.session.commit()
        task_queue.pop(task_key, None)
    except Exception as e:
        logging.error('ERROR in task: {}'.format(str(e)))
    return output.get('errors', [])

