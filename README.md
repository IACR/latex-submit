# IACR LaTeX Compiler

NOTE: This is just a few fragments, and doesn't actually compile uploaded
code yet. It just compiles some fixed file until we discuss what to store
for an upload and how to authenticate people.

This repository contains a web server that receives uploads of zip
files with LaTeX sources for final versions of papers. It is intended
to be used for the IACR Communications on Cryptology using the
`iacrcc.cls` LaTeX class, but we hope that it can eventually be used
more broadly.

## Architecture

The author is expected to upload a zip file to this server with their
LaTeX sources. Compilation of LaTeX received from third parties
constitutes a security risk. For this reason, the production of PDF or
HTML from LaTeX should either be done by authors or within a
controlled environment. Due to the fact that LaTeX is a programming
environment, we have chosen to provide a controlled environment so as
to enforce a look and feel of the papers by limiting which LaTeX
packages may be used. This is essentially the same approach taken by
ACM and arXiv.

NOTE: The implementation describe below uses celery, but I think this
may be too heavyweight for what we want. All we really need is a queue
of tasks to be performed, but this can be handled with Flask-executor
that wraps a ThreadPoolExecutor. If we set this to have a single
thread, then we could have a single server instead of
flask+celery+redis. The advantage of celery is that you can scale it
up and run it as a distributed service, because the celery workers can
run on other machines. I don't think we really need that since we
don't expect a big workload. Using Flask-executor would simplify our
architecture by requiring only one app, namely the flask web server.

This compiler service consists of three servers, namely a submission
web server written in python/Flask, a Redis server, and a celery
worker that runs the compilations. The actual
compilations are performed in a docker container that is created for
each compilation, and these are run as celery tasks by the celery
worker.  Using a docker container provides some degree of security
against malicious uploaded LaTeX code.  The purpose of the Redis
server is to handle a queue of tasks for the compilation server to
perform, and report back results to the submission web server.  The
glue between the servers is provided by the python Celery framework,
using Redis as the message queue.

When the author uploads their zipfile, they also include a unique
paper ID and the email address of the submitting author. For a paper
ID of `xyz`, For a paper ID of `xyz`, the server will store data for
this upload in the directory `webapp/data/xyz`. The server first
stores the zip file there, and then unzips the zip file into
`webapp/data/xyz/input`. After it runs LaTeX on the files, the output
goes into webapp/data/xyz/output`. The server also stores a file
`webapp/data/xyz/meta.json` with minimal metadata about the upload.

One the web server has received the zip file and unzipped it, the web
server registers a Celery task through Redis for the compilation
server to run. The user's browser waits until the task is finished,
and displays the results to the user.

Once the celery task is registered, the compilation server picks it up
from a queue of tasks. The compilation server creates a docker
container with a limited version of texlive along with the iacrcc.cls
file.  It runs latexmk to run lualatex plus either bibtex or biber,
producing either an error log or a successful output.  If the
compilation is successful, then the output from compliation is
reported back (including the meta file produced from the iacrcc.cls
during the compliation.  If the compilation fails, then a detailed
error log is reported back to Redis, which is picked up by the web
server.

## The compiler process

LaTeX environements can vary quite a bit, and this can complicate the
submitting author's ability to submit suitably well formed LaTeX.  The
controlled environment we use is based on texlive, but we allow access
to only a limited number of packages. Because of this, it is important
to provide detailed error messages to the submitting authors so that
they may understand how to fix their problems.

Installation is as follows (TODO: review this):

```
python3 -m pip install flask
python3 -m pip install flask-limiter
python3 -m pip install flask-mail
python3 -m pip install celery
python3 -m pip install redis
python3 -m pip install docker
sudo apt install redis-server
sudo apt install python3-celery
sudo apt install docker
```
add user to docker group with
```
sudo usermod -aG docker $USER
```
Then you will need to logout and login again.

See instructions for [installing redis](https://www.digitalocean.com/community/tutorials/how-to-install-and-secure-redis-on-ubuntu-20-04).
You only need to set the password for accessing redis by changing the line for
`requirepass` in `/etc/redis/redis.conf`.  The password
is currently in `config.py`. (TODO: where should this be kept?)

```
cd webapp/compiler
docker build -t debian-slim-texlive2022 .
```
(note the dot at the end). While you are in that directory, you should try
```
python3 runner.py
```
to check that the docker compiler is working. This will produce output in /tmp/passing.tar

## Running the app in dev

When Redis is installed, it is normally started and running via
systemd. In order to start the web server, run:
```
python3 run.py
```

Then in another shell, start the celery worker by running:
```
celery -A webapp.tasks worker --loglevel=DEBUG
```
At this point you should be able to point your browser at localhost:5000

## Running the app in production

As stated above, the Redis server will ordinarily be started by systemd after it
is installed (be sure to configure the password as in `config.py`).

The web server would ordinarily be started behind apache running mod_wsgi. This requires
a `.wsgi` file, which isn't completed yet.

In production, the celery worker will have to also be started using
systemd. I have not done this yet, but [see
this](https://ahmadalsajid.medium.com/daemonizing-celery-beat-with-systemd-97f1203e7b32)

## Publishing workflow (not sure if we need this here)

The purpose of this server is to fulfill part of the publishing
workflow for a journal. Once a paper is accepted by a review process,
the authors will be pointed to this server in order to upload their
final versions.  This is but one part of a publishing workflow based
on a LaTeX class that captures metadata about publications.

A publishing workflow consists of several steps, which may
include:

1. writing by the author(s)
2. submission for review
3. a review process
4. feedback to authors
5. possible revision
6. submission of final version
7. copy editing
8. production of final version
9. registration of metadata
10. hosting for publication.

This project is only designed to fulfill steps 6, and 8-10.  One
crucial feature of step 8 is that the `iacrcc` LaTeX class produces
machine-readable metadata as a byproduct of compiling the LaTeX.


