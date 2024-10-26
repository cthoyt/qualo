"""Generation of qualo."""

from pathlib import Path
from textwrap import dedent
from typing import Mapping, Optional, Union

from curies import Reference
from biosynonyms import parse_synonyms
from biosynonyms.generate_owl import _write_owl_rdf
from biosynonyms.resources import _clean_str

HERE = Path(__file__).parent.resolve()
EXPOR_PATH = HERE.joinpath("qualo_synonyms.ttl")


def _restriction(prop: str, target: str) -> str:
    return f"[ a owl:Restriction ; owl:onProperty {prop} ; owl:someValuesFrom {target} ]"


def get_remote_curie_map(
    path: Union[str, Path], key: str = "label", delimiter: Optional[str] = None
) -> Mapping[Reference, str]:
    """Get a one-to-one data column from a TSV for CURIEs."""
    import pandas as pd

    df = pd.read_csv(path, sep=delimiter or "\t")
    return {Reference.from_curie(curie): value for curie, value in df[["curie", key]].values}


def _main() -> None:
    import pandas as pd

    """
    See:
    - https://docs.google.com/spreadsheets/d/1xW5VcBIjnDHDxVuEEMgdN0-5vnd7g7pKWbpqglx2fb8/edit?gid=0#gid=0
    - https://github.com/cthoyt/orcid_downloader/blob/main/src/orcid_downloader/standardize.py
    """

    metadata = dedent(
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
    qualo_base = (
        "https://docs.google.com/spreadsheets/d/e/2PACX-1vTLjgYCVw6wY8mYMcZJY4KSY5"
        "xyLWYHSaStOUfoonQvsSU_nRyzYiRJ8pYsfF7Zid5jERB08s89bdt0/pub?single=true&output=tsv"
    )
    names_url = f"{qualo_base}&gid=0"
    synonyms_url = f"{qualo_base}&gid=1557592961"

    df = pd.read_csv(names_url, sep="\t")
    df["reference"] = df["curie"].map(Reference.from_curie, na_action="ignore")

    names = dict(df[["reference", "label"]].values)
    parents_1 = dict(df[["reference", "parent_1"]].values)
    parents_2 = dict(df[["reference", "parent_2"]].values)

    synonyms = parse_synonyms(synonyms_url, names=names)

    with open(EXPOR_PATH, "w") as file:
        _write_owl_rdf(
            synonyms,
            file,
            prefix_map={
                "QUALO": "http://purl.obolibrary.org/obo/QUALO_",
                "DISCO": "http://purl.obolibrary.org/obo/DISCO_",
                "PATO": "http://purl.obolibrary.org/obo/PATO_",
                "EDAM": "http://edamontology.org/topic_",
            },
            metadata=metadata,
        )
        for k, v in parents_1.items():
            if not k:
                continue
            if v and pd.notna(v):
                file.write(
                    f'{k.curie} rdfs:subClassOf {v} ; rdfs:label "{_clean_str(names[k])}" .\n'
                )
            if k in parents_2 and pd.notna(parents_2[k]):
                file.write(f"{k.curie} rdfs:subClassOf {parents_2[k]} .\n")

        for k, example_curie, example_label in df[["reference", "example", "example_label"]].values:
            if not example_curie or pd.isna(example_label):
                continue
            # this ORCID profile is evidence for the existence of this degree
            file.write(f"{k.curie} oboInOwl:hasDbXref {example_curie} .\n")
            file.write(
                f'{example_curie} a NCBITaxon:9606; rdfs:label "{_clean_str(example_label)}" .\n'
            )

        for k, wikidata in df[["reference", "wikidata"]].values:
            if not wikidata or pd.isna(wikidata):
                continue
            wikidata = wikidata.removeprefix("https://www.wikidata.org/wiki/")
            file.write(f"{k.curie} skos:exactMatch {wikidata} .\n")

        for k, discipline_curie, discipline_label in df[
            ["reference", "discipline", "discipline_label"]
        ].values:
            if not discipline_curie or pd.isna(discipline_curie):
                continue
            file.write(
                f'{k.curie} rdfs:subClassOf {_restriction("QUALO:1000002", discipline_curie)} .\n'
            )
            file.write(
                f'{discipline_curie} a owl:Class; rdfs:label "{_clean_str(discipline_label)}" .\n'
            )


if __name__ == "__main__":
    _main()

    # import bioontologies.robot
    # bioontologies.robot.convert(TTL_PATH, OWL_PATH)
