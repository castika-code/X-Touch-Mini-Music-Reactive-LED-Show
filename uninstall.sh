#!/bin/bash
# Removes the launchd agent (the folder itself, XTouchShow.app included, is left untouched).
LABEL="com.dogleg.xtouchshow"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null && echo "autostart stopped" || echo "no autostart item was running"
# Stop anything still running: the applet wrapper and the python show itself.
pkill -f "XTouchShow.app/Contents/MacOS/applet" 2>/dev/null && echo "stopped XTouchShow.app" || true
pkill -f "xtouch_show.py" 2>/dev/null && echo "stopped xtouch_show.py" || true
rm -f "$PLIST" && echo "removed: $PLIST"
echo "Done. Delete the whole folder to remove everything else."
