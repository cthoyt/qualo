from pathlib import Path

import click
import pandas as pd


@click.command()
def main() -> None:
    """Lint files."""
    from qualo.build import (
        CONFERRERS_PATH,
        DISCIPLINES_PATH,
        EXAMPLES_PATH,
        MAPPINGS_PATH,
        SYNONYMS_PATH,
        TERMS_PATH,
    )

    lint_table(TERMS_PATH, key="curie")
    lint_table(SYNONYMS_PATH, key=["curie", 'text', 'language'])
    lint_table(DISCIPLINES_PATH, key=["curie", 'discipline'])
    lint_table(MAPPINGS_PATH, key=["subject_id", 'object_id'])
    lint_table(EXAMPLES_PATH, key=["curie", 'person_curie'])
    lint_table(CONFERRERS_PATH, key=["curie", 'conferrer_curie'])


def lint_table(path: Path, *, key: str | list[str], sep='\t') -> None:
    """Lint a table."""
    df = pd.read_csv(path, sep=sep)
    df = df.sort_values(key)
    df.to_csv(path, index=False, sep=sep)


if __name__ == '__main__':
    main()
