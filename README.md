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
| 음악이 없는 조용한 상태 | 기본적으로 노이즈 게이트가 꺼져 있어 미세한 방 안 소음에도 LED가 움직일 수 있습니다. `calibrate.sh`를 실행하여 게이트를 활성화할 수 있습니다. |
| 페이더 (Fader) | 민감도(바 높이)를 조절합니다. 끝까지 내리면 배경 쇼는 유지된 채 LED 출력만 꺼집니다. |
| Layer A / B 버튼 | 쇼를 켜고 끕니다 (`toggle_button`으로 설정 가능).<br>

<br>• **LED 꺼짐**: 쇼 OFF<br>

<br>• **깜빡임**: 쇼 실행 중 |
| 기기 연결 해제 후 재연결 | 자동으로 재연결됩니다. |

LED 링(왼쪽→오른쪽)에 대응하는 주파수 대역: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

마이크는 X-Touch Mini가 연결되어 있고 쇼가 켜져 있을 때만 열립니다. 컨트롤러를 뽑거나 Layer 버튼으로 쇼를 끄면 오디오 입력이 닫히고, 메뉴 막대의 주황색 마이크 표시도 꺼집니다.

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

### 3-1. X-Touch Mini를 MC 모드로 설정

1. USB 케이블을 뽑습니다.
2. 기기 좌측 하단의 **MC** 버튼을 누른 상태에서 USB 케이블을 다시 연결합니다.
3. 우측 상단의 **MC MODE** LED가 켜진 상태로 유지되면 버튼을 뗍니다.

### 3-2. 프로그램 설치

1. 다운로드한 `xtouch_show` 폴더를 사용자 홈 디렉토리(`~/xtouch_show`)에 위치시킵니다.
> **주의:** `iCloud Drive`, `Dropbox`, `바탕화면`, `문서` 폴더 내부에 두지 마세요. macOS 권한 제한으로 인해 로그인 시 자동 실행이 작동하지 않습니다.


2. 터미널(Terminal)을 엽니다.
3. 아래 설치 명령어를 실행합니다:

```zsh
~/xtouch_show/install.sh

```

4. **설치 스크립트 동작 내용:**
* Python 3 환경 확인 및 가상환경(`.venv`) 생성 후 필요 라이브러리(`python-rtmidi`, `sounddevice`, `numpy`)를 설치합니다.
* 설정 파일(`config.json`)이 없으면 **설정 위저드**를 실행합니다.
* 런처 앱(`XTouchShow.app`)을 생성하고 기기 연결 테스트(LED 링 스윕)를 진행합니다.
* 로그인 시 **자동 실행되도록 등록**하고 즉시 실행합니다. 첫 실행 시 마이크 권한 요청 팝업이 뜨면 [허용]을 선택해야 합니다.



### 3-3. 설정 위저드 (`setup.sh`)

설정 파일을 재구성하고 싶다면 언제든 아래 명령어를 실행할 수 있습니다:

```zsh
~/xtouch_show/setup.sh

```

대괄호 `[]` 안에 표시되는 기본값을 사용하려면 **Enter**를 누르면 됩니다.

| 설정 항목 | 기본값 | 설명 |
| --- | --- | --- |
| MIDI 출력 포트 [`midi_port_name`] | `"X-TOUCH MINI"` | 장치 번호를 선택하거나 이름을 입력합니다. |
| 오디오 입력 장치 [`audio_input_device`] | 시스템 기본 입력 | 내장 마이크 또는 커스텀 장치를 선택합니다. |
| On/Off 토글 버튼 [`toggle_button`] | `A` | Layer A 또는 B 버튼 중 선택합니다. |
| 버튼 LED 레벨 바 [`buttons_enabled`] | `y` | 하단 버튼의 레벨 바 표시 여부를 설정합니다. |

### 3-4. 수동 실행 및 권한 확인

프로그램을 터미널에서 수동으로 직접 실행하여 로그를 확인하려면:

```zsh
~/xtouch_show/run.sh

```

*(단, 자동 실행 서비스와 충돌할 수 있으므로 테스트 시 `~/xtouch_show/uninstall.sh`로 자동 실행을 먼저 중지하는 것이 좋습니다.)*

마이크는 X-Touch Mini가 연결되고 쇼가 켜진 뒤에만 열립니다. Layer 버튼으로 쇼를 끄거나 컨트롤러를 뽑으면 로그에 `audio input closed`가 찍히고 마이크가 해제되어, 쇼가 다시 켜질 때까지 메뉴 막대의 주황색 마이크 표시가 꺼집니다.

### 3-5. 동작 확인 및 조정

1. 음악을 재생하여 LED 링이 즉시 반응하는지 확인합니다.
2. **민감도 조절:**
* 바가 너무 작게 움직일 경우: 마이크를 가깝게 두거나 `config.json`에서 `min_db`를 `-50` 또는 `-40`으로 올립니다.
* 바가 너무 꽉 찰 경우: `min_db`를 `-70` 정도로 낮춥니다.
* 조용한 상태에서도 LED가 움직인다면 노이즈 게이트를 설정합니다:
```zsh
~/xtouch_show/calibrate.sh

```


*(측정 중에는 방을 완전히 조용히 유지해야 합니다.)*



---

## 4. 설정 파일 설명 (`config.json`)

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI 포트 검색 문자열입니다. |
| `audio_input_device` | `"default"` | 오디오 입력 장치명입니다. |
| `frame_rate` | `30` | 초당 LED 재생 빈도(FPS)입니다. |
| `toggle_button` | `"A"` | 토글 스위치 버튼 (`"A"` 또는 `"B"`). |
| `buttons_enabled` | `true` | 버튼 LED 레벨 바 활성화 여부입니다. |
| `band_centers_hz` | `60` ~ `8000` | 8개 엔코더 LED 대역의 중심 주파수입니다. |
| `noise_gate_db` | `null` | 노이즈 게이트 임계값(dB)입니다. `null`은 게이트 OFF 상태입니다. |

`config.json` 수동 수정 후에는 아래 명령어로 안전하게 재시작할 수 있습니다:

```zsh
~/xtouch_show/restart.sh

```

---

## 5. 문제 해결 (Troubleshooting)

* **`MIDI port 'X-TOUCH MINI' not found` 발생 시**: USB 연결을 확인하고 다른 DAW 프로그램이 MIDI 포트를 점유하고 있는지 확인하세요.
* **LED 링이 반응하지 않음**: 기기의 **MC MODE** LED가 켜져 있는지 확인하세요.
* **프로그램은 돌아가는데 바가 0에 고정됨**: 마이크 권한(`시스템 설정 → 개인정보 보호 및 보안 → 마이크`)에서 **Terminal** 또는 **XTouchShow**가 허용되어 있는지 확인하세요.
* **주황색 마이크 표시가 꺼지지 않음**: 쇼는 X-Touch Mini가 연결되어 있고 쇼가 켜져 있을 때만 마이크를 유지합니다. Layer 버튼으로 쇼를 끄거나 컨트롤러를 뽑으면 약 2초 안에 표시가 꺼집니다. 그래도 켜져 있으면 다른 앱이 마이크를 사용 중인 것입니다.
* **자동 실행 삭제 명령어**:
```zsh
~/xtouch_show/uninstall.sh

```



---

## 6. 프로젝트 파일 구조

```text
xtouch_show/
├── xtouch_show.py    # 메인 엔진 스크립트
├── config.json       # 실행 설정 파일 (setup.sh 실행 시 생성)
├── requirements.txt   # Python 의존성 목록
├── install.sh        # 설치 및 자동실행 등록 스크립트
├── setup.sh          # 설정 위저드
├── calibrate.sh      # 노이즈 게이트 캘리브레이션 스크립트
├── restart.sh        # 재시작 스크립트
├── uninstall.sh      # 자동실행 삭제 스크립트
└── run.sh            # 터미널 수동 실행 스크립트

```

*License: MIT*
---

---

# X-Touch Mini Music-Reactive LED Show (Python) - 日本語ガイド

Behringer X-Touch Mini コントローラー用の音楽連動型 LED ライトショープログラムです。コントローラーを接続して音楽を再生すると、マイクで拾った音が 8 つの周波数帯域に解析され、8 つのエンコーダーの LED リングにスペクトラムバー（イコライザー）として表示されます。また、16 個のボタンには全体の音量レベルが表示されます。

単一の Python ファイルで動作し、個別のアプリをインストールする必要はありません。**macOS 専用**です。

本ガイドは、**依存パッケージがインストールされていないクリーンな Mac** を前提としています。セットアップには約 10〜20 分かかります。

---

## 1. 主な動作

| 状況 | 動作 |
|---|---|
| プログラム起動 / 機器接続 | ショー ON（デフォルト）。8 つの LED リングが音楽に合わせてスペクトラムバーとして動き始めます。 |
| ショー実行中の上段ボタン (1–8) | 左から右へ点灯する絶対音量レベルバーです。 |
| ショー実行中の下段ボタン (9–16) | 直近数秒間の最小〜最大範囲を基準とした相対音量レベルバーです。音圧の高い音源でもダイナミックに動きます。 |
| ノブ操作およびその他のボタン入力 | 無視されます。LED ショーは維持され、MIDI 本来の機能も正常に動作します。 |
| 音楽が流れていない静かな状態 | デフォルトではノイズゲートが OFF になっているため、微小な室内ノイズで LED が動くことがあります。`calibrate.sh` を実行してゲートを有効化できます。 |
| フェーダー (Fader) | 感度（バーの高さ）を調整します。一番下まで下げると、バックグラウンドのショーは維持されたまま LED 出力のみが OFF になります。 |
| Layer A / B ボタン | ショーの ON/OFF を切り替えます（`toggle_button` で設定可能）。<br>• **LED 消灯**: ショー OFF<br>• **点滅**: ショー実行中 |
| 機器の切断と再接続 | 自動的に再接続されます。 |

LED リング（左→右）に対応する周波数帯域: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**

マイクは X-Touch Mini が接続されていて、かつショーが ON のときだけ開きます。コントローラーを抜くか Layer ボタンでショーを切るとオーディオ入力が閉じ、メニューバーのオレンジ色のマイク表示も消えます。

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

### 3-1. X-Touch Mini を MC モードに設定
1. USB ケーブルを抜きます。
2. 本体左下の **MC** ボタンを押しながら、USB ケーブルを Mac に再接続します。
3. 右上の **MC MODE** LED が点灯したままになったら、ボタンを離します。

### 3-2. プログラムのインストール
1. ダウンロードした `xtouch_show` フォルダを**ユーザーのホームディレクトリー (`~/xtouch_show`)** に配置します。
   > **注意:** `iCloud Drive`、`Dropbox`、`デスクトップ`、`書類` フォルダ内には配置しないでください。macOS の権限制限により、ログイン時の自動起動が動作しなくなります。
2. **ターミナル (Terminal)** を開きます。
3. 以下のインストールコマンドを実行します:

```zsh
~/xtouch_show/install.sh

```

4. **インストーラーの動作内容:**
* Python 3 環境を確認し、仮想環境 (`.venv`) を作成して必要なライブラリ (`python-rtmidi`, `sounddevice`, `numpy`) をインストールします。
* 設定ファイル (`config.json`) が存在しない場合は、**セットアップウィザード**を実行します。
* ランチャーアプリ (`XTouchShow.app`) を生成し、実機接続テスト (LED リングスイープ) を行います。
* ログイン時に**自動起動するよう登録**し、すぐに実行します。初回起動時にマイク権限の確認ポップアップが表示されたら、**[許可]** を選択してください。



### 3-3. セットアップウィザード (`setup.sh`)

設定ファイルを再構成したい場合は、いつでも以下のコマンドを実行できます:

```zsh
~/xtouch_show/setup.sh

```

角括弧 `[]` 内に表示されるデフォルト値を使用する場合は、**Enter** キーを押します。

| 設定項目 | デフォルト値 | 説明 |
| --- | --- | --- |
| MIDI 出力ポート [`midi_port_name`] | `"X-TOUCH MINI"` | デバイス番号を選択するか、名前を入力します。 |
| オーディオ入力デバイス [`audio_input_device`] | システムデフォルト入力 | 内蔵マイクまたはカスタムデバイスを選択します。 |
| On/Off トグルボタン [`toggle_button`] | `A` | Layer A または B ボタンから選択します。 |
| ボタン LED レベルバー [`buttons_enabled`] | `y` | 下段ボタンのレベルバー表示の有効/無効を設定します。 |

### 3-4. 手動実行と権限の確認

プログラムをターミナルから直接手動実行し、ログを確認したい場合:

```zsh
~/xtouch_show/run.sh

```

*(ただし、自動起動サービスと競合する可能性があるため、テストの際は `~/xtouch_show/uninstall.sh` で自動起動を一度停止することをお勧めします。)*

マイクは X-Touch Mini が接続され、ショーが ON になってから開きます。Layer ボタンでショーを切るかコントローラーを抜くとログに `audio input closed` が出てマイクが解放され、ショーが再び動くまでメニューバーのオレンジ色のマイク表示は消えます。

### 3-5. 動作確認と調整

1. 音楽を再生し、LED リングがすぐに反応することを確認します。
2. **感度調整:**
* バーの動きが小さすぎる場合: マイクを近づけるか、`config.json` の `min_db` を `-50` や `-40` に上げます。
* バーが振り切れすぎる場合: `min_db` を `-70` 程度に下げます。
* 静かな状態でも LED が動く場合はノイズゲートを設定します:
```zsh
~/xtouch_show/calibrate.sh

```


*(測定中は室内を完全な静寂状態に保ってください。)*



---

## 4. 設定ファイルの説明 (`config.json`)

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `midi_port_name` | `"X-TOUCH MINI"` | MIDI ポート検索文字列です。 |
| `audio_input_device` | `"default"` | オーディオ入力デバイス名です。 |
| `frame_rate` | `30` | 1秒あたりの LED 描画フレームレート (FPS) です。 |
| `toggle_button` | `"A"` | トグルスイッチボタン (`"A"` または `"B"`). |
| `buttons_enabled` | `true` | ボタン LED レベルバーの有効/無効設定です。 |
| `band_centers_hz` | `60` ~ `8000` | 8つのエンコーダー LED 帯域の中心周波数です。 |
| `noise_gate_db` | `null` | ノイズゲートのしきい値 (dB) です。`null` はゲート OFF の状態です。 |

`config.json` を手動変更した後は、以下のコマンドで安全に再起動できます:

```zsh
~/xtouch_show/restart.sh

```

---

## 5. トラブルシューティング

* **`MIDI port 'X-TOUCH MINI' not found` が発生する場合**: USB 接続を確認し、他の DAW ソフトウェアが MIDI ポートを占有していないか確認してください。
* **LED リングが反応しない**: 本体の **MC MODE** LED が点灯しているか確認してください。
* **プログラムは動いているがバーが 0 から動かない**: マイク権限 (`システム設定 → プライバシーとセキュリティ → マイク`) で **Terminal** または **XTouchShow** が許可されているか確認してください。
* **オレンジ色のマイク表示が消えない**: ショーは X-Touch Mini が接続されていて、かつショーが ON のときだけマイクを保持します。Layer ボタンでショーを切るかコントローラーを抜くと、約 2 秒以内に表示が消えます。それでも点いたままなら、別のアプリがマイクを使っています。
* **自動起動の削除コマンド**:
```zsh
~/xtouch_show/uninstall.sh

```



---

## 6. プロジェクトのファイル構成

```text
xtouch_show/
├── xtouch_show.py    # メインエンジン・スクリプト
├── config.json       # 実行設定ファイル (setup.sh 実行時に生成)
├── requirements.txt   # Python 依存関係リスト
├── install.sh        # インストールおよび自動起動登録スクリプト
├── setup.sh          # セットアップウィザード
├── calibrate.sh      # ノイズゲート・キャリブレーションスクリプト
├── restart.sh        # 再起動スクリプト
├── uninstall.sh      # 自動起動削除スクリプト
└── run.sh            # ターミナル手動実行スクリプト

```

*ライセンス: MIT*
