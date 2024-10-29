"""Generation of qualo."""

import subprocess
from collections import defaultdict
from collections.abc import Sequence
from functools import lru_cache
from operator import attrgetter
from pathlib import Path
from textwrap import dedent

import click
import gilda
import pandas as pd
import regex
from biosynonyms import group_synonyms, parse_synonyms
from biosynonyms.generate_owl import (
    PREAMBLE,
    get_axiom_str,
    write_prefix_map,
)
from biosynonyms.generate_owl import (
    _get_prefixes as _get_synonym_prefixes,
)
from biosynonyms.resources import Synonym, _clean_str, _gilda_term
from curies import Reference

__all__ = [
    "get_name",
    "ground",
    "get_gilda_grounder",
    "get_synonyms",
]

PREFIX = "QUALO"
URI_PREFIX = "https://w3id.org/qualo/"

HERE = Path(__file__).parent.resolve()

ROOT = HERE.parent.parent.resolve()
EXPORT_DIR = ROOT.joinpath("export")
EXPORT_DIR.mkdir(exist_ok=True)
EXPORT_PATH = EXPORT_DIR.joinpath("qualo.ttl")
EXPORT_OWL_PATH = EXPORT_DIR.joinpath("qualo.owl")
EXPORT_OFN_PATH = EXPORT_DIR.joinpath("qualo.ofn")

DATA_DIR = HERE.joinpath("data")
TERMS_PATH = DATA_DIR.joinpath("terms.tsv")
SYNONYMS_PATH = DATA_DIR.joinpath("synonyms.tsv")
SYNONYMS_COLUMNS = ["curie", "label", "scope", "text", "language", "type", "contributor", "date"]
MAPPINGS_PATH = DATA_DIR.joinpath("mappings.sssom.tsv")
EXAMPLES_PATH = DATA_DIR.joinpath("holders.tsv")
CONFERRERS_PATH = DATA_DIR.joinpath("conferrers.tsv")
DISCIPLINES_PATH = DATA_DIR.joinpath("disciplines.tsv")

ONTOLOGY_IRI = "https://w3id.org/qualo/qualo.ttl"
DISCIPLINE_TERM = f"{PREFIX}:9999990"


def _restriction(prop: str, target: str) -> str:
    return f"[ a owl:Restriction ; owl:onProperty {prop} ; owl:someValuesFrom {target} ]"


METADATA = dedent(
    f"""\
<{ONTOLOGY_IRI}> a owl:Ontology ;
    dcterms:title "Qualification Ontology" ;
    dcterms:description "An ontology representation qualifications, such as academic degrees" ;
    dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    rdfs:comment "Built by https://github.com/cthoyt/qualo"^^xsd:string ;
    dcterms:creator orcid:0000-0003-4423-4370 .

PATO:0000001 rdfs:label "quality" .

{DISCIPLINE_TERM} a owl:Class ; rdfs:label "academic discipline" .

{PREFIX}:1000001 a owl:AnnotationProperty;
    rdfs:label "example holder"^^xsd:string ;
    rdfs:range NCBITaxon:9606 ;
    rdfs:domain {PREFIX}:0000001 .

{PREFIX}:1000002 a owl:ObjectProperty;
    rdfs:label "for discipline"^^xsd:string ;
    rdfs:range {DISCIPLINE_TERM} ;
    rdfs:domain {PREFIX}:0000001 .

{PREFIX}:1000003 a owl:AnnotationProperty;
    rdfs:label "example conferrer"^^xsd:string ;
    skos:exactMatch wikidata:P1027 ;
    owl:equivalentProperty wikidata:P1027 ;
    rdfs:domain {PREFIX}:0000001 .
"""
)

ID_REGEX = regex.compile(r"^\d{7}$")


def get_name(reference: str | Reference) -> str:
    """Get the qualification name, by CURIE."""
    if isinstance(reference, str):
        if ID_REGEX.match(reference):
            reference = Reference(prefix=PREFIX, identifier=reference)
        else:
            reference = Reference.from_curie(reference)
    if reference.prefix != PREFIX:
        raise ValueError(f"Invalid reference: {reference}")
    return _get_names()[reference]


@lru_cache
def _get_names() -> dict[Reference, str]:
    df = pd.read_csv(TERMS_PATH, sep="\t")
    df = df[df["curie"].str.startswith(f"{PREFIX}:")]
    df["curie"] = df["curie"].map(Reference.from_curie)
    return dict(df[["curie", "label"]].values)


def ground(text: str) -> Reference | None:
    """Ground a qualification to the CURIE."""
    grounder = get_gilda_grounder()
    match = grounder.ground_best(text)
    if match is None:
        return None
    return Reference(prefix=match.term.db, identifier=match.term.id)


@lru_cache
def get_gilda_grounder() -> "gilda.Grounder":
    """Get a Gilda grounder."""
    return gilda.Grounder(_get_terms())


def get_synonyms(names: dict[Reference, str] | None = None) -> list[Synonym]:
    """Get all synonyms."""
    if names is None:
        names = _get_names()
    return parse_synonyms(SYNONYMS_PATH, names=names)


def _get_terms() -> list[gilda.Term]:
    names = _get_names()
    rv: list[gilda.Term] = []
    rv.extend(s.as_gilda_term() for s in get_synonyms(names=names))
    rv.extend(
        _gilda_term(text=name, reference=reference, source=PREFIX, status="name")
        for reference, name in names.items()
        if reference.prefix == PREFIX
    )
    return rv


def lint_table(
    path: Path,
    *,
    key: str | list[str],
    duplicate_subsets: str | Sequence[str] | None = None,
    casefold: str | None = None,
    sep: str | None = "\t",
) -> None:
    """Lint a table."""
    df = pd.read_csv(path, sep=sep)
    df = df.sort_values(key)
    if casefold:
        df[f"{casefold}_cf"] = df[casefold].map(str.casefold)
    if duplicate_subsets is not None:
        duplicate_subsets = [f"{x}_cf" if x == casefold else x for x in duplicate_subsets]
        df = df.drop_duplicates(duplicate_subsets)
    if casefold:
        del df[f"{casefold}_cf"]
    df.to_csv(path, index=False, sep=sep)


def lint_synonyms() -> None:
    lint_table(
        SYNONYMS_PATH,
        key=["curie", "text", "language"],
        duplicate_subsets=["curie", "text", "type", "language"],
        casefold="text",
    )


def add_synonym(synonym: Synonym) -> None:
    with SYNONYMS_PATH.open("a") as file:
        dd = synonym.model_dump()
        print(
            *(dd[key] for key in SYNONYMS_COLUMNS),
            sep="\t",
            file=file,
        )
    lint_synonyms()


@click.command()
def main() -> None:  # noqa: C901
    """Build the Turtle ontology artifact.

    .. seealso:: https://github.com/cthoyt/orcid_downloader/blob/main/src/orcid_downloader/standardize.py
    """
    df = pd.read_csv(TERMS_PATH, sep="\t")

    for c in ["curie", "parent_1", "parent_2"]:
        df[c] = df[c].map(Reference.from_curie, na_action="ignore")

    names = dict(df[["curie", "label"]].values)

    all_parents: defaultdict[Reference, list[Reference]] = defaultdict(list)
    for child, p1, p2 in df[["curie", "parent_1", "parent_2"]].values:
        if pd.notna(p1):
            all_parents[child].append(p1)
        if pd.notna(p2):
            all_parents[child].append(p2)

    synonym_index = group_synonyms(parse_synonyms(SYNONYMS_PATH, names=names))

    examples: defaultdict[Reference, list[Reference]] = defaultdict(list)
    for parent, example in pd.read_csv(EXAMPLES_PATH, sep="\t", usecols=[0, 2]).values:
        examples[Reference.from_curie(parent)].append(Reference.from_curie(example))

    disciplines_df = pd.read_csv(DISCIPLINES_PATH, sep="\t")
    for c in ["curie", "discipline"]:
        disciplines_df[c] = disciplines_df[c].map(Reference.from_curie)
    disciplines = dict(disciplines_df[["curie", "discipline"]].values)

    prefix_map = {
        PREFIX: URI_PREFIX,
        "PATO": "http://purl.obolibrary.org/obo/PATO_",
        "mesh": "http://id.nlm.nih.gov/mesh/",
        "EDAM": "http://edamontology.org/topic_",
        "wikidata": "http://wikidata.org/entity/",
    }

    prefixes: set[str] = set()
    # TODO get prefixes from other places
    prefixes.update(_get_synonym_prefixes(synonym_index))

    mappings_df = pd.read_csv(MAPPINGS_PATH, sep="\t")
    for c in ["predicate_id", "object_id", "contributor"]:
        mappings_df[c] = mappings_df[c].map(Reference.from_curie, na_action="ignore")

    mdfg = {Reference.from_curie(k): sdf for k, sdf in mappings_df.groupby("subject_id")}
    mdfg_cols = ["predicate_id", "object_id", "contributor", "date"]

    with open(EXPORT_PATH, "w") as file:
        write_prefix_map(prefixes, file, prefix_map=prefix_map)
        file.write("\n")
        file.write(METADATA)
        file.write(PREAMBLE)

        for k, label in disciplines_df[["discipline", "discipline_label"]].drop_duplicates().values:
            file.write(
                f"\n{k.curie} a owl:Class; "
                f'rdfs:label "{_clean_str(label)}"; '
                f"rdfs:subClassOf {DISCIPLINE_TERM} .\n"
            )

        for k, label in df[["curie", "label"]].values:
            file.write(f'\n{k.curie} a owl:Class; rdfs:label "{_clean_str(label)}" .\n')
            for example in examples.get(k, []):
                file.write(f"{k.curie} oboInOwl:hasDbXref {example.curie} .\n")
            if parents := all_parents.get(k, []):
                x = ", ".join(parent.curie for parent in sorted(parents, key=attrgetter("curie")))
                file.write(f"{k.curie} rdfs:subClassOf {x} .\n")
            if discipline := disciplines.get(k):
                rr = _restriction(f"{PREFIX}:1000002", discipline.curie)
                file.write(f"{k.curie} rdfs:subClassOf {rr} .\n")
            for synonym in synonym_index.get(k, []):
                file.write(f"{k.curie} {synonym.scope.curie} {synonym.text_for_turtle} . \n")
                if axiom := get_axiom_str(k, synonym):
                    file.write(axiom)

            if (sdf := mdfg.get(k)) is not None:
                for p, o, contributor, d in sdf[mdfg_cols].values:
                    file.write(f"{k.curie} {p.curie} {o.curie} .\n")
                    file.write(
                        dedent(f"""\
                    [
                        a owl:Axiom ;
                        owl:annotatedSource {k.curie} ;
                        owl:annotatedProperty {p.curie} ;
                        owl:annotatedTarget {o.curie} ;
                        dcterms:contributor {contributor.curie} ;
                        dcterms:date "{d}"^^xsd:date .
                    ] .
                    """)
                    )

    try:
        import bioontologies.robot
    except ImportError:
        click.secho("bioontologies is not installed, can't convert to OWL and OFN")
    else:
        try:
            bioontologies.robot.convert(EXPORT_PATH, EXPORT_OWL_PATH)
        except subprocess.CalledProcessError as e:
            click.secho("Failed to create OWL")
            click.echo(str(e))
        try:
            bioontologies.robot.convert(EXPORT_PATH, EXPORT_OFN_PATH)
        except subprocess.CalledProcessError as e:
            click.secho("Failed to create OFN")
            click.echo(str(e))


if __name__ == "__main__":
    main()
