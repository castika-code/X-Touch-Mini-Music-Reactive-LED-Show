#!/bin/bash
# bash run.sh -> run the show in this Terminal window; Ctrl-C to stop
cd "$(dirname "$0")"
if [ ! -x .venv/bin/python ]; then
  echo "It needs to be installed first:  bash install.sh"
  read -r -p "Press Enter to install it now..." _
  bash install.sh
fi
if [ ! -f config.json ]; then
  ./.venv/bin/python xtouch_show.py --setup
fi
./.venv/bin/python xtouch_show.py
