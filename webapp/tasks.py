"""This defines the tasks to be run in executor.
"""
import json
from pathlib import Path
import time
from .compiler import runner
from . import task_queue
#from .metadata import meta_parse
from .metadata.latex.iacrcc.parser import meta_parse
from .metadata.compilation import Compilation, Meta, CompileStatus, VersionEnum

def run_latex_task(input_path, output_path, paperid):
    """Execute latex on input_path contents, writing into output_path.
    args:
       input_path: absolute string path to input directory
       output_path: absolute string path to output directory
       paperid: string paperid
    returns:
       dict that contains 'error' if something goes wrong, and
       'log', 'code', 'execution_time' if the compilation finishes.
       A finished compilation may still contain errors if code!=0.
    """
    output = {}
    try:
        start_time = time.time()
        output = runner.run_latex(input_path, output_path)
        end_time = time.time()
        output['execution_time'] = round(end_time - start_time, 2)
    except Exception as e:
        output['error'] = 'Exception running latex: ' + str(e)
    try:
        json_file = Path(output_path).parents[0] / Path('compilation.json')
        if json_file.is_file():
            compilation = Compilation.parse_raw(json_file.read_text(encoding='UTF-8'))
            compilation.compile_time = output.get('execution_time', -1)
            compilation.log = output.get('log', 'no log')
            latexlog = Path(output_path) / 'main.log'
            for warning in output.get('warnings', []):
                compilation.warning_log.append(warning)
            if latexlog.is_file():
                latexlog = latexlog.read_text(encoding='UTF-8')
                # Flag some warnings and errors from the log. We may want to process the log
                # line by line, since LaTeX is miserable at the try ... catch paradigm.
                if 'LaTeX Warning: There were undefined references' in latexlog:
                    compilation.error_log.append('LaTeX Warning: There were undefined references')
                    compilation.status = CompileStatus.COMPILATION_ERRORS
                if 'Specify a country for each affiliation for the final version' in latexlog:
                    compilation.error_log.append('At least one affiliation is missing a country')
                    compilation.status = CompileStatus.COMPILATION_ERRORS
                if 'LaTeX Warning: There were multiply-defined labels.' in latexlog:
                    compilation.error_log.append('There were multiply-defined labels.')
                    compilation.status = CompileStatus.COMPILATION_ERRORS
                if 'Unable to redefine math accent' in latexlog:
                    compilation.warning_log.append('You may have lost a math character. Search for "redefine math accent"')
                # TODO: check severity before declaring it an error
                if 'Overfull \\hbox ' in latexlog:
                    compilation.warning_log.append('You have an overfull hbox. Please correct it.')
                if 'Overfull \\vbox ' in latexlog:
                    compilation.warning_log.append('You have an overfull vbox. Please correct it.')
            if 'error' in output:
                compilation.error_log.append(output.get('error'))
                compilation.status = CompileStatus.COMPILATION_FAILED
            compilation.exit_code = output.get('exit_code', -1)
            if compilation.exit_code != 0:
                compilation.status = CompileStatus.COMPILATION_FAILED
                compilation.error_log.append('Exit code of {} means that the compilation failed'.format(compilation.exit_code))
            elif compilation.venue.value != 'iacrcc':
                compilation.status = CompileStatus.COMPILATION_SUCCESS
            if compilation.status != CompileStatus.COMPILATION_FAILED and compilation.venue.value == 'iacrcc':
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
                            data['abstract'] = abstract_file.read_text(encoding='UTF-8')
                            compilation.meta = Meta(**data)
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
                    compilation.error_log.append('No metadata file')
            json_file.write_text(compilation.json(indent=2, exclude_none=True), encoding='UTF-8')
        else:
            output['error'] = 'Missing json file.'
    except Exception as e:
        output['error'] = 'Exception saving output: ' + str(e)
    if 'error' in output:
        print('ERROR:' + output['error'])
    task_queue.pop(paperid, None)
    return json.dumps(output, indent=2)

