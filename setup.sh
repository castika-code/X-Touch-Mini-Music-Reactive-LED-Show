#!/bin/bash
# X-Touch Mini Music-Reactive LED Show settings wizard
#   bash setup.sh        -> ask for the MIDI port, audio input, toggle button, button bars
#                           and noise gate, then save them to config.json
# If the show is registered as an autostart agent, it is restarted so the new settings take effect.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ ! -x "./.venv/bin/python" ]; then
  echo "Run install.sh first."
  exit 1
fi

./.venv/bin/python xtouch_show.py --setup
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  exit "$STATUS"
fi

echo "Applying the new settings."
bash "$DIR/restart.sh"
