"""Embedding helpers: try GraphSAGE, TS2Vec, PyG, then PCA fallback.

This module exposes compute_embeddings(...) and train_and_cache_embeddings(...).
Both functions will attempt available backends in order and fall back to
PCA-based aggregation when learned methods are not available or fail.
"""
from typing import Optional
import pandas as pd
import logging
from datetime import datetime

log = logging.getLogger(__name__)

# optional backends (set to None if import fails)
try:
    from .graphsage import compute_graphsage_embeddings, train_and_cache_graphsage
except Exception:
    compute_graphsage_embeddings = None
    train_and_cache_graphsage = None

try:
    from .ts2vec_wrapper import compute_ts2vec_embeddings, train_and_cache_ts2vec
except Exception:
    compute_ts2vec_embeddings = None
    train_and_cache_ts2vec = None

try:
    from .pyg_wrapper import compute_pyg_embeddings, train_and_cache_pyg
except Exception:
    compute_pyg_embeddings = None
    train_and_cache_pyg = None


def _detect_group_col(df: pd.DataFrame, preferred: str = 'asset') -> str:
    candidates = [preferred, 'ticker', 'symbol', 'id']
    for c in candidates:
        if c in df.columns:
            return c
    raise KeyError(f"No group column found; tried {candidates}")


def _pca(df: pd.DataFrame, group_col: str, time_col: str, value_cols, out_dim: int = 16) -> pd.DataFrame:
    from .simple_embeddings import compute_pca_embeddings

    return compute_pca_embeddings(df, group_col=group_col, time_col=time_col, value_cols=value_cols, out_dim=out_dim)


def compute_embeddings(df: pd.DataFrame, group_col: str = 'asset', time_col: str = 'date', value_cols=None, out_dir: str = 'Dash/models/embeddings', out_dim: int = 16, **kwargs) -> Optional[pd.DataFrame]:
    """Compute embeddings using available backends. Returns DataFrame or None."""
    try:
        actual_group = group_col if group_col in df.columns else _detect_group_col(df, preferred=group_col)
    except KeyError:
        actual_group = _detect_group_col(df)

    # GraphSAGE compute
    if compute_graphsage_embeddings is not None:
        try:
            emb = compute_graphsage_embeddings(df, actual_group, time_col, value_cols, out_dim=out_dim, **kwargs)
            if emb is not None:
                log.info("Using GraphSAGE embeddings")
                return emb
        except Exception:
            log.exception("graphsage attempt failed")

    # TS2Vec compute
    if compute_ts2vec_embeddings is not None:
        try:
            emb = compute_ts2vec_embeddings(df, actual_group, time_col, value_cols, out_dim=out_dim, **kwargs)
            if emb is not None:
                log.info("Using ts2vec embeddings")
                return emb
        except Exception:
            log.exception("ts2vec attempt failed")

    # PyG compute
    if compute_pyg_embeddings is not None:
        try:
            emb = compute_pyg_embeddings(df, actual_group, time_col, value_cols, out_dim=out_dim, **kwargs)
            if emb is not None:
                log.info("Using pyg embeddings")
                return emb
        except Exception:
            log.exception("pyg attempt failed")

    # PCA fallback
    try:
        emb = _pca(df, actual_group, time_col, value_cols, out_dim=out_dim)
        log.info("Using PCA embeddings (fallback)")
        return emb
    except Exception:
        log.exception("pca fallback failed")

    log.warning("No embedding method succeeded; returning None")
    return None


def train_and_cache_embeddings(df: pd.DataFrame, group_col: str = 'asset', time_col: str = 'date', value_cols=None, out_dir: str = 'Dash/models/embeddings', out_dim: int = 16, **kwargs):
    """Train embeddings using available backends and cache the result.

    Returns a dict with key 'embeddings' pointing to the CSV path on success.
    """
    try:
        actual_group = group_col if group_col in df.columns else _detect_group_col(df, preferred=group_col)
    except KeyError:
        actual_group = _detect_group_col(df)

    # GraphSAGE train/cache
    if train_and_cache_graphsage is not None:
        try:
            return train_and_cache_graphsage(df, actual_group, time_col, value_cols, out_dir=str(out_dir) + "/graphsage", out_dim=out_dim, **kwargs)
        except Exception:
            log.exception("train_and_cache_graphsage failed")

    # TS2Vec train/cache
    if train_and_cache_ts2vec is not None:
        try:
            return train_and_cache_ts2vec(df, actual_group, time_col, value_cols, out_dir=str(out_dir) + "/ts2vec", out_dim=out_dim, **kwargs)
        except Exception:
            log.exception("train_and_cache_ts2vec failed")

    # PyG train/cache
    if train_and_cache_pyg is not None:
        try:
            return train_and_cache_pyg(df, actual_group, time_col, value_cols, out_dir=str(out_dir) + "/pyg", out_dim=out_dim, **kwargs)
        except Exception:
            log.exception("train_and_cache_pyg failed")

    # PCA fallback: compute embeddings and write CSV
    try:
        emb = _pca(df, actual_group, time_col, value_cols, out_dim=out_dim)
        from pathlib import Path

        outp = Path(out_dir)
        outp.mkdir(parents=True, exist_ok=True)
        p = outp / f"embeddings_pca_{datetime.now().strftime('%Y%m%d')}.csv"
        emb.to_csv(p, index=False)
        return {"embeddings": str(p)}
    except Exception:
        log.exception("train_and_cache_embeddings: PCA fallback failed")
        raise
