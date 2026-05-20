#!/usr/bin/env bash
# Shim — the real installer lives in mission-control/setup.sh
# This file exists so `bash setup.sh` keeps working from the repo root.
exec bash "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/mission-control/setup.sh" "$@"
