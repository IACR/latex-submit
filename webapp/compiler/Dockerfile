FROM debian:stable-slim

ARG DOCFILES=no
ARG SRCFILES=no
ARG SCHEME=medium

RUN apt-get update -q \
    && apt-get install -qy build-essential wget libfontconfig1 \
    && rm -rf /var/lib/apt/lists/*

# Install TexLive
RUN echo "Building with documentation: $DOCFILES" && \
    echo "Building with sources: $SRCFILES" && \
    echo "Building with scheme: $SCHEME"; \
    wget http://mirror.ctan.org/systems/texlive/tlnet/install-tl-unx.tar.gz; \
    mkdir /install-tl-unx; \
    tar -xvf install-tl-unx.tar.gz -C /install-tl-unx --strip-components=1; \
    echo "selected_scheme scheme-$SCHEME" >> /install-tl-unx/texlive.profile && \
    if [ "$DOCFILES" = "no" ]; then echo "tlpdbopt_install_docfiles 0" >> /install-tl-unx/texlive.profile; fi && \
    if [ "$SRCFILES" = "no" ]; then echo "tlpdbopt_install_srcfiles 0" >> /install-tl-unx/texlive.profile; fi && \
    /install-tl-unx/install-tl -profile /install-tl-unx/texlive.profile; \
    rm -r /install-tl-unx; rm install-tl-unx.tar.gz

ENV PATH="/usr/local/texlive/2022/bin/x86_64-linux:${PATH}"

# Install latex packages
RUN tlmgr install latexmk multirow xstring hyperxmp ifmtarg sectsty biblatex lastpage fancyvrb floatrow caption float lineno microtype tocloft sttools relsize import enumitem xargs ieeetran comment pgfplots pgf-blur calculator todonotes adjustbox collectbox standalone currfile gincltex svn-prov filemod
COPY LatexMk /etc

RUN useradd -ms /bin/bash texlive
USER texlive
COPY iacrcc/iacrcc.cls /home/texlive/texmf/tex/latex/iacrcc/iacrcc.cls
COPY iacrcc/iacrcc.bst /home/texlive/texmf/bibtex/bst/iacrcc/iacrcc.bst
COPY iacrcc/CC-by.png /home/texlive/texmf/tex/latex/iacrcc/CC-by.png
WORKDIR /data

# This causes the container to run no more than 500 seconds. This is to protect against
# lua code with an infinite loop, or something stupid like
# \newcommand{\foo}{\foo}\foo which generates an infinite loop.
# A single compilation should not take this long under any circumstances.
ENTRYPOINT ["/bin/bash", "-c", "timeout 500 tail -f /dev/null"]
