"""Generation of the ontology."""

import datetime
from collections import defaultdict
from operator import attrgetter
from textwrap import dedent

import click
import pandas as pd
import regex
import ssslm
from curies import NamableReference, NamedReference, Reference
from curies.vocabulary import charlie, has_exact_synonym
from ssslm import group_literal_mappings, read_literal_mappings
from ssslm.ontology import PREAMBLE, _clean_str, _text_for_turtle
from ssslm.ontology import _get_axiom_str as get_axiom_str
from ssslm.ontology import _write_prefix_map as write_prefix_map

from qualo.constants import ROOT
from qualo.data import (
    MAPPINGS_PATH,
    PREFIX,
    REPOSITORY,
    SYNONYMS_PATH,
    add_discipline,
    add_synonym,
    append_term,
    get_conferrers,
    get_degree_holders,
    get_disciplines,
    get_grounder,
    get_names,
    get_terms_df,
)
from qualo.prefixes import (
    BACHELOR_OF_ARTS_PREFIXES,
    BACHELOR_OF_SCIENCE_PREFIXES,
    BACHELOR_PREFIXES,
    MASTER_PREFIXES,
    MSC_PREFIXES,
    PHD_PREFIXES,
)

__all__ = [
    "get_name",
    "ground",
]

URI_PREFIX = f"https://w3id.org/{PREFIX.lower()}/"

EXPORT_DIR = ROOT.joinpath("export")
EXPORT_DIR.mkdir(exist_ok=True)
EXPORT_TTL_PATH = EXPORT_DIR.joinpath(PREFIX.lower()).with_suffix(".ttl")
EXPORT_OWL_PATH = EXPORT_DIR.joinpath(PREFIX.lower()).with_suffix(".owl")
EXPORT_OFN_PATH = EXPORT_DIR.joinpath(PREFIX.lower()).with_suffix(".ofn")

ONTOLOGY_IRI = f"https://w3id.org/{PREFIX.lower()}/{PREFIX.lower()}.ttl"
DISCIPLINE_TERM = f"{PREFIX}:9999990"
ORG_TERM = "OBI:0000245"


def _restriction(prop: str, target: str) -> str:
    return f"[ a owl:Restriction ; owl:onProperty {prop} ; owl:someValuesFrom {target} ]"


METADATA = dedent(
    f"""\
<{ONTOLOGY_IRI}> a owl:Ontology ;
    dcterms:title "Qualification Ontology" ;
    dcterms:description "An ontology representation qualifications, such as academic degrees" ;
    dcterms:license <https://creativecommons.org/publicdomain/zero/1.0/> ;
    rdfs:comment "Built by {REPOSITORY}"^^xsd:string ;
    dcterms:creator orcid:0000-0003-4423-4370 .

PATO:0000001 a owl:Class ;
    rdfs:label "quality" .
{ORG_TERM} a owl:Class ;
    rdfs:label "organization"@en .

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
    names = get_names()
    return names[reference]  # type:ignore[index]


def ground(text: str) -> NamableReference | None:
    """Ground a qualification to the CURIE."""
    grounder = get_grounder()
    text = text.replace("’", "'")  # noqa:RUF001
    match = grounder.get_best_match(text)
    if match is None:
        return None
    return match.reference


ACADEMIC_DEGREE = NamedReference(
    prefix=PREFIX, identifier="0000021", name="academic degree by discipline"
)

BACHELOR_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000003", "bachelor's degree")
MASTER_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000004", "master's degree")
BSC_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000024", "bachelor of science")
BA_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000031", "bachelor of arts")
MSC_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000057", "master of science")
PHD_DEGREE = NamedReference.from_curie(f"{PREFIX}:0000016", "doctor of philosophy")


def append_degree_by_discipline(  # noqa:C901
    discipline_term: NamedReference,
    has_bachelor_of_science: bool = False,
    has_ba: bool = False,
    has_msc: bool = False,
    has_phd: bool = False,
) -> NamedReference:
    """Append a new discipline."""
    name_to_reference: dict[str, NamedReference] = {v: k for k, v in get_names().items()}

    discipline_name = discipline_term.name.lower()
    degree_name = f"academic degree in {discipline_name}"
    degree_term = name_to_reference.get(degree_name)
    if degree_term is None:
        degree_term = append_term(degree_name, parent=ACADEMIC_DEGREE)

    add_discipline(degree_term, discipline_term)
    add_synonym(_fast_literal_mapping(degree_term, f"degree in {discipline_name}"))

    bachelor_name = f"bachelor of {discipline_name}"
    bachelor_term = name_to_reference.get(bachelor_name)
    if bachelor_term is None:
        bachelor_term = append_term(bachelor_name, BACHELOR_DEGREE, degree_term)
    for synonym_prefix in BACHELOR_PREFIXES:
        add_synonym(_fast_literal_mapping(bachelor_term, f"{synonym_prefix} {discipline_name}"))

    master_name = f"master of {discipline_name}"
    master_term = name_to_reference.get(master_name)
    if master_term is None:
        master_term = append_term(master_name, MASTER_DEGREE, degree_term)
    for synonym_prefix in MASTER_PREFIXES:
        add_synonym(_fast_literal_mapping(master_term, f"{synonym_prefix} {discipline_name}"))

    if has_bachelor_of_science:
        bs_name = f"bachelor of science in {discipline_name}"
        bs_term = name_to_reference.get(bs_name)
        if bs_term is None:
            bs_term = append_term(bs_name, BSC_DEGREE, bachelor_term)
        for synonym_prefix in BACHELOR_OF_SCIENCE_PREFIXES:
            add_synonym(_fast_literal_mapping(bs_term, f"{synonym_prefix} {discipline_name}"))

    if has_ba:
        ba_name = f"bachelor of arts in {discipline_name}"
        ba_term = name_to_reference.get(ba_name)
        if ba_term is None:
            ba_term = append_term(ba_name, BSC_DEGREE, bachelor_term)
        for synonym_prefix in BACHELOR_OF_ARTS_PREFIXES:
            add_synonym(_fast_literal_mapping(ba_term, f"{synonym_prefix} {discipline_name}"))

    if has_msc:
        msc_name = f"master of science in {discipline_name}"
        msc_term = name_to_reference.get(msc_name)
        if msc_term is None:
            msc_term = append_term(msc_name, MSC_DEGREE, master_term)
        for synonym_prefix in MSC_PREFIXES:
            add_synonym(_fast_literal_mapping(msc_term, f"{synonym_prefix} {discipline_name}"))

    if has_phd:
        phd_name = f"doctor of philosophy in {discipline_name}"
        phd_term = name_to_reference.get(phd_name)
        if phd_term is None:
            phd_term = append_term(phd_name, PHD_DEGREE, degree_term)
        for synonym_prefix in PHD_PREFIXES:
            add_synonym(_fast_literal_mapping(phd_term, f"{synonym_prefix} {discipline_name}"))

    return degree_term


def _fast_literal_mapping(reference: NamedReference, text: str) -> ssslm.LiteralMapping:
    return ssslm.LiteralMapping(
        reference=reference,
        text=text,
        language="en",
        predicate=has_exact_synonym,
        contributor=charlie,
        date=datetime.date.today(),
    )


@click.command()
def main() -> None:  # noqa: C901
    """Build the Turtle ontology artifact.

    .. seealso:: https://github.com/cthoyt/orcid_downloader/blob/main/src/orcid_downloader/standardize.py
    """
    df = get_terms_df()

    for c in ["curie", "parent_1", "parent_2"]:
        df[c] = df[c].map(Reference.from_curie, na_action="ignore")

    names = dict(df[["curie", "label"]].values)

    all_parents: defaultdict[Reference, list[Reference]] = defaultdict(list)
    for child, p1, p2 in df[["curie", "parent_1", "parent_2"]].values:
        if pd.notna(p1):
            all_parents[child].append(p1)
        if pd.notna(p2):
            all_parents[child].append(p2)

    literal_mapping_index = group_literal_mappings(
        read_literal_mappings(SYNONYMS_PATH, names=names)
    )

    degree_holder_examples = get_degree_holders()
    conferrer_examples = get_conferrers()
    disciplines = get_disciplines()

    prefix_map = {
        PREFIX: URI_PREFIX,
        "PATO": "http://purl.obolibrary.org/obo/PATO_",
        "mesh": "http://id.nlm.nih.gov/mesh/",
        "EDAM": "http://edamontology.org/topic_",
        "wikidata": "http://wikidata.org/entity/",
        "ror": "http://ror.org/",
        "OBI": "http://purl.obolibrary.org/obo/OBI_",
    }

    prefixes: set[str] = set()
    # TODO get prefixes from other places
    prefixes.update(ssslm.get_prefixes(literal_mapping_index))

    mappings_df = pd.read_csv(MAPPINGS_PATH, sep="\t")
    for c in ["predicate_id", "object_id", "contributor"]:
        mappings_df[c] = mappings_df[c].map(Reference.from_curie, na_action="ignore")

    mdfg = {Reference.from_curie(k): sdf for k, sdf in mappings_df.groupby("subject_id")}
    mdfg_cols = ["predicate_id", "object_id", "contributor", "date"]

    with open(EXPORT_TTL_PATH, "w") as file:
        write_prefix_map(prefixes, file, prefix_map=prefix_map)
        file.write("\n")
        file.write(METADATA)
        file.write(PREAMBLE)

        for discipline_reference in sorted(set(disciplines.values())):
            file.write(
                f"\n{discipline_reference.curie} a owl:Class; "
                f'rdfs:label "{_clean_str(discipline_reference.name)}"; '
                f"rdfs:subClassOf {DISCIPLINE_TERM} .\n"
            )

        for conferrer in sorted(
            {value for values in conferrer_examples.values() for value in values}
        ):
            file.write(
                f'\n{conferrer.curie} a {ORG_TERM}; rdfs:label "{_clean_str(conferrer.name)}" .\n'
            )

        # TODO add discipline hierarchy

        for k, label in df[["curie", "label"]].values:
            file.write(f'\n{k.curie} a owl:Class; rdfs:label "{_clean_str(label)}" .\n')
            for person in degree_holder_examples.get(k, []):
                # could also simplify to using oboInOwl:hasDbXref
                file.write(f"{k.curie} {PREFIX}:1000001 {person.curie} .\n")
            for conferrer in conferrer_examples.get(k, []):
                file.write(f"{k.curie} {PREFIX}:1000003 {conferrer.curie} .\n")
            if parents := all_parents.get(k, []):
                x = ", ".join(parent.curie for parent in sorted(parents, key=attrgetter("curie")))
                file.write(f"{k.curie} rdfs:subClassOf {x} .\n")
            if discipline := disciplines.get(k):
                rr = _restriction(f"{PREFIX}:1000002", discipline.curie)
                file.write(f"{k.curie} rdfs:subClassOf {rr} .\n")
            for literal_mapping in literal_mapping_index.get(k, []):
                file.write(
                    f"{k.curie} {literal_mapping.predicate.curie} "
                    f"{_text_for_turtle(literal_mapping)} . \n"
                )
                if axiom := get_axiom_str(k, literal_mapping):
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

        file.write(f'\n{charlie.curie} a NCBITaxon:9606; rdfs:label "Charles Tapley Hoyt" .\n')

    try:
        import bioontologies.robot
    except ImportError:
        click.secho("bioontologies is not installed, can't convert to OWL and OFN")
    else:
        try:
            bioontologies.robot.convert(
                EXPORT_TTL_PATH, EXPORT_OFN_PATH, debug=True, merge=False, reason=False
            )
        except Exception as e:
            click.secho("Failed to create OFN")
            click.echo(str(e))


if __name__ == "__main__":
    main()
