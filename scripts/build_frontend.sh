#!/usr/bin/env bash
set -euo pipefail
cd "$(dirname "$0")/.."
export PATH="$PWD/.tools/node/current/bin:$PATH"
npm --prefix frontend ci
backend/.venv/bin/python -m scripts.make_recipe_art
npm --prefix frontend run build
