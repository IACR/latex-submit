# IACR LaTeX Compiler

This repository contains a web server that receives uploads of zip
files with LaTeX sources for final versions of papers. It is intended
to be used for the IACR Communications on Cryptology using the
`iacrcc.cls` LaTeX class, but others may find the framework useful.
This project has a submodule from IACR/latex in order to import
`iacrcc.cls`. In order to pull this in, use
```
git submodule update --init --recursive
```
This also pulls in `cryptobib` since IACR/latex depends on it.

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

NOTE: The original implementation used celery to maintain a queue of
compilation tasks and execute them. This was deemed to be too
complicated because it required running three servers, namely the web
server, redis, and a celery worker. This has some advantages for
scalability and running as a distributed system, but since we only
process one run of LaTeX at a time, we deemed it unnecessary. If this
is adapted to a higher-throughput environment, then celery is probably a
good choice.

The actual compilation is carried out in a docker container that is
started for each paper upload. Using a docker container provides some
degree of security against malicious uploaded LaTeX code.  The web
server keeps a queue of tasks and executes them one by one with a
`ThreadPoolExecutor`.  When an author uploads their paper, they are
shown their position in the queue. The user's browser waits until the
task is finished, and displays the results to the user. If the user tries to
upload another version of their paper before the first one is finished, it
is rejected until compilation of the first upload is completed.

When the author uploads their zipfile, they also include several
items:
* a unique paper ID that encodes the ID of the paper in the reviewing system.
* an email address of the submitting author.
* the original submission date prior to review
* the acceptance date.
These fields will be authenticated with an HMAC in the URL.
For a paper ID of `xyz`, the server will store data for
this upload in the directory `webapp/data/xyz`. The server first
stores the zip file there along with some metadata in a file
`webapp/data/xyz/compilation.json`. It then unzips the zip file into
`webapp/data/xyz/input`. After it runs LaTeX on the files, the output
goes into webapp/data/xyz/output`. As the compilation happens, the file
`compilation.json` gets updated accordingly. The data for this file follows
a schema enforced by the file `webapp/metadata/compilation.py`.

When the web server has received the zip file and unzipped it, the web
server submits a compilation to the ThreadPoolExecutor. When the
thread runs, it creates a docker container with a limited version of
texlive along with the `iacrcc.cls` file.  It runs `latexmk` to
compile the paper using `lualatex` plus either `bibtex` or `biber`,
producing either an error log or a successful output.  If the
LaTeX compilation is successful, then there is further processing on the `main.meta`
output file from `iacrcc.cls`. There are various things that can go wrong:
1. the zip file could be incomplete, or the `main.tex` file might be missing.
2. the paper may fail to compile with `lualatex`. This can happen for various reasons,
   including:
   a. a missing style file in our texlive distribution.
   b. missing metadata in the LaTeX file.
   c. a missing font in our texlive distribution.
   d. a flaw in the supplied metadata (e.g., no author with an email,
      or an empty author name).

The author may continue to upload the paper, which will overwrite any
previous versions they submitted. Once they have had their paper pass
the automated process, they are prompted to check the PDF for visual
flaws and check the extracted metadata for accuracy. They then press a
button to submit their paper for review by a copy editor.

Once the author finalizes their submission, the copy editor will need to
approve it. For this they can simply do a cursory check of the PDF and
the metadata (we do not plan to use proofreading). When the editor approves
it, the API will publish the paper, and the metadata can be submitted to
crossref to assign a DOI (TBD).

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
python3 -m pip install flask-mail
python3 -m pip install docker
sudo apt install docker
```
add user to docker group with
```
sudo usermod -aG docker $USER
```
Then you will need to logout and login again.

```
cd webapp/compiler
docker build -t debian-slim-texlive2022 .
```
(note the dot at the end). While you are in that directory, you should try
running `webapp/compiler/runner.py` on some sample input to check that
the docker compiler is working.

## Running the app in dev

In order to start the web server, run:
```
python3 run.py
```

At this point you should be able to point your browser at localhost:5000

## Running the app in production

The web server would ordinarily be started behind apache running mod_wsgi. This requires
a `.wsgi` file, which isn't completed yet.

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


