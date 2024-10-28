# Qualification Ontology (`QUALO`)

An ontology of qualifications and distinctions that uses the 
[Phenotype And Trait Ontology](https://bioregistry.io/pato)
term [`quality` (PATO:0000001)](https://bioregistry.io/PATO:0000001?provider=ols)
as a root term.

The original motivation for this resource was to standardize education labels in ORCID
(see https://doi.org/10.5281/zenodo.10137939).
Therefore, the first version of this resource focuses on academic qualifications, namely,
degrees conferred by universities. The [Bologna Process](https://en.wikipedia.org/wiki/Bologna_Process)
did a lot of work to standardize academic qualifications, but there is still a wide vocabulary used, some of
which is ambiguous.

Future versions of this resource could include additional qualifications.

## Data

- `synonyms.tsv` follows the [Biosynonyms format](https://github.com/biopragmatics/biosynonyms)
- `mappings.sssom.tsv` follows the [SSSOM format](https://mapping-commons.github.io/sssom/)
- `examples.tsv` has for each discipline one or more example people

## TODO

- add test for duplicate labels
