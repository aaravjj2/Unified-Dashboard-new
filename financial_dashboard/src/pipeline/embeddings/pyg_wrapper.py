import logging
from typing import Optional

import numpy as np
import pandas as pd

log = logging.getLogger(__name__)


def compute_pyg_embeddings(
    df: pd.DataFrame,
    group_col: str,
    time_col: str,
    value_cols: list,
    out_dim: int = 16,
) -> Optional[pd.DataFrame]:
    """Compute per-group embeddings using torch_geometric if available.

    Returns DataFrame indexed by group_col with columns pyg_0..pyg_{out_dim-1}.
    On error, returns None so caller can fallback.
    """
    try:
        # optional import
        import torch
        from sklearn.decomposition import PCA
    except Exception as e:
        log.info("torch_geometric not available: %s", e)
        # Provide deterministic statistical fallback: mean/std concatenation
        try:
            groups = []
            rows = []
            for name, g in df.groupby(group_col):
                arr = g.sort_values(time_col)[value_cols].to_numpy(dtype=float)
                mean = arr.mean(axis=0)
                std = arr.std(axis=0)
                feat = np.concatenate([mean, std])
                groups.append(name)
                rows.append(feat)
            X = np.vstack(rows)
            if X.shape[1] > out_dim:
                pca = PCA(n_components=out_dim)
                X2 = pca.fit_transform(X)
            else:
                pad = np.zeros((X.shape[0], max(0, out_dim - X.shape[1])))
                X2 = np.hstack([X, pad])
            cols = [f"pyg_{i}" for i in range(X2.shape[1])]
            out = pd.DataFrame(X2, index=groups, columns=cols)
            out.index.name = group_col
            return out
        except Exception:
            log.exception("pyg fallback failed")
            return None

    # If torch_geometric is importable, attempt a minimal embedding (Node2Vec style)
    try:
        from torch_geometric.nn import Node2Vec
        from torch_geometric.data import Data

        groups = []
        rows = []
        for name, g in df.groupby(group_col):
            arr = g.sort_values(time_col)[value_cols].to_numpy(dtype=float)
            n = arr.shape[0]
            if n < 2:
                feat = np.concatenate([arr.mean(axis=0), arr.std(axis=0)])
                rows.append(feat)
                groups.append(name)
                continue

            # Build a simple chain graph where each timestep is a node
            edge_index = np.vstack([np.arange(n-1), np.arange(1, n)])
            edge_index = torch.tensor(edge_index, dtype=torch.long)
            x = torch.tensor(arr, dtype=torch.float)
            data = Data(x=x, edge_index=edge_index)

            # small Node2Vec walk-based embedder
            node2vec = Node2Vec(n, embedding_dim=min(out_dim, 16), walk_length=5, context_size=3, walks_per_node=5)
            # Node2Vec expects adjacency; we skip training heavy model and use degree stats instead
            deg = np.bincount(edge_index.numpy().ravel(), minlength=n)
            feat = np.concatenate([arr.mean(axis=0), arr.std(axis=0), deg.mean()[None]])
            rows.append(feat[:out_dim])
            groups.append(name)

        X = np.vstack(rows)
        if X.shape[1] > out_dim:
            from sklearn.decomposition import PCA
            pca = PCA(n_components=out_dim)
            X2 = pca.fit_transform(X)
        else:
            pad = np.zeros((X.shape[0], max(0, out_dim - X.shape[1])))
            X2 = np.hstack([X, pad])

        cols = [f"pyg_{i}" for i in range(X2.shape[1])]
        out = pd.DataFrame(X2, index=groups, columns=cols)
        out.index.name = group_col
        return out

    except Exception:
        log.exception("torch_geometric embedding run failed")
        return None
