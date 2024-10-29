"""Curating orcid list."""

from pathlib import Path

import click

import qualo

HERE = Path(__file__).parent.resolve()
ROOT = HERE.parent.parent.parent.resolve()
DATA = ROOT.joinpath("data")
PATH = DATA.joinpath("roles_curate_first.tsv")


@click.command()
def main() -> None:
    """Curate by list."""
    seen = set()
    with PATH.open() as f:
        _ = next(f)
        lineno = 1
        for line in f:
            if lineno > 10_000:
                break
            lineno += 1
            key, _, count = line.strip().partition("\t")
            if key.casefold() in seen:
                continue
            seen.add(key.casefold())
            ref = qualo.ground(key)
            if ref is None:
                click.echo(key)


if __name__ == "__main__":
    main()
