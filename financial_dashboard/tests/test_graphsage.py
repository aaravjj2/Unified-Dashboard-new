import pandas as pd
from src.pipeline.embeddings import compute_embeddings, train_and_cache_embeddings


def make_df():
    # tiny synthetic dataset with a 'ticker' group column to exercise autodetect
    df = pd.DataFrame({
        'ticker': ['A', 'A', 'B', 'B'],
        'date': pd.to_datetime(['2020-01-01', '2020-01-02', '2020-01-01', '2020-01-02']),
        'feat1': [1.0, 2.0, 3.0, 4.0],
        'feat2': [0.5, 0.6, 0.4, 0.3],
    })
    return df


def test_compute_embeddings_fallback():
    df = make_df()
    emb = compute_embeddings(df, group_col='asset', time_col='date', value_cols=['feat1', 'feat2'], out_dim=4)
    assert emb is not None
    assert 'ticker' in emb.columns or 'asset' in emb.columns or emb.shape[1] >= 2


def test_train_and_cache_embeddings(tmp_path):
    df = make_df()
    out = train_and_cache_embeddings(df, group_col='asset', time_col='date', value_cols=['feat1', 'feat2'], out_dir=str(tmp_path), out_dim=4)
    assert isinstance(out, dict)
    assert 'embeddings' in out
