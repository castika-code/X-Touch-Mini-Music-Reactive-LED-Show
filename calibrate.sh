#!/bin/bash
# X-Touch Mini Music-Reactive LED Show noise-gate calibration
#   bash calibrate.sh        -> measure the room noise for 3 seconds and save noise_gate_db
#   bash calibrate.sh 10     -> measure for 10 seconds instead
# If the show is registered as an autostart agent, it is restarted so the new gate takes effect.
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

SECONDS_ARG="${1:-3}"

if [ ! -x "./.venv/bin/python" ]; then
  echo "Run install.sh first."
  exit 1
fi

case "$SECONDS_ARG" in
  ''|*[!0-9.]*|.|*.*.*)
    echo "Usage: calibrate.sh [seconds]   (seconds must be a number, default 3)"
    exit 1
    ;;
esac

echo "Stop any music and stay quiet during the measurement."
if [ -t 0 ]; then
  echo "Press Enter to start (Ctrl-C to cancel)."
  read -r _
fi

echo "Measuring room noise for $SECONDS_ARG seconds. Keep the room quiet (no music)."
./.venv/bin/python xtouch_show.py --calibrate --calibrate-seconds "$SECONDS_ARG"
STATUS=$?
if [ "$STATUS" -ne 0 ]; then
  exit "$STATUS"
fi

echo "Applying the new noise gate."
bash "$DIR/restart.sh"
