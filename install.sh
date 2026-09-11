#!/bin/bash
# X-Touch Mini Music-Reactive LED Show installer
#   bash install.sh                -> create .venv, install libraries, build XTouchShow.app,
#                                     run a ring test and register a launchd agent
#                                     (starts at login, restarts if it dies)
#   bash install.sh --no-autostart -> same, but do not register the launchd agent
#   bash install.sh --autostart    -> accepted for compatibility; this is the default
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

AUTOSTART=1
for arg in "$@"; do
  case "$arg" in
    --no-autostart) AUTOSTART=0 ;;
    --autostart) AUTOSTART=1 ;;
    *)
      echo "Unknown option: $arg"
      echo "Usage: bash install.sh [--no-autostart]"
      exit 1
      ;;
  esac
done

case "$DIR" in
  */Library/CloudStorage/*|"$HOME"/Documents/*|"$HOME"/Desktop/*)
    echo "WARNING: this folder is inside a cloud-synced or privacy-protected location:"
    echo "  $DIR"
    echo "Autostart at login cannot run from iCloud Drive, OneDrive, Dropbox, Google Drive,"
    echo "Documents or Desktop: the background process is denied access to its own files"
    echo "(\"Operation not permitted\") and never starts."
    echo "Copy the folder to a plain folder in your home directory instead:"
    echo "  cp -R \"$DIR\" ~/xtouch_show"
    echo "  bash ~/xtouch_show/install.sh"
    if [ "$AUTOSTART" = "1" ]; then
      echo "Refusing to register autostart from this location."
      echo "To install here without autostart:  bash install.sh --no-autostart"
      exit 1
    fi
    echo "Continuing without autostart: manual use from this folder still works."
    ;;
esac

LABEL="com.dogleg.xtouchshow"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="$DIR/XTouchShow.app"
APPLET="$APP/Contents/MacOS/applet"
MIC_TEXT="XTouch Show listens to the music to drive the X-Touch Mini LEDs."

echo "[1/5] Creating the Python virtual environment and installing the libraries"
if ! xcode-select -p >/dev/null 2>&1 && ! python3 -c "import venv" >/dev/null 2>&1; then
  echo "Python 3 is not installed yet."
  echo "macOS will now offer to install the Command Line Tools (this includes Python 3)."
  echo "Click Install in the dialog, wait for it to finish, then run this script again."
  xcode-select --install >/dev/null 2>&1 || true
  exit 1
fi
[ -d .venv ] || python3 -m venv .venv
./.venv/bin/pip install -q --upgrade pip
./.venv/bin/pip install -q -r requirements.txt
echo "      done: $DIR/.venv"

if [ ! -f config.json ]; then
  echo "[2/5] No config file yet. Starting the setup wizard (--setup)"
  if [ -t 0 ]; then
    ./.venv/bin/python xtouch_show.py --setup
  else
    echo "      Not a terminal, skipping. Run it yourself later:  ./.venv/bin/python xtouch_show.py --setup"
  fi
else
  echo "[2/5] Config file found: $DIR/config.json (to run the wizard again: ./.venv/bin/python xtouch_show.py --setup)"
fi

# An app bundle is what macOS grants microphone access to. A bare python process
# started by launchd is denied silently, so the show is always launched through
# this small applet, which carries NSMicrophoneUsageDescription and is ad-hoc signed.
echo "[3/5] Building the XTouchShow.app launcher (microphone permission holder)"
mkdir -p "$DIR/logs"
rm -rf "$APP"
TMPDIR_APPLET="$(mktemp -d)"
SRC="$TMPDIR_APPLET/xtouchshow.applescript"
cat > "$SRC" <<EOF
do shell script "exec '$DIR/.venv/bin/python' '$DIR/xtouch_show.py' --config '$DIR/config.json' >> '$DIR/logs/xtouch_show.log' 2>&1"
EOF
osacompile -o "$APP" "$SRC"
rm -rf "$TMPDIR_APPLET"
P="$APP/Contents/Info.plist"
/usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription '$MIC_TEXT'" "$P" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string '$MIC_TEXT'" "$P"
/usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$P" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$P"
/usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier com.dogleg.xtouchshow.app" "$P" 2>/dev/null \
  || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string com.dogleg.xtouchshow.app" "$P"
codesign -s - --force "$APP"
echo "Built XTouchShow.app"

echo "[4/5] Checking the devices"
./.venv/bin/python xtouch_show.py --list-devices
if ./.venv/bin/python xtouch_show.py --list-devices | grep -q "X-TOUCH MINI"; then
  echo "      X-TOUCH MINI found. Sending a ring test (the rings sweep up and down, then the Layer A/B LEDs light briefly)."
  ./.venv/bin/python xtouch_show.py --test-rings || true
else
  echo "      X-TOUCH MINI not found. Check the USB cable and MC mode. (The install continues.)"
fi

if [ "$AUTOSTART" = "1" ]; then
  echo "[5/5] Registering autostart at login (launchd)"
  mkdir -p "$HOME/Library/LaunchAgents" "$DIR/logs"
  cat > "$PLIST" <<PL
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
  <key>Label</key><string>$LABEL</string>
  <key>ProgramArguments</key>
  <array>
    <string>$APPLET</string>
  </array>
  <key>WorkingDirectory</key><string>$DIR</string>
  <key>RunAtLoad</key><true/>
  <key>KeepAlive</key><true/>
  <key>ThrottleInterval</key><integer>10</integer>
  <key>StandardOutPath</key><string>$DIR/logs/launchd.log</string>
  <key>StandardErrorPath</key><string>$DIR/logs/launchd.log</string>
</dict>
</plist>
PL
  launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
  launchctl bootstrap "gui/$(id -u)" "$PLIST"
  echo "      Registered. It is running in the background now and starts at every login."
  echo "      On the very first start macOS shows a microphone permission dialog for \"XTouchShow\"."
  echo "      It must be allowed, otherwise the rings stay at zero and the log fills with silence warnings."
  echo "      If no dialog appears, double-click XTouchShow.app once in Finder to trigger it."
  echo "      Log: $DIR/logs/xtouch_show.log   (applet errors: $DIR/logs/launchd.log)"
  echo "      To remove autostart later:  bash uninstall.sh"
  echo "      To install without autostart: bash install.sh --no-autostart"
else
  echo "[5/5] Autostart was skipped (--no-autostart)."
  echo "      To run the show by hand: bash run.sh  or  ./.venv/bin/python xtouch_show.py"
  echo "      To register autostart at login later:  bash install.sh"
fi
echo "Install finished."
