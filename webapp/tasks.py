"""This defines the tasks to be run in executor.
"""
import json
from pathlib import Path
import time
from .compiler import runner
from . import task_queue

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
        output['execution_time'] = end_time - start_time
    except Exception as e:
        output['error'] = 'Exception running latex: ' + str(e)
    json_file = Path(output_path).parents[0] / Path('meta.json')
    try:
        if json_file.is_file():
            jstr = json_file.read_text(encoding='UTF-8')
            data = json.loads(jstr)
            data['execution_time'] = output.get('execution_time', -1)
            data['log'] = output.get('log', 'no log')
            data['code'] = output.get('code', -1)
            json_file.write_text(json.dumps(data, indent=2), encoding='UTF-8')
        else:
            output['error'] = 'Missing json file.'
    except Exception as e:
        output['error'] = 'Exception saving output: ' + str(e)
    task_queue.pop(paperid, None)
    return json.dumps(output, indent=2)

