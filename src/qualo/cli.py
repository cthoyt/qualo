"""A CLI for QUALO."""

from collections import defaultdict
from operator import attrgetter
from textwrap import dedent

import click
import pandas as pd
import ssslm
from curies import Reference
from curies.vocabulary import charlie
from ssslm import group_literal_mappings, read_literal_mappings
from ssslm.ontology import PREAMBLE, _clean_str, _text_for_turtle
from ssslm.ontology import _get_axiom_str as get_axiom_str
from ssslm.ontology import _write_prefix_map as write_prefix_map

from qualo.api import (
    DISCIPLINE_TERM,
    DOCS_DIR,
    EXPORT_OBO_PATH,
    EXPORT_OFN_PATH,
    EXPORT_TTL_PATH,
    METADATA,
    ORG_TERM,
    URI_PREFIX,
    _restriction,
)
from qualo.data import (
    MAPPINGS_PATH,
    PREFIX,
    SYNONYMS_PATH,
    get_conferrers,
    get_degree_holders,
    get_disciplines,
    get_terms_df,
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
            click.secho("Failed to create OFN artifact from TTL")
            click.echo(str(e))

        try:
            bioontologies.robot.convert(
                EXPORT_TTL_PATH, EXPORT_OBO_PATH, debug=True, merge=False, reason=False
            )
        except Exception as e:
            click.secho("Failed to create OBO artifact from TTL")
            click.echo(str(e))
        else:
            import pyobo
            from pyobo.ssg import make_site

            ont = pyobo.from_obo_path(path=EXPORT_OBO_PATH, prefix=PREFIX, version=None)
            make_site(ont, directory=DOCS_DIR, manifest=True)


if __name__ == "__main__":
    main()
