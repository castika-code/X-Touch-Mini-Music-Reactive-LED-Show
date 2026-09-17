#!/usr/bin/env python3
"""
X-Touch Mini / X-Touch One music-reactive LED show (MC mode).

Either controller may be connected, both, or neither; each hot-plugs independently
and both share one microphone, one ON/OFF state and one config file.

While the show is on, the 8 encoder LED rings of the Behringer X-Touch Mini display
an 8-band audio spectrum of whatever a microphone hears (the built-in mic picking up
the speakers, or any other input), and the 16 button LEDs show the loudness as two
bars filling left to right (top row = absolute loudness, bottom row = loudness
relative to the recent minimum/maximum). One Layer button (A or B) switches the show
on and off; its LED is dark while the show is off and blinks while it runs. The fader
scales bar height (sensitivity).

The X-Touch One shows a BPM peak indicator (lights briefly whenever overall loudness
crosses a fixed threshold) and three button-LED rows that each fill left to right with
a high/mid/low frequency band (F1 line, Marker line, Rewind line), plus a fifth bar that
fills the Bank/Channel/nav-cluster buttons bottom to top with overall relative loudness,
an encoder ring showing absolute loudness, the device's own level meter also driven by
overall relative loudness, and a 12-character display that scrolls a configurable
message. A configurable button (Scrub by default) switches the show on and off, blinking
in software while it runs. Toggling the show on either controller switches both.

An optional noise gate (off by default) keeps plain room noise from moving the LEDs.
Every other knob and button keeps its normal function; the show ignores it.

While the display is asleep the show keeps running on the power adapter and stops on
battery (both configurable), and it re-initializes itself after the Mac wakes from sleep.

For DAW users the program offers each connected controller a virtual MIDI device
("X-TOUCH MINI SHOW" / "X-TOUCH ONE SHOW") that is selected in the DAW instead of the
controller: traffic is passed both ways, the show takes the LEDs over while it runs,
and when it stops the LEDs go back to exactly what the DAW last set.

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
IDLE_LOOP_SECONDS = 2.0      # main-loop pause between iterations while the show is switched off
AUDIO_CLOSE_TIMEOUT = 3.0    # how long closing the audio stream may take before it is abandoned
WATCHDOG_SECONDS = 15.0      # no main-loop iteration for this long = the loop is stuck
WATCHDOG_CHECK_SECONDS = 5.0 # how often the watchdog compares the clocks
POLL_STALL_SECONDS = 30.0    # no finished device poll for this long = the poller is stuck
EXIT_STALLED = 3             # exit code the watchdog uses; launchd KeepAlive restarts the show

# ----------------------------------------------------------------------------
# X-Touch One protocol constants (MC mode, verified on hardware 2026-09-16)
# ----------------------------------------------------------------------------
# All 33 host-controllable LEDs: name -> note number. Master is not host-controllable and
# is never touched.
ONE_LED_NOTES = {
    "BPM": 114,
    "Channel Record": 0, "Channel Solo": 8, "Channel Mute": 16, "Channel Select": 24,
    "Bank Left": 46, "Bank Right": 47,
    "Channel Left": 104, "Channel Right": 105,
    "F1": 74, "F2": 75, "F3": 76, "F4": 77, "F5": 78, "F6": 79,
    "Marker": 84, "Nudge": 85, "Cycle": 86, "Drop": 87, "Replace": 88, "Click": 89, "Solo": 90,
    "Rewind": 91, "Forward": 92, "Stop": 93, "Play": 94, "Record": 95,
    "Up": 96, "Down": 97, "Left": 98, "Right": 99, "Zoom": 100, "Scrub": 101,
}
# Three frequency-band rows (F1 line = high band, Marker line = mid band, Rewind line =
# low band), each filling left to right; whichever row holds the configured toggle button
# has that name removed from its fill sequence.
ONE_F1_LINE_NAMES = ["F1", "F2", "F3", "F4", "F5", "F6"]
# F1-F6 respond at different notes depending on which MC personality (Standard vs
# Logic) the device's own on-device setting currently selects -- switchable by the
# user at any time, with no way found tonight to query or force it via MIDI. Sending
# a Note On to whichever set doesn't apply is harmless (confirmed live, repeatedly),
# so both sets are always sent together instead of picking one.
ONE_F1_LINE_NOTES_STANDARD = [54, 55, 56, 57, 58, 59]
ONE_F1_LINE_NOTES_LOGIC = [74, 75, 76, 77, 78, 79]
ONE_MARKER_LINE_NAMES = ["Marker", "Nudge", "Cycle", "Drop", "Replace", "Click", "Solo"]
ONE_REWIND_LINE_NAMES = ["Rewind", "Forward", "Stop", "Play", "Record"]
# A fourth flat row, one LED per step like the rows above, but driven directly by overall
# relative loudness instead of a frequency band. Fills in physical left-to-right order
# (Mute, then Solo, then Record) as loudness rises. Channel Select sits immediately to
# their left on the device but is not part of this row: it is a separate, permanently-on
# prerequisite switched on once per connect by on_connected(), never touched per-frame.
ONE_CHANNEL_STRIP_LINE_NAMES = ["Channel Mute", "Channel Solo", "Channel Record"]
# A fifth relative-level bar: the Bank/Channel/nav-cluster buttons sit in one vertical
# column on the device, so they are grouped into 5 tiers (bottom to top) and lit like a
# bar graph, one tier per group, instead of one LED per step like the rows above.
ONE_NAV_TIERS = [
    ("Down",),
    ("Left", "Zoom", "Right"),
    ("Up",),
    ("Channel Left", "Channel Right"),
    ("Bank Left", "Bank Right"),
]
# No LEDs are left over: BPM, the four button rows, the nav-cluster tiers and Channel
# Select (armed once per connect, see OneRenderer.on_connected, and never cleared by the
# show) account for all 33. Kept as an empty list, rather than removed, so _clear_rows's
# loop over it needs no special-casing.
ONE_UNUSED_NAMES = []
RING_CC_ONE = RING_CC_BASE          # CC 48: the One's single V-Pot ring (Fan mode, same scheme as the Mini)
DISPLAY_CC_BASE = 64                # CC 64..75: the 12-character display, one CC per position
DISPLAY_CC_TOP = 75
ONE_BLINK_PERIOD_S = 0.5            # software toggle-LED blink half-period (on 0.5s, off 0.5s)
ONE_PEAK_THRESHOLD = 0.9            # relative loudness above this = a peak
ONE_PEAK_HOLD_S = 0.25              # minimum time BPM stays lit once a peak is seen
# The One's real level meter (separate from the encoder ring) responds to Channel Pressure,
# but only once Channel Select (note 24) has been turned on -- confirmed by direct A/B
# testing, identical sweeps sent before/after got no response/an immediate response. The
# upper nibble of the value is a channel-strip index; this device has only one channel, so
# it always stays 0.
ONE_METER_STATUS = 0xD0             # Channel Pressure status nibble
ONE_METER_MAX = 15                  # meter level range: 0 = off, 15 = full/CLIP
# Note 114 (BPM) ignores velocity-0 and real Note Off -- confirmed live, nothing clears it
# short of a power cycle. Note 113 has no LED of its own but is the only way to turn 114
# off; the two act as a mutually exclusive pair (almost certainly the Mackie Control
# SMPTE/Beats display-mode toggle).
ONE_BPM_OFF_NOTE = 113
# note numbers that count as a press of a given LED name; equal to the LED note except
# for these three, where the device sends a different note on press (see README/spec)
ONE_PRESS_OVERRIDES = {
    ONE_LED_NOTES["BPM"]: (53,),
    ONE_LED_NOTES["Channel Left"]: (48, 31),    # Master mode on / off; both are accepted
    ONE_LED_NOTES["Channel Right"]: (49, 24),
}

DEFAULT_MINI = {
    "enabled": True,
    "midi_port_name": "X-TOUCH MINI",
    "toggle_button": "A",
    "buttons_enabled": True,
    "daw_proxy": True,                         # offer a virtual MIDI device for a DAW to use
    "daw_proxy_name": "X-TOUCH MINI SHOW",     # the name that device has in the DAW
}

DEFAULT_ONE = {
    "enabled": False,
    "midi_port_name": "X-Touch One",
    "toggle_button": "Scrub",
    "daw_proxy": True,
    "daw_proxy_name": "X-TOUCH ONE SHOW",
    "display_text": "LED ON",
    "display_scroll": True,
    "display_scroll_step_s": 0.3,
}

# Legacy flat top-level keys from the single-device config format. load_config() always
# migrates these into the 'mini' section and mirrors them back onto the top level, so
# code written against the old flat keys (this module's own MiniRenderer included) keeps
# working whether config.json uses the old format or the new 'mini'/'one' sections.
LEGACY_MINI_KEYS = ("midi_port_name", "toggle_button", "buttons_enabled", "daw_proxy", "daw_proxy_name")

DEFAULT_CONFIG = {
    "midi_port_name": DEFAULT_MINI["midi_port_name"],
    "toggle_button": DEFAULT_MINI["toggle_button"],
    "buttons_enabled": DEFAULT_MINI["buttons_enabled"],
    "daw_proxy": DEFAULT_MINI["daw_proxy"],
    "daw_proxy_name": DEFAULT_MINI["daw_proxy_name"],
    # shared settings: audio input/analysis, timing, power behaviour
    "audio_input_device": "default",
    "frame_rate": 30,
    "decay_per_frame": 1,
    "show_enabled_at_start": True,
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
    "noise_gate_margin_db": 4.0,
    # new-format per-device sections
    "mini": dict(DEFAULT_MINI),
    "one": dict(DEFAULT_ONE),
}

NOISE_CALIBRATION_SECONDS = 3.0   # --calibrate: how long the room noise is measured
NOISE_PERCENTILE = 75             # percentile of the measured blocks; ignores clicks and coughs
DIGITAL_SILENCE_DB = -100.0       # below this the input is not quiet, it is dead (muted or denied)


def _default_config():
    """A fresh copy of DEFAULT_CONFIG, including its nested/list values."""
    cfg = dict(DEFAULT_CONFIG)
    cfg["mini"] = dict(DEFAULT_CONFIG["mini"])
    cfg["one"] = dict(DEFAULT_CONFIG["one"])
    cfg["band_centers_hz"] = list(DEFAULT_CONFIG["band_centers_hz"])
    cfg["band_gains"] = list(DEFAULT_CONFIG["band_gains"])
    return cfg


def _note_to_name(note):
    for name, n in ONE_LED_NOTES.items():
        if n == note:
            return name
    return None


def _resolve_one_led_note(value):
    """(name, note) for an X-Touch One LED spec: a name (case-insensitive) or a literal
    note number 0-127, as either a string or a number. `name` is the canonical LED name
    when `value` matched one, `note` is the MIDI note either way. (None, None) when
    `value` matches nothing at all.
    """
    if isinstance(value, str):
        s = value.strip()
        for name, note in ONE_LED_NOTES.items():
            if name.lower() == s.lower():
                return name, note
        if s.lstrip("-").isdigit():
            note = int(s)
            if 0 <= note <= 127:
                return _note_to_name(note), note
    elif isinstance(value, (int, float)) and not isinstance(value, bool):
        note = int(value)
        if 0 <= note <= 127:
            return _note_to_name(note), note
    return None, None


def _one_press_notes(led_note):
    """Note number(s) the X-Touch One sends when the button with this LED note is pressed."""
    return ONE_PRESS_OVERRIDES.get(led_note, (led_note,))


def _one_char_code(ch):
    """The X-Touch One display's character code (CC value) for one character.

    ASCII 0x40-0x5F (the 7-segment-rendered letters and a few symbols) -> code = ascii - 0x40.
    ASCII 0x20-0x3F (space, digits, punctuation) -> code = ascii. Anything else is blank.
    """
    o = ord(ch)
    if 0x40 <= o <= 0x5F:
        return o - 0x40
    if 0x20 <= o <= 0x3F:
        return o
    return 0x20


def _apply_user_config(cfg, user):
    top_level = set(cfg)
    unknown = set(user) - top_level
    if unknown:
        log.warning("config: unknown keys ignored: %s", ", ".join(sorted(unknown)))
    shared_keys = top_level - {"mini", "one"} - set(LEGACY_MINI_KEYS)
    cfg.update({k: v for k, v in user.items() if k in shared_keys})
    legacy = {k: user[k] for k in LEGACY_MINI_KEYS if k in user}
    if legacy:
        cfg["mini"].update(legacy)
        log.info("config: migrating old-format key(s) into the 'mini' section: %s",
                 ", ".join(sorted(legacy)))
    for section in ("mini", "one"):
        given = user.get(section)
        if isinstance(given, dict):
            unknown_section = set(given) - set(cfg[section])
            if unknown_section:
                log.warning("config: unknown keys in '%s' ignored: %s",
                           section, ", ".join(sorted(unknown_section)))
            cfg[section].update({k: v for k, v in given.items() if k in cfg[section]})


def _finalize_config(cfg):
    """Validate, and mirror the 'mini' section back onto the legacy flat top-level keys."""
    for k in LEGACY_MINI_KEYS:
        cfg[k] = cfg["mini"][k]
    if cfg["toggle_button"] not in LAYER_NOTES:
        raise ValueError("toggle_button must be 'A' or 'B'")
    if len(cfg["band_centers_hz"]) != 8 or len(cfg["band_gains"]) != 8:
        raise ValueError("band_centers_hz and band_gains must have 8 entries")
    if cfg["daw_proxy"] and not str(cfg["daw_proxy_name"] or "").strip():
        raise ValueError("daw_proxy_name must be the name of the virtual MIDI device, "
                         "for example 'X-TOUCH MINI SHOW'")
    gate = cfg["noise_gate_db"]
    if gate is not None and (isinstance(gate, bool) or not isinstance(gate, (int, float))):
        raise ValueError("noise_gate_db must be null (no noise gate) or a number in dB, "
                         "for example -45.0; got %r" % (gate,))
    if cfg["one"]["daw_proxy"] and not str(cfg["one"]["daw_proxy_name"] or "").strip():
        raise ValueError("one.daw_proxy_name must be the name of the virtual MIDI device, "
                         "for example 'X-TOUCH ONE SHOW'")
    raw_toggle = cfg["one"].get("toggle_button", "Scrub")
    name, note = _resolve_one_led_note(raw_toggle)
    if note is None:
        log.warning("config: one.toggle_button %r is not valid; using 'Scrub'", raw_toggle)
        name = "Scrub"
    cfg["one"]["toggle_button"] = name if name is not None else note
    cfg["one"]["display_text"] = str(cfg["one"].get("display_text") or "LED ON").upper()[:12]
    cfg["one"]["display_scroll"] = bool(cfg["one"].get("display_scroll", True))
    try:
        step = float(cfg["one"].get("display_scroll_step_s") or 0.3)
    except (TypeError, ValueError):
        step = 0.3
    cfg["one"]["display_scroll_step_s"] = step if step > 0 else 0.3


def load_config(path):
    cfg = _default_config()
    if path and os.path.exists(path):
        with open(path, encoding="utf-8") as f:
            user = json.load(f)
        _apply_user_config(cfg, user)
    elif path:
        log.warning("config file not found, using defaults: %s", path)
    _finalize_config(cfg)
    return cfg


# ----------------------------------------------------------------------------
# Show logic (no I/O; fully testable)
# ----------------------------------------------------------------------------
class ShowState:
    """The shared ON/OFF flag, read and flipped by one or more device renderers.

    Two renderers can be given the same ShowState instance so that toggling the show on
    either connected controller is reflected by both on their next frame: `enabled` reads
    and writes go through one lock, and `toggle()` flips the flag atomically so that two
    simultaneous toggles (one per device) cannot race each other into a lost flip.

    Renderers sharing the flag also register themselves here (see `register()`), because a
    renderer whose `tick()` returns early on a shared OFF flag would otherwise leave its
    hardware frozen at whatever it last drew: switching the show off on one controller now
    clears every other registered one straight away.
    """

    def __init__(self, enabled):
        self._enabled = bool(enabled)
        self._renderers = []
        self.lock = threading.Lock()
        # toggles arrive on the MIDI callback thread; this lets the main loop idle for
        # seconds while the show is off and still start rendering the instant it goes on
        self.wake_event = threading.Event()

    def register(self, renderer):
        """Remember a renderer so a switch-off on another device can clear it as well."""
        if renderer not in self._renderers:
            self._renderers.append(renderer)

    @property
    def enabled(self):
        with self.lock:
            return self._enabled

    @enabled.setter
    def enabled(self, value):
        with self.lock:
            self._enabled = bool(value)

    def toggle(self, caller=None):
        """Flip the flag and, when it went off, clear every registered renderer but `caller`.

        `caller` (the renderer whose button was pressed) is skipped because it clears itself
        inside its own `_toggle()`. The lock is deliberately released before calling into any
        other renderer: each renderer's `_toggle()` holds its own lock across the call to this
        method, so reaching for a second renderer's lock while still holding this one would
        invert the lock order between two device threads and could deadlock.
        """
        with self.lock:
            self._enabled = not self._enabled
            new_enabled = self._enabled
            others = [r for r in self._renderers if r is not caller] if not new_enabled else []
        self.wake_event.set()
        for r in others:
            r.full_clear()
        return new_enabled


class MiniRenderer:
    """Renders the show on the Behringer X-Touch Mini. State machine: OFF / ON, sending
    MIDI through callbacks. Kept as a plain device-specific renderer so it can run alone
    (its own private ShowState) or share one with an X-Touch One via the `state` param."""

    def __init__(self, cfg, send_cc, send_note, state=None):
        self.cfg = cfg
        self.send_cc = send_cc
        self.send_note = send_note
        self.toggle_note = LAYER_NOTES[cfg["toggle_button"]]
        self.gains = list(cfg["band_gains"])
        self.decay = int(cfg["decay_per_frame"])
        self._state = state if state is not None else ShowState(bool(cfg["show_enabled_at_start"]))
        self._state.register(self)   # so a switch-off on another controller clears this one too
        self.buttons_enabled = bool(cfg["buttons_enabled"])
        self.fader_scale = 1.0
        self.current = [0] * 8
        self.last_sent = [-1] * 8
        self.bar_top = 0             # top-row absolute loudness bar, 0..8 buttons lit
        self.bar_bottom = 0          # bottom-row relative loudness bar, 0..8 buttons lit
        self.last_button = [-1] * 16 # last velocity sent per BUTTON_NOTES entry
        self.last_led = None         # last toggle-LED velocity sent; avoids redundant notes
        self.lock = threading.Lock()

    @property
    def enabled(self):
        return self._state.enabled

    @enabled.setter
    def enabled(self, value):
        self._state.enabled = value

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
            log.info("[mini] device ready | state=%s | toggle=Layer %s (note %d)",
                     self.state, self.cfg["toggle_button"], self.toggle_note)

    def clear_output(self, suspending=False):
        """Take the rings and the button LEDs out once without changing the ON/OFF state.

        Used while the show is suspended (the display is asleep): the toggle LED is left
        alone regardless of `suspending` (accepted only so the call site can be shared with
        OneRenderer) since the Mini's hardware keeps blinking it on its own; the next `tick`
        renders from scratch.
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
            new_enabled = self._state.toggle(caller=self)
            if not new_enabled:
                self._clear_rings()
                self._clear_buttons()
            self._set_toggle_led()
            log.info("[mini] show %s (Layer %s)", "ON" if new_enabled else "OFF", self.cfg["toggle_button"])

    # -- periodic update (called from main loop) ---------------------------
    def tick(self, dt, levels, loudness=0.0, loudness_rel=None,
             band_rel_low=None, band_rel_mid=None, band_rel_high=None):
        # band_rel_low/mid/high: the X-Touch One's per-band auto-ranging rows have no
        # equivalent on the Mini; accepted and ignored so the main loop's polymorphic
        # tick(...) call can pass the same arguments to every device uniformly.
        with self.lock:
            # a toggle on the other controller only flips the shared flag, so the LED is
            # brought in line here every frame (deduped: MIDI goes out only on a change)
            self._set_toggle_led()
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

    def full_clear(self):
        """Clear the rings and buttons and force the toggle LED off. Used only at shutdown;
        `clear_output()` leaves the toggle LED alone so it keeps showing the show is ON."""
        with self.lock:
            self._clear_rings()
            self._clear_buttons()
            self.send_note(self.toggle_note, LED_OFF)
            self.last_led = LED_OFF


Show = MiniRenderer   # backward-compatible alias: identical behavior, old name


# ----------------------------------------------------------------------------
# X-Touch One renderer (no I/O; fully testable)
# ----------------------------------------------------------------------------
class OneRenderer:
    """Renders the show on the Behringer X-Touch One: BPM (note 114) as a peak indicator
    (lights briefly, with a short hold, whenever loudness normalised against its own recent
    min/max range -- the same auto-ranging idea the band rows below use -- crosses a fixed
    threshold), three frequency-band button-LED rows that each fill left to right with
    the same one-step-per-frame decay algorithm MiniRenderer's bars use (F1 line = high
    band, Marker line = mid band, Rewind line = low band). Each row is driven directly by
    the SpectrumAnalyzer's own auto-ranging value for that band group: the loudest
    gain-adjusted sub-band in the group, normalised against its own recent min/max range
    (the same rolling-envelope idea the Mini's relative-loudness bar uses, applied per
    band group instead of to overall loudness), so a row fills to near-full at the loudest
    recent moment in that frequency range regardless of the track's overall volume -- a
    fixed sensitivity multiplier could never suit both quiet and loud passages when a row
    only has 5-7 LEDs. A fourth row (Channel Mute, Channel Solo, Channel Record, in that
    physical left-to-right order) fills the same way, one LED per step, but is driven
    directly by overall relative loudness instead of a frequency band. A fifth
    relative-level bar reuses the Bank/Channel/nav-cluster buttons, which sit in one
    vertical column on the device: grouped into 5 tiers (see ONE_NAV_TIERS) and filled
    from the bottom tier upward as overall relative loudness rises, one tier per step
    instead of one LED per step. There is also one encoder ring (absolute loudness,
    sensitivity fixed at 1.0: the One has no fader to scale it), the real hardware level
    meter (driven by overall relative loudness via Channel Pressure, separately from the
    ring), a 12-character scrolling display, and a software-blinked toggle LED (the
    device's blink velocity is unverified).

    Pass the same ShowState instance a MiniRenderer uses (via `state`) to have both
    controllers reflect one shared ON/OFF flag; standalone use creates a private one.
    """

    def __init__(self, cfg, one_cfg, send_cc, send_note, send_raw, state=None):
        self.cfg = cfg
        self.one_cfg = one_cfg
        self.send_cc = send_cc
        self.send_note = send_note
        self.send_raw = send_raw     # 2-byte messages (Channel Pressure, the level meter) don't fit send_cc/send_note
        self.decay = int(cfg["decay_per_frame"])
        self._state = state if state is not None else ShowState(bool(cfg["show_enabled_at_start"]))
        self._state.register(self)   # so a switch-off on another controller clears this one too

        name, note = _resolve_one_led_note(one_cfg.get("toggle_button", "Scrub"))
        if note is None:
            name, note = "Scrub", ONE_LED_NOTES["Scrub"]
        self.toggle_name = name                          # None for a bare, unnamed note number
        self.toggle_note = note
        self.toggle_label = name if name is not None else ("note %d" % note)
        self.press_notes = _one_press_notes(note)

        self.f1_line_names = [n for n in ONE_F1_LINE_NAMES if n != self.toggle_name]
        self.marker_line_names = [n for n in ONE_MARKER_LINE_NAMES if n != self.toggle_name]
        self.rewind_line_names = [n for n in ONE_REWIND_LINE_NAMES if n != self.toggle_name]
        self.channel_strip_line_names = [n for n in ONE_CHANNEL_STRIP_LINE_NAMES if n != self.toggle_name]
        # one (standard_note, logic_note) pair per surviving F1-row position: both are
        # always sent, since the active MC personality can't be queried (see the
        # ONE_F1_LINE_NOTES_* constants)
        self.f1_line_notes = [(std, logic) for name, std, logic in
                              zip(ONE_F1_LINE_NAMES, ONE_F1_LINE_NOTES_STANDARD, ONE_F1_LINE_NOTES_LOGIC)
                              if name != self.toggle_name]
        self.marker_line_notes = [ONE_LED_NOTES[n] for n in self.marker_line_names]
        self.rewind_line_notes = [ONE_LED_NOTES[n] for n in self.rewind_line_names]
        self.channel_strip_line_notes = [ONE_LED_NOTES[n] for n in self.channel_strip_line_names]
        # 5 tiers, bottom to top; the toggle button's name (if any) is dropped from
        # whichever tier holds it, same as the three rows above
        self.nav_tiers = [[ONE_LED_NOTES[n] for n in tier if n != self.toggle_name]
                          for tier in ONE_NAV_TIERS]
        self.unused_notes = [ONE_LED_NOTES[n] for n in ONE_UNUSED_NAMES if n != self.toggle_name]

        self.display_text = str(one_cfg.get("display_text") or "LED ON").upper()[:12]
        self.display_scroll = bool(one_cfg.get("display_scroll", True))
        try:
            step = float(one_cfg.get("display_scroll_step_s") or 0.3)
        except (TypeError, ValueError):
            step = 0.3
        self.scroll_step_s = step if step > 0 else 0.3

        self.f1_line = 0
        self.marker_line = 0
        self.rewind_line = 0
        self.channel_strip_line = 0
        self.nav_bar = 0
        self.peak_hold_remaining = 0.0
        self.peak_on = False
        self.ring_current = 0
        self.last_ring = None
        self.last_button = {}        # note -> last velocity sent
        self.last_display = {}       # CC -> last character code sent
        self.last_toggle_led = None
        self.last_bpm_on = None      # BPM's own on/off dedup; never goes through last_button
        self.last_meter_level = None # the meter's own dedup; not a note, so not in last_button
        self.blink_on = False
        self.blink_accum = 0.0       # seconds accumulated toward the next blink flip
        self.scroll_offset = 0
        self.scroll_accum = 0.0      # seconds accumulated toward the next scroll step
        self.lock = threading.Lock()

    @property
    def enabled(self):
        return self._state.enabled

    @enabled.setter
    def enabled(self, value):
        self._state.enabled = value

    @property
    def state(self):
        return "ON" if self.enabled else "OFF"

    # -- device (re)connect -------------------------------------------------
    def on_connected(self):
        with self.lock:
            self.last_ring = None
            self.last_button = {}
            self.last_display = {}
            self.last_toggle_led = None
            self.last_bpm_on = None
            self.last_meter_level = None
            self.blink_on = False
            self.blink_accum = 0.0
            self.scroll_offset = 0
            self.scroll_accum = 0.0
            self._clear_all()
            # the real level meter stays dead until Channel Select has been turned on once
            # (confirmed live: identical Channel Pressure sweeps got no response before this
            # and an immediate response after); sent here, alongside the other one-time setup,
            # so every reconnect re-arms it
            self.send_note(ONE_LED_NOTES["Channel Select"], LED_ON)
            log.info("[one] device ready | state=%s | toggle=%s (note %d)",
                     self.state, self.toggle_label, self.toggle_note)

    def clear_output(self, suspending=False):
        """Take the bars, the ring and the display out once without changing the ON/OFF
        state; used while the show is suspended (the display is asleep) and once when the
        show switches fully off (see full_clear()). `suspending=True` is for the display-off
        suspension case only: the show is still switched ON, so the toggle LED is left
        solidly lit (velocity 127) instead of going dark, and the software blink is stopped
        (reset to a fresh state) so it restarts cleanly once the show resumes and `tick`
        runs again. `suspending=False` (the default, used at shutdown) instead forces the
        toggle LED fully off, matching a genuine OFF. The next `tick` (or reconnect) renders
        the bars/ring/display from scratch either way."""
        with self.lock:
            self._clear_rows()
            self._clear_ring()
            self._clear_display()
            self._clear_meter()
            self.blink_on = False
            self.blink_accum = 0.0
            self._send_toggle_led(LED_ON if suspending else LED_OFF)

    # -- input events (called from MIDI thread) ------------------------------
    def on_midi(self, msg):
        """Only the toggle button belongs to the show; everything else (including the
        jog wheel's CC 60) is ignored."""
        if len(msg) < 3:
            return
        status, d1, d2 = msg[0], msg[1], msg[2]
        kind, ch = status & 0xF0, status & 0x0F
        if kind == 0x90 and ch == MIDI_CH and d2 > 0 and d1 in self.press_notes:
            self._toggle()

    def _toggle(self):
        with self.lock:
            new_enabled = self._state.toggle(caller=self)
            if not new_enabled:
                self._clear_all()
            log.info("[one] show %s (%s)", "ON" if new_enabled else "OFF", self.toggle_label)

    # -- periodic update (called from main loop) -----------------------------
    def tick(self, dt, levels, loudness=0.0, loudness_rel=None,
             band_rel_low=None, band_rel_mid=None, band_rel_high=None):
        # `levels` is kept in the signature for interface parity with MiniRenderer.tick
        # (the main loop calls every device's tick(...) polymorphically with the same
        # arguments); the rows below are driven entirely by the analyzer's own
        # band_rel_low/mid/high values instead.
        with self.lock:
            if not self.enabled:
                return
            rel = 0.0 if loudness_rel is None else loudness_rel
            self._render_rows(0.0 if band_rel_low is None else band_rel_low,
                              0.0 if band_rel_mid is None else band_rel_mid,
                              0.0 if band_rel_high is None else band_rel_high)
            self._render_peak(dt, rel)
            self._render_channel_strip(rel)
            self._render_nav_bar(rel)
            self._render_ring(loudness)
            self._render_meter(rel)
            self._render_display(dt)
            self._render_blink(dt)

    def _render_rows(self, band_rel_low, band_rel_mid, band_rel_high):
        """Three frequency-band rows, each filling left to right with the same
        one-step-per-frame decay algorithm as the old loudness bars, sized to the row.
        Each of the three inputs is already the SpectrumAnalyzer's own auto-ranging value
        for that band group -- the loudest gain-adjusted sub-band in the group, normalised
        against its own recent min/max range -- so it is used here as-is, with no further
        scaling."""
        self.f1_line = self._step_bar(self.f1_line, band_rel_high, len(self.f1_line_notes))
        self.marker_line = self._step_bar(self.marker_line, band_rel_mid, len(self.marker_line_notes))
        self.rewind_line = self._step_bar(self.rewind_line, band_rel_low, len(self.rewind_line_notes))
        for i, (std_note, logic_note) in enumerate(self.f1_line_notes):
            on = LED_ON if i < self.f1_line else LED_OFF
            self._send_button(std_note, on)
            self._send_button(logic_note, on)
        for i, note in enumerate(self.marker_line_notes):
            self._send_button(note, LED_ON if i < self.marker_line else LED_OFF)
        for i, note in enumerate(self.rewind_line_notes):
            self._send_button(note, LED_ON if i < self.rewind_line else LED_OFF)

    def _render_channel_strip(self, loudness_rel):
        """A fourth flat row, one LED per step like the three band rows above, but driven
        directly by overall relative loudness: fills Mute, then Solo, then Record as
        loudness rises."""
        self.channel_strip_line = self._step_bar(self.channel_strip_line, loudness_rel,
                                                  len(self.channel_strip_line_notes))
        for i, note in enumerate(self.channel_strip_line_notes):
            self._send_button(note, LED_ON if i < self.channel_strip_line else LED_OFF)

    def _render_nav_bar(self, loudness_rel):
        """Fifth relative-level bar: the same one-step-per-frame decay as the rows above,
        but sized to the 5 nav-cluster tiers (ONE_NAV_TIERS) instead of to individual LEDs
        -- every button in a lit tier goes on together, every button in an unlit tier goes
        off together."""
        self.nav_bar = self._step_bar(self.nav_bar, loudness_rel, len(self.nav_tiers))
        for i, notes in enumerate(self.nav_tiers):
            for note in notes:
                self._send_button(note, LED_ON if i < self.nav_bar else LED_OFF)

    def _render_peak(self, dt, loudness_rel):
        """BPM lights as a peak indicator: on immediately at/above the threshold, held on
        for at least ONE_PEAK_HOLD_S afterward so short peaks stay visible."""
        if loudness_rel >= ONE_PEAK_THRESHOLD:
            self.peak_hold_remaining = ONE_PEAK_HOLD_S
            self.peak_on = True
        elif self.peak_hold_remaining > 0:
            self.peak_hold_remaining = max(0.0, self.peak_hold_remaining - dt)
            self.peak_on = self.peak_hold_remaining > 0
        else:
            self.peak_on = False
        if self.toggle_name != "BPM":    # BPM is the toggle LED itself; _send_toggle_led owns it
            self._set_bpm(self.peak_on)

    def _step_bar(self, bar, level, size):
        """Next row length in LEDs: rises at once, falls at most decay_per_frame per frame."""
        level = min(1.0, max(0.0, float(level)))
        target = int(round(level * size))
        return max(target, bar - self.decay) if target < bar else target

    def _render_ring(self, loudness):
        level = min(1.0, max(0.0, float(loudness)))
        target = int(round(level * RING_MAX))
        if target < self.ring_current:
            self.ring_current = max(target, self.ring_current - self.decay)
        else:
            self.ring_current = target
        self._send_ring(RING_FAN + self.ring_current)

    def _render_meter(self, loudness_rel):
        """The real level meter, via Channel Pressure -- separate from the encoder ring
        and from every note-based LED above. Scaled straight from relative loudness with
        no decay of its own: the hardware meter has its own release behavior."""
        level = min(ONE_METER_MAX, max(0, int(round(min(1.0, max(0.0, float(loudness_rel))) * ONE_METER_MAX))))
        self._send_meter(level)

    def _render_display(self, dt):
        text = self.display_text
        length = len(text)
        max_offset = max(0, 12 - length) if length else 0
        if self.display_scroll and max_offset > 0:
            self.scroll_accum += dt
            if self.scroll_accum >= self.scroll_step_s:
                steps = int(self.scroll_accum // self.scroll_step_s)
                self.scroll_accum -= steps * self.scroll_step_s
                self.scroll_offset = (self.scroll_offset + steps) % (max_offset + 1)
        else:
            self.scroll_offset = 0
        self._draw_display(text, self.scroll_offset)

    def _draw_display(self, text, offset):
        length = len(text)
        for position in range(1, 13):
            idx = position - 1 - offset
            ch = text[idx] if 0 <= idx < length else " "
            self._send_display(position, _one_char_code(ch))

    def _render_blink(self, dt):
        self.blink_accum += dt
        if self.blink_accum >= ONE_BLINK_PERIOD_S:
            steps = int(self.blink_accum // ONE_BLINK_PERIOD_S)
            self.blink_accum -= steps * ONE_BLINK_PERIOD_S
            if steps % 2 == 1:
                self.blink_on = not self.blink_on
        self._send_toggle_led(LED_ON if self.blink_on else LED_OFF)

    # -- low-level send helpers (skip a message whose LED state did not change) --------
    def _send_button(self, note, velocity):
        if self.last_button.get(note) != velocity:
            self.send_note(note, velocity)
            self.last_button[note] = velocity

    def _send_ring(self, value):
        if value != self.last_ring:
            self.send_cc(RING_CC_ONE, value)
            self.last_ring = value

    def _send_meter(self, level):
        """Channel Pressure: a 2-byte message, unlike every other output here, so it
        cannot go through send_cc/send_note and gets its own dedicated send call."""
        if level != self.last_meter_level:
            self.send_raw([ONE_METER_STATUS | MIDI_CH, level])
            self.last_meter_level = level

    def _send_display(self, position, code):
        cc = DISPLAY_CC_TOP - (position - 1)
        if self.last_display.get(cc) != code:
            self.send_cc(cc, code)
            self.last_display[cc] = code

    def _send_toggle_led(self, velocity):
        if velocity != self.last_toggle_led:
            self.send_note(self.toggle_note, velocity)
            self.last_toggle_led = velocity

    def _set_bpm(self, on):
        """BPM (note 114) is not a normal LED: velocity 0 / Note Off never clears it, so
        "off" is sent as velocity 127 to ONE_BPM_OFF_NOTE (113) instead -- see that
        constant's comment. Dedup tracks last_bpm_on directly rather than going through
        last_button, since note 114 must never receive a velocity-0 message."""
        if on == self.last_bpm_on:
            return
        self.send_note(ONE_LED_NOTES["BPM"] if on else ONE_BPM_OFF_NOTE, LED_ON)
        self.last_bpm_on = on

    # -- clearing -------------------------------------------------------------
    def _clear_rows(self):
        for std_note, logic_note in self.f1_line_notes:
            self._send_button(std_note, LED_OFF)
            self._send_button(logic_note, LED_OFF)
        for note in self.marker_line_notes + self.rewind_line_notes + self.channel_strip_line_notes:
            self._send_button(note, LED_OFF)
        for notes in self.nav_tiers:
            for note in notes:
                self._send_button(note, LED_OFF)
        for note in self.unused_notes:
            self._send_button(note, LED_OFF)
        if self.toggle_name != "BPM":
            self._set_bpm(False)
        self.f1_line = 0
        self.marker_line = 0
        self.rewind_line = 0
        self.channel_strip_line = 0
        self.nav_bar = 0
        self.peak_hold_remaining = 0.0
        self.peak_on = False

    def _clear_ring(self):
        self._send_ring(RING_FAN)
        self.ring_current = 0

    def _clear_display(self):
        for position in range(1, 13):
            self._send_display(position, 0x20)

    def _clear_meter(self):
        self._send_meter(0)

    def _clear_all(self):
        """Every rendered LED off (Channel Select is left alone -- it only re-arms the
        meter and never needs to go dark), the ring at position 0 (off), the meter at 0,
        the display fully blank."""
        self._clear_rows()
        self._clear_ring()
        self._clear_display()
        self._clear_meter()
        self._send_toggle_led(LED_OFF)
        self.blink_on = False
        self.blink_accum = 0.0

    def full_clear(self):
        """Same as `clear_output()`: used at shutdown too, since the One's toggle LED is
        already part of the full clear (it is software-blinked, not hardware-blinked)."""
        self.clear_output()


# ----------------------------------------------------------------------------
# Audio analysis
# ----------------------------------------------------------------------------
def block_decay(block_s, tau_s):
    """Per-block factor of an exponential decay with time constant tau_s (falls to ~37 % in tau_s)."""
    return float(np.exp(-block_s / max(1e-3, float(tau_s))))


# Floor under a rolling envelope's (hi - lo) span, so a nearly-silent or nearly-constant
# signal (span close to 0) cannot divide the relative reading up to a huge, noisy value.
REL_ENVELOPE_FLOOR = 0.1


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
        # rolling min/max envelopes of the loudness -> relative bar, and of each of the
        # three frequency-band groups -> the X-Touch One's auto-ranging rows. All four
        # share the same time constants (bar_max_fall_s / bar_min_rise_s below).
        self.loud_hi, self.loud_lo = 0.0, 1.0
        self.band_low_hi, self.band_low_lo = 0.0, 1.0
        self.band_mid_hi, self.band_mid_lo = 0.0, 1.0
        self.band_high_hi, self.band_high_lo = 0.0, 1.0
        self.band_rel_low = 0.0
        self.band_rel_mid = 0.0
        self.band_rel_high = 0.0
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
                # the three frequency-band groups feeding the X-Touch One's auto-ranging
                # rows: each is the loudest gain-adjusted sub-band in the group, not diluted
                # by quieter siblings, then normalised against its OWN recent min/max range
                # exactly like the overall loudness above -- a fixed multiplier can never
                # suit both quiet and loud passages when a row only has 5-7 LEDs.
                gains = self.cfg["band_gains"]
                band_low = max(float(self.levels[0]) * gains[0], float(self.levels[1]) * gains[1])
                band_mid = max(float(self.levels[i]) * gains[i] for i in (2, 3, 4, 5))
                band_high = max(float(self.levels[6]) * gains[6], float(self.levels[7]) * gains[7])
                self.band_low_hi, self.band_low_lo, self.band_rel_low = \
                    self._update_envelope(band_low, self.band_low_hi, self.band_low_lo)
                self.band_mid_hi, self.band_mid_lo, self.band_rel_mid = \
                    self._update_envelope(band_mid, self.band_mid_hi, self.band_mid_lo)
                self.band_high_hi, self.band_high_lo, self.band_rel_high = \
                    self._update_envelope(band_high, self.band_high_hi, self.band_high_lo)
            else:
                # the min/max envelopes must not learn the noise floor, so only the exposed
                # relative values decay -- the envelope state itself stays frozen
                self.loudness_rel *= self.release
                self.band_rel_low *= self.release
                self.band_rel_mid *= self.release
                self.band_rel_high *= self.release

    def _update_envelope(self, cur, hi, lo):
        """One step of a rolling min/max envelope: `hi` chases the recent loudest moment
        (jumps up at once, falls at most `hi_decay` per block), `lo` chases the recent
        quietest moment (drops at once, rises at most `lo_rate` per block), and `cur` is
        then reported as its position within that [lo, hi] span, clamped to [0, 1]. Shared
        by every rolling envelope this analyzer keeps (overall loudness, and each of the
        three frequency-band groups) so they all use exactly the same math.
        Returns (new_hi, new_lo, rel); does not touch `self` -- the caller stores the
        result under whichever tracker's own attribute names."""
        hi = max(cur, hi * self.hi_decay)
        lo = min(cur, lo + (cur - lo) * self.lo_rate)
        span = max(hi - lo, REL_ENVELOPE_FLOOR)
        rel = min(1.0, max(0.0, (cur - lo) / span))
        return hi, lo, rel

    def _track_loudness(self, loud):
        """Normalise the loudness against its own recent range, so quiet-but-dynamic music still fills the bar."""
        self.loud_hi, self.loud_lo, self.loudness_rel = self._update_envelope(loud, self.loud_hi, self.loud_lo)

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

    def get_band_rel_low(self):
        with self.lock:
            return float(self.band_rel_low)

    def get_band_rel_mid(self):
        with self.lock:
            return float(self.band_rel_mid)

    def get_band_rel_high(self):
        with self.lock:
            return float(self.band_rel_high)

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
def _log_prefix(label):
    """'[mini] ' / '[one] ' for a device-specific log line, or '' when there is no label."""
    return "[%s] " % label if label else ""


class MidiLink:
    """The MIDI ports of the device, with the port list read through one long-lived pair.

    Every `rtmidi.MidiIn()` / `MidiOut()` is a new CoreMIDI client, and asking a fresh
    client for its port names has to look every endpoint up again - which can block for
    a long time while the USB bus re-enumerates (a Thunderbolt display waking the hub
    the device hangs off). The two probe objects below are created once and answer every
    later port scan; the ports that are really opened stay separate objects, so closing
    them never disturbs the scanning.
    """

    def __init__(self, port_name, on_message, exclude=(), label=None):
        import rtmidi
        self.rtmidi = rtmidi
        self.port_name = port_name
        self.on_message = on_message
        self.label = label       # e.g. "mini" / "one": prefixes this device's log lines
        # Port names that are never the device, however well they match: the program's own
        # virtual DAW device is one of them. Its name contains the device name
        # ("X-TOUCH MINI SHOW" contains "X-TOUCH MINI"), so with the controller unplugged
        # the substring rule below would otherwise connect the show to its own port.
        self.exclude = {str(n).strip().lower() for n in exclude if n and str(n).strip()}
        self.midi_in = None
        self.midi_out = None
        self.lock = threading.Lock()
        self.probe_in = rtmidi.MidiIn()      # never opened: used only to list the ports
        self.probe_out = rtmidi.MidiOut()

    def _usable(self, port):
        return port.strip().lower() not in self.exclude

    def _find(self, ports):
        for i, p in enumerate(ports):
            if p == self.port_name and self._usable(p):
                return i
        for i, p in enumerate(ports):
            if self.port_name.lower() in p.lower() and self._usable(p):
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
        log.info("%sMIDI connected: '%s'", _log_prefix(self.label), out_ports[oi])
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
        log.warning("%sMIDI disconnected", _log_prefix(self.label))

    def send_cc(self, cc, value):
        self._send([0xB0 | MIDI_CH, cc & 0x7F, value & 0x7F])

    def send_note(self, note, velocity):
        self._send([0x90 | MIDI_CH, note & 0x7F, velocity & 0x7F])

    def send_raw(self, msg):
        """Send a message exactly as it is; the DAW proxy passes its traffic through here."""
        self._send(list(msg))

    def _send(self, msg):
        with self.lock:
            if self.midi_out:
                try:
                    self.midi_out.send_message(msg)
                except Exception as e:
                    log.warning("MIDI send failed: %s", e)


# ----------------------------------------------------------------------------
# DAW proxy: the virtual MIDI device a DAW uses instead of the controller
# ----------------------------------------------------------------------------
class DawProxy:
    """A virtual MIDI device that sits between a DAW and the real X-Touch Mini.

    In MC mode every LED of the controller is drawn by the DAW, so a show that lights
    the LEDs itself destroys that picture and cannot put it back: it never saw what the
    DAW sent. The proxy fixes that by being the device the DAW talks to. Two virtual
    ports carry the traffic - `midi_in` is a destination the DAW sends to, `midi_out` a
    source the DAW receives from - and everything that passes through is forwarded to
    the other side, so the DAW keeps working exactly as before.

    What the proxy adds is a cache: every LED message the DAW sends (Note On/Off on
    channel 1, CC 48-55 for the rings) is remembered. While the show renders, those
    messages are held back instead of reaching the device, and when the show stops
    `restore` replays the cache, so the LEDs return to the DAW's own state. Everything
    else - the motor fader, the display digits, SysEx, other channels - is passed on
    untouched in both states.

    The callbacks run on rtmidi's threads: the cache and the rendering flag are guarded
    by `lock`, and messages are sent on without holding it.
    """

    def __init__(self, name, send_device, toggle_note, send_daw=None, led_cc_ranges=None, label=None):
        self.name = name
        self.send_device = send_device   # callable(msg): to the real device (MidiLink.send_raw)
        self.send_daw = send_daw         # callable(msg): to the DAW; open() wires the virtual port
        # the show's own button(s): never handed to the DAW. A single int (the Mini, one
        # note) or an iterable of ints (the One: a button's press note can differ from its
        # LED note, and Channel Left/Right have two valid press notes - see ONE_PRESS_OVERRIDES)
        self.toggle_notes = {toggle_note} if isinstance(toggle_note, int) else set(toggle_note)
        self.notes = {}                  # note -> velocity the DAW last set (0 = LED off)
        self.rings = {}                  # LED-type CC -> value the DAW last set
        # which CCs count as LED state to cache/hold; default matches the Mini's 8 rings
        self.led_cc_ranges = led_cc_ranges if led_cc_ranges is not None else [(RING_CC_BASE, RING_CC_BASE + 8)]
        self.label = label               # e.g. "mini" / "one": prefixes this proxy's log lines
        self.rendering = False
        self.lock = threading.Lock()
        self.midi_in = None
        self.midi_out = None

    # -- ports --------------------------------------------------------------
    def open(self):
        """Create the two virtual ports. False (with one warning) when that is not possible."""
        try:
            import rtmidi
            midi_in = rtmidi.MidiIn()
            midi_in.open_virtual_port(self.name)
            # the DAW's SysEx has to reach the device; clock and active sensing do not
            midi_in.ignore_types(sysex=False, timing=True, active_sense=True)
            midi_in.set_callback(lambda event, data=None: self.from_daw(event[0]))
            midi_out = rtmidi.MidiOut()
            midi_out.open_virtual_port(self.name)
        except Exception as e:
            log.warning("%sDAW proxy unavailable (%s); the show runs without it", _log_prefix(self.label), e)
            return False
        self.midi_in, self.midi_out = midi_in, midi_out
        self.send_daw = midi_out.send_message
        log.info("%sDAW proxy ready: '%s'", _log_prefix(self.label), self.name)
        return True

    def close(self):
        for port in (self.midi_in, self.midi_out):
            if port:
                try:
                    port.close_port()
                except Exception:
                    pass
        self.midi_in = self.midi_out = None
        self.send_daw = None

    # -- rendering flag -----------------------------------------------------
    def set_rendering(self, rendering):
        """Tell the proxy whether the show owns the LEDs right now."""
        with self.lock:
            self.rendering = bool(rendering)

    # -- device -> DAW (rtmidi callback of the real device) -----------------
    def from_device(self, msg):
        """Hand a message from the controller to the DAW; the show's toggle button is consumed."""
        if self.send_daw is None or self._is_toggle(msg):
            return
        try:
            self.send_daw(list(msg))
        except Exception as e:
            log.debug("DAW proxy send failed (%s)", e)

    def _is_toggle(self, msg):
        return len(msg) >= 3 and (msg[0] & 0xF0) in (0x90, 0x80) and msg[1] in self.toggle_notes

    # -- DAW -> device (rtmidi callback of the virtual input) ---------------
    def from_daw(self, msg):
        """Cache the DAW's LED state and pass the message on unless the show owns the LEDs."""
        if not msg:
            return
        log.debug("%sfrom DAW: %s", _log_prefix(self.label), list(msg))
        led = self._led_message(msg)
        with self.lock:
            if led is not None:
                kind, key, value = led
                (self.notes if kind == "note" else self.rings)[key] = value
            hold = led is not None and self.rendering
        if not hold:
            self.send_device(list(msg))

    def _led_message(self, msg):
        """('note', note, velocity) or ('ring', cc, value) for an LED message, else None."""
        if len(msg) < 3:
            return None
        status, d1, d2 = msg[0], msg[1], msg[2]
        kind, ch = status & 0xF0, status & 0x0F
        if ch != MIDI_CH:
            return None
        if kind == 0x90:
            return ("note", d1 & 0x7F, d2 & 0x7F)          # velocity 0 is an LED switched off
        if kind == 0x80:
            return ("note", d1 & 0x7F, 0)
        if kind == 0xB0:
            for lo, hi in self.led_cc_ranges:
                if lo <= d1 < hi:
                    return ("ring", d1, d2 & 0x7F)
        return None

    # -- restore ------------------------------------------------------------
    def restore(self):
        """Replay the DAW's LED state to the device, in the order the DAW first set it.

        Called after the show has cleared its own output. Returns False when nothing was
        ever cached (no DAW connected), in which case the cleared LEDs simply stay dark.
        """
        with self.lock:
            notes, rings = list(self.notes.items()), list(self.rings.items())
        if not notes and not rings:
            return False
        for note, velocity in notes:
            self.send_device([0x90 | MIDI_CH, note & 0x7F, velocity & 0x7F])
        for cc, value in rings:
            self.send_device([0xB0 | MIDI_CH, cc & 0x7F, value & 0x7F])
        log.info("%sDAW LED state restored (%d notes, %d rings)", _log_prefix(self.label), len(notes), len(rings))
        return True


def open_daw_proxy(cfg, send_device, toggle_note, label=None, led_cc_ranges=None):
    """The configured proxy, or None when it is switched off or its ports cannot be created."""
    if not cfg["daw_proxy"]:
        return None
    proxy = DawProxy(cfg["daw_proxy_name"], send_device, toggle_note, led_cc_ranges=led_cc_ranges, label=label)
    return proxy if proxy.open() else None


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


PROXY_PORT_NOTE = "(this program's virtual device, do not choose)"


def _print_list(items, notes=None):
    """The numbered list; `notes` maps a name to a remark printed after it."""
    if not items:
        print("  (the list is empty)")
        return
    for i, name in enumerate(items, 1):
        note = (notes or {}).get(name)
        print("  [%d] %s%s" % (i, name, " " + note if note else ""))


def _first_match(items, needle, exclude=()):
    """The name to suggest: an exact one first, then the first case-insensitive match.

    `exclude` holds names that must never be suggested. The program's own virtual DAW
    device is one of them: its name carries the device name inside it ("X-TOUCH MINI
    SHOW"), so without this the wizard would offer the proxy as the controller and the
    show would then look for a port it deliberately ignores.
    """
    skip = {str(n).strip().lower() for n in exclude if n and str(n).strip()}
    usable = [name for name in items or [] if name.strip().lower() not in skip]
    for name in usable:
        if name == needle:
            return name
    for name in usable:
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


def _ask_text(ask, prompt, default):
    """A freely typed value, or Enter for `default`. Unlike `_ask_name`, digits are taken
    literally instead of indexing a list - used for the One's toggle button/display text,
    which have no numbered list to pick from."""
    answer = ask("%s [%s]: " % (prompt, default)).strip()
    return answer if answer else default


def _config_for_write(cfg):
    """The new-structure view of `cfg` that the wizard writes: shared top-level settings
    plus the 'mini' and 'one' sections, without the legacy flat per-device keys."""
    shared_keys = set(DEFAULT_CONFIG) - {"mini", "one"} - set(LEGACY_MINI_KEYS)
    out = {k: cfg[k] for k in shared_keys}
    out["mini"] = dict(cfg["mini"])
    out["one"] = dict(cfg["one"])
    return out


def run_setup(config_path, ask=input, midi_ports=None, audio_devices=None, noise_samples=None):
    """Interactive first-time setup. Writes `config_path` (in the new mini/one structure)
    and returns an exit code.

    `ask`, `midi_ports` and `audio_devices` can be injected so the wizard runs without a terminal
    (the tests do that); `audio_devices` is a list of input device names. `noise_samples` replaces
    the real input of the noise measurement in the same way: under an injected `ask` the
    measurement is skipped unless the samples are given.
    """
    if ask is input and not sys.stdin.isatty():
        print("--setup must be run from a terminal (standard input is not a terminal).", file=sys.stderr)
        return 2

    cfg = _default_config()
    if os.path.exists(config_path):
        try:
            with open(config_path, encoding="utf-8") as f:
                _apply_user_config(cfg, json.load(f))
            print("Loaded the existing settings: %s" % config_path)
        except Exception as e:
            print("Could not read the existing settings, starting from the defaults (%s)." % e)

    print("\nX-Touch Mini / X-Touch One Music-Reactive LED Show setup (Enter = the default in brackets)\n")

    if midi_ports is None:
        midi_ports = _midi_output_ports()
    # the program's own virtual devices can be in this list; they are marked and never suggested
    proxy_names = [str(cfg["mini"]["daw_proxy_name"] or "").strip(), str(cfg["one"]["daw_proxy_name"] or "").strip()]
    proxy_notes = dict.fromkeys([n for n in proxy_names if n], PROXY_PORT_NOTE)

    print("1) X-Touch Mini MIDI output port [mini.midi_port_name]")
    _print_list(midi_ports, proxy_notes)
    default_port = _first_match(midi_ports, "X-TOUCH MINI", exclude=proxy_names) \
        or cfg["mini"]["midi_port_name"]
    if str(default_port).strip().lower() in {n.lower() for n in proxy_names}:
        default_port = DEFAULT_MINI["midi_port_name"]
    cfg["mini"]["midi_port_name"] = _ask_name(ask, "   Number or port name", midi_ports, default_port)

    print("\n2) Audio input device [audio_input_device]")
    print("   Pick the microphone that will hear the music (choose BlackHole 2ch if you installed it)")
    default_input = None
    if audio_devices is None:
        audio_devices, default_input = _audio_input_devices()
    _print_list(audio_devices)
    default_dev = default_input or cfg["audio_input_device"]
    cfg["audio_input_device"] = _ask_name(ask, "   Number or device name", audio_devices, default_dev)

    print("\n3) Button that switches the Mini's show on and off [mini.toggle_button]: Layer A or B")
    cfg["mini"]["toggle_button"] = _ask_choice(ask, "   A/B", ("A", "B"), cfg["mini"]["toggle_button"])

    print("\n4) Use the Mini's two button-LED loudness bars? [mini.buttons_enabled]")
    cfg["mini"]["buttons_enabled"] = _ask_yes_no(ask, "   y/n", bool(cfg["mini"]["buttons_enabled"]))

    print("\n5) Noise gate [noise_gate_db] (shared by both controllers)")
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

    print("\n6) Enable the X-Touch One? [one.enabled]")
    one_default_port = _first_match(midi_ports, "X-Touch One", exclude=proxy_names)
    cfg["one"]["enabled"] = _ask_yes_no(ask, "   y/n", bool(one_default_port))
    if cfg["one"]["enabled"]:
        print("\n7) Is your X-Touch One set to MC mode? [one.enabled]")
        print("   If not set to MC mode, the motorized fader will click/stutter while the show runs.")
        if not _ask_yes_no(ask, "   y/n", False):
            cfg["one"]["enabled"] = False

    if cfg["one"]["enabled"]:
        print("\n8) X-Touch One MIDI output port [one.midi_port_name]")
        _print_list(midi_ports, proxy_notes)
        default_one_port = one_default_port or cfg["one"]["midi_port_name"]
        if str(default_one_port).strip().lower() in {n.lower() for n in proxy_names}:
            default_one_port = DEFAULT_ONE["midi_port_name"]
        cfg["one"]["midi_port_name"] = _ask_name(ask, "   Number or port name", midi_ports, default_one_port)

        print("\n9) X-Touch One toggle button [one.toggle_button]")
        print("   Any of the 33 LED names (BPM, F1-F6, Marker, Play, Scrub, ...) or a MIDI note number.")
        raw_toggle = _ask_text(ask, "   Button name or note number", cfg["one"]["toggle_button"])
        name, note = _resolve_one_led_note(raw_toggle)
        if note is None:
            print("  '%s' is not a valid button; keeping '%s'." % (raw_toggle, cfg["one"]["toggle_button"]))
        else:
            cfg["one"]["toggle_button"] = name if name is not None else note

        print("\n10) X-Touch One display text [one.display_text]")
        print("   Up to 12 characters, shown in capitals; scrolls automatically if longer than")
        print("   fits. Note: on this display W renders like U, and M, K, X are unreadable or")
        print("   ambiguous, so avoid them if you can.")
        text = _ask_text(ask, "   Text", cfg["one"]["display_text"])
        cfg["one"]["display_text"] = str(text).upper()[:12]

    _write_config(config_path, _config_for_write(cfg))
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


def loop_wait_seconds(enabled, frame, idle_seconds=IDLE_LOOP_SECONDS):
    """How long one main-loop iteration may last: a frame while rendering, seconds while off.

    Nothing is drawn while the show is off and button presses arrive on the MIDI callback
    thread, so waking 30 times a second only to do nothing costs battery for no gain.
    """
    return float(frame) if enabled else float(idle_seconds)


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


class _Device:
    """Runtime bundle for one connected controller (Mini or One): its MIDI link, its
    renderer, its optional DAW proxy, and the poller that answers `still_present()` off
    the main thread."""

    def __init__(self, label, link, renderer, proxy, poller):
        self.label = label
        self.link = link
        self.renderer = renderer
        self.proxy = proxy
        self.poller = poller
        self.rendering = False    # what the proxy was last told about who owns the LEDs


def _poll_connection(dev):
    """Hot-plug bookkeeping for one device, using its poller's latest present() answer.
    Returns True if the device was (re)connected during this call."""
    present = dev.poller.present
    if dev.link.connected():
        if not present:
            dev.link.disconnect()
        return False
    if not present:
        log.debug("[%s] waiting for MIDI port '%s'", dev.label, dev.link.port_name)
        return False
    if dev.link.try_connect():
        dev.renderer.on_connected()
        return True
    return False


def _sync_proxy(dev, running, reconnected):
    """Tell this device's DAW proxy whether the show owns its LEDs right now, and restore
    the DAW's own LED state whenever the show gives them back (or the device reconnects)."""
    if not dev.proxy:
        return
    device_running = dev.link.connected() and running
    if device_running != dev.rendering:
        dev.rendering = device_running
        dev.proxy.set_rendering(dev.rendering)
        if not dev.rendering and dev.link.connected():
            dev.proxy.restore()
    elif reconnected and not dev.rendering:
        dev.proxy.restore()     # a re-plugged controller shows the DAW's state again


def main(argv=None):
    ap = argparse.ArgumentParser(description="X-Touch Mini / X-Touch One music-reactive LED show (MC mode)")
    ap.add_argument("--config", default=os.path.join(os.path.dirname(os.path.abspath(__file__)), "config.json"))
    ap.add_argument("--list-devices", action="store_true", help="list MIDI and audio devices and exit")
    ap.add_argument("--setup", action="store_true", help="interactive setup wizard: write config.json and exit")
    ap.add_argument("--test-rings", action="store_true",
                    help="sweep the Mini's rings once and exit (MIDI path check)")
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

    # the name of every virtual DAW device is kept out of every device search from the
    # start, whether or not that proxy is switched on and before it is created: an earlier
    # run of the program may still own a port of that name, and neither controller must
    # ever mistake the other's proxy (or its own) for real hardware
    proxy_names = [cfg["mini"]["daw_proxy_name"], cfg["one"]["daw_proxy_name"]]

    if args.test_rings:
        link = MidiLink(cfg["mini"]["midi_port_name"], on_message=lambda m: None, exclude=proxy_names)
        if not link.try_connect():
            log.error("MIDI port '%s' not found. Use --list-devices.", cfg["mini"]["midi_port_name"])
            return 2
        ring_test(link)
        return 0

    show_state = ShowState(bool(cfg["show_enabled_at_start"]))
    power = PowerState()      # shared: the display and the power source are not per-device
    devices = []

    if cfg["mini"]["enabled"]:
        link_mini = MidiLink(cfg["mini"]["midi_port_name"], on_message=lambda m: None,
                             exclude=proxy_names, label="mini")
        renderer_mini = MiniRenderer(cfg, send_cc=link_mini.send_cc, send_note=link_mini.send_note,
                                     state=show_state)
        # the DAW talks to the virtual device instead of the controller, so the show knows
        # the LED state the DAW set and can put it back when it stops rendering
        proxy_mini = open_daw_proxy(dict(cfg, daw_proxy=cfg["mini"]["daw_proxy"],
                                         daw_proxy_name=cfg["mini"]["daw_proxy_name"]),
                                    link_mini.send_raw, renderer_mini.toggle_note, label="mini")

        def _on_mini_message(msg, r=renderer_mini, p=proxy_mini):
            r.on_midi(msg)
            if p:
                p.from_device(msg)

        link_mini.on_message = _on_mini_message
        poller_mini = DevicePoller(link_mini.still_present, power.display_asleep, power.on_battery)
        devices.append(_Device("mini", link_mini, renderer_mini, proxy_mini, poller_mini))

    if cfg["one"]["enabled"]:
        link_one = MidiLink(cfg["one"]["midi_port_name"], on_message=lambda m: None,
                            exclude=proxy_names, label="one")
        renderer_one = OneRenderer(cfg, cfg["one"], send_cc=link_one.send_cc, send_note=link_one.send_note,
                                   send_raw=link_one.send_raw, state=show_state)
        one_led_ranges = [(RING_CC_ONE, RING_CC_ONE + 1), (DISPLAY_CC_BASE, DISPLAY_CC_TOP + 1)]
        proxy_one = open_daw_proxy(dict(cfg, daw_proxy=cfg["one"]["daw_proxy"],
                                        daw_proxy_name=cfg["one"]["daw_proxy_name"]),
                                   link_one.send_raw, renderer_one.press_notes,
                                   label="one", led_cc_ranges=one_led_ranges)

        def _on_one_message(msg, r=renderer_one, p=proxy_one):
            r.on_midi(msg)
            if p:
                p.from_device(msg)

        link_one.on_message = _on_one_message
        poller_one = DevicePoller(link_one.still_present, power.display_asleep, power.on_battery)
        devices.append(_Device("one", link_one, renderer_one, proxy_one, poller_one))

    if not devices:
        log.warning("neither controller is enabled in the config; nothing to show")

    # one shared microphone/analysis pipeline: opened only while the show is on and at
    # least one of the two controllers is connected
    audio = AudioController(cfg)
    wake = WakeDetector(WAKE_JUMP_SECONDS)

    # each device's poller asks the system whether it is present on its own thread; those
    # calls can block for a long time when the USB bus re-enumerates, and the show must
    # keep running meanwhile. All pollers also read the (shared) display/power state.
    for dev in devices:
        dev.poller.poll_once()       # one synchronous round, so the first iteration already knows
        dev.poller.start()
    beat = Heartbeat()
    watchdog = None
    if not args.no_watchdog and devices:
        watchdog = Watchdog(lambda: beat.value,
                            lambda: min(d.poller.last_update for d in devices))
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
    def _toggle_desc(dev):
        if dev.label == "mini":
            return "mini=Layer %s" % cfg["mini"]["toggle_button"]
        return "one=%s" % dev.renderer.toggle_label

    toggles = ", ".join(_toggle_desc(d) for d in devices) or "none"
    log.info("started | fps=%s toggle=%s | Ctrl-C to quit", cfg["frame_rate"], toggles)
    try:
        while True:
            now = time.monotonic()
            reconnected = {d.label: False for d in devices}   # set up again in this iteration
            if t_end and now >= t_end:
                log.info("duration reached, quitting")
                break
            if wake.check(time.time(), now):
                # after a system sleep the audio stream is stale and the controllers may
                # have been reset: drop the stream and set them up again from scratch
                log.info("system woke up, reinitializing")
                audio.close()
                for dev in devices:
                    if dev.link.connected():
                        dev.renderer.on_connected()
                        reconnected[dev.label] = True
                last = now
            if now - last_check >= DEVICE_CHECK_SECONDS:
                last_check = now
                # the pollers' latest answers; never a fresh system call from this thread
                if devices:
                    display_asleep = devices[0].poller.display_asleep
                    on_battery = devices[0].poller.on_battery
                for dev in devices:
                    if _poll_connection(dev):
                        reconnected[dev.label] = True
            running = should_run(show_state.enabled, display_asleep, on_battery, cfg)
            if not show_state.enabled:
                suspended = False            # switched off by hand: not a display suspension
            elif not running and not suspended:
                suspended = True
                for dev in devices:
                    if dev.link.connected():
                        dev.renderer.clear_output(suspending=True)   # toggle LED keeps its ON indication (Mini: blinking; One: solid)
                log.info("show suspended (display off, on %s)", "battery" if on_battery else "AC power")
            elif running and suspended:
                suspended = False
                log.info("show resumed")
            for dev in devices:
                _sync_proxy(dev, running, reconnected[dev.label])
            # nothing can use the microphone while no device is connected or the show is not running
            wanted = any(dev.link.connected() for dev in devices) and running and not args.no_audio
            analyzer = audio.update(now, wanted)
            if analyzer is None:
                silent_since = None
            if args.verbose and now - last_status >= 5.0 and analyzer:
                last_status = now
                log.debug("state=%s loud=%.2f rel=%.2f db=%.1f gate=%s levels=%s",
                          "ON" if show_state.enabled else "OFF", analyzer.get_loudness(),
                          analyzer.get_loudness_rel(), analyzer.get_loud_db(), analyzer.get_gate_status(),
                          " ".join("%.2f" % v for v in analyzer.get_levels()))
            levels = analyzer.get_levels() if analyzer else np.zeros(8)
            loudness = analyzer.get_loudness() if analyzer else 0.0
            loudness_rel = analyzer.get_loudness_rel() if analyzer else None
            band_rel_low = analyzer.get_band_rel_low() if analyzer else None
            band_rel_mid = analyzer.get_band_rel_mid() if analyzer else None
            band_rel_high = analyzer.get_band_rel_high() if analyzer else None
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
            for dev in devices:
                if dev.link.connected() and running:
                    dev.renderer.tick(now - last, levels, loudness, loudness_rel,
                                      band_rel_low, band_rel_mid, band_rel_high)
            last = now
            beat.beat()      # tells the watchdog this iteration finished
            # cleared before the flag is read, so a toggle racing this line still wakes the wait
            show_state.wake_event.clear()
            wait = loop_wait_seconds(show_state.enabled, frame)
            show_state.wake_event.wait(max(0.0, wait - (time.monotonic() - now)))
    except KeyboardInterrupt:
        log.info("stopping")
    finally:
        # the shutdown below may take its time; it is not a stall
        if watchdog:
            watchdog.stop()
        for dev in devices:
            dev.poller.stop()
        for dev in devices:
            if dev.link.connected():
                dev.renderer.full_clear()
                if dev.proxy:
                    dev.proxy.restore()      # leave the LEDs as the DAW last drew them
            if dev.proxy:
                dev.proxy.close()
            dev.link.disconnect()
        audio.close()
    return 0


if __name__ == "__main__":
    sys.exit(main())
