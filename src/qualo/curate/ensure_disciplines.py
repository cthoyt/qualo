"""Ensure the discipline hierarchy.

Go through the disciplines.tsv file and make sure there's a child class of
academic degree by discipline for it.
"""

import click

from qualo.data import DISCIPLINES_PATH, PREFIX, TERMS_PATH, get_disciplines, get_highest, get_names


@click.command()
def main() -> None:
    """Ensure discipline hierarchy."""
    current = get_highest() + 1
    names = get_names()
    disciplines = set(get_disciplines().values())
    with TERMS_PATH.open("a") as file, DISCIPLINES_PATH.open("a") as dfile:
        for discipline in sorted(disciplines):
            xx = f"degree in {discipline.name}"
            if xx not in names.values():
                new_curie = f"{PREFIX}:{current:07}"
                new_name = f"degree in {discipline.name}"
                rows = (
                    new_curie,
                    new_name,
                    f"{PREFIX}:0000021",
                    "academic degree by discipline",
                )
                print(*rows, sep="\t", file=file)
                drow = (
                    new_curie,
                    new_name,
                    discipline.curie,
                    discipline.name,
                )
                print(*drow, sep="\t", file=dfile)
                current += 1


if __name__ == "__main__":
    main()
