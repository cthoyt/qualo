"""Access to ontology data."""

import datetime
from collections.abc import Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any

import gilda
import pandas as pd
from biosynonyms import Synonym, parse_synonyms
from biosynonyms.resources import _gilda_term
from curies import NamedReference

HERE = Path(__file__).parent.resolve()
TERMS_PATH = HERE.joinpath("terms.tsv")
SYNONYMS_PATH = HERE.joinpath("synonyms.tsv")
SYNONYMS_COLUMNS = ["curie", "label", "scope", "text", "language", "type", "contributor", "date"]
MAPPINGS_PATH = HERE.joinpath("mappings.sssom.tsv")
EXAMPLES_PATH = HERE.joinpath("holders.tsv")
CONFERRERS_PATH = HERE.joinpath("conferrers.tsv")
DISCIPLINES_PATH = HERE.joinpath("disciplines.tsv")

PREFIX = "QUALO"
REPOSITORY = "https://github.com/cthoyt/qualo"
NAME_LOWER = "qualo"
TODAY = datetime.date.today()


def get_terms_df(**kwargs: Any) -> pd.DataFrame:
    """Get the terms dataframe."""
    return pd.read_csv(TERMS_PATH, sep="\t", **kwargs)


@lru_cache
def get_names() -> dict[NamedReference, str]:
    """Get all names."""
    df = get_terms_df()
    df = df[df["curie"].str.startswith(f"{PREFIX}:")]
    df["curie"] = [
        NamedReference.from_curie(curie, name) for curie, name in df[["curie", "label"]].values
    ]
    return dict(df[["curie", "label"]].values)


def get_highest() -> int:
    """Get the highest existing ID."""
    df = get_terms_df(usecols=[0])
    pp = f"{PREFIX}:"
    return max(int(value.removeprefix(pp)) for value in df["curie"])


@lru_cache
def get_gilda_grounder() -> "gilda.Grounder":
    """Get a Gilda grounder."""
    return gilda.Grounder(get_gilda_terms())


def get_synonyms(names: dict[NamedReference, str] | None = None) -> list[Synonym]:
    """Get all synonyms."""
    if names is None:
        names = get_names()
    return parse_synonyms(SYNONYMS_PATH, names=names)  # type:ignore[arg-type]


def get_gilda_terms() -> list[gilda.Term]:
    """Get gilda objects for terms in the ontology."""
    names = get_names()
    rv: list[gilda.Term] = []
    rv.extend(s.as_gilda_term() for s in get_synonyms(names=names))
    rv.extend(
        _gilda_term(text=name, reference=reference, source=PREFIX, status="name")
        for reference, name in names.items()
        if reference.prefix == PREFIX
    )
    return rv


def lint_table(
    path: Path,
    *,
    key: str | list[str],
    duplicate_subsets: str | Sequence[str] | None = None,
    casefold: str | None = None,
    sep: str | None = "\t",
) -> None:
    """Lint a table."""
    df = pd.read_csv(path, sep=sep)
    df = df.sort_values(key)
    if casefold:
        df[f"{casefold}_cf"] = df[casefold].map(str.casefold)
    if duplicate_subsets is not None:
        duplicate_subsets = [f"{x}_cf" if x == casefold else x for x in duplicate_subsets]
        df = df.drop_duplicates(duplicate_subsets)
    if casefold:
        del df[f"{casefold}_cf"]
    df.to_csv(path, index=False, sep=sep)


def lint_synonyms() -> None:
    """Lint the synonyms table."""
    lint_table(
        SYNONYMS_PATH,
        key=["curie", "text", "language"],
        duplicate_subsets=["curie", "text", "type", "language"],
        casefold="text",
    )


def add_synonym(synonym: Synonym) -> None:
    """Add a synonym."""
    with SYNONYMS_PATH.open("a") as file:
        columns = (
            synonym.reference.curie,
            synonym.name,
            synonym.scope.curie,
            synonym.text,
            synonym.language,
            synonym.type.curie if synonym.type else "",
            synonym.contributor.curie if synonym.contributor else "",
            (synonym.date if synonym.date else TODAY).strftime("%Y-%m-%d"),
        )
        print(*columns, sep="\t", file=file)


def get_disciplines() -> dict[NamedReference, NamedReference]:
    """Get the disciplines dictionary."""
    disciplines_df = pd.read_csv(DISCIPLINES_PATH, sep="\t")
    for column_id, column_label in [("curie", "label"), ("discipline", "discipline_label")]:
        disciplines_df[column_id] = [
            NamedReference.from_curie(curie, label)
            for curie, label in disciplines_df[[column_id, column_label]].values
        ]
    disciplines = dict(disciplines_df[["curie", "discipline"]].values)
    return disciplines


def append_term(
    name: str, parent: NamedReference, parent_2: NamedReference | None = None
) -> NamedReference:
    """Append a term to the terms list."""
    current = get_highest() + 1
    new = NamedReference(prefix=PREFIX, identifier=f"{current:07}", name=name)
    row: tuple[str, ...] = new.curie, new.name, parent.curie, parent.name
    if parent_2:
        row = (*row, parent_2.curie, parent_2.name)
    with TERMS_PATH.open("a") as file:
        print(*row, sep="\t", file=file)
    return new


def add_discipline(degree: NamedReference, discipline: NamedReference) -> None:
    """Add a discipline to the list."""
    if degree.prefix != PREFIX:
        raise ValueError
    with DISCIPLINES_PATH.open("a") as file:
        print(degree.curie, degree.name, discipline.curie, discipline.name, sep="\t", file=file)
