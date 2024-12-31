"""This script plots the hierarchy on a given discipine."""

import networkx as nx
import pandas as pd
from curies import NamedReference

from qualo.constants import ROOT
from qualo.data import PREFIX, get_disciplines, get_terms_df


def _parse_named_references(df: pd.DataFrame, curie_col: str, name_col: str) -> None:
    df[curie_col] = [
        NamedReference.from_curie(curie, name) if pd.notna(curie) and pd.notna(name) else None
        for curie, name in df[[curie_col, name_col]].values
    ]
    del df[name_col]


IMG = ROOT.joinpath("docs", "source", "img")
IMG.mkdir(exist_ok=True)
PATH = IMG.joinpath("hierarchy.png")
ROOTS = {
    NamedReference(prefix="PATO", identifier="0000001", name="quality"),
    NamedReference(prefix=PREFIX, identifier="0000001", name="qualification"),
}


def main(discipline: NamedReference | None = None) -> None:
    """Generate a chart for a given discipline."""
    if discipline is None:
        discipline = NamedReference(prefix="mesh", identifier="D011584", name="psychology")

    graph = nx.DiGraph()
    terms_df = get_terms_df()

    _parse_named_references(terms_df, "curie", "label")
    _parse_named_references(terms_df, "parent_1", "parent_1_label")
    _parse_named_references(terms_df, "parent_2", "parent_2_label")

    for curie, parent_1, parent_2 in terms_df.values:
        if pd.notna(parent_1):
            graph.add_edge(curie, parent_1)
        if pd.notna(parent_2):
            graph.add_edge(curie, parent_2)

    for degree, discipline in get_disciplines().items():
        graph.add_edge(degree, discipline)

    ancestors = nx.ancestors(graph, discipline) | {discipline}
    descendants = {
        descendant for ancestor in ancestors for descendant in nx.descendants(graph, ancestor)
    }

    nodes = (ancestors | descendants) - ROOTS

    sg: nx.DiGraph = nx.subgraph(graph, nodes)
    sg = nx.relabel_nodes(sg, {node: f"{node.name}\n{node.curie}" for node in sg})

    ag = nx.nx_agraph.to_agraph(sg)
    ag.draw(PATH, prog="dot", args="-Gdpi=300")


if __name__ == "__main__":
    main()
