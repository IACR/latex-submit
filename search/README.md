# Search components

This directory contains an independent flask app that is intended
to be run separately from publish.iacr.org in order to provide 
some search functionality. The server only responds with JSON,
but is able to search multiple corpora. These include:
1. search on [cryptobib](https://github.com/cryptobib/)
2. search on the [ROR](https://ror.org/) and
[crossref Open Funder registry](https://www.crossref.org/documentation/funder-registry/accessing-the-funder-registry/)

On publish.iacr.org we run the server on the domain publish.iacr.org
as an different WSGI app that is accessible only via https. This
allows us to keep a separation between the two codebases and thus it
is possible to apply separate licenses to them. The search app in this
directory must be licenses as GPL because the
[xapian](https://xapian.org) library is only released under a GPL
license. The license for the code that runs publish.iacr.org itself is
under the ../webapp directory.  These should not be linked to each
other in order to preserve their license status.


