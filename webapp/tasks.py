"""This defines the tasks to be run in executor.
"""
import json
import os
import re
from pathlib import Path
import time
from .compiler import runner
from . import db, task_queue
#from .metadata import meta_parse
from .metadata.latex.iacrcc.parser import meta_parse
from .metadata.meta_parse import clean_abstract, check_bibtex
from .metadata.compilation import Compilation, Meta, CompileStatus, VersionEnum, FileTree
from .db_models import CompileRecord, TaskStatus


def run_latex_task(cmd, paper_path, paperid, version, task_key):
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
        output['errors'] = []
        end_time = time.time()
        execution_time = round(end_time - start_time, 2)
    except Exception as e:
        output['errors'].append('Exception running latex: ' + str(e))
        task_status = TaskStatus.FAILED_EXCEPTION
    json_file = Path(paper_path) / Path('compilation.json')
    compilation = None
    comprec = CompileRecord.query.filter_by(paperid=paperid,version=version).first()
    try:
        if not comprec:
            raise Exception('no CompileRecord')
        compilation = Compilation.parse_raw(comprec.result)
        compilation.compile_time = execution_time
        compilation.log = output.get('log', 'no log')
        compilation.output_tree = FileTree.from_path(output_path)
        for warning in output.get('warnings', []):
            compilation.warning_log.append(warning)
        for error in output.get('errors', []):
            compilation.error_log.append(error)
        logfile = Path(output_path) / 'main.log'
        if logfile.is_file():
            try:
                latexlog = logfile.read_text(encoding='UTF-8')
            except Exception as e:
                compilation.warning_log.append('latex log is not UTF-8')
                try:
                    latexlog = logfile.read_text(encoding='iso-8859-1', errors='replace')
                except Exception as ee:
                    compilation.error_log.append('unable to read main.log as text')
                    latexlog = ''
            # Flag some warnings and errors from the log. We may want to process the log
            # line by line, since LaTeX is miserable at the try ... catch paradigm.
            if 'LaTeX Warning: There were undefined references' in latexlog:
                compilation.error_log.append('LaTeX Error: There were undefined references')
                compilation.status = CompileStatus.COMPILATION_ERRORS
            if 'Specify a country for each affiliation for the final version' in latexlog:
                compilation.error_log.append('At least one affiliation is missing a country')
                compilation.status = CompileStatus.COMPILATION_ERRORS
            if 'LaTeX Warning: There were multiply-defined labels.' in latexlog:
                compilation.error_log.append('There were multiply-defined labels.')
                compilation.status = CompileStatus.COMPILATION_ERRORS
            if 'Unable to redefine math accent' in latexlog:
                compilation.warning_log.append('You may have lost a math character. Search for "redefine math accent"')
            if 'Missing character' in latexlog:
                compilation.warning_log.append('You may have lost a character. Avoid using too many unusual fonts.')
            lines = latexlog.splitlines()
            overfull_pat = re.compile(r'^Overfull \\(v|h)box \((\d+\.)')
            for line in lines:
                if line.startswith('LaTeX Warning: Label '):
                    compilation.error_log.append(line)
                elif line.startswith('LaTeX Warning: Citation '):
                    compilation.error_log.append(line)
                res = overfull_pat.search(line)
                if res:
                    if res.group(1) == 'v' and len(res.group(2)) > 3: # vbox of 100pts at least
                        compilation.warning_log.append('Please fix: ' + line)
                    if res.group(1) == 'h' and len(res.group(2)) > 2: # hbox of 10pts at least.
                        if len(res.group(2)) > 3: # > 100pt too wide
                            compilation.error_log.append('Please fix: ' + line)
                        else:
                            compilation.warning_log.append('Please fix: ' + line)
        if output.get('errors', []):
            compilation.status = CompileStatus.COMPILATION_FAILED
        compilation.exit_code = output.get('exit_code', -1)
        if compilation.exit_code != 0:
            compilation.status = CompileStatus.COMPILATION_FAILED
            compilation.error_log.append('Exit code of {} means that the compilation failed'.format(compilation.exit_code))
        elif compilation.venue != 'cic':
            compilation.status = CompileStatus.COMPILATION_SUCCESS
        if compilation.status != CompileStatus.COMPILATION_FAILED:
            if compilation.venue == 'cic':
                # Look for stuff we need for iacrcc.
                metafile = Path(output_path) / Path('main.meta')
                if metafile.is_file():
                    try:
                        metastr = metafile.read_text(encoding='UTF-8')
                        data = meta_parse.parse_meta(metastr)
                        # Check to see if references have DOIs.
                        for citation in data.get('citations'):
                            if citation.get('ptype') in ['article', 'book', 'inproceedings'] and 'doi' not in citation:
                                compilation.warning_log.append('missing DOI on reference: {}: "{}". It is important to include DOIs when available.'.format(citation.get('id'), citation.get('title', '')))
                        abstract_file = Path(output_path) / Path('main.abstract')
                        if not abstract_file.is_file():
                            compilation.status = CompileStatus.MISSING_ABSTRACT
                            compilation.error_log.append('An abstract is required.')
                        else:
                            data['abstract'] = clean_abstract(abstract_file.read_text(encoding='UTF-8'))
                        compilation.meta = Meta(**data)
                        # Check authors to see if they have ORCID and affiliations.
                        for author in compilation.meta.authors:
                            if not author.orcid:
                                compilation.warning_log.append('author {} is lacking an ORCID. They are strongly recommended for all authors.'.format(author.name))
                            if not author.affiliations:
                                compilation.warning_log.append('author {} is lacking an affiliation'.format(author.name))
                        if compilation.meta.version != VersionEnum.FINAL:
                            compilation.status = CompileStatus.WRONG_VERSION
                            compilation.error_log.append('Paper should use documentclass[version=final]')
                        elif compilation.error_log:
                            compilation.status = CompileStatus.COMPILATION_ERRORS
                        else:
                            compilation.status = CompileStatus.COMPILATION_SUCCESS
                    except Exception as me:
                        compilation.error_log.append('Failure to extract metadata: ' + str(me))
                        compilation.status = CompileStatus.METADATA_PARSE_FAIL
                else:
                    compilation.status = CompileStatus.METADATA_FAIL
                    compilation.error_log.append('No metadata file. Are you sure you used iacrcc?')
            else: # not cic, so check references from bibtex and .aux.
                res = check_bibtex(output_path, compilation)
        # This is a legacy to attempt to fix issue #12. I gave up and
        # made it dependent on the value in the database, but we still
        # store the compilation.json file.
        # We do not use pathlib functions here in order to use
        # os.fsync to flush data from this write all the way
        # through the OS buffers. Otherwise the other thread
        # may not see the output from this file. As it turns out,
        # it still isn't seen so we switched to the database.
        jfile = open(str(json_file.resolve()), 'w', encoding='UTF-8')
        jfile.write(compilation.json(indent=2, exclude_none=True))
        jfile.flush()
        os.fsync(jfile.fileno())
        jfile.close()
    except Exception as e:
        compilation.error_log.append('exception someplace: ' + str(e))
    # Update the database record with the compilation and status.
    comprec.result = compilation.json(indent=2, exclude_none=True)
    comprec.task_status = TaskStatus.FINISHED.value
    db.session.commit()
    task_queue.pop(task_key, None)
    return output.get('errors', [])

