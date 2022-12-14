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
# NOTE: minted requires a shell escape, and is not supported.
RUN tlmgr install mwe orcidlink llncs  # TODO: Remove this later
RUN tlmgr install latexmk multirow xstring hyperxmp ifmtarg sectsty biblatex lastpage fancyvrb floatrow caption float lineno microtype tocloft sttools relsize import enumitem xargs ieeetran comment pgfplots pgf-blur calculator todonotes adjustbox collectbox standalone currfile gincltex svn-prov filemod biber tikzscale pbox forloop varwidth bigfoot environ ntheorem breakcites ifoddpage bbm cleveref bbm-macros blindtext tcolorbox pdfcol doublestroke paralist glossaries mfirstuc xfor datatool mdframed zref needspace lipsum placeins thmtools tocbibind mmap qtree pict2e tree-dvips braket qcircuit xypic dashbox was arydshln threeparttable booktabs cases ascmac cancel autonum etextools textpos everypage apptools boxedminipage chngcntr framed hanging ncctools tablefootnote xifthen subfigure tikz-cd appendix diagbox makecell ifsym capt-of bbold esvect totcount supertabular fifo-stack tikzmark fixmath here tabu hyphenat wrapfig changepage cjhebrew luabidi endnotes xurl seqsplit newunicodechar minibox mathabx quantikz lettrine minifp bbding fontawesome5 tabto-ltx xpatch marginnote morefloats silence yfonts tabulary pdfsync csquotes printlen csvsimple kantlipsum babel-greek datetime2 spverbatim subfiles version rotfloat ellipsis calrsfs tkz-euclide imakeidx academicons anyfontsize scalerel titlesec fixme blkarray circuitikz multibib sidecap mathalpha outlines graphbox eqparbox epigraph nextpage gensymb newtx dblfloatfix spath3 stmaryrd
RUN tlmgr install acronym tikz-qtree lkproof layouts totpages tikz-timing pgfopts esint ltablex acro translations breakurl msc picture accsupp accessibility axessibility nag quoting mleftright subdepth tikzpeople stackengine savesym
RUN tlmgr install dashrule transparent numprint moresize tasks shipunov sauerj verbatimbox readarray changes truncate fmtcount contour sourcecodepro sourcesanspro sourceserifpro cjk biblatex-trad biblatex-ext marginfix sidenotes doclicense ccicons
# install some fonts
RUN tlmgr install fandol noto arphic-ttf dutchcal notomath ascii-font eulervm asana-math sfmath svrsymbols cm-unicode libertine inconsolata simpleicons
COPY compiler/LatexMk /etc

RUN useradd -ms /bin/bash texlive
# The :33 is to ensure that texlive has the same numeric GID as the www-data group,
# so it can write to the staging directory.
USER texlive:33
COPY metadata/latex/iacrcc/iacrcc.cls /home/texlive/texmf/tex/latex/iacrcc/iacrcc.cls
COPY metadata/latex/iacrcc/iacrcc.bst /home/texlive/texmf/bibtex/bst/iacrcc/iacrcc.bst
COPY metadata/iacrtrans/CC-by.pdf /home/texlive/texmf/tex/latex/iacrcc/CC-by.pdf
COPY metadata/iacrtrans/iacrtrans.cls /home/texlive/texmf/tex/latex/iacrcc/iacrtrans.cls
COPY metadata/iacrtrans/settings.tosc.tex /home/texlive/texmf/tex/latex/iacrcc/settings.tosc.tex
COPY metadata/iacrtrans/settings.tches.tex /home/texlive/texmf/tex/latex/iacrcc/settings.tches.tex
WORKDIR /data

# This causes the container to run no more than 500 seconds. This is to protect against
# lua code with an infinite loop, or something stupid like
# \newcommand{\foo}{\foo}\foo which generates an infinite loop.
# A single compilation should not take this long under any circumstances.
ENTRYPOINT ["/bin/bash", "-c", "timeout 500 tail -f /dev/null"]
