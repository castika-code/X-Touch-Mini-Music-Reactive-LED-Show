#!/bin/bash
# X-Touch Mini Music-Reactive LED Show restart helper
#   bash restart.sh        -> check config.json for errors, then restart the autostart agent
# Run this after editing config.json by hand. If the file has an error the show is left
# running with the previous settings instead of crash-looping on a broken config.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

LABEL="com.dogleg.xtouchshow"

if [ -x "./.venv/bin/python" ]; then
  CONFIG_ERROR="$(./.venv/bin/python -c "import xtouch_show; xtouch_show.load_config('config.json')" 2>&1)"
  if [ $? -ne 0 ]; then
    echo "config.json has an error:"
    echo "$CONFIG_ERROR"
    exit 1
  fi
fi

if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
  launchctl kickstart -k "gui/$(id -u)/$LABEL"
  echo "Show restarted with the current config.json."
else
  echo "Autostart is not registered. Start the show with 'bash run.sh', or run install.sh to register autostart."
fi
