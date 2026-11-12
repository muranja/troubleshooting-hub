#!/usr/bin/env bash
# install.sh — Install troubleup/troubledown CLI links and the Antigravity
# troubleshooting-documenter skill from this repository.
set -euo pipefail

REPO_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BIN_DIR="${BIN_DIR:-$HOME/.local/bin}"
AGY_SKILLS_DIR="${AGY_SKILLS_DIR:-$HOME/.gemini/antigravity/skills}"
AGENTS_SKILLS_DIR="${AGENTS_SKILLS_DIR:-$HOME/.agents/skills}"
SKILL_NAME="troubleshooting-documenter"
INSTALL_SKILL=1
UNINSTALL=0

usage() {
    cat <<EOF
Usage: ./install.sh [options]

Options:
  --bin-dir <dir>    Directory for troubleup/troubledown symlinks (default: ~/.local/bin)
  --no-skill         Skip installing the Antigravity skill
  --uninstall        Remove installed symlinks (keeps all local Markdown files)
  -h, --help         Show this help message
EOF
}

while [ "$#" -gt 0 ]; do
    case "$1" in
        --bin-dir)
            [ "$#" -ge 2 ] || { echo "Error: --bin-dir requires an argument" >&2; exit 1; }
            BIN_DIR="$2"
            shift 2
            ;;
        --no-skill)
            INSTALL_SKILL=0
            shift
            ;;
        --uninstall)
            UNINSTALL=1
            shift
            ;;
        -h|--help)
            usage
            exit 0
            ;;
        *)
            echo "Error: unknown option '$1'" >&2
            usage >&2
            exit 1
            ;;
    esac
done

if [ "$UNINSTALL" -eq 1 ]; then
    rm -f "$BIN_DIR/troubleup" "$BIN_DIR/troubledown"
    rm -rf "$AGY_SKILLS_DIR/$SKILL_NAME" "$AGENTS_SKILLS_DIR/$SKILL_NAME"
    echo "✅ Removed CLI symlinks and skill links (local Markdown notes untouched)."
    exit 0
fi

chmod +x "$REPO_DIR/server.py" \
         "$REPO_DIR/bin/troubleup" \
         "$REPO_DIR/bin/troubledown" \
         "$REPO_DIR/skill/$SKILL_NAME/scripts/new_entry.py"

mkdir -p "$BIN_DIR"
ln -sfn "$REPO_DIR/bin/troubleup" "$BIN_DIR/troubleup"
ln -sfn "$REPO_DIR/bin/troubledown" "$BIN_DIR/troubledown"
echo "✅ Linked troubleup & troubledown into $BIN_DIR"

if [ "$INSTALL_SKILL" -eq 1 ]; then
    mkdir -p "$AGY_SKILLS_DIR" "$AGENTS_SKILLS_DIR"
    rm -rf "$AGY_SKILLS_DIR/$SKILL_NAME" "$AGENTS_SKILLS_DIR/$SKILL_NAME"
    ln -sfn "$REPO_DIR/skill/$SKILL_NAME" "$AGENTS_SKILLS_DIR/$SKILL_NAME"
    ln -sfn "$AGENTS_SKILLS_DIR/$SKILL_NAME" "$AGY_SKILLS_DIR/$SKILL_NAME"
    echo "✅ Installed Antigravity skill '$SKILL_NAME':"
    echo "   - $AGENTS_SKILLS_DIR/$SKILL_NAME"
    echo "   - $AGY_SKILLS_DIR/$SKILL_NAME"
fi

case ":$PATH:" in
    *":$BIN_DIR:"*) ;;
    *)
        echo "ℹ️  Add $BIN_DIR to your PATH to run 'troubleup' from anywhere:"
        echo "   export PATH=\"$BIN_DIR:\$PATH\""
        ;;
esac

echo "🚀 Ready! Run 'troubleup' and open http://127.0.0.1:8898/"
