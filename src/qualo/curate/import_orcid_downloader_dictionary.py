"""Import the curated dictionary from :mod:`orcid_downloader`."""

from typing import cast

import click
import pandas as pd
import pystow
from gilda import Grounder
from orcid_downloader.standardize import REVERSE_REPLACEMENTS

from qualo.data import get_gilda_grounder

PATH = pystow.join(
    "orcid", "2023", "output", "roles", name="education_role_unstandardized_summary.tsv"
)

SKIP = {
    "Adjunct Professor",
    "Assistant Lecturer",
    "Assistant Professor",
    "Associate Professor",
    "Department Head",
    "Diploma",  # FIXME add
    "Docent",
    "Engineer",
    "Graduate Student",  # FIXME add
    "Habilitation",  # FIXME add
    "Intern",
    "Lawyer",
    "Lecturer",
    "Medical Resident",
    "Nurse",
    "Physiotherapist",
    "Postdoctoral Researcher",
    "Professor",
    "Psychologist",
    "Research Assistant",
    "Research Associate",
    "Researcher",
    "Software Developer",
    "Specialist",
    "Student",
    "Teaching Assistant",
    "Trainee",
}


def _ground_best(grounder: Grounder, text: str) -> str | None:
    x = grounder.ground_best(text)
    if not x:
        return None
    return cast(str, x.term.get_curie())


@click.command()
def main() -> None:
    """Curate new content."""
    grounder = get_gilda_grounder()

    n_misses = 0
    n_hits = 0
    for k, synonyms in REVERSE_REPLACEMENTS.items():
        if k in SKIP:
            continue
        term = _ground_best(grounder, k)
        if not term:
            pass
        for s in synonyms:
            matches = grounder.ground(s)
            if not matches:
                n_misses += 1
            elif len(matches) > 1:
                click.echo(f"Multiple matches for {k} - {s}")
                n_misses += 1
            else:
                n_hits += 1

    total = n_hits + n_misses
    click.echo(f"Remaining curation: {n_misses}/{total}")

    # This is for finding new parts
    df = pd.read_csv(PATH, sep="\t")
    for role, count, example in df.head().values:
        click.echo("\t".join((role, count, example, grounder.ground_best(role))))


if __name__ == "__main__":
    main()
