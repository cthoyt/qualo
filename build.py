"""Generation of qualo."""

from collections import defaultdict
from operator import attrgetter
from pathlib import Path
from textwrap import dedent
from typing import Mapping, Optional, Union

from curies import Reference
from biosynonyms import parse_synonyms, group_synonyms
from biosynonyms.generate_owl import (
    get_axiom_str,
    PREAMBLE,
    write_prefix_map,
    _get_prefixes as _get_synonym_prefixes,
)
from biosynonyms.resources import _clean_str
import pandas as pd

HERE = Path(__file__).parent.resolve()
EXPORT_DIR = HERE.joinpath("export")
EXPORT_DIR.mkdir(exist_ok=True)
EXPORT_PATH = EXPORT_DIR.joinpath("qualo.ttl")

DATA_DIR = HERE.joinpath("data")
TERMS_PATH = DATA_DIR.joinpath("terms.tsv")
SYNONYMS_PATH = DATA_DIR.joinpath("synonyms.tsv")
MAPPINGS_PATH = DATA_DIR.joinpath("mappings.sssom.tsv")
EXAMPLES_PATH = DATA_DIR.joinpath("examples.tsv")


def _restriction(prop: str, target: str) -> str:
    return (
        f"[ a owl:Restriction ; owl:onProperty {prop} ; owl:someValuesFrom {target} ]"
    )


def get_remote_curie_map(
    path: Union[str, Path], key: str = "label", delimiter: Optional[str] = None
) -> Mapping[Reference, str]:
    """Get a one-to-one data column from a TSV for CURIEs."""
    df = pd.read_csv(path, sep=delimiter or "\t")
    return {
        Reference.from_curie(curie): value for curie, value in df[["curie", key]].values
    }


METADATA = dedent(
    """\
<https://purl.obolibrary.org/obo/qualo.owl> a owl:Ontology ;
    dcterms:title "Qualification Ontology" ;
    dcterms:description "An ontology representation qualifications, such as academic degrees" ;
    dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    rdfs:comment "Built by https://github.com/biopragmatics/biosynonyms"^^xsd:string ;
    dcterms:contributor orcid:0000-0003-4423-4370 .

PATO:0000001 rdfs:label "quality" .

DISCO:0000001 a owl:Class ; rdfs:label "academic discipline" .

QUALO:1000001 a owl:AnnotationProperty;
    rdfs:label "example holder"^^xsd:string ;
    rdfs:range NCBITaxon:9606 ;
    rdfs:domain QUALO:0000001 .

QUALO:1000002 a owl:ObjectProperty;
    rdfs:label "for discipline"^^xsd:string ;
    rdfs:range DISCO:0000001 ;
    rdfs:domain QUALO:0000021 .
"""
)


def _main() -> None:
    """
    See:
    - https://docs.google.com/spreadsheets/d/1xW5VcBIjnDHDxVuEEMgdN0-5vnd7g7pKWbpqglx2fb8/edit?gid=0#gid=0
    - https://github.com/cthoyt/orcid_downloader/blob/main/src/orcid_downloader/standardize.py
    """
    df = pd.read_csv(TERMS_PATH, sep="\t")
    for c in ["curie", "parent_1", "parent_2", "discipline"]:
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

    disciplines = dict(df[df["discipline"].notna()][["curie", "discipline"]].values)

    prefix_map = {
        "QUALO": "http://purl.obolibrary.org/obo/QUALO_",
        "DISCO": "http://purl.obolibrary.org/obo/DISCO_",
        "PATO": "http://purl.obolibrary.org/obo/PATO_",
        "EDAM": "http://edamontology.org/topic_",
        "wikidata": "http://wikidata.org/entity/",
    }

    prefixes: set[str] = set()
    # TODO get prefixes from other places
    prefixes.update(_get_synonym_prefixes(synonym_index))

    mappings_df = pd.read_csv(MAPPINGS_PATH, sep='\t')
    for c in ['predicate_id', 'object_id', 'contributor']:
        mappings_df[c] = mappings_df[c].map(Reference.from_curie, na_action="ignore")

    mdfg = {
        Reference.from_curie(k): sdf
        for k, sdf in mappings_df.groupby('subject_id')
    }

    with open(EXPORT_PATH, "w") as file:
        write_prefix_map(prefixes, file, prefix_map=prefix_map)
        file.write("\n")
        file.write(METADATA)
        file.write(PREAMBLE)

        for k, label in df[["curie", "label"]].values:
            file.write(f'\n{k.curie} a owl:Class; rdfs:label "{_clean_str(label)}" .\n')
            for example in examples.get(k, []):
                file.write(f"{k.curie} oboInOwl:hasDbXref {example.curie} .\n")
            if parents := all_parents.get(k, []):
                x = ", ".join(
                    parent.curie for parent in sorted(parents, key=attrgetter("curie"))
                )
                file.write(f"{k.curie} rdfs:subClassOf {x} .\n")
            if discipline := disciplines.get(k):
                file.write(
                    f'{k.curie} rdfs:subClassOf {_restriction("QUALO:1000002", discipline.curie)} .\n'
                )
            for synonym in synonym_index.get(k, []):
                file.write(
                    f"{k.curie} {synonym.scope.curie} {synonym.text_for_turtle} . \n"
                )
                if axiom := get_axiom_str(k, synonym):
                    file.write(axiom)

            if (sdf:=mdfg.get(k)) is not None:
                for p, o, c,d in sdf[['predicate_id', 'object_id', 'contributor', 'date']].values:
                    file.write(f"{k.curie} {p.curie} {o.curie} .\n")
                    file.write(dedent(f"""\
                    [
                        a owl:Axiom ;
                        owl:annotatedSource {k.curie} ;
                        owl:annotatedProperty {p.curie} ;
                        owl:annotatedTarget {o.curie} ;
                        dcterms:contributor {c.curie} ;
                        dcterms:date "{d}"^^xsd:date .
                    ] .
                    """))

if __name__ == "__main__":
    _main()

    # import bioontologies.robot
    # bioontologies.robot.convert(TTL_PATH, OWL_PATH)
