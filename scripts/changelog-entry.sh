#!/usr/bin/env bash
# ---------------------------------------------------------------------------
# changelog-entry.sh
# Fügt einen neuen Eintrag in den [Unreleased]-Abschnitt des CHANGELOG ein.
#
# Verwendung:
#   ./scripts/changelog-entry.sh "Added" "Neue Feature-Beschreibung"
#   ./scripts/changelog-entry.sh "Fixed" "Bug behoben: XYZ"
#   ./scripts/changelog-entry.sh "Changed" "Verhalten von ABC geändert"
#
# Typen: Added | Changed | Deprecated | Removed | Fixed | Security
# ---------------------------------------------------------------------------
set -euo pipefail

TYPE="${1:?Bitte Typ angeben: Added|Changed|Fixed|...}"
ENTRY="${2:?Bitte Eintrag-Text angeben}"
CHANGELOG="CHANGELOG.md"
DATE=$(date +%Y-%m-%d)

# Prüfe ob [Unreleased]-Sektion existiert
if ! grep -q "## \[Unreleased\]" "$CHANGELOG"; then
    echo "Fehler: Keine [Unreleased]-Sektion in $CHANGELOG gefunden." >&2
    exit 1
fi

# Prüfe ob der Typ-Abschnitt unter [Unreleased] schon existiert
if grep -A 20 "## \[Unreleased\]" "$CHANGELOG" | grep -q "### ${TYPE}"; then
    # Typ-Abschnitt existiert – Eintrag dort einfügen
    python3 - <<PYEOF
import re

with open("$CHANGELOG", "r", encoding="utf-8") as f:
    content = f.read()

# Finde den ersten ### ${TYPE} nach [Unreleased] und füge Eintrag ein
pattern = r'(## \[Unreleased\].*?### ${TYPE}\n)(.*?)(\n###|\n## )'
match = re.search(pattern, content, re.DOTALL)
if match:
    insertion = match.group(1) + match.group(2) + "- ${ENTRY}\n" + match.group(3)
    content = content[:match.start()] + insertion + content[match.end():]
    with open("$CHANGELOG", "w", encoding="utf-8") as f:
        f.write(content)
    print("Eintrag hinzugefügt unter ### ${TYPE}")
else:
    print("Warnung: Konnte Einfügeposition nicht finden.")
PYEOF
else
    # Typ-Abschnitt fehlt – nach [Unreleased] einfügen
    python3 - <<PYEOF
with open("$CHANGELOG", "r", encoding="utf-8") as f:
    content = f.read()

marker = "## [Unreleased]\n"
idx = content.index(marker) + len(marker)
insertion = "\n### ${TYPE}\n- ${ENTRY}\n"
content = content[:idx] + insertion + content[idx:]

with open("$CHANGELOG", "w", encoding="utf-8") as f:
    f.write(content)
print("Neuen Abschnitt ### ${TYPE} erstellt und Eintrag hinzugefügt")
PYEOF
fi

echo ""
echo "CHANGELOG aktualisiert. Bitte vor dem Release:"
echo "  1. [Unreleased] in [$(cat VERSION | tr -d '[:space]')] – $DATE umbenennen"
echo "  2. Neuen [Unreleased]-Abschnitt anlegen"
echo "  3. VERSION erhöhen"
