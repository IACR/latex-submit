"""This defines the tasks to be run in executor.
"""
import json
from pathlib import Path
import time
from .compiler import runner
from . import task_queue
#from .metadata import meta_parse
from .metadata.latex.iacrcc.parser import meta_parse
from .metadata.compilation import Compilation, Meta, StatusEnum, VersionEnum

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
            if 'error' in output:
                compilation.error_log.append(output.get('error'))
                compilation.status = StatusEnum.COMPILATION_FAILED
            compilation.exit_code = output.get('exit_code', -1)
            if compilation.exit_code != 0:
                compilation.status = StatusEnum.COMPILATION_FAILED
                compilation.error_log.append('Error code of {} means that the compilation failed'.format(compilation.exit_code))
            if compilation.status != StatusEnum.COMPILATION_FAILED and compilation.venue.value == 'iacrcc':
                # Look for stuff we need for iacrcc.
                metafile = Path(output_path) / Path('main.meta')
                if metafile.is_file():
                    try:
                        metastr = metafile.read_text(encoding='UTF-8')
                        data = meta_parse.parse_meta(metastr)
                        abstract_file = Path(output_path) / Path('main.abstract')
                        if not abstract_file.is_file():
                            compilation.status = StatusEnum.MISSING_ABSTRACT
                            compilation.error_log.append('An abstract is required.')
                        else:
                            data['abstract'] = abstract_file.read_text(encoding='UTF-8')
                            compilation.meta = Meta(**data)
                            if compilation.meta.version != VersionEnum.FINAL:
                                compilation.status = StatusEnum.WRONG_VERSION
                                compilation.error_log.append('Paper should use documentclass[version=final]')
                            else:
                                compilation.status = StatusEnum.COMPILATION_SUCCESS
                    except Exception as me:
                        compilation.error_log.append('Failure to extract metadata: ' + str(me))
                        compilation.status = StatusEnum.METADATA_PARSE_FAIL
                else:
                    compilation.status = StatusEnum.METADATA_FAIL
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

