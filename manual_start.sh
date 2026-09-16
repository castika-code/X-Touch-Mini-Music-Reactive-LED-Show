#!/bin/bash
# X-Touch Mini Music-Reactive LED Show manual launcher
#   bash manual_start.sh      -> run the show in this Terminal window; Ctrl-C to stop
#   bash manual_start.sh -v   -> the same, with verbose output for troubleshooting
# For use when autostart is off. Only one instance may run at a time, so this script
# refuses to start while the autostart agent is registered, or while another instance
# is already running: both would fight over the same MIDI device.
cd "$(dirname "$0")"

LABEL="com.castika.xtouchshow"
if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  echo "The show is already running as an autostart agent (the toggle LED is blinking). Logs: logs/xtouch_show.log. To run it manually, first run: bash uninstall.sh"
  exit 1
fi
if pgrep -f "xtouch_show.py" >/dev/null; then
  echo "Another instance of the show is already running. Stop it first (Ctrl-C in its window)."
  exit 1
fi
if [ ! -x .venv/bin/python ]; then
  echo "Run bash install.sh first and answer N to autostart."
  exit 1
fi

exec ./.venv/bin/python xtouch_show.py "$@"
