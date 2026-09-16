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

While the display is asleep the show keeps running on the power adapter and stops on
battery (both configurable), and it re-initializes itself after the Mac wakes from sleep.

Requires: python-rtmidi, sounddevice, numpy.  See README.md.
"""
import argparse
import ctypes
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
WAKE_JUMP_SECONDS = 3.0      # wall clock running this far ahead of the monotonic clock = the Mac slept
DEVICE_CHECK_SECONDS = 2.0   # how often the MIDI port, the display and the power source are polled
AUDIO_CLOSE_TIMEOUT = 3.0    # how long closing the audio stream may take before it is abandoned
WATCHDOG_SECONDS = 15.0      # no main-loop iteration for this long = the loop is stuck
WATCHDOG_CHECK_SECONDS = 5.0 # how often the watchdog compares the clocks
POLL_STALL_SECONDS = 30.0    # no finished device poll for this long = the poller is stuck
EXIT_STALLED = 3             # exit code the watchdog uses; launchd KeepAlive restarts the show

DEFAULT_CONFIG = {
    "midi_port_name": "X-TOUCH MINI",
    "audio_input_device": "default",
    "frame_rate": 30,
    "decay_per_frame": 1,
    "toggle_button": "A",
    "show_enabled_at_start": True,
    "buttons_enabled": True,
    "show_when_display_off_on_ac": False,      # power adapter connected: stop the show while the display is asleep
    "show_when_display_off_on_battery": False, # on battery: stop the show while the display is asleep
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

    def clear_output(self):
        """Take the rings and the button LEDs out once without changing the ON/OFF state.

        Used while the show is suspended (the display is asleep): the toggle LED is left
        alone, so it keeps blinking to show the show is still switched ON, and the next
        `tick` renders from scratch.
        """
        with self.lock:
            self._clear_rings()
            self._clear_buttons()

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
    """The MIDI ports of the device, with the port list read through one long-lived pair.

    Every `rtmidi.MidiIn()` / `MidiOut()` is a new CoreMIDI client, and asking a fresh
    client for its port names has to look every endpoint up again - which can block for
    a long time while the USB bus re-enumerates (a Thunderbolt display waking the hub
    the device hangs off). The two probe objects below are created once and answer every
    later port scan; the ports that are really opened stay separate objects, so closing
    them never disturbs the scanning.
    """

    def __init__(self, port_name, on_message):
        import rtmidi
        self.rtmidi = rtmidi
        self.port_name = port_name
        self.on_message = on_message
        self.midi_in = None
        self.midi_out = None
        self.lock = threading.Lock()
        self.probe_in = rtmidi.MidiIn()      # never opened: used only to list the ports
        self.probe_out = rtmidi.MidiOut()

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
        in_ports, out_ports = self.probe_in.get_ports(), self.probe_out.get_ports()
        ii, oi = self._find(in_ports), self._find(out_ports)
        if ii is None or oi is None:
            return False
        mi, mo = self.rtmidi.MidiIn(), self.rtmidi.MidiOut()
        mi.open_port(ii)
        mi.ignore_types(sysex=True, timing=True, active_sense=True)
        mi.set_callback(lambda event, data=None: self.on_message(event[0]))
        mo.open_port(oi)
        with self.lock:
            self.midi_in, self.midi_out = mi, mo
        log.info("MIDI connected: '%s'", out_ports[oi])
        return True

    def still_present(self):
        return self._find(self.probe_out.get_ports()) is not None

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


def stop_analyzer(analyzer, timeout=AUDIO_CLOSE_TIMEOUT):
    """Stop an analyzer's stream without ever blocking the caller for long.

    Closing a CoreAudio stream normally takes milliseconds, but it can hang when the
    interface behind it disappears (a display that hosts the microphone going to sleep).
    The close therefore runs on a daemon thread: after `timeout` the stream is abandoned
    - one leaked stream object costs far less than a frozen show. Returns True when the
    close finished in time.
    """
    done = threading.Event()

    def run():
        try:
            analyzer.stop()
        finally:
            done.set()

    threading.Thread(target=run, name="audio-close", daemon=True).start()
    if done.wait(timeout):
        return True
    log.warning("audio stream did not close in time; abandoning it")
    return False


def open_audio(cfg):
    """Build and start a SpectrumAnalyzer. Returns (analyzer, None) or (None, exception)."""
    analyzer = None
    try:
        analyzer = SpectrumAnalyzer(cfg)
        analyzer.start()
        return analyzer, None
    except Exception as e:
        if analyzer is not None:
            stop_analyzer(analyzer)
        return None, e


class AudioController:
    """Owns the audio input stream and keeps it open only while it is wanted.

    The microphone must not stay open when nothing can use it, so `update(now, wanted)`
    opens the stream the first time it is wanted, closes it as soon as it is not, and
    returns the analyzer to read from (None while the stream is closed). `wanted` is
    the caller's decision - in the show that is "MIDI device connected and show ON".
    A failed open is retried every `retry_seconds`, but only while the stream is still
    wanted, so an unplugged device or a show that is off costs no attempts at all.

    Opening runs on a daemon thread and `update` never waits for it: the first open after
    the app bundle was rebuilt can sit inside CoreAudio for half a minute while macOS
    re-evaluates the microphone permission, and a main loop blocked that long is a stalled
    show the watchdog would kill. Only one open is ever in flight; a stream that arrives
    after it stopped being wanted is stopped instead of used.
    """

    def __init__(self, cfg, open_fn=None, retry_seconds=AUDIO_RETRY_SECONDS,
                 close_timeout=AUDIO_CLOSE_TIMEOUT):
        self.cfg = cfg
        self.open_fn = open_fn if open_fn is not None else open_audio
        self.retry_seconds = float(retry_seconds)
        self.close_timeout = float(close_timeout)
        self.analyzer = None
        self.last_try = None     # when the last open finished failing; None = try at once
        self.failed = False      # a failure streak is running; its error was already reported
        self.lock = threading.Lock()
        self.opening = False     # an open thread is in flight; its result is not collected yet
        self.abandoned = False   # that open is no longer wanted: stop whatever it returns
        self.result = None       # (analyzer, error) handed over by the open thread

    def update(self, now, wanted):
        self._collect(now)       # a finished open is taken over (or thrown away) either way
        if not wanted:
            self.close()
            return None
        if self.analyzer is None and not self.opening and (
                self.last_try is None or now - self.last_try >= self.retry_seconds):
            self._start_open()
        return self.analyzer

    def _start_open(self):
        """Run one open on its own thread; `_collect` picks the result up later."""
        self.opening = True
        self.abandoned = False
        log.debug("audio input opening")
        threading.Thread(target=self._run_open, name="audio-open", daemon=True).start()

    def _run_open(self):
        try:
            analyzer, error = self.open_fn(self.cfg)
        except Exception as e:                       # an open_fn that raises must not kill the thread
            analyzer, error = None, e
        with self.lock:
            self.result = (analyzer, error)

    def _collect(self, now):
        """Take over the result of a finished open thread, if one has delivered."""
        with self.lock:
            result, self.result = self.result, None
        if result is None:
            return
        self.opening = False
        analyzer, error = result
        if self.abandoned:
            # the stream stopped being wanted while it was opening: never hand it out
            self.abandoned = False
            if analyzer is not None:
                stop_analyzer(analyzer, self.close_timeout)
                log.info("audio input closed")
            return
        if analyzer is not None:
            self.analyzer = analyzer
            self.last_try = None
            self.failed = False
            log.info("audio input opened")
            return
        self.last_try = now      # the retry cadence runs from the end of the attempt
        if not self.failed:
            self.failed = True
            log.error("audio input failed (%s). Retrying every %.0f s "
                      "(macOS may still be asking for microphone permission).", error, self.retry_seconds)
        else:
            log.debug("audio input still unavailable (%s)", error)

    def close(self):
        """Stop and drop the stream; the next `wanted` update opens a fresh one right away."""
        analyzer, self.analyzer = self.analyzer, None
        self.last_try = None
        self.failed = False
        if self.opening:
            self.abandoned = True
        if analyzer is not None:
            stop_analyzer(analyzer, self.close_timeout)
            log.info("audio input closed")


# ----------------------------------------------------------------------------
# System state: sleep/wake, display, power source
# ----------------------------------------------------------------------------
class WakeDetector:
    """Spots a return from system sleep by comparing the two clocks.

    While the Mac sleeps the wall clock keeps counting and the monotonic clock does not,
    so a loop iteration whose wall-clock delta runs `threshold` seconds ahead of its
    monotonic delta means the machine has just woken up. `check` reports that once, then
    starts measuring from the new pair, so it needs no timers and no sleeping to test.
    """

    def __init__(self, threshold=WAKE_JUMP_SECONDS):
        self.threshold = float(threshold)
        self.last_wall = None
        self.last_mono = None

    def check(self, wall_now, mono_now):
        last_wall, last_mono = self.last_wall, self.last_mono
        self.last_wall, self.last_mono = float(wall_now), float(mono_now)
        if last_wall is None:
            return False                      # the first call only takes the baseline
        return (wall_now - last_wall) - (mono_now - last_mono) > self.threshold


CF_ENCODING_UTF8 = 0x08000100
AC_POWER = "AC Power"        # IOPSGetProvidingPowerSourceType: else "Battery Power" / "UPS Power"
CORE_GRAPHICS = "/System/Library/Frameworks/CoreGraphics.framework/CoreGraphics"
IOKIT = "/System/Library/Frameworks/IOKit.framework/IOKit"
CORE_FOUNDATION = "/System/Library/Frameworks/CoreFoundation.framework/CoreFoundation"


class PowerState:
    """Reads whether the main display is asleep and whether the Mac runs on battery.

    Both come straight from the macOS C frameworks through ctypes, so no extra package
    is needed. Anything that goes wrong (a framework that will not load, an unexpected
    return value) falls back to "display awake, on AC power" - the combination that keeps
    the show running - and is logged once at DEBUG level.
    """

    def __init__(self, load=True):
        self.cg = self.iokit = self.cf = None
        self.failed = False
        if load:
            self._load()

    def _load(self):
        try:
            cg = ctypes.CDLL(CORE_GRAPHICS)
            iokit = ctypes.CDLL(IOKIT)
            cf = ctypes.CDLL(CORE_FOUNDATION)
            cg.CGMainDisplayID.restype = ctypes.c_uint32
            cg.CGDisplayIsAsleep.argtypes = [ctypes.c_uint32]
            cg.CGDisplayIsAsleep.restype = ctypes.c_int
            iokit.IOPSCopyPowerSourcesInfo.restype = ctypes.c_void_p
            iokit.IOPSGetProvidingPowerSourceType.argtypes = [ctypes.c_void_p]
            iokit.IOPSGetProvidingPowerSourceType.restype = ctypes.c_void_p
            cf.CFRelease.argtypes = [ctypes.c_void_p]
            cf.CFStringGetCString.argtypes = [ctypes.c_void_p, ctypes.c_char_p,
                                              ctypes.c_long, ctypes.c_uint32]
            cf.CFStringGetCString.restype = ctypes.c_ubyte
            self.cg, self.iokit, self.cf = cg, iokit, cf
        except Exception as e:
            self._fail(e)

    def display_asleep(self):
        if self.cg is None:
            return False
        try:
            return bool(self.cg.CGDisplayIsAsleep(self.cg.CGMainDisplayID()))
        except Exception as e:
            self._fail(e)
            return False

    def on_battery(self):
        if self.iokit is None:
            return False
        try:
            blob = self.iokit.IOPSCopyPowerSourcesInfo()
            if not blob:
                return False
            try:
                # a "Get" function: the string belongs to the blob and must not be released
                source = self._cfstring(self.iokit.IOPSGetProvidingPowerSourceType(blob))
            finally:
                self.cf.CFRelease(blob)
            return bool(source) and source != AC_POWER
        except Exception as e:
            self._fail(e)
            return False

    def _cfstring(self, ref):
        if not ref:
            return None
        buf = ctypes.create_string_buffer(64)
        if not self.cf.CFStringGetCString(ref, buf, len(buf), CF_ENCODING_UTF8):
            return None
        return buf.value.decode("utf-8", "replace")

    def _fail(self, error):
        """Give up for good: every later read takes the fallback without asking again."""
        self.cg = self.iokit = self.cf = None
        if not self.failed:
            self.failed = True
            log.debug("power state unavailable (%s); assuming the display is on and the "
                      "power adapter is connected", error)


def should_run(enabled, display_asleep, on_battery, cfg):
    """Whether the show should render right now.

    A show that is switched off never renders. A show that is on renders whenever the
    display is awake, and while the display is asleep only if the setting for the current
    power source allows it.
    """
    if not enabled:
        return False
    if not display_asleep:
        return True
    key = "show_when_display_off_on_battery" if on_battery else "show_when_display_off_on_ac"
    return bool(cfg[key])


# ----------------------------------------------------------------------------
# Background threads: device polling and the watchdog
# ----------------------------------------------------------------------------
class DevicePoller(threading.Thread):
    """Asks the system every `interval` seconds what the device and the power state look like.

    Every one of these questions goes into a macOS framework (CoreMIDI for the port list,
    CoreGraphics and IOKit for the display and the power source) and any of them can block
    for a long time while the USB bus re-enumerates. Asking them from the main loop means
    the whole show freezes whenever that happens, so they are asked here instead: the
    answers are stored in fields the main loop reads without ever waiting, and a call that
    blocks only stalls this thread. `last_update` says how fresh the answers are; the
    watchdog watches it.
    """

    def __init__(self, present_fn, display_fn, battery_fn, interval=DEVICE_CHECK_SECONDS):
        threading.Thread.__init__(self, name="device-poll", daemon=True)
        self.present_fn = present_fn
        self.display_fn = display_fn
        self.battery_fn = battery_fn
        self.interval = float(interval)
        self.lock = threading.Lock()
        self.stopped = threading.Event()
        self._present = False
        self._display_asleep = False
        self._on_battery = False
        self._last_update = time.monotonic()

    def poll_once(self):
        """One round of questions. Called by `run`, and once by the caller before starting."""
        present = self._read(self.present_fn, self._present)
        display_asleep = self._read(self.display_fn, self._display_asleep)
        on_battery = self._read(self.battery_fn, self._on_battery)
        with self.lock:
            self._present = bool(present)
            self._display_asleep = bool(display_asleep)
            self._on_battery = bool(on_battery)
            self._last_update = time.monotonic()

    def _read(self, fn, previous):
        """A question that raises keeps the previous answer; the show must not stop for it."""
        try:
            return fn()
        except Exception as e:
            log.debug("device poll failed (%s); keeping the last value", e)
            return previous

    def run(self):
        while not self.stopped.is_set():
            self.poll_once()
            self.stopped.wait(self.interval)

    def stop(self):
        self.stopped.set()

    @property
    def present(self):
        with self.lock:
            return self._present

    @property
    def display_asleep(self):
        with self.lock:
            return self._display_asleep

    @property
    def on_battery(self):
        with self.lock:
            return self._on_battery

    @property
    def last_update(self):
        with self.lock:
            return self._last_update


def stall_check(now, heartbeat, poll_update, loop_limit=WATCHDOG_SECONDS,
                poll_limit=POLL_STALL_SECONDS):
    """Why the show counts as stuck right now, or None while it is healthy.

    `heartbeat` is when the main loop last finished an iteration and `poll_update` when the
    device poller last finished a round, both on the monotonic clock. Either one falling too
    far behind `now` means a system call is not coming back, and the only cure is a restart.
    """
    behind = now - float(heartbeat)
    if behind > loop_limit:
        return "main loop stalled for %.0f s, exiting so launchd restarts the show" % behind
    behind = now - float(poll_update)
    if behind > poll_limit:
        return "device poll stalled for %.0f s, exiting so launchd restarts the show" % behind
    return None


def _exit_stalled():
    """Leave at once, without unwinding: whatever is stuck would block a clean shutdown too."""
    logging.shutdown()
    os._exit(EXIT_STALLED)


class Watchdog(threading.Thread):
    """Ends the process when the main loop or the device poller stops making progress.

    A frozen show cannot fix itself, but launchd's KeepAlive starts it again within seconds
    of it quitting, so quitting is the repair. Nothing is exited while the clocks stay fresh.
    """

    def __init__(self, heartbeat_fn, poll_update_fn, interval=WATCHDOG_CHECK_SECONDS,
                 loop_limit=WATCHDOG_SECONDS, poll_limit=POLL_STALL_SECONDS, on_stall=_exit_stalled):
        threading.Thread.__init__(self, name="watchdog", daemon=True)
        self.heartbeat_fn = heartbeat_fn
        self.poll_update_fn = poll_update_fn
        self.interval = float(interval)
        self.loop_limit = float(loop_limit)
        self.poll_limit = float(poll_limit)
        self.on_stall = on_stall
        self.stopped = threading.Event()

    def run(self):
        while not self.stopped.wait(self.interval):
            reason = stall_check(time.monotonic(), self.heartbeat_fn(), self.poll_update_fn(),
                                 self.loop_limit, self.poll_limit)
            if reason:
                log.error("%s", reason)
                self.on_stall()
                return

    def stop(self):
        self.stopped.set()


class Heartbeat:
    """The monotonic time of the last main-loop iteration, read by the watchdog thread.

    Storing one float needs no lock: in CPython the assignment and the read are each a
    single bytecode, so the watchdog always sees either the old value or the new one.
    """

    def __init__(self):
        self.value = time.monotonic()

    def beat(self):
        self.value = time.monotonic()


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
    ap.add_argument("--no-watchdog", action="store_true",
                    help="do not quit when the show stops making progress (for debugging; "
                         "normally a stalled show exits so launchd restarts it)")
    ap.add_argument("-v", "--verbose", action="store_true")
    args = ap.parse_args(argv)

    logging.basicConfig(level=logging.DEBUG if args.verbose else logging.INFO,
                        format="%(asctime)s %(levelname)s %(message)s", datefmt="%Y-%m-%d %H:%M:%S")

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

    # the microphone is opened only while the device is connected and the show is running
    audio = AudioController(cfg)
    power = PowerState()
    wake = WakeDetector(WAKE_JUMP_SECONDS)

    # the device and the power state are asked for on their own thread: those calls can block
    # for a long time when the USB bus re-enumerates, and the show must keep running meanwhile
    poller = DevicePoller(link.still_present, power.display_asleep, power.on_battery)
    poller.poll_once()       # one synchronous round, so the first iteration already knows
    poller.start()
    beat = Heartbeat()
    watchdog = None
    if not args.no_watchdog:
        watchdog = Watchdog(lambda: beat.value, lambda: poller.last_update)
        watchdog.start()

    frame = 1.0 / float(cfg["frame_rate"])
    last_check = 0.0
    last = time.monotonic()
    silent_since = None
    display_asleep = False
    on_battery = False
    suspended = False        # switched on, but not rendering because the display is asleep
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
            if wake.check(time.time(), now):
                # after a system sleep the audio stream is stale and the controller may have
                # been reset: drop the stream and set the device up again from scratch
                log.info("system woke up, reinitializing")
                audio.close()
                if link.connected():
                    show.on_connected()
                last = now
            if now - last_check >= DEVICE_CHECK_SECONDS:
                last_check = now
                # the poller's latest answers; never a fresh system call from this thread
                display_asleep = poller.display_asleep
                on_battery = poller.on_battery
                present = poller.present
                if link.connected():
                    if not present:
                        link.disconnect()
                elif not present:
                    log.debug("waiting for MIDI port '%s'", cfg["midi_port_name"])
                elif link.try_connect():
                    show.on_connected()
            running = should_run(show.enabled, display_asleep, on_battery, cfg)
            if not show.enabled:
                suspended = False            # switched off by hand: not a display suspension
            elif not running and not suspended:
                suspended = True
                if link.connected():
                    show.clear_output()      # the toggle LED keeps blinking: the show stays ON
                log.info("show suspended (display off, on %s)", "battery" if on_battery else "AC power")
            elif running and suspended:
                suspended = False
                log.info("show resumed")
            # nothing can use the microphone while the device is away or the show is not running
            wanted = link.connected() and running and not args.no_audio
            analyzer = audio.update(now, wanted)
            if analyzer is None:
                silent_since = None
            if args.verbose and now - last_status >= 5.0 and analyzer:
                last_status = now
                log.debug("state=%s fader=%.2f loud=%.2f rel=%.2f db=%.1f gate=%s levels=%s",
                          show.state, show.fader_scale, analyzer.get_loudness(),
                          analyzer.get_loudness_rel(), analyzer.get_loud_db(), analyzer.get_gate_status(),
                          " ".join("%.2f" % v for v in analyzer.get_levels()))
            levels = analyzer.get_levels() if analyzer else np.zeros(8)
            loudness = analyzer.get_loudness() if analyzer else 0.0
            loudness_rel = analyzer.get_loudness_rel() if analyzer else None
            if analyzer:
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
            if link.connected() and running:
                show.tick(now - last, levels, loudness, loudness_rel)
            last = now
            beat.beat()      # tells the watchdog this iteration finished
            time.sleep(max(0.0, frame - (time.monotonic() - now)))
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        # the shutdown below may take its time; it is not a stall
        if watchdog:
            watchdog.stop()
        poller.stop()
        if link.connected():
            with show.lock:
                show._clear_rings()
                show._clear_buttons()
                link.send_note(show.toggle_note, LED_OFF)
        audio.close()
        link.disconnect()
    return 0


if __name__ == "__main__":
    sys.exit(main())
