#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# bump-version.sh
# Erhöht die VERSION-Datei und aktualisiert CHANGELOG.md.
#
# Verwendung:
#   ./scripts/bump-version.sh patch    # 0.4.0 → 0.4.1
#   ./scripts/bump-version.sh minor    # 0.4.0 → 0.5.0
#   ./scripts/bump-version.sh major    # 0.4.0 → 1.0.0
# ---------------------------------------------------------------------------
set -euo pipefail

BUMP="${1:?Bitte Typ angeben: patch|minor|major}"
VERSION_FILE="VERSION"
CHANGELOG="CHANGELOG.md"

CURRENT=$(cat "$VERSION_FILE" | tr -d '[:space:]')
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

case "$BUMP" in
    patch) PATCH=$((PATCH + 1)) ;;
    minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
    major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
    *) echo "Unbekannter Typ: $BUMP (patch|minor|major)" >&2; exit 1 ;;
esac

NEW="${MAJOR}.${MINOR}.${PATCH}"
DATE=$(date +%Y-%m-%d)

echo "$NEW" > "$VERSION_FILE"
echo "VERSION: $CURRENT → $NEW"

# CHANGELOG: [Unreleased] → [NEW] und neuen [Unreleased] einfügen
python3 - <<PYEOF
with open("$CHANGELOG", "r", encoding="utf-8") as f:
    content = f.read()

# [Unreleased] → [NEW] – DATE
content = content.replace(
    "## [Unreleased]",
    "## [Unreleased]\n\n---\n\n## [$NEW] – $DATE",
    1
)

# Vergleichs-Links am Ende aktualisieren
import re

# [Unreleased]-Link aktualisieren
content = re.sub(
    r'\[Unreleased\]: .+/compare/v[^.]+\.[^.]+\.[^.]+\.\.\.HEAD',
    f'[Unreleased]: https://github.com/4cpa/prognostic-fullstack/compare/v{NEW}...HEAD',
    content
)

# Neuen Versions-Link einfügen (nach [Unreleased]-Link)
prev = "$CURRENT"
new_link = f'[{NEW}]: https://github.com/4cpa/prognostic-fullstack/compare/v{prev}...v{NEW}'
content = re.sub(
    r'(\[Unreleased\]: .+\n)',
    r'\1' + new_link + '\n',
    content
)

with open("$CHANGELOG", "w", encoding="utf-8") as f:
    f.write(content)

print(f"CHANGELOG aktualisiert: [Unreleased] → [{NEW}]")
PYEOF

echo ""
echo "Nächste Schritte:"
echo "  git add VERSION CHANGELOG.md"
echo "  git commit -m \"chore: release v${NEW}\""
echo "  git push  # → Release-Workflow erstellt automatisch den Git-Tag"
