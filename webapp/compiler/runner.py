"""
This is what runs latexmk in docker. It is called from our web server, but may
also be used from the command line.
"""

import argparse
import os
from pathlib import Path
import tempfile
import shutil
import sys

import docker
from docker.errors import APIError
from docker.types import Mount

def run_latex(input_dirname, output_tarfile_name, staging_directory='webapp/compiler/staging'):
    """Run latexmk safely in a docker container.

       args:
           input_dirname: directory where user-uploaded latex sources are. symlinks
               in this directory are ignored but subdirectories are allowed.
           output_tarfile_name:
               path to where resulting tarball should be deposited.
           staging_directory:
               path to where input files are placed. This is mounted by docker
               under /data. The default is for use by webapp.
       returns: A string to indicate failure or success, along with the output
                from running latexmk. TODO: make this json?
       raises: 
          ValueError if some conditions are not satisfied.
          APIError if there is an error from the docker API.

          """
    input_dir = Path(input_dirname)
    if not input_dir.is_dir():
        raise ValueError('directory not found: {}'.format(str(input_dir)))
    main_tex_file = Path(input_dir, 'main.tex')
    if not main_tex_file.is_file():
        raise ValueError('missing main.tex')
    staging_dir = Path(staging_directory)
    if not staging_dir.is_dir():
        raise ValueError('missing staging directory')
    staging_has_files = any(staging_dir.iterdir())
    if staging_has_files:
        raise ValueError('staging directory must be empty')
    latexmk_config = Path(staging_dir) / Path('latexmkrc')
    latexmk_config.write_text('$pdf_mode = 4;')
    for entry in input_dir.iterdir():
        shutil.copy(entry, staging_dir, follow_symlinks=False)
    client = docker.from_env()
    output = ''
    try:
        # We mount the staging_dir as /data in the container.
        mount = Mount('/data', str(staging_dir.absolute()), type='bind')
        container = client.containers.run('debian-slim-texlive2022',
                                          detach=True,
                                          mounts=[mount])
        code, output = container.exec_run('latexmk -lualatex="lualatex -safer" main', workdir='/data')
        localtarfile = open(output_tarfile_name, 'wb')
        tarball,stat = container.get_archive('data/')
        for chunk in tarball:
            localtarfile.write(chunk)
        localtarfile.close()
        container.kill()
    except APIError as e:
        print(e)
        raise(e)
    finally:
        container.stop()
        container.remove()
        for entry in staging_dir.iterdir():
            entry.unlink()
    if code:
        return 'Compilation failed: ' + output.decode()
    else:
        return 'Compilation success: ' + output.decode()


if __name__ == '__main__':
    argparser = argparse.ArgumentParser(description='Run a latex docker compilation')
    argparser.add_argument('--input_dir',
                           default='tests/passing')
    argparser.add_argument('--output_tarfile',
                           default = '/tmp/passing.tar')
    argparser.add_argument('--staging_directory',
                           default = 'staging')
    args = argparser.parse_args()
    print(run_latex(args.input_dir, args.output_tarfile, args.staging_directory))



