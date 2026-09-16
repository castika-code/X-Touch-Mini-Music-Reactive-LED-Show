[English](#x-touch-mini-music-reactive-led-show-python) | [한국어](#x-touch-mini-music-reactive-led-show-python---한국어-가이드) | [日本語](#x-touch-mini-music-reactive-led-show-python---日本語ガイド)

<img width="1280" height="640" alt="X-Touch Mini Music-Reactive LED Show" src="https://github.com/user-attachments/assets/7b5e6bbb-038e-48aa-adfc-614ae0614aeb" />

---

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
| Quiet room, no music playing | The noise gate is off by default, so faint room noise can still move the LEDs a little. Run `install.sh` and answer **y** to the room-noise measurement to enable the gate and keep them dark. |
| Fader | Adjusts sensitivity (bar height). Moving it all the way down turns off display output (the background show remains running). |
| Layer A or B button (configurable) | Turns the show on and off (configured via `toggle_button`).<br>• **LED off**: Show off<br>• **Blinking**: Show running |
| Unplugging and replugging device | Reconnects automatically. |
| Display asleep (screen dark, Mac still awake) | The show stops and the microphone closes until the display wakes again — on the power adapter and on battery alike (`show_when_display_off_on_ac` and `show_when_display_off_on_battery`, both off by default). The Layer LED keeps blinking, so the show is still switched on. Set either one to `true` to keep the show running while the screen is dark on that power source. |

The frequency bands corresponding to the LED rings from left to right are: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, and 8 kHz**.

The microphone is only open while the X-Touch Mini is connected **and** the show is on; unplugging the controller or switching the show off with the Layer button closes the audio input, so the orange microphone indicator in the menu bar goes off.

After the Mac wakes from sleep the show re-initializes itself: it sends the MC mode command to the controller, restores the LEDs, and reopens the microphone, so there is nothing to restart by hand.

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

For a first install, set the controller to MC mode (Section 3-1), then run the one command below and answer the questions it asks. Pressing **Enter** accepts the default shown in brackets `[]`.

```bash
bash ~/xtouch_show/install.sh
```

That is the only command needed to install the show, to change its settings later, and to apply changes. It takes no options: it asks what it needs. Run it again at any time.

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
| MIDI output port [`midi_port_name`] | First port matching `"X-TOUCH MINI"` | Pick a device number or type a name. |
| Audio input device [`audio_input_device`] | System default input | Built-in microphone or custom device. |
| On/Off Toggle Button [`toggle_button`] | `A` | Choose `A` or `B` for Layer buttons. |
| Button LED level bars [`buttons_enabled`] | `y` | Enable/disable the two button-row level bars. |
| Measure room noise now to enable the noise gate? [`noise_gate_db`] | `n` (gate off) | Answer `y` only if room noise moves the LEDs: it listens for 3 seconds and stores the measured noise floor plus `noise_gate_margin_db`. Keep the room quiet while it measures. Answering `n` leaves the gate off, or keeps the gate already in `config.json` (shown as `[n, current: -41.0]`). |

Select the **microphone capturing audio from your speakers**. Leave other settings default unless needed. The wizard will write to `config.json` upon completion.

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
- **Status Verification:** The Layer A/B LED blinks when the show is running. Logs are saved to `logs/xtouch_show.log` (launcher errors: `logs/launchd.log`).
- **To remove autostart and stop the show:** Run `bash ~/xtouch_show/uninstall.sh`.
- **To register it again:** Re-run `bash ~/xtouch_show/install.sh` and answer **Y**.
- **To turn autostart off without uninstalling:** Run `bash ~/xtouch_show/install.sh` and answer **N**; the show is then started by hand with `bash ~/xtouch_show/manual_start.sh`.

### 3-7. Optional: Direct System Audio Capture (No Microphone)

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

| Parameter | Default | Description |
|---|---|---|
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI port search string (partial matching enabled). |
| `audio_input_device` | `"default"` | System input. Specify a custom name if required. |
| `frame_rate` | `30` | Target LED refresh rate per second. |
| `decay_per_frame` | `1` | Max bar decay steps per single frame. |
| `toggle_button` | `"A"` | Activation toggle button (`"A"` or `"B"`). |
| `show_enabled_at_start` | `true` | Automatically starts visualizer when app launches. |
| `buttons_enabled` | `true` | Enables/disables the two button-row level bars (top = absolute level, bottom = relative level). When false, button LEDs are never touched. |
| `show_when_display_off_on_ac` | `false` | Keeps the show running while the display is asleep and the power adapter is connected. Off by default: the rings and button LEDs go out and the microphone closes until the display wakes. Set to `true` to keep the show running with the screen dark on AC power. |
| `show_when_display_off_on_battery` | `false` | Keeps the show running while the display is asleep on battery. Off by default: the rings and button LEDs go out and the microphone closes until the display wakes, saving power. Set to `true` to keep the show running on battery as well. |
| `bar_max_fall_s` | `2.0` | Time constant (seconds) for dynamic range ceiling decay. |
| `bar_min_rise_s` | `4.0` | Time constant (seconds) for dynamic range floor rising. |
| `band_centers_hz` | `60` to `8000` | Center frequencies for the 8 encoder LED bands. |
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
| `MIDI port 'X-TOUCH MINI' not found` | Check USB connection. On a first install `install.sh` prints the MIDI and audio device list, which shows the exact port name. |
| LED rings do not react | Verify **MC MODE** LED status. Close any DAWs that may be overriding MIDI control. |
| Toggle button LED stays dark | MIDI path not acquired. Check logs for `MIDI connected`. |
| Show runs, but bars stay at 0 | Check mic permissions, input device naming, or input audio level. With autostart off, run `bash ~/xtouch_show/manual_start.sh -v` to inspect real-time level telemetry (`gate=off` means no noise gate is configured; `gate=False` with music playing means the noise gate is too high). |
| Bars move with no music playing | Room noise reaches the LEDs because the noise gate is off (the default). Run `bash ~/xtouch_show/install.sh` in a quiet room and answer **y** to the room-noise measurement to enable it (it saves the gate and restarts the show), or set `noise_gate_db` in `config.json` to a value such as `-45`. |
| Music does not move the bars, only loud sounds like a cough do | The noise gate is too high, usually because the measurement ran while music was playing or someone was talking. Run `bash ~/xtouch_show/install.sh` and repeat the room-noise measurement with no music and no talking, lower `noise_gate_db` in `config.json` (e.g., `-40`), or set it to `null` to switch the gate off. |
| Orange microphone indicator stays on | The show only holds the microphone while the X-Touch Mini is connected **and** the show is on. Switch the show off with the Layer button, or unplug the controller, and the indicator goes off within about two seconds. If it stays on, another app is using the microphone. |
| The show stops reacting after a long time (LEDs frozen, Layer button has no effect, microphone indicator stuck) | The program restarts itself automatically within about 30 seconds, so just wait. Look for `stalled` in `logs/xtouch_show.log` to confirm. If it keeps happening, run `bash ~/xtouch_show/install.sh`. |
| Accidentally denied mic permissions | Navigate to *System Settings → Privacy & Security → Microphone* and grant access to **Terminal** or **XTouchShow**. |
| Bars too small / maxed out | Adjust `min_db` parameter (`-50` or `-40` for low levels; `-70` for high levels). |
| High frequencies unresponsive | Increase high-band gain values under `band_gains` (e.g., `1.5`, `2.0`). |
| Rings stay dark after exit | Expected behavior. MC Mode LED rings only update upon active MIDI input from host. |
| Autostart runs but rings stay at 0 | Ensure **XTouchShow** is allowed under System Microphone settings. |
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

# X-Touch Mini Music-Reactive LED Show (Python) - 한국어 가이드

Behringer X-Touch Mini 컨트롤러를 위한 음악 반응형 LED 라이트 쇼 프로그램입니다. 컨트롤러를 연결하고 음악을 재생하면, 마이크로 입력된 소리가 8개 주파수 대역으로 분석되어 8개 엔코더의 LED 링에 스펙트럼 바(이퀄라이저) 형태로 표시되며, 16개 버튼에는 전체 볼륨 레벨이 표시됩니다.

단일 Python 파일로 작동하며 별도의 앱 설치가 필요 없습니다. **macOS 전용**입니다.

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
| Layer A / B 버튼 | 쇼를 켜고 끕니다 (`toggle_button`으로 설정 가능).<br>• **LED 꺼짐**: 쇼 OFF<br>• **깜빡임**: 쇼 실행 중 |
| 기기 연결 해제 후 재연결 | 자동으로 재연결됩니다. |
| 디스플레이 잠자기 (화면만 꺼지고 Mac은 켜진 상태) | 전원 어댑터를 연결했든 배터리로 쓰고 있든, 화면이 다시 켜질 때까지 쇼가 멈추고 마이크가 닫힙니다 (`show_when_display_off_on_ac`와 `show_when_display_off_on_battery`, 둘 다 기본값 꺼짐). Layer LED는 계속 깜빡이므로 쇼 자체는 켜진 상태입니다. 해당 전원 상태에서 화면이 꺼져도 쇼를 유지하려면 각 항목을 `true`로 설정하세요. |

LED 링(왼쪽→오른쪽)에 대응하는 주파수 대역: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

마이크는 X-Touch Mini가 연결되어 있고 쇼가 켜져 있을 때만 열립니다. 컨트롤러를 뽑거나 Layer 버튼으로 쇼를 끄면 오디오 입력이 닫히고, 메뉴 막대의 주황색 마이크 표시도 꺼집니다.

Mac이 잠자기에서 깨어나면 쇼가 스스로 다시 초기화됩니다. 컨트롤러에 MC 모드 명령을 보내고 LED를 복구한 뒤 마이크를 다시 열기 때문에 손으로 재시작할 것은 없습니다.

---

## 2. 요구 사항

| 항목 | 비고 |
| --- | --- |
| Mac (macOS 12 이상) | 기본 설치 과정에는 관리자 권한이 필요하지 않습니다. |
| Behringer X-Touch Mini + USB 케이블 | Mac의 USB 포트에 직접 연결합니다. |
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

### 3-1. X-Touch Mini를 MC 모드로 설정

1. USB 케이블을 뽑습니다.
2. 기기 좌측 하단의 **MC** 버튼을 누른 상태에서 USB 케이블을 다시 연결합니다.
3. 우측 상단의 **MC MODE** LED가 켜진 상태로 유지되면 버튼을 뗍니다.

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
| MIDI 출력 포트 [`midi_port_name`] | `"X-TOUCH MINI"` | 장치 번호를 선택하거나 이름을 입력합니다. |
| 오디오 입력 장치 [`audio_input_device`] | 시스템 기본 입력 | 내장 마이크 또는 커스텀 장치를 선택합니다. |
| On/Off 토글 버튼 [`toggle_button`] | `A` | Layer A 또는 B 버튼 중 선택합니다. |
| 버튼 LED 레벨 바 [`buttons_enabled`] | `y` | 하단 버튼의 레벨 바 표시 여부를 설정합니다. |

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

마이크는 X-Touch Mini가 연결되고 쇼가 켜진 뒤에만 열립니다. Layer 버튼으로 쇼를 끄거나 컨트롤러를 뽑으면 로그에 `audio input closed`가 찍히고 마이크가 해제되어, 쇼가 다시 켜질 때까지 메뉴 막대의 주황색 마이크 표시가 꺼집니다.

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



---

## 4. 설정 파일 설명 (`config.json`)

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI 포트 검색 문자열입니다. |
| `audio_input_device` | `"default"` | 오디오 입력 장치명입니다. |
| `frame_rate` | `30` | 초당 LED 재생 빈도(FPS)입니다. |
| `decay_per_frame` | `1` | 한 프레임에 바가 내려갈 수 있는 최대 단계 수입니다. |
| `toggle_button` | `"A"` | 토글 스위치 버튼 (`"A"` 또는 `"B"`). |
| `show_enabled_at_start` | `true` | 프로그램이 시작될 때 쇼를 자동으로 켭니다. |
| `buttons_enabled` | `true` | 버튼 LED 레벨 바 활성화 여부입니다 (상단 = 절대 레벨, 하단 = 상대 레벨). `false`이면 버튼 LED를 건드리지 않습니다. |
| `show_when_display_off_on_ac` | `false` | 전원 어댑터를 연결한 상태에서 디스플레이가 잠자기일 때도 쇼를 계속 실행합니다. 기본값은 꺼짐이며, LED 링과 버튼 LED가 꺼지고 화면이 다시 켜질 때까지 마이크도 닫힙니다. 화면이 꺼져도 쇼를 유지하려면 `true`로 설정하세요. |
| `show_when_display_off_on_battery` | `false` | 배터리 상태에서 디스플레이가 잠자기일 때도 쇼를 계속 실행합니다. 기본값은 꺼짐이며, LED 링과 버튼 LED가 꺼지고 화면이 다시 켜질 때까지 마이크도 닫혀 전력을 아낍니다. 배터리에서도 쇼를 유지하려면 `true`로 설정하세요. |
| `bar_max_fall_s` | `2.0` | 다이내믹 레인지 상한이 내려가는 시간 상수(초)입니다. |
| `bar_min_rise_s` | `4.0` | 다이내믹 레인지 하한이 올라가는 시간 상수(초)입니다. |
| `band_centers_hz` | `60`–`8000` | 8개 엔코더 LED 대역의 중심 주파수입니다. |
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

* **`MIDI port 'X-TOUCH MINI' not found` 발생 시**: USB 연결을 확인하고 다른 DAW 프로그램이 MIDI 포트를 점유하고 있는지 확인하세요.
* **LED 링이 반응하지 않음**: 기기의 **MC MODE** LED가 켜져 있는지 확인하세요.
* **토글 버튼 LED가 켜지지 않음**: MIDI 경로가 잡히지 않은 상태입니다. 로그에 `MIDI connected`가 있는지 확인하세요.
* **프로그램은 돌아가는데 바가 0에 고정됨**: 마이크 권한(`시스템 설정 → 개인정보 보호 및 보안 → 마이크`)에서 **Terminal** 또는 **XTouchShow**가 허용되어 있는지 확인하세요. 자동 실행이 꺼진 상태에서 `bash ~/xtouch_show/manual_start.sh -v`로 실행하면 실시간 레벨을 볼 수 있습니다 (`gate=off`는 노이즈 게이트가 설정되지 않은 상태, 음악이 나오는데 `gate=False`이면 게이트가 너무 높은 상태입니다).
* **음악이 없는데 바가 움직임**: 기본값인 노이즈 게이트 OFF 상태라 방 안 소음이 LED까지 전달되는 것입니다. 조용한 방에서 `bash ~/xtouch_show/install.sh`를 실행하고 방 소음 측정 질문에 **y**로 답해 게이트를 켜거나, `config.json`의 `noise_gate_db`를 `-45` 같은 값으로 설정하세요.
* **음악에는 반응하지 않고 기침 같은 큰 소리에만 반응함**: 노이즈 게이트가 너무 높습니다. 음악과 대화를 멈춘 상태에서 `bash ~/xtouch_show/install.sh`를 실행해 방 소음 측정을 다시 하거나, `config.json`의 `noise_gate_db`를 낮추고(예: `-40`) 필요하면 `null`로 되돌려 게이트를 끄세요.
* **주황색 마이크 표시가 꺼지지 않음**: 쇼는 X-Touch Mini가 연결되어 있고 쇼가 켜져 있을 때만 마이크를 유지합니다. Layer 버튼으로 쇼를 끄거나 컨트롤러를 뽑으면 약 2초 안에 표시가 꺼집니다. 그래도 켜져 있으면 다른 앱이 마이크를 사용 중이거나, 수동으로 실행한 두 번째 인스턴스가 돌아가고 있는 것입니다.
* **오랜 시간이 지난 뒤 쇼가 반응하지 않음 (LED가 멈추고, Layer 버튼이 먹지 않으며, 마이크 표시가 켜진 채로 남음)**: 프로그램이 약 30초 안에 스스로 다시 시작하므로 잠시 기다리면 됩니다. `logs/xtouch_show.log`에서 `stalled`를 찾아 확인할 수 있습니다. 같은 일이 계속 반복되면 `bash ~/xtouch_show/install.sh`를 실행하세요.
* **바가 너무 작거나 꽉 참**: `config.json`의 `min_db`를 조절하세요 (작게 움직이면 `-50` 또는 `-40`, 꽉 차면 `-70`).
* **고음역이 잘 반응하지 않음**: `band_gains`의 고역 값을 올리세요 (예: `1.5`, `2.0`).
* **종료 후에도 링이 꺼진 채로 남음**: 정상 동작입니다. MC 모드의 LED 링은 호스트가 MIDI를 보낼 때만 갱신됩니다.
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

# X-Touch Mini Music-Reactive LED Show (Python) - 日本語ガイド

Behringer X-Touch Mini コントローラー用の音楽連動型 LED ライトショープログラムです。コントローラーを接続して音楽を再生すると、マイクで拾った音が 8 つの周波数帯域に解析され、8 つのエンコーダーの LED リングにスペクトラムバー（イコライザー）として表示されます。また、16 個のボタンには全体の音量レベルが表示されます。

単一の Python ファイルで動作し、個別のアプリをインストールする必要はありません。**macOS 専用**です。

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
| Layer A / B ボタン | ショーの ON/OFF を切り替えます（`toggle_button` で設定可能）。<br>• **LED 消灯**: ショー OFF<br>• **点滅**: ショー実行中 |
| 機器の切断と再接続 | 自動的に再接続されます。 |
| ディスプレイのスリープ（画面だけが消え、Mac は起動中） | 電源アダプター接続時もバッテリー駆動時も、画面が再び点くまでショーは停止し、マイクも閉じます（`show_when_display_off_on_ac` と `show_when_display_off_on_battery`、どちらもデフォルトは OFF）。Layer LED は点滅し続けるため、ショー自体は ON のままです。その電源状態で画面が消えてもショーを続けたい場合は、各項目を `true` に設定してください。 |

LED リング（左→右）に対応する周波数帯域: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

マイクは X-Touch Mini が接続されていて、かつショーが ON のときだけ開きます。コントローラーを抜くか Layer ボタンでショーを切るとオーディオ入力が閉じ、メニューバーのオレンジ色のマイク表示も消えます。

Mac がスリープから復帰すると、ショーは自動的に初期化し直します。コントローラーに MC モードコマンドを送り、LED を復元してからマイクを開き直すため、手動で再起動する必要はありません。

---

## 2. 必要条件

| 項目 | 備考 |
|---|---|
| Mac (macOS 12 以降) | 基本的なインストール手順に管理者権限は不要です。 |
| Behringer X-Touch Mini + USB ケーブル | Mac の USB ポートに直接接続します。 |
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

### 3-1. X-Touch Mini を MC モードに設定
1. USB ケーブルを抜きます。
2. 本体左下の **MC** ボタンを押しながら、USB ケーブルを Mac に再接続します。
3. 右上の **MC MODE** LED が点灯したままになったら、ボタンを離します。

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
| MIDI 出力ポート [`midi_port_name`] | `"X-TOUCH MINI"` | デバイス番号を選択するか、名前を入力します。 |
| オーディオ入力デバイス [`audio_input_device`] | システムデフォルト入力 | 内蔵マイクまたはカスタムデバイスを選択します。 |
| On/Off トグルボタン [`toggle_button`] | `A` | Layer A または B ボタンから選択します。 |
| ボタン LED レベルバー [`buttons_enabled`] | `y` | 下段ボタンのレベルバー表示の有効/無効を設定します。 |

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

マイクは X-Touch Mini が接続され、ショーが ON になってから開きます。Layer ボタンでショーを切るかコントローラーを抜くとログに `audio input closed` が出てマイクが解放され、ショーが再び動くまでメニューバーのオレンジ色のマイク表示は消えます。

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



---

## 4. 設定ファイルの説明 (`config.json`)

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI ポート検索文字列です。 |
| `audio_input_device` | `"default"` | オーディオ入力デバイス名です。 |
| `frame_rate` | `30` | 1秒あたりの LED 描画フレームレート (FPS) です。 |
| `decay_per_frame` | `1` | 1 フレームでバーが下がる最大ステップ数です。 |
| `toggle_button` | `"A"` | トグルスイッチボタン (`"A"` または `"B"`). |
| `show_enabled_at_start` | `true` | プログラム起動時にショーを自動的に ON にします。 |
| `buttons_enabled` | `true` | ボタン LED レベルバーの有効/無効設定です（上段 = 絶対レベル、下段 = 相対レベル）。`false` の場合はボタン LED に一切触れません。 |
| `show_when_display_off_on_ac` | `false` | 電源アダプター接続時に、ディスプレイがスリープでもショーを継続します。デフォルトは OFF で、LED リングとボタン LED が消え、画面が再び点くまでマイクも閉じます。画面が消えてもショーを続けたい場合は `true` に設定してください。 |
| `show_when_display_off_on_battery` | `false` | バッテリー駆動時に、ディスプレイがスリープでもショーを継続します。デフォルトは OFF で、LED リングとボタン LED が消え、画面が再び点くまでマイクも閉じて電力を節約します。バッテリーでもショーを続けたい場合は `true` に設定してください。 |
| `bar_max_fall_s` | `2.0` | ダイナミックレンジ上限が下がる時定数（秒）です。 |
| `bar_min_rise_s` | `4.0` | ダイナミックレンジ下限が上がる時定数（秒）です。 |
| `band_centers_hz` | `60`–`8000` | 8つのエンコーダー LED 帯域の中心周波数です。 |
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

* **`MIDI port 'X-TOUCH MINI' not found` が発生する場合**: USB 接続を確認し、他の DAW ソフトウェアが MIDI ポートを占有していないか確認してください。
* **LED リングが反応しない**: 本体の **MC MODE** LED が点灯しているか確認してください。
* **トグルボタンの LED が点灯しない**: MIDI 経路が確立していません。ログに `MIDI connected` があるか確認してください。
* **プログラムは動いているがバーが 0 から動かない**: マイク権限 (`システム設定 → プライバシーとセキュリティ → マイク`) で **Terminal** または **XTouchShow** が許可されているか確認してください。自動起動を OFF にした状態で `bash ~/xtouch_show/manual_start.sh -v` を実行するとリアルタイムのレベルを確認できます（`gate=off` はノイズゲート未設定、音楽が鳴っているのに `gate=False` ならゲートが高すぎる状態です）。
* **音楽が鳴っていないのにバーが動く**: デフォルトではノイズゲートが OFF のため、室内ノイズが LED まで届いています。静かな部屋で `bash ~/xtouch_show/install.sh` を実行し、室内ノイズ測定の質問に **y** と答えてゲートを有効にするか、`config.json` の `noise_gate_db` を `-45` などに設定してください。
* **音楽では動かず、咳のような大きな音にだけ反応する**: ノイズゲートが高すぎます。音楽も会話も止めた状態で `bash ~/xtouch_show/install.sh` を実行して室内ノイズ測定をやり直すか、`config.json` の `noise_gate_db` を下げ（例: `-40`）、必要なら `null` に戻してゲートを OFF にしてください。
* **オレンジ色のマイク表示が消えない**: ショーは X-Touch Mini が接続されていて、かつショーが ON のときだけマイクを保持します。Layer ボタンでショーを切るかコントローラーを抜くと、約 2 秒以内に表示が消えます。それでも点いたままなら、別のアプリがマイクを使っているか、手動で起動した 2 つ目のインスタンスが動いています。
* **長時間経つとショーが反応しなくなる（LED が固まり、Layer ボタンが効かず、マイク表示が点いたまま）**: プログラムが約 30 秒以内に自動的に再起動するので、少し待ってください。`logs/xtouch_show.log` で `stalled` を探すと確認できます。同じことが繰り返される場合は `bash ~/xtouch_show/install.sh` を実行してください。
* **バーが小さすぎる / 振り切れる**: `config.json` の `min_db` を調整してください（小さすぎる場合は `-50` や `-40`、振り切れる場合は `-70`）。
* **高音域が反応しにくい**: `band_gains` の高域の値を上げてください（例: `1.5`、`2.0`）。
* **終了後もリングが消えたままになる**: 正常な動作です。MC モードの LED リングは、ホストから MIDI が送られたときにのみ更新されます。
* **自動起動はしているがバーが 0 から動かない**: システムのマイク設定で **XTouchShow** が許可されているか確認してください。
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
