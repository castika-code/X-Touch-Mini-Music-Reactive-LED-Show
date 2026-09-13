# X-Touch Mini Music-Reactive LED Show (Python)

This is a music-reactive LED show for the Behringer X-Touch Mini. Plug in the controller and play some music: the sound picked up by your microphone is analyzed into 8 frequency bands and shown as a spectrum bar display (an equalizer) on the LED rings of the 8 encoders, and the 16 buttons show the overall level as two bars. It does not matter whether the music comes from your computer's speakers or from another device nearby; it only has to reach the microphone. The Layer A or Layer B button (configurable) turns the show on and off. Every other knob and button is left alone and keeps its normal function.

It runs entirely from a single Python file with no separate app required. **macOS only.**

This guide assumes you are starting from a **fresh Mac with no pre-installed dependencies**. The setup takes about 10–20 minutes.

---

## 1. How It Behaves

| Situation | Behavior |
|---|---|
| Program starts / device connected | Show ON (default). The 8 LED rings start moving as spectrum bars in sync with the music. |
| Top row of buttons (1–8) while show runs | Absolute level bar filling from left to right. |
| Bottom row of buttons (9–16) while show runs | Relative level bar scaled against the minimum-to-maximum range of the last few seconds. Fills left to right and maintains dynamic movement even on heavily compressed tracks. |
| Turning a knob, pressing any other button | Ignored. The show keeps running and the control keeps its normal MIDI function. |
| Quiet room, no music playing | The noise gate is off by default, so faint room noise can still move the LEDs a little. Run `calibrate.sh` to enable the gate and keep them dark. |
| Fader | Adjusts sensitivity (bar height). Moving it all the way down turns off display output (the background show remains running). |
| Layer A or B button (configurable) | Turns the show on and off (configured via `toggle_button`).<br>• **LED off**: Show off<br>• **Blinking**: Show running |
| Unplugging and replugging device | Reconnects automatically. |

The frequency bands corresponding to the LED rings from left to right are: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, and 8 kHz**.

The microphone is only open while the X-Touch Mini is connected **and** the show is on; unplugging the controller or switching the show off with the Layer button closes the audio input, so the orange microphone indicator in the menu bar goes off.

---

## 2. Requirements

| Item | Notes |
|---|---|
| Mac (macOS 12 or later) | The basic installation does not require administrator privileges. |
| Behringer X-Touch Mini + USB cable | Connect directly to a USB port on your Mac. |
| The `xtouch_show` folder | See the file structure section below. |
| Audio Microphone | The Mac's built-in microphone works great. Any external, display, or USB microphone will also work. |

Python 3 is included with the macOS Command Line Tools. If missing, the installation script will prompt you to install them automatically. Python 3 installed via python.org or Homebrew works equally well.

*Note: This is designed as a dynamic visual decorator rather than a high-precision audio analyzer. If you prefer to capture your computer's system audio directly without using a physical microphone, refer to Section 3-7.*

---

## 3. Installation

### 3-1. Set the X-Touch Mini to MC Mode

1. Unplug the USB cable.
2. Hold down the **MC** button on the bottom left of the device while plugging the USB cable back into your Mac.
3. Release the button once the **MC MODE** LED in the top right stays lit. (This setting persists across power cycles.)

*The program also sends an MC mode command automatically upon connecting, ensuring the unit stays in MC mode even if reset.*

### 3-2. Install the Program

1. Place the folder in your home directory (e.g., `~/xtouch_show`).  
   **Important: Do not place the folder inside cloud-synced directories (iCloud Drive, OneDrive, Dropbox, Google Drive) or restricted system directories (`Documents`, `Desktop`). Automatic start at login cannot work from there due to macOS permission restrictions, and the installer will refuse to run.**
2. Open **Terminal** (via Spotlight search).
3. Run the following installation command:

```bash
bash ~/xtouch_show/install.sh
```

4. **What the installer does:**
   - Checks for Python 3. If missing, macOS will prompt you to install Command Line Tools. Click **Install**, wait for completion, and re-run the script above.
   - Creates a virtual environment (`.venv`) inside the directory and installs required libraries (`python-rtmidi`, `sounddevice`, `numpy`).
   - Launches the **Setup Wizard** (Section 3-3) if `config.json` is missing.
   - Generates the launcher app `XTouchShow.app`, which handles microphone permissions for autostart.
   - Displays connected devices and runs a **ring test** if an X-TOUCH MINI is detected. If the 8 LED rings sweep up/down and Layer A/B LEDs flash, the MIDI path is working.
   - Registers the show to **start automatically at login** (through `XTouchShow.app`) and starts it right away. On the first start macOS asks for microphone permission for **"XTouchShow"** — this must be allowed, otherwise the LED rings stay at zero. See Section 3-6.

*For a manual-only install without autostart, run `bash ~/xtouch_show/install.sh --no-autostart`.*

*Admin privileges are not required. All files stay within the project directory.*

### 3-3. Setup Wizard (`setup.sh`)

If `config.json` is not found, the setup wizard runs automatically. You can also trigger it manually anytime:

```bash
bash ~/xtouch_show/setup.sh
```

It asks the same questions, writes the answers to `config.json`, and restarts the autostart agent automatically so the new settings take effect right away.

Press **Enter** to accept default values shown in square brackets `[]`.

| Setting | Default | Description |
|---|---|---|
| MIDI output port [`midi_port_name`] | First port matching `"X-TOUCH MINI"` | Pick a device number or type a name. |
| Audio input device [`audio_input_device`] | System default input | Built-in microphone or custom device. |
| On/Off Toggle Button [`toggle_button`] | `A` | Choose `A` or `B` for Layer buttons. |
| Button LED level bars [`buttons_enabled`] | `y` | Enable/disable the two button-row level bars. |
| Measure room noise now to enable the noise gate? [`noise_gate_db`] | `n` (gate off) | Answer `y` only if room noise moves the LEDs: it listens for 3 seconds and stores the measured noise floor plus `noise_gate_margin_db`. Keep the room quiet while it measures. Answering `n` leaves the gate off, or keeps the gate already in `config.json` (shown as `[n, current: -41.0]`). |

Select the **microphone capturing audio from your speakers**. Leave other settings default unless needed. The wizard will write to `config.json` upon completion.

Every setting can also be changed later by editing `config.json` directly (see Section 4); afterwards run `bash ~/xtouch_show/restart.sh`, which checks the file for errors and restarts the show.

### 3-4. First Run and Permissions

After `install.sh` the show is normally **already running in the background** (the Layer A/B LED blinks and the rings react to music), so there is nothing to start by hand. The steps below are for running it **manually in a Terminal window** instead, which is useful for watching the log output.

**Only one instance may run at a time** — both would fight over the same MIDI device. Stop the autostart first with `bash ~/xtouch_show/uninstall.sh`, and re-register it later with `bash ~/xtouch_show/install.sh`.

1. Run the script via Terminal:

```bash
bash ~/xtouch_show/run.sh
```

2. When macOS prompts **"Terminal would like to access the microphone"**, click **Allow**. Without this permission, audio monitoring will fail. (To fix accidental denials, navigate to *System Settings → Privacy & Security → Microphone*).
3. Successful execution displays output similar to this:

```text
13:05:38 INFO MIDI connected: 'X-TOUCH MINI'
13:05:38 INFO device ready | state=ON | toggle=Layer A (note 84)
13:05:38 INFO started | fps=30 toggle=Layer A | Ctrl-C to quit
13:05:38 INFO audio input: 'MacBook Pro Microphone' @ 48000 Hz, fft 4096
13:05:38 INFO audio input opened
```

The microphone is opened only once the X-Touch Mini is connected and the show is on: switching the show off with the Layer button or unplugging the controller logs `audio input closed` and releases the microphone, so the orange microphone indicator in the menu bar goes off until the show runs again.

### 3-5. Verifying Operation

1. Play music; the LED rings should animate right away.
2. Confirm that the Layer A/B button turns the show on and off (its LED blinks while the show runs), and that moving the fader alters sensitivity.
3. **Sensitivity Tuning:**
   - If bars are too small: Move the mic closer or increase `min_db` (e.g., `-50` or `-40`).
   - If bars are maxed out: Lower `min_db` (e.g., `-70`).
   - **The noise gate is off by default** (`"noise_gate_db": null`), so every sound reaches the LEDs.
   - If the bars move when no music is playing, enable the gate: run `bash ~/xtouch_show/calibrate.sh` in a quiet room. It measures the room noise, saves the resulting `noise_gate_db`, and restarts the autostart agent automatically if one is registered. Alternatively, set `noise_gate_db` in `config.json` to a value by hand (e.g., `-45`); raise it in a noisy room.
   - **Calibrate in silence.** Stop the music and do not talk while `calibrate.sh` measures. Any sound during the measurement is taken for room noise and pushes the gate too high.
   - If music does not move the bars and only loud sounds such as a cough do, the gate is set too high. Run `bash ~/xtouch_show/calibrate.sh` again in a silent room, lower `noise_gate_db` in `config.json` (e.g., `-40`), or set it back to `null` to switch the gate off.
4. Press `Ctrl+C` to quit.

### 3-6. Autostart at Login

`install.sh` sets this up **by default**: the show launches in the background at every login and restarts itself if it stops.

Autostart executes through **`XTouchShow.app`**. macOS requires app bundle permissions for background microphone usage.

- Upon first boot, allow the prompt: **"XTouchShow would like to access the microphone"**.
- If the prompt does not appear, double-click `XTouchShow.app` once in Finder to trigger it.
- **Status Verification:** The Layer A/B LED blinks when the show is running. Logs are saved to `logs/xtouch_show.log` (launcher errors: `logs/launchd.log`).
- **To remove autostart:** Run `bash ~/xtouch_show/uninstall.sh`.
- **To register it again:** Re-run `bash ~/xtouch_show/install.sh`.
- **To install without autostart:** Run `bash ~/xtouch_show/install.sh --no-autostart`.

### 3-7. Optional: Direct System Audio Capture (No Microphone)

If you lack a microphone or want to pass direct digital audio, route system output via a virtual loopback driver. *Requires administrator privileges.*

1. **Install BlackHole**: Download **BlackHole 2ch** installer (`.pkg`) from [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole) or via Homebrew (`brew install blackhole-2ch`).
2. **Set up a Multi-Output Device**:
   1. Open **Audio MIDI Setup** via Spotlight.
   2. Click **`+`** (bottom left) → **Create Multi-Output Device**.
   3. Check both your main output (Speakers/DAC) and **BlackHole 2ch**. Set speakers as Primary/Master, enabling **Drift Correction** for BlackHole.
   4. Right-click the new Multi-Output Device → **Use This Device For Sound Output**.
3. **Configure Program**: Point the show at BlackHole in either of these ways.
   - Run `bash ~/xtouch_show/setup.sh` and pick **BlackHole 2ch** as the audio input device. The script saves the choice and restarts the autostart agent for you.
   - Or edit `config.json` and set `"audio_input_device": "BlackHole 2ch"`, then restart the show with `bash ~/xtouch_show/restart.sh`. If you run the show manually instead of by autostart, press `Ctrl+C` and run `bash ~/xtouch_show/run.sh` again.

*Note: macOS disables hardware volume keys when using a Multi-Output Device. Adjust output volume directly inside your software applications.*

---

## 4. Configuration (`config.json`)

| Parameter | Default | Description |
|---|---|---|
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI port search string (partial matching enabled). |
| `audio_input_device` | `"default"` | System input. Specify a custom name if required. |
| `frame_rate` | `30` | Target LED refresh rate per second. |
| `decay_per_frame` | `1` | Max bar decay steps per single frame. |
| `toggle_button` | `"A"` | Activation toggle button (`"A"` or `"B"`). |
| `show_enabled_at_start` | `true` | Automatically starts visualizer when app launches. |
| `buttons_enabled` | `true` | Enables/disables the two button-row level bars (top = absolute level, bottom = relative level). When false, button LEDs are never touched. |
| `bar_max_fall_s` | `2.0` | Time constant (seconds) for dynamic range ceiling decay. |
| `bar_min_rise_s` | `4.0` | Time constant (seconds) for dynamic range floor rising. |
| `band_centers_hz` | `60` to `8000` | Center frequencies for the 8 encoder LED bands. |
| `band_gains` | `[1.0, ...]` | Individual gain modifiers per frequency band. |
| `min_db` / `max_db` | `-60` / `0` | Dynamic range floor and ceiling calibration (in dB). |
| `fft_size` | `4096` | Analysis window size. High values increase low-end precision. |
| `level_release` | `0.7` | Falloff smoothing factor (0 to 1; higher values yield slower decay). |
| `noise_gate_db` | `null` | `null` = **noise gate off** (every sound reaches the LEDs). A number enables the gate as a threshold in dB: input quieter than this counts as silence and the LEDs go dark. `calibrate.sh` writes this value for you; raise it (e.g., `-35`) in a noisy room, lower it (e.g., `-55`) if quiet passages are cut off, or set it back to `null` to switch the gate off again. |
| `noise_gate_margin_db` | `4.0` | Headroom added to the measured room noise by `--calibrate` and the setup wizard. |

*All settings are read at startup only. After editing `config.json` by hand, run `bash ~/xtouch_show/restart.sh`: it checks the file for errors and restarts the show (if the file has a mistake it reports it and leaves the running show untouched). If you run the show manually with `bash ~/xtouch_show/run.sh` instead of by autostart, press `Ctrl+C` and run it again. The helper scripts restart the show for you: `bash ~/xtouch_show/setup.sh` for the settings wizard, and `bash ~/xtouch_show/calibrate.sh` for `noise_gate_db`.*

**CLI Options:** `--setup` (wizard), `--calibrate` (measure room noise and save `noise_gate_db`, which enables the gate), `--calibrate-seconds SEC` (measurement length, default 3), `--list-devices` (list audio/MIDI devices), `--test-rings` (LED ring hardware sweep), `--input NAME`, `--duration SEC` (timed test exit), `--no-audio`, `-v` (verbose debug output).

---

## 5. Troubleshooting

| Symptom | Cause & Solution |
|---|---|
| `MIDI port 'X-TOUCH MINI' not found` | Check USB connection. Run `--list-devices` to verify the port name. |
| LED rings do not react | Verify **MC MODE** LED status. Close any DAWs that may be overriding MIDI control. |
| Toggle button LED stays dark | MIDI path not acquired. Check logs for `MIDI connected`. |
| Show runs, but bars stay at 0 | Check mic permissions, input device naming, or input audio level. Run with `-v` flag to inspect real-time level telemetry (`gate=off` means no noise gate is configured; `gate=False` with music playing means the noise gate is too high). |
| Bars move with no music playing | Room noise reaches the LEDs because the noise gate is off (the default). Run `bash ~/xtouch_show/calibrate.sh` in a quiet room to enable it (it saves the gate and restarts autostart), or set `noise_gate_db` in `config.json` to a value such as `-45`. |
| Music does not move the bars, only loud sounds like a cough do | The noise gate is too high, usually because the calibration ran while music was playing or someone was talking. Run `bash ~/xtouch_show/calibrate.sh` again with no music and no talking, lower `noise_gate_db` in `config.json` (e.g., `-40`), or set it to `null` to switch the gate off. |
| Orange microphone indicator stays on | The show only holds the microphone while the X-Touch Mini is connected **and** the show is on. Switch the show off with the Layer button, or unplug the controller, and the indicator goes off within about two seconds. If it stays on, another app is using the microphone. |
| Accidentally denied mic permissions | Navigate to *System Settings → Privacy & Security → Microphone* and grant access to **Terminal** or **XTouchShow**. |
| Bars too small / maxed out | Adjust `min_db` parameter (`-50` or `-40` for low levels; `-70` for high levels). |
| High frequencies unresponsive | Increase high-band gain values under `band_gains` (e.g., `1.5`, `2.0`). |
| Rings stay dark after exit | Expected behavior. MC Mode LED rings only update upon active MIDI input from host. |
| Autostart runs but rings stay at 0 | Ensure **XTouchShow** is allowed under System Microphone settings. |
| Autostart fails to launch | Inspect state via `launchctl print gui/$(id -u)/com.dogleg.xtouchshow` or read `logs/xtouch_show.log`. |
| `Operation not permitted` in log | Directory resides in a protected path (`Desktop`, `Documents`, or cloud sync folder). Relocate the folder to `~/xtouch_show` and re-run `bash ~/xtouch_show/install.sh`. The installer refuses to register autostart from such a location. |

---

## 6. Project File Structure

```text
xtouch_show/
├── xtouch_show.py     Main engine (MIDI, DSP, state machine, CLI wizard)
├── config.json        Runtime configuration settings (created by the setup wizard)
├── requirements.txt   Python dependencies list
├── install.sh         Installation & setup script
├── setup.sh           Settings wizard (writes config.json, restarts autostart)
├── calibrate.sh       Noise-gate calibration (measures room noise, restarts autostart)
├── restart.sh         Restarts the show after config changes (checks config.json first)
├── uninstall.sh       Autostart service removal script
├── run.sh             Manual launcher script (runs the show in a Terminal window)
├── test_show.py       Hardware-free logic simulation tool
├── XTouchShow.app     Autostart helper app bundle, built by install.sh (handles macOS permissions)
├── LICENSE            MIT license text
├── .gitignore         Files kept out of version control (.venv, logs, config.json, ...)
└── logs/              Application runtime and daemon logs
```

`config.json`, `XTouchShow.app`, `.venv/` and `logs/` are created on your machine by
`install.sh` and the setup wizard, so they are not part of the downloaded source.

**MC Mode MIDI Specs Reference:**  
- **LED Rings**: Channel 1, CC 48–55, Values `32 + (0–11)`  
- **Button LEDs**: Note On, Velocity `127` (Solid ON), `1` (Blinking), `0` (OFF)  
- **Layer Switches**: Layer A = Note 84, Layer B = Note 85  
- **Fader**: Channel 9 Pitch Bend (Max 16256)  
- **Encoders**: CC 16–23 (Relative values), Push switches = Note 32–39  

License: MIT
