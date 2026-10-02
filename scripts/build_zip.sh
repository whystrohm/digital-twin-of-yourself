#!/usr/bin/env bash
# Rebuild digital-twin-skill.zip from SKILL.md. Run after every SKILL.md edit.
# The test suite fails if the zip and SKILL.md differ.
set -euo pipefail
cd "$(dirname "$0")/.."
rm -f digital-twin-skill.zip
zip -q -X digital-twin-skill.zip SKILL.md
unzip -l digital-twin-skill.zip
