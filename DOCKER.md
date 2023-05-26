The process to add new packages is as follows:

1. modify one of the last "RUN tlmgr install" lines to add the package at the end of the line. The docker build uses a cache of everything built up to that point, so modifying the last RUN line will make the build faster.

2. the instructions to build the docker file are in the README.md: 
cd webapp/compiler
docker build -t debian-slim-texlive2022 .
(note the dot at the end to indicate where to look for Dockerfile)
The instructions on publish.iacr.org are slightly different, since the docker image needs to be owned by the www-data user. I preface it with "sudo -u www-data"

3. if the docker image builds, then make sure you modify templates/installed.html and templates/unsupported.html to include the new package. The descriptions are the official instructions from CTAN.

