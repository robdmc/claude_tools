#!/bin/bash
# Marp compilation wrapper with required flags
# Usage: compile_marp.sh <presentation-slug> [format]
# Formats: pdf, pptx, html
#
# Examples:
#   compile_marp.sh q4-review           # Compile to PDF
#   compile_marp.sh q4-review pptx      # Compile to PowerPoint
#   compile_marp.sh product-launch html # Compile to HTML

set -e

SLUG="$1"
FORMAT="${2:-pdf}"

if [ -z "$SLUG" ]; then
    echo "Usage: compile_marp.sh <presentation-slug> [format]"
    echo "Formats: pdf (default), pptx, html"
    echo ""
    echo "Examples:"
    echo "  compile_marp.sh q4-review"
    echo "  compile_marp.sh q4-review pptx"
    exit 1
fi

# Determine presentation directory
PRES_DIR="presentations/$SLUG"

if [ ! -d "$PRES_DIR" ]; then
    echo "Error: Presentation directory not found: $PRES_DIR"
    exit 1
fi

INPUT="$PRES_DIR/slides.md"

if [ ! -f "$INPUT" ]; then
    echo "Error: Slides file not found: $INPUT"
    exit 1
fi

OUTPUT="$PRES_DIR/slides.${FORMAT}"

echo "Compiling: $INPUT -> $OUTPUT"

# Run marp with required flags
# --no-stdin: Prevents hanging waiting for input
# --allow-local-files: Enables local image references
marp --no-stdin --allow-local-files "$INPUT" -o "$OUTPUT"

echo "Done: $OUTPUT"
