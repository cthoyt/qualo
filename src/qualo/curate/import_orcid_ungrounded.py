"""Curating orcid list."""

import datetime
from collections import defaultdict
from pathlib import Path
from typing import Any

import click
import pyobo
import ssslm
from curies import NamedReference, ReferenceTuple

import qualo
from qualo.api import append_degree_by_discipline
from qualo.data import get_disciplines, lint_synonyms
from qualo.prefixes import (
    BACHELOR_OF_ARTS_PREFIXES_CF,
    BACHELOR_OF_SCIENCE_PREFIXES_CF,
    MSC_PREFIXES_CF,
    PHD_PREFIXES_CF,
)

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent.resolve()
DATA = ROOT.joinpath("data")
PATH = DATA.joinpath("roles_curate_first.tsv")

today = datetime.date.today().isoformat()
QUALIFICATION_PREFIXES = [
    "degree in",
    "graduation in",
    "graduate in",
    "graduated in",
    "undergraduate in",
]

SKIP_DISCIPLINES = {
    "science",
    "Science",
    "medicine",
    "Medicine",
    "technology",
    "Technology",
}


def _get_mesh_grounder() -> ssslm.Grounder:
    return pyobo.get_grounder("mesh")


@click.command()
def main(write: bool = False) -> None:  # noqa:C901
    """Curate by list."""
    seen = set()
    #: don't go past this line number, to avoid the long tail.
    maximum_line = 50_000

    dd: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)

    curated_disciplines: set[ReferenceTuple] = {r.pair for r in get_disciplines().values()}

    with PATH.open() as f:
        _ = next(f)
        lineno = 1
        for line in f:
            if lineno > maximum_line:
                break
            lineno += 1
            key, _, count = line.strip().partition("\t")
            if key.casefold() in seen:
                continue
            seen.add(key.casefold())
            ref = qualo.ground(key)
            if ref is not None:
                continue

            if " in " in key:
                _, _, discipline_text = key.partition(" in ")
                dd[discipline_text.casefold()].append((int(count), key))

            # TODO add the else, after initial curation for all of this is done

    disciple_text_to_degrees: dict[str, list[tuple[int, str]]] = {
        discipline: sorted(degrees, reverse=True, key=lambda t: _sort(t[1]))
        for discipline, degrees in dd.items()
    }

    discipline_text_degrees_pairs = sorted(
        disciple_text_to_degrees.items(), key=lambda pair: sum(count for count, _word in pair[1])
    )
    mesh_grounder = _get_mesh_grounder()

    # re-sort by lexicalization
    for discipline_text, degree_texts in sorted(discipline_text_degrees_pairs):
        if discipline_text.casefold() in SKIP_DISCIPLINES:
            continue
        if "engineering" in discipline_text.casefold():
            continue  # need different logic for this

        discipline_scored_match = mesh_grounder.get_best_match(discipline_text)
        if not discipline_scored_match:
            continue
        discipline_term = NamedReference.from_reference(discipline_scored_match.reference)

        if discipline_term.pair in curated_disciplines:
            continue  # not necessary to curate again

        if discipline_term.name is None:
            continue

        if (
            discipline_term.name.casefold() != discipline_text.casefold()
            or " " in discipline_term.name
        ):
            continue  # TODO remove this later. for now, keep it simple - only do simple disciplines

        has_bachelor_of_science = _has(degree_texts, BACHELOR_OF_SCIENCE_PREFIXES_CF)
        has_master_of_science = _has(degree_texts, MSC_PREFIXES_CF)
        has_phd = _has(degree_texts, PHD_PREFIXES_CF)
        has_ba = _has(degree_texts, BACHELOR_OF_ARTS_PREFIXES_CF)
        append_degree_by_discipline(
            discipline_term,
            has_bachelor_of_science=has_bachelor_of_science,
            has_ba=has_ba,
            has_phd=has_phd,
            has_msc=has_master_of_science,
        )

    lint_synonyms()

    if write or True:
        _write(discipline_text_degrees_pairs)


def _write(discipline_text_degrees_pairs: list[tuple[str, list[tuple[Any, str]]]]) -> None:
    for discipline_text, v in discipline_text_degrees_pairs:
        click.echo(discipline_text)
        for _, z in v:
            if any(
                z.lower().startswith(qualification_prefix)
                for qualification_prefix in QUALIFICATION_PREFIXES
            ):
                scope = "oboInOwl:hasRelatedSynonym"
            else:
                scope = "oboInOwl:hasExactSynonym"
            row = ("", "", scope, z, "en", "", "0000-0003-4423-4370", today)
            click.echo("\t".join(row))


def _has(degree_texts: list[tuple[int, str]], prefixes_cf: set[str]) -> bool:
    return any(
        degree_text.casefold().startswith(prefix)
        for _, degree_text in degree_texts
        for prefix in prefixes_cf
    )


def _sort(key: str) -> tuple[str, str]:
    ss = key.split()
    ss[0] = ss[0].rstrip("s").rstrip("'").replace(".", "")
    return " ".join(ss), key


if __name__ == "__main__":
    main()
