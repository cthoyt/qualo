"""Access to ontology data."""

import datetime
from collections import defaultdict
from collections.abc import Mapping, Sequence
from functools import lru_cache
from pathlib import Path
from typing import Any, cast

import pandas as pd
import ssslm
from curies import NamedReference, Reference
from curies.vocabulary import has_label

HERE = Path(__file__).parent.resolve()
TERMS_PATH = HERE.joinpath("terms.tsv")
SYNONYMS_PATH = HERE.joinpath("synonyms.tsv")
SYNONYMS_COLUMNS = ["curie", "label", "scope", "text", "language", "type", "contributor", "date"]
MAPPINGS_PATH = HERE.joinpath("mappings.sssom.tsv")
DEGREE_HOLDER_PATH = HERE.joinpath("holders.tsv")
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
def get_names() -> Mapping[NamedReference, str]:
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
def get_grounder() -> "ssslm.Grounder":
    """Get a grounder."""
    return ssslm.make_grounder(get_literal_mappings())


def get_literal_mappings(
    *, names: Mapping[NamedReference, str] | None = None
) -> list[ssslm.LiteralMapping]:
    """Get literal mapping objects for terms in the ontology."""
    if names is None:
        names = get_names()
    rv = ssslm.read_literal_mappings(SYNONYMS_PATH, names=cast(dict[Reference, str], names))
    rv.extend(
        ssslm.LiteralMapping(text=name, reference=reference, source=PREFIX, predicate=has_label)
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
    ssslm.lint_literal_mappings(SYNONYMS_PATH)


def add_synonym(synonym: ssslm.LiteralMapping) -> None:
    """Add a synonym."""
    ssslm.append_literal_mapping(synonym, SYNONYMS_PATH)


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


def get_degree_holders() -> dict[NamedReference, list[NamedReference]]:
    """Get example degree holders."""
    rv: defaultdict[NamedReference, list[NamedReference]] = defaultdict(list)
    df = pd.read_csv(DEGREE_HOLDER_PATH, sep="\t").values
    for degree_curie, degree_name, person_curie, person_name in df:
        rv[NamedReference.from_curie(degree_curie, degree_name)].append(
            NamedReference.from_curie(person_curie, person_name)
        )
    return dict(rv)


def get_conferrers() -> dict[NamedReference, list[NamedReference]]:
    """Get example conferrers."""
    rv: defaultdict[NamedReference, list[NamedReference]] = defaultdict(list)
    df = pd.read_csv(CONFERRERS_PATH, sep="\t").values
    for degree_curie, degree_name, conferrer_curie, conferrer_name, _reference in df:
        rv[NamedReference.from_curie(degree_curie, degree_name)].append(
            NamedReference.from_curie(conferrer_curie, conferrer_name)
        )
    return dict(rv)


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


def add_degree_holder(degree: NamedReference, person: NamedReference) -> None:
    """Add a degree holder example."""
    if degree.prefix != PREFIX:
        raise ValueError
    with DEGREE_HOLDER_PATH.open("a") as file:
        print(degree.curie, degree.name, person.curie, person.name, sep="\t", file=file)
