#!/usr/bin/env bash
set -e
cd "$(dirname "$0")/../spa"
npm ci
npm run build
echo "SPA built to src/synapps/web/static/"
