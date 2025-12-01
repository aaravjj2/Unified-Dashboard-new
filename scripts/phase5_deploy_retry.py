#!/usr/bin/env python3
"""
Simple retry wrapper around az ml endpoint+deployment create commands.
Saves debug logs to /tmp/phase5_deploy_retry.log and /tmp/phase5_deploy_debug.log.
"""
import subprocess
import time
import shlex
import sys
from pathlib import Path

LOG = Path('/tmp/phase5_deploy_retry.log')
DEBUG_LOG = Path('/tmp/phase5_deploy_debug.log')

ENDPOINT_NAME = 'portfolio-prediction-v1'
WORKSPACE = 'unified-dashboard-ml'
RG = 'unified-dashboard-rg'
DEPLOYMENT_YAML = 'deployment.yml'
MAX_ATTEMPTS = 6

cmds = [
    # delete existing endpoint (ignore errors)
    f"az ml online-endpoint delete --name {ENDPOINT_NAME} -w {WORKSPACE} -g {RG} --yes --no-wait",
    # create endpoint
    f"az ml online-endpoint create --name {ENDPOINT_NAME} -w {WORKSPACE} -g {RG}",
    # create deployment from yaml
    f"az ml online-deployment create -f {DEPLOYMENT_YAML} -n blue --endpoint-name {ENDPOINT_NAME} -w {WORKSPACE} -g {RG}",
    # route traffic
    f"az ml online-endpoint update --name {ENDPOINT_NAME} --traffic blue=100 -w {WORKSPACE} -g {RG}",
    # show scoring uri
    f"az ml online-endpoint show --name {ENDPOINT_NAME} -w {WORKSPACE} -g {RG} --query scoring_uri -o tsv",
]


def run(cmd, capture_debug=False):
    LOG.write_text(LOG.read_text() + f"\n\n>>> RUN: {cmd}\n") if LOG.exists() else LOG.write_text(f">>> RUN: {cmd}\n")
    args = shlex.split(cmd)
    if capture_debug:
        # run with --debug and capture output
        args_debug = args + ['--debug']
        p = subprocess.Popen(args_debug, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out = ''
        for line in p.stdout:
            out += line
        p.wait()
        DEBUG_LOG.write_text(DEBUG_LOG.read_text() + out) if DEBUG_LOG.exists() else DEBUG_LOG.write_text(out)
        return p.returncode, out
    else:
        p = subprocess.Popen(args, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True)
        out = ''
        for line in p.stdout:
            out += line
        p.wait()
        LOG.write_text(LOG.read_text() + out) if LOG.exists() else LOG.write_text(out)
        return p.returncode, out


def main():
    attempt = 0
    while attempt < MAX_ATTEMPTS:
        attempt += 1
        print(f"Attempt {attempt}/{MAX_ATTEMPTS}")
        # step 1: delete (fire-and-forget)
        rc, out = run(cmds[0])
        print('delete requested (rc=%s)' % rc)
        time.sleep(5)

        # step 2: create endpoint
        rc, out = run(cmds[1], capture_debug=True)
        print('create endpoint rc=', rc)
        if rc == 0 and 'Provisioning_state' not in out:
            # still may be async; check endpoint show
            pass
        if rc != 0:
            if 'SubscriptionNotRegistered' in out or 'SubscriptionNotRegistered' in out:
                wait = 30 * attempt
                print(f"SubscriptionNotRegistered detected; sleeping {wait}s then retrying...")
                time.sleep(wait)
                continue
            else:
                print('create endpoint failed, captured debug to', DEBUG_LOG)
                break

        # step 3: create deployment
        rc, out = run(cmds[2], capture_debug=True)
        print('create deployment rc=', rc)
        if rc != 0:
            if 'SubscriptionNotRegistered' in out:
                wait = 30 * attempt
                print(f"SubscriptionNotRegistered detected during deployment; sleeping {wait}s then retrying...")
                time.sleep(wait)
                continue
            if 'Docker image or Dockerfile is required' in out or 'Docker' in out:
                print('Docker/environment error detected; ensure deployment.yml environment has docker image and conda file')
                break
            print('deployment failed; captured debug to', DEBUG_LOG)
            break

        # step 4: route traffic
        rc, out = run(cmds[3])
        print('route traffic rc=', rc)
        # step 5: get scoring uri
        rc, out = run(cmds[4])
        print('scoring uri rc=', rc)
        if rc == 0:
            print('Deployment succeeded, scoring uri:')
            print(out)
            return 0
        else:
            print('failed to get scoring uri; retrying...')
            time.sleep(30)
    print('All attempts exhausted; see /tmp/phase5_deploy_retry.log and /tmp/phase5_deploy_debug.log for details')
    return 1


if __name__ == '__main__':
    sys.exit(main())
