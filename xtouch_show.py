#!/usr/bin/env python3
"""
X-Touch Mini music-reactive LED show (MC mode).

While the show is on, the 8 encoder LED rings of the Behringer X-Touch Mini display
an 8-band audio spectrum of whatever a microphone hears (the built-in mic picking up
the speakers, or any other input), and the 16 button LEDs show the loudness as two
bars filling left to right (top row = absolute loudness, bottom row = loudness
relative to the recent minimum/maximum). One Layer button (A or B) switches the show
on and off; its LED is dark while the show is off and blinks while it runs. The fader
scales bar height (sensitivity). An optional noise gate (off by default) keeps plain
room noise from moving the LEDs. Every other knob and button keeps its normal
function; the show ignores it.

Requires: python-rtmidi, sounddevice, numpy.  See README.md.
"""
import argparse
import json
import logging
import os
import sys
import threading
import time

import numpy as np

log = logging.getLogger("xtouch_show")

# ----------------------------------------------------------------------------
# MC-mode protocol constants (verified on hardware 2026-09-11)
# ----------------------------------------------------------------------------
MIDI_CH = 0              # channel 1 (0-based)
CC_MC_MODE = 127         # CC 127 value 1 -> MC mode
RING_CC_BASE = 48        # ring 1..8 = CC 48..55
RING_FAN = 32            # Fan mode offset (0x20); value = 32 + position(0..11)
RING_MAX = 11            # max position in MC mode (12/13 look identical to 11)
ENCODER_CC = range(16, 24)         # encoder turns, relative (ignored by the show)
ENCODER_PUSH_NOTES = range(32, 40) # encoder push switches (ignored by the show)
BUTTON_NOTES = [89, 90, 40, 41, 42, 43, 44, 45,     # top row 1-8
                87, 88, 91, 92, 86, 93, 94, 95]     # bottom row 9-16
LAYER_NOTES = {"A": 84, "B": 85}
FADER_MAX = 16256        # pitch bend max reported by the device (127 << 7)
LED_ON, LED_BLINK, LED_OFF = 127, 1, 0
AUDIO_RETRY_SECONDS = 5.0    # macOS can deny the first stream while the mic permission dialog is open
AUDIO_BLOCKSIZE = 1024       # frames per audio callback; the analyzer's clock unit

DEFAULT_CONFIG = {
    "midi_port_name": "X-TOUCH MINI",
    "audio_input_device": "default",
    "frame_rate": 30,
    "decay_per_frame": 1,
    "toggle_button": "A",
    "show_enabled_at_start": True,
    "buttons_enabled": True,
    "bar_max_fall_s": 2.0,
    "bar_min_rise_s": 4.0,
    "band_centers_hz": [60, 120, 250, 500, 1000, 2000, 4000, 8000],
    "band_gains": [1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0, 1.0],
    "min_db": -60,
    "max_db": 0,
    "fft_size": 4096,
    "level_release": 0.7,
    "noise_gate_db": None,          # null = no noise gate; a number in dB enables it
    "noise_gate_margin_db": 4.0
}

NOISE_CALIBRATION_SECONDS = 3.0   # --calibrate: how long the room noise is measured
NOISE_PERCENTILE = 75             # percentile of the measured blocks; ignores clicks and coughs
DIGITAL_SILENCE_DB = -100.0       # below this the input is not quiet, it is dead (muted or denied)


def load_config(path):
    cfg = dict(DEFAULT_CONFIG)
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        unknown = set(user) - set(cfg)
        if unknown:
            log.warning("config: unknown keys ignored: %s", ", ".join(sorted(unknown)))
        cfg.update({k: v for k, v in user.items() if k in cfg})
    elif path:
        log.warning("config file not found, using defaults: %s", path)
    if cfg["toggle_button"] not in LAYER_NOTES:
        raise ValueError("toggle_button must be 'A' or 'B'")
    if len(cfg["band_centers_hz"]) != 8 or len(cfg["band_gains"]) != 8:
        raise ValueError("band_centers_hz and band_gains must have 8 entries")
    gate = cfg["noise_gate_db"]
    if gate is not None and (isinstance(gate, bool) or not isinstance(gate, (int, float))):
        raise ValueError("noise_gate_db must be null (no noise gate) or a number in dB, "
                         "for example -45.0; got %r" % (gate,))
    return cfg


# ----------------------------------------------------------------------------
# Show logic (no I/O; fully testable)
# ----------------------------------------------------------------------------
class Show:
    """State machine: OFF / ON. Sends MIDI through callbacks."""

    def __init__(self, cfg, send_cc, send_note):
        self.cfg = cfg
        self.send_cc = send_cc
        self.send_note = send_note
        self.toggle_note = LAYER_NOTES[cfg["toggle_button"]]
        self.gains = list(cfg["band_gains"])
        self.decay = int(cfg["decay_per_frame"])
        self.enabled = bool(cfg["show_enabled_at_start"])
        self.buttons_enabled = bool(cfg["buttons_enabled"])
        self.fader_scale = 1.0
        self.current = [0] * 8
        self.last_sent = [-1] * 8
        self.bar_top = 0             # top-row absolute loudness bar, 0..8 buttons lit
        self.bar_bottom = 0          # bottom-row relative loudness bar, 0..8 buttons lit
        self.last_button = [-1] * 16 # last velocity sent per BUTTON_NOTES entry
        self.last_led = None         # last toggle-LED velocity sent; avoids redundant notes
        self.lock = threading.Lock()

    # -- device (re)connect -------------------------------------------------
    def on_connected(self):
        with self.lock:
            self.send_cc(CC_MC_MODE, 1)
            self.last_sent = [-1] * 8
            self.last_button = [-1] * 16
            self.last_led = None          # the device forgot its LEDs, re-send
            self._clear_rings()
            self._clear_buttons()
            self._set_toggle_led()
            log.info("device ready | state=%s | toggle=Layer %s (note %d)",
                     self.state, self.cfg["toggle_button"], self.toggle_note)

    # -- input events (called from MIDI thread) ----------------------------
    def on_midi(self, msg):
        """Only two controls belong to the show: the toggle button and the fader. The rest is ignored."""
        if len(msg) < 3:
            return
        status, d1, d2 = msg[0], msg[1], msg[2]
        kind, ch = status & 0xF0, status & 0x0F
        if kind == 0xE0 and ch == 8:                                  # pitch bend, channel 9 = fader
            self._on_fader((d2 << 7) | d1)
        elif kind == 0x90 and d2 > 0 and d1 == self.toggle_note:      # note on, toggle button
            self._toggle()

    def _on_fader(self, value14):
        self.fader_scale = max(0.0, min(1.0, value14 / FADER_MAX))

    def _toggle(self):
        with self.lock:
            self.enabled = not self.enabled
            if not self.enabled:
                self._clear_rings()
                self._clear_buttons()
            self._set_toggle_led()
            log.info("show %s (Layer %s)", "ON" if self.enabled else "OFF", self.cfg["toggle_button"])

    # -- periodic update (called from main loop) ---------------------------
    def tick(self, dt, levels, loudness=0.0, loudness_rel=None):
        with self.lock:
            if not self.enabled:
                return
            self._render(levels)
            self._render_buttons(loudness, 0.0 if loudness_rel is None else loudness_rel)

    def _render(self, levels):
        for i in range(8):
            level = min(1.0, max(0.0, float(levels[i]) * self.gains[i]))
            target = int(round(level * self.fader_scale * RING_MAX))
            if target < self.current[i]:
                self.current[i] = max(target, self.current[i] - self.decay)
            else:
                self.current[i] = target
            if self.current[i] != self.last_sent[i]:
                self.send_cc(RING_CC_BASE + i, RING_FAN + self.current[i])
                self.last_sent[i] = self.current[i]

    def _render_buttons(self, loudness, loudness_rel):
        """Top row = absolute loudness bar, bottom row = relative loudness bar; both fill left->right."""
        if not self.buttons_enabled:
            return
        self.bar_top = self._step_bar(self.bar_top, loudness)
        self.bar_bottom = self._step_bar(self.bar_bottom, loudness_rel)
        for i in range(8):
            self._send_button(i, LED_ON if i < self.bar_top else LED_OFF)
            self._send_button(8 + i, LED_ON if i < self.bar_bottom else LED_OFF)

    def _step_bar(self, bar, loudness):
        """Next bar height in buttons: rises at once, falls at most decay_per_frame per frame."""
        level = min(1.0, max(0.0, float(loudness)))
        target = int(round(level * self.fader_scale * 8))
        return max(target, bar - self.decay) if target < bar else target

    def _send_button(self, i, velocity):
        if velocity != self.last_button[i]:
            self.send_note(BUTTON_NOTES[i], velocity)
            self.last_button[i] = velocity

    def _clear_rings(self):
        for i in range(8):
            self.send_cc(RING_CC_BASE + i, RING_FAN)
            self.current[i] = 0
            self.last_sent[i] = 0

    def _clear_buttons(self):
        if not self.buttons_enabled:
            return
        for i in range(16):
            self.send_note(BUTTON_NOTES[i], LED_OFF)
            self.last_button[i] = LED_OFF
        self.bar_top = 0
        self.bar_bottom = 0

    def _set_toggle_led(self):
        """OFF -> dark, ON -> blinking. Sent only when it changes."""
        velocity = LED_BLINK if self.enabled else LED_OFF
        if velocity != self.last_led:
            self.send_note(self.toggle_note, velocity)
            self.last_led = velocity

    @property
    def state(self):
        return "ON" if self.enabled else "OFF"


# ----------------------------------------------------------------------------
# Audio analysis
# ----------------------------------------------------------------------------
def block_decay(block_s, tau_s):
    """Per-block factor of an exponential decay with time constant tau_s (falls to ~37 % in tau_s)."""
    return float(np.exp(-block_s / max(1e-3, float(tau_s))))


class SpectrumAnalyzer:
    """Rolling FFT over the input stream; exposes 8 band levels and the broadband loudness
    (absolute and normalised to the recent min/max). An optional noise gate keeps room
    noise out: when `noise_gate_db` is a number, blocks quieter than it count as silence;
    when it is None there is no gate and every block is analysed."""

    def __init__(self, cfg):
        import sounddevice as sd
        self.sd = sd
        self.device_index, self.device_name = self._pick_device(cfg["audio_input_device"])
        self._init_state(cfg, sd.query_devices(self.device_index)["default_samplerate"])

    def _init_state(self, cfg, samplerate):
        """All state that does not touch sounddevice; the tests build an analyzer through this."""
        self.cfg = cfg
        self.samplerate = int(samplerate)
        self.n = int(cfg["fft_size"])
        self.buf = np.zeros(self.n, dtype=np.float32)
        self.window = np.hanning(self.n).astype(np.float32)
        self.levels = np.zeros(8, dtype=np.float32)
        self.loudness = 0.0
        self.loudness_rel = 0.0
        self.release = float(cfg["level_release"])
        gate = cfg["noise_gate_db"]
        self.noise_gate_db = None if gate is None else float(gate)   # None = no gate
        self.loud_db = -120.0        # latest broadband level in dB
        # True while that level is above the noise gate; always True when there is no gate
        self.gate_open = self.noise_gate_db is None
        self.lock = threading.Lock()
        self.stream = None
        self.block_s = AUDIO_BLOCKSIZE / float(self.samplerate)   # one callback block, in seconds
        # rolling min/max envelopes of the loudness -> relative bar
        self.loud_hi, self.loud_lo = 0.0, 1.0
        self.hi_decay = block_decay(self.block_s, cfg["bar_max_fall_s"])
        self.lo_rate = 1.0 - block_decay(self.block_s, cfg["bar_min_rise_s"])
        self._build_bins()

    def _pick_device(self, wanted):
        """'default' (or empty) = the system default input; otherwise exact name, then substring."""
        devs = self.sd.query_devices()
        wanted = (wanted or "").strip()
        if wanted.lower() in ("", "default"):
            return self._default_device(devs)
        inputs = [(i, d) for i, d in enumerate(devs) if d["max_input_channels"] > 0]
        for i, d in inputs:
            if d["name"] == wanted:
                return i, d["name"]
        for i, d in inputs:
            if wanted.lower() in d["name"].lower():
                return i, d["name"]
        index, name = self._default_device(devs)
        log.warning("audio input '%s' not found; using default input '%s'", wanted, name)
        return index, name

    def _default_device(self, devs):
        default = self.sd.default.device[0]
        if default is None or default < 0:
            raise RuntimeError("no audio input device available")
        return default, devs[default]["name"]

    def _build_bins(self):
        centers = np.array(self.cfg["band_centers_hz"], dtype=float)
        # geometric edges between neighbouring centers; outer edges by same ratio
        ratio = np.sqrt(centers[1:] / centers[:-1])
        edges = np.concatenate(([centers[0] / ratio[0]], np.sqrt(centers[1:] * centers[:-1]), [centers[-1] * ratio[-1]]))
        freqs = np.fft.rfftfreq(self.n, 1.0 / self.samplerate)
        self.band_bins = []
        for lo, hi in zip(edges[:-1], edges[1:]):
            idx = np.where((freqs >= lo) & (freqs < hi))[0]
            if len(idx) == 0:
                idx = np.array([int(np.argmin(np.abs(freqs - (lo + hi) / 2)))])
            self.band_bins.append(idx)
        self.win_gain = self.window.sum() / 2.0     # full-scale sine -> ~0 dB

    def _callback(self, indata, frames, time_info, status):
        mono = indata[:, 0] if indata.ndim > 1 else indata
        if indata.ndim > 1 and indata.shape[1] > 1:
            mono = indata.mean(axis=1)
        k = len(mono)
        if k >= self.n:
            self.buf[:] = mono[-self.n:]
        else:
            self.buf = np.roll(self.buf, -k)
            self.buf[-k:] = mono
        spec = np.abs(np.fft.rfft(self.buf * self.window)) / self.win_gain
        power = spec * spec
        lo, hi = float(self.cfg["min_db"]), float(self.cfg["max_db"])
        new = np.zeros(8, dtype=np.float32)
        for i, idx in enumerate(self.band_bins):
            p = float(power[idx].sum())      # band energy: octave-spaced bands stay balanced for music
            db = 10.0 * np.log10(p + 1e-12)
            new[i] = min(1.0, max(0.0, (db - lo) / (hi - lo)))
        total_db = 10.0 * np.log10(float(power.sum()) + 1e-12)   # broadband level: every bin, not just the 8 bands
        gate_open = self.noise_gate_db is None or total_db > self.noise_gate_db
        if not gate_open:
            # room noise only: aim at silence, but let the release smoothing take the LEDs down
            new[:] = 0.0
        loud = min(1.0, max(0.0, (total_db - lo) / (hi - lo))) if gate_open else 0.0
        with self.lock:
            self.loud_db = total_db
            self.gate_open = gate_open
            # instant attack, smoothed release
            self.levels = np.maximum(new, self.levels * self.release)
            self.loudness = max(loud, self.loudness * self.release)
            if gate_open:
                self._track_loudness(self.loudness)
            else:
                # the min/max envelopes must not learn the noise floor, so only the bar decays
                self.loudness_rel *= self.release

    def _track_loudness(self, loud):
        """Normalise the loudness against its own recent range, so quiet-but-dynamic music still fills the bar."""
        self.loud_hi = max(loud, self.loud_hi * self.hi_decay)
        self.loud_lo = min(loud, self.loud_lo + (loud - self.loud_lo) * self.lo_rate)
        span = max(self.loud_hi - self.loud_lo, 0.1)
        self.loudness_rel = min(1.0, max(0.0, (loud - self.loud_lo) / span))

    def start(self):
        self.stream = self.sd.InputStream(device=self.device_index, channels=1, samplerate=self.samplerate,
                                          blocksize=AUDIO_BLOCKSIZE, dtype="float32", callback=self._callback)
        self.stream.start()
        log.info("audio input: '%s' @ %d Hz, fft %d", self.device_name, self.samplerate, self.n)

    def stop(self):
        stream = getattr(self, "stream", None)
        self.stream = None
        if stream is None:
            return
        for close in (stream.stop, stream.close):
            try:
                close()
            except Exception:
                pass

    def get_levels(self):
        with self.lock:
            return self.levels.copy()

    def get_loudness(self):
        with self.lock:
            return float(self.loudness)

    def get_loudness_rel(self):
        with self.lock:
            return float(self.loudness_rel)

    def get_loud_db(self):
        """Broadband level of the latest block, in dB (the value the noise gate compares)."""
        with self.lock:
            return float(self.loud_db)

    def get_gate_open(self):
        with self.lock:
            return bool(self.gate_open)

    def get_gate_status(self):
        """'off' when no gate is configured, otherwise the current open/closed state."""
        return "off" if self.noise_gate_db is None else self.get_gate_open()


# ----------------------------------------------------------------------------
# Noise-gate calibration
# ----------------------------------------------------------------------------
def recommended_gate_db(cfg, measured_db):
    """The gate to use for a room whose noise floor measured `measured_db`."""
    return round(float(measured_db) + float(cfg["noise_gate_margin_db"]), 1)


def _percentile_low(values, percent):
    """Percentile picking the nearest sample at or below it: a single click cannot pull it up."""
    ordered = sorted(float(v) for v in values)
    return ordered[min(len(ordered) - 1, int(percent / 100.0 * (len(ordered) - 1)))]


def _measure_noise_db(cfg, seconds, stream_factory):
    """Open the input for `seconds` and return the broadband dB level of every audio block."""
    analyzer = stream_factory(cfg) if stream_factory else SpectrumAnalyzer(cfg)
    values = []
    analyze_block = analyzer._callback

    def record(indata, frames, time_info, status):
        analyze_block(indata, frames, time_info, status)
        values.append(analyzer.get_loud_db())

    analyzer._callback = record        # start() reads the callback off the instance
    try:
        analyzer.start()
        time.sleep(max(0.1, float(seconds)))
    finally:
        analyzer.stop()
    return values


def calibrate_noise(cfg, seconds=NOISE_CALIBRATION_SECONDS, samples=None, stream_factory=None):
    """Measure the room noise floor in dB.

    Listens for `seconds` and returns the 75th percentile of the per-block broadband levels,
    so a chair creak or a keystroke does not raise the result, and intermittent talking or
    music left playing during the measurement inflates it far less than a high percentile
    would. `samples` (a list of dB values) and `stream_factory` replace the real input;
    the tests use them.
    """
    values = list(samples) if samples is not None else _measure_noise_db(cfg, seconds, stream_factory)
    if not values:
        raise RuntimeError("no audio was captured")
    return round(_percentile_low(values, NOISE_PERCENTILE), 1)


# ----------------------------------------------------------------------------
# MIDI I/O with hot-plug handling
# ----------------------------------------------------------------------------
class MidiLink:
    def __init__(self, port_name, on_message):
        import rtmidi
        self.rtmidi = rtmidi
        self.port_name = port_name
        self.on_message = on_message
        self.midi_in = None
        self.midi_out = None
        self.lock = threading.Lock()

    def _find(self, ports):
        for i, p in enumerate(ports):
            if p == self.port_name:
                return i
        for i, p in enumerate(ports):
            if self.port_name.lower() in p.lower():
                return i
        return None

    def connected(self):
        return self.midi_out is not None

    def try_connect(self):
        mi, mo = self.rtmidi.MidiIn(), self.rtmidi.MidiOut()
        ii, oi = self._find(mi.get_ports()), self._find(mo.get_ports())
        if ii is None or oi is None:
            return False
        mi.open_port(ii)
        mi.ignore_types(sysex=True, timing=True, active_sense=True)
        mi.set_callback(lambda event, data=None: self.on_message(event[0]))
        mo.open_port(oi)
        with self.lock:
            self.midi_in, self.midi_out = mi, mo
        log.info("MIDI connected: '%s'", mo.get_ports()[oi])
        return True

    def still_present(self):
        return self._find(self.rtmidi.MidiOut().get_ports()) is not None

    def disconnect(self):
        with self.lock:
            for p in (self.midi_in, self.midi_out):
                if p:
                    try:
                        p.close_port()
                    except Exception:
                        pass
            self.midi_in = self.midi_out = None
        log.warning("MIDI disconnected")

    def send_cc(self, cc, value):
        self._send([0xB0 | MIDI_CH, cc & 0x7F, value & 0x7F])

    def send_note(self, note, velocity):
        self._send([0x90 | MIDI_CH, note & 0x7F, velocity & 0x7F])

    def _send(self, msg):
        with self.lock:
            if self.midi_out:
                try:
                    self.midi_out.send_message(msg)
                except Exception as e:
                    log.warning("MIDI send failed: %s", e)


# ----------------------------------------------------------------------------
# Main
# ----------------------------------------------------------------------------
def list_devices():
    import rtmidi
    import sounddevice as sd
    print("MIDI inputs :", rtmidi.MidiIn().get_ports())
    print("MIDI outputs:", rtmidi.MidiOut().get_ports())
    print("Audio inputs:")
    for i, d in enumerate(sd.query_devices()):
        if d["max_input_channels"] > 0:
            print("  [%d] %s  (%d ch, %.0f Hz)" % (i, d["name"], d["max_input_channels"], d["default_samplerate"]))


# ----------------------------------------------------------------------------
# Setup wizard (--setup)
# ----------------------------------------------------------------------------
def _midi_output_ports():
    """Output port names, or None when rtmidi is missing / the enumeration fails."""
    try:
        import rtmidi
        return list(rtmidi.MidiOut().get_ports())
    except Exception as e:
        print("  Could not list the MIDI ports (%s). Type the name by hand." % e)
        return None


def _audio_input_devices():
    """(input device names, default input name), or (None, None) when the enumeration fails."""
    try:
        import sounddevice as sd
        names = [d["name"] for d in sd.query_devices() if d["max_input_channels"] > 0]
        default = sd.default.device[0]
        default_name = sd.query_devices(default)["name"] if default is not None and default >= 0 else None
        return names, default_name
    except Exception as e:
        print("  Could not list the audio input devices (%s). Type the name by hand." % e)
        return None, None


def _write_config(path, cfg):
    with open(path, "w", encoding="utf-8") as f:
        json.dump(cfg, f, ensure_ascii=False, indent=2)
        f.write("\n")


def _update_config_key(path, cfg, key, value):
    """Write one key into `path`, keeping every other key that is already in the file."""
    stored = dict(cfg)
    if os.path.exists(path):
        try:
            with open(path, encoding="utf-8") as f:
                stored = json.load(f)
        except Exception as e:
            print("Could not read %s (%s); writing a fresh file." % (path, e))
    stored[key] = value
    _write_config(path, stored)


def _print_list(items):
    if not items:
        print("  (the list is empty)")
        return
    for i, name in enumerate(items, 1):
        print("  [%d] %s" % (i, name))


def _first_match(items, needle):
    for name in items or []:
        if needle.lower() in name.lower():
            return name
    return None


def _ask_name(ask, prompt, items, default):
    """Number from the printed list, a name typed by hand, or Enter for `default`."""
    while True:
        answer = ask("%s [%s]: " % (prompt, default)).strip()
        if not answer:
            return default
        if answer.isdigit():
            n = int(answer)
            if items and 1 <= n <= len(items):
                return items[n - 1]
            print("  That number is not in the list. Enter a number or a device name.")
            continue
        return answer


def _ask_choice(ask, prompt, choices, default):
    while True:
        answer = ask("%s [%s]: " % (prompt, default)).strip().upper()
        if not answer:
            return default
        if answer in choices:
            return answer
        print("  Enter one of: %s." % " / ".join(choices))


def _ask_yes_no(ask, prompt, default, hint=None):
    """`hint` is appended to the bracketed default, e.g. '[n, current: -41.0]'."""
    label = "y" if default else "n"
    if hint:
        label = "%s, %s" % (label, hint)
    while True:
        answer = ask("%s [%s]: " % (prompt, label)).strip().lower()
        if not answer:
            return default
        if answer in ("y", "yes"):
            return True
        if answer in ("n", "no"):
            return False
        print("  Enter y or n.")


def run_setup(config_path, ask=input, midi_ports=None, audio_devices=None, noise_samples=None):
    """Interactive first-time setup. Writes `config_path` and returns an exit code.

    `ask`, `midi_ports` and `audio_devices` can be injected so the wizard runs without a terminal
    (the tests do that); `audio_devices` is a list of input device names. `noise_samples` replaces
    the real input of the noise measurement in the same way: under an injected `ask` the
    measurement is skipped unless the samples are given.
    """
    if ask is input and not sys.stdin.isatty():
        print("--setup must be run from a terminal (standard input is not a terminal).", file=sys.stderr)
        return 2

    cfg = dict(DEFAULT_CONFIG)
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                cfg.update({k: v for k, v in json.load(f).items() if k in cfg})
            print("Loaded the existing settings: %s" % config_path)
        except Exception as e:
            print("Could not read the existing settings, starting from the defaults (%s)." % e)

    print("\nX-Touch Mini Music-Reactive LED Show setup (Enter = the default in brackets)\n")

    print("1) MIDI output port [midi_port_name]")
    if midi_ports is None:
        midi_ports = _midi_output_ports()
    _print_list(midi_ports)
    default_port = _first_match(midi_ports, "X-TOUCH MINI") or cfg["midi_port_name"]
    cfg["midi_port_name"] = _ask_name(ask, "   Number or port name", midi_ports, default_port)

    print("\n2) Audio input device [audio_input_device]")
    print("   Pick the microphone that will hear the music (choose BlackHole 2ch if you installed it)")
    default_input = None
    if audio_devices is None:
        audio_devices, default_input = _audio_input_devices()
    _print_list(audio_devices)
    default_dev = default_input or cfg["audio_input_device"]
    cfg["audio_input_device"] = _ask_name(ask, "   Number or device name", audio_devices, default_dev)

    print("\n3) Button that switches the show on and off [toggle_button]: Layer A or B")
    cfg["toggle_button"] = _ask_choice(ask, "   A/B", ("A", "B"), cfg["toggle_button"])

    print("\n4) Use the two button-LED loudness bars? [buttons_enabled]")
    cfg["buttons_enabled"] = _ask_yes_no(ask, "   y/n", bool(cfg["buttons_enabled"]))

    print("\n5) Noise gate [noise_gate_db]")
    print("   The noise gate is off by default. Enable it only if room noise alone moves the")
    print("   LEDs: the measurement sets the level below which the input counts as silence.")
    current = cfg["noise_gate_db"]
    if current is None:
        print("   Answering n leaves the gate off.")
        hint = None
    else:
        print("   Answering n keeps the current gate (%.1f dB)." % float(current))
        hint = "current: %.1f" % float(current)
    if _ask_yes_no(ask, "   Measure room noise now to enable the noise gate?", False, hint):
        _setup_noise_gate(cfg, ask, noise_samples)

    _write_config(config_path, cfg)
    print("\nSettings saved: %s" % config_path)
    return 0


def _gate_text(value):
    """How a noise_gate_db value is shown to the user: 'off' for None, else the dB value."""
    return "off" if value is None else "%.1f" % float(value)


def _setup_noise_gate(cfg, ask, noise_samples):
    """Measure the room noise with the device chosen above and store the recommended gate."""
    if noise_samples is None and ask is not input:
        print("   Skipped (no audio input here); keeping noise_gate_db %s." % _gate_text(cfg["noise_gate_db"]))
        return
    print("   Measuring room noise for %.0f seconds. Keep quiet." % NOISE_CALIBRATION_SECONDS)
    try:
        measured = calibrate_noise(cfg, samples=noise_samples)
    except Exception as e:
        print("   The measurement failed (%s); keeping noise_gate_db %s."
              % (e, _gate_text(cfg["noise_gate_db"])))
        return
    cfg["noise_gate_db"] = recommended_gate_db(cfg, measured)
    print("   Room noise %.1f dB -> noise_gate_db %.1f." % (measured, cfg["noise_gate_db"]))


def run_calibrate(cfg, config_path, seconds=NOISE_CALIBRATION_SECONDS, samples=None, stream_factory=None):
    """--calibrate: measure the room noise, print and store the recommended gate."""
    print("Measuring room noise for %.0f seconds. Keep quiet." % seconds)
    try:
        measured = calibrate_noise(cfg, seconds=seconds, samples=samples, stream_factory=stream_factory)
    except Exception as e:
        print("The measurement failed (%s). Check the audio input device and the microphone "
              "permission." % e, file=sys.stderr)
        return 2
    gate = recommended_gate_db(cfg, measured)
    print("Room noise: %.1f dB" % measured)
    print("Recommended noise_gate_db: %.1f (room noise + %.1f dB margin)" % (gate, cfg["noise_gate_margin_db"]))
    print("If music later fails to open the gate, run the calibration again in a quieter "
          "moment or lower noise_gate_db in config.json. Setting noise_gate_db back to "
          "null switches the gate off again.")
    _update_config_key(config_path, cfg, "noise_gate_db", gate)
    print("Saved to %s. Restart the show to use it." % config_path)
    return 0


def ring_test(link):
    """Sweep all rings up and down, then light the Layer LEDs. Used to verify the MIDI path."""
    link.send_cc(CC_MC_MODE, 1)
    time.sleep(0.2)
    for n in list(range(0, RING_MAX + 1)) + list(range(RING_MAX - 1, -1, -1)):
        for i in range(8):
            link.send_cc(RING_CC_BASE + i, RING_FAN + n)
        time.sleep(0.06)
    link.send_note(LAYER_NOTES["A"], LED_ON)
    link.send_note(LAYER_NOTES["B"], LED_BLINK)
    time.sleep(1.0)
    link.send_note(LAYER_NOTES["A"], LED_OFF)
    link.send_note(LAYER_NOTES["B"], LED_OFF)
    log.info("ring test done (all rings swept 0->11->0, Layer A on / B blink for 1 s)")


def open_audio(cfg):
    """Build and start a SpectrumAnalyzer. Returns (analyzer, None) or (None, exception)."""
    analyzer = None
    try:
        analyzer = SpectrumAnalyzer(cfg)
        analyzer.start()
        return analyzer, None
    except Exception as e:
        if analyzer is not None:
            analyzer.stop()
        return None, e


def main(argv=None):
    ap = argparse.ArgumentParser(description="X-Touch Mini music-reactive LED show (MC mode)")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    ap.add_argument("--list-devices", action="store_true", help="list MIDI and audio devices and exit")
    ap.add_argument("--setup", action="store_true", help="interactive setup wizard: write config.json and exit")
    ap.add_argument("--test-rings", action="store_true", help="sweep the rings once and exit (MIDI path check)")
    ap.add_argument("--calibrate", action="store_true",
                    help="measure the room noise and write the recommended noise_gate_db into the "
                         "config (this enables the noise gate; set noise_gate_db back to null to "
                         "switch it off)")
    ap.add_argument("--calibrate-seconds", type=float, default=NOISE_CALIBRATION_SECONDS,
                    help="how many seconds --calibrate listens to the room (default %.0f)"
                         % NOISE_CALIBRATION_SECONDS)
    ap.add_argument("--input", help="override audio_input_device")
    ap.add_argument("--no-audio", action="store_true", help="run without audio (rings stay at 0); for MIDI-only tests")
    ap.add_argument("--duration", type=float, help="quit automatically after this many seconds (for tests)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%H:%M:%S")

    if args.list_devices:
        list_devices()
        return 0

    if args.setup:
        try:
            return run_setup(args.config)
        except (EOFError, KeyboardInterrupt):
            print("\nSetup cancelled.")
            return 2

    if not os.path.exists(args.config) and sys.stdin.isatty():
        log.info("no config file yet: run '%s %s --setup' to create one (defaults are used until then)",
                 os.path.basename(sys.executable), os.path.basename(__file__))

    cfg = load_config(args.config)
    if args.input:
        cfg["audio_input_device"] = args.input

    if args.calibrate:
        return run_calibrate(cfg, args.config, seconds=args.calibrate_seconds)

    link = MidiLink(cfg["midi_port_name"], on_message=lambda m: None)
    if args.test_rings:
        if not link.try_connect():
            log.error("MIDI port '%s' not found. Use --list-devices.", cfg["midi_port_name"])
            return 2
        ring_test(link)
        return 0

    show = Show(cfg, send_cc=link.send_cc, send_note=link.send_note)
    link.on_message = show.on_midi

    analyzer = None
    if not args.no_audio:
        analyzer, audio_error = open_audio(cfg)
        if analyzer is None:
            log.error("audio input failed (%s). Retrying every %.0f s "
                      "(macOS may still be asking for microphone permission).", audio_error, AUDIO_RETRY_SECONDS)

    frame = 1.0 / float(cfg["frame_rate"])
    last_check = 0.0
    last_audio_try = time.monotonic()
    last = time.monotonic()
    silent_since = None
    t_end = time.monotonic() + args.duration if args.duration else None
    last_status = 0.0
    log.info("started | fps=%s toggle=Layer %s | Ctrl-C to quit",
             cfg["frame_rate"], cfg["toggle_button"])
    try:
        while True:
            now = time.monotonic()
            if t_end and now >= t_end:
                log.info("duration reached, quitting")
                break
            if args.verbose and now - last_status >= 5.0 and analyzer:
                last_status = now
                log.debug("state=%s fader=%.2f loud=%.2f rel=%.2f db=%.1f gate=%s levels=%s",
                          show.state, show.fader_scale, analyzer.get_loudness(),
                          analyzer.get_loudness_rel(), analyzer.get_loud_db(), analyzer.get_gate_status(),
                          " ".join("%.2f" % v for v in analyzer.get_levels()))
            if analyzer is None and not args.no_audio and now - last_audio_try >= AUDIO_RETRY_SECONDS:
                last_audio_try = now
                analyzer, audio_error = open_audio(cfg)
                if analyzer is not None:
                    silent_since = None
                    log.info("audio input ready")
                else:
                    log.debug("audio input still unavailable (%s)", audio_error)
            if now - last_check >= 2.0:
                last_check = now
                if link.connected():
                    if not link.still_present():
                        link.disconnect()
                elif link.try_connect():
                    show.on_connected()
                else:
                    log.debug("waiting for MIDI port '%s'", cfg["midi_port_name"])
            levels = analyzer.get_levels() if analyzer else np.zeros(8)
            loudness = analyzer.get_loudness() if analyzer else 0.0
            loudness_rel = analyzer.get_loudness_rel() if analyzer else None
            if analyzer and show.enabled:
                # digital silence, not just a quiet room: a denied microphone reads exactly zero,
                # while real room noise sits well above the floor even with the gate closed
                if analyzer.get_loud_db() <= DIGITAL_SILENCE_DB:
                    if silent_since is None:
                        silent_since = now
                    elif now - silent_since > 15:
                        log.warning("the audio input has delivered pure silence for 15 s: check the input "
                                    "device and the microphone permission")
                        silent_since = now
                else:
                    silent_since = None
            if link.connected():
                show.tick(now - last, levels, loudness, loudness_rel)
            last = now
            time.sleep(max(0.0, frame - (time.monotonic() - now)))
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        if link.connected():
            with show.lock:
                show._clear_rings()
                show._clear_buttons()
                link.send_note(show.toggle_note, LED_OFF)
        if analyzer:
            analyzer.stop()
        link.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
