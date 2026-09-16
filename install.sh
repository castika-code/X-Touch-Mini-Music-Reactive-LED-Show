#!/bin/bash
# X-Touch Mini Music-Reactive LED Show installer
#   bash install.sh -> the only command needed. It creates the Python environment,
#                      installs the libraries, asks for the settings, checks config.json,
#                      builds XTouchShow.app and registers the autostart agent.
# Run it again at any time to change the settings or to apply edits made to config.json
# by hand: it asks what it needs and restarts the show with the current files.
# The script takes no options. Press Enter to accept the default shown in brackets;
# when it is not run from a terminal every question is answered with its default.
set -e
DIR="$(cd "$(dirname "$0")" && pwd)"
cd "$DIR"

if [ "$#" -gt 0 ]; then
  echo "This script takes no options; it asks what it needs."
  exit 1
fi

# ask_yes_no "question" default   -> default is y or n; returns 0 for yes, 1 for no
ask_yes_no() {
  question="$1"
  default="$2"
  if [ "$default" = "y" ]; then
    label="Y/n"
  else
    label="y/N"
  fi
  if [ ! -t 0 ]; then
    echo "$question [$label] -> using the default (not a terminal)"
    if [ "$default" = "y" ]; then return 0; else return 1; fi
  fi
  while true; do
    printf '%s [%s] ' "$question" "$label"
    read -r answer || answer=""
    answer="$(printf '%s' "$answer" | tr '[:upper:]' '[:lower:]')"
    [ -n "$answer" ] || answer="$default"
    case "$answer" in
      y|yes) return 0 ;;
      n|no) return 1 ;;
      *) echo "  Please answer y or n." ;;
    esac
  done
}

# build_applet_icns source.png App.app   -> writes App.app/Contents/Resources/applet.icns
# Returns non-zero when the conversion fails; the caller then keeps the default
# applet icon. Called from an "if", so set -e does not abort the script here.
build_applet_icns() {
  icon_src="$1"
  icon_app="$2"
  icon_tmp="$(mktemp -d)" || return 1
  iconset="$icon_tmp/applet.iconset"
  mkdir -p "$iconset" || { rm -rf "$icon_tmp"; return 1; }
  for spec in 16:icon_16x16 32:icon_16x16@2x 32:icon_32x32 64:icon_32x32@2x \
              128:icon_128x128 256:icon_128x128@2x 256:icon_256x256 512:icon_256x256@2x \
              512:icon_512x512 1024:icon_512x512@2x; do
    px="${spec%%:*}"
    name="${spec#*:}"
    if ! sips -s format png -z "$px" "$px" "$icon_src" --out "$iconset/$name.png" >/dev/null 2>&1; then
      rm -rf "$icon_tmp"
      return 1
    fi
  done
  mkdir -p "$icon_app/Contents/Resources"
  if ! iconutil -c icns "$iconset" -o "$icon_app/Contents/Resources/applet.icns" >/dev/null 2>&1; then
    rm -rf "$icon_tmp"
    return 1
  fi
  rm -rf "$icon_tmp"
  return 0
}

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
    echo "Refusing to install from this location."
    exit 1
    ;;
esac

LABEL="com.castika.xtouchshow"
PLIST="$HOME/Library/LaunchAgents/$LABEL.plist"
APP="$DIR/XTouchShow.app"
APPLET="$APP/Contents/MacOS/applet"
STAMP="$DIR/.venv/.requirements.stamp"
MIC_TEXT="XTouch Show listens to the music to drive the X-Touch Mini LEDs."
FIRST_INSTALL=0

echo "[1/6] Preparing the Python virtual environment and the libraries"
if ! xcode-select -p >/dev/null 2>&1 && ! python3 -c "import venv" >/dev/null 2>&1; then
  echo "Python 3 is not installed yet."
  echo "macOS will now offer to install the Command Line Tools (this includes Python 3)."
  echo "Click Install in the dialog, wait for it to finish, then run this script again."
  xcode-select --install >/dev/null 2>&1 || true
  exit 1
fi
if [ ! -d .venv ]; then
  FIRST_INSTALL=1
  python3 -m venv .venv
fi
if [ "$FIRST_INSTALL" = "1" ] || [ ! -f "$STAMP" ] || [ requirements.txt -nt "$STAMP" ]; then
  ./.venv/bin/pip install -q --upgrade pip
  ./.venv/bin/pip install -q -r requirements.txt
  touch "$STAMP"
  echo "      libraries installed: $DIR/.venv"
else
  echo "      libraries are already up to date: $DIR/.venv"
fi

echo "[2/6] Settings"
WIZARD_RAN=0
if [ ! -f config.json ]; then
  echo "      No settings file yet. Starting the settings wizard."
  if ! ./.venv/bin/python xtouch_show.py --setup; then
    echo "The settings wizard did not finish, so there is no config.json yet."
    echo "Run this script again from a Terminal window to answer the questions."
    exit 1
  fi
  WIZARD_RAN=1
else
  if ask_yes_no "      Run the settings wizard again?" n; then
    ./.venv/bin/python xtouch_show.py --setup
    WIZARD_RAN=1
  fi
fi
if [ "$WIZARD_RAN" = "0" ]; then
  if ask_yes_no "      Measure the room noise for the noise gate?" n; then
    echo "Stop any music and stay quiet during the measurement."
    echo "Press Enter to start (Ctrl-C to cancel)."
    read -r _
    ./.venv/bin/python xtouch_show.py --calibrate
  fi
fi

echo "[3/6] Checking the settings file"
if ! CONFIG_ERROR="$(./.venv/bin/python -c "import xtouch_show; xtouch_show.load_config('config.json')" 2>&1)"; then
  echo "config.json has an error:"
  echo "$CONFIG_ERROR"
  echo "Fix the file (or run this script again and answer y to the settings wizard)."
  echo "The running show was left untouched."
  exit 1
fi
echo "      config.json is valid: $DIR/config.json"

# An app bundle is what macOS grants microphone access to. A bare python process
# started by launchd is denied silently, so the show is always launched through
# this small applet, which carries NSMicrophoneUsageDescription and is ad-hoc signed.
# Rebuilding it gives it a new signature, which makes macOS ask for the microphone
# permission again, so the app is only rebuilt when something it contains has changed.
# The fingerprint below holds everything the build puts into the bundle; it is stored
# inside the app (before the signing, so the signature covers it) and compared on every run.
echo "[4/6] Building the XTouchShow.app launcher (microphone permission holder)"
mkdir -p "$DIR/logs"
BUNDLE_ID="com.castika.xtouchshow.app"
STAMP_APP="$APP/Contents/Resources/build.stamp"
RUN_LINE="do shell script \"exec '$DIR/.venv/bin/python' '$DIR/xtouch_show.py' --config '$DIR/config.json' >> '$DIR/logs/xtouch_show.log' 2>&1\""
# The icon goes into the bundle, so its checksum belongs in the fingerprint:
# editing or replacing icon.png rebuilds the app with the new icon.
ICON_SRC="$DIR/icon.png"
if [ -f "$ICON_SRC" ]; then
  ICON_SUM="$(shasum -a 256 "$ICON_SRC" | awk '{print $1}')"
else
  ICON_SUM="none"
fi
FINGERPRINT="$DIR
$MIC_TEXT
$BUNDLE_ID
$RUN_LINE
icon:$ICON_SUM"
if [ -d "$APP" ] && [ -x "$APPLET" ] && [ -f "$STAMP_APP" ] \
   && [ "$(cat "$STAMP_APP")" = "$FINGERPRINT" ]; then
  echo "      XTouchShow.app is up to date (kept, so the microphone permission stays granted)"
else
  rm -rf "$APP"
  TMPDIR_APPLET="$(mktemp -d)"
  SRC="$TMPDIR_APPLET/xtouchshow.applescript"
  printf '%s\n' "$RUN_LINE" > "$SRC"
  osacompile -o "$APP" "$SRC"
  rm -rf "$TMPDIR_APPLET"
  P="$APP/Contents/Info.plist"
  /usr/libexec/PlistBuddy -c "Set :NSMicrophoneUsageDescription '$MIC_TEXT'" "$P" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :NSMicrophoneUsageDescription string '$MIC_TEXT'" "$P"
  /usr/libexec/PlistBuddy -c "Set :LSUIElement true" "$P" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :LSUIElement bool true" "$P"
  /usr/libexec/PlistBuddy -c "Set :CFBundleIdentifier $BUNDLE_ID" "$P" 2>/dev/null \
    || /usr/libexec/PlistBuddy -c "Add :CFBundleIdentifier string $BUNDLE_ID" "$P"
  mkdir -p "$APP/Contents/Resources"
  # Custom icon, so the microphone dialog, System Settings > Privacy & Security >
  # Microphone and Control Center show this app instead of the blank applet.
  # osacompile writes CFBundleIconFile = applet (matching Resources/applet.icns)
  # and also CFBundleIconName = applet, which points at the stock icon inside
  # Assets.car and wins over the .icns file; both are removed so the new
  # applet.icns is the only icon in the bundle. No icon.png means no change.
  if [ -f "$ICON_SRC" ]; then
    if build_applet_icns "$ICON_SRC" "$APP"; then
      /usr/libexec/PlistBuddy -c "Set :CFBundleIconFile applet" "$P" 2>/dev/null \
        || /usr/libexec/PlistBuddy -c "Add :CFBundleIconFile string applet" "$P"
      /usr/libexec/PlistBuddy -c "Delete :CFBundleIconName" "$P" 2>/dev/null || true
      rm -f "$APP/Contents/Resources/Assets.car"
      echo "      Icon taken from icon.png"
    else
      echo "      icon.png could not be converted; keeping the default applet icon."
    fi
  fi
  printf '%s' "$FINGERPRINT" > "$STAMP_APP"
  codesign -s - --force "$APP"
  echo "      Built XTouchShow.app"
  echo "      macOS asks for the microphone permission again the first time it runs."
fi

echo "[5/6] Checking the devices"
if [ "$FIRST_INSTALL" = "1" ]; then
  ./.venv/bin/python xtouch_show.py --list-devices
  if ./.venv/bin/python xtouch_show.py --list-devices | grep -q "X-TOUCH MINI"; then
    echo "      X-TOUCH MINI found. Sending a ring test (the rings sweep up and down, then the Layer A/B LEDs light briefly)."
    ./.venv/bin/python xtouch_show.py --test-rings || true
  else
    echo "      X-TOUCH MINI not found. Check the USB cable and MC mode. (The install continues.)"
  fi
else
  echo "      Skipping the ring test (already installed)."
fi

echo "[6/6] Autostart at login"
if ask_yes_no "      Start the show automatically at login?" y; then
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
  echo "      Registered. It starts at every login."
  echo "      On the very first start macOS shows a microphone permission dialog for \"XTouchShow\"."
  echo "      It must be allowed, otherwise the rings stay at zero and the log fills with silence warnings."
  echo "      If no dialog appears, double-click XTouchShow.app once in Finder to trigger it."
  echo "      Log: $DIR/logs/xtouch_show.log   (applet errors: $DIR/logs/launchd.log)"
  echo "      To remove autostart later:  bash uninstall.sh"
  echo "The show is running now. To change settings later, run: bash install.sh"
else
  if launchctl print "gui/$(id -u)/$LABEL" >/dev/null 2>&1; then
    launchctl bootout "gui/$(id -u)/$LABEL" 2>/dev/null || true
    rm -f "$PLIST"
    echo "      The autostart agent was removed and the show stopped."
  fi
  echo "Autostart is off. Start the show by hand with: bash manual_start.sh"
fi
echo "Install finished."
