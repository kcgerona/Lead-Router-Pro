#!/usr/bin/env bash
# Run assigned_to_history tests using project venv so deps (e.g. sqlalchemy) are available.
set -e
cd "$(dirname "$0")"
if [[ -d .venv ]]; then
  .venv/bin/python test_assigned_to_history.py "$@"
else
  echo "No .venv found. Create one and install deps:"
  echo "  python3 -m venv .venv && .venv/bin/pip install sqlalchemy"
  echo "Then run: ./run_test_assigned_to_history.sh"
  exit 1
fi
