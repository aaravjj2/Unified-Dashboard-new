"""Simple fallback embeddings using group-level aggregation + PCA.

Provides compute_pca_embeddings(df, group_col, time_col, value_cols, out_dim)
which returns a DataFrame with columns [group_col, 'emb_0', ..., 'emb_{k-1}']
"""
from typing import List
import pandas as pd
import numpy as np


def compute_pca_embeddings(df: pd.DataFrame, group_col: str, time_col: str, value_cols: List[str] = None, out_dim: int = 16) -> pd.DataFrame:
    # infer value columns if not provided
    if value_cols is None:
        value_cols = df.select_dtypes(include=["number"]).columns.tolist()
        # remove possible group/time cols
        value_cols = [c for c in value_cols if c not in [group_col, time_col]]

    # simple group-level aggregation: mean and std for each feature
    agg_funcs = {}
    for v in value_cols:
        agg_funcs[v + "__mean"] = (v, "mean")
        agg_funcs[v + "__std"] = (v, "std")

    # build aggregated DataFrame
    grouped = df.groupby(group_col).agg(**agg_funcs)
    # fill NaN stds with 0
    grouped = grouped.fillna(0.0)

    X = grouped.values

    # if out_dim >= n_features, just pad/truncate
    n_features = X.shape[1]
    k = int(out_dim)
    if n_features == 0:
        # return zeros
        emb = np.zeros((len(grouped), k))
    else:
        try:
            from sklearn.decomposition import PCA

            pca = PCA(n_components=min(k, n_features))
            Z = pca.fit_transform(X)
            if Z.shape[1] < k:
                # pad with zeros
                Z = np.hstack([Z, np.zeros((Z.shape[0], k - Z.shape[1]))])
            emb = Z[:, :k]
        except Exception:
            # sklearn not available or PCA failed: fallback to simple linear projection
            # take first k columns (or pad)
            if n_features >= k:
                emb = X[:, :k]
            else:
                emb = np.hstack([X, np.zeros((X.shape[0], k - n_features))])

    cols = [f"emb_{i}" for i in range(k)]
    out = pd.DataFrame(emb, index=grouped.index, columns=cols).reset_index()
    out.rename(columns={grouped.index.name: group_col}, inplace=True)
    # ensure group_col column exists
    if group_col not in out.columns:
        out.insert(0, group_col, grouped.index.values)
    return out
