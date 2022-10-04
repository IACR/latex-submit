"""
This is what runs latexmk in docker. It is called from our web server, but may
also be used from the command line.
"""

import argparse
import json
import os
from pathlib import Path
import random
import shutil
import string
import sys

import docker
from docker.errors import APIError
from docker.types import Mount

_container = None

def run_latex(input_dirname, output_dirname):
    """Run latexmk safely in a docker container.

       args:
           input_dirname: directory where user-uploaded latex sources are. symlinks
               in this directory are ignored but subdirectories are allowed.
           output_dirname:
               path to where resulting output should be deposited.
       returns: A JSON string to indicate failure or success, along with the output
                from running latexmk.
       raises: 
          ValueError if some conditions are not satisfied.
          APIError if there is an error from the docker API.

          """
    input_dir = Path(input_dirname)
    if not input_dir.is_dir():
        raise ValueError('input directory not found: {}'.format(str(input_dir)))
    output_dir = Path(output_dirname)
    if not output_dir.is_dir():
        raise ValueError('output directory {} not found'.format(str(output_dir)))

    main_tex_file = Path(input_dir, 'main.tex')
    if not main_tex_file.is_file():
        raise ValueError('missing main.tex')
    # Create a temporary staging_dir for inputs, and copy inputs to
    # staging_dir.  This directory will be mounted as /data in the
    # docker container.
    tmpdirname = ''.join(random.choice(string.ascii_lowercase+string.ascii_uppercase) for n in range(12))
    staging_dir = Path(os.path.dirname(os.path.abspath(__file__))) / Path(tmpdirname)
    if staging_dir.is_dir():
        raise ValueError('staging directory {} already exists'.format(str(staging_dir)))
    staging_dir.mkdir()
    for entry in input_dir.iterdir():
        shutil.copy(entry, staging_dir, follow_symlinks=False)
    client = docker.from_env()
    try:
        # We mount the staging_dir as /data in the container.
        mount = Mount('/data', str(staging_dir.absolute()), type='bind')
        container = client.containers.run('debian-slim-texlive2022',
                                          detach=True,
                                          mounts=[mount])
        # TODO: figure out how to set a timeout on the run of the container, in order to
        # protect against people running infinite loops in lualatex.
        # TODO: determine whether we should use --safer. There is evidence that this
        # interferes with the fontspec package, which some people may rely upon. Without
        # --safer, there are attacks on the container that are possible using lua.io
        code, output = container.exec_run('latexmk -lualatex="lualatex --safer --nosocket --no-shell-escape" main', workdir='/data')
        for entry in staging_dir.iterdir():
            shutil.copy(entry, output_dir)
        container.kill()
        response = {'log': output.decode(), 'code': code}
        return json.dumps(response, indent=2)
    except APIError as e:
        print(e)
        raise(e)
    finally:
        shutil.rmtree(staging_dir)
        container.stop()
        container.remove()
    if code:
        return 'Compilation failed: ' + output.decode()
    else:
        return 'Compilation success: ' + output.decode()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Run a latex docker compilation')
    argparser.add_argument('--input_dir',
                           default='tests/passing')
    args = argparser.parse_args()
    output_dir = Path('/tmp/output')
    if output_dir.is_dir():
        shutil.rmtree(output_dir)
    output_dir.mkdir()
    print(run_latex(args.input_dir, str(output_dir)))



