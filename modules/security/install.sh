#!/usr/bin/env sh
# leroy-security installer — refuses to install without explicit authorized-use consent.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
echo "──────────────────────────────────────────────────────────"
cat "$DIR/ACKNOWLEDGMENT.md"
echo "──────────────────────────────────────────────────────────"
printf "Type 'I AGREE' to confirm authorized-use only: "
read ans
if [ "$ans" != "I AGREE" ]; then
  echo "Not installed. The security module requires authorized-use consent."
  exit 1
fi
mkdir -p "$HOME/.claude/skills/security" "$HOME/.claude/config"
cp -r "$DIR/skills/." "$HOME/.claude/skills/security/"
date -u +"%Y-%m-%dT%H:%M:%SZ consent=I_AGREE" > "$HOME/.claude/config/security-consent.txt"
echo "leroy-security installed to ~/.claude/skills/security. Use only where you are authorized."
