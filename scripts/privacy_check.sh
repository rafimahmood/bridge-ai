#!/usr/bin/env bash
# Fail if real data could have been committed.
set -e
bad=$(git ls-files | grep -E '^data/|\.(csv|parquet|feather|pkl|sqlite|db|lin)$|^\.env' || true)
bad+=$(git ls-files | grep -E '\.(html|js)$' | grep -v '^tests/fixtures/' || true)
if [ -n "$bad" ]; then echo "Forbidden tracked files:"; echo "$bad"; exit 1; fi
echo "privacy check ok"

# Notebooks must be committed without outputs (they would contain real hands).
for nb in $(git ls-files '*.ipynb'); do
  if python3 -c "import json,sys; nb=json.load(open('$nb')); sys.exit(any(c.get('outputs') for c in nb['cells']))"; then :; else
    echo "Notebook $nb has outputs"; exit 1
  fi
done
echo "notebook check ok"
