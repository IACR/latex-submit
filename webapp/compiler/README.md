# LaTeX Compiler

This part is mostly standalone, and is used by the web server as a way to compile
uploaded LaTeX code. There is a command line interface for testing.

# Quick start

The steps to make this work are:

1. install docker

2. cd to the webapp directory and execute the command:
```
docker build -t debian-slim-texlive .
```
(note the dot at the end). This will build the docker image from `Dockerfile`
and tag it as `debian-slim-texlive`.

3. for a test run, use `python3 runner.py`.

## The design

The goal here is that we will run this on a machine that receives uploaded files
from the user. The files that the user uploads will be placed into some directory.
For the test above, `run.py` uses the directory `texfiles`, but ordinarily this would
be a directory created by the upload.

A description of what `run.py` does is:
1. check that the input directory contains main.tex.
2. create a temporary directory and copy the user-uploaded files into that directory.
3. start a docker container from the docker image `debian-slim-texlive` This
   container is configured to mount the temporary directory read-write as /data.
4. Execute the command `latexmk` with suitable arguments within the docker container.
5. create a tar file with the output from running `latexmk` within the host machine.
6. stop the container and remove it.

If run from the command line, `run.py` will use texfiles as input and save the tar
file to `/tmp/output.tar`. It does this by calling a function `run_latex` with
default parameters for input and output. When used from the web server, these
will be supplied as arguments derived from the upload.

## LaTeX packages

Neither ACM nor arXiv support all LaTeX packages in texlive-full. There are several reasons
why we might not want to include all of texlive-full:

1. some packages may conflict with iacrcc.cls
2. the docker image would be five times larger
3. some may be unsafe to run on untrusted inputs.
4. some may interfere with future conversion to HTML.

## Running in production

When running this as a wsgi app in production, the user that the app is running after requires
access to docker. If this user is `www-data` as it would be under `mod_wsgi`, the solution is to
execute:
```
sudo usermod -aG docker www-data
```
Then build the container as `www-data` using:
```
sudo -u www-data docker build -t debian-slim-texlive .
```
