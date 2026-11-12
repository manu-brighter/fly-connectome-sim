#!/usr/bin/env bash
# Source this file: . scripts/cloud/env.sh
export FLY_CLOUD_ROOT="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../.." && pwd)"
export FLY_CLOUD_TOOLS="$FLY_CLOUD_ROOT/.tools/cloud"
export PATH="$FLY_CLOUD_TOOLS/npm/bin:$FLY_CLOUD_TOOLS/node/bin:$FLY_CLOUD_TOOLS/uv:$PATH"
export UV_PYTHON_INSTALL_DIR="$FLY_CLOUD_ROOT/.tools/python"
export UV_PYTHON_BIN_DIR="$FLY_CLOUD_TOOLS/python-bin"
export UV_CACHE_DIR="$FLY_CLOUD_ROOT/.tools/uv-cache"
export UV_TOOL_DIR="$FLY_CLOUD_TOOLS/uv-tools"
export UV_PROJECT_ENVIRONMENT="$FLY_CLOUD_ROOT/.venv"
export UV_PYTHON=3.12.14
export NODE_USE_ENV_PROXY=1
