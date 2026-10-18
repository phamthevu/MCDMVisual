"""Code co-occurrence counts for excerpt-level qualitative coding exports."""
from __future__ import annotations

import numpy as np
import pandas as pd


def _presence(value) -> int:
    if pd.isna(value):
        return 0
    if isinstance(value, (bool, np.bool_)):
        return int(value)
    if isinstance(value, (int, float, np.integer, np.floating)):
        number = float(value)
        if number in (0.0, 1.0):
            return int(number)
        raise ValueError("Code presence cells must be 0/1 or blank.")
    text = str(value).strip().lower()
    if text in ("", "0", "no", "false", "n", "absent"):
        return 0
    if text in ("1", "yes", "true", "y", "present", "x", "coded"):
        return 1
    raise ValueError(f"Unrecognized code-presence value: {value!r}. Use 1/0, Yes/No, or blank.")


def compute_code_cooccurrence(frame: pd.DataFrame):
    """Return (code_names, shared-excerpt count matrix, excerpt_count).

    Accepts either a wide presence sheet (Excerpt ID + one 0/1 column per
    code) or a long assignment sheet (Excerpt ID, Code), one code assignment
    per row. Repeated excerpt/code assignments are deduplicated.
    """
    if not isinstance(frame, pd.DataFrame):
        frame = pd.DataFrame(frame)
    frame = frame.dropna(how="all").dropna(axis=1, how="all").copy()
    if frame.shape[1] < 2:
        raise ValueError("Import a sheet with Excerpt ID and at least two codes (wide format), or Excerpt ID and Code (long format).")

    id_column = frame.columns[0]
    ids = frame[id_column].astype("string").str.strip()
    valid_id = ids.notna() & ids.ne("") & ids.str.lower().ne("nan")
    frame = frame.loc[valid_id].copy()
    ids = ids.loc[valid_id].astype(str)
    if frame.empty:
        raise ValueError("No excerpt IDs were found. Add at least one coded excerpt row.")

    # Two-column files are treated as a long list of code assignments.
    if frame.shape[1] == 2:
        code_column = frame.columns[1]
        codes = frame[code_column].astype("string").str.strip()
        valid_code = codes.notna() & codes.ne("") & codes.str.lower().ne("nan")
        assignments = pd.DataFrame({"excerpt": ids.loc[valid_code].values,
                                    "code": codes.loc[valid_code].astype(str).values})
        if assignments.empty:
            raise ValueError("No code assignments were found in the Code column.")
        labels = list(dict.fromkeys(assignments["code"].tolist()))
        if len(labels) < 2:
            raise ValueError("At least two distinct codes are needed for a co-occurrence chart.")
        presence = np.zeros((assignments["excerpt"].nunique(), len(labels)), dtype=np.int64)
        excerpt_ids = list(dict.fromkeys(assignments["excerpt"].tolist()))
        row_index = {name: i for i, name in enumerate(excerpt_ids)}
        col_index = {name: i for i, name in enumerate(labels)}
        for excerpt, code in assignments.drop_duplicates().itertuples(index=False, name=None):
            presence[row_index[excerpt], col_index[code]] = 1
    else:
        raw_labels = [str(c).strip() for c in frame.columns[1:]]
        if any(not label or label.lower() == "nan" for label in raw_labels):
            raise ValueError("Code column names must not be blank.")
        if len(set(raw_labels)) != len(raw_labels):
            raise ValueError("Code column names must be unique.")
        if len(raw_labels) < 2:
            raise ValueError("At least two code columns are required.")
        presence = np.column_stack([
            np.fromiter((_presence(v) for v in frame.iloc[:, col].tolist()), dtype=np.int64)
            for col in range(1, frame.shape[1])
        ])
        # Collapse repeated rows for the same excerpt by taking code presence.
        excerpt_ids = list(dict.fromkeys(ids.tolist()))
        if len(excerpt_ids) != len(ids):
            collapsed = np.zeros((len(excerpt_ids), presence.shape[1]), dtype=np.int64)
            row_index = {name: i for i, name in enumerate(excerpt_ids)}
            for excerpt, values in zip(ids, presence):
                collapsed[row_index[excerpt]] = np.maximum(collapsed[row_index[excerpt]], values)
            presence = collapsed
        labels = raw_labels

    counts = presence.T @ presence
    return labels, counts.astype(float), len(excerpt_ids)
