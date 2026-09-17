[English](#xtouchshow) | [한국어](#xtouchshow---한국어-가이드) | [日本語](#xtouchshow---日本語ガイド)

---

# XTouchShow

This is a music-reactive LED show for the Behringer **X-Touch Mini / X-Touch One**. Plug in either controller (or both) and play some music: the sound picked up by your microphone is analyzed and shown on the controller's LEDs. On the Mini, that means an 8-band spectrum on the 8 encoder rings and the overall level as two 16-button bars. On the One, it means the overall level on two button-LED bars, one encoder ring, and a scrolling message on the 12-character display. It does not matter whether the music comes from your computer's speakers or from another device nearby; it only has to reach the microphone. A configurable button on each controller turns the show on and off, and toggling it on either one switches both. Every other knob and button is left alone and keeps its normal function.

Either controller works on its own, and both can run together at the same time. It runs entirely from a single Python file with no separate app required. **macOS only.**

This guide assumes you are starting from a **fresh Mac with no pre-installed dependencies**. The setup takes about 10–20 minutes.

---

## 1. How It Behaves

| Situation | Behavior |
|---|---|
| Program starts / device connected | Show ON (default). The 8 LED rings start moving as spectrum bars in sync with the music. |
| Top row of buttons (1–8) while show runs | Absolute level bar filling from left to right. |
| Bottom row of buttons (9–16) while show runs | Relative level bar scaled against the minimum-to-maximum range of the last few seconds. Fills left to right and maintains dynamic movement even on heavily compressed tracks. |
| Turning a knob, pressing any other button | Ignored. The show keeps running and the control keeps its normal MIDI function. |
| Quiet room, no music playing | The noise gate is off by default, so faint room noise can still move the LEDs a little. Run `install.sh` and answer **y** to the room-noise measurement to enable the gate and keep them dark. |
| Fader | Adjusts sensitivity (bar height). Moving it all the way down turns off display output (the background show remains running). |
| Layer A or B button on the Mini (configurable) | Turns the Mini's show on and off (configured via `mini.toggle_button`).<br>• **LED off**: Show off<br>• **Blinking**: Show running |
| Scrub button on the One (configurable) | Turns the show on and off (configured via `one.toggle_button`).<br>• **LED off**: Show off<br>• **Blinking (software, every 0.5 s)**: Show running<br>Toggling on either controller switches both — there is only one ON/OFF state. |
| X-Touch One connected | The BPM button lights briefly as a peak indicator whenever the level, scaled against the minimum-to-maximum range of the last few seconds, crosses a fixed threshold, with a short hold so quick peaks stay visible. Three button rows fill left to right, each showing one frequency band — mirroring how the Mini's 8 rings show 8 bands: F1–F6 (6 LEDs) shows the high band (4 kHz, 8 kHz), Marker–Solo (7 LEDs) shows the mid band (250 Hz–2 kHz), and Rewind–Record (5 LEDs) shows the low band (60 Hz, 120 Hz). Each row follows the loudest of its sub-bands, not an average of them, and is scaled against the minimum-to-maximum range of that band over the last few seconds — the same auto-ranging idea as the Mini's bottom relative-level row above, applied per frequency band instead of to the overall level, so each row keeps moving whether that part of the mix is quiet or loud. A fifth row lights Channel Mute, Channel Solo, and Channel Record one LED at a time, left to right, with the overall relative level. A sixth bar fills the Bank, Channel, and Up/Left/Zoom/Right/Down buttons from the bottom up, in 5 tiers, with the same overall relative level (Down; Left+Zoom+Right; Up; Channel Left+Right; Bank Left+Right, bottom to top). One encoder ring shows the absolute level, and the device's own level meter also lights up with the overall relative level. The 12-character display scrolls `one.display_text` (`"LED ON"` by default). The Master LED is not used by the show. |
| Unplugging and replugging either device | Reconnects automatically, independently of the other controller. |
| Used together with a DAW | Point the DAW at the virtual `X-TOUCH MINI SHOW` and/or `X-TOUCH ONE SHOW` device (Section 3-7): the DAW keeps working while the show is off, the show takes the LEDs over while it runs, and the DAW's LEDs come back when it stops. |
| Display asleep (screen dark, Mac still awake) | The show stops and the microphone closes until the display wakes again — on the power adapter and on battery alike (`show_when_display_off_on_ac` and `show_when_display_off_on_battery`, both off by default). The Mini's Layer LED keeps blinking, so the show is still switched on. Set either one to `true` to keep the show running while the screen is dark on that power source. |

The frequency bands corresponding to the Mini's LED rings from left to right are: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, and 8 kHz**.

The microphone is only open while at least one controller is connected **and** the show is on; unplugging the last controller or switching the show off closes the audio input, so the orange microphone indicator in the menu bar goes off.

After the Mac wakes from sleep the show re-initializes itself: it sends the MC mode command to each connected controller, restores the LEDs, and reopens the microphone, so there is nothing to restart by hand.

**About the X-Touch One's display:** letters render as 7-segment shapes. `W` looks like `U`, and `M`, `K`, `X` are unreadable or ambiguous on this display, so avoid them in `one.display_text` if you can. `"LED ON"` (the default) renders clearly.

---

## 2. Requirements

| Item | Notes |
|---|---|
| Mac (macOS 12 or later) | The basic installation does not require administrator privileges. |
| Behringer X-Touch Mini and/or X-Touch One + USB cable(s) | Connect directly to a USB port on your Mac. Either one works alone; both can run together. |
| The `xtouch_show` folder | See the file structure section below. |
| Audio Microphone | The Mac's built-in microphone works great. Any external, display, or USB microphone will also work. |

Python 3 is included with the macOS Command Line Tools. If missing, the installation script will prompt you to install them automatically. Python 3 installed via python.org or Homebrew works equally well.

*Note: This is designed as a dynamic visual decorator rather than a high-precision audio analyzer. If you prefer to capture your computer's system audio directly without using a physical microphone, refer to Section 3-9.*

---

## 3. Installation

For a first install, set the controller to MC mode (Section 3-1), then run the one command below and answer the questions it asks. Pressing **Enter** accepts the default shown in brackets `[]`.

```bash
bash ~/xtouch_show/install.sh
```

That is the only command needed to install the show, to change its settings later, and to apply changes. It takes no options: it asks what it needs. Run it again at any time.

### 3-1. Set the Controller(s) to MC Mode

**X-Touch Mini:**

1. Unplug the USB cable.
2. Hold down the **MC** button on the bottom left of the device while plugging the USB cable back into your Mac.
3. Release the button once the **MC MODE** LED in the top right stays lit. (This setting persists across power cycles.)

**X-Touch One:** set it to MC mode the same way, following the button combination in Behringer's X-Touch One manual (it also has a physical MC mode switch/menu on some firmware versions).

*The program also sends an MC mode command automatically upon connecting, ensuring each unit stays in MC mode even if reset.*

This show has been tested against X-Touch One firmware version 1.10.

> [!WARNING]
> **Required, not optional:** this show is built and tested specifically against MC mode's **MC Standard** and **MC Logic** personalities — both confirmed working, with the F1–F6 row's messages even sent using both personalities' note numbers simultaneously specifically so both work correctly, which is why either one is safe to use interchangeably (switched on the device itself).
> No other mode is supported — not any other MC personality the device may offer, and not one of the non-MC raw modes, Behringer's "MIDI Send CC" / "MIDI Send Note" (sometimes labeled "Standard MIDI mode" in the device manual; not to be confused with the "MC Standard" *personality* inside MC mode).
> Every LED, ring, display, and fader message this show sends assumes the MC-mode addressing that only MC Standard and MC Logic are confirmed to honor correctly, and running outside those two has been confirmed to cause malfunction — the motorized fader in particular behaves abnormally, clicking and stuttering, because it keeps receiving MC-protocol fader messages that mode doesn't interpret correctly.
> Do not use the show outside MC mode (MC Standard or MC Logic).

### 3-2. Install the Program

1. Place the folder in your home directory (e.g., `~/xtouch_show`).  
   **Important: Do not place the folder inside cloud-synced directories (iCloud Drive, OneDrive, Dropbox, Google Drive) or restricted system directories (`Documents`, `Desktop`). Automatic start at login cannot work from there due to macOS permission restrictions, and the installer will refuse to run.**
2. Open **Terminal** (via Spotlight search).
3. Run the following installation command:

```bash
bash ~/xtouch_show/install.sh
```

4. **What the installer asks and does:**
   - Checks for Python 3. If missing, macOS will prompt you to install Command Line Tools. Click **Install**, wait for completion, and re-run the script above.
   - Creates a virtual environment (`.venv`) inside the directory and installs required libraries (`python-rtmidi`, `sounddevice`, `numpy`). On later runs the libraries are only reinstalled when `requirements.txt` has changed.
   - Runs the **Setup Wizard** (Section 3-3) if `config.json` is missing. If the file already exists it asks **"Run the settings wizard again?"** (default **N**), and then **"Measure the room noise for the noise gate?"** (default **N**; skipped right after the wizard, which already offers the measurement).
   - Checks `config.json` for errors. If the file has a mistake it reports it and stops before touching the running show.
   - Generates the launcher app `XTouchShow.app`, which handles microphone permissions for autostart.
   - On a first install, displays connected devices and runs a **ring test** if an X-TOUCH MINI is detected. If the 8 LED rings sweep up/down and Layer A/B LEDs flash, the MIDI path is working. Later runs skip the ring test.
   - Asks **"Start the show automatically at login?"** (default **Y**). Answering **Y** registers the show through `XTouchShow.app` and (re)starts it right away with the current files. On the first start macOS asks for microphone permission for **"XTouchShow"** — this must be allowed, otherwise the LED rings stay at zero. See Section 3-6.

*Answering **N** to the autostart question leaves autostart off; the show is then started by hand with `bash ~/xtouch_show/manual_start.sh` (Section 3-4).*

*When the script is not run from a terminal, every question is answered with its default.*

*Admin privileges are not required. All files stay within the project directory.*

*To use your own icon, replace icon.png (1024×1024 PNG) and run install.sh again; macOS will ask for the microphone permission once more.*

### 3-3. Setup Wizard

If `config.json` is not found, the setup wizard runs automatically as part of the installation. To go through it again later, run the install command again and answer **y** to **"Run the settings wizard again?"**:

```bash
bash ~/xtouch_show/install.sh
```

It asks the same questions, writes the answers to `config.json`, and the rest of `install.sh` restarts the show so the new settings take effect right away.

Press **Enter** to accept default values shown in square brackets `[]`.

| Setting | Default | Description |
|---|---|---|
| Mini MIDI output port [`mini.midi_port_name`] | First port matching `"X-TOUCH MINI"` | Pick a device number or type a name. |
| Audio input device [`audio_input_device`] | System default input | Built-in microphone or custom device. Shared by both controllers. |
| Mini On/Off Toggle Button [`mini.toggle_button`] | `A` | Choose `A` or `B` for Layer buttons. |
| Mini button LED level bars [`mini.buttons_enabled`] | `y` | Enable/disable the Mini's two button-row level bars. |
| Measure room noise now to enable the noise gate? [`noise_gate_db`] | `n` (gate off) | Answer `y` only if room noise moves the LEDs: it listens for 3 seconds and stores the measured noise floor plus `noise_gate_margin_db`. Keep the room quiet while it measures. Answering `n` leaves the gate off, or keeps the gate already in `config.json` (shown as `[n, current: -41.0]`). Shared by both controllers. |
| Enable the X-Touch One? [`one.enabled`] | `y` if an X-Touch One is currently connected, otherwise `n` | Answering `y` continues to the MC-mode question below; `n` skips it and the rest, leaving the One switched off. |
| Is your X-Touch One set to MC mode? [`one.enabled`] | `n` | If not set to MC mode, the motorized fader will click/stutter while the show runs. Answering `n` (the default) leaves the One switched off and skips the three questions below, even if you answered `y` above. |
| One MIDI output port [`one.midi_port_name`] | First port matching `"X-Touch One"` | Pick a device number or type a name. |
| One toggle button [`one.toggle_button`] | `Scrub` | Any of its 33 LED names (`BPM`, `F1`-`F6`, `Marker`, `Play`, `Scrub`, ...) or a MIDI note number. |
| One display text [`one.display_text`] | `LED ON` | Up to 12 characters, shown in capitals; scrolls automatically if longer than fits. `W` renders like `U`, and `M`, `K`, `X` are unreadable or ambiguous on this display — avoid them if you can. |

Select the **microphone capturing audio from your speakers**. Leave other settings default unless needed. The wizard will write to `config.json` upon completion, using the `mini`/`one` structure described in Section 4.

Every setting can also be changed later by editing `config.json` directly (see Section 4); afterwards run `bash ~/xtouch_show/install.sh`, which checks the file for errors and restarts the show.

### 3-4. First Run and Permissions

After `install.sh` the show is normally **already running in the background** (the Layer A/B LED blinks and the rings react to music), so there is nothing to start by hand. The steps below are for running it **manually in a Terminal window** instead, which is useful for watching the log output.

`manual_start.sh` is meant for users who answered **N** to the autostart question, or for troubleshooting with `-v`.

**Only one instance may run at a time** — both would fight over the same MIDI device. `manual_start.sh` refuses to start while the autostart agent is registered, and tells you to remove it first. Stop the autostart with `bash ~/xtouch_show/uninstall.sh`, and register it again later with `bash ~/xtouch_show/install.sh`.

1. Run the script via Terminal:

```bash
bash ~/xtouch_show/manual_start.sh
```

To see verbose debug output while troubleshooting, add `-v`:

```bash
bash ~/xtouch_show/manual_start.sh -v
```

2. When macOS prompts **"Terminal would like to access the microphone"**, click **Allow**. Without this permission, audio monitoring will fail. (To fix accidental denials, navigate to *System Settings → Privacy & Security → Microphone*).
3. Successful execution displays output similar to this:

```text
13:05:38 INFO started | fps=30 toggle=mini=Layer A, one=Scrub | Ctrl-C to quit
13:05:38 INFO [mini] MIDI connected: 'X-TOUCH MINI'
13:05:38 INFO [mini] device ready | state=ON | toggle=Layer A (note 84)
13:05:38 INFO [one] MIDI connected: 'X-Touch One'
13:05:38 INFO [one] device ready | state=ON | toggle=Scrub (note 101)
13:05:38 INFO audio input: 'MacBook Pro Microphone' @ 48000 Hz, fft 4096
13:05:38 INFO audio input opened
```

Log lines about one specific controller are prefixed `[mini]` or `[one]`; lines with neither prefix (the microphone, the shared ON/OFF state) apply to both. Only the controllers enabled in `config.json` (Section 4) print their lines — a Mini-only or One-only setup shows only that controller's lines.

The microphone is opened only once at least one controller is connected and the show is on: switching the show off or unplugging the last controller logs `audio input closed` and releases the microphone, so the orange microphone indicator in the menu bar goes off until the show runs again.

### 3-5. Verifying Operation

1. Play music; the Mini's LED rings and/or the One's bars and ring should animate right away.
2. Confirm that the Mini's Layer A/B button and/or the One's Scrub button turn the show on and off (the LED blinks while the show runs — in software, every 0.5 s, on the One), that toggling on one controller also switches the other, and that moving the Mini's fader alters its sensitivity.
3. **Sensitivity Tuning:**
   - If bars are too small: Move the mic closer or increase `min_db` (e.g., `-50` or `-40`).
   - If bars are maxed out: Lower `min_db` (e.g., `-70`).
   - **The noise gate is off by default** (`"noise_gate_db": null`), so every sound reaches the LEDs.
   - If the bars move when no music is playing, enable the gate: run `bash ~/xtouch_show/install.sh` in a quiet room and answer **y** to **"Measure the room noise for the noise gate?"**. It measures the room noise, saves the resulting `noise_gate_db`, and restarts the show. Alternatively, set `noise_gate_db` in `config.json` to a value by hand (e.g., `-45`); raise it in a noisy room.
   - **Measure in silence.** Stop the music and do not talk while the measurement runs. Any sound during the measurement is taken for room noise and pushes the gate too high.
   - If music does not move the bars and only loud sounds such as a cough do, the gate is set too high. Run the measurement again in a silent room, lower `noise_gate_db` in `config.json` (e.g., `-40`), or set it back to `null` to switch the gate off.
4. Press `Ctrl+C` to quit.

### 3-6. Autostart at Login

`install.sh` sets this up **by default**: answering **Y** to **"Start the show automatically at login?"** makes the show launch in the background at every login and restart itself if it stops.

Autostart executes through **`XTouchShow.app`**. macOS requires app bundle permissions for background microphone usage.

- Upon first boot, allow the prompt: **"XTouchShow would like to access the microphone"**.
- The prompt only comes back when `XTouchShow.app` has to be rebuilt (for example after moving the folder); ordinary re-runs of `install.sh` keep the app, so the permission stays granted.
- If the prompt does not appear, double-click `XTouchShow.app` once in Finder to trigger it.
- **Status Verification:** The Mini's Layer A/B LED and/or the One's Scrub LED blink when the show is running. Logs are saved to `logs/xtouch_show.log` (launcher errors: `logs/launchd.log`).
- **To remove autostart and stop the show:** Run `bash ~/xtouch_show/uninstall.sh`.
- **To register it again:** Re-run `bash ~/xtouch_show/install.sh` and answer **Y**.
- **To turn autostart off without uninstalling:** Run `bash ~/xtouch_show/install.sh` and answer **N**; the show is then started by hand with `bash ~/xtouch_show/manual_start.sh`.

### 3-7. Using it Alongside a DAW

In MC mode every LED of a connected controller is drawn by your DAW, so a show that lights the same LEDs wipes that picture out. To avoid that, the program offers the DAW a MIDI device of its own for each controller.

While the program runs it creates a virtual MIDI device for each **enabled** controller: **`X-TOUCH MINI SHOW`** for the Mini and **`X-TOUCH ONE SHOW`** for the One (input and output each). In your DAW's control surface setup, select that device **instead of the real controller** for both the MIDI input and the MIDI output of the corresponding Mackie Control surface. In the DAW's device list it sits right next to the real controller. The program passes everything through in both directions, so:

- **While the show is off**, the DAW works exactly as before: your knobs, buttons and fader/encoder reach the DAW, and the DAW's LEDs, fader moves, display digits, and SysEx reach the controller.
- **While the show is on**, the show owns that controller's LEDs (rings/bars and, on the One, the display). The DAW's LED messages are remembered but not sent on; everything else (the Mini's motor fader and display digits, the One's SysEx) still passes through.
- **When the show switches off** — with the toggle button, when the display goes to sleep, or when the program quits — the LEDs return to exactly what the DAW last set.

Notes:

- Each virtual device exists **only while the program is running and that controller is enabled**, so leave autostart on (Section 3-6); otherwise the device disappears from the DAW whenever the show is not running.
- The **toggle button is not passed to the DAW** (the show consumes it) — on the Mini that's the configured Layer button, on the One its press note(s) (see Section 4). Every other button, knob and the fader/encoder reach the DAW as usual. If you need that button in the DAW, change `mini.toggle_button` or `one.toggle_button`.
- You can still point the DAW at the real controller directly: everything works, but then the show cannot see the DAW's LED state, so the LEDs are simply cleared when the show stops and stay dark until the DAW redraws them.
- To switch a virtual device off entirely, set `"daw_proxy": false` inside that controller's `mini`/`one` section in `config.json`.

### 3-8. About the X-Touch One

The X-Touch One works the same way as the Mini overall (MC mode, hot-plug, DAW proxy, display-off suspension) but shows the music differently, since it has one encoder instead of eight and a 12-character display instead of eight rings:

- **BPM (peak indicator)** lights briefly whenever the level, scaled against the minimum-to-maximum range of the last few seconds, crosses a fixed threshold, held on for a short time afterward so quick peaks stay visible.
- **Three frequency-band rows** fill left to right the same way the Mini's bars do, each with the same one-step-per-frame decay: **F1 line** (F1-F6, 6 LEDs) shows the high band (4 kHz, 8 kHz); **Marker line** (Marker through Solo, 7 LEDs) shows the mid band (250 Hz-2 kHz); **Rewind line** (Rewind through Record, 5 LEDs) shows the low band (60 Hz, 120 Hz) — mirroring how the Mini's 8 rings show 8 bands. Each row follows the loudest of its sub-bands, not an average of them, so a single loud sub-band is not diluted by quieter neighbours in the same group. Each row is also auto-ranged against the minimum-to-maximum level of its own band over the last few seconds — the same idea as the Mini's bottom relative-level row, applied per band instead of to the overall level — so it keeps moving whether that part of the mix is quiet or loud, even with only 5-7 LEDs to work with. Whichever row contains the configured toggle button has that button left out of its fill sequence.
- **A fifth row** lights the Channel Mute, Channel Solo, and Channel Record buttons one LED at a time, in that physical left-to-right order, as the overall relative level rises — the same value the sixth bar below and the Mini's bottom bar both use, not any single frequency band.
- **A sixth relative-level bar** reuses the Bank, Channel, and Up/Left/Zoom/Right/Down buttons, which sit in one vertical column on the device: grouped into 5 tiers and filled from the bottom tier upward with the overall relative level, the same value the Mini's bottom bar and the One's encoder ring both use. Bottom to top: Down; Left+Zoom+Right together; Up; Channel Left+Right together; Bank Left+Right together — so all the buttons in a tier always light or go dark together.
- **One encoder ring** shows the absolute level, exactly like one of the Mini's 8 rings.
- **The device's own level meter** also lights up with the overall relative level, separately from the encoder ring.
- **The 12-character display** shows `one.display_text` (`"LED ON"` by default, forced to capitals, 12 characters max) while the show is on, and is blank while it is off. If the text is longer than fits, it scrolls: the message shifts one position to the right every `one.display_scroll_step_s` seconds until it has fully crossed the display, then restarts from the left (set `one.display_scroll` to `false` for a static, left-aligned display instead). Letters render as 7-segment shapes: `W` looks like `U`, and `M`, `K`, `X` are unreadable or ambiguous, so avoid them if you can.
- **The toggle button** (`Scrub` by default, any of the 33 LED-controllable buttons) turns the show on and off; its LED blinks in software every 0.5 s while the show runs (the device's own hardware blink velocity is unverified, so the program drives it itself instead).
- **Not used by the show:** the Master LED — the show never lights it.
- **Both controllers together:** the Mini and the One can run at the same time, each hot-plugging independently. There is only one ON/OFF state, one microphone, and one config file — toggling the show on either controller's button switches both.

### 3-9. Optional: Direct System Audio Capture (No Microphone)

If you lack a microphone or want to pass direct digital audio, route system output via a virtual loopback driver. *Requires administrator privileges.*

1. **Install BlackHole**: Download **BlackHole 2ch** installer (`.pkg`) from [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole) or via Homebrew (`brew install blackhole-2ch`).
2. **Set up a Multi-Output Device**:
   1. Open **Audio MIDI Setup** via Spotlight.
   2. Click **`+`** (bottom left) → **Create Multi-Output Device**.
   3. Check both your main output (Speakers/DAC) and **BlackHole 2ch**. Set speakers as Primary/Master, enabling **Drift Correction** for BlackHole.
   4. Right-click the new Multi-Output Device → **Use This Device For Sound Output**.
3. **Configure Program**: Point the show at BlackHole in either of these ways.
   - Run `bash ~/xtouch_show/install.sh`, answer **y** to **"Run the settings wizard again?"**, and pick **BlackHole 2ch** as the audio input device. The script saves the choice and restarts the show for you.
   - Or edit `config.json` and set `"audio_input_device": "BlackHole 2ch"`, then run `bash ~/xtouch_show/install.sh` to check the file and restart the show. If you run the show manually instead of by autostart, press `Ctrl+C` and run `bash ~/xtouch_show/manual_start.sh` again.

*Note: macOS disables hardware volume keys when using a Multi-Output Device. Adjust output volume directly inside your software applications.*

---

## 4. Configuration (`config.json`)

Each controller has its own section, `"mini"` and `"one"`; everything else is shared by both. A `config.json` from before X-Touch One support (flat `midi_port_name`, `toggle_button`, `buttons_enabled`, `daw_proxy`, `daw_proxy_name` keys) still loads correctly — the program migrates them into `"mini"` automatically — but the setup wizard always writes the structure below.

### `mini` section (X-Touch Mini)

| Parameter | Default | Description |
|---|---|---|
| `mini.enabled` | `true` | Whether the Mini is used at all. Set to `false` to ignore it even if connected. |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI port search string (partial matching enabled). |
| `mini.toggle_button` | `"A"` | Activation toggle button (`"A"` or `"B"`). |
| `mini.buttons_enabled` | `true` | Enables/disables the two button-row level bars (top = absolute level, bottom = relative level). When false, button LEDs are never touched. |
| `mini.daw_proxy` | `true` | Creates the virtual MIDI device a DAW can use instead of the controller (Section 3-7), so the LEDs the DAW drew are restored when the show stops. Set to `false` to create no virtual device at all. |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | The name of that virtual device as it appears in the DAW. |

### `one` section (X-Touch One)

| Parameter | Default | Description |
|---|---|---|
| `one.enabled` | `false` | Whether the One is used at all. Set to `false` to ignore it even if connected. |
| `one.midi_port_name` | `"X-Touch One"` | MIDI port search string (partial matching enabled). |
| `one.toggle_button` | `"Scrub"` | One of the 33 LED-controllable button names (`BPM`, `Channel Record`, `Channel Solo`, `Channel Mute`, `Channel Select`, `Bank Left/Right`, `Channel Left/Right`, `F1`-`F6`, `Marker`, `Nudge`, `Cycle`, `Drop`, `Replace`, `Click`, `Solo`, `Rewind`, `Forward`, `Stop`, `Play`, `Record`, `Up`, `Down`, `Left`, `Right`, `Zoom`, `Scrub`), case-insensitive, or a literal MIDI note number. An invalid value falls back to `"Scrub"` with a warning in the log. |
| `one.daw_proxy` | `true` | Same as `mini.daw_proxy`, for the One (Section 3-7). |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | The name of that virtual device as it appears in the DAW. |
| `one.display_text` | `"LED ON"` | Shown on the 12-character display while the show is on (Section 3-8). Forced to capitals and truncated to 12 characters. |
| `one.display_scroll` | `true` | Scrolls `display_text` across the display when it is longer than fits. `false` shows it statically, left-aligned. |
| `one.display_scroll_step_s` | `0.3` | Seconds between each one-position scroll step. |

### Shared settings

| Parameter | Default | Description |
|---|---|---|
| `audio_input_device` | `"default"` | System input. Specify a custom name if required. |
| `frame_rate` | `30` | Target LED refresh rate per second. |
| `decay_per_frame` | `1` | Max bar/ring decay steps per single frame. |
| `show_enabled_at_start` | `true` | Automatically starts visualizer when app launches. |
| `show_when_display_off_on_ac` | `false` | Keeps the show running while the display is asleep and the power adapter is connected. Off by default: the LEDs go out and the microphone closes until the display wakes. Set to `true` to keep the show running with the screen dark on AC power. |
| `show_when_display_off_on_battery` | `false` | Keeps the show running while the display is asleep on battery. Off by default: the LEDs go out and the microphone closes until the display wakes, saving power. Set to `true` to keep the show running on battery as well. |
| `bar_max_fall_s` | `2.0` | Time constant (seconds) for dynamic range ceiling decay — shared by the Mini's relative-level row and the X-Touch One's three frequency-band rows. |
| `bar_min_rise_s` | `4.0` | Time constant (seconds) for dynamic range floor rising — shared by the same four auto-ranging trackers. |
| `band_centers_hz` | `60` to `8000` | Center frequencies for the Mini's 8 encoder LED bands. |
| `band_gains` | `[1.0, ...]` | Individual gain modifiers per frequency band. |
| `min_db` / `max_db` | `-60` / `0` | Dynamic range floor and ceiling calibration (in dB). |
| `fft_size` | `4096` | Analysis window size. High values increase low-end precision. |
| `level_release` | `0.7` | Falloff smoothing factor (0 to 1; higher values yield slower decay). |
| `noise_gate_db` | `null` | `null` = **noise gate off** (every sound reaches the LEDs). A number enables the gate as a threshold in dB: input quieter than this counts as silence and the LEDs go dark. The room-noise measurement offered by `install.sh` writes this value for you; raise it (e.g., `-35`) in a noisy room, lower it (e.g., `-55`) if quiet passages are cut off, or set it back to `null` to switch the gate off again. |
| `noise_gate_margin_db` | `4.0` | Headroom added to the measured room noise by the room-noise measurement and the setup wizard. |

*All settings are read at startup only. After editing `config.json` by hand, run `bash ~/xtouch_show/install.sh`: it checks the file for errors and restarts the show (if the file has a mistake it reports it and leaves the running show untouched). If you run the show manually with `bash ~/xtouch_show/manual_start.sh` instead of by autostart, press `Ctrl+C` and run it again.*

---

## 5. Troubleshooting

| Symptom | Cause & Solution |
|---|---|
| `MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` | Check USB connection. On a first install `install.sh` prints the MIDI and audio device list, which shows the exact port name. If you only own one of the two controllers, this is expected for the other and harmless — set that controller's `enabled` to `false` in `config.json` to silence it. |
| LED rings/bars do not react | Verify **MC MODE** status on the controller. Close any DAWs that may be overriding MIDI control, or point the DAW at the `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` device instead (Section 3-7). |
| Motorized fader clicks/stutters | The controller is not in one of the two tested MC personalities (**MC Standard** or **MC Logic**). Malfunction outside those two is confirmed, not just possible — set the controller to MC Standard or MC Logic in MC mode (Section 3-1), and do not use the show in any other mode. |
| DAW does not see the `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` device | The device exists only while the program is running and that controller is enabled: start it (autostart, or `bash ~/xtouch_show/manual_start.sh`) and look for `[mini] DAW proxy ready` / `[one] DAW proxy ready` in `logs/xtouch_show.log`. A `DAW proxy unavailable` line means the virtual ports could not be created; `"daw_proxy": false` in that controller's `config.json` section switches the device off on purpose. Rescan the MIDI devices in the DAW afterwards. |
| Toggle button LED stays dark | MIDI path not acquired. Check logs for `[mini] MIDI connected` / `[one] MIDI connected`. |
| Show runs, but bars stay at 0 | Check mic permissions, input device naming, or input audio level. With autostart off, run `bash ~/xtouch_show/manual_start.sh -v` to inspect real-time level telemetry (`gate=off` means no noise gate is configured; `gate=False` with music playing means the noise gate is too high). |
| Bars move with no music playing | Room noise reaches the LEDs because the noise gate is off (the default). Run `bash ~/xtouch_show/install.sh` in a quiet room and answer **y** to the room-noise measurement to enable it (it saves the gate and restarts the show), or set `noise_gate_db` in `config.json` to a value such as `-45`. |
| Music does not move the bars, only loud sounds like a cough do | The noise gate is too high, usually because the measurement ran while music was playing or someone was talking. Run `bash ~/xtouch_show/install.sh` and repeat the room-noise measurement with no music and no talking, lower `noise_gate_db` in `config.json` (e.g., `-40`), or set it to `null` to switch the gate off. |
| Orange microphone indicator stays on | The show only holds the microphone while at least one controller is connected **and** the show is on. Switch the show off, or unplug the last controller, and the indicator goes off within about two seconds. If it stays on, another app is using the microphone. |
| The show stops reacting after a long time (LEDs frozen, toggle button has no effect, microphone indicator stuck) | The program restarts itself automatically within about 30 seconds, so just wait. Look for `stalled` in `logs/xtouch_show.log` to confirm. If it keeps happening, run `bash ~/xtouch_show/install.sh`. |
| Accidentally denied mic permissions | Navigate to *System Settings → Privacy & Security → Microphone* and grant access to **Terminal** or **XTouchShow**. |
| Bars too small / maxed out | Adjust `min_db` parameter (`-50` or `-40` for low levels; `-70` for high levels). |
| High frequencies unresponsive | Increase high-band gain values under `band_gains` (e.g., `1.5`, `2.0`). |
| Rings/display stay dark after exit | Expected behavior. MC Mode LEDs only update upon active MIDI input from host. If a DAW drives the controller through the `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` device, the LEDs return to the DAW's own state instead (Section 3-7). |
| X-Touch One display text is garbled or unreadable | `W` renders like `U`, and `M`, `K`, `X` are unreadable or ambiguous on this display's 7-segment font — pick a different `one.display_text`. |
| Autostart runs but rings/bars stay at 0 | Ensure **XTouchShow** is allowed under System Microphone settings. |
| Autostart fails to launch | Inspect state via `launchctl print gui/$(id -u)/com.castika.xtouchshow` or read `logs/xtouch_show.log`. |
| `Operation not permitted` in log | Directory resides in a protected path (`Desktop`, `Documents`, or cloud sync folder). Relocate the folder to `~/xtouch_show` and re-run `bash ~/xtouch_show/install.sh`. The installer refuses to run from such a location. |

---

## 6. Project File Structure

```text
xtouch_show/
├── xtouch_show.py     Main engine (MIDI, DSP, state machine, setup wizard)
├── test_show.py       Hardware-free logic simulation tool
├── requirements.txt   Python dependencies list
├── install.sh         Install, change settings, apply changes (the only command needed)
├── uninstall.sh       Removes autostart and stops the show
├── manual_start.sh    Manual launcher (runs the show in a Terminal window)
├── icon.png           App icon source (1024x1024 PNG), used for XTouchShow.app
├── README.md          This guide
├── LICENSE            MIT license text
├── .gitignore         Files kept out of version control (.venv, logs, config.json, ...)
├── config.json        Runtime configuration settings (created by the setup wizard)
├── XTouchShow.app     Autostart helper app bundle, built by install.sh (handles macOS permissions)
├── .venv/             Python environment with the required libraries
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

---

# XTouchShow - 한국어 가이드

Behringer **X-Touch Mini / X-Touch One** 컨트롤러를 위한 음악 반응형 LED 라이트 쇼 프로그램입니다. 둘 중 하나(또는 둘 다)를 연결하고 음악을 재생하면, 마이크로 입력된 소리가 분석되어 컨트롤러의 LED에 표시됩니다. Mini는 8개 엔코더 LED 링에 8개 주파수 대역 스펙트럼을, 16개 버튼에 전체 볼륨 레벨을 두 개의 바로 표시합니다. One은 버튼 LED 바 두 개와 엔코더 링 하나에 전체 볼륨 레벨을, 12자 디스플레이에 스크롤 메시지를 표시합니다. 각 컨트롤러마다 설정 가능한 버튼으로 쇼를 켜고 끌 수 있으며, 어느 쪽에서 켜고 꺼도 둘 다 함께 전환됩니다.

두 컨트롤러 모두 단독으로 작동하며, 동시에 함께 사용할 수도 있습니다. 단일 Python 파일로 작동하며 별도의 앱 설치가 필요 없습니다. **macOS 전용**입니다.

이 가이드는 **의존성 패키지가 설치되지 않은 깨끗한 Mac** 기준 설명입니다. 설정에는 약 10–20분이 소요됩니다.

---

## 1. 주요 동작 방식

| 상황 | 동작 방식 |
| --- | --- |
| 프로그램 시작 / 기기 연결 | 쇼 ON (기본값). 8개 LED 링이 음악에 맞춰 스펙트럼 바로 움직이기 시작합니다. |
| 쇼 실행 중 상단 버튼 (1–8) | 왼쪽에서 오른쪽으로 채워지는 절대 음량 레벨 바입니다. |
| 쇼 실행 중 하단 버튼 (9–16) | 최근 몇 초간의 최소-최대 범위를 기준으로 한 상대 음량 레벨 바입니다. 압축이 강한 음원에서도 다이내믹하게 움직입니다. |
| 노브 조작 및 기타 버튼 입력 | 무시됩니다. LED 쇼는 계속 유지되며 MIDI 본래 기능도 정상 작동합니다. |
| 음악이 없는 조용한 상태 | 기본적으로 노이즈 게이트가 꺼져 있어 미세한 방 안 소음에도 LED가 움직일 수 있습니다. `install.sh`를 실행하고 방 소음 측정 질문에 **y**로 답하면 게이트를 켤 수 있습니다. |
| 페이더 (Fader) | 민감도(바 높이)를 조절합니다. 끝까지 내리면 배경 쇼는 유지된 채 LED 출력만 꺼집니다. |
| Mini의 Layer A / B 버튼 (설정 가능) | Mini의 쇼를 켜고 끕니다 (`mini.toggle_button`으로 설정).<br>• **LED 꺼짐**: 쇼 OFF<br>• **깜빡임**: 쇼 실행 중 |
| One의 Scrub 버튼 (설정 가능) | 쇼를 켜고 끕니다 (`one.toggle_button`으로 설정).<br>• **LED 꺼짐**: 쇼 OFF<br>• **소프트웨어 깜빡임 (0.5초 주기)**: 쇼 실행 중<br>ON/OFF 상태는 하나뿐이라, 어느 컨트롤러에서 켜고 꺼도 둘 다 함께 전환됩니다. |
| X-Touch One 연결 시 | BPM 버튼이 최근 몇 초간의 최소-최대 범위를 기준으로 한 레벨이 일정 임계값을 넘을 때마다 짧게 켜지는 피크 표시등 역할을 하며, 짧은 피크도 보이도록 잠시 켜진 상태를 유지합니다. 버튼 세 줄이 좌→우로 채워지며 각각 하나의 주파수 대역을 표시합니다(Mini의 8개 링이 8개 대역을 보여주는 것과 같은 방식): F1~F6(6개 LED)은 고음 대역(4kHz, 8kHz), Marker~Solo(7개 LED)는 중음 대역(250Hz~2kHz), Rewind~Record(5개 LED)는 저음 대역(60Hz, 120Hz)을 표시합니다. 각 줄은 해당 대역에 속한 세부 대역의 평균이 아니라 가장 큰 값을 따라가며, 최근 몇 초간의 해당 대역 최소-최대 범위를 기준으로 크기가 조정됩니다 — 위의 Mini 하단 상대 레벨 바와 같은 자동 범위 조정 방식을 전체 레벨 대신 주파수 대역별로 적용한 것으로, 음악의 그 부분이 조용하든 크든 각 줄이 계속 움직입니다. 다섯 번째 줄은 Channel Mute, Channel Solo, Channel Record 버튼을 좌→우 순서로 한 개씩 전체 상대 레벨에 따라 켭니다. 여섯 번째 바는 Bank, Channel, Up/Left/Zoom/Right/Down 버튼을 5단으로 나누어 같은 전체 상대 레벨에 따라 아래에서 위로 채웁니다(아래부터: Down, Left+Zoom+Right, Up, Channel Left+Right, Bank Left+Right). 엔코더 링 하나가 절대 레벨을 표시하며, 기기 자체의 레벨 미터도 전체 상대 레벨에 따라 함께 켜집니다. 12자 디스플레이가 `one.display_text`(기본값 `"LED ON"`)를 스크롤합니다. Master LED는 쇼에서 사용하지 않습니다. |
| 기기 연결 해제 후 재연결 | 각 컨트롤러가 서로 독립적으로 자동 재연결됩니다. |
| DAW와 함께 사용할 때 | DAW의 MIDI 입력·출력을 가상 장치 `X-TOUCH MINI SHOW` 및/또는 `X-TOUCH ONE SHOW`로 지정하세요(3-6 참고). 쇼가 꺼져 있으면 DAW가 평소대로 동작하고, 쇼가 켜지면 쇼가 LED를 가져가며, 쇼가 멈추면 DAW의 LED 상태가 그대로 복원됩니다. |
| 디스플레이 잠자기 (화면만 꺼지고 Mac은 켜진 상태) | 전원 어댑터를 연결했든 배터리로 쓰고 있든, 화면이 다시 켜질 때까지 쇼가 멈추고 마이크가 닫힙니다 (`show_when_display_off_on_ac`와 `show_when_display_off_on_battery`, 둘 다 기본값 꺼짐). Mini의 Layer LED는 계속 깜빡이므로 쇼 자체는 켜진 상태입니다. 해당 전원 상태에서 화면이 꺼져도 쇼를 유지하려면 각 항목을 `true`로 설정하세요. |

Mini의 LED 링(왼쪽→오른쪽)에 대응하는 주파수 대역: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

마이크는 컨트롤러가 하나라도 연결되어 있고 쇼가 켜져 있을 때만 열립니다. 마지막 컨트롤러를 뽑거나 쇼를 끄면 오디오 입력이 닫히고, 메뉴 막대의 주황색 마이크 표시도 꺼집니다.

Mac이 잠자기에서 깨어나면 쇼가 스스로 다시 초기화됩니다. 연결된 각 컨트롤러에 MC 모드 명령을 보내고 LED를 복구한 뒤 마이크를 다시 열기 때문에 손으로 재시작할 것은 없습니다.

**X-Touch One 디스플레이 참고:** 글자는 7세그먼트 모양으로 표시됩니다. `W`는 `U`처럼 보이고, `M`, `K`, `X`는 읽기 어렵거나 다른 글자와 헷갈리므로 `one.display_text`에서 가능하면 피하세요. 기본값인 `"LED ON"`은 선명하게 표시됩니다.

---

## 2. 요구 사항

| 항목 | 비고 |
| --- | --- |
| Mac (macOS 12 이상) | 기본 설치 과정에는 관리자 권한이 필요하지 않습니다. |
| Behringer X-Touch Mini 및/또는 X-Touch One + USB 케이블 | Mac의 USB 포트에 직접 연결합니다. 하나만 있어도 되고, 둘 다 함께 사용할 수도 있습니다. |
| `xtouch_show` 폴더 | 아래 파일 구조 섹션을 참고하세요. |
| 오디오 마이크 | Mac 내장 마이크로도 잘 작동하며, 외장/USB 마이크도 지원합니다. |

Python 3는 macOS Command Line Tools에 포함되어 있습니다. 미설치 시 설치 스크립트가 자동 안내합니다.

---

## 3. 설치 가이드

처음 설치할 때는 컨트롤러를 MC 모드로 설정한 뒤(3-1), 아래 명령 하나를 실행하고 물어보는 질문에 답하면 됩니다. 대괄호 `[]` 안의 기본값을 쓰려면 **Enter**를 누르세요.

```zsh
bash ~/xtouch_show/install.sh
```

설치, 설정 변경, 변경 사항 적용에 필요한 명령은 이것 하나뿐입니다. 옵션은 없으며 필요한 것을 직접 물어봅니다. 언제든 다시 실행할 수 있습니다.

### 3-1. 컨트롤러를 MC 모드로 설정

**X-Touch Mini:**

1. USB 케이블을 뽑습니다.
2. 기기 좌측 하단의 **MC** 버튼을 누른 상태에서 USB 케이블을 다시 연결합니다.
3. 우측 상단의 **MC MODE** LED가 켜진 상태로 유지되면 버튼을 뗍니다.

**X-Touch One:** Behringer X-Touch One 매뉴얼에 나온 버튼 조합으로 동일하게 MC 모드로 설정하세요(펌웨어에 따라 물리적인 MC 모드 스위치/메뉴가 있는 경우도 있습니다).

이 쇼는 X-Touch One 펌웨어 버전 1.10을 기준으로 테스트되었습니다.

> [!WARNING]
> **필수 사항입니다:** 이 쇼는 MC 모드의 두 퍼스낼리티, **MC Standard**와 **MC Logic**을 기준으로 만들어지고 실제로 테스트되었습니다 — 두 퍼스낼리티 모두 정상 동작이 확인되었고, F1-F6 줄 메시지는 두 퍼스낼리티의 노트 번호를 동시에 보내도록 되어 있어서 어느 쪽을 선택해도 그대로 맞물려 동작합니다(기기에서 직접 선택).
> 이 두 가지 외에는 어떤 모드도 지원되지 않습니다 — 기기에 다른 MC 퍼스낼리티가 있다면 그것도, 그리고 Behringer가 "MIDI Send CC" / "MIDI Send Note"라고 부르는(매뉴얼에 따라 "Standard MIDI mode"로도 불리는, MC 모드 안의 "MC Standard" 퍼스낼리티와는 다른 개념인) raw 모드도 마찬가지입니다.
> 이 쇼가 보내는 LED·링·디스플레이·페이더 메시지는 전부 MC 모드 주소 체계를 전제로 하기 때문에, MC 모드가 아니면 오작동이 확인되었으며, 모터라이즈 페이더가 이상 작동하므로 사용하지 마십시오.

### 3-2. 프로그램 설치

1. 다운로드한 `xtouch_show` 폴더를 사용자 홈 디렉토리(`~/xtouch_show`)에 위치시킵니다.
> **주의:** `iCloud Drive`, `OneDrive`, `Dropbox`, `Google Drive`, `바탕화면`, `문서` 폴더 내부에 두지 마세요. macOS 권한 제한으로 인해 로그인 시 자동 실행이 작동하지 않으며, 설치 스크립트가 해당 위치에서는 실행을 거부합니다.


2. 터미널(Terminal)을 엽니다.
3. 아래 설치 명령어를 실행합니다:

```zsh
bash ~/xtouch_show/install.sh

```

4. **설치 스크립트가 묻고 하는 일:**
* Python 3 환경 확인 및 가상환경(`.venv`) 생성 후 필요 라이브러리(`python-rtmidi`, `sounddevice`, `numpy`)를 설치합니다. 이후 실행에서는 `requirements.txt`가 바뀐 경우에만 다시 설치합니다.
* 설정 파일(`config.json`)이 없으면 **설정 위저드**를 실행합니다. 이미 있으면 **"Run the settings wizard again?"**(기본값 **N**)을 묻고, 이어서 **"Measure the room noise for the noise gate?"**(기본값 **N**)를 묻습니다. 위저드를 방금 실행한 경우에는 위저드가 이미 측정을 제안하므로 이 질문은 건너뜁니다.
* `config.json`에 오류가 없는지 확인합니다. 오류가 있으면 내용을 알려 주고, 실행 중인 쇼를 건드리지 않은 채 멈춥니다.
* 런처 앱(`XTouchShow.app`)을 생성합니다. 이 앱이 자동 실행 시 마이크 권한을 담당합니다.
* 처음 설치할 때만 연결된 기기 목록을 보여 주고 기기 연결 테스트(LED 링 스윕)를 진행합니다. 이후 실행에서는 링 테스트를 건너뜁니다.
* **"Start the show automatically at login?"**(기본값 **Y**)을 묻습니다. **Y**로 답하면 로그인 시 **자동 실행되도록 등록**하고 현재 파일로 쇼를 즉시 (재)시작합니다. 첫 실행 시 마이크 권한 요청 팝업이 뜨면 [허용]을 선택해야 합니다. 이 팝업은 `XTouchShow.app`을 다시 만들어야 할 때(예: 폴더를 옮긴 경우)에만 다시 나타나며, 평소처럼 `install.sh`를 다시 실행할 때는 앱이 그대로 유지되므로 권한도 그대로 남습니다.

*자동 실행 질문에 **N**으로 답하면 자동 실행이 꺼진 상태로 남습니다. 이때는 `bash ~/xtouch_show/manual_start.sh`로 직접 실행합니다(3-4 참고).*

*터미널이 아닌 곳에서 실행하면 모든 질문은 기본값으로 처리됩니다.*

*직접 만든 아이콘을 쓰려면 icon.png(1024×1024 PNG)를 교체한 뒤 install.sh를 다시 실행하세요. macOS가 마이크 권한을 한 번 더 묻습니다.*



### 3-3. 설정 위저드

`config.json`이 없으면 설치 과정에서 설정 위저드가 자동으로 실행됩니다. 나중에 설정을 다시 잡고 싶다면 설치 명령을 다시 실행하고 **"Run the settings wizard again?"**에 **y**로 답하세요:

```zsh
bash ~/xtouch_show/install.sh

```

위저드가 끝나면 `install.sh`의 나머지 단계가 쇼를 다시 시작하므로 새 설정이 바로 반영됩니다.

대괄호 `[]` 안에 표시되는 기본값을 사용하려면 **Enter**를 누르면 됩니다.

| 설정 항목 | 기본값 | 설명 |
| --- | --- | --- |
| Mini MIDI 출력 포트 [`mini.midi_port_name`] | `"X-TOUCH MINI"` | 장치 번호를 선택하거나 이름을 입력합니다. |
| 오디오 입력 장치 [`audio_input_device`] | 시스템 기본 입력 | 내장 마이크 또는 커스텀 장치를 선택합니다. 두 컨트롤러가 공유합니다. |
| Mini On/Off 토글 버튼 [`mini.toggle_button`] | `A` | Layer A 또는 B 버튼 중 선택합니다. |
| Mini 버튼 LED 레벨 바 [`mini.buttons_enabled`] | `y` | 하단 버튼의 레벨 바 표시 여부를 설정합니다. |
| 방 소음 측정 여부 [`noise_gate_db`] | `n` (게이트 꺼짐) | 두 컨트롤러가 공유합니다. |
| X-Touch One 사용 여부 [`one.enabled`] | X-Touch One이 현재 연결되어 있으면 `y`, 아니면 `n` | `y`로 답하면 아래 MC 모드 질문으로 이어지고, `n`이면 건너뛰어 One을 꺼진 상태로 둡니다. |
| X-Touch One이 MC 모드로 설정되어 있나요? [`one.enabled`] | `n` | MC 모드가 아니면 쇼가 실행되는 동안 모터 페이더가 딸깍거립니다. 위에서 `y`로 답했더라도 여기서 `n`(기본값)으로 답하면 One은 꺼진 상태로 남고 아래 세 질문은 건너뜁니다. |
| One MIDI 출력 포트 [`one.midi_port_name`] | `"X-Touch One"`과 일치하는 첫 포트 | 장치 번호를 선택하거나 이름을 입력합니다. |
| One 토글 버튼 [`one.toggle_button`] | `Scrub` | 33개 LED 버튼 이름(`BPM`, `F1`-`F6`, `Marker`, `Play`, `Scrub` 등) 중 하나 또는 MIDI 노트 번호. |
| One 디스플레이 텍스트 [`one.display_text`] | `LED ON` | 최대 12자, 대문자로 표시됩니다. `W`는 `U`처럼 보이고 `M`, `K`, `X`는 읽기 어렵거나 헷갈리므로 가능하면 피하세요. |

### 3-4. 수동 실행 및 권한 확인

자동 실행 질문에 **N**으로 답했거나, 로그를 보며 문제를 살펴보려는 경우에는 터미널에서 직접 실행합니다:

```zsh
bash ~/xtouch_show/manual_start.sh

```

자세한 디버그 로그를 보려면 `-v`를 붙입니다:

```zsh
bash ~/xtouch_show/manual_start.sh -v

```

*(같은 MIDI 기기를 두고 충돌하므로 한 번에 하나만 실행할 수 있습니다. 자동 실행이 등록되어 있으면 `manual_start.sh`는 실행을 거부합니다. `bash ~/xtouch_show/uninstall.sh`로 자동 실행을 먼저 중지하고, 나중에 `bash ~/xtouch_show/install.sh`로 다시 등록하세요.)*

마이크는 컨트롤러가 하나라도 연결되고 쇼가 켜진 뒤에만 열립니다. 쇼를 끄거나 마지막 컨트롤러를 뽑으면 로그에 `audio input closed`가 찍히고 마이크가 해제되어, 쇼가 다시 켜질 때까지 메뉴 막대의 주황색 마이크 표시가 꺼집니다. 특정 컨트롤러에 대한 로그 줄에는 `[mini]` 또는 `[one]` 접두어가 붙습니다.

### 3-5. 동작 확인 및 조정

1. 음악을 재생하여 LED 링이 즉시 반응하는지 확인합니다.
2. **민감도 조절:**
* 바가 너무 작게 움직일 경우: 마이크를 가깝게 두거나 `config.json`에서 `min_db`를 `-50` 또는 `-40`으로 올립니다.
* 바가 너무 꽉 찰 경우: `min_db`를 `-70` 정도로 낮춥니다.
* 조용한 상태에서도 LED가 움직인다면 노이즈 게이트를 설정합니다. 조용한 방에서 아래 명령을 실행하고 **"Measure the room noise for the noise gate?"**에 **y**로 답하세요:
```zsh
bash ~/xtouch_show/install.sh

```


*(측정 중에는 방을 완전히 조용히 유지해야 합니다. 측정이 끝나면 쇼가 새 게이트 값으로 다시 시작됩니다.)*

### 3-6. DAW와 함께 사용하기

MC 모드에서는 연결된 컨트롤러의 모든 LED를 DAW가 직접 그립니다. 그래서 쇼가 같은 LED를 사용하면 DAW가 만들어 둔 화면이 지워집니다. 이를 위해 프로그램은 컨트롤러마다 DAW가 쓸 MIDI 장치를 따로 만들어 줍니다.

프로그램이 실행되는 동안 **활성화된** 컨트롤러마다 가상 MIDI 장치(입력·출력)가 만들어집니다: Mini는 **`X-TOUCH MINI SHOW`**, One은 **`X-TOUCH ONE SHOW`**. DAW의 컨트롤 서피스 설정에서 MIDI 입력과 출력을 **실제 컨트롤러 대신 이 장치로** 지정하세요. DAW의 장치 목록에서는 실제 컨트롤러 바로 옆에 표시됩니다. 프로그램이 양방향 트래픽을 모두 중계하므로 다음과 같이 동작합니다:

* **쇼가 꺼져 있을 때**: DAW는 평소와 똑같이 동작합니다. 노브·버튼·페이더/엔코더 조작이 DAW에 전달되고, DAW가 보내는 LED·모터 페이더·디스플레이 숫자·SysEx가 컨트롤러에 그대로 전달됩니다.
* **쇼가 켜져 있을 때**: 쇼가 해당 컨트롤러의 LED(링/바, One은 디스플레이도)를 가져갑니다. DAW가 보낸 LED 메시지는 기억만 하고 보내지 않으며, 나머지(Mini의 모터 페이더·디스플레이 숫자, One의 SysEx)는 계속 전달됩니다.
* **쇼가 꺼지는 순간**(토글 버튼으로 끄거나, 디스플레이가 잠자기에 들어가거나, 프로그램이 종료될 때): LED가 DAW가 마지막으로 설정한 상태로 정확히 되돌아갑니다.

참고:

* 각 가상 장치는 **프로그램이 실행 중이고 해당 컨트롤러가 활성화되어 있을 때만 존재**합니다. 자동 실행을 켜 두는 것을 권장합니다. 그렇지 않으면 쇼가 실행되지 않는 동안 DAW에서 장치가 사라집니다.
* **쇼를 켜고 끄는 토글 버튼은 DAW로 전달되지 않습니다**(쇼가 사용합니다). Mini는 설정한 Layer 버튼, One은 그 버튼의 프레스 노트(들)가 해당합니다. 나머지 버튼·노브·페이더/엔코더는 평소대로 DAW에 전달됩니다. 그 버튼을 DAW에서 써야 한다면 `mini.toggle_button` 또는 `one.toggle_button`을 바꾸세요.
* DAW를 실제 컨트롤러에 그대로 연결해도 됩니다. 모든 기능이 정상 동작하지만, 쇼가 DAW의 LED 상태를 알 수 없으므로 쇼가 멈출 때 LED는 그냥 꺼지고 DAW가 다시 그릴 때까지 꺼진 채로 남습니다.
* 특정 가상 장치를 아예 만들지 않으려면 `config.json`의 해당 `mini`/`one` 섹션에서 `"daw_proxy": false`로 설정하세요.

### 3-7. X-Touch One에 대하여

X-Touch One은 전반적으로 Mini와 같은 방식(MC 모드, 핫플러그, DAW 프록시, 디스플레이 꺼짐 시 일시 중단)으로 동작하지만, 엔코더가 8개가 아니라 1개이고 8개 링 대신 12자 디스플레이가 있어 음악을 표시하는 방식이 다릅니다:

* **BPM(피크 표시등)**은 최근 몇 초간의 최소-최대 범위를 기준으로 한 레벨이 일정 임계값을 넘을 때마다 짧게 켜지며, 짧은 피크도 보이도록 잠시 켜진 상태를 유지합니다.
* **주파수 대역 줄 세 개**가 Mini의 바와 같은 방식(한 프레임당 한 칸씩 줄어듦)으로 좌→우로 채워지며, Mini의 8개 링이 8개 대역을 보여주는 것과 같은 방식으로 각 줄이 하나의 주파수 대역을 표시합니다: **F1 줄**(F1-F6, 6개 LED)은 고음 대역(4kHz, 8kHz), **Marker 줄**(Marker부터 Solo까지, 7개 LED)은 중음 대역(250Hz-2kHz), **Rewind 줄**(Rewind부터 Record까지, 5개 LED)은 저음 대역(60Hz, 120Hz)을 표시합니다. 각 줄은 해당 대역에 속한 세부 대역의 평균이 아니라 가장 큰 값을 따라가므로, 세부 대역 하나가 크게 울려도 옆의 조용한 대역 때문에 묽어지지 않습니다. 또한 각 줄은 최근 몇 초간 그 대역 자체의 최소-최대 범위를 기준으로 자동 조정됩니다 — Mini 하단 상대 레벨 바와 같은 방식을 전체 레벨 대신 대역별로 적용한 것으로, LED가 5~7개뿐인 줄에서도 그 부분이 조용하든 크든 계속 움직입니다. 설정한 토글 버튼이 속한 줄에서는 그 버튼이 채우기 순서에서 제외됩니다.
* **다섯 번째 줄**은 Channel Mute, Channel Solo, Channel Record 버튼을 왼쪽부터 오른쪽 순서로 한 번에 한 개씩, 전체 상대 레벨(아래 여섯 번째 바와 Mini 하단 바가 쓰는 것과 같은 값)에 따라 켭니다 — 특정 주파수 대역이 아닌 전체 레벨을 따라갑니다.
* **여섯 번째 상대 레벨 바**는 기기에서 한 줄로 나란히 배치된 Bank, Channel, Up/Left/Zoom/Right/Down 버튼을 재사용합니다: 5단으로 묶어 전체 상대 레벨(Mini 하단 바와 One 엔코더 링이 쓰는 것과 같은 값)에 따라 아래 단부터 위로 채웁니다. 아래부터 위로: Down; Left+Zoom+Right 함께; Up; Channel Left+Right 함께; Bank Left+Right 함께 — 같은 단에 속한 버튼은 항상 함께 켜지고 함께 꺼집니다.
* **엔코더 링 하나**가 Mini의 8개 링 중 하나와 똑같이 절대 레벨을 표시합니다.
* **기기 자체의 레벨 미터**도 엔코더 링과 별개로 전체 상대 레벨에 따라 켜집니다.
* **12자 디스플레이**는 쇼가 켜져 있는 동안 `one.display_text`(기본값 `"LED ON"`, 대문자로 강제 변환, 최대 12자)를 표시하고 꺼져 있으면 비어 있습니다. 텍스트가 화면보다 길면 스크롤됩니다: `one.display_scroll_step_s`초마다 한 칸씩 오른쪽으로 이동하다가 화면을 다 지나가면 다시 왼쪽부터 시작합니다(`one.display_scroll`을 `false`로 하면 스크롤 없이 왼쪽 정렬로 고정 표시). 글자는 7세그먼트 모양으로 표시되어 `W`는 `U`처럼 보이고, `M`, `K`, `X`는 읽기 어렵거나 헷갈리므로 가능하면 피하세요.
* **토글 버튼**(기본값 `Scrub`, 33개 LED 버튼 중 아무거나 가능)이 쇼를 켜고 끕니다. 쇼가 실행 중이면 LED가 소프트웨어적으로 0.5초마다 깜빡입니다(기기 자체의 하드웨어 깜빡임 속도는 검증되지 않아 프로그램이 직접 제어합니다).
* **쇼에서 사용하지 않는 것:** Master LED — 쇼가 이 LED를 켜지 않습니다.
* **두 컨트롤러 함께 사용:** Mini와 One은 동시에 실행할 수 있으며, 각자 독립적으로 핫플러그됩니다. ON/OFF 상태, 마이크, 설정 파일은 하나뿐입니다 — 어느 컨트롤러의 버튼으로 쇼를 켜고 꺼도 둘 다 함께 전환됩니다.

---

## 4. 설정 파일 설명 (`config.json`)

컨트롤러마다 `"mini"`, `"one"` 섹션이 따로 있고, 나머지는 두 컨트롤러가 공유합니다. X-Touch One 지원 이전의 `config.json`(평평한 `midi_port_name`, `toggle_button`, `buttons_enabled`, `daw_proxy`, `daw_proxy_name` 키)도 그대로 읽히며, 프로그램이 자동으로 `"mini"` 섹션으로 옮겨 줍니다. 다만 설정 위저드는 항상 아래 구조로 저장합니다.

### `mini` 섹션 (X-Touch Mini)

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `mini.enabled` | `true` | Mini를 사용할지 여부입니다. `false`로 두면 연결되어 있어도 무시합니다. |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI 포트 검색 문자열입니다. |
| `mini.toggle_button` | `"A"` | 토글 스위치 버튼 (`"A"` 또는 `"B"`). |
| `mini.buttons_enabled` | `true` | 버튼 LED 레벨 바 활성화 여부입니다 (상단 = 절대 레벨, 하단 = 상대 레벨). `false`이면 버튼 LED를 건드리지 않습니다. |
| `mini.daw_proxy` | `true` | DAW가 컨트롤러 대신 사용할 가상 MIDI 장치를 만듭니다(3-6 참고). 쇼가 멈출 때 DAW가 그려 둔 LED 상태를 복원해 줍니다. `false`로 두면 가상 장치를 만들지 않습니다. |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | DAW에 표시되는 가상 장치의 이름입니다. |

### `one` 섹션 (X-Touch One)

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `one.enabled` | `false` | One을 사용할지 여부입니다. `false`로 두면 연결되어 있어도 무시합니다. |
| `one.midi_port_name` | `"X-Touch One"` | MIDI 포트 검색 문자열입니다. |
| `one.toggle_button` | `"Scrub"` | 33개 LED 버튼 이름(`BPM`, `Channel Record`, `Channel Solo`, `Channel Mute`, `Channel Select`, `Bank Left/Right`, `Channel Left/Right`, `F1`-`F6`, `Marker`, `Nudge`, `Cycle`, `Drop`, `Replace`, `Click`, `Solo`, `Rewind`, `Forward`, `Stop`, `Play`, `Record`, `Up`, `Down`, `Left`, `Right`, `Zoom`, `Scrub`) 중 하나(대소문자 구분 없음) 또는 MIDI 노트 번호. 값이 올바르지 않으면 경고와 함께 `"Scrub"`으로 대체됩니다. |
| `one.daw_proxy` | `true` | `mini.daw_proxy`와 동일하며 One용입니다(3-6 참고). |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | DAW에 표시되는 가상 장치의 이름입니다. |
| `one.display_text` | `"LED ON"` | 쇼가 켜져 있는 동안 12자 디스플레이에 표시됩니다(3-7 참고). 대문자로 강제 변환되고 최대 12자로 잘립니다. |
| `one.display_scroll` | `true` | 텍스트가 화면보다 길면 스크롤합니다. `false`이면 스크롤 없이 왼쪽 정렬로 고정 표시합니다. |
| `one.display_scroll_step_s` | `0.3` | 한 칸씩 스크롤되는 간격(초)입니다. |

### 공유 설정

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `audio_input_device` | `"default"` | 오디오 입력 장치명입니다. |
| `frame_rate` | `30` | 초당 LED 재생 빈도(FPS)입니다. |
| `decay_per_frame` | `1` | 한 프레임에 바/링이 내려갈 수 있는 최대 단계 수입니다. |
| `show_enabled_at_start` | `true` | 프로그램이 시작될 때 쇼를 자동으로 켭니다. |
| `show_when_display_off_on_ac` | `false` | 전원 어댑터를 연결한 상태에서 디스플레이가 잠자기일 때도 쇼를 계속 실행합니다. 기본값은 꺼짐이며, LED가 꺼지고 화면이 다시 켜질 때까지 마이크도 닫힙니다. 화면이 꺼져도 쇼를 유지하려면 `true`로 설정하세요. |
| `show_when_display_off_on_battery` | `false` | 배터리 상태에서 디스플레이가 잠자기일 때도 쇼를 계속 실행합니다. 기본값은 꺼짐이며, LED가 꺼지고 화면이 다시 켜질 때까지 마이크도 닫혀 전력을 아낍니다. 배터리에서도 쇼를 유지하려면 `true`로 설정하세요. |
| `bar_max_fall_s` | `2.0` | 다이내믹 레인지 상한이 내려가는 시간 상수(초)입니다. Mini의 상대 레벨 바와 X-Touch One의 주파수 대역 줄 세 개가 모두 함께 사용합니다. |
| `bar_min_rise_s` | `4.0` | 다이내믹 레인지 하한이 올라가는 시간 상수(초)입니다. 같은 네 개의 자동 범위 조정 트래커가 함께 사용합니다. |
| `band_centers_hz` | `60`–`8000` | Mini의 8개 엔코더 LED 대역의 중심 주파수입니다. |
| `band_gains` | `[1.0, ...]` | 주파수 대역별 개별 게인 값입니다. |
| `min_db` / `max_db` | `-60` / `0` | 다이내믹 레인지의 하한과 상한 보정값(dB)입니다. |
| `fft_size` | `4096` | 분석 윈도 크기입니다. 값이 클수록 저역 정밀도가 높아집니다. |
| `level_release` | `0.7` | 감쇠 스무딩 계수(0–1)입니다. 값이 클수록 천천히 내려갑니다. |
| `noise_gate_db` | `null` | `null`은 **노이즈 게이트 OFF**(모든 소리가 LED에 전달됨)입니다. 숫자를 넣으면 dB 임계값으로 게이트가 켜져, 이보다 조용한 입력은 무음으로 간주되어 LED가 꺼집니다. `install.sh`의 방 소음 측정이 이 값을 대신 기록해 주며, 시끄러운 방에서는 값을 올리고(예: `-35`) 조용한 부분이 잘리면 낮추면 됩니다(예: `-55`). 다시 `null`로 되돌리면 게이트가 꺼집니다. |
| `noise_gate_margin_db` | `4.0` | 방 소음 측정과 설정 위저드가 측정한 방 소음에 더하는 여유값입니다. |

모든 설정은 시작할 때만 읽습니다. `config.json`을 손으로 고친 뒤에는 아래 명령어로 안전하게 적용할 수 있습니다. 파일을 검사한 뒤 쇼를 다시 시작하며, 오류가 있으면 알려 주고 실행 중인 쇼는 그대로 둡니다:

```zsh
bash ~/xtouch_show/install.sh

```

`bash ~/xtouch_show/manual_start.sh`로 직접 실행 중이라면 `Ctrl+C`로 멈춘 뒤 다시 실행하세요.

---

## 5. 문제 해결 (Troubleshooting)

* **`MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` 발생 시**: USB 연결을 확인하고 다른 DAW 프로그램이 MIDI 포트를 점유하고 있는지 확인하세요. 컨트롤러를 하나만 갖고 있다면 나머지 하나에 대해서는 정상적으로 나타나는 메시지입니다 — `config.json`에서 그 컨트롤러의 `enabled`를 `false`로 두면 더 이상 나타나지 않습니다.
* **LED 링/바가 반응하지 않음**: 기기의 **MC MODE** 상태를 확인하세요. DAW가 MIDI를 점유하고 있다면 DAW를 끄거나, DAW의 MIDI 입력·출력을 `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` 장치로 바꾸세요(3-6 참고).

> [!WARNING]
> **모터 페이더가 딸깍거림(따깍따깍)**: 컨트롤러가 이 쇼에서 테스트된 두 퍼스낼리티(MC Standard, MC Logic) 중 하나로 설정되어 있지 않은 상태입니다. 둘 중 하나로 MC 모드를 설정하세요(3-1 참고) — MC 모드가 아니면 오작동이 확인되었으므로, 그 외의 모드에서는 이 쇼를 사용하지 마십시오.

* **DAW에서 `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` 장치가 보이지 않음**: 이 장치는 프로그램이 실행 중이고 해당 컨트롤러가 활성화되어 있을 때만 존재합니다. 프로그램을 실행한 뒤(자동 실행 또는 `bash ~/xtouch_show/manual_start.sh`) `logs/xtouch_show.log`에 `[mini] DAW proxy ready` / `[one] DAW proxy ready`가 있는지 확인하세요. `DAW proxy unavailable`이 보이면 가상 포트를 만들지 못한 경우이고, 해당 섹션의 `"daw_proxy": false`는 장치를 일부러 끈 설정입니다. 확인 후 DAW에서 MIDI 장치를 다시 검색하세요.
* **토글 버튼 LED가 켜지지 않음**: MIDI 경로가 잡히지 않은 상태입니다. 로그에 `[mini] MIDI connected` / `[one] MIDI connected`가 있는지 확인하세요.
* **프로그램은 돌아가는데 바가 0에 고정됨**: 마이크 권한(`시스템 설정 → 개인정보 보호 및 보안 → 마이크`)에서 **Terminal** 또는 **XTouchShow**가 허용되어 있는지 확인하세요. 자동 실행이 꺼진 상태에서 `bash ~/xtouch_show/manual_start.sh -v`로 실행하면 실시간 레벨을 볼 수 있습니다 (`gate=off`는 노이즈 게이트가 설정되지 않은 상태, 음악이 나오는데 `gate=False`이면 게이트가 너무 높은 상태입니다).
* **음악이 없는데 바가 움직임**: 기본값인 노이즈 게이트 OFF 상태라 방 안 소음이 LED까지 전달되는 것입니다. 조용한 방에서 `bash ~/xtouch_show/install.sh`를 실행하고 방 소음 측정 질문에 **y**로 답해 게이트를 켜거나, `config.json`의 `noise_gate_db`를 `-45` 같은 값으로 설정하세요.
* **음악에는 반응하지 않고 기침 같은 큰 소리에만 반응함**: 노이즈 게이트가 너무 높습니다. 음악과 대화를 멈춘 상태에서 `bash ~/xtouch_show/install.sh`를 실행해 방 소음 측정을 다시 하거나, `config.json`의 `noise_gate_db`를 낮추고(예: `-40`) 필요하면 `null`로 되돌려 게이트를 끄세요.
* **주황색 마이크 표시가 꺼지지 않음**: 쇼는 컨트롤러가 하나라도 연결되어 있고 쇼가 켜져 있을 때만 마이크를 유지합니다. 쇼를 끄거나 마지막 컨트롤러를 뽑으면 약 2초 안에 표시가 꺼집니다. 그래도 켜져 있으면 다른 앱이 마이크를 사용 중이거나, 수동으로 실행한 두 번째 인스턴스가 돌아가고 있는 것입니다.
* **오랜 시간이 지난 뒤 쇼가 반응하지 않음 (LED가 멈추고, 토글 버튼이 먹지 않으며, 마이크 표시가 켜진 채로 남음)**: 프로그램이 약 30초 안에 스스로 다시 시작하므로 잠시 기다리면 됩니다. `logs/xtouch_show.log`에서 `stalled`를 찾아 확인할 수 있습니다. 같은 일이 계속 반복되면 `bash ~/xtouch_show/install.sh`를 실행하세요.
* **바가 너무 작거나 꽉 참**: `config.json`의 `min_db`를 조절하세요 (작게 움직이면 `-50` 또는 `-40`, 꽉 차면 `-70`).
* **고음역이 잘 반응하지 않음**: `band_gains`의 고역 값을 올리세요 (예: `1.5`, `2.0`).
* **종료 후에도 링/디스플레이가 꺼진 채로 남음**: 정상 동작입니다. MC 모드의 LED는 호스트가 MIDI를 보낼 때만 갱신됩니다. DAW가 `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` 장치로 컨트롤러를 제어하고 있다면, 대신 DAW가 마지막으로 설정한 상태로 되돌아갑니다(3-6 참고).
* **X-Touch One 디스플레이 텍스트가 이상하게 보임**: `W`는 `U`처럼 보이고, `M`, `K`, `X`는 이 디스플레이의 7세그먼트 폰트로는 읽기 어렵거나 헷갈립니다 — `one.display_text`를 다른 문구로 바꿔보세요.
* **자동 실행은 되는데 바가 0에 고정됨**: 시스템 마이크 설정에서 **XTouchShow**가 허용되어 있는지 확인하세요.
* **자동 실행이 시작되지 않음**: `launchctl print gui/$(id -u)/com.castika.xtouchshow`로 상태를 확인하거나 `logs/xtouch_show.log`를 읽어 보세요.
* **로그에 `Operation not permitted`가 보임**: 폴더가 보호된 경로(`바탕화면`, `문서`, 클라우드 동기화 폴더)에 있습니다. `~/xtouch_show`로 옮긴 뒤 `bash ~/xtouch_show/install.sh`를 다시 실행하세요. 설치 스크립트는 이런 위치에서는 실행을 거부합니다.
* **자동 실행 삭제 및 쇼 중지 명령어** (다시 켜려면 `bash ~/xtouch_show/install.sh`):
```zsh
bash ~/xtouch_show/uninstall.sh

```



---

## 6. 프로젝트 파일 구조

```text
xtouch_show/
├── xtouch_show.py    # 메인 엔진 스크립트 (MIDI, 음향 분석, 설정 위저드)
├── test_show.py      # 하드웨어 없이 동작 로직을 검증하는 도구
├── requirements.txt  # Python 의존성 목록
├── install.sh        # 설치, 설정 변경, 변경 사항 적용 (필요한 명령은 이것 하나뿐)
├── uninstall.sh      # 자동 실행 삭제 및 쇼 중지 스크립트
├── manual_start.sh   # 터미널 수동 실행 스크립트
├── icon.png          # 앱 아이콘 원본 (1024x1024 PNG), XTouchShow.app 아이콘으로 사용
├── README.md         # 이 가이드
├── LICENSE           # MIT 라이선스 전문
├── .gitignore        # 버전 관리에서 제외되는 파일 목록 (.venv, logs, config.json 등)
├── config.json       # 실행 설정 파일 (설정 위저드 실행 시 생성)
├── XTouchShow.app    # 자동 실행용 런처 앱 (install.sh가 생성, 마이크 권한 담당)
├── .venv/            # 필요한 라이브러리가 설치된 Python 환경
└── logs/             # 실행 로그

```

`config.json`, `XTouchShow.app`, `.venv/`, `logs/`는 `install.sh`와 설정 위저드가 사용자의 Mac에서 만들어 주는 항목이라 내려받은 소스에는 들어 있지 않습니다.

*License: MIT*
---

---

# XTouchShow - 日本語ガイド

Behringer **X-Touch Mini / X-Touch One** コントローラー用の音楽連動型 LED ライトショープログラムです。どちらか一方（または両方）を接続して音楽を再生すると、マイクで拾った音が解析され、コントローラーの LED に表示されます。Mini では 8 つのエンコーダー LED リングに 8 帯域スペクトラムを、16 個のボタンに全体の音量レベルを 2 本のバーで表示します。One ではボタン LED バー 2 本とエンコーダーリング 1 個に全体の音量レベルを、12 文字ディスプレイにスクロールメッセージを表示します。各コントローラーに設定可能なボタンがあり、それでショーの ON/OFF を切り替えます。どちらのボタンで切り替えても両方が連動して切り替わります。

どちらのコントローラーも単体で動作し、同時に両方使うこともできます。単一の Python ファイルで動作し、個別のアプリをインストールする必要はありません。**macOS 専用**です。

本ガイドは、**依存パッケージがインストールされていないクリーンな Mac** を前提としています。セットアップには約 10–20 分かかります。

---

## 1. 主な動作

| 状況 | 動作 |
|---|---|
| プログラム起動 / 機器接続 | ショー ON（デフォルト）。8 つの LED リングが音楽に合わせてスペクトラムバーとして動き始めます。 |
| ショー実行中の上段ボタン (1–8) | 左から右へ点灯する絶対音量レベルバーです。 |
| ショー実行中の下段ボタン (9–16) | 直近数秒間の最小〜最大範囲を基準とした相対音量レベルバーです。音圧の高い音源でもダイナミックに動きます。 |
| ノブ操作およびその他のボタン入力 | 無視されます。LED ショーは維持され、MIDI 本来の機能も正常に動作します。 |
| 音楽が流れていない静かな状態 | デフォルトではノイズゲートが OFF になっているため、微小な室内ノイズで LED が動くことがあります。`install.sh` を実行し、室内ノイズ測定の質問に **y** と答えるとゲートを有効化できます。 |
| フェーダー (Fader) | 感度（バーの高さ）を調整します。一番下まで下げると、バックグラウンドのショーは維持されたまま LED 出力のみが OFF になります。 |
| Mini の Layer A / B ボタン（設定可能） | Mini のショーの ON/OFF を切り替えます（`mini.toggle_button` で設定）。<br>• **LED 消灯**: ショー OFF<br>• **点滅**: ショー実行中 |
| One の Scrub ボタン（設定可能） | ショーの ON/OFF を切り替えます（`one.toggle_button` で設定）。<br>• **LED 消灯**: ショー OFF<br>• **ソフトウェア点滅（0.5 秒周期）**: ショー実行中<br>ON/OFF 状態は 1 つだけなので、どちらのボタンで切り替えても両方が連動します。 |
| X-Touch One 接続時 | BPM ボタンが、直近数秒間の最小〜最大範囲を基準とした音量が一定のしきい値を超えるたびに短く点灯するピークインジケーターとして動作し、瞬間的なピークも見えるよう少しの間点灯を保持します。ボタン 3 列が左から右へ点灯し、それぞれ 1 つの周波数帯域を表示します（Mini の 8 個のリングが 8 帯域を表示するのと同じ考え方です）: F1~F6（6 個の LED）は高音域（4kHz、8kHz）、Marker~Solo（7 個の LED）は中音域（250Hz~2kHz）、Rewind~Record（5 個の LED）は低音域（60Hz、120Hz）を表示します。各列は、その帯域に含まれるサブ帯域の平均ではなく、いちばん大きいサブ帯域に追従し、さらに直近数秒間のその帯域自体の最小〜最大範囲を基準にスケーリングされます — 上記の Mini の下段相対レベルバーと同じ自動レンジ調整の考え方を、全体音量ではなく周波数帯域ごとに適用したもので、ミックスのその部分が静かでも大きくても各列が動き続けます。5 番目の列は Channel Mute、Channel Solo、Channel Record を左から右の順に 1 個ずつ、全体の相対レベルに応じて点灯します。6 番目のバーは Bank、Channel、Up/Left/Zoom/Right/Down の各ボタンを 5 段に分け、同じ全体の相対レベルに応じて下段から上段へ点灯します（下から順に Down、Left+Zoom+Right、Up、Channel Left+Right、Bank Left+Right）。エンコーダーリング 1 個が絶対レベルを表示し、本体自体のレベルメーターも全体の相対レベルに応じて点灯します。12 文字ディスプレイが `one.display_text`（デフォルト `"LED ON"`）をスクロール表示します。Master LED はショーで使用しません。 |
| 機器の切断と再接続 | 各コントローラーが互いに独立して自動的に再接続されます。 |
| DAW と併用する場合 | DAW の MIDI 入力・出力を仮想デバイス `X-TOUCH MINI SHOW` および/または `X-TOUCH ONE SHOW` に指定します（3-6 参照）。ショーが OFF の間は DAW が通常どおり動作し、ショーが ON になると LED をショーが使い、ショーが止まると DAW の LED 状態がそのまま復元されます。 |
| ディスプレイのスリープ（画面だけが消え、Mac は起動中） | 電源アダプター接続時もバッテリー駆動時も、画面が再び点くまでショーは停止し、マイクも閉じます（`show_when_display_off_on_ac` と `show_when_display_off_on_battery`、どちらもデフォルトは OFF）。Mini の Layer LED は点滅し続けるため、ショー自体は ON のままです。その電源状態で画面が消えてもショーを続けたい場合は、各項目を `true` に設定してください。 |

Mini の LED リング（左→右）に対応する周波数帯域: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

マイクはコントローラーが 1 台でも接続されていて、かつショーが ON のときだけ開きます。最後のコントローラーを抜くかショーを切るとオーディオ入力が閉じ、メニューバーのオレンジ色のマイク表示も消えます。

Mac がスリープから復帰すると、ショーは自動的に初期化し直します。接続中の各コントローラーに MC モードコマンドを送り、LED を復元してからマイクを開き直すため、手動で再起動する必要はありません。

**X-Touch One のディスプレイについて:** 文字は 7 セグメント表示の形になります。`W` は `U` のように見え、`M`、`K`、`X` は読みにくいか他の文字と紛らわしいため、`one.display_text` ではできるだけ避けてください。デフォルトの `"LED ON"` ははっきり表示されます。

---

## 2. 必要条件

| 項目 | 備考 |
|---|---|
| Mac (macOS 12 以降) | 基本的なインストール手順に管理者権限は不要です。 |
| Behringer X-Touch Mini および/または X-Touch One + USB ケーブル | Mac の USB ポートに直接接続します。どちらか一方だけでも動作し、両方を同時に使うこともできます。 |
| `xtouch_show` フォルダ | 以下のファイル構成セクションを参照してください。 |
| オーディオマイク | Mac 内蔵マイクで問題なく動作します。外付け・USB マイクもサポートしています。 |

Python 3 は macOS Command Line Tools に含まれています。未インストールの場合は、インストールスクリプトが自動的に案内します。

---

## 3. インストールガイド

初めてインストールする場合は、コントローラーを MC モードに設定したうえで (3-1)、以下のコマンドを 1 つ実行し、表示される質問に答えるだけです。角括弧 `[]` 内のデフォルト値を使う場合は **Enter** キーを押します。

```zsh
bash ~/xtouch_show/install.sh
```

インストール、設定変更、変更の反映に必要なコマンドはこれ 1 つだけです。オプションはなく、必要なことはスクリプトが質問します。いつでも実行し直せます。

### 3-1. コントローラーを MC モードに設定

**X-Touch Mini:**
1. USB ケーブルを抜きます。
2. 本体左下の **MC** ボタンを押しながら、USB ケーブルを Mac に再接続します。
3. 右上の **MC MODE** LED が点灯したままになったら、ボタンを離します。

**X-Touch One:** Behringer X-Touch One のマニュアルに記載されたボタン操作で同様に MC モードに設定してください（ファームウェアによっては物理的な MC モードスイッチ/メニューがある場合もあります）。

このショーは X-Touch One ファームウェアバージョン 1.10 でテスト済みです。

> [!WARNING]
> **必須の設定です:** このショーは MC モードの 2 つのパーソナリティ、**MC Standard** と **MC Logic** を対象に作られ、実際にテスト済みです — どちらも正常動作が確認されており、F1–F6 列のメッセージは両方のパーソナリティのノート番号を同時に送るようになっているため、どちらを選んでも問題なく動作します（本体側で選択）。
> この 2 つ以外のモードは非対応です — 本体に他の MC パーソナリティがあればそれも、そして Behringer が「MIDI Send CC」「MIDI Send Note」と呼ぶ（マニュアルでは「Standard MIDI mode」とも呼ばれる、MC モード内の「MC Standard」パーソナリティとは別物の）raw モードも同様です。
> このショーが送る LED・リング・ディスプレイ・フェーダーのメッセージはすべて MC モードのアドレス体系を前提にしているため、MC モード以外では誤動作が確認されています。特にモーターフェーダーが異常な動作をしますので、MC モード以外ではこのショーを使用しないでください。

### 3-2. プログラムのインストール
1. ダウンロードした `xtouch_show` フォルダを**ユーザーのホームディレクトリー (`~/xtouch_show`)** に配置します。
   > **注意:** `iCloud Drive`、`OneDrive`、`Dropbox`、`Google Drive`、`デスクトップ`、`書類` フォルダ内には配置しないでください。macOS の権限制限により、ログイン時の自動起動が動作せず、インストールスクリプトもその場所では実行を拒否します。
2. **ターミナル (Terminal)** を開きます。
3. 以下のインストールコマンドを実行します:

```zsh
bash ~/xtouch_show/install.sh

```

4. **インストーラーが尋ねること・行うこと:**
* Python 3 環境を確認し、仮想環境 (`.venv`) を作成して必要なライブラリ (`python-rtmidi`, `sounddevice`, `numpy`) をインストールします。2 回目以降は `requirements.txt` が変更された場合のみ再インストールします。
* 設定ファイル (`config.json`) が存在しない場合は、**セットアップウィザード**を実行します。すでにある場合は **"Run the settings wizard again?"**（デフォルト **N**）と尋ね、続いて **"Measure the room noise for the noise gate?"**（デフォルト **N**）と尋ねます。ウィザードを実行した直後は、ウィザード自体が測定を提案するためこの質問は省略されます。
* `config.json` にエラーがないか確認します。問題があれば内容を表示し、実行中のショーに触れずに停止します。
* ランチャーアプリ (`XTouchShow.app`) を生成します。自動起動時のマイク権限はこのアプリが担当します。
* 初回インストール時のみ、接続されている機器の一覧を表示し、実機接続テスト (LED リングスイープ) を行います。2 回目以降はリングテストを省略します。
* **"Start the show automatically at login?"**（デフォルト **Y**）と尋ねます。**Y** と答えるとログイン時に**自動起動するよう登録**し、現在のファイルでショーをすぐに（再）起動します。初回起動時にマイク権限の確認ポップアップが表示されたら、**[許可]** を選択してください。このポップアップは `XTouchShow.app` を作り直す必要があるとき (フォルダを移動した場合など) にのみ再び表示され、通常どおり `install.sh` を再実行する場合はアプリがそのまま残るため、権限も維持されます。

*自動起動の質問に **N** と答えると自動起動は OFF のままになります。その場合は `bash ~/xtouch_show/manual_start.sh` で手動起動します (3-4 参照)。*

*ターミナル以外から実行した場合、すべての質問はデフォルト値で処理されます。*

*独自のアイコンを使うには icon.png (1024×1024 PNG) を差し替えて install.sh を再実行してください。macOS がマイク権限をもう一度尋ねます。*



### 3-3. セットアップウィザード

`config.json` がない場合、セットアップウィザードはインストールの一環として自動的に実行されます。後から設定をやり直したい場合は、インストールコマンドを再実行して **"Run the settings wizard again?"** に **y** と答えてください:

```zsh
bash ~/xtouch_show/install.sh

```

ウィザードが終わると `install.sh` の残りの手順がショーを再起動するため、新しい設定がすぐに反映されます。

角括弧 `[]` 内に表示されるデフォルト値を使用する場合は、**Enter** キーを押します。

| 設定項目 | デフォルト値 | 説明 |
| --- | --- | --- |
| Mini の MIDI 出力ポート [`mini.midi_port_name`] | `"X-TOUCH MINI"` | デバイス番号を選択するか、名前を入力します。 |
| オーディオ入力デバイス [`audio_input_device`] | システムデフォルト入力 | 内蔵マイクまたはカスタムデバイスを選択します。両方のコントローラーで共有します。 |
| Mini の On/Off トグルボタン [`mini.toggle_button`] | `A` | Layer A または B ボタンから選択します。 |
| Mini のボタン LED レベルバー [`mini.buttons_enabled`] | `y` | 下段ボタンのレベルバー表示の有効/無効を設定します。 |
| 室内ノイズを測定してノイズゲートを有効にするか [`noise_gate_db`] | `n`（ゲート OFF） | 両方のコントローラーで共有します。 |
| X-Touch One を有効にするか [`one.enabled`] | X-Touch One が現在接続されていれば `y`、そうでなければ `n` | `y` と答えると下の MC モードの質問に進み、`n` ならスキップして One は OFF のままになります。 |
| X-Touch One は MC モードに設定されていますか？ [`one.enabled`] | `n` | MC モードでない場合、ショー実行中にモーターフェーダーがカチカチと音を立てます。上で `y` と答えていても、ここで `n`（デフォルト）と答えると One は OFF のままとなり、下の 3 つの質問はスキップされます。 |
| One の MIDI 出力ポート [`one.midi_port_name`] | `"X-Touch One"` に一致する最初のポート | デバイス番号を選択するか、名前を入力します。 |
| One のトグルボタン [`one.toggle_button`] | `Scrub` | 33 個の LED ボタン名（`BPM`、`F1`-`F6`、`Marker`、`Play`、`Scrub` など）のいずれか、または MIDI ノート番号。 |
| One のディスプレイテキスト [`one.display_text`] | `LED ON` | 最大 12 文字、大文字で表示されます。`W` は `U` のように見え、`M`、`K`、`X` は読みにくいか紛らわしいため、できるだけ避けてください。 |

### 3-4. 手動実行と権限の確認

自動起動の質問に **N** と答えた場合や、ログを見ながら動作を確認したい場合は、ターミナルから直接実行します:

```zsh
bash ~/xtouch_show/manual_start.sh

```

詳細なデバッグログを見たい場合は `-v` を付けます:

```zsh
bash ~/xtouch_show/manual_start.sh -v

```

*(同じ MIDI 機器を奪い合うため、同時に実行できるのは 1 つだけです。自動起動が登録されていると `manual_start.sh` は起動を拒否します。まず `bash ~/xtouch_show/uninstall.sh` で自動起動を停止し、後で `bash ~/xtouch_show/install.sh` で登録し直してください。)*

マイクはコントローラーが 1 台でも接続され、ショーが ON になってから開きます。ショーを切るか最後のコントローラーを抜くとログに `audio input closed` が出てマイクが解放され、ショーが再び動くまでメニューバーのオレンジ色のマイク表示は消えます。特定のコントローラーに関するログ行には `[mini]` または `[one]` の接頭辞が付きます。

### 3-5. 動作確認と調整

1. 音楽を再生し、LED リングがすぐに反応することを確認します。
2. **感度調整:**
* バーの動きが小さすぎる場合: マイクを近づけるか、`config.json` の `min_db` を `-50` や `-40` に上げます。
* バーが振り切れすぎる場合: `min_db` を `-70` 程度に下げます。
* 静かな状態でも LED が動く場合はノイズゲートを設定します。静かな部屋で以下のコマンドを実行し、**"Measure the room noise for the noise gate?"** に **y** と答えてください:
```zsh
bash ~/xtouch_show/install.sh

```


*(測定中は室内を完全な静寂状態に保ってください。測定が終わると、新しいゲート値でショーが再起動します。)*

### 3-6. DAW と一緒に使う

MC モードでは接続中のコントローラーのすべての LED を DAW が描画します。そのためショーが同じ LED を使うと、DAW が作った表示が消えてしまいます。これを避けるため、プログラムはコントローラーごとに DAW 専用の MIDI デバイスを用意します。

プログラムの実行中は、**有効になっている**コントローラーごとに仮想 MIDI デバイス（入力・出力）が作られます: Mini には **`X-TOUCH MINI SHOW`**、One には **`X-TOUCH ONE SHOW`**。DAW のコントロールサーフェス設定で、MIDI 入力と出力を**実機の代わりにこのデバイス**に指定してください。DAW のデバイス一覧では実機のすぐ隣に表示されます。プログラムが双方向のデータをすべて中継するため、次のように動作します:

* **ショーが OFF のとき**: DAW はこれまでどおり動作します。ノブ・ボタン・フェーダー/エンコーダーの操作は DAW に届き、DAW が送る LED・モーターフェーダー・ディスプレイの数字・SysEx はコントローラーにそのまま届きます。
* **ショーが ON のとき**: ショーがそのコントローラーの LED（リング/バー、One はディスプレイも）を使います。DAW が送った LED メッセージは記憶されるだけで送られず、それ以外（Mini のモーターフェーダー・ディスプレイの数字、One の SysEx）はそのまま通過します。
* **ショーが OFF になった瞬間**（トグルボタンで消したとき、ディスプレイがスリープに入ったとき、プログラム終了時）: LED は DAW が最後に設定した状態へ正確に戻ります。

注意点:

* 各仮想デバイスは**プログラムが動いていて、かつそのコントローラーが有効になっている間だけ存在**します。自動起動を有効にしたままにすることをおすすめします。そうしないと、ショーが動いていない間は DAW からデバイスが消えます。
* **ショーを ON/OFF するトグルボタンは DAW に送られません**（ショーが使用します）。Mini は設定した Layer ボタン、One はそのボタンのプレスノート（複数の場合あり）が対象です。それ以外のボタン・ノブ・フェーダー/エンコーダーは通常どおり DAW に届きます。そのボタンを DAW で使いたい場合は `mini.toggle_button` または `one.toggle_button` を変更してください。
* DAW を実機に接続したままでも構いません。動作自体は問題ありませんが、ショーは DAW の LED 状態を知ることができないため、ショーが止まると LED は単に消灯し、DAW が描き直すまで消えたままになります。
* 特定の仮想デバイスをまったく作りたくない場合は、`config.json` の該当する `mini`/`one` セクションで `"daw_proxy": false` に設定してください。

### 3-7. X-Touch One について

X-Touch One は全体的な動作（MC モード、ホットプラグ、DAW プロキシ、ディスプレイスリープ時の一時停止）は Mini と同じですが、エンコーダーが 8 個ではなく 1 個、8 個のリングの代わりに 12 文字ディスプレイがあるため、音楽の表示方法が異なります:

* **BPM（ピークインジケーター）**は、直近数秒間の最小〜最大範囲を基準とした音量が一定のしきい値を超えるたびに短く点灯し、瞬間的なピークも見えるよう少しの間点灯を保持します。
* **周波数帯域の列 3 本**が、Mini のバーと同じ方式（1 フレームにつき 1 段ずつ減少）で左から右に点灯し、Mini の 8 個のリングが 8 帯域を表示するのと同じ考え方で、それぞれの列が 1 つの周波数帯域を表示します: **F1 列**（F1-F6、6 個の LED）は高音域（4kHz、8kHz）、**Marker 列**（Marker から Solo まで、7 個の LED）は中音域（250Hz-2kHz）、**Rewind 列**（Rewind から Record まで、5 個の LED）は低音域（60Hz、120Hz）を表示します。各列は、その帯域に含まれるサブ帯域の平均ではなく、いちばん大きいサブ帯域に追従するため、1 つのサブ帯域が大きく鳴っても、同じ組の静かな隣の帯域に薄められることはありません。さらに各列は、直近数秒間のその帯域自体の最小〜最大範囲を基準に自動調整されます — Mini の下段相対レベルバーと同じ考え方を全体音量ではなく帯域ごとに適用したもので、LED が 5~7 個しかない列でも、その部分が静かでも大きくても動き続けます。設定したトグルボタンがいずれかの列に含まれる場合、そのボタンは点灯順から除外されます。
* **5 番目の列**は、Channel Mute、Channel Solo、Channel Record の各ボタンを左から右の順に 1 個ずつ、全体の相対レベル（下の 6 番目のバーや Mini の下段バーと同じ値）に応じて点灯させます — 特定の周波数帯域ではなく全体レベルに追従します。
* **6 番目の相対レベルバー**は、本体上で 1 列に並んでいる Bank、Channel、Up/Left/Zoom/Right/Down の各ボタンを再利用します: 5 段にグループ化し、全体の相対レベル（Mini の下段バーや One のエンコーダーリングと同じ値）に応じて下段から順に点灯させます。下から順に: Down、Left+Zoom+Right をまとめて、Up、Channel Left+Right をまとめて、Bank Left+Right をまとめて — 同じ段のボタンは常に一緒に点灯し、一緒に消灯します。
* **エンコーダーリング 1 個**が、Mini の 8 個のリングのうちの 1 個と同じように絶対レベルを表示します。
* **本体自体のレベルメーター**も、エンコーダーリングとは別に全体の相対レベルに応じて点灯します。
* **12 文字ディスプレイ**は、ショーが ON の間 `one.display_text`（デフォルト `"LED ON"`、大文字に変換、最大 12 文字）を表示し、OFF の間は空白になります。テキストが表示幅より長い場合はスクロールします: `one.display_scroll_step_s` 秒ごとに 1 文字分右にずれていき、表示を完全に通過すると左端から再開します（`one.display_scroll` を `false` にすると、スクロールせず左揃えで固定表示されます）。文字は 7 セグメント形状で表示され、`W` は `U` のように見え、`M`、`K`、`X` は読みにくいか紛らわしいため、できるだけ避けてください。
* **トグルボタン**（デフォルト `Scrub`、33 個の LED ボタンから選択可能）がショーの ON/OFF を切り替えます。ショー実行中は LED がソフトウェア側で 0.5 秒ごとに点滅します（本体自体のハードウェア点滅速度は未検証のため、プログラムが自前で制御します）。
* **ショーで使用しないもの:** Master LED — ショーはこの LED を点灯しません。
* **両方のコントローラーを一緒に使う:** Mini と One は同時に実行でき、それぞれ独立してホットプラグされます。ON/OFF 状態、マイク、設定ファイルは 1 つだけです — どちらのコントローラーのボタンでショーを切り替えても、両方が連動します。

---

## 4. 設定ファイルの説明 (`config.json`)

コントローラーごとに `"mini"`、`"one"` セクションがあり、それ以外は両方のコントローラーで共有されます。X-Touch One 対応前の `config.json`（フラットな `midi_port_name`、`toggle_button`、`buttons_enabled`、`daw_proxy`、`daw_proxy_name` キー）もそのまま読み込め、プログラムが自動的に `"mini"` セクションへ移行します。ただし、セットアップウィザードは常に以下の構造で保存します。

### `mini` セクション（X-Touch Mini）

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `mini.enabled` | `true` | Mini を使用するかどうかです。`false` にすると、接続されていても無視します。 |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI ポート検索文字列です。 |
| `mini.toggle_button` | `"A"` | トグルスイッチボタン (`"A"` または `"B"`)。 |
| `mini.buttons_enabled` | `true` | ボタン LED レベルバーの有効/無効設定です（上段 = 絶対レベル、下段 = 相対レベル）。`false` の場合はボタン LED に一切触れません。 |
| `mini.daw_proxy` | `true` | DAW がコントローラーの代わりに使う仮想 MIDI デバイスを作成します（3-6 参照）。ショーが止まったときに DAW が描いていた LED 状態を復元できます。`false` にすると仮想デバイスを作りません。 |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | DAW に表示される仮想デバイスの名前です。 |

### `one` セクション（X-Touch One）

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `one.enabled` | `false` | One を使用するかどうかです。`false` にすると、接続されていても無視します。 |
| `one.midi_port_name` | `"X-Touch One"` | MIDI ポート検索文字列です。 |
| `one.toggle_button` | `"Scrub"` | 33 個の LED ボタン名（`BPM`、`Channel Record`、`Channel Solo`、`Channel Mute`、`Channel Select`、`Bank Left/Right`、`Channel Left/Right`、`F1`-`F6`、`Marker`、`Nudge`、`Cycle`、`Drop`、`Replace`、`Click`、`Solo`、`Rewind`、`Forward`、`Stop`、`Play`、`Record`、`Up`、`Down`、`Left`、`Right`、`Zoom`、`Scrub`）のいずれか（大文字小文字は区別しません）、または MIDI ノート番号です。無効な値の場合は警告とともに `"Scrub"` に置き換わります。 |
| `one.daw_proxy` | `true` | `mini.daw_proxy` と同じで、One 用です（3-6 参照）。 |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | DAW に表示される仮想デバイスの名前です。 |
| `one.display_text` | `"LED ON"` | ショーが ON の間、12 文字ディスプレイに表示されます（3-7 参照）。大文字に変換され、最大 12 文字に切り詰められます。 |
| `one.display_scroll` | `true` | テキストが表示幅より長い場合にスクロールします。`false` にするとスクロールせず左揃えで固定表示します。 |
| `one.display_scroll_step_s` | `0.3` | 1 文字分スクロールする間隔（秒）です。 |

### 共有設定

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `audio_input_device` | `"default"` | オーディオ入力デバイス名です。 |
| `frame_rate` | `30` | 1秒あたりの LED 描画フレームレート (FPS) です。 |
| `decay_per_frame` | `1` | 1 フレームでバー/リングが下がる最大ステップ数です。 |
| `show_enabled_at_start` | `true` | プログラム起動時にショーを自動的に ON にします。 |
| `show_when_display_off_on_ac` | `false` | 電源アダプター接続時に、ディスプレイがスリープでもショーを継続します。デフォルトは OFF で、LED が消え、画面が再び点くまでマイクも閉じます。画面が消えてもショーを続けたい場合は `true` に設定してください。 |
| `show_when_display_off_on_battery` | `false` | バッテリー駆動時に、ディスプレイがスリープでもショーを継続します。デフォルトは OFF で、LED が消え、画面が再び点くまでマイクも閉じて電力を節約します。バッテリーでもショーを続けたい場合は `true` に設定してください。 |
| `bar_max_fall_s` | `2.0` | ダイナミックレンジ上限が下がる時定数（秒）です。Mini の相対レベルバーと X-Touch One の周波数帯域の列 3 本のすべてで共有されます。 |
| `bar_min_rise_s` | `4.0` | ダイナミックレンジ下限が上がる時定数（秒）です。同じ 4 つの自動レンジ調整トラッカーで共有されます。 |
| `band_centers_hz` | `60`–`8000` | Mini の 8 つのエンコーダー LED 帯域の中心周波数です。 |
| `band_gains` | `[1.0, ...]` | 周波数帯域ごとの個別ゲイン値です。 |
| `min_db` / `max_db` | `-60` / `0` | ダイナミックレンジの下限と上限の補正値 (dB) です。 |
| `fft_size` | `4096` | 解析ウィンドウのサイズです。値が大きいほど低域の精度が上がります。 |
| `level_release` | `0.7` | 減衰のスムージング係数 (0–1) です。値が大きいほどゆっくり下がります。 |
| `noise_gate_db` | `null` | `null` は**ノイズゲート OFF**（すべての音が LED に届く状態）です。数値を入れると dB のしきい値としてゲートが有効になり、これより静かな入力は無音として扱われ LED が消えます。`install.sh` の室内ノイズ測定がこの値を書き込んでくれます。騒がしい部屋では値を上げ（例: `-35`）、静かな部分が切れる場合は下げてください（例: `-55`）。`null` に戻すとゲートは再び OFF になります。 |
| `noise_gate_margin_db` | `4.0` | 室内ノイズ測定とセットアップウィザードが、測定した室内ノイズに加える余裕値です。 |

すべての設定は起動時にのみ読み込まれます。`config.json` を手動変更した後は、以下のコマンドで安全に反映できます。ファイルを検査してからショーを再起動し、問題があれば内容を表示して実行中のショーはそのまま残します:

```zsh
bash ~/xtouch_show/install.sh

```

`bash ~/xtouch_show/manual_start.sh` で手動実行している場合は、`Ctrl+C` で停止してから再度実行してください。

---

## 5. トラブルシューティング

* **`MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` が発生する場合**: USB 接続を確認し、他の DAW ソフトウェアが MIDI ポートを占有していないか確認してください。どちらか一方のコントローラーしか持っていない場合、もう一方についてはこのメッセージが出るのが正常です — `config.json` でそのコントローラーの `enabled` を `false` にすると表示されなくなります。
* **LED リング/バーが反応しない**: 本体の **MC MODE** の状態を確認してください。DAW が MIDI を占有している場合は DAW を終了するか、DAW の MIDI 入力・出力を `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` デバイスに変更してください（3-6 参照）。

> [!WARNING]
> **モーターフェーダーがカチカチ音を立てる/スタッタリングする**: コントローラーが、このショーでテスト済みの 2 つのパーソナリティ（MC Standard、MC Logic）のどちらにもなっていません。どちらかで MC モードに設定してください（3-1 参照）— MC モード以外では誤動作が確認されているため、それ以外のモードではこのショーを使用しないでください。

* **DAW に `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` デバイスが表示されない**: このデバイスはプログラムが実行中で、かつそのコントローラーが有効になっている間だけ存在します。プログラムを起動し（自動起動または `bash ~/xtouch_show/manual_start.sh`）、`logs/xtouch_show.log` に `[mini] DAW proxy ready` / `[one] DAW proxy ready` があるか確認してください。`DAW proxy unavailable` が出ている場合は仮想ポートを作成できなかった状態で、該当セクションの `"daw_proxy": false` は意図的に無効化した設定です。確認後、DAW で MIDI デバイスを再スキャンしてください。
* **トグルボタンの LED が点灯しない**: MIDI 経路が確立していません。ログに `[mini] MIDI connected` / `[one] MIDI connected` があるか確認してください。
* **プログラムは動いているがバーが 0 から動かない**: マイク権限 (`システム設定 → プライバシーとセキュリティ → マイク`) で **Terminal** または **XTouchShow** が許可されているか確認してください。自動起動を OFF にした状態で `bash ~/xtouch_show/manual_start.sh -v` を実行するとリアルタイムのレベルを確認できます（`gate=off` はノイズゲート未設定、音楽が鳴っているのに `gate=False` ならゲートが高すぎる状態です）。
* **音楽が鳴っていないのにバーが動く**: デフォルトではノイズゲートが OFF のため、室内ノイズが LED まで届いています。静かな部屋で `bash ~/xtouch_show/install.sh` を実行し、室内ノイズ測定の質問に **y** と答えてゲートを有効にするか、`config.json` の `noise_gate_db` を `-45` などに設定してください。
* **音楽では動かず、咳のような大きな音にだけ反応する**: ノイズゲートが高すぎます。音楽も会話も止めた状態で `bash ~/xtouch_show/install.sh` を実行して室内ノイズ測定をやり直すか、`config.json` の `noise_gate_db` を下げ（例: `-40`）、必要なら `null` に戻してゲートを OFF にしてください。
* **オレンジ色のマイク表示が消えない**: ショーはコントローラーが 1 台でも接続されていて、かつショーが ON のときだけマイクを保持します。ショーを切るか最後のコントローラーを抜くと、約 2 秒以内に表示が消えます。それでも点いたままなら、別のアプリがマイクを使っているか、手動で起動した 2 つ目のインスタンスが動いています。
* **長時間経つとショーが反応しなくなる（LED が固まり、トグルボタンが効かず、マイク表示が点いたまま）**: プログラムが約 30 秒以内に自動的に再起動するので、少し待ってください。`logs/xtouch_show.log` で `stalled` を探すと確認できます。同じことが繰り返される場合は `bash ~/xtouch_show/install.sh` を実行してください。
* **バーが小さすぎる / 振り切れる**: `config.json` の `min_db` を調整してください（小さすぎる場合は `-50` や `-40`、振り切れる場合は `-70`）。
* **高音域が反応しにくい**: `band_gains` の高域の値を上げてください（例: `1.5`、`2.0`）。
* **終了後もリング/ディスプレイが消えたままになる**: 正常な動作です。MC モードの LED は、ホストから MIDI が送られたときにのみ更新されます。DAW が `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` デバイス経由でコントローラーを制御している場合は、代わりに DAW が最後に設定した状態へ戻ります（3-6 参照）。
* **X-Touch One のディスプレイ表示が読みにくい**: `W` は `U` のように見え、`M`、`K`、`X` はこのディスプレイの 7 セグメントフォントでは読みにくいか紛らわしい文字です — `one.display_text` を別の文言に変えてみてください。
* **自動起動はしているがバー/リングが 0 から動かない**: システムのマイク設定で **XTouchShow** が許可されているか確認してください。
* **自動起動が立ち上がらない**: `launchctl print gui/$(id -u)/com.castika.xtouchshow` で状態を確認するか、`logs/xtouch_show.log` を読んでください。
* **ログに `Operation not permitted` が出る**: フォルダが保護されたパス (`デスクトップ`、`書類`、クラウド同期フォルダ) にあります。`~/xtouch_show` へ移動してから `bash ~/xtouch_show/install.sh` を再実行してください。インストールスクリプトはこうした場所では実行を拒否します。
* **自動起動を削除してショーを停止するコマンド**（再び有効にするには `bash ~/xtouch_show/install.sh`）:
```zsh
bash ~/xtouch_show/uninstall.sh

```



---

## 6. プロジェクトのファイル構成

```text
xtouch_show/
├── xtouch_show.py    # メインエンジン・スクリプト (MIDI、音響解析、セットアップウィザード)
├── test_show.py      # ハードウェアなしで動作ロジックを検証するツール
├── requirements.txt  # Python 依存関係リスト
├── install.sh        # インストール、設定変更、変更の反映 (必要なコマンドはこれ 1 つ)
├── uninstall.sh      # 自動起動削除・ショー停止スクリプト
├── manual_start.sh   # ターミナル手動実行スクリプト
├── icon.png          # アプリアイコンの元画像 (1024x1024 PNG)、XTouchShow.app のアイコンに使用
├── README.md         # 本ガイド
├── LICENSE           # MIT ライセンス全文
├── .gitignore        # バージョン管理から除外するファイル (.venv、logs、config.json ほか)
├── config.json       # 実行設定ファイル (セットアップウィザード実行時に生成)
├── XTouchShow.app    # 自動起動用ランチャーアプリ (install.sh が生成、マイク権限を担当)
├── .venv/            # 必要なライブラリを含む Python 環境
└── logs/             # 実行ログ

```

`config.json`、`XTouchShow.app`、`.venv/`、`logs/` は `install.sh` とセットアップウィザードがお使いの Mac 上で生成するため、ダウンロードしたソースには含まれていません。

*ライセンス: MIT*
