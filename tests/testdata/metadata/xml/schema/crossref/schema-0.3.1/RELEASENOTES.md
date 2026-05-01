# 0.3.0 Tagged Crossref bundle

2021-09-28

Current versions:

* common5.3.0.xsd (breaking change)
* crossref5.3.0.xsd (breaking change)
* crossref4.8.0.xsd (non-breaking change)
* common4.8.0.xsd (non-breaking change)
* doi_resources4.4.2.xsd
* AccessIndicators.xsd
* clinicaltrials.xsd
* fundref.xsd
* grant_id.0.1.1.xsd
* relations.xsd

New in this release:
* relations.xsd updated to include finances / isFinancedBy relationship

# 0.2.0 Tagged Crossref bundle

2021-07-21

Current versions:

* common5.3.0.xsd (breaking change)
* crossref5.3.0.xsd (breaking change)
* crossref4.8.0.xsd (non-breaking change)
* common4.8.0.xsd (non-breaking change)
* doi_resources4.4.2.xsd
* AccessIndicators.xsd
* clinicaltrials.xsd
* fundref.xsd
* grant_id.0.1.1.xsd
* relations.xsd

JATS schema include:

JATS-journalpublishing1-3d2-elements.xsd JATS-journalpublishing1-mathml3-3d2-elements.xsd JATS-journalpublishing1-mathml3.xsd JATS-journalpublishing1.xsd

New in this release:

* crossref5.3.0.xsd
* common5.3.0xsd
* crossref4.8.0.xsd
* common4.8.0.xsd
* grant_id.0.1.1.xsd


Added to 4.8.0:

* refactoring of schema
* relax regex rules for email addresses
* allow ISBN beginning with 979
* update imported JATS schema to v. 1.3

Added to 5.3.0
Support for ROR and other organization identifiers:
- replace <affiliation> tag  with <affilations>  to support new affiliations structure
- add  <institution_id> element to support ROR and other org IDs
- make either <institution_id> or <institution_name> required within <institution>

Added to grant v. 0.1.1
- remove investigators requirement
- fix regex for <funder-id>
- add required 'version' attribute to <doi_batch>

# 0.1.1 Tagged Crossref bundle
2019-08-07
Current versions:

- AccessIndicators.xsd
- clinicaltrials.xsd
- common4.4.2.xsd
- crossref4.4.2.xsd
- doi_resources4.4.2.xsd
- fundref.xsd
- grant_id.0.0.1.xsd
- relations.xsd

JATS schema include:
- JATS-journalpublishing1-elements.xsd
- JATS-journalpublishing1-mathml3-elements.xsd
- JATS-journalpublishing1-mathml3.xsd
- JATS-journalpublishing1.xsd

New in this release:

- common4.4.2.xsd
- crossref4.4.2.xsd
- doi_resources4.4.2.xsd
- grant_id.0.0.1.xsd

Released deposit schema v. 4.4.2 updated with JATS files, first version of Grant ID schema
Added to 4.4.2:

- support for Pending Publication
- support for DUL
- support for JATS 1.2 abstracts
- add abstract support to dissertations, reports, and allow multiple abstracts wherever available
- add support for multiple dissertation authors
- add acceptance_date element to journal article, books, book chapter, conference paper

# 0.1.0 First tagged Crossref bundle

2019-06-28

Current versions:

 - AccessIndicators.xsd
 - clinicaltrials.xsd
 - common4.4.2.xsd
 - crossref4.4.2.xsd
 - doi_resources4.4.2.xsd
 - fundref.xsd
 - grant_id.0.0.1.xsd
 - relations.xsd

New in this release:

 - common4.4.2.xsd
 - crossref4.4.2.xsd
 - doi_resources4.4.2.xsd
 - grant_id.0.0.1.xsd

Released deposit schema v. 4.4.2 and added first version of Grant IDs.
Added to 4.4.2:
- support for Pending Publication
- support for DUL
- support for JATS 1.2 abstracts
- add abstract support to dissertations, reports, and allow multiple abstracts wherever available
- add support for multiple dissertation authors
- add acceptance_date element to journal article, books, book chapter, conference paper
