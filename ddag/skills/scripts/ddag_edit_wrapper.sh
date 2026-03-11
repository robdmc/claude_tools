#!/bin/bash
# Wrapper script for ddag external code editing.
# Runs in iTerm2: opens vim, then hands off to post-edit script.
#
# Usage: ddag_edit_wrapper.sh <ddag_path> <name>

DDAG_PATH="$1"
NAME="$2"
SCRIPT_DIR="$(cd "$(dirname "$0")" && pwd)"

# Phase 1: Edit code in vim
vim ".ddag_work/${NAME}.code.py"

# Phase 2: Post-edit handles vimdiff review + commit
python3 "$SCRIPT_DIR/ddag_edit_post.py" "$DDAG_PATH" "$NAME" || read -p "Error occurred. Press enter to close..."
