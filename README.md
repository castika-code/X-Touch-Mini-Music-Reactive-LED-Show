[English](#xtouchshow) | [한국어](#xtouchshow---한국어-가이드) | [日本語](#xtouchshow---日本語ガイド)

---

# XTouchShow - English Guide

This is a music-reactive LED light show program for the Behringer **X-Touch Mini / X-Touch One** controllers. It receives ambient music via a microphone, analyzes it, and visually displays the sound on the LEDs of the X-Touch controller. The Mini displays this on its 8 encoder LED rings and 16 buttons, while the One uses its buttons, encoder ring, volume meter, and 12-character display. The show can be turned on or off using a configurable button on each controller. If both devices are connected, toggling the show on either device syncs both simultaneously.

It operates as a single Python file and requires no complex separate app installation. This program is **macOS only**.

This guide assumes a **clean Mac with no dependencies installed**. The entire setup process takes about 10–20 minutes.

---

## 1. How It Behaves

| Situation | Behavior |
| --- | --- |
| Program starts / device connected | The show turns on automatically (default). Spectrum bars immediately begin to move in time with the music. |
| Knob manipulation and other button inputs | Status remains as is. The LED show continues uninterrupted, and original MIDI functions operate normally. |
| Quiet state with no music | The noise gate is off by default, so LEDs may react to faint ambient room noise. You can turn the gate on by answering **y** to the room noise measurement step after running `install.sh`. |
| Mini Fader | Adjusts the Mini's sensitivity (bar height). Lowering the fader completely turns off the LED output while the background show remains running. |
| One Jog Wheel | Adjusts the One's sensitivity, the fader's counterpart there. Turn the jog/shuttle wheel; it starts at full sensitivity on every connection. |
| Mini Layer A / B button (Configurable) | Turns the Mini's show on and off (set via `mini.toggle_button`).



• **LED Off**: Show OFF



• **Blinking**: Show running |
| One Scrub button (Configurable) | Turns the show on and off (set via `one.toggle_button`).



• **LED Off**: Show OFF



• **Software Blinking (0.5s cycle)**: Show running



ON/OFF status is synced together regardless of which controller you operate. |
| Device disconnection and reconnection | Each controller reconnects automatically and independently. |
| When using with a DAW | Set the DAW's MIDI input and output to the virtual devices `X-TOUCH MINI SHOW` and/or `X-TOUCH ONE SHOW` (See 3-6). |
| When the display turns off (Mac is still on) | The show pauses and microphone input is blocked until the screen turns back on (`show_when_display_off_on_ac` and `show_when_display_off_on_battery` are both off by default). The Mini's Layer LED keeps blinking, meaning the show program itself is still running. To keep the show running regardless of power status when the screen is off, set these to `true`. |

* Frequency bands corresponding to the Mini's LED rings (left to right): **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**
* The microphone is only active while at least one controller is connected and the show is On. Disconnecting all controllers or turning the show Off also turns the microphone Off.

---

## 2. Requirements

| Item | Notes |
| --- | --- |
| Mac (macOS 12 or later) | The basic installation process does not require administrator privileges. |
| Behringer X-Touch Mini and/or X-Touch One + USB cable | Connect directly to a USB port on your Mac. |
| `xtouch_show` folder | Prepare this by referring to the file structure section below. |
| Audio microphone | Operates by default with the Mac's built-in microphone; external and USB microphones are also supported. |

Python 3 is included by default in the macOS Command Line Tools. If it is not installed, follow the instructions provided by the installation script.

*Note: This program is designed as a tool for dynamic visual presentation, not as a precise audio measurement device. If you wish to capture your computer's system audio directly instead of using a physical microphone, please refer to 3-7.*

---

## 3. Installation Guide

For the initial installation, set the controller to MC mode first (3-1), then run the command below in Terminal and answer the prompts to install automatically. Later settings changes or reinstallations can be performed using the same command.

```zsh
bash ~/xtouch_show/install.sh

```

### 3-1. Set Controller to MC Mode

**X-Touch Mini:**

1. Disconnect the USB cable.
2. Hold down the **MC** button on the bottom left of the device while reconnecting the USB cable.
3. Release the button when the **MC MODE** LED on the top right remains lit.

**X-Touch One:**

1. Disconnect the power cable.
2. Hold down the top encoder while reconnecting the power.
3. Turn the encoder to select the mode.

> [!WARNING] **Warning**
> * XTouchShow was tested on X-Touch One firmware version 1.10.
> * Compatibility has been confirmed in **MC Standard** and **MC Logic** environments.
> * Using other MC modes may result in some LEDs not lighting up.
> * If not in MC mode, it has been confirmed that no LEDs will light up at all.
> * In particular, the motorized fader may behave abnormally in some modes, so please do not use those modes.
> 
> 

### 3-2. Program Installation

1. Place the downloaded `xtouch_show` folder in your user home directory (`~/xtouch_show`).

> **Note:** Do not place it inside `iCloud Drive`, `OneDrive`, `Dropbox`, `Google Drive`, `Desktop`, or `Documents` folders. Due to macOS security permission restrictions, the auto-run feature will not work correctly upon login, and the installation script will refuse to run from these locations.

2. Open the Terminal app.
3. Run the following installation command:

```zsh
bash ~/xtouch_show/install.sh

```

4. **Installation script process:**

* Checks the Python 3 environment, creates a virtual environment (`.venv`), and installs required libraries (`python-rtmidi`, `sounddevice`, `numpy`). On subsequent runs, libraries are reinstalled only if there are changes to `requirements.txt`.
* Automatically runs the **Setup Wizard** if the configuration file (`config.json`) is missing.
* Generates the launcher app (`XTouchShow.app`). A microphone permission request pop-up will appear the first time this app runs. You must select [Allow].

*If you answer **N** to the auto-run question, the auto-run feature will be turned off. In this case, you can start it manually using the `bash ~/xtouch_show/manual_start.sh` command (See 3-4).*

*If executed outside of a terminal environment, all setup questions are automatically processed with their default values.*

### 3-3. Setup Wizard

If the `config.json` file does not exist, the Setup Wizard runs automatically during installation. If you want to reconfigure settings later, rerun the installation command and enter **y** when asked **"Run the settings wizard again?"**:

```zsh
bash ~/xtouch_show/install.sh

```

Once the wizard completes, the show will automatically restart according to the rest of the `install.sh` steps, applying the new settings immediately. To use the default value for any prompt, simply press **Enter**.

1. Enable X-Touch Mini [`mini.enabled`] - Default: `y` if an X-Touch Mini is currently connected, otherwise `n`
Selecting `n` leaves the Mini disabled and skips the two Mini questions below (MIDI port, toggle button).
2. Mini MIDI output port [`mini.midi_port_name`] - Default: `"X-TOUCH MINI"`
Select a device number or manually type the name.
3. Audio input device [`audio_input_device`] - Default: System default input
Select the built-in microphone or a connected external device. Both controllers share this device.
4. Mini On/Off toggle button [`mini.toggle_button`] - Default: `A`
Select either the Layer A or B button.
5. Measure room noise [`noise_gate_db`] - Default: `n` (Gate off)
Shared by both controllers.
6. Enable X-Touch One [`one.enabled`] - Default: `y` if an X-Touch One is currently connected, otherwise `n`
Selecting `y` proceeds to the MC mode confirmation step below; selecting `n` skips it and leaves the One disabled.
7. Is X-Touch One set to MC mode? [`one.enabled`] - Default: `n`
If not in MC mode, the motorized fader will generate noise (clicking) while the show is running. Even if you selected `y` in the previous step, selecting `n` (default) here keeps the One disabled and skips the next three questions.
8. One MIDI output port [`one.midi_port_name`] - Default: The first port matching `"X-Touch One"`
Select a device number or type the name.
9. One toggle button [`one.toggle_button`] - Default: `Scrub`
Any of the 33 LED names (e.g., `BPM`, `F1`-`F6`, `Marker`, `Play`, `Scrub`) or a MIDI note number.
10. One display text [`one.display_text`] - Default: `LED ON`
Displayed in uppercase, up to 12 characters. `W` looks like `U`, and `M`, `K`, `X` have poor readability or can be confusing, so it is recommended to avoid them if possible.

### 3-4. Manual Run and Permission Check

If you selected **N** for auto-run, or if you want to diagnose issues while looking directly at the logs, run it manually in Terminal:

```zsh
bash ~/xtouch_show/manual_start.sh

```

To see detailed debug logs, append the `-v` option:

```zsh
bash ~/xtouch_show/manual_start.sh -v

```

### 3-5. Verifying Operation and Adjustment

1. Play music to confirm that the LED rings react immediately.
2. **How to adjust sensitivity:**

* If the LED bars move too little: Move the microphone closer to the source or increase the `min_db` value in `config.json` to `-50` or `-40`.
* If the LED bars max out too easily: Lower the `min_db` value to around `-70`.
* If the LEDs react unnecessarily in a quiet environment: Set up the noise gate. Run the command below in a quiet room and answer **y** to the **"Measure the room noise for the noise gate?"** prompt:

```zsh
bash ~/xtouch_show/install.sh

```

### 3-6. Using it Alongside a DAW

If you run XTouchShow while working in a DAW, it remembers the LED states right before the show started and restores them to their original state when the show ends. For this to work properly, you must designate the virtual MIDI device provided by XTouchShow as the Control Surface instead of the actual X-TOUCH MINI or One. (Mini is **`X-TOUCH MINI SHOW`**, One is **`X-TOUCH ONE SHOW`**)

**Notes:**

* Each virtual device appears **only while the program is running and the corresponding controller is enabled**. Therefore, it is recommended to leave auto-run on.
* **The toggle button input value for turning the show on/off is not passed to the DAW; it is consumed directly by the show program.** For the Mini, this is the configured Layer button; for the One, it is the press note of the corresponding button. If you need to use that button for another function within the DAW, change the `mini.toggle_button` or `one.toggle_button` setting.
* You may connect the DAW directly to the actual controller, but in this case, restoring the previous LED state after the show ends is not supported.
* To disable the virtual device feature entirely, set `"daw_proxy": false` in the `mini` or `one` section of the `config.json` file.

### 3-7. Optional: Direct System Audio Capture Without a Microphone

If you do not have an external microphone or want to pass the computer's internal audio directly, you can bypass the system output using a virtual loopback driver. *(This process requires administrator privileges.)*

1. **Install BlackHole**: Download the **BlackHole 2ch** installer (`.pkg`) from [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole?utm_source=gemini) or install it via Homebrew (`brew install blackhole-2ch`).
2. **Set up a Multi-Output Device**:
3. Open the **Audio MIDI Setup** app using Spotlight.
4. Click the **`+`** button in the bottom left corner of the window and select **Create Multi-Output Device**.
5. Check both your default output device (Speakers or DAC) and **BlackHole 2ch**. Set your speakers as the Master (Primary/Master) device, and enable Drift Correction for the BlackHole entry.
6. Right-click the newly created Multi-Output Device and select **Use This Device For Sound Output**.
7. **Apply Program Settings**: Designate BlackHole as the audio input using one of the following two methods:

* Run `bash ~/xtouch_show/install.sh`, answer **y** to "Run the settings wizard again?", and select **BlackHole 2ch** as the audio input device. The show will automatically restart after the setting is saved.
* Or, manually edit `config.json` to set `"audio_input_device": "BlackHole 2ch"`, then run `bash ~/xtouch_show/install.sh` to check the settings and restart the show. If it was running manually, terminate it with `Ctrl+C` and run `bash ~/xtouch_show/manual_start.sh` again.

*Note: While using a Multi-Output Device, macOS hardware volume control keys are disabled. You must adjust the output volume directly within the app playing the audio.*

---

## 4. Configuration File Description (`config.json`)

* Parameters prefixed with `mini` are exclusive to the X-TOUCH MINI, and those prefixed with `one` are for the X-TOUCH ONE. Items without a prefix are shared settings.

### `mini` / `one` Section Parameters

| Parameter | Default | Description |
| --- | --- | --- |
| `mini.enabled` | `true` | Whether to use the Mini. If `false`, the device is ignored even if connected. |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI port search string. |
| `mini.toggle_button` | `"A"` | Toggle switch button (`"A"` or `"B"`). |
| `mini.buttons_enabled` | `true` | Whether to enable button LED level bars (Top = absolute level, Bottom = relative level). If `false`, button LED states are not altered. |
| `mini.daw_proxy` | `true` | Creates a virtual MIDI device the DAW can use instead of the controller (See 3-6). Restores the LED states controlled by the DAW when the show stops. If `false`, no virtual device is created. |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | The name of the virtual device displayed in the DAW. |
| `one.enabled` | `false` | Whether to use the One. If `false`, the device is ignored even if connected. |
| `one.midi_port_name` | `"X-Touch One"` | MIDI port search string. |
| `one.toggle_button` | `"Scrub"` | One of the 33 LED button names (case-insensitive) or a MIDI note number. If the value is invalid, it automatically falls back to `"Scrub"` with a warning. |
| `one.daw_proxy` | `true` | Functions identically to `mini.daw_proxy`, applied to the One (See 3-6). |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | The name of the virtual device displayed in the DAW. |
| `one.display_text` | `"LED ON"` | Text displayed on the 12-character display while the show is on (See 3-7). |
| `one.display_scroll` | `true` | Whether to scroll the text. If `false`, it is displayed statically, left-aligned. |
| `one.display_scroll_step_s` | `0.3` | The interval (in seconds) for scrolling the text one step at a time. |
| --- | --- | --- |
| `audio_input_device` | `"default"` | The name of the audio input device to use. |
| `frame_rate` | `30` | LED playback frequency (FPS) per second. |
| `decay_per_frame` | `1` | The maximum number of steps a bar/ring can fall per frame. |
| `show_enabled_at_start` | `true` | Automatically turns on the show when the program runs. |
| `show_when_display_off_on_ac` | `false` | Keeps the show running even when the screen is asleep while connected to power. The default is off; when the screen turns off, LEDs turn off, and the microphone is blocked until the screen turns back on. |
| `show_when_display_off_on_battery` | `false` | Whether to keep the show running when the screen is asleep on battery power. The default is off to save power. |
| `bar_max_fall_s` | `2.0` | Time constant (seconds) for the dynamic range ceiling to fall. |
| `bar_min_rise_s` | `4.0` | Time constant (seconds) for the dynamic range floor to rise. |
| `band_centers_hz` | `60`–`8000` | Center frequencies for the Mini's 8 encoder LED bands. |
| `band_gains` | `[1.0, ...]` | Individual gain values per frequency band. |
| `min_db` / `max_db` | `-60` / `0` | Dynamic range floor and ceiling calibration values (dB). |
| `fft_size` | `4096` | Analysis window size. Larger values yield higher low-frequency precision. |
| `level_release` | `0.7` | Attenuation smoothing factor (0–1). Higher values decay more slowly. |
| `noise_gate_db` | `null` | `null` means **Noise Gate OFF** (all sounds affect LEDs). If a number is specified, input quieter than that dB threshold is considered silence, blocking LED output. |
| `noise_gate_margin_db` | `4.0` | Margin value added to the room noise measured in the Setup Wizard. |

---

## 5. Troubleshooting

* **When `MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` occurs**: Check the USB cable connection and ensure another DAW program is not monopolizing the MIDI port. If you do not own the controller, change the corresponding device setting to `false` in `config.json`.
* **LED rings/bars do not react**: Check the device's **MC MODE** status. If a DAW is occupying the MIDI, close the DAW or change its MIDI input/output to the `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` device (See 3-6).

> [!WARNING]
> **If the motorized fader clicks**: This is a normal malfunction symptom that occurs when not in MC mode. You must set it to MC mode before use.

* **The `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` device is not visible in the DAW**: These devices are generated dynamically only when the program is running and the corresponding controller is enabled. After running the program (`bash ~/xtouch_show/manual_start.sh`), check the `logs/xtouch_show.log` file to ensure the virtual port was created successfully.
* **Toggle button LED does not light up**: The MIDI path is not connected correctly. Check the log to verify the MIDI connection.
* **The program runs, but the bars are stuck at 0**: Check in macOS System Settings (`System Settings → Privacy & Security → Microphone`) that microphone permissions are allowed for the **Terminal** or **XTouchShow** app.
* **Bars keep moving even with no music**: This occurs because the noise gate is off, reflecting ambient room noise. In a quiet environment, run `bash ~/xtouch_show/install.sh` to measure room noise again, or adjust the `noise_gate_db` value in `config.json`.
* **Does not react to music, only to loud sounds like coughing**: The noise gate threshold is set too high. Lower the gate value or set it to `null` to turn the feature off.
* **The show stops after a long time (LEDs freeze, toggle button does not work, etc.)**: The program restarts automatically within about 30 seconds, so please wait a moment. If the same issue repeats, run `bash ~/xtouch_show/install.sh` again.
* **Bars are too small or maxed out**: Adjust the `min_db` value in `config.json` (if moving too little, `-50` or `-40`; if maxed out, `-70`).
* **High frequencies do not react well**: Increase the high-frequency values in `band_gains` (e.g., `1.5`, `2.0`).
* **Rings/display remain turned off even after exiting**: This is normal behavior. MC mode LEDs update only when the host sends a MIDI signal.
* **Autostart does not begin**: Check the status using the `launchctl print gui/$(id -u)/com.castika.xtouchshow` command or check `logs/xtouch_show.log`.
* **`Operation not permitted` appears in the log**: The program folder is located in a protected path (`Desktop`, `Documents`, or cloud folders). Move the folder to the `~/xtouch_show` path and run `bash ~/xtouch_show/install.sh` again.
* **Command to remove autostart and stop the show** (To turn it back on, run `bash ~/xtouch_show/install.sh`):

```zsh
bash ~/xtouch_show/uninstall.sh

```

---

## 6. Project File Structure

```text
xtouch_show/
├── xtouch_show.py     # Main engine script (MIDI, audio analysis, setup wizard)
├── test_show.py       # Tool to verify operational logic without hardware
├── requirements.txt   # Python dependency list
├── install.sh         # Installation, configuration changes, apply changes script
├── uninstall.sh       # Autostart removal and show stop script
├── manual_start.sh    # Terminal manual run script
├── icon.png           # Original app icon (1024x1024 PNG)
├── README.md          # Guide document
├── LICENSE            # Full MIT license text
├── .gitignore         # Excluded files for version control (.venv, logs, config.json, etc.)
├── config.json        # Execution config file (created when running Setup Wizard)
├── XTouchShow.app     # Autostart launcher app (created by install.sh, handles mic permissions)
├── .venv/             # Python virtual environment folder where libraries are installed
└── logs/              # Execution log storage folder

```

The `XTouchShow.app`, `.venv/`, and `logs/` folders are generated directly by `install.sh` and the Setup Wizard on the user's Mac and are not included in the source files.

## *License: MIT*

---

# XTouchShow - 한국어 가이드

Behringer **X-Touch Mini / X-Touch One** 컨트롤러를 위한 음악 반응형 LED 라이트 쇼 프로그램입니다. 주변 음악을 마이크로 입력받아 분석한 뒤, 그 소리를 X-Touch 컨트롤러의 LED에 시각적으로 표시합니다. Mini는 8개의 엔코더 LED 링과 16개의 버튼에, One은 버튼, 엔코더 링, 볼륨 미터(Volume Meter), 12자 디스플레이에 각각 표시합니다. 각 컨트롤러에서 설정 가능한 버튼으로 쇼를 켜거나 끌 수 있으며, 두 장치가 모두 연결된 경우 어느 한쪽에서 켜거나 꺼도 두 장치가 동시에 연동됩니다.

단일 Python 파일로 작동하며 별도의 복잡한 앱 설치가 필요 없습니다. 본 프로그램은 **macOS 전용**입니다.

이 가이드는 **의존성 패키지가 아직 설치되지 않은 초기 상태의 Mac**을 기준으로 설명합니다. 전체 설정에는 약 10~20분이 소요됩니다.

---

## 1. 주요 동작 방식

| 상황 | 동작 방식 |
| --- | --- |
| 프로그램 시작 / 기기 연결 | 쇼가 자동으로 켜집니다(기본값). 음악에 맞춰 스펙트럼 바가 즉시 움직이기 시작합니다. |
| 노브 조작 및 기타 버튼 입력 | 그대로 유지됩니다. LED 쇼는 방해받지 않고 계속 작동하며, MIDI 본래의 기능도 정상 수행됩니다. |
| 음악이 없는 조용한 상태 | 기본적으로 노이즈 게이트가 꺼져 있어, 방 안의 미세한 생활 소음에도 LED가 반응할 수 있습니다. `install.sh`를 실행한 후 방 소음 측정 단계에서 **y**를 입력하면 게이트를 켤 수 있습니다. |
| Mini 페이더 (Fader) | Mini의 감도(바 높이)를 조절합니다. 페이더를 끝까지 내리면 배경 쇼는 유지된 채 LED 출력만 꺼집니다. |
| One 조그 휠 (Jog Wheel) | One에서 휠을 돌려 감도 조절을 합니다. |
| Mini의 Layer A / B 버튼 (설정 가능) | Mini의 쇼를 켜고 끕니다 (`mini.toggle_button`으로 지정).

• **LED 꺼짐**: 쇼 OFF

• **깜빡임**: 쇼 실행 중 |
| One의 Scrub 버튼 (설정 가능) | 쇼를 켜고 끕니다 (`one.toggle_button`으로 지정).

• **LED 꺼짐**: 쇼 OFF

• **소프트웨어 깜빡임 (0.5초 주기)**: 쇼 실행 중

ON/OFF 상태는 어느 컨트롤러에서 조작하든 함께 연동됩니다. |
| 기기 연결 해제 후 재연결 | 각 컨트롤러가 서로 독립적으로 자동 재연결됩니다. |
| DAW와 함께 사용할 때 | DAW의 MIDI 입력과 출력을 가상 장치인 `X-TOUCH MINI SHOW` 및/또는 `X-TOUCH ONE SHOW`로 지정하세요 (3-6 참고). |
| 디스플레이가 꺼졌을 때 (Mac은 켜진 상태) | 화면이 다시 켜질 때까지 쇼가 일시 정지되고 마이크 입력이 차단됩니다 (`show_when_display_off_on_ac`, `show_when_display_off_on_battery` 모두 기본값은 꺼짐). Mini의 Layer LED는 계속 깜빡이므로 쇼 프로그램 자체는 켜진 상태입니다. 전원 상태와 무관하게 화면이 꺼져도 쇼를 계속 유지하려면 각 항목을 `true`로 설정하세요. |

* Mini의 LED 링(왼쪽에서 오른쪽 방향)에 대응하는 주파수 대역: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**
* 컨트롤러가 1개 이상 연결되어 있고 쇼가 켜져(On) 있는 동안에만 마이크가 활성화됩니다. 모든 컨트롤러의 연결을 해제하거나 쇼를 끄면 마이크도 꺼집니다(Off).

---

## 2. 요구 사항

| 항목 | 비고 |
| --- | --- |
| Mac (macOS 12 이상) | 기본 설치 과정에는 관리자 권한이 필요하지 않습니다. |
| Behringer X-Touch Mini 및/또는 X-Touch One + USB 케이블 | Mac의 USB 포트에 직접 연결합니다. |
| `xtouch_show` 폴더 | 아래 파일 구조 섹션을 참고하여 준비합니다. |
| 오디오 마이크 | Mac 내장 마이크로 기본 작동하며, 외장 및 USB 마이크도 지원합니다. |

Python 3는 macOS Command Line Tools에 기본 포함되어 있습니다. 만약 미설치 상태라면 설치 스크립트의 안내에 따르십시오.

*참고: 본 프로그램은 정밀한 오디오 측정기가 아니라 역동적인 시각 연출을 위한 도구로 설계되었습니다. 물리적 마이크 대신 컴퓨터의 시스템 오디오를 직접 캡처하고 싶다면 3-7을 참고하세요.*

---

## 3. 설치 가이드

최초 설치 시 컨트롤러를 MC 모드로 설정한 뒤(3-1), 터미널에서 아래 명령어를 실행하고 안내에 따라 질문에 답하면 자동으로 설치됩니다. 이후 설정 변경이나 재설치 역시 동일한 명령어로 수행할 수 있습니다.

```zsh
bash ~/xtouch_show/install.sh

```

### 3-1. 컨트롤러를 MC 모드로 설정

**X-Touch Mini:**

1. USB 케이블을 분리합니다.
2. 기기 좌측 하단의 **MC** 버튼을 누른 상태에서 USB 케이블을 다시 연결합니다.
3. 우측 상단의 **MC MODE** LED가 켜진 상태로 유지되면 버튼을 놓습니다.

**X-Touch One:**

1. 전원 케이블을 분리합니다.
2. 상단 엔코더를 누른 상태에서 전원을 연결합니다.
3. 엔코더를 돌려 모드를 선택합니다.

> [!WARNING] **주의사항**
> * XTouchShow는 X-Touch One 펌웨어 버전 1.10에서 테스트되었습니다.
> * **MC Standard**와 **MC Logic** 환경에서 호환성이 확인되었습니다.
> * 다른 MC 모드를 사용할 경우 일부 LED가 점등되지 않을 수 있습니다.
> * MC 모드가 아닐 경우, 어떠한 LED도 켜지지 않는 현상이 확인되었습니다.
> * 특히 일부 모드에서는 모터라이즈드 페이더가 비정상적으로 작동할 수 있으므로 해당 모드는 사용하지 마십시오.
> 
> 

### 3-2. 프로그램 설치

1. 다운로드한 `xtouch_show` 폴더를 사용자 홈 디렉토리(`~/xtouch_show`)에 위치시킵니다.

> **주의:** `iCloud Drive`, `OneDrive`, `Dropbox`, `Google Drive`, `바탕화면`, `문서` 폴더 내부에 두지 마세요. macOS의 보안 권한 제한으로 인해 로그인 시 자동 실행 기능이 정상 작동하지 않으며, 설치 스크립트가 해당 위치에서의 실행을 거부합니다.

2. 터미널(Terminal) 앱을 엽니다.
3. 아래 설치 명령어를 실행합니다:

```zsh
bash ~/xtouch_show/install.sh

```

4. **설치 스크립트의 진행 과정:**

* Python 3 환경을 확인하고 가상환경(`.venv`)을 생성한 뒤 필요한 라이브러리(`python-rtmidi`, `sounddevice`, `numpy`)를 설치합니다. 이후 실행 시에는 `requirements.txt`에 변경 사항이 있을 때만 라이브러리를 다시 설치합니다.
* 설정 파일(`config.json`)이 없다면 **설정 위저드**를 자동으로 실행합니다.
* 런처 앱(`XTouchShow.app`)을 생성합니다. 해당 앱이 처음 실행될 때 마이크 권한 승인 요청 팝업이 나타납니다. 반드시 [허용]을 선택해야 합니다.

*자동 실행 여부를 묻는 질문에 **N**으로 답하면 자동 실행 기능이 꺼집니다. 이 경우 `bash ~/xtouch_show/manual_start.sh` 명령어로 수동 실행할 수 있습니다(3-4 참고).*

*터미널이 아닌 환경에서 실행하면 모든 설정 질문은 기본값으로 자동 처리됩니다.*

### 3-3. 설정 위저드

`config.json` 파일이 없으면 설치 과정에서 설정 위저드가 자동으로 실행됩니다. 설정을 다시 구성하고 싶다면 설치 명령어를 다시 실행한 뒤 **"Run the settings wizard again?"** 질문에 **y**를 입력하세요:

```zsh
bash ~/xtouch_show/install.sh

```

위저드가 완료되면 `install.sh`의 나머지 단계에 따라 쇼가 자동으로 재시작되어 새 설정이 즉시 반영됩니다. 기본값을 그대로 사용하려면 **Enter** 키를 누르면 됩니다.

1. X-Touch Mini 사용 여부 [`mini.enabled`] - 기본값: X-Touch Mini가 현재 연결되어 있으면 `y`, 아니면 `n`. 
`n`을 선택하면 Mini를 비활성화 상태로 두고 아래 두 가지 Mini 질문(MIDI 포트, 토글 버튼)은 건너뜁니다.
2. Mini MIDI 출력 포트 [`mini.midi_port_name`] - 기본값: `"X-TOUCH MINI"`  
장치 번호를 선택하거나 이름을 직접 입력합니다.
3. 오디오 입력 장치 [`audio_input_device`] - 기본값: 시스템 기본 입력  
내장 마이크 또는 사용 중인 외장 장치를 선택합니다. 두 컨트롤러가 이 장치를 공유합니다.
4. Mini On/Off 토글 버튼 [`mini.toggle_button`] - 기본값: `A`  
Layer A 또는 B 버튼 중 하나를 선택합니다.
5. 방 소음 측정 여부 [`noise_gate_db`] - 기본값: `n` (게이트 꺼짐). 
두 컨트롤러가 공유합니다.
6. X-Touch One 사용 여부 [`one.enabled`] - 기본값: X-Touch One이 현재 연결되어 있으면 `y`, 아니면 `n`. 
`y`를 선택하면 아래의 MC 모드 확인 단계로 이어지고, `n`을 선택하면 건너뛰어 One을 비활성화 상태로 둡니다.
7. X-Touch One이 MC 모드로 설정되어 있나요? [`one.enabled`] - 기본값: `n`. 
MC 모드가 아닐 경우 쇼가 실행되는 동안 모터 페이더에서 소음(딸깍거림)이 발생합니다. 앞선 단계에서 `y`를 선택했더라도 여기서 `n`(기본값)을 선택하면 One은 꺼진 상태로 유지되며 아래 세 가지 질문은 건너뜁니다.
8. One MIDI 출력 포트 [`one.midi_port_name`] - 기본값: `"X-Touch One"`과 일치하는 첫 번째 포트. 
장치 번호를 선택하거나 이름을 입력합니다.
9. One 토글 버튼 [`one.toggle_button`] - 기본값: `Scrub`  
33개의 LED 버튼 이름(예: `BPM`, `F1`-`F6`, `Marker`, `Play`, `Scrub`) 중 하나 또는 MIDI 노트 번호를 입력합니다.
10. One 디스플레이 텍스트 [`one.display_text`] - 기본값: `LED ON` 

### 3-4. 수동 실행 및 권한 확인

자동 실행 질문에 **N**을 선택했거나, 로그를 직접 보며 문제를 진단하려면 터미널에서 수동으로 실행합니다:

```zsh
bash ~/xtouch_show/manual_start.sh

```

상세한 디버그 로그를 함께 보려면 `-v` 옵션을 붙입니다:

```zsh
bash ~/xtouch_show/manual_start.sh -v

```

### 3-5. 동작 확인 및 조정

1. 음악을 재생하여 LED 링이 즉시 반응하는지 확인합니다.
2. **민감도 조절 방법:**
* LED 바가 너무 작게 움직일 경우: 마이크를 소스에 가깝게 두거나 `config.json`에서 `min_db` 값을 `-50` 또는 `-40`으로 높입니다.
* LED 바가 너무 쉽게 최대치로 꽉 찰 경우: `min_db` 값을 `-70` 정도로 낮춥니다.
* 조용한 환경에서도 LED가 불필요하게 움직인다면 노이즈 게이트를 설정합니다. 조용한 방에서 아래 명령어를 실행하고 **"Measure the room noise for the noise gate?"** 질문에 **y**로 답하세요:
```zsh
bash ~/xtouch_show/install.sh

```





### 3-6. DAW와 함께 사용하기

DAW 작업 도중 XTouchShow를 실행하면, 쇼가 시작되기 직전의 LED 상태를 기억했다가 쇼가 종료될 때 원래 상태로 복원해 줍니다. 이를 정상적으로 작동하려면 실제 X-TOUCH MINI나 One 대신 XTouchShow가 제공하는 가상 MIDI 장치를 서피스(Surface)로 지정해야 합니다. (Mini는 **`X-TOUCH MINI SHOW`**, One은 **`X-TOUCH ONE SHOW`**)

**참고 사항:**

* 각 가상 장치는 **프로그램이 실행 중이고 해당 컨트롤러가 활성화된 상태일 때만** 나타납니다. 따라서 자동 실행을 켜 두는 것을 권장합니다.
* **쇼를 켜고 끄는 토글 버튼 입력값은 DAW로 전달되지 않고 쇼 프로그램이 직접 사용합니다.** Mini는 설정한 Layer 버튼, One은 해당 버튼의 프레스 노트가 이에 해당합니다. 만약 해당 버튼을 DAW 내 다른 기능으로 써야 한다면 `mini.toggle_button` 또는 `one.toggle_button` 설정을 변경하십시오.
* DAW를 실제 컨트롤러에 직접 연결해도 무방하지만, 이 경우 쇼 종료 후 이전 LED 상태로의 복원은 지원되지 않습니다.
* 가상 장치 기능을 완전히 사용하지 않으려면 `config.json` 파일의 `mini` 또는 `one` 섹션에서 `"daw_proxy": false`로 설정하세요.

### 3-7. 선택 사항: 마이크 없이 시스템 오디오 직접 캡처

외부 마이크가 없거나 컴퓨터의 내부 오디오를 직접 전달하고 싶다면, 가상 루프백 드라이버를 통해 시스템 출력을 우회시킬 수 있습니다. *(이 과정에는 관리자 권한이 필요합니다.)*

1. **BlackHole 설치**: [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole?utm_source=gemini)에서 **BlackHole 2ch** 설치 파일(`.pkg`)을 내려받거나 Homebrew를 통해 설치합니다 (`brew install blackhole-2ch`).
2. **멀티 오우트풋(Multi-Output) 장치 설정**:
1. Spotlight를 이용해 **Audio MIDI 설정** 앱을 엽니다.
2. 창 좌측 하단의 **`+`** 버튼을 클릭하고 **Multi-Output 장치 생성**을 선택합니다.
3. 기본 출력 장치(스피커 또는 DAC)와 **BlackHole 2ch**를 모두 체크합니다. 스피커를 마스터(Primary/Master)로 지정하고, BlackHole 항목에는 Drift Correction(드리프트 보정)을 켭니다.
4. 새로 생성한 Multi-Output 장치를 우클릭한 뒤 **이 장치를 사운드 출력으로 사용**을 선택합니다.


3. **프로그램 설정 적용**: 다음 두 가지 방법 중 하나로 BlackHole을 오디오 입력으로 지정합니다.
* `bash ~/xtouch_show/install.sh`를 실행하고 "Run the settings wizard again?"에 **y**를 입력한 뒤, 오디오 입력 장치로 **BlackHole 2ch**를 선택합니다. 설정이 저장된 후 쇼가 자동으로 재시작됩니다.
* 또는 `config.json` 파일에서 직접 `"audio_input_device": "BlackHole 2ch"`로 수정한 후 `bash ~/xtouch_show/install.sh`를 실행하여 설정을 검사하고 쇼를 재시작합니다. 만약 수동 실행 중이었다면 `Ctrl+C`로 종료한 뒤 `bash ~/xtouch_show/manual_start.sh`를 다시 실행하세요.



*참고: Multi-Output 장치를 사용하는 동안에는 macOS의 하드웨어 볼륨 조절 키가 비활성화됩니다. 출력 볼륨은 오디오를 재생하는 앱 내부에서 직접 조절해야 합니다.*

---

## 4. 설정 파일 설명 (`config.json`)

* 접두사가 `mini`인 경우 X-TOUCH MINI, `one`인 경우 X-TOUCH ONE 전용 파라미터입니다. 접두사가 없는 항목은 공통 설정입니다.

### `mini` / `one` 섹션 파라미터

| 파라미터 | 기본값 | 설명 |
| --- | --- | --- |
| `mini.enabled` | `true` | Mini 사용 여부입니다. `false`로 설정하면 기기가 연결되어 있어도 무시합니다. |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI 포트 검색 문자열입니다. |
| `mini.toggle_button` | `"A"` | 토글 스위치 버튼 (`"A"` 또는 `"B"`). |
| `mini.buttons_enabled` | `true` | 버튼 LED 레벨 바 활성화 여부입니다 (상단 = 절대 레벨, 하단 = 상대 레벨). `false`이면 버튼 LED 상태를 변경하지 않습니다. |
| `mini.daw_proxy` | `true` | DAW가 컨트롤러 대신 사용할 수 있는 가상 MIDI 장치를 생성합니다(3-6 참고). 쇼가 멈출 때 DAW가 제어하던 LED 상태를 복원해 줍니다. `false`로 설정하면 가상 장치를 만들지 않습니다. |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | DAW에 표시되는 가상 장치의 이름입니다. |
| `one.enabled` | `false` | One 사용 여부입니다. `false`로 설정하면 기기가 연결되어 있어도 무시합니다. |
| `one.midi_port_name` | `"X-Touch One"` | MIDI 포트 검색 문자열입니다. |
| `one.toggle_button` | `"Scrub"` | 33개 LED 버튼 이름(대소문자 구분 없음) 중 하나 또는 MIDI 노트 번호. 값이 올바르지 않으면 경고와 함께 `"Scrub"`으로 자동 대체됩니다. |
| `one.daw_proxy` | `true` | `mini.daw_proxy`와 동일한 기능으로 One에 적용됩니다(3-6 참고). |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | DAW에 표시되는 가상 장치의 이름입니다. |
| `one.display_text` | `"LED ON"` | 쇼가 켜져 있는 동안 12자 디스플레이에 표시될 텍스트(3-7 참고). |
| `one.display_scroll` | `true` | 텍스트 스크롤 여부입니다. `false`이면 스크롤 없이 왼쪽 정렬로 고정 표시합니다. |
| `one.display_scroll_step_s` | `0.3` | 텍스트가 한 칸씩 스크롤되는 간격(초)입니다. |
| `audio_input_device` | `"default"` | 사용할 오디오 입력 장치 이름입니다. |
| `frame_rate` | `30` | 초당 LED 재생 빈도(FPS)입니다. |
| `decay_per_frame` | `1` | 한 프레임당 바/링이 내려갈 수 있는 최대 단계 수입니다. |
| `show_enabled_at_start` | `true` | 프로그램 실행 시 쇼를 자동으로 켭니다. |
| `show_when_display_off_on_ac` | `false` | 전원 어댑터 연결 상태에서 화면이 잠자기 모드일 때도 쇼를 계속 실행합니다. 기본값은 꺼짐이며, 화면이 꺼지면 LED도 꺼지고 화면이 켜질 때까지 마이크가 차단됩니다. |
| `show_when_display_off_on_battery` | `false` | 배터리 사용 상태에서 화면이 잠자기 모드일 때 쇼를 계속 실행할지 여부입니다. 전력 절약을 위해 기본값은 꺼짐입니다. |
| `bar_max_fall_s` | `2.0` | 다이내믹 레인지 상한이 내려가는 시간 상수(초)입니다. |
| `bar_min_rise_s` | `4.0` | 다이내믹 레인지 하한이 올라가는 시간 상수(초)입니다. |
| `band_centers_hz` | `60`–`8000` | Mini의 8개 엔코더 LED 대역의 중심 주파수입니다. |
| `band_gains` | `[1.0, ...]` | 주파수 대역별 개별 게인 값입니다. |
| `min_db` / `max_db` | `-60` / `0` | 다이내믹 레인지의 하한 및 상한 보정값(dB)입니다. |
| `fft_size` | `4096` | 분석 윈도우 크기입니다. 값이 클수록 저역 주파수 정밀도가 높아집니다. |
| `level_release` | `0.7` | 감쇠 스무딩 계수(0–1)입니다. 값이 클수록 더 천천히 내려갑니다. |
| `noise_gate_db` | `null` | `null`은 **노이즈 게이트 OFF**(모든 소리가 LED에 반영)를 의미합니다. 숫자를 지정하면 해당 dB 임계값보다 조용한 입력은 무음으로 간주하여 LED 출력을 차단합니다. |
| `noise_gate_margin_db` | `4.0` | 방 소음 측정 및 설정 위저드에서 측정된 소음에 더해주는 여유값입니다. |

---

## 5. 문제 해결 (Troubleshooting)

* **`MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` 발생 시**: USB 케이블 연결 상태를 확인하고, 다른 DAW 프로그램이 해당 MIDI 포트를 독점하고 있는지 확인하세요. 컨트롤러를 보유하고 있지 않다면 `config.json`에서 해당 장치 설정을 `false`로 변경하세요.
* **LED 링/바가 반응하지 않음**: 기기의 **MC MODE** 설정 상태를 확인하세요. DAW가 MIDI를 점유하고 있다면 DAW를 종료하거나, DAW의 MIDI 입출력을 `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` 장치로 변경하세요(3-6 참고).

> [!WARNING]
> **모터라이즈드 페이더가 딸깍거리는 경우**: MC 모드가 아닐 때 발생하는 정상적인 오작동 증상입니다. 반드시 MC 모드로 설정한 뒤 사용하세요.

* **DAW에서 `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` 장치가 보이지 않음**: 이 장치들은 프로그램이 실행 중이고 해당 컨트롤러가 활성화되어 있을 때만 동적으로 생성됩니다. 프로그램을 실행한 뒤(`bash ~/xtouch_show/manual_start.sh`) `logs/xtouch_show.log` 파일에서 가상 포트가 정상 생성되었는지 확인하세요.
* **토글 버튼 LED가 켜지지 않음**: MIDI 경로가 올바르게 연결되지 않은 상태입니다. 로그에서 MIDI 연결 여부를 확인하세요.
* **프로그램은 실행되는데 바가 0에 고정됨**: macOS 시스템 설정(`시스템 설정 → 개인정보 보호 및 보안 → 마이크`)에서 **Terminal** 또는 **XTouchShow** 앱의 마이크 권한이 허용되어 있는지 확인하세요.
* **음악이 없는데도 바가 계속 움직임**: 노이즈 게이트가 꺼져 있어 방 안의 생활 소음이 반영되는 현상입니다. 조용한 환경에서 `bash ~/xtouch_show/install.sh`를 실행해 방 소음 측정을 다시 진행하거나, `config.json`의 `noise_gate_db` 값을 조정하세요.
* **음악에는 반응하지 않고 기침 소리 같은 큰 소리에만 반응함**: 노이즈 게이트 임계값이 너무 높게 설정된 경우입니다. 게이트 값을 낮추거나 `null`로 설정해 기능을 꺼보세요.
* **오랜 시간이 지난 뒤 쇼가 멈춤 (LED 정지, 토글 버튼 미작동 등)**: 프로그램이 약 30초 내에 스스로 재시작되므로 잠시 기다려 주십시오. 동일한 문제가 반복되면 `bash ~/xtouch_show/install.sh`를 다시 실행하세요.
* **바가 너무 작거나 꽉 참**: `config.json`의 `min_db` 값을 조절하세요 (작게 움직이면 `-50` 또는 `-40`, 너무 꽉 차면 `-70`).
* **고음역대가 잘 반응하지 않음**: `band_gains` 항목에서 고역대 값을 상향 조정하세요 (예: `1.5`, `2.0`).
* **종료 후에도 링/디스플레이가 꺼진 채로 남음**: 정상적인 동작입니다. MC 모드의 LED는 호스트가 MIDI 신호를 보낼 때만 갱신됩니다.
* **자동 실행이 시작되지 않음**: `launchctl print gui/$(id -u)/com.castika.xtouchshow` 명령어로 상태를 확인하거나 `logs/xtouch_show.log`를 확인하세요.
* **로그에 `Operation not permitted`가 표시됨**: 프로그램 폴더가 보호된 경로(`바탕화면`, `문서` 또는 클라우드 폴더)에 위치해 있습니다. 폴더를 `~/xtouch_show` 경로로 이동한 뒤 `bash ~/xtouch_show/install.sh`를 다시 실행하세요.
* **자동 실행 삭제 및 쇼 중지 명령어** (다시 켜려면 `bash ~/xtouch_show/install.sh` 실행):
```zsh
bash ~/xtouch_show/uninstall.sh

```



---

## 6. 프로젝트 파일 구조

```text
xtouch_show/
├── xtouch_show.py     # 메인 엔진 스크립트 (MIDI, 음향 분석, 설정 위저드)
├── test_show.py       # 하드웨어 없이 동작 로직을 검증하는 도구
├── requirements.txt   # Python 의존성 목록
├── install.sh         # 설치, 설정 변경, 변경 사항 적용 스크립트
├── uninstall.sh       # 자동 실행 삭제 및 쇼 중지 스크립트
├── manual_start.sh    # 터미널 수동 실행 스크립트
├── icon.png           # 앱 아이콘 원본 (1024x1024 PNG)
├── README.md          # 가이드 문서
├── LICENSE            # MIT 라이선스 전문
├── .gitignore         # 버전 관리 제외 파일 목록 (.venv, logs, config.json 등)
├── config.json        # 실행 설정 파일 (설정 위저드 실행 시 생성됨)
├── XTouchShow.app     # 자동 실행용 런처 앱 (install.sh가 생성, 마이크 권한 담당)
├── .venv/             # 라이브러리가 설치된 Python 가상환경 폴더
└── logs/              # 실행 로그 저장 폴더

```

`XTouchShow.app`, `.venv/`, `logs/` 폴더는 사용자의 Mac에서 `install.sh` 및 설정 위저드가 직접 생성하는 항목으로 소스 파일에 포함되지 않습니다.

## *License: MIT*


---

# XTouchShow - 日本語ガイド

Behringer **X-Touch Mini / X-Touch One** コントローラー用の音楽連動型 LED ライトショープログラムです。周辺音楽をマイクで入力して分析した後、その音を X-Touch コントローラーの LED に視覚的に表示します。Mini は 8 個のエンコーダー LED リングと 16 個のボタンに、One はボタン、エンコーダー LED リング、ボリュームメーター（Volume Meter）、12 文字ディスプレイにそれぞれ表示します。各コントローラーで設定可能なボタンによりショーの ON/OFF を切り替えることができ、両方のデバイスが接続されている場合は、どちらか一方で操作しても同時に連動して切り替わります。

単一の Python ファイルで動作し、個別の複雑なアプリのインストールは不要です。本プログラムは **macOS 専用** です。

本ガイドは、**依存パッケージがまだインストールされていない初期状態の Mac** を基準に説明しています。全体のセットアップには約 10〜20 分かかります。

---

## 1. 主な動作

| 状況 | 動作方式 |
| --- | --- |
| プログラム起動 / 機器接続 | ショーが自動的に ON になります（デフォルト）。音楽に合わせてスペクトラムバーが即座に動き始めます。 |
| ノブ操作およびその他のボタン入力 | そのまま維持されます。LED ショーは妨げられることなく継続して動作し、MIDI 本来の機能も正常に機能します。 |
| 音楽が流れていない静かな状態 | デフォルトではノイズゲートが OFF になっているため、部屋の中の微細な生活音にも LED が反応する場合があります。`install.sh` を実行し、室内ノイズ測定の段階で **y** を入力するとゲートを有効化できます。 |
| Mini のフェーダー (Fader) | Mini の感度（バーの高さ）を調節します。フェーダーを一番下まで下げると、バックグラウンドのショーは維持されたまま LED 出力のみが OFF になります。 |
| One のジョグホイール (Jog Wheel) | One でフェーダーに当たる感度調節です。ジョグ／シャトルホイールを回して調節し、接続のたびに最大感度から始まります。 |
| Mini の Layer A / B ボタン（設定可能） | Mini のショーを ON/OFF します（`mini.toggle_button` で指定）。

• **LED 消灯**: ショー OFF

• **点滅**: ショー実行中 |
| One の Scrub ボタン（設定可能） | ショーを ON/OFF します（`one.toggle_button` で指定）。

• **LED 消灯**: ショー OFF

• **ソフトウェア点滅（0.5 秒周期）**: ショー実行中

ON/OFF 状態はどちらのコントローラーで操作しても共に連動します。 |
| 機器の接続解除後の再接続 | 各コントローラーが互いに独立して自動的に再接続されます。 |
| DAW と併用する場合 | DAW の MIDI 入力と出力を仮想デバイスである `X-TOUCH MINI SHOW` および/または `X-TOUCH ONE SHOW` に指定してください（3-6 参照）。 |
| ディスプレイが消えたとき（Mac は起動中の状態） | 画面が再び点くまでショーが一時停止し、マイク入力が遮断されます（`show_when_display_off_on_ac` と `show_when_display_off_on_battery` はどちらもデフォルトで OFF）。Mini の Layer LED は点滅し続けるため、ショープログラム自体は ON の状態です。電源状態に関係なく画面が消えてもショーを継続したい場合は、各項目を `true` に設定してください。 |

* Mini の LED リング（左から右の方向）に対応する周波数帯域: **60 Hz, 120 Hz, 250 Hz, 500 Hz, 1 kHz, 2 kHz, 4 kHz, 8 kHz**
* コントローラーが 1 台以上接続されており、かつショーが ON の状態である間にのみマイクが有効化されます。すべてのコントローラーの接続を解除するかショーを OFF にすると、マイクも無効化されます（OFF）。

---

## 2. 必要条件

| 項目 | 備考 |
| --- | --- |
| Mac (macOS 12 以降) | 基本的なインストール手順に管理者権限は不要です。 |
| Behringer X-Touch Mini および/または X-Touch One + USB ケーブル | Mac の USB ポートに直接接続します。 |
| `xtouch_show` フォルダ | 以下のファイル構成セクションを参照して準備します。 |
| オーディオマイク | Mac の内蔵マイクで基本動作し、外付けおよび USB マイクもサポートしています。 |

Python 3 は macOS Command Line Tools に基本含まれています。未インストールの場合は、インストールスクリプトの案内に従ってください。

*注: 本プログラムは精密なオーディオ測定器ではなく、動的な視覚演出のためのツールとして設計されています。物理マイクの代わりにコンピューターのシステムオーディオを直接キャプチャしたい場合は、3-7 を参照してください。*

---

## 3. インストールガイド

初回インストール時は、コントローラーを MC モードに設定した後（3-1）、ターミナルで以下のコマンドを実行し、案内に沿って質問に答えるだけで自動的にインストールされます。以降の設定変更や再インストールも、同じコマンドで実行できます。

```zsh
bash ~/xtouch_show/install.sh

```

### 3-1. コントローラーを MC モードに設定

**X-Touch Mini:**

1. USB ケーブルを取り外します。
2. 本体左下の **MC** ボタンを押しながら、USB ケーブルを再度接続します。
3. 右上の **MC MODE** LED が点灯したままになったら、ボタンを離します。

**X-Touch One:**

1. 電源ケーブルを取り外します。
2. 上部エンコーダーを押したまま電源を接続します。
3. エンコーダーを回してモードを選択します。

> [!WARNING] **注意事項**
> * XTouchShow は X-Touch One ファームウェアバージョン 1.10 でテストされています。
> * **MC Standard** と **MC Logic** 環境で互換性が確認されています。
> * 他の MC モードを使用する場合、一部の LED が点灯しないことがあります。
> * MC モードではない場合、いかなる LED も点灯しない現象が確認されています。
> * 特に一部のモードではモーターフェーダーが異常動作する可能性があるため、該当するモードは使用しないでください。
> 
> 

### 3-2. プログラムのインストール

1. ダウンロードした `xtouch_show` フォルダをユーザーのホームディレクトリ（`~/xtouch_show`）に配置します。

> **注意:** `iCloud Drive`、`OneDrive`、`Dropbox`、`Google Drive`、`デスクトップ`、`書類` フォルダ内には配置しないでください。macOS のセキュリティ権限制限により、ログイン時の自動起動機能が正常に動作せず、インストールスクリプトがその場所での実行を拒否します。

2. **ターミナル（Terminal）** アプリを開きます。
3. 以下のインストールコマンドを実行します:

```zsh
bash ~/xtouch_show/install.sh

```

4. **インストールスクリプトの進行プロセス:**

* Python 3 環境を確認し、仮想環境（`.venv`）を作成した後、必要なライブラリ（`python-rtmidi`、`sounddevice`、`numpy`）をインストールします。以降の実行時からは、`requirements.txt` に変更がある場合のみライブラリを再インストールします。
* 設定ファイル（`config.json`）が存在しない場合は、**セットアップウィザード**を自動的に実行します。
* ランチャーアプリ（`XTouchShow.app`）を生成します。該当アプリが初めて実行されるとき、マイク権限の承認ポップアップが表示されます。必ず **[許可]** を選択してください。

*自動起動の有無を問う質問に **N** と答えると自動起動機能が OFF になります。この場合、`bash ~/xtouch_show/manual_start.sh` コマンドで手動実行できます（3-4 参照）。*

*ターミナル以外の環境から実行した場合、すべての設定に関する質問はデフォルト値で自動処理されます。*

### 3-3. セットアップウィザード

`config.json` ファイルが存在しない場合、インストール過程でセットアップウィザードが自動的に実行されます。設定を再構成したい場合は、インストールコマンドを再度実行した後に **"Run the settings wizard again?"** の質問に **y** を入力してください:

```zsh
bash ~/xtouch_show/install.sh

```

ウィザードが完了すると、`install.sh` の残りの手順に従ってショーが自動的に再起動し、新しい設定が即座に反映されます。デフォルト値をそのまま使用する場合は **Enter** キーを押してください。

1. X-Touch Mini 使用の有無 [`mini.enabled`] - デフォルト: X-Touch Mini が現在接続されていれば `y`、そうでなければ `n`
`n` を選択すると Mini を無効化状態に置き、以下の 2 つの Mini の質問（MIDI ポート、トグルボタン）はスキップされます。
2. Mini MIDI 出力ポート [`mini.midi_port_name`] - デフォルト: `"X-TOUCH MINI"`
デバイス番号を選択するか、名前を直接入力します。
3. オーディオ入力デバイス [`audio_input_device`] -デフォルト: システムデフォルト入力
内蔵マイクまたは使用中の外付けデバイスを選択します。両方のコントローラーがこのデバイスを共有します。
4. Mini On/Off トグルボタン [`mini.toggle_button`] - デフォルト: `A`
Layer A または B ボタンのいずれかを選択します。
5. 室内ノイズ測定の有無 [`noise_gate_db`] - デフォルト: `n`（ゲート OFF）
両方のコントローラーで共有します。
6. X-Touch One 使用の有無 [`one.enabled`] - デフォルト: X-Touch One が現在接続されていれば `y`、そうでなければ `n`
`y` を選択すると以下の MC モード確認段階に進み、ビジュアルな `n` を選択するとスキップして One を無効化状態に置きます。
7. X-Touch One は MC モードに設定されていますか？ [`one.enabled`] - デフォルト: `n`
MC モードではない場合、ショーが実行されている間、モーターフェーダーから騒音（カチカチ音）が発生します。前の段階で `y` を選択していたとしても、ここで `n`（デフォルト）を選択すると One は OFF の状態のまま維持され、以下の 3 つの質問はスキップされます。
8. One MIDI 出力ポート [`one.midi_port_name`] - デフォルト: `"X-Touch One"` に一致する最初のポート
デバイス番号を選択するか、名前を入力します。
9. One トグルボタン [`one.toggle_button`] - デフォルト: `Scrub`
33 個の LED ボタン名（例: `BPM`、`F1`-`F6`、`Marker`、`Play`、`Scrub`）のいずれか、または MIDI ノート番号を入力します。
10. One ディスプレイテキスト [`one.display_text`] - デフォルト: `LED ON`
最大 12 文字まで大文字で表示されます。`W` は `U` のように見え、`M`、`K`、`X` は視認性が低下したり紛らわしいため、可能な限り避けることを推奨します。

### 3-4. 手動実行と権限の確認

自動起動の質問に **N** を選択した場合や、ログを直接見ながら問題を診断したい場合は、ターミナルで手動実行します:

```zsh
bash ~/xtouch_show/manual_start.sh

```

詳細なデバッグログを合わせて確認するには `-v` オプションを付与します:

```zsh
bash ~/xtouch_show/manual_start.sh -v

```

### 3-5. 動作確認と調整

1. 音楽を再生して、LED リングが即座に反応するか確認します。
2. **感度調節の方法:**
* LED バーの動きが小さすぎる場合: マイクをソースに近づけるか、`config.json` の `min_db` 値を `-50` または `-40` に上げます。
* LED バーが簡単に最大値まで振り切れてしまう場合: `min_db` 値を `-70` 程度に下げます。
* 静かな環境でも LED が不要に動く場合はノイズゲートを設定します。静かな部屋で以下のコマンドを実行し、**"Measure the room noise for the noise gate?"** の質問に **y** と答えてください:
```zsh
bash ~/xtouch_show/install.sh

```





### 3-6. DAW と一緒に使う

DAW で作業中に XTouchShow を実行すると、ショーが開始される直前の LED 状態を記憶しておき、ショーが終了する際に元の状態に復元してくれます。これを正常に機能させるには、実際の X-Touch Mini や One の代わりに、XTouchShow が提供する仮想 MIDI デバイスをコントロールサーフェス（Surface）として指定する必要があります（Mini は **`X-TOUCH MINI SHOW`**、One は **`X-TOUCH ONE SHOW`**）。

**参考事項:**

* 各仮想デバイスは、**プログラムが実行中で、かつ該当のコントローラーが有効化されている状態の時のみ**表示されます。そのため、自動起動を有効にしておくことを推奨します。
* **ショーを ON/OFF するトグルボタンの入力値は DAW に送信されず、ショープログラムが直接使用します。** Mini は設定した Layer ボタン、One は該当ボタンのプレスノートがこれに該当します。もし該当ボタンを DAW 内の別の機能として使いたい場合は、`mini.toggle_button` または `one.toggle_button` の設定を変更してください。
* DAW を実際のコントローラーに直接接続しても問題ありませんが、この場合はショー終了後に以前の LED 状態へ復元する機能はサポートされません。
* 仮想デバイス機能を全く使用したくない場合は、`config.json` ファイルの `mini` または `one` セクションで `"daw_proxy": false` に設定してください。

### 3-7. 任意: マイクを使えずシステムオーディオを直接キャプチャ

外付けマイクがない場合や、コンピューターの内部オーディオを直接送信したい場合は、仮想ループバックドライバーを介してシステム出力をバイパスさせることができます。*(このプロセスには管理者権限が必要です。)*

1. **BlackHole のインストール**: [ExistentialAudio/BlackHole](https://github.com/ExistentialAudio/BlackHole?utm_source=gemini) から **BlackHole 2ch** インストールファイル（`.pkg`）をダウンロードするか、Homebrew を通じてインストールします（`brew install blackhole-2ch`）。
2. **マルチ出力（Multi-Output）デバイスの設定**:
1. Spotlight を利用して **Audio MIDI 設定** アプリを開きます。
2. ウィンドウ左下の **`+`** ボタンをクリックし、**Multi-Output デバイスを作成** を選択します。
3. 基本出力デバイス（スピーカーまたは DAC）と **BlackHole 2ch** の両方にチェックを入れます。スピーカーをマスター（Primary/Master）に指定し、BlackHole 項目には Drift Correction（ドリ프트補正）を有効にします。
4. 新規作成した Multi-Output デバイスを右クリックし、**このデバイスをサウンド出力に使用** を選択します。


3. **プログラムの設定適用**: 次の 2 つの方法のいずれかで BlackHole をオーディオ入力に指定します。
* `bash ~/xtouch_show/install.sh` を実行し、**"Run the settings wizard again?"** に **y** を入力した後、オーディオ入力デバイスとして **BlackHole 2ch** を選択します。設定が保存された後、ショーが自動的に再起動します。
* または `config.json` ファイルを直接編集して `"audio_input_device": "BlackHole 2ch"` に修正した後、`bash ~/xtouch_show/install.sh` を実行して設定を検証し、ショーを再起動します。手動で実行中だった場合は `Ctrl+C` で終了した後、`bash ~/xtouch_show/manual_start.sh` を再度実行してください。



*注: Multi-Output デバイスを使用している間は、macOS のハードウェア音量調節キーが無効化されます。出力音量はオーディオを再生するアプリ内部で直接調節してください。*

---

## 4. 設定ファイルの説明 (`config.json`)

* 接頭辞が `mini` の場合は X-TOUCH MINI、`one` の場合は X-TOUCH ONE 専用のパラメータです。接頭辞のない項目は共通設定です。

### `mini` / `one` セクションパラメータ

| パラメータ | デフォルト値 | 説明 |
| --- | --- | --- |
| `mini.enabled` | `true` | Mini の使用有無です。`false` に設定すると、機器が接続されていても無視します。 |
| `mini.midi_port_name` | `"X-TOUCH MINI"` | MIDI ポート検索文字列です。 |
| `mini.toggle_button` | `"A"` | トグルスイッチボタン（`"A"` または `"B"`）。 |
| `mini.buttons_enabled` | `true` | ボタン LED レベルバーの有効化有無です（上部 = 絶対レベル、下部 = 相対レベル）。`false` の場合はボタン LED の状態を変更しません。 |
| `mini.daw_proxy` | `true` | DAW がコントローラーの代わりに利用できる仮想 MIDI デバイスを作成します（3-6 参照）。ショーが停止したときに DAW が制御していた LED 状態を復元してくれます。`false` に設定すると仮想デバイスを作成しません。 |
| `mini.daw_proxy_name` | `"X-TOUCH MINI SHOW"` | DAW に表示される仮想デバイスの名前です。 |
| `one.enabled` | `false` | One の使用有無です。`false` に設定すると、機器が接続されていても無視します。 |
| `one.midi_port_name` | `"X-Touch One"` | MIDI ポート検索文字列です。 |
| `one.toggle_button` | `"Scrub"` | 33個の LED ボタン名（大文字小文字不問）のいずれか、または MIDI ノート番号。値が無効な場合は警告とともに `"Scrub"` に自動代替されます。 |
| `one.daw_proxy` | `true` | `mini.daw_proxy` と同じ機能で、One に適用されます（3-6 参照）。 |
| `one.daw_proxy_name` | `"X-TOUCH ONE SHOW"` | DAW に表示される仮想デバイスの名前です。 |
| `one.display_text` | `"LED ON"` | ショーが有効な間、12 文字ディスプレイに表示されるテキストです（3-7 参照）。 |
| `one.display_scroll` | `true` | テキストのスクロール有無です。`false` の場合はスクロールなしで左揃えで固定表示します。 |
| `one.display_scroll_step_s` | `0.3` | テキストが一文字ずつスクロールする間隔（秒）です。 |
| --- | --- | --- |
| `audio_input_device` | `"default"` | 使用するオーディオ入力デバイス名です。 |
| `frame_rate` | `30` | 1 秒あたりの LED 再生頻度（FPS）です。 |
| `decay_per_frame` | `1` | 1 フレームあたりにバー/リングが下降できる最大ステップ数です。 |
| `show_enabled_at_start` | `true` | プログラム実行時にショーを自動的に ON にします。 |
| `show_when_display_off_on_ac` | `false` | 電源アダプター接続状態で画面がスクリプト（スリープ）モードのときもショーを継続実行します。デフォルトは OFF で、画面が消えると LED も消灯し、画面が再び点くまでマイクも遮断されます。 |
| `show_when_display_off_on_battery` | `false` | バッテリー使用状態で画面がスリープモードのときにショーを継続実行するかどうかです。電力節約のためデフォルトは OFF です。 |
| `bar_max_fall_s` | `2.0` | ダイナミックレンジの上限が下がる時定数（秒）です。 |
| `bar_min_rise_s` | `4.0` | ダイナミックレンジの下限が上がる時定数（秒）です。 |
| `band_centers_hz` | `60`–`8000` | Mini の 8 個のエンコーダー LED 帯域の中心周波数です。 |
| `band_gains` | `[1.0, ...]` | 周波数帯域別の個別ゲイン値です。 |
| `min_db` / `max_db` | `-60` / `0` | ダイナミックレンジの下限および上限補正値 (dB) です。 |
| `fft_size` | `4096` | 分析ウィンドウサイズです。値が大きいほど低域周波数の精度が高くなります。 |
| `level_release` | `0.7` | 減衰スムージング係数（0–1）です。値が大きいほどよりゆっくり下降します。 |
| `noise_gate_db` | `null` | `null` は **ノイズゲート OFF**（すべての音が LED に反映される状態）を意味します。数値を指定すると、その dB 閾値より静かな入力は無音とみなして LED 出力を遮断します。 |
| `noise_gate_margin_db` | `4.0` | 室内ノイズ測定およびセットアップウィザードで測定されたノイズに加える余裕値です。 |

---

## 5. トラブルシューティング (Troubleshooting)

* **`MIDI port 'X-TOUCH MINI' not found` / `'X-Touch One' not found` が発生する場合**: USB ケーブルの接続状態を確認し、他の DAW プログラムが該当 MIDI ポートを占有していないか確認してください。コントローラーを所持していない場合は `config.json` で該当デバイスの設定を `false` に変更してください。
* **LED リング/バーが反応しない**: 本体側の **MC MODE** の設定状態を確認してください。DAW が MIDI を占有している場合は DAW を終了するか、DAW の MIDI 入出力設定を `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` デバイスに変更してください（3-6 参照）。

> [!WARNING]
> **モーターライズドフェーダーがカチカチと音を立てる場合**: MC モードではないときに発生する正常な誤動作の症状です。必ず MC モードに設定した上でご使用ください。

* **DAW に `X-TOUCH MINI SHOW` / `X-TOUCH ONE SHOW` デバイスが表示されない**: これらのデバイスはプログラムが実行中で、かつ該当のコントローラーが有効化されているときにのみ動的に生成されます。プログラムを実行した後（`bash ~/xtouch_show/manual_start.sh`）、`logs/xtouch_show.log` ファイルから仮想ポートが正常に生成されたか確認してください。
* **トグルボタンの LED が点灯しない**: MIDI パスが正しく接続されていない状態です。ログから MIDI 接続状態を確認してください。
* **プログラムは実行されるのにバーが 0 に固定される**: macOS のシステム設定（`システム設定 → プライバシーとセキュリティ → マイク`）から **Terminal** または **XTouchShow** アプリのマイク権限が許可されているか確認してください。
* **音楽がないのにバーが動き続ける**: ノイズゲートが OFF になっているため、部屋の生活音が反映されている現象です。静かな環境で `bash ~/xtouch_show/install.sh` を実行して室内ノイズ測定をやり直すか、`config.json` の `noise_gate_db` 値を調整してください。
* **音楽には反応せず、咳払いのような大きな音にのみ反応する**: ノイズゲートの閾値が高すぎる状態です。ゲート値を下げるか `null` に設定して機能を OFF にしてみてください。
* **長時間経過した後にショーが停止する（LED 停止、トグルボタン未作動など）**: プログラムが約 30 秒以内に自動的に再起動しますので、少しお待ちください。同様の問題が繰り返される場合は `bash ~/xtouch_show/install.sh` を再実行してください。
* **バーが小さすぎる、または振り切れる**: `config.json` の `min_db` 値を調節してください（動きが小さすぎる場合は `-50` または `-40`、振り切れる場合は `-70`）。
* **高音域が反応しにくい**: `band_gains` 項目で高域側の値を上方修正してください（例: `1.5`、`2.0`）。
* **終了後もリング/ディスプレイが消えたままになる**: 正常な動作です。MC モードの LED はホストから MIDI 信号が送信されたときのみ更新されます。
* **自動起動が立ち上がらない**: `launchctl print gui/$(id -u)/com.castika.xtouchshow` コマンドで状態を確認するか、`logs/xtouch_show.log` を確認してください。
* **ログに `Operation not permitted` が表示される**: プログラムフォルダが保護されたパス（`デスクトップ`、`書類`またはクラウドフォルダ）に位置しています。フォルダを `~/xtouch_show` のパスに移動させた後、`bash ~/xtouch_show/install.sh` を再度実行してください。
* **自動起動の削除およびショー停止コマンド**（再び有効にするには `bash ~/xtouch_show/install.sh` を実行）:
```zsh
bash ~/xtouch_show/uninstall.sh

```



---

## 6. プロジェクトのファイル構成

```text
xtouch_show/
├── xtouch_show.py     # メインエンジン・スクリプト (MIDI、音響解析、セットアップウィザード)
├── test_show.py       # ハードウェアなしで動作ロジックを検証するツール
├── requirements.txt   # Python 依存関係リスト
├── install.sh         # インストール、設定変更、変更点適用スクリプト
├── uninstall.sh       # 自動起動削除・ショー停止スクリプト
├── manual_start.sh    # ターミナル手動実行スクリプト
├── icon.png           # アプリアイコンの原寸画像 (1024x1024 PNG)
├── README.md          # ガイドドキュメント
├── LICENSE            # MIT ライセンス全文
├── .gitignore         # バージョン管理除外ファイルリスト (.venv、logs、config.json など)
├── config.json        # 実行設定ファイル (セットアップウィザード実行時に生成)
├── XTouchShow.app     # 自動起動用ランチャーアプリ (install.sh が生成、マイク権限を担当)
├── .venv/             # ライブラリがインストールされた Python 仮想環境フォルダ
└── logs/              # 実行ログ保存フォルダ

```

`XTouchShow.app`、`.venv/`、`logs/` フォルダは、ユーザーの Mac 上で `install.sh` およびセットアップウィザードが直接生成する項目であり、ソースファイルには含まれません。

*License: MIT*