# IACR LaTeX Publishing Workflow

This repository contains a web server to support the workflow of
submission of final papers for a journal (the IACR Communications
in Cryptology). The system may prove useful for other journals in
computer science and mathematics.

## Publishing workflows

A publishing workflow consists of several steps, which may
include:

1. writing by the author(s)
2. submission for review
3. a review process
4. feedback to authors
5. possible revision; acceptance or rejection.
6. submission of final version by the author
7. copy editing, with feedback to authors
8. revision by author or copy editor to fix errors.
9. production of final version
10. registration of metadata and DOI assignment.
11. hosting for publication.

We exclude from discussion certain other steps such as marketing, cost
recovery, access control, and distribution through print or electronic
push technologies. Our focus is on open access publishing, so these are
less important to us.

### Monolithic vs Component Architecture

A system that implements all of the steps in a publishing workflow is
necessarily quite complex, because there are multiple paths between
authors, editors, reviewers, copy editors, and production
editors. People have designed systems for some parts of the workflow,
including overleaf for authoring, HotCRP and openreview.net for
reviewing, and various web-based systems for hosting a journal. Others
like [OJS](https://pkp.sfu.ca/software/ojs/) have taken the monolithic
approach to develop a system to encompass the entire workflow. Unfortunately
a monolithic approach has several drawbacks, and we chose to tackle
a smaller part of the problem.

A journal publishing workflow can be separated into three major components:

1. Reviewing (steps 1-5 above).
2. Production and copy editing (steps 6-10).
3. Hosting and publication (step 11).

Systems like HotCRP and openreview.net implement the first phase
(openreview can also be used for the third phase). By contrast, the
goal of our system is to implement the second phase. We expect to
combine our system with HotCRP for the first phase. The third phase
should be fairly easy once we export the necessary metadata
about publications.

In order to break the publishing workflow into a set of components, we
need to define the interaction between them. The output from the
reviewing process consists of manuscripts that need to be curated for
publishing and readership. As such, we only need to provide an
interface in the reviewing phase for authors of accepted papers to
upload their "final" versions to the production and copy editing
process. This consists of a URL with embedded authentication that is
constructed with a shared key between the reviewing phase and the
production phase.

Our system is based on the assumption that authors use LaTeX; and
moreover that authors use a specific LaTeX document class that
facilitates metadata capture. More about this can be found in the
[iacrcc document class](https://github.com/IACR/latex) and also in [a
separate paper](https://arxiv.org/abs/2301.08277) describing the
solution.  The system can be extended to cover other LaTeX classes,
but then the capture of metadata needs to be done in the reviewing
phase and communicated to this system via a separate API. We may build
that in the future, but for now we didn't want to modify any specific
reviewing systems.

The capture of metadata is designed to eliminate as much human labor
as possible. It is essentially impossible to completely automate copy
editing, which is mentioned in a separate section below.

The output from the production and copy editing phase consists of a
set of article documents with associated metadata. Articles may be
grouped into issues, or articles may be emitted individually. The
metadata may be used for indexing and browsing in the hosting phase.
In the production and copy editing phase, each paper is assigned a DOI
and the hosting phase must agree to provide access to the article at
the URL pointed to by the DOI. The term "document" is a little vague;
for now we assume that authors write in LaTeX for eventual production
of a PDF document.

### Drawbacks of monolithic systems

By viewing a publishing workflow as these three phases, it allows us
to concentrate on building systems incrementally rather than
monolithically. By contrast, the OJS system is a monolithic systems
that bundles all three phases into a single one. This makes it easy
for a journal to run a single system, but it also constrains the
publication process to fit within the assumptions made by OJS.  We
found multiple places where OJS did not fulfill our needs in all three
phases of publishing. For example, we wanted to start a journal that
used a completely different reviewing system (HotCRP) in which papers
are submitted at periodic deadlines, and reviewing is done by a
committee on a schedule that results in a new set of accepted papers
on a schedule. Others may choose to change to an open reviewing system
like openreview.net. We wanted the flexibility to replace part of the
publishing workflow.

As a monolithic system, OJS has an underlying schema for metadata that
needs to support all three phases of publishing. Schema changes are
notoriously difficult to change in software systems, because a schema
change can touch many different parts of the code. Moreover, metadata
is increasingly important to academic publishing, and OJS has been
slow to adopt things like multiple affiliations, authors with multiple
countries, matching to different taxonomies, extraction of
bibligraphic references, different document formats, etc.

Another reason why we rejected OJS is due to the fact that it's
inconvenient to customize the hosting system. If for example the journal
wanted to provide different views on their content (e.g., by topic or
by a hierarchical taxonomy), it would be difficult to build this into
OJS. Support for mathematics is quite limited in OJS. There is no
support for hosting both HTML and PDF versions of articles. Perhaps
most importantly to us, there is no support for LaTeX in the copy
editing and production phases.

From a software standpoint, OJS is written in the fairly archaic
programming language of PHP with Smarty templates. Front-end web
development is increasingly moving toward javascript frontends with
REST backends, and fewer people are learning PHP as a result. From
a long-term maintenance and evolution standpoint, a monolithic
system built in PHP looks less desirable.

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

### Details about the flow

When the author uploads their zipfile, they also include several
items:
* a unique paper ID that encodes the ID of the paper in the reviewing system.
* an email address of the submitting author.
* the original submission date prior to review
* the acceptance date.

When the submission server forwards the author to at GET at /submit,
the fields will be included as URL parameters, and include an HMAC To
authenticate the payload. For paper ID of `xyz`, the server will store
data for this upload in the directory `webapp/data/xyz`.  For this
reason, the `paperid` must be "directory-safe" using only characters
[-.a-z0-9]. The `paperid` is assumed to be globally unique and is
assigned by the workflow prior to it being received by this server
(e.g., by hotcrp). For IACR this would generally be something like
`tosc_2023_1_15` if it had been assigned paper #15 in a hotcrp version
called `tosc_2023_1`, but the volume and issue number will not be
derived from this.

We don't store every version that is uploaded, but we store
potentially three versions:
1. the "candidate" version from the author. This can be replaced by the author
   up until the time that they mark it as ready for copy editing.
2. the "copyedit" version of the paper. This is created once the author decides
   that they are satisfied with the "candidate" version. It is
   essentially the same as the "candidate" version except it contains
   line numbers.
3. the "final" version of the paper. This is uploaded by the author in
   response to copy edit instructions. It may be replaced by the author up
   until the time that it is finalized by the copy editor.

These directory structure for these versions is:
```
webapp/data/<paperid>/status.json
webapp/data/<paperid>/candidate/all.zip
webapp/data/<paperid>/candidate/input
webapp/data/<paperid>/candidate/output
webapp/data/<paperid>/candidate/compilation.json
webapp/data/<paperid>/copyedit/input
webapp/data/<paperid>/copyedit/output
webapp/data/<paperid>/copyedit/compilation.json
webapp/data/<paperid>/final/all.zip
webapp/data/<paperid>/final/input
webapp/data/<paperid>/final/output
webapp/data/<paperid>/final/compilation.json
```

The `compilation.json` files are serializations of the `Compilation`
object in `webapp/metadata/compilation.py`.  The server keeps a
database to track the flow of papers through the workflow. This
database is currently based on sqlite and is accessed via
SQLAlchemy. In the event that this database needs to grow in the
future, SQLAlchemy makes it easy to migrate to mariadb or postgres.

The workflow transitions between `candidate`, `copyedit`, and `final` are
shown in the figure below.

![workflow](Workflow_transitions.svg).

The `candidate` version is created at the very beginning when the
author uploads their zip file. As soon as the `candidate` version is
flagged as acceptable to the author, then it may no longer be
edited. The `copyedit` version is created when the copy editor is
assigned. This is derived from the `candidate` version by only adding
page numbers. The copy editor reviews the paper and creates a list of
discussion items to the author for them to correct.  The `final`
version is created when the author uploads their response to the copy
editor.

After one round of copy editing, we hope that the `final` version
fulfills all of the required changes from the copy editor, but if they
find new problems or if the author hasn't corrected serious problems,
then the copy editing process starts anew.  In this case, the
`candidate` version is replaced by the `final` version and the
`copyedit` version is recompiled from the new `candidate` version. The
`final` version is removed and all existing discussion items are
archived because they no longer have line numbers and page numbers
that reference the `candidate` version.

It's possible that the new `final` version is actually worse than the
original `candidate` version, but the original `candidate` version is
lost at this point. If the copy editor wishes to avoid this, then they
should communicate to the author via email and have them upload a
different `final` version instead of cycling the `final` version to
replace the `candidate` version.

As it stands now, the copy editor can only send messages to the author
to change their file - the copy editor does not directly edit the
LaTeX.  If the copy editor submits further items to the author, then
they can continue to upload a `final` version until the copy editor is
satisfied.  Once they are satisfied, the `final` version is frozen and
used to produce the published paper.

### Data model and database schema

A relational database is used to store relational data about journals, volumes,
issues, papers, versions, compilations, discussion, users, and log events.
There are various ways to understand the schema:
1. through the SQLAlchemy specification in the `webapp/metadata/db_models.py`
file. This is complicated by the fact that SQLAlchemy went through a major breaking
change in version 2.0, so many tools no longer work.
2. through the mysql schema for tables that are generated.
3. through a visual representation

From a high level point of view, there are journals, which contain
volumes, which contain issues, which contain papers. The main class
for a paper is the `PaperStatus`, which stores the most recent
information related to the paper. A paper may have different versions
(`candidate`, `copyedit`, or `final`), and for each version we store
information about the latest compilation of that version in the
`CompileRecord`. Thus for each paper there may be multiple
`CompileRecords` so we can compare what the author submitted
originally (the `candidate`) vs what the copy editor saw (the
`copyedit` version`) vs what the author uploaded after seeing their
copy editor feedback (the `final` version).

A visualization of the schema in sqlite can be created with
```
eralchemy -i 'sqlite:///db.sqlite' -o db_erd.dot
```
followed by post-processing on the dot file. Another view is provided
by mysql Workbench below.

![workflow](schema.svg).

This makes the hierarchy obvious:
```
Journal -> Volume -> Issue -> PaperStatus
```
A `PaperStatus` can have multiple `CompileRecord`, `LogEvent`, and `Discussion`
objects associated with them. The `result` field in `CompileRecord` is
the JSON serialization of the `Compilation` object.

### `db_models.py`
A journal, volume, or issue is defined by a record in `db_models.py`.
When a hotcrp instance is created, it has journal, volume, and issue
identifiers that later show up in this server. Specifically the information
is matched as follows:
* journal (identified by hotcrp_key)
* volume (identified by name)
* issue (identified by name)

The information for a paper is stored permanently in the `PaperStatus`
record, and a paper is initially linked to an issue.  The paper may
later be moved to another issue, but this is done by changing the
`issue_id` in `PaperStatus`. A paper may be "unassigned" by setting
the `issue_id` to null. If a paper is assigned to an issue, then the
paper must be recompiled because the `main.iacrmetadata` file will
have to be changed to inject the volume and issue number back into the
PDF.

You can change the name or acronym of a journal or volume or issue,
but the `hotcrp_key` should remain fixed to identify which hotcrp
instance it came from.

### Usage for conferences
This system is designed for journals, but computer science typically
uses a conference model of publication. That can be mapped into the data
model of this system in various ways, such as:
1. journal: ACM KDD
2. volume: year
3. issue: track (e.g., industry track vs research track vs invited talks).

This is a clumsy mapping, but at least it breaks things down in a
hierarchy.  For conferences that don't have multiple tracks, they
might have only a single issue. For conferences that occur multiple
times per year, they might have one volume per conference rather than
one volume per year. Alternatively, they could use year and use issue
to represent each individual conference. The mapping needs to be
selected in a way that best represents the hierarchy.

Alternatively, we could use this hierarchy:
1. journal: LNCS
2. volume: TCC
3. issue: year

The mapping is arbitrary, but keep in mind that a journal needs an
EISSN.  All LNCS volumes have the same EISSN of 1611-3349. Another
contraint is that administrative or copy editor access control must be
decided at the level of a journal or volume or issue (this is TBD).

### Authentication

#### Authors

When the author is referred to /submit, there
will be URL paramters that are authenticated with an hmac using a key
shared between the review system and this server. Thereafer the user
is supplied with URLs of the form
```
/view/<paperid>/<version>/<auth>
/view/<paperid>/<version>/<auth>/main.pdf
```
where `auth` is another hmac created by the server to obfuscate the URLs.
An author is free to share these URLs with other authors so that we do
not require authors to login on the site. This may change in the future,
because there is now authentication on the site to restrict access to
the `/admin` section of the site.

Authors do not typically receive accounts on the system - they supply an email
address and receive notifications to that address. Views of their results
are authenticated in HMACS that are embedded into the URLs.

#### Admin and copy editor authentication

Administrators and copy editors receive accounts on the system and have
to login with a username/password. The access control is yet TBD, and for
the moment there is just one class of user.

### The compilation process

When either the `candidate` or `final` version is created, the server
stores the zip file in the appropriate directory, and unzips it into
the `input` subdirectory. The server runs LaTeX on it, producing the
content in the `output` subdirectory.

A compilation is done by submitting a task to the
ThreadPoolExecutor. When the thread runs, it creates a docker
container with a limited version of texlive along with the
`iacrcc.cls` file.  It runs `latexmk` to compile the paper using
`lualatex` plus either `bibtex` or `biber`, producing either an error
log or a successful output.  If the LaTeX compilation is successful,
then there is further processing on the `main.meta` output file from
`iacrcc.cls`. There are various things that can go wrong: 1. the zip
file could be incomplete, or the `main.tex` file might be missing.
2. the paper may fail to compile with `lualatex`. This can happen for
various reasons, including: a. a missing style file in our texlive
distribution.  b. missing metadata in the LaTeX file.  c. a missing
font in our texlive distribution.  d. a flaw in the supplied metadata
(e.g., no author with an email, or an empty author name).

LaTeX environements can vary quite a bit, and this can complicate the
submitting author's ability to submit suitably well formed LaTeX.  The
controlled environment we use is based on texlive, but we allow access
to only a limited number of packages. Because of this, it is important
to provide detailed error messages to the submitting authors so that
they may understand how to fix their problems.

## Installation

Installation is as follows (TODO: review this):

```
python3 -m pip install flask
python3 -m pip install flask-mail
python3 -m pip install flask-login
python3 -m pip install sqlalchemy
python3 -m pip install flask-WTF
python3 -m pip install docker
python3 -m pip install arxiv-latex-cleaner
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

The web server would ordinarily be started behind apache running
mod_wsgi. This requires a `.wsgi` file, which isn't checked in
here. Your environment may vary to run it (e.g., with another wsgi
server behind nginx).

## Copy editing

The step for copy editing is purely a human process, which makes it
the most costly part of the process of publishing. There is room for
argument on how much effort should be put into copy editing. Obviously
many manuscripts would benefit greatly from careful copy editing,
particularly for manuscripts written by an author whose native
language is not English. Unfortunately, because of the human cost of
editing, we restrict the activity to a very narrow set of corrections.
Specifically, we have adopted a stripped-down process derived from the
[AMS editorial-light
guidelines](https://docplayer.net/122465-Mathematics-into-type.html)
in the book "Mathematics into Type" by Ellen Swanson. The primary goal of
this is to "do no harm" to the science embodied in the paper. Even small things
like spell correction run the risk of introducing factual errors.

The end result of an extremely light copy-editing process is that some
manuscripts will end up being poorly written. We have taken the
decision that this should reflect back on the authors themselves. ACM
has taken a similar stance, but [partners with the International
Science Editing service
(ISE)](https://www.acm.org/publications/authors/submissions) to
provide language editing services for authors. The cost of these
editing services is borne by the authors.

## Publishing an issue

The current model of the journal has that the unit of publication is
an "issue" consisting of a sequence of papers that have been reviewed
in hotcrp.  At some point in the future we may move to a continuous model
in which papers are published individually, and the notion of an
"issue" goes away.

A hotcrp instance is intended to supply the papers for an issue, but papers may
theoretically arise from other sources:
1. an invited paper may bypass hotcrp.
2. a paper may be held over from a previous hotcrp if the author does not meet the
   deadline for publishing.

The `PaperStatus` table has a reference to the issue for a paper, but
that can be changed in the admin interface. When a paper is reassigned to a new
issue, it must be recompiled to make sure that the PDF contains the correct
issue number.

Papers are assigned a `paperno` within the issue that indicates their
order within the issue. This will influence the order in which the
papers appear in the table of contents, and may also provide the
final URL for the paper. Prior to publishing the issue, the papers can
be re-ordered in the administrative interface. Once the issue is published,
the `paperno` is fixed and may not be changed because it becomes part
of the archived contents.

When an issue is published, it takes all of the papers in the issue
and sets their status to `PaperStatusEnum.PUBLISHED`, exports them to
the journal site, and sets the `published` date on the issue. If a
paper is submitted to this issue after the issue has been published,
then the paper is automatically unassigned.

There is some doubt about whether the papers in an issue have a prescribed
order. For now we assume that the editor decides this as the issue is
published, and a paper therefore gets a paper number starting with 1
for that issue.

## Export to the journal site

The act of publishing an issue must push the data to the site that
hosts the journal. This server may or may not run on the same machine
as the public-facing journal site where papers are hosted. In order to
maintain this separation, we define an export format from this server
that can be read by the journal site.

### Archiving

There is yet another constraint on the export of published articles,
namely that it should fulfill the need for archiving. The CLOCKSS
system is organized around an AU (Archival Unit) and in our case that
corresponds to an issue. It would be nice to make our export format
consistent with the format required by
[CLOCKSS](https://lockss.github.io/clockss-file-transfer-guidelines.htmlhttps://lockss.github.io/clockss-file-transfer-guidelines.html)
but unfortunately that format is rather vague. The format that we use
is at least consistent with their requirements.

### Export for cic.iacr.org

The format that we use for export to cic.iacr.org is our own design. There are dependencies
in the [github for cic](https://github.com/IACR/cicjournal).

1. each issue consists of a zip file.
2. within the zip file, there is a file called `issue.json` that contains volume number,
   export date, issue number, year, hotcrp shortName, and an optional description field for
   the issue (e.g., "Special Issue on Information Theory"). It also contains the paper
   numbers to indicate the order of papers in the issue.
3. For each paper there is a subdirectory for that paper named by the `paperno`.
4. within the subdirectory for a paper, there are four items:
    - `meta.json` with article metadata that is a stripped-down version of `Compilation`.
    - `main.pdf`
    - `jats.xmp` with metadata in JATS format.
    - `main.zip` with all LaTeX sources.

This omits some information from publish.iacr.org such as the copyedit information.

### Export and import for OJS

There are potentially three ways to do this:
1. have this server export in a native format. OJS has a native import/export plugin, but it
   is poorly documented and the schema changes from one version to another. For example,
   you cannot export from OJS 3.2 and import into 3.3. The OJS team has advised against
   using this as an import method.
2. We could write a different import plugin, but I am unable to locate any template that is
   usable for writing an import template and it would have the same schema problem across different
   versions of OJS as their database schema changes.  The "quickSubmit" plugin might come closest,
   since it provides a form for each new submission.
3. The OJS team [recommended][appears](https://github.com/pkp/pkp-lib/issues/7898)
   using their REST API to import data into OJS. This is weakly
   documented and changes from one version of OJS to another. Since the papers don't start
   out in OJS, we would have to create completely new submissions and publications that
   would bypass the review process.

It's not clear if ToSC or TCHES would use any of these.

#### The native import/export plugin.

At first glance, it appears that if the journal site is OJS then we should probably use
their native import XML format, which has a schema that changes with every release
[native.xsd](https://github.com/pkp/ojs/blob/main/plugins/importexport/native/native.xsd)
that in turn depends upon another
[pkp-native.xsd](https://github.com/pkp/pkp-lib/blob/main/plugins/importexport/native/pkp-native.xsd)
These schemas are lacking in several ways, including the fact that they
don't support ROR for affiliations.  I tried exporting an issue from
an OJS instance, and got a file that was something like the one below
(some fields omitted).
```
<?xml version="1.0"?>
<issue xmlns="http://pkp.sfu.ca"
       xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
       published="1"
       current="1"
       access_status="1"
       url_path=""
       xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
  <id type="internal" advice="ignore">2</id>
  <issue_identification>
    <volume>1</volume>
    <number>2</number>
    <year>2024</year>
    <title locale="en">This is optional</title>
  </issue_identification>
  <date_published>2024-04-01</date_published> <!== optional ==>
  <date_modified>2024-04-01</date_modified>   <!== optional ==>
  <articles xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance"
            xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
    <article xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" locale="en" date_submitted="2023-11-06" status="3" submission_progress="" current_publication_id="3" stage="production">
      <id type="internal" advice="ignore">3</id>
      <submission_file xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="15" created_at="2023-11-06" date_created="" file_id="7" stage="final" updated_at="2023-11-06" viewable="false" genre="Source Texts" source_submission_file_id="14" uploader="fester" xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
        <name locale="en">164.zip</name>
        <file id="7" filesize="322938" extension="zip">
          <embed encoding="base64">base64 content goes here</embed>
        </file>
      </submission_file>
      <submission_file xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" id="16" created_at="2023-11-06" date_created="" file_id="6" stage="final" updated_at="2023-11-06" viewable="false" genre="Article Text" source_submission_file_id="13" uploader="fester" xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
        <name locale="en">main.pdf</name>
        <file id="6" filesize="266578" extension="pdf">
          <embed encoding="base64">base64 content goes here</embed>
        </file>
      </submission_file>
      <publication xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" version="1" status="3" primary_contact_id="6" url_path="" seq="2" access_status="0" date_published="2023-11-06" section_ref="ART" xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
        <id type="internal" advice="ignore">3</id>
        <title locale="en">This is my paper title</title>
        <abstract locale="en">&lt;p&gt;I was too lazy to write an abstract. Note that this is HTML.&lt;/p&gt;</abstract>
        <copyrightHolder locale="en">Author(s)</copyrightHolder>
        <copyrightYear>2023</copyrightYear>
        <authors xmlns:xsi="http://www.w3.org/2001/XMLSchema-instance" xsi:schemaLocation="http://pkp.sfu.ca native.xsd">
          <author include_in_browse="true" user_group_ref="Author" seq="0" id="6">
            <givenname locale="en">Fester</givenname>
            <familyname locale="en">Bestertester</familyname>
            <affiliation locale="en">Digicrime</affiliation>
            <country>US</country>
            <email>author1@digicrime.com</email>
          </author>
          <author include_in_browse="true" user_group_ref="Author" seq="0" id="7">
            <givenname locale="en">Kevin</givenname>
            <familyname locale="en">McCurley</familyname>
            <affiliation locale="en">San Jose State University</affiliation>
            <country>US</country>
            <email>author3@digicrime.com</email>
            <orcid>https://orcid.org/0000-0001-7890-5430</orcid>
            <biography locale="en">&lt;p&gt;Kevin is retired.&lt;/p&gt;</biography>
          </author>
        </authors>
      </publication>
    </article>
  </articles>
</issue>
```
The specifics are described in the schemas (sort of). Note that
others have reported that the import/export plugin sometimes just fails. This makes it
fragile to try this route, so it's currently not implemented. If ToSC and TCHES adopt
this route then it will require coordination with whoever runs the RUB OJS site.

