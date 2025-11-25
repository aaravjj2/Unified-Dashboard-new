#!/usr/bin/env python3
"""
Compute FinBERT sentiment aggregates per ticker from a headlines CSV or parquet.

The script detects GPU (torch.cuda.is_available()) and batches accordingly.
Writes per-ticker aggregates to a parquet file suitable for merging.

Usage:
  python3 scripts/enrich_finbert.py --headlines data/weekly_headlines_all.parquet --out data/weekly_sentiment.parquet

"""
import argparse
import pandas as pd

MODEL_NAME = 'yiyanghkust/finbert-tone'


def compute_sentiment_batch(headlines, device=None, model_name=MODEL_NAME):
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
    except Exception as e:
        raise RuntimeError('transformers/torch not installed') from e

    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name)
    model.to(device)
    model.eval()

    texts = headlines['title'].fillna(headlines.get('headline', '')).astype(str).tolist()
    batch_size = 64 if device.startswith('cuda') else 8
    out = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        enc = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        out.extend(probs.tolist())

    dfp = pd.DataFrame(out, columns=['neg_prob', 'neu_prob', 'pos_prob'])
    dfp['compound'] = dfp['pos_prob'] - dfp['neg_prob']
    return dfp


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--headlines', required=True, help='Path to headlines CSV or parquet')
    p.add_argument('--out', default='data/weekly_sentiment.parquet')
    p.add_argument('--device', default=None, help='torch device string (e.g., cuda:0)')
    args = p.parse_args()

    if args.headlines.lower().endswith('.parquet'):
        headlines = pd.read_parquet(args.headlines)
    else:
        headlines = pd.read_csv(args.headlines, parse_dates=['published_at', 'date'], low_memory=False)

    if headlines.empty:
        print('no headlines to process')
        return

    # ensure required columns: ticker, title/headline
    if 'ticker' not in headlines.columns:
        raise ValueError('headlines data must include ticker column')
    if 'title' not in headlines.columns and 'headline' not in headlines.columns:
        raise ValueError('headlines data must include title or headline column')

    device = args.device
    # compute sentiment per headline
    sent = compute_sentiment_batch(headlines, device=device)
    out = pd.concat([headlines.reset_index(drop=True), sent], axis=1)

    # aggregate per ticker
    agg = out.groupby('ticker').agg(
        sentiment_mean_7d=('compound', 'mean'),
        sentiment_vol_7d=('compound', 'std'),
        sentiment_count_7d=('compound', 'count'),
        last_sentiment=('compound', 'last'),
    ).reset_index()
    agg.to_parquet(args.out)
    print('wrote', args.out)


#!/usr/bin/env python3
"""
Compute FinBERT sentiment aggregates per ticker from a headlines CSV or parquet.

The script detects GPU (torch.cuda.is_available()) and batches accordingly.
Writes per-ticker aggregates to a parquet file suitable for merging.

Usage:
  python3 scripts/enrich_finbert.py --headlines data/weekly_headlines_all.parquet --out data/weekly_sentiment.parquet

"""

MODEL_NAME = 'yiyanghkust/finbert-tone'


def compute_sentiment_batch(headlines, device=None, model_name=MODEL_NAME):
    try:
        from transformers import AutoTokenizer, AutoModelForSequenceClassification
        import torch
    except Exception as e:
        raise RuntimeError('transformers/torch not installed') from e

    if device is None:
        device = 'cuda' if torch.cuda.is_available() else 'cpu'

    tokenizer = AutoTokenizer.from_pretrained(model_name)
    model = AutoModelForSequenceClassification.from_pretrained(model_name, use_safetensors=True, trust_remote_code=True)
    model.to(device)
    model.eval()

    texts = headlines.get('title', headlines.get('headline', pd.Series([''] * len(headlines)))).fillna('').astype(str).tolist()
    batch_size = 64 if str(device).startswith('cuda') else 8
    out = []
    for i in range(0, len(texts), batch_size):
        batch = texts[i:i+batch_size]
        enc = tokenizer(batch, padding=True, truncation=True, return_tensors='pt')
        enc = {k: v.to(device) for k, v in enc.items()}
        with torch.no_grad():
            logits = model(**enc).logits
        probs = torch.softmax(logits, dim=-1).cpu().numpy()
        out.extend(probs.tolist())

    dfp = pd.DataFrame(out, columns=['neg_prob', 'neu_prob', 'pos_prob'])
    dfp['compound'] = dfp['pos_prob'] - dfp['neg_prob']
    return dfp


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--headlines', required=True, help='Path to headlines CSV or parquet')
    p.add_argument('--out', default='data/weekly_sentiment.parquet')
    p.add_argument('--device', default=None, help='torch device string (e.g., cuda:0)')
    args = p.parse_args()

    # load headlines
    if args.headlines.lower().endswith('.parquet'):
        headlines = pd.read_parquet(args.headlines)
    else:
        # fallback CSV read (avoid forcing specific parse columns)
        headlines = pd.read_csv(args.headlines, low_memory=False)

    if headlines.empty:
        print('no headlines to process')
        return

    # ensure required columns: ticker, title/headline
    if 'ticker' not in headlines.columns:
        raise ValueError('headlines data must include ticker column')
    if 'title' not in headlines.columns and 'headline' not in headlines.columns:
        raise ValueError('headlines data must include title or headline column')

    device = args.device
    # compute sentiment per headline
    sent = compute_sentiment_batch(headlines, device=device)
    out = pd.concat([headlines.reset_index(drop=True), sent], axis=1)

    # aggregate per ticker
    agg = out.groupby('ticker').agg(
        sentiment_mean_7d=('compound', 'mean'),
        sentiment_vol_7d=('compound', 'std'),
        sentiment_count_7d=('compound', 'count'),
        last_sentiment=('compound', 'last'),
    ).reset_index()
    agg.to_parquet(args.out)
    print('wrote', args.out)


if __name__ == '__main__':
    main()
