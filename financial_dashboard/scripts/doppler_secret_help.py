"""Diagnostic helper for Doppler secrets.

Checks for required secrets (FINNHUB, ALPACA, POLYGON) using the Doppler CLI
and prints which are present and which are missing. For missing secrets it
prints ready-to-run `doppler secrets set` commands (with placeholders) that
you can fill in or script to import from a local `keys.env` file.

Usage:
  source /mnt/c/Aarav/fin_env/.venv_local/bin/activate
  PYTHONPATH=/mnt/c/Aarav/fin_env/unified-dashboard python3 financial_dashboard/scripts/doppler_secret_help.py
"""
import os
import shutil
import subprocess
from financial_dashboard import key_names as KN

REQUIRED = [
    'FINNHUB_API_KEY_1',
    'FINNHUB_API_KEY_2',
    'ALPACA_API_KEY',
    'ALPACA_SECRET_KEY',
    'POLYGON_API_KEY'
]


def check_with_doppler(candidate, project, config):
    cmd = ['doppler', 'secrets', 'get', candidate, '--plain', '--project', project, '--config', config]
    try:
        proc = subprocess.run(cmd, capture_output=True, text=True, timeout=12)
        if proc.returncode == 0 and proc.stdout.strip():
            return True, proc.stdout.strip()
        # If non-zero, capture stderr for diagnostics
        return False, proc.stderr.strip() or proc.stdout.strip()
    except FileNotFoundError:
        return False, 'doppler CLI not found'
    except Exception as e:
        return False, str(e)


def main():
    print('Doppler diagnostic helper')
    print('Project/config from env or defaults:')
    doppler_project = os.getenv('DOPPLER_PROJECT') or os.getenv('DOPPLER_PROJECT_NAME') or 'dash'
    doppler_config = os.getenv('DOPPLER_CONFIG') or os.getenv('DOPPLER_ENV') or 'dev'
    print(f'  project={doppler_project}  config={doppler_config}')
    print('')

    if not shutil.which('doppler'):
        print('ERROR: doppler CLI not found in PATH')
        return

    missing = []
    for name in REQUIRED:
        resolved = KN.resolve_env_names(name)
        # try all resolved candidates
        found_any = False
        last_err = None
        for cand in resolved:
            ok, out = check_with_doppler(cand, doppler_project, doppler_config)
            if ok:
                print(f'✓ Found secret: {cand} (via Doppler)')
                found_any = True
                break
            else:
                last_err = out
        if not found_any:
            missing.append((name, resolved, last_err))

    print('\nSummary:')
    if not missing:
        print('All required secrets appear to be present in Doppler (for the configured project/config).')
        return

    print(f'{len(missing)} missing secrets:')
    for name, resolved, err in missing:
        print('\n-', name)
        print('  Resolved candidates:', resolved)
        print('  Last Doppler error/output:', err)
        print('  To add this secret, run (replace VALUE):')
        print(f"    doppler secrets set {resolved[0]}=\"<VALUE>\" --project {doppler_project} --config {doppler_config}")

    # If keys.env exists, show how to import it
    keys_env_path = os.path.join(os.path.dirname(os.path.dirname(__file__)), '..', 'keys.env')
    keys_env_path = os.path.abspath(keys_env_path)
    if os.path.exists(keys_env_path):
        print('\nFound local keys.env at', keys_env_path)
        print('You can import it into Doppler with:')
        print(f"  doppler import --format env --project {doppler_project} --config {doppler_config} < {keys_env_path}")
    else:
        print('\nNo local keys.env found in project root.')


if __name__ == '__main__':
    main()
