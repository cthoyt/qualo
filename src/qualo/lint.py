"""Lint files."""

import click


@click.command()
def main() -> None:
    """Lint files."""
    from qualo.data import (
        CONFERRERS_PATH,
        DEGREE_HOLDER_PATH,
        DISCIPLINES_PATH,
        MAPPINGS_PATH,
        TERMS_PATH,
        lint_synonyms,
        lint_table,
    )

    lint_table(TERMS_PATH, key="curie")
    lint_synonyms()
    lint_table(
        DISCIPLINES_PATH, key=["curie", "discipline"], duplicate_subsets=["curie", "discipline"]
    )
    lint_table(MAPPINGS_PATH, key=["subject_id", "object_id"])
    lint_table(DEGREE_HOLDER_PATH, key=["curie", "person_curie"])
    lint_table(CONFERRERS_PATH, key=["curie", "conferrer_curie"])


if __name__ == "__main__":
    main()
