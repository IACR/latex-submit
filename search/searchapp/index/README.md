# Funding and affiliation search

This provides an index over `Funder` objects that are defined in
`model.py`. A `Funder` is a generalization of the organizations in the
'Fundref registry' and the 'ROR registry'.  A `Funder` has a source of
where it come from in these two registries.  [As of
2023-9](https://www.crossref.org/blog/open-funder-registry-to-transition-into-research-organization-registry-ror/),
there is a plan to merge these under ROR. A ROR `Funder` may have a
`preferred_fundref` which points to a `Funder` from Fundref. In this
case the Fundref `Funder` is deemed to be superceded by the correspond
ROR `Funder`. Some Fundref `Funder`s may not correspond to a ROR
`Funder`, so they also get indexed.

`Funder` objects have several kind of relationships:
* parent organization(s)
* child organization(s)
* related organizations
* successor (currently unused)
* predecessor (currently unused)

## Indexing strategy

Because ROR is superceding Fundref, we only index an agency from
Fundref if it is not mentioned in a ROR as `preferred_fundref`. We
first parse the ROR set, and save the `preferred_fundref` values.
Then we pass the Fundref set and ignore those we have already seen as
a ROR that referenced them.
