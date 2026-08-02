#!/bin/bash
# Builds "Twitch Markers.app" with the GUI script embedded and installs it
# to /Applications (or ~/Applications if not writable), signed ad-hoc.
# Installing outside iCloud-synced folders avoids macOS privacy blocks.
set -e
cd "$(dirname "$0")"

APP="Twitch Markers.app"
TMP="$(mktemp -d)"
trap 'rm -rf "$TMP"' EXIT

ditto "$APP" "$TMP/$APP"
cp twitch_markers_app.py "$TMP/$APP/Contents/Resources/"
chmod +x "$TMP/$APP/Contents/MacOS/launcher"
xattr -cr "$TMP/$APP"
codesign --force --deep --sign - "$TMP/$APP"

DEST="/Applications"
if [ ! -w "$DEST" ]; then
    DEST="$HOME/Applications"
    mkdir -p "$DEST"
fi
rm -rf "$DEST/$APP"
ditto "$TMP/$APP" "$DEST/$APP"

echo "Installed: $DEST/$APP"
echo "Launch it from Launchpad, Spotlight (\"Twitch Markers\"), or $DEST."
