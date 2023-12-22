# ROR and Fundreg search

This directory contains an independent flask app that is
configured under apache to run under /funding. We do this because
this part depends on the `xapian` library, which is distributed
under the GPL license. By isolating these servers from each
other, we are able to distribute the main webapp under a different
license.
