"""Curating orcid list."""

import datetime
from collections import defaultdict
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
    llll = 10_000

    dd: defaultdict[str, list[tuple[int, str]]] = defaultdict(list)

    with PATH.open() as f:
        _ = next(f)
        lineno = 1
        for line in f:
            if lineno > llll:
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
                _, _, res = key.partition(" in ")
                dd[res.casefold()].append((int(count), key))

            # TODO add the else, after initial curation for all of this is done

    x: dict[str, list[tuple[int, str]]] = {
        k: sorted(v, reverse=True, key=lambda t: _sort(t[1])) for k, v in dd.items()
    }
    today = datetime.date.today().isoformat()
    qualification_prefixes = ["degree in", "graduation in", "graduate in"]
    for k, v in sorted(x.items(), key=lambda pair: sum(count for count, _word in pair[1])):
        click.echo(k)
        for _, z in v:
            if any(
                z.lower().startswith(qualification_prefix)
                for qualification_prefix in qualification_prefixes
            ):
                scope = "oboInOwl:hasRelatedSynonym"
            else:
                scope = "oboInOwl:hasExactSynonym"
            row = ("", "", scope, z, "en", "", "0000-0003-4423-4370", today)
            click.echo("\t".join(row))


def _sort(key: str) -> tuple[str, str]:
    ss = key.split()
    ss[0] = ss[0].rstrip("s").rstrip("'").replace(".", "")
    return " ".join(ss), key


if __name__ == "__main__":
    main()
