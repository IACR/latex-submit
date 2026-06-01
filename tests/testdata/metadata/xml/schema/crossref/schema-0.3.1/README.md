# Schema

This repository contains information about Crossref’s metadata deposit schema and supports planning for future versions. Details for most supported versions of the Crossref deposit schema are available in the [Crossref support documentation](https://support.crossref.org/hc/en-us/articles/214169586). Documentation for version 5.3.0 is forthcoming.

## Schema versioning

We have a number of schemas which span our history. Historically some have been versioned and some have not. Where schemas are versioned you will find the version in the file name, e.g. `crossref4.4.1.xsd` and in the corresponding namespace, e.g. `http://www.crossref.org/schema/4.4.1`.

We release the Crossref Schemas bundle as a whole. The release notes for each bundle mentions the latest version of each schema contained in it.

## What's here

### Schemas

The XML schemas are found in the `schemas` directory. All active Crossref schema are included. Crossref schema import a local copy of JATS schema as well as the JATS schema lack a namespace.  The JATS schemas in this repository have been modified to include a namespace.

### Index

The `schemas/index.json` contains the filename of every schema file along with the Target Namespace that it represents.

### Examples

We have a growing collection of example XML files for demonstrating and testing XML submissions. These live in the examples directory (or subdirectories) and are automatically validated. A 'best practice' directory  (best-practice-examples) has been added to demonstrate best practice for Crossref XML creation.

XML examples are registered with our demonstration DOI prefix (10.32013) and belong to our fake publisher, Society of Metadata Idealists.  Please feel free to add your own examples or request examples for specific situations.
