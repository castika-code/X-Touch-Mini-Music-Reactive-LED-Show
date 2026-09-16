"""Logic tests for the Show state machine (no hardware needed). Run: .venv/bin/python test_show.py"""
import logging
import xtouch_show as x

sent = []
def cc(c, v): sent.append(("cc", c, v))
def note(n, v): sent.append(("note", n, v))
def rings(): return [s for s in sent if s[0] == "cc" and 48 <= s[1] <= 55]
def last_ring(i): return [s for s in rings() if s[1] == 48 + i][-1][2] - 32
def last_led(n=84): return [s for s in sent if s[0] == "note" and s[1] == n][-1][2]
def btn_sent(notes, velocity): return [s[1] for s in sent if s[0] == "note" and s[1] in notes and s[2] == velocity]

TOP, BOT = x.BUTTON_NOTES[:8], x.BUTTON_NOTES[8:]

logging.basicConfig(level=logging.WARNING)
cfg = x.load_config(None)
lv = [1.0, 0, 0, 0.5, 0, 0, 0, 0.25]
show = x.Show(cfg, cc, note)

# 1. connect while enabled: MC mode, rings cleared, Layer A LED blinking, state ON
show.on_connected()
assert ("cc", 127, 1) in sent and ("note", 84, 1) in sent and len(rings()) == 8
assert show.state == "ON" and last_led() == 1

# 2. rendering runs from the very first tick: no waiting period any more
sent.clear(); show.tick(0.03, lv)
assert last_ring(0) == 11 and last_ring(3) == round(0.5*11) and last_ring(7) == round(0.25*11)

# 3. decay one step per frame; unchanged rings and the LED are not resent
sent.clear(); show.tick(0.03, [0]*8); show.tick(0.03, [0]*8)
assert [s[2]-32 for s in rings() if s[1] == 48] == [10, 9]
sent.clear(); show.tick(0.03, [0]*8)
assert not any(s[1] in (49, 50, 52, 53, 54) for s in rings())   # rings sitting at 0 are not resent
assert not any(s[0] == "note" for s in sent)                    # LED not resent every frame

# 4. fader halves bar height
show.on_midi([0xE8, 0, 64])   # pitch bend ch9, value 8192
assert abs(show.fader_scale - 8192/16256) < 1e-6
for _ in range(12): show.tick(0.03, lv)
assert last_ring(0) == round(8192/16256*11) and show.state == "ON"

# 5. every other control is ignored: encoder turn, encoder push, button, the other Layer button,
#    and a note-off on the toggle button itself all send nothing and change nothing
sent.clear()
for msg in ([0xB0, 16, 1], [0xB0, 23, 65], [0x90, 40, 127], [0x90, 35, 127],
            [0x90, 85, 127], [0x80, 84, 127], [0x90, 84, 0]):
    show.on_midi(msg)
assert sent == [] and show.state == "ON"

# 6. rendering carries on unchanged after that input: the rings still fall and rise
sent.clear()
for _ in range(3): show.tick(0.03, [0]*8)
assert [s[2]-32 for s in rings() if s[1] == 48] == [5, 4, 3]
for _ in range(12): show.tick(0.03, lv)
assert last_ring(0) == round(8192/16256*11) and show.state == "ON"

# 7. the toggle button switches the show off: rings to 0, all 16 button LEDs out, LED dark
sent.clear(); show.on_midi([0x90, 84, 127])
assert show.state == "OFF"
assert len([s for s in rings() if s[2] == 32]) == 8
assert sorted(btn_sent(x.BUTTON_NOTES, 0)) == sorted(x.BUTTON_NOTES)
assert last_led() == 0

# 8. while off nothing is sent at all; the note-off of the toggle press is ignored
sent.clear()
for _ in range(50): show.tick(0.03, lv, 1.0, 1.0)
assert sent == []
show.on_midi([0x90, 84, 0]); assert show.state == "OFF"

# 9. switching back on: LED blinks again and rendering resumes
sent.clear(); show.on_midi([0x90, 84, 127])
assert show.state == "ON" and last_led() == 1
sent.clear(); show.tick(0.03, lv)
assert last_ring(0) == round(8192/16256*11)

# 10. reconnect re-sends MC mode, the blinking LED and clears the rings
sent.clear(); show.on_connected()
assert ("cc", 127, 1) in sent and ("note", 84, 1) in sent and len(rings()) == 8

# 11. Layer B as the toggle button; Layer A is then just another ignored button
cfg2 = dict(cfg); cfg2["toggle_button"] = "B"; sent.clear()
s2 = x.Show(cfg2, cc, note); s2.on_connected()
assert ("note", 85, 1) in sent and s2.state == "ON"
s2.on_midi([0xB0, 16, 1]); assert s2.state == "ON"
s2.on_midi([0x90, 84, 127]); assert s2.state == "ON"
s2.on_midi([0x90, 85, 127]); assert s2.state == "OFF" and last_led(85) == 0
s2.on_midi([0x90, 85, 127]); assert s2.state == "ON" and last_led(85) == 1

# ---------------------------------------------------------------------------
# button rows (top = absolute loudness bar, bottom = relative loudness bar)
# ---------------------------------------------------------------------------

# 12. connect clears all 16; loudness 1.0 with the fader up fills the top row
sent.clear()
s3 = x.Show(cfg, cc, note); s3.on_connected()
assert sorted(btn_sent(x.BUTTON_NOTES, 0)) == sorted(x.BUTTON_NOTES)
sent.clear()
for _ in range(12): s3.tick(0.03, [0]*8, 1.0)
assert sorted(btn_sent(TOP, 127)) == sorted(TOP) and btn_sent(TOP, 0) == []
assert btn_sent(BOT, 127) == []                 # no loudness_rel -> bottom bar counts as 0

# 13. loudness 0.5 -> 4 top buttons; the bar falls one step per frame, unchanged buttons not resent
sent.clear(); s3.tick(0.03, [0]*8, 0.5); s3.tick(0.03, [0]*8, 0.5)
assert btn_sent(TOP, 0) == [TOP[7], TOP[6]]
for _ in range(12): s3.tick(0.03, [0]*8, 0.5)
assert sorted(btn_sent(TOP, 0)) == sorted(TOP[4:]) and btn_sent(TOP, 127) == []
sent.clear(); s3.tick(0.03, [0]*8, 0.5)
assert not any(s[0] == "note" for s in sent)

# 14. loudness_rel drives the bottom row on its own: rel 1.0 with loudness 0.2 -> 8 bottom, 2 top
sent.clear()
for _ in range(12): s3.tick(0.03, [0]*8, 0.2, 1.0)
assert sorted(btn_sent(BOT, 127)) == sorted(BOT) and btn_sent(BOT, 0) == []
assert sorted(btn_sent(TOP, 0)) == sorted(TOP[2:4]) and btn_sent(TOP, 127) == []

# 15. the fader halves both bars
sent.clear(); s3.on_midi([0xE8, 0, 64])         # pitch bend ch9, value 8192 -> scale ~0.5
for _ in range(12): s3.tick(0.03, [0]*8, 1.0, 1.0)
assert sorted(btn_sent(TOP, 127)) == sorted(TOP[2:4]) and sorted(btn_sent(BOT, 0)) == sorted(BOT[4:])

# 16. switching the show off takes all 16 button LEDs out
sent.clear(); s3.on_midi([0x90, 84, 127])
assert s3.state == "OFF" and sorted(btn_sent(x.BUTTON_NOTES, 0)) == sorted(x.BUTTON_NOTES)

# 17. buttons_enabled false -> button LEDs are never touched
cfg4 = dict(cfg); cfg4["buttons_enabled"] = False
sent.clear()
s4 = x.Show(cfg4, cc, note); s4.on_connected()
for _ in range(20): s4.tick(0.03, [0]*8, 1.0, 1.0)
s4.on_midi([0x90, 84, 127])
assert s4.state == "OFF" and not any(s[0] == "note" and s[1] in x.BUTTON_NOTES for s in sent)

# ---------------------------------------------------------------------------
# audio analysis (no stream is ever opened)
# ---------------------------------------------------------------------------
class FakeSD:
    def query_devices(self, i=None):
        d = {"name": "Fake", "max_input_channels": 1, "default_samplerate": 44100.0}
        return d if i is not None else [d]
    class default: device = (0, 0)
import numpy as np
SR, BLOCK = 44100, x.AUDIO_BLOCKSIZE

def analyzer(c=None):
    """A SpectrumAnalyzer without a stream: everything but the device lookup lives in _init_state."""
    a = x.SpectrumAnalyzer.__new__(x.SpectrumAnalyzer)
    a.sd = FakeSD(); a._init_state(c or cfg, SR)
    return a

def feed(a, amp, freq, count, phase=0):
    """Push `count` callback blocks of a sine (amp 0 = silence); the phase runs on across calls."""
    for _ in range(count):
        t = (np.arange(BLOCK) + phase) / float(SR)
        a._callback((amp * np.sin(2*np.pi*freq*t)).astype(np.float32).reshape(-1, 1), BLOCK, None, None)
        phase += BLOCK
    return phase

# 18. band mapping sanity: a 1 kHz sine lands in band 5 (index 4)
an = analyzer()
t = np.arange(4096) / 44100.0
sig = (0.5 * np.sin(2*np.pi*1000*t)).astype(np.float32)
an._callback(sig.reshape(-1, 1), 4096, None, None)
lev = an.get_levels()
assert int(np.argmax(lev)) == 4, lev
assert lev[4] > 0.8, lev            # -6 dBFS sine -> ~0.9 with min -60 / max 0
assert an.get_loudness() > 0.8, an.get_loudness()   # broadband level of the same sine

# 19. relative loudness swings the full range where the absolute loudness barely moves
ad = analyzer(); ph = loud_rel = quiet_rel = 0
for _ in range(4):
    ph = feed(ad, 0.5, 1000, 8, ph); loud_rel = ad.get_loudness_rel()
    ph = feed(ad, 0.05, 1000, 8, ph); quiet_rel = ad.get_loudness_rel()
assert loud_rel > 0.7, loud_rel
assert quiet_rel < 0.3, quiet_rel
assert ad.get_loudness() > 0.5, ad.get_loudness()   # -26 dBFS still reads ~0.6 absolute

# 20. device pick: "default"/"" take the system default input, a name matches exactly or by
#     substring, anything unknown falls back to the default
pick = analyzer()._pick_device
assert pick("default") == (0, "Fake") and pick("") == (0, "Fake") and pick(None) == (0, "Fake")
assert pick("Fake") == (0, "Fake") and pick("fak") == (0, "Fake")
assert pick("No Such Device") == (0, "Fake")

# 21. no noise gate (the default): the gate reads open and a very quiet block is still analysed
assert cfg["noise_gate_db"] is None, cfg["noise_gate_db"]
ao = analyzer(); feed(ao, 0.002, 1000, 6)
assert ao.get_gate_open(), ao.get_loud_db()          # None -> always open
assert ao.get_gate_status() == "off", ao.get_gate_status()
assert ao.get_loud_db() < -45.0, ao.get_loud_db()    # -54 dBFS: a gate would have closed here
assert 0.05 < ao.get_levels()[4] < 0.3, ao.get_levels()   # small but nonzero with min_db -60
assert ao.get_loudness() > 0.0 and ao.get_loudness_rel() > 0.0, ao.get_loudness()

# 21b. load_config takes null or a number for noise_gate_db and rejects anything else
import json as _json, os as _os, tempfile as _tempfile

def load_with_gate(value):
    fd, p = _tempfile.mkstemp(suffix=".json")
    with _os.fdopen(fd, "w", encoding="utf-8") as f:
        _json.dump({"noise_gate_db": value}, f)
    try:
        return x.load_config(p)
    finally:
        _os.remove(p)

assert load_with_gate(None)["noise_gate_db"] is None
assert load_with_gate(-41.0)["noise_gate_db"] == -41.0
assert load_with_gate(-41)["noise_gate_db"] == -41
for bad in ("-45", "off", True, [], {}):
    try:
        load_with_gate(bad)
    except ValueError as e:
        assert "noise_gate_db" in str(e), e
    else:
        raise AssertionError("noise_gate_db %r should be rejected" % (bad,))

# 22. noise gate open: -14 dBFS is well above the -45 dB gate
GATED = dict(cfg); GATED["noise_gate_db"] = -45.0
ag = analyzer(GATED); feed(ag, 0.2, 1000, 6)
assert ag.get_gate_open() and ag.get_loud_db() > GATED["noise_gate_db"], ag.get_loud_db()
assert ag.get_gate_status() is True, ag.get_gate_status()
assert ag.get_levels()[4] > 0.5, ag.get_levels()

# 23. noise gate closed: -54 dBFS counts as silence, bands and the relative bar fall to 0 and
#     the min/max envelopes do not learn the noise floor
aq = analyzer(GATED); ph = 0
for _ in range(3):
    ph = feed(aq, 0.5, 1000, 8, ph)
    ph = feed(aq, 0.05, 1000, 8, ph)
ph = feed(aq, 0.5, 1000, 8, ph)
assert aq.get_gate_open() and aq.get_loudness_rel() > 0.7, aq.get_loudness_rel()
ph = feed(aq, 0.002, 1000, 4, ph)        # flush the loud tail out of the FFT buffer
assert not aq.get_gate_open(), aq.get_loud_db()
lo_before, hi_before = aq.loud_lo, aq.loud_hi
ph = feed(aq, 0.002, 1000, 20, ph)
assert not aq.get_gate_open() and aq.get_loud_db() < GATED["noise_gate_db"], aq.get_loud_db()
assert aq.get_gate_status() is False, aq.get_gate_status()
assert aq.get_levels().max() < 0.02, aq.get_levels()
assert aq.get_loudness_rel() < 0.02, aq.get_loudness_rel()
assert (aq.loud_lo, aq.loud_hi) == (lo_before, hi_before)

# 24. calibration: the 75th percentile ignores the single loud sample, the recommendation adds the margin
measured = x.calibrate_noise(cfg, samples=[-60, -58, -59, -57, -20, -58])
assert -59 < measured < -57, measured
assert x.recommended_gate_db(cfg, measured) == round(measured + 4.0, 1)
assert cfg["noise_gate_margin_db"] == 4.0

# ---------------------------------------------------------------------------
# setup wizard (--setup), driven through the injected ask/device lists
# ---------------------------------------------------------------------------
import contextlib, io, json, os, tempfile

PORTS = ["IAC Driver Bus 1", "X-TOUCH MINI"]
DEVICES = ["MacBook Pro Microphone", "USB Audio CODEC", "Studio Display Microphone"]
SAMPLES = [-60, -58, -59, -57, -20, -58]

def wizard(path, answers, noise_samples=None):
    """Run run_setup with canned answers; returns (exit code, written config, printed text).

    Question order: MIDI port, audio input, toggle button, button bars, measure the noise gate
    (the last one defaults to n: the gate stays off / keeps whatever the file already has).
    """
    it = iter(answers)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = x.run_setup(path, ask=lambda prompt: next(it), midi_ports=PORTS,
                           audio_devices=DEVICES, noise_samples=noise_samples)
    written = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return code, written, out.getvalue()

tmp = tempfile.mkdtemp()
path = os.path.join(tmp, "config.json")

# 25. answers are written; Enter keeps the preselected X-TOUCH MINI port; full key set kept.
#     Enter on the noise question = n: no measurement, so the gate stays off.
code, written, printed = wizard(path, ["", "3", "B", "n", ""])
assert code == 0, code
assert set(written) == set(x.DEFAULT_CONFIG), set(written) ^ set(x.DEFAULT_CONFIG)
assert written["midi_port_name"] == "X-TOUCH MINI", written
assert written["audio_input_device"] == "Studio Display Microphone", written
assert written["toggle_button"] == "B" and written["buttons_enabled"] is False
assert written["noise_gate_db"] is None, written        # default answer -> gate off
assert "leaves the gate off" in printed, printed
assert all(written[k] == x.DEFAULT_CONFIG[k] for k in ("frame_rate", "band_gains", "min_db", "level_release"))
assert path in printed
assert x.load_config(path)["toggle_button"] == "B"   # no unknown/missing keys

# 26. saying yes to the measurement stores room noise + noise_gate_margin_db (= enables the gate)
code, gated, printed = wizard(path, ["", "3", "B", "n", "y"], noise_samples=SAMPLES)
assert code == 0 and gated["noise_gate_db"] == -54.0, gated["noise_gate_db"]
assert set(gated) == set(x.DEFAULT_CONFIG)

# 27. yes without an audio input available: the measurement is skipped and the value kept
code, kept, printed = wizard(path, ["", "3", "B", "n", "y"])
assert code == 0 and kept["noise_gate_db"] == -54.0, kept["noise_gate_db"]
assert "Skipped" in printed, printed

# 28. a second run offers the existing file's values as defaults (the MIDI list keeps its own
#     preselection: the port containing X-TOUCH MINI). Enter on the noise question keeps the
#     existing gate instead of switching it off, and the prompt says so.
code, again, printed = wizard(path, ["", "", "", "", ""])
assert code == 0 and set(again) == set(x.DEFAULT_CONFIG)
assert again["toggle_button"] == "B" and again["buttons_enabled"] is False
assert again["midi_port_name"] == "X-TOUCH MINI", again
assert again["audio_input_device"] == "Studio Display Microphone", again
assert again["noise_gate_db"] == -54.0, again
assert "keeps the current gate (-54.0 dB)" in printed, printed

# 29. an out-of-range number is rejected and asked again; a typed name is taken as is
code, typed, _ = wizard(path, ["9", "My Port", "My USB Mic", "A", "y", "n"])
assert code == 0 and typed["midi_port_name"] == "My Port", typed
assert typed["audio_input_device"] == "My USB Mic" and typed["toggle_button"] == "A"
assert typed["buttons_enabled"] is True
assert typed["noise_gate_db"] == -54.0, typed        # n -> the existing gate is left alone

# 30. with no config file the audio default is "default" = the system default input and the
#     gate is off
os.remove(path)
code, fresh, _ = wizard(path, ["", "", "", "", ""])
assert code == 0 and fresh["audio_input_device"] == "default", fresh
assert set(fresh) == set(x.DEFAULT_CONFIG)
assert fresh["noise_gate_db"] is None and x.DEFAULT_CONFIG["noise_gate_db"] is None

os.remove(path); os.rmdir(tmp)

# ---------------------------------------------------------------------------
# AudioController: the input stream is open only while it is wanted
# (device connected AND show ON), so the microphone indicator goes off otherwise
# ---------------------------------------------------------------------------
class FakeAnalyzer:
    def __init__(self): self.stops = 0
    def stop(self): self.stops += 1

import threading as _threading, time as _time

class FakeOpen:
    """Stands in for open_audio: counts the calls, hands out an analyzer or fails.

    `gate`, when given, is a threading.Event the open waits for, so a test can hold the
    open thread inside open_fn and watch update() carry on without it.
    """
    def __init__(self, fail=False, gate=None):
        self.fail, self.calls, self.made, self.gate = fail, 0, [], gate
    def __call__(self, c):
        if self.gate is not None:
            self.gate.wait(10.0)
        self.calls += 1
        if self.fail:
            return None, RuntimeError("microphone unavailable")
        self.made.append(FakeAnalyzer())
        return self.made[-1], None

def controller(open_fn):
    return x.AudioController(cfg, open_fn=open_fn, retry_seconds=5.0)

def delivered(ac, timeout=10.0):
    """Wait until the open thread the last update() started has handed its result over."""
    end = _time.time() + timeout
    while ac.opening and ac.result is None and _time.time() < end:
        _time.sleep(0.002)
    return ac.result is not None

# 31. never wanted -> the stream is never opened, however long the program runs
op = FakeOpen(); ac = controller(op)
for t in (0.0, 5.0, 10.0, 60.0):
    assert ac.update(t, False) is None
assert op.calls == 0 and ac.analyzer is None and ac.opening is False

# 32. wanted -> the open runs on its own thread: the first update returns None and the
#     analyzer is handed out by the update that follows the open
op = FakeOpen(); ac = controller(op)
assert ac.update(0.0, True) is None and ac.opening is True
assert delivered(ac)
a = ac.update(0.1, True)
assert a is op.made[0] and op.calls == 1 and ac.opening is False
for t in (0.2, 5.0, 30.0):
    assert ac.update(t, True) is a
assert op.calls == 1 and a.stops == 0

# 33. wanted -> not wanted: the analyzer is stopped and dropped; wanting it again reopens at once
assert ac.update(31.0, False) is None
assert a.stops == 1 and ac.analyzer is None
assert ac.update(31.1, True) is None and ac.opening is True
assert delivered(ac)
b = ac.update(31.2, True)
assert b is op.made[1] and b is not a and op.calls == 2 and a.stops == 1

# 34. an open that blocks never blocks update(): it keeps returning None, only one thread
#     is ever started, and the analyzer arrives once the open returns
gate = _threading.Event()
op = FakeOpen(gate=gate); ac = controller(op)
started = _time.time()
for t in (0.0, 0.1, 5.0, 10.0):
    assert ac.update(t, True) is None
assert _time.time() - started < 1.0        # no update waited for the blocked open
assert op.calls == 0 and ac.opening is True
gate.set()
assert delivered(ac)
c = ac.update(10.1, True)
assert c is op.made[0] and op.calls == 1   # one open thread only, however many updates ran

# 35. an open abandoned while it is in flight: the analyzer that arrives late is stopped
#     instead of used, and the next time it is wanted a fresh open starts
gate = _threading.Event()
op = FakeOpen(gate=gate); ac = controller(op)
assert ac.update(0.0, True) is None and ac.opening is True
assert ac.update(0.1, False) is None and ac.abandoned is True
gate.set()
assert delivered(ac)
assert ac.update(0.2, False) is None
assert op.made[0].stops == 1 and ac.analyzer is None and ac.opening is False
assert ac.update(0.3, True) is None and ac.opening is True
assert delivered(ac)
assert ac.update(0.4, True) is op.made[1] and op.calls == 2

x.log.setLevel(logging.CRITICAL)   # the two tests below log the expected open failure

# 36. a failing open returns None, is not retried before retry_seconds counted from the
#     end of the attempt, and is retried after
op = FakeOpen(fail=True); ac = controller(op)
assert ac.update(100.0, True) is None
assert delivered(ac)
assert ac.update(100.0, True) is None and op.calls == 1   # the failure is picked up at 100.0
assert ac.update(101.0, True) is None and op.calls == 1
assert ac.update(104.9, True) is None and op.calls == 1
assert ac.update(105.0, True) is None and op.calls == 2
assert delivered(ac)
assert ac.update(110.0, True) is None and op.calls == 2   # second failure collected at 110.0
op.fail = False
assert ac.update(114.9, True) is None and op.calls == 2
assert ac.update(115.0, True) is None and op.calls == 3
assert delivered(ac)
assert ac.update(115.1, True) is op.made[0]
assert ac.update(120.0, True) is op.made[0] and op.calls == 3

# 37. not wanted while the open keeps failing: no retry attempt at all, however long it waits
op = FakeOpen(fail=True); ac = controller(op)
assert ac.update(0.0, True) is None
assert delivered(ac)
assert ac.update(0.1, True) is None and op.calls == 1
for t in (5.0, 10.0, 60.0):
    assert ac.update(t, False) is None
assert op.calls == 1

x.log.setLevel(logging.NOTSET)

# ---------------------------------------------------------------------------
# sleep/wake and the display/power settings
# ---------------------------------------------------------------------------

# 38. WakeDetector: only wall-clock time running ahead of the monotonic clock is a wake
wd = x.WakeDetector(x.WAKE_JUMP_SECONDS)
assert wd.check(1000.0, 500.0) is False               # the first call only takes the baseline
for i in (1, 2, 3):
    assert wd.check(1000.0 + i, 500.0 + i) is False   # both clocks advance together
assert wd.check(1014.0, 504.0) is True                # 11 s wall time against 1 s monotonic
assert wd.check(1015.0, 505.0) is False               # reported once, then measured afresh
assert wd.check(1018.0, 506.0) is False               # 2 s jump: below the 3 s threshold
assert x.WakeDetector(3.0).check(0.0, 0.0) is False

# 39. should_run: the show stops only while the display is asleep and the setting for the
#     current power source says so
run = x.should_run
assert cfg["show_when_display_off_on_ac"] is False
assert cfg["show_when_display_off_on_battery"] is False
for asleep in (False, True):
    for battery in (False, True):
        assert run(False, asleep, battery, cfg) is False       # switched off stays off
assert run(True, False, False, cfg) is True
assert run(True, False, True, cfg) is True             # display on: the power source does not matter
assert run(True, True, False, cfg) is False            # display off on AC: stops by default
assert run(True, True, True, cfg) is False             # display off on battery: stops
swapped = dict(cfg, show_when_display_off_on_ac=True, show_when_display_off_on_battery=True)
assert run(True, True, False, swapped) is True
assert run(True, True, True, swapped) is True
assert run(True, False, False, swapped) is True and run(True, False, True, swapped) is True
ac_only = dict(cfg, show_when_display_off_on_ac=True)
assert run(True, True, False, ac_only) is True         # display off on AC: kept on by the setting
assert run(True, True, True, ac_only) is False         # battery still follows its own setting

# 40. suspending: the rings and button LEDs go out once while the show stays ON, the toggle
#     LED is left blinking, and the next tick renders again
sent.clear()
s5 = x.Show(cfg, cc, note); s5.on_connected()
for _ in range(12): s5.tick(0.03, lv, 1.0, 1.0)
sent.clear(); s5.clear_output()
assert s5.state == "ON" and s5.enabled is True
assert len([s for s in rings() if s[2] == 32]) == 8
assert sorted(btn_sent(x.BUTTON_NOTES, 0)) == sorted(x.BUTTON_NOTES)
assert not any(s[0] == "note" and s[1] == 84 for s in sent)    # the toggle LED is not touched
sent.clear(); s5.tick(0.03, lv, 1.0, 1.0)
assert last_ring(0) == 11 and last_ring(3) == round(0.5*11)
assert sorted(btn_sent(TOP, 127)) == sorted(TOP)

# 41. PowerState falls back to "display on, AC power" when the frameworks are unavailable
ps = x.PowerState(load=False)
assert ps.display_asleep() is False and ps.on_battery() is False

# ---------------------------------------------------------------------------
# DevicePoller: the blocking system questions are answered off the main loop
# ---------------------------------------------------------------------------
import threading, time

# 42. poll_once reads every probe once and publishes the answers with a fresh timestamp
probe = {"present": False, "asleep": False, "battery": False, "calls": 0}

def probe_present():
    probe["calls"] += 1
    return probe["present"]

dp = x.DevicePoller(probe_present, lambda: probe["asleep"], lambda: probe["battery"], interval=0.01)
assert dp.present is False and dp.display_asleep is False and dp.on_battery is False
before = dp.last_update
probe.update(present=True, asleep=True, battery=True)
dp.poll_once()
assert dp.present is True and dp.display_asleep is True and dp.on_battery is True
assert dp.last_update >= before and probe["calls"] == 1

# 43. a probe that raises keeps the last answer instead of stopping the show
answers = [True, RuntimeError("CoreMIDI is busy")]

def flaky():
    answer = answers.pop(0)
    if isinstance(answer, Exception):
        raise answer
    return answer

dp2 = x.DevicePoller(flaky, lambda: False, lambda: False)
dp2.poll_once(); assert dp2.present is True
dp2.poll_once(); assert dp2.present is True          # the failed question changed nothing

# 44. the thread keeps polling on its own and stop() ends it
dp3 = x.DevicePoller(lambda: True, lambda: False, lambda: False, interval=0.01)
stamp = dp3.last_update
dp3.start()
for _ in range(200):
    if dp3.present and dp3.last_update > stamp:
        break
    time.sleep(0.01)
assert dp3.present is True and dp3.last_update > stamp
dp3.stop(); dp3.join(2.0)
assert not dp3.is_alive()

# ---------------------------------------------------------------------------
# watchdog: a main loop or a poller that stops making progress ends the process
# ---------------------------------------------------------------------------

# 45. stall_check: healthy, main loop stalled, device poll stalled
assert x.stall_check(100.0, 99.0, 99.0, 15.0, 30.0) is None
assert x.stall_check(100.0, 85.0, 70.0, 15.0, 30.0) is None      # exactly at both limits
loop_stall = x.stall_check(100.0, 80.0, 99.0, 15.0, 30.0)
assert loop_stall == "main loop stalled for 20 s, exiting so launchd restarts the show", loop_stall
poll_stall = x.stall_check(100.0, 99.0, 60.0, 15.0, 30.0)
assert poll_stall == "device poll stalled for 40 s, exiting so launchd restarts the show", poll_stall
assert "main loop" in x.stall_check(100.0, 80.0, 60.0, 15.0, 30.0)   # the loop is reported first
now = 1000.0
assert x.stall_check(now, now - x.WATCHDOG_SECONDS - 1, now) is not None       # default limits
assert x.stall_check(now, now, now - x.POLL_STALL_SECONDS - 1) is not None
assert x.stall_check(now, now - 1.0, now - 1.0) is None

# 46. the watchdog thread reports a stalled main loop and stops the program (exit injected)
x.log.setLevel(logging.CRITICAL)      # the expected stall is logged as an error
fired = threading.Event()
wdog = x.Watchdog(lambda: time.monotonic() - 60.0, time.monotonic, interval=0.01,
                  on_stall=fired.set)
wdog.start()
assert fired.wait(5.0)
wdog.join(2.0); assert not wdog.is_alive()

# 47. healthy clocks: the watchdog never fires and stop() ends it
never = threading.Event()
wok = x.Watchdog(time.monotonic, time.monotonic, interval=0.01, on_stall=never.set)
wok.start()
assert not never.wait(0.2)
wok.stop(); wok.join(2.0); assert not wok.is_alive()
x.log.setLevel(logging.NOTSET)

# 48. Heartbeat: every beat moves the value forward
hb = x.Heartbeat(); first = hb.value
time.sleep(0.01); hb.beat()
assert hb.value > first

# ---------------------------------------------------------------------------
# MidiLink: the port list is read through one long-lived probe pair
# ---------------------------------------------------------------------------
import sys as _sys, types as _types

PORT_LIST = ["IAC Driver Bus 1", "X-TOUCH MINI"]
made = {"MidiIn": 0, "MidiOut": 0}

class FakePort:
    """Every construction is counted: one object here = one CoreMIDI client."""
    kind = None
    def __init__(self):
        made[self.kind] += 1
        self.scans = 0
        self.opened = None
    def get_ports(self): self.scans += 1; return list(PORT_LIST)
    def open_port(self, i): self.opened = i
    def ignore_types(self, **kw): pass
    def set_callback(self, cb): self.cb = cb
    def close_port(self): self.opened = None
    def send_message(self, msg): pass

class FakeMidiIn(FakePort): kind = "MidiIn"
class FakeMidiOut(FakePort): kind = "MidiOut"

fake_rtmidi = _types.ModuleType("rtmidi")
fake_rtmidi.MidiIn, fake_rtmidi.MidiOut = FakeMidiIn, FakeMidiOut
_sys.modules["rtmidi"] = fake_rtmidi

# 49. one probe pair is built at startup and answers every later port scan
link = x.MidiLink("X-TOUCH MINI", on_message=lambda m: None)
assert made == {"MidiIn": 1, "MidiOut": 1}, made
probe_in, probe_out = link.probe_in, link.probe_out
for _ in range(5):
    assert link.still_present() is True
assert made == {"MidiIn": 1, "MidiOut": 1}, made         # no new CoreMIDI client per poll
assert probe_out.scans == 5 and (link.probe_in, link.probe_out) == (probe_in, probe_out)

# 50. connecting opens the real ports on their own objects; the probes stay the same two
assert link.try_connect() is True
assert made == {"MidiIn": 2, "MidiOut": 2}, made
assert (link.probe_in, link.probe_out) == (probe_in, probe_out)
assert link.midi_in is not probe_in and link.midi_out is not probe_out
assert link.midi_out.opened == 1 and link.connected() is True
assert probe_in.scans == 1 and probe_out.scans == 6      # try_connect scanned through the probes

# 51. a device that is gone: the probes report it without building anything new
PORT_LIST[:] = ["IAC Driver Bus 1"]
assert link.still_present() is False
link.disconnect()
assert link.connected() is False and made == {"MidiIn": 2, "MidiOut": 2}, made
assert link.try_connect() is False and made == {"MidiIn": 2, "MidiOut": 2}, made

del _sys.modules["rtmidi"]

print("ALL TESTS PASSED")
