#!/usr/bin/env bash
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"
SOLYTICS_DIR="/home/jens/Repos/solytics"
RENDER="python ${SCRIPT_DIR}/src/render.py"
FIRMA="Solytics GmbH"
ORT="Karlstein a. Main"
NAME="Jens Laufer"
POSITION="Geschäftsführer"
hebesatz_for_year() {
    case $1 in
        2022) echo 305 ;;
        2023|2024|2025) echo 325 ;;
        2026) echo 395 ;;
        *) echo "ERROR: Unknown Hebesatz for year $1" >&2; return 1 ;;
    esac
}

for YEAR in 2022 2023 2024 2025 2026; do
    JOURNAL="${SOLYTICS_DIR}/${YEAR}/Buchungssaetze/journal.csv"
    OUTPUT_DIR="${SOLYTICS_DIR}/${YEAR}/Berichte"
    HEBESATZ=$(hebesatz_for_year "$YEAR")

    if [ ! -f "$JOURNAL" ]; then
        echo "SKIP ${YEAR}: no journal.csv"
        continue
    fi

    echo "Rendering ${YEAR} (Hebesatz: ${HEBESATZ})..."
    $RENDER all \
        --journal "$JOURNAL" \
        --jahr "$YEAR" \
        --hebesatz "$HEBESATZ" \
        --firma "$FIRMA" \
        --ort "$ORT" \
        --name "$NAME" \
        --position "$POSITION" \
        --output-dir "$OUTPUT_DIR"
done

echo "Done."
