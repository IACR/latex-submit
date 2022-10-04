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
RUN tlmgr install latexmk multirow
COPY LatexMk /etc

WORKDIR /data

# This just keeps it running while we run latexmk and copy files off.
ENTRYPOINT ["tail", "-f", "/dev/null"]
