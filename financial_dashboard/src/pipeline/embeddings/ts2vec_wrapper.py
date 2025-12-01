import logging
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def compute_ts2vec_embeddings(
    df: pd.DataFrame,
    group_col: str,
    time_col: str,
    value_cols: list,
    out_dim: int = 16,
    window: int = 128,
    stride: int = 64,
) -> Optional[pd.DataFrame]:
    """Compute per-group embeddings using ts2vec and compress with PCA.

    Returns a DataFrame with index=group and columns feature_0..feature_{out_dim-1}.
    On any error, returns None (caller should fallback to PCA-only embedding).
    """
    try:
        # lazy import so package is optional
        import ts2vec
        from sklearn.decomposition import PCA
    except Exception as e:
        log.exception("ts2vec or sklearn not available: %s", e)
        return None

    groups = []
    embeds = []

    try:
        for name, g in df.groupby(group_col):
            # sort by time
            g2 = g.sort_values(time_col)
            # build multivariate time-series array (T, F)
            arr = g2[value_cols].to_numpy(dtype=float)
            if arr.shape[0] < 16:
                # not enough timesteps; pad with zeros
                pad = np.zeros((max(0, 16 - arr.shape[0]), arr.shape[1]), dtype=float)
                arr = np.vstack([arr, pad])

            try:
                # ts2vec expects shape (N, L, C) or similar; we'll use the simplest API
                model = ts2vec.TS2Vec()
                # ts2vec has fit_transform variant in its API - use safe calls
                emb = model.extract_features(arr, mode="avg")
                if emb is None:
                    # fallback: compute a simple summary
                    emb = arr.mean(axis=0)
                # ensure 1D
                emb = np.asarray(emb).ravel()
            except Exception:
                log.exception("ts2vec failed for group %s, falling back to mean vector", name)
                emb = arr.mean(axis=0)

            groups.append(name)
            embeds.append(emb)

        # stack and reduce to out_dim
        X = np.vstack(embeds)
        if X.shape[1] > out_dim:
            pca = PCA(n_components=out_dim)
            X2 = pca.fit_transform(X)
        else:
            # pad columns
            pad = np.zeros((X.shape[0], max(0, out_dim - X.shape[1])))
            X2 = np.hstack([X, pad])

        cols = [f"ts2vec_{i}" for i in range(X2.shape[1])]
        out = pd.DataFrame(X2, index=groups, columns=cols)
        out.index.name = group_col
        return out

    except Exception:
        log.exception("ts2vec embedding pipeline failed")
        return None
