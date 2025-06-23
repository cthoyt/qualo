"""Import the curated dictionary from :mod:`orcid_downloader`."""

import click
import pandas as pd
import pystow
import ssslm
from orcid_downloader.standardize import REVERSE_REPLACEMENTS
from tabulate import tabulate

from qualo.data import get_grounder

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


def _ground_best(grounder: ssslm.Grounder, text: str) -> str | None:
    best_match = grounder.get_best_match(text)
    if not best_match:
        return None
    return best_match.curie


@click.command()
def main() -> None:
    """Curate new content."""
    grounder = get_grounder()

    n_misses = 0
    n_hits = 0
    for k, synonyms in REVERSE_REPLACEMENTS.items():
        if k in SKIP:
            continue

        term = _ground_best(grounder, k)
        if not term:
            pass
        for s in synonyms:
            matches = grounder.get_matches(s)
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
    rows = [
        (role, count, example, _ground_best(grounder, role))
        for role, count, example in df.head().values
    ]
    click.echo(tabulate(rows, headers=["role", "count", "example", "curie"], tablefmt="github"))


if __name__ == "__main__":
    main()
