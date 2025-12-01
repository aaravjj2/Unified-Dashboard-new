#!/usr/bin/env python3
"""Compute and cache per-headline embeddings using a transformer (FinBERT or fallback).

Produces:
- data/embeddings_index.parquet (columns: hash, text, file)
- data/embeddings_cache/<hash>.npy (embedding arrays)

Supports --dry-run and --limit for safe testing.
"""
import argparse
from pathlib import Path
import hashlib
import time
import numpy as np
import pandas as pd


def sha1(s: str) -> str:
    return hashlib.sha1(s.encode('utf-8')).hexdigest()


def load_headlines(path):
    df = pd.read_parquet(path)
    # expect columns ['ticker','date','headline','source'] or similar
    df = df.rename(columns={c: c.strip() for c in df.columns})
    # ensure text field
    if 'headline' not in df.columns:
        # try 'title'
        if 'title' in df.columns:
            df['headline'] = df['title']
        else:
            raise SystemExit('No headline/title column found in headlines parquet')
    df['headline_text'] = df['headline'].astype(str).str.strip()
    # drop empty
    df = df[df['headline_text'].str.len() > 0].copy()
    return df


def make_embeddings_dir(base: Path):
    base.mkdir(parents=True, exist_ok=True)
    (base / 'cache').mkdir(parents=True, exist_ok=True)
    return base


def compute_batch_embeddings(texts, model_name='ProsusAI/finbert', device='cpu'):
    try:
        from transformers import AutoTokenizer, AutoModel
        import torch
        tokenizer = AutoTokenizer.from_pretrained(model_name)
        model = AutoModel.from_pretrained(model_name, use_safetensors=True, trust_remote_code=True)
        if device == 'cuda' and torch.cuda.is_available():
            model = model.to('cuda')
            dev = torch.device('cuda')
        else:
            dev = torch.device('cpu')
        model.eval()
        inputs = tokenizer(texts, padding=True, truncation=True, return_tensors='pt')
        inputs = {k: v.to(dev) for k, v in inputs.items()}
        with torch.no_grad():
            out = model(**inputs, output_hidden_states=False, return_dict=True)
            # use pooled output if present, else mean pool last_hidden_state
            if hasattr(out, 'pooler_output') and out.pooler_output is not None:
                emb = out.pooler_output.cpu().numpy()
            else:
                last = out.last_hidden_state
                emb = last.mean(dim=1).cpu().numpy()
        return emb
    except Exception as e:
        print('Transformer embedding failed, falling back to simple hashing vector:', e)
        # fallback: use a deterministic hashed vector
        out = []
        for t in texts:
            h = sha1(t)
            vec = np.frombuffer(bytes.fromhex(h[:64]), dtype=np.uint8).astype(float)
            # normalize/pad to 128
            v = vec.astype(float)
            if v.size < 128:
                v = np.pad(v, (0, 128 - v.size))
            out.append(v[:128])
        return np.vstack(out)


def main():
    p = argparse.ArgumentParser()
    p.add_argument('--headlines', default='data/weekly_headlines_all.parquet')
    p.add_argument('--out-dir', default='data/embeddings')
    p.add_argument('--model', default='ProsusAI/finbert')
    p.add_argument('--device', default='cuda' if (hasattr(__import__('torch'), 'cuda') and __import__('torch').cuda.is_available()) else 'cpu')
    p.add_argument('--dry-run', action='store_true')
    p.add_argument('--limit', type=int, default=0, help='Limit number of unique headlines to embed (for testing)')
    args = p.parse_args()

    base = make_embeddings_dir(Path(args.out_dir))
    index_path = base / 'embeddings_index.parquet'
    cache_dir = base / 'cache'

    print('Loading headlines from', args.headlines)
    df = load_headlines(args.headlines)
    # build unique headlines list
    unique = df['headline_text'].drop_duplicates().reset_index(drop=True)
    if args.limit and args.limit > 0:
        unique = unique.head(args.limit)
    print('Unique headlines to consider:', len(unique))
    # load existing index
    if index_path.exists():
        idx = pd.read_parquet(index_path)
        existing = set(idx['hash'].tolist())
    else:
        idx = pd.DataFrame(columns=['hash','text','file','created_at'])
        existing = set()

    to_process = []
    for t in unique.tolist():
        h = sha1(t)
        if h in existing:
            continue
        to_process.append((h, t))

    print('New headlines to embed:', len(to_process))
    if args.dry_run:
        print('Dry-run mode; will not compute embeddings. Exiting after index check.')
        return

    batch_size = 32
    texts = [t for (_, t) in to_process]
    hashes = [h for (h, _) in to_process]
    for i in range(0, len(texts), batch_size):
        batch_texts = texts[i:i+batch_size]
        batch_hashes = hashes[i:i+batch_size]
        print(f'Computing embeddings for batch {i // batch_size + 1} / {((len(texts)-1)//batch_size)+1}')
        embs = compute_batch_embeddings(batch_texts, model_name=args.model, device=args.device)
        for j, h in enumerate(batch_hashes):
            vec = embs[j]
            fn = cache_dir / f'{h}.npy'
            np.save(fn, vec)
            idx = pd.concat([idx, pd.DataFrame([{'hash': h, 'text': batch_texts[j], 'file': str(fn), 'created_at': time.time()}])], ignore_index=True)
    # write index
    idx.to_parquet(index_path, index=False)
    print('Wrote index to', index_path)


if __name__ == '__main__':
    main()
