#!/usr/bin/env bash
# Fail if real data could have been committed.
set -e
bad=$(git ls-files | grep -E '^data/|\.(csv|parquet|feather|pkl|sqlite|db|lin)$|^\.env' || true)
bad+=$(git ls-files | grep -E '\.(html|js)$' | grep -v '^tests/fixtures/' || true)
if [ -n "$bad" ]; then echo "Forbidden tracked files:"; echo "$bad"; exit 1; fi
echo "privacy check ok"
