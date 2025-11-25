#!/usr/bin/env bash
# trusted_runner.sh
# Safe command runner: executes only whitelisted commands or commands signed with HMAC.
# Writes audit logs. Intended to be explicit and auditable alternative to an auto-allow policy.
# Usage:
#   ./trusted_runner.sh run "command string" [signature]
#   ./trusted_runner.sh import-vscode-settings path/to/settings.json  # generate whitelist from settings

set -euo pipefail

WHITELIST_REPO_FILE="$(pwd)/.trusted_commands.list"
WHITELIST_HOME_FILE="${HOME}/.trusted_commands.list"
TOKEN_FILE="${HOME}/.trusted_token"
LOG_FILE="${HOME}/.trusted_runner.log"

log() { printf '%s %s\n' "$(date --iso-8601=seconds)" "$*" | tee -a "${LOG_FILE}"; }

is_whitelisted() {
  local cmd="$1"
  # check repo whitelist first
  for f in "${WHITELIST_REPO_FILE}" "${WHITELIST_HOME_FILE}"; do
    if [[ -f "$f" ]]; then
      while IFS= read -r pattern; do
        [[ -z "$pattern" ]] && continue
        # exact match or substring match
        if [[ "$cmd" == "$pattern" ]] || [[ "$cmd" == *"$pattern"* ]]; then
          return 0
        fi
      done < "$f"
    fi
  done
  return 1
}

verify_signed_command() {
  local cmd="$1"; local sig="$2"
  if [[ ! -f "${TOKEN_FILE}" ]]; then
    return 1
  fi
  local key; key=$(<"${TOKEN_FILE}")
  # compute expected sig using openssl
  if ! command -v openssl >/dev/null 2>&1; then
    echo "openssl is required for signed mode" >&2
    return 1
  fi
  local expected; expected=$(printf '%s' "$cmd" | openssl dgst -sha256 -hmac "$key" -hex | awk '{print $2}')
  [[ "$expected" == "$sig" ]]
}

run_command() {
  local cmd="$1"; local sig="${2:-}"
  if is_whitelisted "$cmd"; then
    log "WHITELISTED: $cmd"
    bash -lc "$cmd" 2>&1 | tee -a "${LOG_FILE}"
    log "DONE: $cmd"
    return 0
  fi

  if [[ -n "$sig" ]]; then
    if verify_signed_command "$cmd" "$sig"; then
      log "SIGNED AND VERIFIED: $cmd"
      bash -lc "$cmd" 2>&1 | tee -a "${LOG_FILE}"
      log "DONE (signed): $cmd"
      return 0
    else
      log "SIGNATURE FAILED: $cmd"
      return 2
    fi
  fi

  log "UNAUTHORIZED: $cmd - not in whitelist and not signed"
  echo "Command not authorized. Add to ${WHITELIST_REPO_FILE} or ${WHITELIST_HOME_FILE}, or provide HMAC signature." >&2
  return 3
}

import_vscode_settings_to_whitelist() {
  local settings_path="$1"
  python3 - <<'PY'
import json,sys,os
sfile=sys.argv[1]
with open(sfile,'r',encoding='utf-8') as f:
    j=json.load(f)
mp=j.get('chat.tools.terminal.autoApprove',{})
# normalize keys
out=[]
for k,v in mp.items():
    # keys can be strings or dicts; we just use the key string as pattern
    if isinstance(k,str) and len(k.strip())>0:
        out.append(k.strip())
# write to repo whitelist
repo_file=os.path.join(os.getcwd(),'.trusted_commands.list')
with open(repo_file,'w',encoding='utf-8') as fh:
    for p in sorted(set(out)):
        fh.write(p+'\n')
print('Wrote',len(out),'patterns to',repo_file)
PY
}

case "${1:-}" in
  run)
    shift
    if [[ $# -lt 1 ]]; then
      echo "Usage: $0 run \"command\" [signature]"
      exit 1
    fi
    cmd="$1"; sig="${2:-}"
    run_command "$cmd" "$sig"
    ;;
  import-vscode-settings)
    shift
    if [[ $# -ne 1 ]]; then
      echo "Usage: $0 import-vscode-settings path/to/settings.json"
      exit 1
    fi
    import_vscode_settings_to_whitelist "$1"
    ;;
  *)
    cat <<EOF
trusted_runner.sh - safe command runner
Usage:
  $0 run "command" [signature]    - run only if whitelisted or signed
  $0 import-vscode-settings path/to/settings.json  - convert VSCode autoApprove map into .trusted_commands.list

Notes:
 - Whitelist files: .trusted_commands.list (repo) and ~/.trusted_commands.list (home)
 - To enable signed commands, create ~/.trusted_token with a secret (hex/base64) and use HMAC-SHA256 to sign commands.
EOF
    exit 2
    ;;
esac

