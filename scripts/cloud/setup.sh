#!/usr/bin/env bash
# Install the CI tool versions locally; never changes system packages or HOME.
set -euo pipefail
source "$(dirname -- "${BASH_SOURCE[0]}")/env.sh"
cd "$FLY_CLOUD_ROOT"
unset VIRTUAL_ENV
export PYTHONPATH='' PYTHONHOME=''
if [[ "$(uname -s)" != Linux || "$(uname -m)" != x86_64 ]]; then
    echo 'This setup supports Linux x86_64 only.' >&2
    exit 1
fi
for command in curl tar xz sha256sum c++ git; do
    command -v "$command" >/dev/null || { echo "Missing prerequisite: $command" >&2; exit 1; }
done
mkdir -p "$FLY_CLOUD_TOOLS" "$FLY_CLOUD_TOOLS/logs"
work=$(mktemp -d "$FLY_CLOUD_TOOLS/setup.XXXXXX")
trap 'rm -rf -- "$work"' EXIT
exec > >(tee "$FLY_CLOUD_TOOLS/logs/setup-$(date -u +%Y%m%dT%H%M%SZ).log") 2>&1
fetch() { curl --fail --location --proto '=https' --tlsv1.2 --connect-timeout 30 --max-time 300 --retry 2 --output "$2" "$1"; }

if [[ ! -x "$FLY_CLOUD_TOOLS/uv/uv" ]] || [[ ! "$("$FLY_CLOUD_TOOLS/uv/uv" --version)" =~ ^uv\ 0\.12\.15([[:space:]]|$) ]]; then
    archive=uv-x86_64-unknown-linux-gnu.tar.gz
    base=https://github.com/astral-sh/uv/releases/download/0.12.15
    fetch "$base/$archive" "$work/$archive"
    fetch "$base/$archive.sha256" "$work/$archive.sha256"
    (cd "$work" && sha256sum --check "$archive.sha256")
    mkdir "$work/uv"
    tar -xzf "$work/$archive" --strip-components=1 -C "$work/uv"
    rm -rf -- "$FLY_CLOUD_TOOLS/uv"
    mv "$work/uv" "$FLY_CLOUD_TOOLS/uv"
fi
if [[ ! -x "$FLY_CLOUD_TOOLS/node/bin/node" ]] || [[ "$("$FLY_CLOUD_TOOLS/node/bin/node" --version)" != v24.21.0 ]]; then
    archive=node-v24.21.0-linux-x64.tar.xz
    base=https://nodejs.org/dist/v24.21.0
    fetch "$base/$archive" "$work/$archive"
    fetch "$base/SHASUMS256.txt" "$work/SHASUMS256.txt"
    (cd "$work" && awk -v name="$archive" '$2 == name { print; found=1 } END { if (!found) exit 1 }' SHASUMS256.txt > node.sha256 && sha256sum --check node.sha256)
    mkdir "$work/node"
    tar -xJf "$work/$archive" --strip-components=1 -C "$work/node"
    rm -rf -- "$FLY_CLOUD_TOOLS/node"
    mv "$work/node" "$FLY_CLOUD_TOOLS/node"
fi
if [[ "$(npm --version)" != 11.19.0 ]]; then
    "$FLY_CLOUD_TOOLS/node/bin/npm" install --prefix "$FLY_CLOUD_TOOLS/npm" --no-audit --no-fund --ignore-scripts npm@11.19.0
    hash -r
fi
[[ "$(uv --version)" =~ ^uv\ 0\.12\.15([[:space:]]|$) ]]
[[ "$(node --version)" == v24.21.0 ]]
[[ "$(npm --version)" == 11.19.0 ]]
cat > "$work/compiler.cpp" <<'CPP'
#include <optional>
int main() { return std::optional<int>{0}.value(); }
CPP
c++ -std=c++17 "$work/compiler.cpp" -o "$work/compiler"
"$work/compiler"
git rev-parse HEAD
cat /etc/os-release
uname -a
command -v c++
c++ --version
uv --version
node --version
npm --version
uv python install 3.12.14 --no-bin
uv sync --locked --extra test --extra media --python 3.12.14
uv run --no-sync python --version
npm --prefix viewer ci
npm --prefix viewer run build
echo 'Ready. Source scripts/cloud/env.sh; start with scripts/cloud/start.sh.'
