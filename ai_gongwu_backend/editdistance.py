"""Minimal fallback implementation for the ``editdistance`` package API.

FunASR imports ``editdistance.eval`` from an optional native extension. The
upstream wheel is not currently available for Python 3.14 on this machine, so
we provide a tiny compatible shim to keep inference working.
"""

from __future__ import annotations


def eval(seq1, seq2) -> int:
    """Return the Levenshtein distance between two sequences."""

    if not seq1:
        return len(seq2)
    if not seq2:
        return len(seq1)

    prev = list(range(len(seq2) + 1))
    for i, item1 in enumerate(seq1, start=1):
        curr = [i]
        for j, item2 in enumerate(seq2, start=1):
            insert_cost = curr[j - 1] + 1
            delete_cost = prev[j] + 1
            replace_cost = prev[j - 1] + (item1 != item2)
            curr.append(min(insert_cost, delete_cost, replace_cost))
        prev = curr
    return prev[-1]
