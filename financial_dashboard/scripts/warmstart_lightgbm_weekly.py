"""Placeholder warmstart helper for weekly LightGBM training.
This script doesn't implement full training; it provides a callable entry
point for integration and can be extended to run real LightGBM training.
"""
import argparse
import joblib

def main(argv=None):
    p = argparse.ArgumentParser()
    p.add_argument('--input-features', help='Path to features parquet', default=None)
    p.add_argument('--out-model', help='Path to write model', default=None)
    args = p.parse_args(argv)
    # no-op placeholder
    if args.out_model:
        joblib.dump({'meta': 'placeholder'}, args.out_model)
        print('Wrote placeholder model to', args.out_model)

if __name__ == '__main__':
    main()
