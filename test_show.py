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

def feed_mix(a, tones, count, phase=0):
    """Push `count` callback blocks built from the SUM of several sine tones (each an
    (amp, freq) pair), so different frequency bands can be given independent, unrelated
    histories within the same blocks; the phase runs on across calls."""
    for _ in range(count):
        t = (np.arange(BLOCK) + phase) / float(SR)
        sig = np.zeros(BLOCK, dtype=np.float32)
        for amp, freq in tones:
            sig = sig + (amp * np.sin(2*np.pi*freq*t)).astype(np.float32)
        a._callback(sig.reshape(-1, 1), BLOCK, None, None)
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
# per-band auto-ranging (feeds the X-Touch One's three rows; replaces the old fixed
# row_sensitivity multiplier entirely)
# ---------------------------------------------------------------------------

# 24b. each of the three band-group trackers ranges against its OWN recent history,
#      independent of the other two groups. Two analyzers get the exact same mid/high
#      history throughout; only one of them also gets a loud low-band burst (a low
#      frequency, unrelated to the mid/high tones) partway through. The mid/high readings
#      must not be disturbed by that burst at all, while the low reading lights up during
#      it and then falls back once the low tone goes quiet again, as the recent-max
#      envelope decays per bar_max_fall_s.
ab = analyzer()
nb = analyzer()
MID_HIGH = [(0.05, 1000), (0.05, 6000)]   # band index 4 (mid group) and index 7 (high group)
ph_ab = feed_mix(ab, MID_HIGH, 60)
ph_nb = feed_mix(nb, MID_HIGH, 60)

ph_ab = feed_mix(ab, [(0.5, 80)] + MID_HIGH, 40, ph_ab)   # + loud low tone (band index 0)
ph_nb = feed_mix(nb, MID_HIGH, 40, ph_nb)                 # no low tone at all
low_during_burst = ab.get_band_rel_low()
assert low_during_burst > 0.7, low_during_burst
assert abs(ab.get_band_rel_mid() - nb.get_band_rel_mid()) < 0.05, (ab.get_band_rel_mid(), nb.get_band_rel_mid())
assert abs(ab.get_band_rel_high() - nb.get_band_rel_high()) < 0.05, (ab.get_band_rel_high(), nb.get_band_rel_high())

ph_ab = feed_mix(ab, MID_HIGH, 150, ph_ab)   # low tone stops; mid/high keep the same history
ph_nb = feed_mix(nb, MID_HIGH, 150, ph_nb)
low_after_silence = ab.get_band_rel_low()
assert low_after_silence < low_during_burst, (low_during_burst, low_after_silence)
assert abs(ab.get_band_rel_mid() - nb.get_band_rel_mid()) < 0.05, (ab.get_band_rel_mid(), nb.get_band_rel_mid())
assert abs(ab.get_band_rel_high() - nb.get_band_rel_high()) < 0.05, (ab.get_band_rel_high(), nb.get_band_rel_high())

# 24c. a WEAK-but-consistent low-band signal is still judged relative to its OWN recent
#      range, not an absolute threshold: alternate a near-silent stretch (lets the floor
#      drop) with a weak-peak stretch whose raw band level never exceeds roughly 0.2 (well
#      below full scale) -- get_band_rel_low() should still climb close to 1.0.
aw = analyzer(); ph = 0
max_low_level = 0.0
for _ in range(4):
    ph = feed(aw, 0.001, 80, 6, ph)      # near-silence
    max_low_level = max(max_low_level, float(aw.get_levels()[0]), float(aw.get_levels()[1]))
    ph = feed(aw, 0.004, 80, 6, ph)      # weak peak: raw level stays well under 0.2
    max_low_level = max(max_low_level, float(aw.get_levels()[0]), float(aw.get_levels()[1]))
assert max_low_level < 0.2, max_low_level          # the raw signal never got loud in absolute terms
assert aw.get_band_rel_low() > 0.7, aw.get_band_rel_low()   # yet it reads near-full, relative to itself

# 24d. the high-band tracker follows the LOUDEST gain-adjusted sub-band in its group (index
#      7, 8000 Hz), not diluted by a much quieter sibling (index 6, 4000 Hz): once the FFT
#      window is filled with steady-state signal, the tracker's envelope ceiling lands on
#      the loud sub-band's own value, clearly above the pair's average.
ae = analyzer()
ph = feed_mix(ae, [(0.0005, 3500), (0.5, 6000)], 8)
lev = ae.get_levels()
gains_e = cfg["band_gains"]
loud_sub = float(lev[7]) * gains_e[7]
quiet_sub = float(lev[6]) * gains_e[6]
assert loud_sub > quiet_sub + 0.5, (loud_sub, quiet_sub)              # sanity: genuinely lopsided
assert abs(ae.band_high_hi - loud_sub) < 1e-5, (ae.band_high_hi, loud_sub)
assert ae.band_high_hi > (loud_sub + quiet_sub) / 2 + 0.15, ae.band_high_hi   # not diluted to the average

# ---------------------------------------------------------------------------
# setup wizard (--setup), driven through the injected ask/device lists
# ---------------------------------------------------------------------------
import contextlib, io, json, os, tempfile

PORTS = ["IAC Driver Bus 1", "X-TOUCH MINI"]
DEVICES = ["MacBook Pro Microphone", "USB Audio CODEC", "Studio Display Microphone"]
SAMPLES = [-60, -58, -59, -57, -20, -58]

def wizard(path, answers, noise_samples=None, midi_ports=None):
    """Run run_setup with canned answers; returns (exit code, written config, printed text).

    Question order: enable the X-Touch Mini, and - only if that answer is yes - its MIDI
    port; then audio input; then - again only if the Mini is enabled - its toggle button;
    then measure the noise gate (defaults to n: the gate stays off /
    keeps whatever the file already has), enable the X-Touch One, and - only if that
    answer is yes - whether it's set to MC mode (no, or the default, forces it back off
    and skips the rest), then - only if MC mode is confirmed - the One's MIDI port,
    toggle button and display text.
    """
    it = iter(answers)
    out = io.StringIO()
    with contextlib.redirect_stdout(out):
        code = x.run_setup(path, ask=lambda prompt: next(it),
                           midi_ports=PORTS if midi_ports is None else midi_ports,
                           audio_devices=DEVICES, noise_samples=noise_samples)
    written = json.load(open(path, encoding="utf-8")) if os.path.exists(path) else None
    return code, written, out.getvalue()

NEW_CONFIG_KEYS = set(x.DEFAULT_CONFIG) - set(x.LEGACY_MINI_KEYS)   # shared keys + 'mini' + 'one'

tmp = tempfile.mkdtemp()
path = os.path.join(tmp, "config.json")

# 25. answers are written in the new mini/one structure; the Mini is in PORTS, so its enable
#     question defaults to 'yes' and Enter keeps both it and the preselected X-TOUCH MINI
#     port; the One is not in PORTS, so its default is 'no' and it is skipped.
#     Enter on the noise question = n: no measurement, so the gate stays off.
code, written, printed = wizard(path, ["", "", "3", "B", "", "n"])
assert code == 0, code
assert set(written) == NEW_CONFIG_KEYS, set(written) ^ NEW_CONFIG_KEYS
assert written["mini"]["enabled"] is True, written
assert written["mini"]["midi_port_name"] == "X-TOUCH MINI", written
assert written["audio_input_device"] == "Studio Display Microphone", written
assert written["mini"]["toggle_button"] == "B", written
#     the button bars are never asked about, so they keep the default
assert written["mini"]["buttons_enabled"] == x.DEFAULT_MINI["buttons_enabled"], written
assert "button-LED loudness bars" not in printed, printed
assert written["noise_gate_db"] is None, written        # default answer -> gate off
assert "leaves the gate off" in printed, printed
assert written["one"]["enabled"] is False, written
assert written["one"]["toggle_button"] == "Scrub" and written["one"]["display_text"] == "LED ON"
assert all(written[k] == x.DEFAULT_CONFIG[k] for k in ("frame_rate", "band_gains", "min_db", "level_release"))
assert path in printed
loaded = x.load_config(path)
assert loaded["toggle_button"] == "B" and loaded["mini"]["toggle_button"] == "B"   # legacy keys mirror 'mini'

# 26. saying yes to the measurement stores room noise + noise_gate_margin_db (= enables the gate)
code, gated, printed = wizard(path, ["", "", "3", "B", "y", "n"], noise_samples=SAMPLES)
assert code == 0 and gated["noise_gate_db"] == -54.0, gated["noise_gate_db"]
assert set(gated) == NEW_CONFIG_KEYS

# 27. yes without an audio input available: the measurement is skipped and the value kept
code, kept, printed = wizard(path, ["", "", "3", "B", "y", "n"])
assert code == 0 and kept["noise_gate_db"] == -54.0, kept["noise_gate_db"]
assert "Skipped" in printed, printed

# 28. a second run offers the existing file's values as defaults (the MIDI list keeps its own
#     preselection: the port containing X-TOUCH MINI). Enter on the noise question keeps the
#     existing gate instead of switching it off, and the prompt says so. The One's default is
#     still 'no' (its port presence, not the stored value, drives the default).
code, again, printed = wizard(path, ["", "", "", "", "", ""])
assert code == 0 and set(again) == NEW_CONFIG_KEYS
assert again["mini"]["toggle_button"] == "B", again
assert again["mini"]["buttons_enabled"] == written["mini"]["buttons_enabled"], again   # never asked
assert again["mini"]["midi_port_name"] == "X-TOUCH MINI", again
assert again["audio_input_device"] == "Studio Display Microphone", again
assert again["noise_gate_db"] == -54.0, again
assert "keeps the current gate (-54.0 dB)" in printed, printed
assert again["one"]["enabled"] is False

# 29. an out-of-range number is rejected and asked again; a typed name is taken as is;
#     saying yes to the One asks its three questions
code, typed, _ = wizard(path, ["y", "9", "My Port", "My USB Mic", "A", "n", "y", "y",
                               "My One Port", "F2", "hi there!!"])
assert code == 0 and typed["mini"]["midi_port_name"] == "My Port", typed
assert typed["audio_input_device"] == "My USB Mic" and typed["mini"]["toggle_button"] == "A"
assert typed["mini"]["buttons_enabled"] == again["mini"]["buttons_enabled"], typed   # never asked
assert typed["noise_gate_db"] == -54.0, typed        # n -> the existing gate is left alone
assert typed["one"]["enabled"] is True
assert typed["one"]["midi_port_name"] == "My One Port"
assert typed["one"]["toggle_button"] == "F2"
assert typed["one"]["display_text"] == "HI THERE!!"

# 29b. a display text longer than the 12-character window is kept in full, just upper-cased
code, long_text, _ = wizard(path, ["y", "9", "My Port", "My USB Mic", "A", "n", "y", "y",
                                   "My One Port", "F2", "show must go on"])
assert code == 0 and long_text["one"]["display_text"] == "SHOW MUST GO ON", long_text["one"]

# 30. with no config file the audio default is "default" = the system default input and the
#     gate is off; an invalid typed toggle button keeps the previous value with a message
os.remove(path)
code, fresh, printed = wizard(path, ["", "", "", "", "", "y", "y", "", "not a button", ""])
assert code == 0 and fresh["audio_input_device"] == "default", fresh
assert set(fresh) == NEW_CONFIG_KEYS
assert fresh["noise_gate_db"] is None and x.DEFAULT_CONFIG["noise_gate_db"] is None
assert fresh["one"]["enabled"] is True
assert fresh["one"]["toggle_button"] == "Scrub", fresh          # invalid input -> kept as-is
assert "is not a valid button" in printed, printed
#     the prompt spells out all 33 names with their row codes, generated from ONE_BUTTON_ROWS
#     so it cannot go stale when a button is renamed, and laid out one line per physical row
row_lines = x._one_row_code_lines()
assert all("   " + line + "\n" in printed for line in row_lines), printed
assert all(len(line) <= 75 for line in row_lines), row_lines
assert row_lines[0].startswith("Row 1: BPM(11) Channel Select(13)"), row_lines
assert "Row 9: Down(91)" in row_lines, row_lines
listed = " ".join(row_lines)
assert all("%s(%d)" % (n, c) in listed for c, n in x.ONE_ROW_CODES.items()), listed
assert "Master" not in listed and "(12)" not in listed, listed   # Master's slot has no code
assert "Master sits at 12" in printed, printed

# 30b. a row code entered at that question is stored as the button name it resolves to, never
#      as the code itself; an unassigned code is rejected like any other invalid answer
code, by_code, printed = wizard(path, ["", "", "", "", "", "y", "y", "", "53", ""])
assert code == 0 and by_code["one"]["toggle_button"] == "Scrub", by_code["one"]
code, by_code2, _ = wizard(path, ["", "", "", "", "", "y", "y", "", "16", ""])
assert code == 0 and by_code2["one"]["toggle_button"] == "Channel Record", by_code2["one"]
assert x.load_config(path)["one"]["toggle_button"] == "Channel Record"
for bad in ("12", "18"):
    code, rejected, printed = wizard(path, ["", "", "", "", "", "y", "y", "", bad, ""])
    assert code == 0 and rejected["one"]["toggle_button"] == "Channel Record", (bad, rejected["one"])
    assert "'%s' is not a valid button" % bad in printed, printed

# 31. the suggestion skips the program's own virtual device and prefers the exact name
assert x._first_match(["X-TOUCH MINI SHOW", "X-TOUCH MINI"], "X-TOUCH MINI",
                      exclude=["X-TOUCH MINI SHOW"]) == "X-TOUCH MINI"
assert x._first_match(["X-TOUCH MINI SHOW"], "X-TOUCH MINI",
                      exclude=["X-TOUCH MINI SHOW"]) is None
assert x._first_match(["X-TOUCH MINI Port 1", "X-TOUCH MINI"], "X-TOUCH MINI") == "X-TOUCH MINI"

# 32. the wizard with both ports listed: 'X-TOUCH MINI' is the default that Enter takes,
#     and the virtual device is marked in the numbered list
os.remove(path)
code, picked, printed = wizard(path, ["", "", "", "", "", "n"],
                               midi_ports=["X-TOUCH MINI SHOW", "X-TOUCH MINI"])
assert code == 0 and picked["mini"]["midi_port_name"] == "X-TOUCH MINI", picked
assert "X-TOUCH MINI SHOW (this program's virtual device, do not choose)" in printed, printed
assert "[2] X-TOUCH MINI\n" in printed, printed        # the real one carries no remark

# 33. only the virtual device present, and a stored name that is the virtual device: it is
#     never offered back as the default. The proxy is not a detected Mini, so the enable
#     question defaults to n here and has to be answered y to reach the port question.
code, none_left, printed = wizard(path, ["y", "", "", "", "", "n"], midi_ports=["X-TOUCH MINI SHOW"])
assert code == 0 and none_left["mini"]["midi_port_name"] == "X-TOUCH MINI", none_left
with open(path, "w", encoding="utf-8") as f:
    json.dump({"midi_port_name": "X-TOUCH MINI SHOW"}, f)     # old-format flat key
code, repaired, _ = wizard(path, ["y", "", "", "", "", "n"], midi_ports=["X-TOUCH MINI SHOW"])
assert code == 0 and repaired["mini"]["midi_port_name"] == "X-TOUCH MINI", repaired

# 33b. the X-Touch One's own virtual device and proxy name are excluded the same way
os.remove(path)
code, one_picked, printed = wizard(path, ["y", "", "", "", "", "y", "y", "", "", ""],
                                   midi_ports=["X-TOUCH ONE SHOW", "X-Touch One"])
assert code == 0 and one_picked["one"]["midi_port_name"] == "X-Touch One", one_picked
assert "X-TOUCH ONE SHOW (this program's virtual device, do not choose)" in printed, printed

# 33c. the MC-mode guard: saying yes to enabling the One but no (the safe default) to the
#      MC-mode question forces it back off and skips its three remaining questions, even
#      though the enable answer itself was yes
code, mc_no, printed = wizard(path, ["", "", "", "", "", "y", "n"])
assert code == 0 and mc_no["one"]["enabled"] is False, mc_no

# 33d. answering yes to the MC-mode question proceeds with the existing enable logic
code, mc_yes, printed = wizard(path, ["", "", "", "", "", "y", "y", "", "", ""])
assert code == 0 and mc_yes["one"]["enabled"] is True, mc_yes

# 33e. saying no to the Mini skips its port and toggle-button questions: the three answers
#      that follow are taken by the audio, noise and One questions, so a Mini question
#      wrongly asked here would swallow one and run the answers out
os.remove(path)
code, no_mini, printed = wizard(path, ["n", "2", "n", "n"])
assert code == 0 and no_mini["mini"]["enabled"] is False, no_mini
assert no_mini["audio_input_device"] == "USB Audio CODEC", no_mini
assert "X-Touch Mini MIDI output port" not in printed, printed
assert no_mini["mini"]["toggle_button"] == x.DEFAULT_MINI["toggle_button"], no_mini
assert no_mini["mini"]["buttons_enabled"] == x.DEFAULT_MINI["buttons_enabled"], no_mini
assert x.DEFAULT_MINI["enabled"] is True        # only the wizard answer turns the Mini off

# 33f. the enable default follows the ports, not the stored value: with no Mini port present
#      Enter alone skips the two questions, and the next run - same file, Mini back in the
#      list - defaults to yes and asks them again
code, absent, printed = wizard(path, ["", "1", "n", "n"], midi_ports=["X-Touch One"])
assert code == 0 and absent["mini"]["enabled"] is False, absent
assert absent["audio_input_device"] == "MacBook Pro Microphone", absent
assert "X-Touch Mini MIDI output port" not in printed, printed
code, present, printed = wizard(path, ["", "", "", "", "", "n"])
assert code == 0 and present["mini"]["enabled"] is True, present
assert "X-Touch Mini MIDI output port" in printed, printed
assert present["mini"]["midi_port_name"] == "X-TOUCH MINI", present
assert present["mini"]["toggle_button"] == "A", present
assert present["mini"]["buttons_enabled"] == x.DEFAULT_MINI["buttons_enabled"], present

os.remove(path); os.rmdir(tmp)

# ---------------------------------------------------------------------------
# AudioController: the input stream is open only while it is wanted
# (device connected AND show ON), so the microphone indicator goes off otherwise
# ---------------------------------------------------------------------------
class FakeAnalyzer:
    def __init__(self): self.stops = 0; self.age = 0.0
    def stop(self): self.stops += 1
    def get_callback_age(self): return self.age   # the tests raise `age` to fake a dead callback

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

# 34. never wanted -> the stream is never opened, however long the program runs
op = FakeOpen(); ac = controller(op)
for t in (0.0, 5.0, 10.0, 60.0):
    assert ac.update(t, False) is None
assert op.calls == 0 and ac.analyzer is None and ac.opening is False

# 35. wanted -> the open runs on its own thread: the first update returns None and the
#     analyzer is handed out by the update that follows the open
op = FakeOpen(); ac = controller(op)
assert ac.update(0.0, True) is None and ac.opening is True
assert delivered(ac)
a = ac.update(0.1, True)
assert a is op.made[0] and op.calls == 1 and ac.opening is False
for t in (0.2, 5.0, 30.0):
    assert ac.update(t, True) is a
assert op.calls == 1 and a.stops == 0

# 36. wanted -> not wanted: the analyzer is stopped and dropped; wanting it again reopens at once
assert ac.update(31.0, False) is None
assert a.stops == 1 and ac.analyzer is None
assert ac.update(31.1, True) is None and ac.opening is True
assert delivered(ac)
b = ac.update(31.2, True)
assert b is op.made[1] and b is not a and op.calls == 2 and a.stops == 1

# 37. an open that blocks never blocks update(): it keeps returning None, only one thread
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

# 38. an open abandoned while it is in flight: the analyzer that arrives late is stopped
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

# 39. a failing open returns None, is not retried before retry_seconds counted from the
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

# 40. not wanted while the open keeps failing: no retry attempt at all, however long it waits
op = FakeOpen(fail=True); ac = controller(op)
assert ac.update(0.0, True) is None
assert delivered(ac)
assert ac.update(0.1, True) is None and op.calls == 1
for t in (5.0, 10.0, 60.0):
    assert ac.update(t, False) is None
assert op.calls == 1

x.log.setLevel(logging.NOTSET)

# ---------------------------------------------------------------------------
# a stream that opens cleanly but stops calling back is reopened on its own
# ---------------------------------------------------------------------------

# 40a. an analyzer whose callback keeps firing is never treated as stalled
op = FakeOpen(); ac = controller(op)
assert ac.update(0.0, True) is None
assert delivered(ac)
a = ac.update(0.1, True)
a.age = 2 * (x.AUDIO_BLOCKSIZE / float(SR))     # two normal callback intervals of jitter
for t in (1.0, 60.0, 3600.0):
    assert ac.update(t, True) is a
assert op.calls == 1 and a.stops == 0

# 40b. the threshold keeps real margin: an age just short of it is still healthy
assert x.AUDIO_STALL_SECONDS >= 20 * (x.AUDIO_BLOCKSIZE / float(SR))
a.age = x.AUDIO_STALL_SECONDS - 0.5
assert ac.update(3601.0, True) is a and op.calls == 1 and a.stops == 0

x.log.setLevel(logging.CRITICAL)   # 40c logs the expected stall warning

# 40c. the callback stops firing: the dead analyzer is stopped and dropped, and the normal
#      open path starts a fresh stream at once - no manual restart
a.age = x.AUDIO_STALL_SECONDS
assert ac.update(3602.0, True) is None
assert a.stops == 1 and ac.analyzer is None and ac.opening is True
assert delivered(ac)
b = ac.update(3602.1, True)
assert b is op.made[1] and b is not a and op.calls == 2

# 40d. a stalled analyzer that stops being wanted is closed by the normal path only: the
#      stall check never runs without an analyzer, so it cannot force an unwanted open
op = FakeOpen(); ac = controller(op)
assert ac.update(0.0, True) is None
assert delivered(ac)
c = ac.update(0.1, True)
c.age = 99.0
assert ac.update(0.2, False) is None
assert c.stops == 1 and ac.analyzer is None and ac.opening is False
for t in (5.0, 60.0):
    assert ac.update(t, False) is None
assert op.calls == 1

x.log.setLevel(logging.NOTSET)

# 40e. the analyzer's own age is reset by every callback, silence included
sa = analyzer()
sa.last_callback = _time.monotonic() - 30.0
assert sa.get_callback_age() > 29.0
feed(sa, 0.0, 440.0, 1)            # a block of pure digital silence still calls back
assert sa.get_callback_age() < 1.0

# ---------------------------------------------------------------------------
# sleep/wake and the display/power settings
# ---------------------------------------------------------------------------

# 41. WakeDetector: only wall-clock time running ahead of the monotonic clock is a wake
wd = x.WakeDetector(x.WAKE_JUMP_SECONDS)
assert wd.check(1000.0, 500.0) is False               # the first call only takes the baseline
for i in (1, 2, 3):
    assert wd.check(1000.0 + i, 500.0 + i) is False   # both clocks advance together
assert wd.check(1014.0, 504.0) is True                # 11 s wall time against 1 s monotonic
assert wd.check(1015.0, 505.0) is False               # reported once, then measured afresh
assert wd.check(1018.0, 506.0) is False               # 2 s jump: below the 3 s threshold
assert x.WakeDetector(3.0).check(0.0, 0.0) is False

# 42. should_run: the show stops only while the display is asleep and the setting for the
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

# 43. suspending: the rings and button LEDs go out once while the show stays ON, the toggle
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

# 44. PowerState falls back to "display on, AC power" when the frameworks are unavailable
ps = x.PowerState(load=False)
assert ps.display_asleep() is False and ps.on_battery() is False

# ---------------------------------------------------------------------------
# DevicePoller: the blocking system questions are answered off the main loop
# ---------------------------------------------------------------------------
import threading, time

# 45. poll_once reads every probe once and publishes the answers with a fresh timestamp
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

# 46. a probe that raises keeps the last answer instead of stopping the show
answers = [True, RuntimeError("CoreMIDI is busy")]

def flaky():
    answer = answers.pop(0)
    if isinstance(answer, Exception):
        raise answer
    return answer

dp2 = x.DevicePoller(flaky, lambda: False, lambda: False)
dp2.poll_once(); assert dp2.present is True
dp2.poll_once(); assert dp2.present is True          # the failed question changed nothing

# 47. the thread keeps polling on its own and stop() ends it
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

# 48. stall_check: healthy, main loop stalled, device poll stalled
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

# 49. the watchdog thread reports a stalled main loop and stops the program (exit injected)
x.log.setLevel(logging.CRITICAL)      # the expected stall is logged as an error
fired = threading.Event()
wdog = x.Watchdog(lambda: time.monotonic() - 60.0, time.monotonic, interval=0.01,
                  on_stall=fired.set)
wdog.start()
assert fired.wait(5.0)
wdog.join(2.0); assert not wdog.is_alive()

# 50. healthy clocks: the watchdog never fires and stop() ends it
never = threading.Event()
wok = x.Watchdog(time.monotonic, time.monotonic, interval=0.01, on_stall=never.set)
wok.start()
assert not never.wait(0.2)
wok.stop(); wok.join(2.0); assert not wok.is_alive()
x.log.setLevel(logging.NOTSET)

# 51. Heartbeat: every beat moves the value forward
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

# 52. one probe pair is built at startup and answers every later port scan
link = x.MidiLink("X-TOUCH MINI", on_message=lambda m: None)
assert made == {"MidiIn": 1, "MidiOut": 1}, made
probe_in, probe_out = link.probe_in, link.probe_out
for _ in range(5):
    assert link.still_present() is True
assert made == {"MidiIn": 1, "MidiOut": 1}, made         # no new CoreMIDI client per poll
assert probe_out.scans == 5 and (link.probe_in, link.probe_out) == (probe_in, probe_out)

# 53. connecting opens the real ports on their own objects; the probes stay the same two
assert link.try_connect() is True
assert made == {"MidiIn": 2, "MidiOut": 2}, made
assert (link.probe_in, link.probe_out) == (probe_in, probe_out)
assert link.midi_in is not probe_in and link.midi_out is not probe_out
assert link.midi_out.opened == 1 and link.connected() is True
assert probe_in.scans == 1 and probe_out.scans == 6      # try_connect scanned through the probes

# 54. a device that is gone: the probes report it without building anything new
PORT_LIST[:] = ["IAC Driver Bus 1"]
assert link.still_present() is False
link.disconnect()
assert link.connected() is False and made == {"MidiIn": 2, "MidiOut": 2}, made
assert link.try_connect() is False and made == {"MidiIn": 2, "MidiOut": 2}, made

# 55. the program's own virtual device is never taken for the controller: with the real
#     one unplugged, only 'X-TOUCH MINI SHOW' is left and it must be ignored
PORT_LIST[:] = ["X-TOUCH MINI SHOW"]
own = x.MidiLink("X-TOUCH MINI", on_message=lambda m: None, exclude=["X-TOUCH MINI SHOW"])
assert own.still_present() is False                  # the substring rule must not fire
assert own.try_connect() is False and own.connected() is False
mirror = x.MidiLink("X-TOUCH MINI SHOW", on_message=lambda m: None,
                    exclude=["X-TOUCH MINI SHOW"])
assert mirror.still_present() is False               # not even by exact name
assert mirror.try_connect() is False and mirror.connected() is False

# 56. with the controller plugged back in, the excluded name is skipped over and the real
#     device is the one that is opened
PORT_LIST[:] = ["X-TOUCH MINI SHOW", "X-TOUCH MINI"]
assert own.still_present() is True
assert own.try_connect() is True and own.connected() is True
assert own.midi_in.opened == 1 and own.midi_out.opened == 1
own.disconnect()

del _sys.modules["rtmidi"]

# ---------------------------------------------------------------------------
# DawProxy: the DAW drives a virtual device, the show gives its LEDs back
# ---------------------------------------------------------------------------
class Collect(logging.Handler):
    """Keeps the formatted log messages so a test can assert on them."""
    def __init__(self):
        logging.Handler.__init__(self)
        self.lines = []
    def emit(self, record):
        self.lines.append(record.getMessage())

SYSEX = [0xF0, 0x00, 0x20, 0x32, 0x7F, 0xF7]
TOGGLE = x.LAYER_NOTES["A"]
to_device = []

# 57. config: the proxy is on by default, named, and the wizard does not ask about it
assert x.DEFAULT_CONFIG["daw_proxy"] is True
assert x.DEFAULT_CONFIG["daw_proxy_name"] == "X-TOUCH MINI SHOW"
assert cfg["daw_proxy"] is True and cfg["daw_proxy_name"] == "X-TOUCH MINI SHOW"

# 58. a DAW LED message while the show is OFF: forwarded to the device and cached
p = x.DawProxy("proxy", to_device.append, TOGGLE)
assert p.rendering is False
p.from_daw([0x90, 40, 127])          # button LED on
p.from_daw([0xB0, 48, 32 + 5])       # ring 1 at position 5
p.from_daw([0x80, 41, 64])           # note off = LED out
assert to_device == [[0x90, 40, 127], [0xB0, 48, 37], [0x80, 41, 64]], to_device
assert p.notes == {40: 127, 41: 0} and p.rings == {48: 37}, (p.notes, p.rings)

# 59. the same messages while the show is ON: cached only, the device is left to the show
to_device.clear(); p.set_rendering(True)
p.from_daw([0x90, 40, 1]); p.from_daw([0xB0, 55, 32 + 9]); p.from_daw([0x90, 40, 0])
assert to_device == [], to_device
assert p.notes == {40: 0, 41: 0} and p.rings == {48: 37, 55: 41}, (p.notes, p.rings)

# 60. pass-through traffic reaches the device in both states and is never cached:
#     the motor fader, the display digits, SysEx, another channel, an encoder CC
for state in (True, False):
    p.set_rendering(state); to_device.clear()
    passed = [[0xE8, 0, 100], [0xB0, 70, 12], list(SYSEX), [0x91, 40, 127], [0xB0, 16, 1]]
    for msg in passed:
        p.from_daw(list(msg))
    assert to_device == passed, (state, to_device)
assert p.notes == {40: 0, 41: 0} and p.rings == {48: 37, 55: 41}, (p.notes, p.rings)

# 61. restore: every cached note (0 included) and every ring, in the order they arrived,
#     with the counts logged
grab = Collect(); x.log.addHandler(grab); x.log.setLevel(logging.INFO)
to_device.clear()
assert p.restore() is True
assert to_device == [[0x90, 40, 0], [0x90, 41, 0], [0xB0, 48, 37], [0xB0, 55, 41]], to_device
assert any("DAW LED state restored (2 notes, 2 rings)" in line for line in grab.lines), grab.lines
x.log.removeHandler(grab); x.log.setLevel(logging.NOTSET)

# 62. nothing cached (no DAW connected): restore does nothing and says so
fresh = x.DawProxy("proxy", to_device.append, TOGGLE)
to_device.clear()
assert fresh.restore() is False and to_device == []

# 63. device -> DAW: everything is forwarded in both states except the toggle button,
#     which belongs to the show alone
to_daw = []
p2 = x.DawProxy("proxy", to_device.append, TOGGLE, send_daw=to_daw.append)
device_msgs = [[0x90, TOGGLE, 127], [0x80, TOGGLE, 0], [0x90, x.LAYER_NOTES["B"], 127],
               [0xB0, 16, 1], [0xE8, 0, 64], [0x90, 40, 127], [0x90, 32, 127]]
for state in (False, True):
    p2.set_rendering(state); to_daw.clear()
    for msg in device_msgs:
        p2.from_device(list(msg))
    assert to_daw == device_msgs[2:], (state, to_daw)
assert to_device == []                    # the device-ward path is untouched by this

# 64. without a DAW-ward port nothing is sent and nothing raises
p3 = x.DawProxy("proxy", to_device.append, TOGGLE)
p3.from_device([0x90, 40, 127])
assert p3.send_daw is None

# -- the virtual ports, through a fake rtmidi -------------------------------
virtual = {"in": [], "out": []}

class VirtualIn(FakeMidiIn):
    def open_virtual_port(self, name): virtual["in"].append(name); self.opened = name

class VirtualOut(FakeMidiOut):
    def __init__(self): FakeMidiOut.__init__(self); self.sent = []
    def open_virtual_port(self, name): virtual["out"].append(name); self.opened = name
    def send_message(self, msg): self.sent.append(list(msg))

fake_rtmidi.MidiIn, fake_rtmidi.MidiOut = VirtualIn, VirtualOut
_sys.modules["rtmidi"] = fake_rtmidi
made.update(MidiIn=0, MidiOut=0)

# 65. enabled: one virtual destination and one virtual source, both under the configured
#     name; the virtual input's callback is the DAW-ward entry point and the device's
#     messages leave through the virtual output
to_device.clear()
p4 = x.open_daw_proxy(cfg, to_device.append, TOGGLE)
assert p4 is not None
assert virtual == {"in": ["X-TOUCH MINI SHOW"], "out": ["X-TOUCH MINI SHOW"]}, virtual
assert made == {"MidiIn": 1, "MidiOut": 1}, made
p4.midi_in.cb(([0xB0, 49, 40], 0.0))                 # the DAW writes a ring
assert to_device == [[0xB0, 49, 40]] and p4.rings == {49: 40}, (to_device, p4.rings)
p4.from_device([0x90, 41, 127])
assert p4.midi_out.sent == [[0x90, 41, 127]], p4.midi_out.sent
p4.close()
assert p4.midi_in is None and p4.midi_out is None and p4.send_daw is None

# 66. disabled: no port is created at all and there is nothing to restore
made.update(MidiIn=0, MidiOut=0); virtual["in"].clear(); virtual["out"].clear()
off = x.open_daw_proxy(dict(cfg, daw_proxy=False), to_device.append, TOGGLE)
assert off is None
assert made == {"MidiIn": 0, "MidiOut": 0} and virtual == {"in": [], "out": []}

# 67. ports that cannot be created: the show carries on without a proxy
class BrokenIn(VirtualIn):
    def open_virtual_port(self, name): raise RuntimeError("virtual ports unavailable")

fake_rtmidi.MidiIn = BrokenIn
x.log.setLevel(logging.CRITICAL)          # the expected warning
assert x.open_daw_proxy(cfg, to_device.append, TOGGLE) is None
x.log.setLevel(logging.NOTSET)

del _sys.modules["rtmidi"]

# 68. an empty proxy name is refused, and the proxy can be switched off in the config
def load_with(**keys):
    fd, p = _tempfile.mkstemp(suffix=".json")
    with _os.fdopen(fd, "w", encoding="utf-8") as f:
        _json.dump(keys, f)
    try:
        return x.load_config(p)
    finally:
        _os.remove(p)

assert load_with(daw_proxy=False)["daw_proxy"] is False
assert load_with(daw_proxy=False, daw_proxy_name="")["daw_proxy_name"] == ""   # unused, so fine
assert load_with(daw_proxy_name="My Surface")["daw_proxy_name"] == "My Surface"
for bad in ("", "   ", None):
    try:
        load_with(daw_proxy=True, daw_proxy_name=bad)
    except ValueError as e:
        assert "daw_proxy_name" in str(e), e
    else:
        raise AssertionError("daw_proxy_name %r should be rejected" % (bad,))

# ---------------------------------------------------------------------------
# config: the old single-device flat format migrates into the new mini/one structure,
# and the new structure loads directly, without losing the legacy flat mirror
# ---------------------------------------------------------------------------

# 69. an old-format config.json (flat keys only) migrates into 'mini'; 'one' gets its defaults
old_flat = {"midi_port_name": "X-TOUCH MINI", "toggle_button": "B", "buttons_enabled": False,
           "daw_proxy": False, "daw_proxy_name": "X-TOUCH MINI SHOW", "noise_gate_db": -41.0}
migrated = load_with(**old_flat)
assert migrated["mini"]["toggle_button"] == "B" and migrated["mini"]["buttons_enabled"] is False
assert migrated["mini"]["daw_proxy"] is False
assert migrated["toggle_button"] == "B" and migrated["buttons_enabled"] is False   # legacy mirror
assert migrated["noise_gate_db"] == -41.0
assert migrated["one"] == x.DEFAULT_ONE, migrated["one"]

# 70. a new-format config (mini/one sections) loads directly; the legacy flat keys mirror it
def load_raw(obj):
    fd, p = _tempfile.mkstemp(suffix=".json")
    with _os.fdopen(fd, "w", encoding="utf-8") as f:
        _json.dump(obj, f)
    try:
        return x.load_config(p)
    finally:
        _os.remove(p)

loaded2 = load_raw({"mini": {"toggle_button": "B", "midi_port_name": "Custom Mini"},
                    "one": {"enabled": False, "toggle_button": "bpm", "display_text": "hi there!!"}})
assert loaded2["mini"]["midi_port_name"] == "Custom Mini" and loaded2["midi_port_name"] == "Custom Mini"
assert loaded2["mini"]["toggle_button"] == "B" and loaded2["toggle_button"] == "B"
assert loaded2["one"]["enabled"] is False
assert loaded2["one"]["toggle_button"] == "BPM"                # case-insensitive, canonicalized
assert loaded2["one"]["display_text"] == "HI THERE!!"

# 70b. a display text longer than the 12-character window survives loading uncut
loaded3 = load_raw({"one": {"display_text": "show must go on"}})
assert loaded3["one"]["display_text"] == "SHOW MUST GO ON", loaded3["one"]["display_text"]

# 71. an invalid one.toggle_button falls back to 'Scrub' (with a warning)
x.log.setLevel(logging.CRITICAL)
bad_toggle = load_raw({"one": {"toggle_button": "Not A Button"}})
x.log.setLevel(logging.NOTSET)
assert bad_toggle["one"]["toggle_button"] == "Scrub"

# 72. _resolve_one_led_note: names (case-insensitive), literal note numbers (named or not),
#     and invalid input
assert x._resolve_one_led_note("BPM") == ("BPM", 114)
assert x._resolve_one_led_note("bpm") == ("BPM", 114)
assert x._resolve_one_led_note("scrub") == ("Scrub", 101)
assert x._resolve_one_led_note(101) == ("Scrub", 101)
assert x._resolve_one_led_note("74") == ("F1", 74)             # a bare note number that names an LED
assert x._resolve_one_led_note(72) == (None, 72)                # a valid note with no name
assert x._resolve_one_led_note("nonsense") == (None, None)
assert x._resolve_one_led_note(200) == (None, None)             # out of MIDI range

# 72b. the physical row layout the wizard's codes are built from covers every LED exactly
#      once and nothing else: a rename in ONE_LED_NOTES that missed ONE_BUTTON_ROWS (or the
#      other way round) fails here instead of printing a code that resolves to nothing
row_names = [n for row in x.ONE_BUTTON_ROWS for n in row if n is not None]
assert len(row_names) == len(set(row_names)) == len(x.ONE_LED_NOTES), row_names
assert set(row_names) == set(x.ONE_LED_NOTES), set(row_names) ^ set(x.ONE_LED_NOTES)
assert x.ONE_BUTTON_ROWS[0][1] is None                      # Master: its slot counts, it is not selectable
assert [n for row in x.ONE_BUTTON_ROWS for n in row].count(None) == 1, x.ONE_BUTTON_ROWS
assert len(x.ONE_BUTTON_ROWS) == 9, x.ONE_BUTTON_ROWS
assert len(x.ONE_ROW_CODES) == len(x.ONE_LED_NOTES)
assert all(11 <= c <= 99 and c % 10 != 0 for c in x.ONE_ROW_CODES), x.ONE_ROW_CODES
assert 12 not in x.ONE_ROW_CODES and 18 not in x.ONE_ROW_CODES

# 72c. _resolve_one_toggle_answer: the wizard also takes a two-digit row+position code
#      (tens = row from the top, ones = position from the left), at least one per row
for code, expected in [(11, "BPM"), (13, "Channel Select"), (16, "Channel Record"),
                       (21, "F1"), (26, "F6"), (31, "Marker"), (37, "Solo"),
                       (41, "Rewind"), (45, "Record"), (51, "Bank Left"), (53, "Scrub"),
                       (61, "Channel Left"), (71, "Up"), (81, "Left"), (83, "Right"),
                       (91, "Down")]:
    assert x._resolve_one_toggle_answer(str(code)) == (expected, x.ONE_LED_NOTES[expected]), code
#      row 1's Solo/Rec are the channel-strip buttons, not row 3's Solo / row 4's Record
assert x._resolve_one_toggle_answer("15") == ("Channel Solo", 8)
assert x._resolve_one_toggle_answer("37") == ("Solo", 90)
assert x._resolve_one_toggle_answer("45") == ("Record", 95)
#      a code with no button behind it is rejected outright rather than falling through to
#      the note number it looks like: 12 is Master's slot, 18 is past the end of row 1
assert x._resolve_one_toggle_answer("12") == (None, None)
assert x._resolve_one_toggle_answer("18") == (None, None)
assert x._resolve_one_toggle_answer("54") == (None, None)      # row 5 stops at Scrub(53)
assert x._resolve_one_toggle_answer("10") == (None, None)      # no position 0
assert x._resolve_one_toggle_answer("99") == (None, None)
#      names and note numbers still resolve exactly as _resolve_one_led_note does
assert x._resolve_one_toggle_answer("bpm") == ("BPM", 114)
assert x._resolve_one_toggle_answer("Bank Left") == ("Bank Left", 46)
assert x._resolve_one_toggle_answer(101) == ("Scrub", 101)
assert x._resolve_one_toggle_answer("114") == ("BPM", 114)     # three digits: a note, not a code
assert x._resolve_one_toggle_answer("8") == ("Channel Solo", 8)
assert x._resolve_one_toggle_answer(74) == ("F1", 74)          # stored ints stay note numbers
assert x._resolve_one_toggle_answer("nonsense") == (None, None)
#      codes are a wizard convenience only: a config file still means note numbers by them
assert x._resolve_one_led_note("11") == (None, 11)

# ---------------------------------------------------------------------------
# X-Touch One: OneRenderer (bars, ring, display, software toggle blink)
# ---------------------------------------------------------------------------
one_sent = []
def one_cc(c, v): one_sent.append(("cc", c, v))
def one_note(n, v): one_sent.append(("note", n, v))
def one_raw(msg): one_sent.append(("raw", msg[0], msg[1]))   # 3-tuple, like ("cc"|"note", ...): keeps every existing (kind, n, v) unpack in this file working

one_default = dict(x.DEFAULT_ONE)

# 73. toggle mapping: BPM presses on note 53 (not its LED note 114); Scrub (the default)
#     presses on note 101, same as its LED
one_sent.clear()
r1 = x.OneRenderer(cfg, dict(one_default, toggle_button="BPM"), one_cc, one_note, one_raw)
assert r1.toggle_note == 114 and r1.press_notes == (53,)
assert r1.enabled is True
r1.on_midi([0x90, 114, 127])            # the LED note itself is NOT a press for BPM
assert r1.enabled is True
r1.on_midi([0x90, 53, 127])
assert r1.enabled is False
r1.on_midi([0x90, 53, 127])
assert r1.enabled is True

r2 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)        # default toggle: Scrub
assert r2.toggle_note == 101 and r2.press_notes == (101,)
r2.on_midi([0x90, 101, 127])
assert r2.enabled is False

# 74. Channel Left/Right accept either Master-mode press note
r3 = x.OneRenderer(cfg, dict(one_default, toggle_button="Channel Left"), one_cc, one_note, one_raw)
assert sorted(r3.press_notes) == [31, 48]
r3.on_midi([0x90, 31, 127]); assert r3.enabled is False
r3.on_midi([0x90, 48, 127]); assert r3.enabled is True

# 75. F1 line is driven directly by the analyzer's band_rel_high value (the SpectrumAnalyzer
#     already clamps it to [0,1] before it gets here -- see SpectrumAnalyzer._update_envelope);
#     the configured toggle button is removed from its row's fill sequence.
one_sent.clear()
r4 = x.OneRenderer(cfg, dict(one_default, toggle_button="F3"), one_cc, one_note, one_raw)
assert "F3" not in r4.f1_line_names and len(r4.f1_line_notes) == 5
for _ in range(3): r4.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=1.0)
r4_flat = [n for pair in r4.f1_line_notes for n in pair]
assert all(r4.last_button.get(n) == x.LED_ON for n in r4_flat)
assert x.ONE_F1_LINE_NOTES_STANDARD[2] not in r4_flat and x.ONE_F1_LINE_NOTES_LOGIC[2] not in r4_flat  # F3 = index 2

one_sent.clear()
r5 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)   # toggle = Scrub, in no row
assert len(r5.f1_line_notes) == 6 and len(r5.marker_line_notes) == 7 and len(r5.rewind_line_notes) == 5
r5.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=0.5)
lit_positions = sum(1 for std, logic in r5.f1_line_notes
                    if r5.last_button.get(std) == x.LED_ON and r5.last_button.get(logic) == x.LED_ON)
assert lit_positions == round(0.5 * 6)

# 75b. F1-F6 answer at notes 54-59 in the "MC Standard" personality and at 74-79 in
#      "MC Logic"; the active personality is an on-device setting with no MIDI query, and
#      a Note On to the inactive set is silently ignored by the hardware, so every F1-row
#      position always sends to BOTH of its notes -- on and off alike.
one_sent.clear()
rd = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rd.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=0.0)   # settle: the row starts dark
one_sent.clear()
rd.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=1.0)   # fills the whole row, positions 0-5 all on
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_STANDARD[0]) == x.LED_ON
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_LOGIC[0]) == x.LED_ON
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_STANDARD[5]) == x.LED_ON
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_LOGIC[5]) == x.LED_ON
on_msgs_pos0 = [(kind, n, v) for (kind, n, v) in one_sent
                if kind == "note" and n in (x.ONE_F1_LINE_NOTES_STANDARD[0], x.ONE_F1_LINE_NOTES_LOGIC[0])]
assert all(v == x.LED_ON for (_, _, v) in on_msgs_pos0) and len(on_msgs_pos0) == 2, on_msgs_pos0
on_msgs_pos5 = [(kind, n, v) for (kind, n, v) in one_sent
                if kind == "note" and n in (x.ONE_F1_LINE_NOTES_STANDARD[5], x.ONE_F1_LINE_NOTES_LOGIC[5])]
assert all(v == x.LED_ON for (_, _, v) in on_msgs_pos5) and len(on_msgs_pos5) == 2, on_msgs_pos5

one_sent.clear()
# decay_per_frame is 1, so 6 ticks at 0.0 walk the 6-LED row all the way back down
for _ in range(8): rd.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=0.0)
assert rd.f1_line == 0
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_STANDARD[0]) == x.LED_OFF
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_LOGIC[0]) == x.LED_OFF
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_STANDARD[5]) == x.LED_OFF
assert rd.last_button.get(x.ONE_F1_LINE_NOTES_LOGIC[5]) == x.LED_OFF
off_msgs_pos0 = [(kind, n, v) for (kind, n, v) in one_sent
                 if kind == "note" and n in (x.ONE_F1_LINE_NOTES_STANDARD[0], x.ONE_F1_LINE_NOTES_LOGIC[0])]
assert all(v == x.LED_OFF for (_, _, v) in off_msgs_pos0) and len(off_msgs_pos0) == 2, off_msgs_pos0

# 76. Marker line shows band_rel_mid and Rewind line shows band_rel_low; the three rows
#     are independent of each other and of the ring, which still tracks `loudness`, not
#     the band values
one_sent.clear()
r6 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
r6.tick(0.03, [0]*8, 0.2, 1.0, band_rel_low=0.0, band_rel_mid=0.5, band_rel_high=0.0)
assert sum(1 for n in r6.marker_line_notes if r6.last_button.get(n) == x.LED_ON) == round(0.5 * 7)
assert sum(1 for n in r6.rewind_line_notes if r6.last_button.get(n) == x.LED_ON) == 0   # stays dark
assert sum(1 for pair in r6.f1_line_notes for n in pair if r6.last_button.get(n) == x.LED_ON) == 0   # unaffected
ring_msgs = [s for s in one_sent if s[0] == "cc" and s[1] == x.RING_CC_ONE]
assert ring_msgs[-1][2] - 32 == round(0.2 * x.RING_MAX), ring_msgs   # ring tracks loudness (0.2)

# 76b. peak indicator: BPM lights at once at/above ONE_PEAK_THRESHOLD and, once relative
#      loudness drops back down, stays lit until ONE_PEAK_HOLD_S has elapsed, then goes dark
one_sent.clear()
rp = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
def last_bpm():
    velocities = [v for (kind, n, v) in one_sent if kind == "note" and n == x.ONE_LED_NOTES["BPM"]]
    return velocities[-1] if velocities else None
def last_bpm_off():
    velocities = [v for (kind, n, v) in one_sent if kind == "note" and n == x.ONE_BPM_OFF_NOTE]
    return velocities[-1] if velocities else None

rp.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD + 0.05)   # a peak
assert rp.peak_on is True and last_bpm() == x.LED_ON

one_sent.clear()
rp.tick(0.03, [0] * 8, 0.0, 0.0)          # relative loudness drops at once; hold not elapsed (0.03s)
assert rp.peak_on is True
assert last_bpm() is None                 # unchanged -> nothing resent (dedup)

elapsed = 0.03
step = 0.05
saw_on_within_hold = False
while elapsed < x.ONE_PEAK_HOLD_S:
    one_sent.clear()
    rp.tick(step, [0] * 8, 0.0, 0.0)
    elapsed += step
    if rp.peak_on:
        saw_on_within_hold = True
assert saw_on_within_hold                 # stayed lit for at least one tick inside the hold window
# off exactly once the hold expires -- as velocity 127 to note 113, since 114 ignores
# velocity-0/Note-Off; nothing further is sent to note 114 at that point
assert rp.peak_on is False, elapsed
assert last_bpm_off() == x.LED_ON, (elapsed, one_sent)
assert last_bpm() is None, one_sent

# 76c. relative loudness that never reaches the threshold never lights BPM at all
one_sent.clear()
rp2 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
for _ in range(20):
    rp2.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD - 0.01)
assert rp2.peak_on is False
assert not any(kind == "note" and n == x.ONE_LED_NOTES["BPM"] and v == x.LED_ON
               for (kind, n, v) in one_sent)

# 76d. ONE_UNUSED_NAMES is empty (Channel Record/Solo/Mute now drive the channel-strip
#      row instead of sitting unused -- see test 99), so unused_notes is empty too, and
#      _clear_rows's loop over it is a harmless no-op, including on a repeated call
one_sent.clear()
ru = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
assert ru.unused_notes == [] and x.ONE_UNUSED_NAMES == []
ru.clear_output()
ru.clear_output()   # second call in a row: nothing left to resend either

# 76e. a row is driven as-is by whatever band_rel_* the caller passes -- OneRenderer
#      applies no gain of its own beyond fader_scale, which is 1.0 here (the per-band gain
#      now lives in SpectrumAnalyzer; see test 24d for "loudest sub-band, not the average"
#      at that level). Passing 0.9 through fills the row to 0.9, unmodified.
one_sent.clear()
rm = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rm.tick(0.03, [0]*8, 0.0, 0.0, band_rel_high=0.9)
lit_f1 = sum(1 for std, logic in rm.f1_line_notes
             if rm.last_button.get(std) == x.LED_ON and rm.last_button.get(logic) == x.LED_ON)
assert lit_f1 == round(0.9 * len(rm.f1_line_notes)) == 5, lit_f1

# 76f. the peak indicator reads the relative loudness, not the raw one: a raw loudness far
#      above the threshold with a low relative loudness leaves BPM dark (raw loudness
#      depends on min_db/max_db calibration and can sit high for minutes on end)
one_sent.clear()
rp3 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
for _ in range(5):
    rp3.tick(0.03, [0] * 8, 1.0, 0.1)
assert rp3.peak_on is False
assert ("note", x.ONE_LED_NOTES["BPM"], x.LED_ON) not in one_sent, one_sent

# 76g. and the other way round: a relative loudness above the threshold lights BPM even
#      while the raw loudness stays at zero
one_sent.clear()
rp4 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
def last_bpm_rel():
    velocities = [v for (kind, n, v) in one_sent if kind == "note" and n == x.ONE_LED_NOTES["BPM"]]
    return velocities[-1] if velocities else None

for _ in range(5):
    rp4.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD + 0.05)
assert rp4.peak_on is True and last_bpm_rel() == x.LED_ON

# 76h. switching the show off while BPM is lit takes it out with the rows and resets the
#      hold, so a later switch-on does not start out mid-peak
one_sent.clear()
rp5 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
for _ in range(3):
    rp5.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD + 0.05)
assert rp5.last_bpm_on is True

one_sent.clear()
rp5.on_midi([0x90, rp5.toggle_note, 127])
assert rp5.enabled is False
# cleared via note 113 velocity 127, not the broken velocity-0-to-114 path
assert ("note", x.ONE_BPM_OFF_NOTE, x.LED_ON) in one_sent, one_sent
assert ("note", x.ONE_LED_NOTES["BPM"], x.LED_OFF) not in one_sent, one_sent
assert rp5.peak_on is False and rp5.peak_hold_remaining == 0.0

# 76i. the peak-ON message goes to note 114 specifically, never to the off note (113)
one_sent.clear()
rp6 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rp6.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD + 0.05)
assert ("note", x.ONE_LED_NOTES["BPM"], x.LED_ON) in one_sent, one_sent
assert not any(kind == "note" and n == x.ONE_BPM_OFF_NOTE for (kind, n, v) in one_sent), one_sent

# 76j. regression guard: once the hold expires, the off message is velocity 127 to note 113
#      -- never a velocity-0 or Note-Off message to note 114, which the hardware ignores
one_sent.clear()
rp7 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rp7.tick(0.03, [0] * 8, 0.0, x.ONE_PEAK_THRESHOLD + 0.05)
one_sent.clear()
for _ in range(10):
    rp7.tick(0.05, [0] * 8, 0.0, 0.0)
    if rp7.peak_on is False:
        break
assert rp7.peak_on is False
assert ("note", x.ONE_BPM_OFF_NOTE, x.LED_ON) in one_sent, one_sent
assert not any(kind == "note" and n == x.ONE_LED_NOTES["BPM"] for (kind, n, v) in one_sent), one_sent

# 76k. dedup: once the off message has gone out, a later tick still wanting BPM off sends
#      nothing further
assert rp7.last_bpm_on is False
one_sent.clear()
rp7.tick(0.03, [0] * 8, 0.0, 0.0)
assert not any(kind == "note" and n == x.ONE_BPM_OFF_NOTE for (kind, n, v) in one_sent), one_sent

# 77. display encoding of 'LED ON' into CC 75..64 (position 1, leftmost, is CC 75)
one_sent.clear()
r7 = x.OneRenderer(cfg, dict(one_default, display_text="LED ON", display_scroll=False), one_cc, one_note, one_raw)
r7.tick(0.03, [0]*8, 0.0, 0.0)
expected_codes = {75: 12, 74: 5, 73: 4, 72: 32, 71: 15, 70: 14,
                  69: 32, 68: 32, 67: 32, 66: 32, 65: 32, 64: 32}
sent_codes = {c: v for (kind, c, v) in one_sent if kind == "cc" and 64 <= c <= 75}
assert sent_codes == expected_codes, sent_codes

# 78. marquee: the 12-character window slides right to left through `text + ONE_SCROLL_GAP`
#     and wraps round for ever, so even text far shorter than 12 characters keeps moving
one_sent.clear()
def one_window(r):
    """The 12 character codes currently on the display, left to right (CC 75 down to 64)."""
    return [r.last_display.get(x.DISPLAY_CC_TOP - i) for i in range(12)]

def one_codes(text): return [x._one_char_code(ch) for ch in text]

r8 = x.OneRenderer(cfg, dict(one_default, display_text="ABCDE", display_scroll=True,
                             display_scroll_step_s=0.3), one_cc, one_note, one_raw)
loop8 = "ABCDE" + x.ONE_SCROLL_GAP
assert len(loop8) == 8
windows8 = []
for _ in range(9):
    r8.tick(0.3, [0]*8, 0.0, 0.0)          # one scroll step per tick
    windows8.append(one_window(r8))
assert len({tuple(w) for w in windows8[:8]}) == 8, windows8   # never static: 8 distinct windows
assert windows8[0] == one_codes("BCDE   ABCDE"), windows8[0]  # offset 1
# 8 steps = one full cycle of loop8: offset back to 0, window back to where it started
assert r8.scroll_offset == 1
assert windows8[7] == one_codes("ABCDE   ABCD"), windows8[7]
assert windows8[8] == windows8[0]

# 78b. scrolling off: the window is left-aligned, padded to 12 characters and identical on
#      every tick -- unchanged by the marquee
one_sent.clear()
r8b = x.OneRenderer(cfg, dict(one_default, display_text="ABCDE", display_scroll=False,
                              display_scroll_step_s=0.3), one_cc, one_note, one_raw)
static8 = []
for _ in range(4):
    r8b.tick(0.3, [0]*8, 0.0, 0.0)
    static8.append(one_window(r8b))
assert static8[0] == one_codes("ABCDE       "), static8[0]
assert all(w == static8[0] for w in static8) and r8b.scroll_offset == 0

# 78c. empty text: the gap alone is what loops, so the display just stays blank -- no
#      modulo-by-zero
one_sent.clear()
r8c = x.OneRenderer(cfg, dict(one_default, display_scroll=True, display_scroll_step_s=0.3),
                    one_cc, one_note, one_raw)
r8c.display_text = ""
for _ in range(5):
    r8c.tick(0.3, [0]*8, 0.0, 0.0)
assert one_window(r8c) == one_codes(" " * 12)

# 78d. a full 12-character text scrolls too (it used to sit static, having nowhere to slide)
one_sent.clear()
r8d = x.OneRenderer(cfg, dict(one_default, display_text="ABCDEFGHIJKL", display_scroll=True,
                              display_scroll_step_s=0.3), one_cc, one_note, one_raw)
r8d.tick(0.3, [0]*8, 0.0, 0.0)
assert one_window(r8d) == one_codes("BCDEFGHIJKL "), one_window(r8d)
r8d.tick(0.3, [0]*8, 0.0, 0.0)
assert one_window(r8d) == one_codes("CDEFGHIJKL  "), one_window(r8d)

# 78e. text longer than the window is loaded whole, so its tail scrolls into view: after 6
#      steps the display holds characters 7-18, none of which ever fit in the first window
one_sent.clear()
r8e = x.OneRenderer(cfg, dict(one_default, display_text="ABCDEFGHIJKLMNOPQR", display_scroll=True,
                              display_scroll_step_s=0.3), one_cc, one_note, one_raw)
assert r8e.display_text == "ABCDEFGHIJKLMNOPQR", r8e.display_text
for _ in range(6):
    r8e.tick(0.3, [0]*8, 0.0, 0.0)
assert one_window(r8e) == one_codes("GHIJKLMNOPQR"), one_window(r8e)

# 79. software toggle-LED blink: flips every 0.5 s while ON, and only a real flip sends a
#     message; turning the show off forces it dark at once
one_sent.clear()
r9 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
def last_toggle_velocity():
    velocities = [v for (kind, n, v) in one_sent if kind == "note" and n == r9.toggle_note]
    return velocities[-1] if velocities else None

r9.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity() == x.LED_ON
r9.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity() == x.LED_OFF
r9.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity() == x.LED_ON
one_sent.clear()
r9.tick(0.25, [0]*8, 0.0, 0.0)
assert one_sent == []                     # under half a period: no flip, nothing resent
one_sent.clear()
r9.on_midi([0x90, r9.toggle_note, 127])
assert r9.enabled is False and last_toggle_velocity() == x.LED_OFF

# 79b. display-off suspension: the One's toggle LED goes solid on while ON+suspended,
#      leaving the blink state reset so blinking resumes cleanly once ticking resumes
one_sent.clear()
r10 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
def last_toggle_velocity_r10():
    velocities = [v for (kind, n, v) in one_sent if kind == "note" and n == r10.toggle_note]
    return velocities[-1] if velocities else None

# (a) ON, not suspended: blinks per the usual timing
r10.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity_r10() == x.LED_ON
r10.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity_r10() == x.LED_OFF

# (b) ON, suspended: clear_output(suspending=True) forces the LED solidly on and resets
#     the blink state, without touching the ON/OFF flag; no tick() runs while suspended,
#     so nothing more is sent beyond this single solid-on message
one_sent.clear()
r10.clear_output(suspending=True)
assert r10.enabled is True
assert last_toggle_velocity_r10() == x.LED_ON
toggle_msgs = [s for s in one_sent if s[0] == "note" and s[1] == r10.toggle_note]
assert len(toggle_msgs) == 1 and toggle_msgs[0][2] == x.LED_ON
assert r10.blink_on is False and r10.blink_accum == 0.0

# (c) suspension ends: the main loop makes no renderer call on resume, tick() simply runs
#     again; blinking resumes from the freshly-reset state, reflecting LED_OFF at once
#     (even before a full period elapses), then continuing to blink normally
r10.tick(0.05, [0]*8, 0.0, 0.0)           # sub-period dt: no flip, just the reset state
assert last_toggle_velocity_r10() == x.LED_OFF
r10.tick(0.45, [0]*8, 0.0, 0.0)           # completes the first 0.5 s period: flips on
assert last_toggle_velocity_r10() == x.LED_ON
r10.tick(0.5, [0]*8, 0.0, 0.0); assert last_toggle_velocity_r10() == x.LED_OFF

# (d) OFF (toggled off by hand, not suspended): _toggle()/_clear_all() forces the LED off
#     (checked against the renderer's own record of the last LED state sent, since a prior
#     tick may already have left it off, in which case the forced-off send is deduplicated)
one_sent.clear()
r10.on_midi([0x90, r10.toggle_note, 127])
assert r10.enabled is False and r10.last_toggle_led == x.LED_OFF

# ---------------------------------------------------------------------------
# X-Touch One: DawProxy classification (note on/off, CC 48, CC 64-75 are LED-type)
# ---------------------------------------------------------------------------

# 80. LED-type messages are cached and held while rendering, restored when it stops;
#     everything else (the motor fader, SysEx, the jog wheel's CC 60) always passes through
one_to_device = []
one_ranges = [(x.RING_CC_ONE, x.RING_CC_ONE + 1), (x.DISPLAY_CC_BASE, x.DISPLAY_CC_TOP + 1)]
p5 = x.DawProxy("one proxy", one_to_device.append, 101, led_cc_ranges=one_ranges)
p5.from_daw([0x90, 96, 127])            # Up LED on
p5.from_daw([0xB0, 48, 32 + 5])         # ring position 5
p5.from_daw([0xB0, 70, 14])             # display CC 70 = 'N'
assert one_to_device == [[0x90, 96, 127], [0xB0, 48, 37], [0xB0, 70, 14]], one_to_device
assert p5.notes == {96: 127} and p5.rings == {48: 37, 70: 14}, (p5.notes, p5.rings)

one_to_device.clear(); p5.set_rendering(True)
p5.from_daw([0x90, 96, 0]); p5.from_daw([0xB0, 64, 32])
assert one_to_device == [], one_to_device
assert p5.notes == {96: 0} and p5.rings == {48: 37, 70: 14, 64: 32}, (p5.notes, p5.rings)

for state in (True, False):
    p5.set_rendering(state); one_to_device.clear()
    passed = [[0xE8, 0, 100], list(SYSEX), [0xB0, 60, 1]]   # fader ch9, SysEx, jog wheel CC 60
    for msg in passed:
        p5.from_daw(list(msg))
    assert one_to_device == passed, (state, one_to_device)

one_to_device.clear()
assert p5.restore() is True
assert one_to_device == [[0x90, 96, 0], [0xB0, 48, 37], [0xB0, 70, 14], [0xB0, 64, 32]], one_to_device

# 81. a multi-note toggle (Channel Left/Right's two press notes) is consumed from the
#     device-ward path regardless of which of the two notes arrives
p6 = x.DawProxy("one proxy 2", one_to_device.append, (48, 31))
assert p6._is_toggle([0x90, 48, 127]) and p6._is_toggle([0x90, 31, 127])
assert not p6._is_toggle([0x90, 104, 127])

# ---------------------------------------------------------------------------
# two devices sharing one ShowState: toggling on either switches both
# ---------------------------------------------------------------------------

# 82. MiniRenderer and OneRenderer given the same ShowState reflect one shared ON/OFF flag
one_sent.clear(); sent.clear()
shared_state = x.ShowState(True)
sm = x.MiniRenderer(cfg, cc, note, state=shared_state)
so = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=shared_state)
assert sm.enabled is True and so.enabled is True
sm.on_midi([0x90, sm.toggle_note, 127])         # toggle on the Mini
assert sm.enabled is False and so.enabled is False
so.on_midi([0x90, so.toggle_note, 127])         # toggle on the One
assert sm.enabled is True and so.enabled is True

# 83. switching off on the Mini clears the One straight away: the One's tick() returns early
#     once the shared flag is off, so without the cross-clear its hardware would stay frozen
#     at the last frame it drew
one_sent.clear(); sent.clear()
state83 = x.ShowState(True)
sm83 = x.MiniRenderer(cfg, cc, note, state=state83)
so83 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state83)
so83.on_connected()
for _ in range(3): so83.tick(0.5, [1.0]*8, 1.0, 1.0, 1.0, 1.0, 1.0)   # odd number of 0.5 s blinks: LED ends lit
assert so83.f1_line > 0 and so83.marker_line > 0 and so83.rewind_line > 0 and so83.ring_current > 0, \
    (so83.f1_line, so83.marker_line, so83.rewind_line, so83.ring_current)   # sanity: really rendering
assert so83.last_toggle_led == x.LED_ON
display_before = dict(so83.last_display)
lit_positions = [c for c, code in display_before.items() if code != 0x20]
assert lit_positions                                     # sanity: the display shows text

one_sent.clear(); sent.clear()
sm83.on_midi([0x90, sm83.toggle_note, 127])              # pressed on the Mini only
assert so83.enabled is False and sm83.enabled is False
assert so83.f1_line == 0 and so83.marker_line == 0 and so83.rewind_line == 0 and so83.ring_current == 0
assert ("cc", x.RING_CC_ONE, x.RING_FAN) in one_sent
off_notes = [n for (kind, n, v) in one_sent if kind == "note" and v == x.LED_OFF]
f1_flat = [n for pair in so83.f1_line_notes for n in pair]
assert all(n in off_notes for n in f1_flat + so83.marker_line_notes + so83.rewind_line_notes), off_notes
blanked = [c for (kind, c, v) in one_sent if kind == "cc" and v == 0x20 and 64 <= c <= 75]
assert all(c in blanked for c in lit_positions), (blanked, lit_positions)
assert ("note", so83.toggle_note, x.LED_OFF) in one_sent
assert so83.last_toggle_led == x.LED_OFF
assert ("note", sm83.toggle_note, x.LED_OFF) in sent     # the caller still clears itself

# 84. and the other way round: switching off on the One clears the Mini
one_sent.clear(); sent.clear()
state84 = x.ShowState(True)
sm84 = x.MiniRenderer(cfg, cc, note, state=state84)
so84 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state84)
sm84.on_connected()
for _ in range(12): sm84.tick(0.03, lv, 1.0, 1.0)
assert sm84.current[0] > 0 and sm84.bar_top > 0 and sm84.bar_bottom > 0   # sanity
assert sm84.last_led == x.LED_BLINK

one_sent.clear(); sent.clear()
so84.on_midi([0x90, so84.toggle_note, 127])              # pressed on the One only
assert sm84.enabled is False and so84.enabled is False
assert sm84.current == [0]*8 and sm84.bar_top == 0 and sm84.bar_bottom == 0
assert len([s for s in rings() if s[2] == x.RING_FAN]) == 8
assert sorted(btn_sent(x.BUTTON_NOTES, x.LED_OFF)) == sorted(x.BUTTON_NOTES)
assert ("note", sm84.toggle_note, x.LED_OFF) in sent     # forced off by full_clear()
assert sm84.last_led == x.LED_OFF

# 85. switching ON reaches the other device's toggle LED and nothing else: the full clear
#     runs only on a True -> False flip, so an ON flip leaves the rest of the other device's
#     frame to its next tick()
one_sent.clear(); sent.clear()
state85 = x.ShowState(False)
sm85 = x.MiniRenderer(cfg, cc, note, state=state85)
so85 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state85)
sm85.on_midi([0x90, sm85.toggle_note, 127])              # switched on from the Mini
assert sm85.enabled is True and so85.enabled is True
assert one_sent == [("note", so85.toggle_note, x.LED_ON)]   # only the One's toggle LED
assert so85.last_toggle_led == x.LED_ON

one_sent.clear(); sent.clear()
state85b = x.ShowState(False)
sm85b = x.MiniRenderer(cfg, cc, note, state=state85b)
so85b = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state85b)
so85b.on_midi([0x90, so85b.toggle_note, 127])            # switched on from the One
assert sm85b.enabled is True and so85b.enabled is True
assert sent == [("note", sm85b.toggle_note, x.LED_BLINK)]   # only the Mini's toggle LED

# 86. per-device suspension stays per-device: the main loop suspends one device by calling
#     clear_output(suspending=True) on it without touching the shared flag, so the other
#     device keeps its rendered state and receives nothing
one_sent.clear(); sent.clear()
state86 = x.ShowState(True)
sm86 = x.MiniRenderer(cfg, cc, note, state=state86)
so86 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state86)
sm86.on_connected(); so86.on_connected()
for _ in range(12): sm86.tick(0.03, lv, 1.0, 1.0)
for _ in range(3): so86.tick(0.5, [0]*8, 1.0, 1.0)
mini_before = (list(sm86.current), sm86.bar_top, sm86.bar_bottom, list(sm86.last_button), sm86.last_led)

sent.clear()
so86.clear_output(suspending=True)                       # suspension only, no toggle
assert sent == []                                        # nothing crossed over to the Mini
assert (list(sm86.current), sm86.bar_top, sm86.bar_bottom,
        list(sm86.last_button), sm86.last_led) == mini_before
assert sm86.enabled is True and so86.enabled is True     # the shared flag is untouched

# 87. switching ON from the One puts the Mini's toggle LED on from the press alone, with no
#     tick() of the Mini's in between, and a following tick() resends nothing
one_sent.clear(); sent.clear()
state87 = x.ShowState(False)
sm87 = x.MiniRenderer(cfg, cc, note, state=state87)
so87 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state87)
sm87.on_connected()
assert sm87.last_led == x.LED_OFF
sent.clear()
so87.on_midi([0x90, so87.toggle_note, 127])              # pressed on the One only
assert sm87.enabled is True
assert sm87.last_led == x.LED_BLINK
assert ("note", sm87.toggle_note, x.LED_BLINK) in sent
sent.clear()
sm87.tick(0.03, lv, 1.0, 1.0)
assert ("note", sm87.toggle_note, x.LED_BLINK) not in sent   # already in line, not resent

# 88. the same call site puts the LED out again, and the tick still renders nothing while off
sent.clear()
state87.enabled = False
sm87.tick(0.03, lv, 1.0, 1.0)
assert sm87.last_led == x.LED_OFF and ("note", sm87.toggle_note, x.LED_OFF) in sent
assert rings() == []
sent.clear(); sm87.tick(0.03, lv, 1.0, 1.0)
assert sent == []                                        # and it is not resent every frame

# ---------------------------------------------------------------------------
# the main loop idles while the show is off
# ---------------------------------------------------------------------------

# 89. every toggle wakes the main loop, in both directions, so a long idle wait costs the
#     switch-on no latency
state89 = x.ShowState(False)
assert not state89.wake_event.is_set()
state89.toggle(); assert state89.wake_event.is_set()
state89.wake_event.clear()
state89.toggle(); assert state89.wake_event.is_set()

# 90. one iteration lasts a frame while rendering and the idle interval while switched off
assert x.loop_wait_seconds(True, 1/30.0, 2.0) == 1/30.0
assert x.loop_wait_seconds(False, 1/30.0, 2.0) == 2.0
assert x.loop_wait_seconds(False, 1/30.0) == x.IDLE_LOOP_SECONDS
assert x.IDLE_LOOP_SECONDS < x.WATCHDOG_SECONDS          # an idling loop must not look stalled

# ---------------------------------------------------------------------------
# X-Touch One: Channel Record/Solo/Mute/Select rename, the nav-tier bar, the level meter
# ---------------------------------------------------------------------------

# 91. the mislabeled "Fader Bank Left/Right" pair is gone, replaced by the real channel-strip
#     row (Record/Solo/Mute/Select); the two OTHER, unrelated buttons that already happened
#     to be named "Solo"/"Record" (part of the Marker-line/Rewind-line groups) are untouched
assert x.ONE_LED_NOTES["Channel Record"] == 0
assert x.ONE_LED_NOTES["Channel Solo"] == 8
assert x.ONE_LED_NOTES["Channel Mute"] == 16
assert x.ONE_LED_NOTES["Channel Select"] == 24
assert "Fader Bank Left" not in x.ONE_LED_NOTES and "Fader Bank Right" not in x.ONE_LED_NOTES
assert x.ONE_LED_NOTES["Solo"] == 90 and x.ONE_LED_NOTES["Record"] == 95
# Channel Record/Solo/Mute now drive the channel-strip row (test 99 below) instead of
# staying unused/dark; Channel Select does not either (it gates the meter, see test 96)
# and neither do the 9 nav-cluster buttons (test 92 below) -- ONE_UNUSED_NAMES is empty
assert x.ONE_UNUSED_NAMES == []
for used_name in ("Channel Record", "Channel Solo", "Channel Mute", "Channel Select",
                   "Bank Left", "Bank Right", "Channel Left", "Channel Right",
                   "Up", "Down", "Left", "Right", "Zoom"):
    assert used_name not in x.ONE_UNUSED_NAMES, used_name

# 92. the nav-tier bar fills its 5 tiers bottom to top as loudness_rel rises, one tick per
#     step (a rise is immediate, same as every other row/bar in this file); every button in
#     a tier always changes together, never independently
one_sent.clear()
nav_tier_notes = [[x.ONE_LED_NOTES[n] for n in tier] for tier in x.ONE_NAV_TIERS]
rn = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
assert rn.nav_tiers == nav_tier_notes                     # toggle = Scrub, in no tier
level_counts = [(0.0, 0), (0.2, 1), (0.4, 2), (0.6, 3), (0.8, 4), (1.0, 5)]
prev_count = 0
nav_notes_flat = [n for tier in nav_tier_notes for n in tier]
for rel, count in level_counts:
    one_sent.clear()
    rn.tick(0.03, [0] * 8, 0.0, rel)
    assert rn.nav_bar == count, (rel, rn.nav_bar)
    lit_this_tick = {n for (kind, n, v) in one_sent
                     if kind == "note" and v == x.LED_ON and n in nav_notes_flat}
    if count > prev_count:
        # exactly the newly-lit tier's buttons appear together in this tick, nothing else
        assert lit_this_tick == set(nav_tier_notes[prev_count]), (rel, lit_this_tick)
    prev_count = count
    for i, notes in enumerate(nav_tier_notes):
        expected = x.LED_ON if i < count else x.LED_OFF
        for note in notes:
            assert rn.last_button.get(note) == expected, (rel, i, note)

# 93. clearing the show clears all 9 nav-cluster notes, and resets the bar to 0
one_sent.clear()
rn.clear_output()
off_sent = {n for (kind, n, v) in one_sent if kind == "note" and v == x.LED_OFF and n in nav_notes_flat}
assert off_sent == set(nav_notes_flat), off_sent
assert rn.nav_bar == 0

# 94. toggling the show off (not just a suspend) clears the nav-tier bar the same way
one_sent.clear()
rn2 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rn2.tick(0.03, [0] * 8, 0.0, 1.0)
assert rn2.nav_bar == 5
one_sent.clear()
rn2.on_midi([0x90, rn2.toggle_note, 127])                  # toggles off
assert rn2.enabled is False and rn2.nav_bar == 0
off_sent2 = {n for (kind, n, v) in one_sent if kind == "note" and v == x.LED_OFF and n in nav_notes_flat}
assert off_sent2 == set(nav_notes_flat), off_sent2

# 95. on_connected() turns Channel Select on once -- the real level meter does not respond
#     to anything until this has been sent (confirmed on hardware; see ONE_METER_STATUS)
one_sent.clear()
rsel = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rsel.on_connected()
assert ("note", x.ONE_LED_NOTES["Channel Select"], x.LED_ON) in one_sent, one_sent

# 96. the level meter maps loudness_rel (0.0-1.0) onto a 0-15 Channel Pressure value and
#     sends it as a 2-byte raw message, [0xD0 | MIDI_CH, level] -- not through send_cc/send_note
one_sent.clear()
rme = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
def last_meter():
    raws = [(a, b) for (kind, a, b) in one_sent if kind == "raw"]
    return raws[-1] if raws else None

rme.tick(0.03, [0] * 8, 0.0, 0.0)
assert last_meter() == (x.ONE_METER_STATUS | x.MIDI_CH, 0), one_sent

one_sent.clear()
rme.tick(0.03, [0] * 8, 0.0, 1.0)
assert last_meter() == (x.ONE_METER_STATUS | x.MIDI_CH, x.ONE_METER_MAX) == (x.ONE_METER_STATUS | x.MIDI_CH, 15)

one_sent.clear()
rme.tick(0.03, [0] * 8, 0.0, 0.4)                           # a mid value: round(0.4 * 15) == 6
assert last_meter() == (x.ONE_METER_STATUS | x.MIDI_CH, 6), one_sent

# 97. dedup: an unchanged level after a second tick sends nothing further
one_sent.clear()
rme.tick(0.03, [0] * 8, 0.0, 0.4)
assert not any(kind == "raw" for (kind, a, b) in one_sent), one_sent

# 98. the meter clears (level 0 sent) wherever the rest of the One's outputs are cleared:
#     a plain clear_output() call, and a toggle-off (through _clear_all)
one_sent.clear()
rmc = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rmc.tick(0.03, [0] * 8, 0.0, 0.8)                           # level 12, non-zero
assert rmc.last_meter_level == 12
one_sent.clear()
rmc.clear_output()
assert (x.ONE_METER_STATUS | x.MIDI_CH, 0) in [(a, b) for (kind, a, b) in one_sent if kind == "raw"]
assert rmc.last_meter_level == 0

rmc.tick(0.03, [0] * 8, 0.0, 0.8)                           # relit
one_sent.clear()
rmc.on_midi([0x90, rmc.toggle_note, 127])                   # toggle off -> _clear_all -> _clear_meter
assert rmc.last_meter_level == 0
assert (x.ONE_METER_STATUS | x.MIDI_CH, 0) in [(a, b) for (kind, a, b) in one_sent if kind == "raw"]

# ---------------------------------------------------------------------------
# X-Touch One: the channel-strip row (Channel Mute / Channel Solo / Channel Record)
# ---------------------------------------------------------------------------

# 99. the channel-strip row fills one LED per step, in physical left-to-right order
#     (Mute, then Solo, then Record), as loudness_rel rises -- driven by overall relative
#     loudness, the same input as the nav-tier bar (test 92) and the meter (test 96), and
#     reusing _step_bar exactly like the F1/Marker/Rewind rows above; the three band
#     values are irrelevant to it
one_sent.clear()
rcs = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)   # toggle = Scrub, in no row
assert rcs.channel_strip_line_notes == [x.ONE_LED_NOTES["Channel Mute"],
                                         x.ONE_LED_NOTES["Channel Solo"],
                                         x.ONE_LED_NOTES["Channel Record"]]
level_counts99 = [(0.0, 0), (0.34, 1), (0.67, 2), (1.0, 3)]
prev99 = 0
for rel, count in level_counts99:
    one_sent.clear()
    rcs.tick(0.03, [0] * 8, 0.0, rel, band_rel_low=0.0, band_rel_mid=0.0, band_rel_high=0.0)
    assert rcs.channel_strip_line == count, (rel, rcs.channel_strip_line)
    if count > prev99:
        # the one newly-lit LED this tick is the next one in fill order, and nothing else
        newly_lit = rcs.channel_strip_line_notes[prev99]
        assert ("note", newly_lit, x.LED_ON) in one_sent, one_sent
    prev99 = count
    for i, note in enumerate(rcs.channel_strip_line_notes):
        expected = x.LED_ON if i < count else x.LED_OFF
        assert rcs.last_button.get(note) == expected, (rel, i, note)

# maxing the three band values must not move this row: it only follows loudness_rel
one_sent.clear()
rcs2 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)   # fresh: no decay carried over
rcs2.tick(0.03, [0] * 8, 0.0, 0.0, band_rel_low=1.0, band_rel_mid=1.0, band_rel_high=1.0)
assert rcs2.channel_strip_line == 0
assert all(rcs2.last_button.get(n) == x.LED_OFF for n in rcs2.channel_strip_line_notes)

# 100. the channel-strip row clears fully (all 3 notes LED_OFF, counter back to 0) on a
#      plain clear_output() and on toggling the show off, matching every other row
one_sent.clear()
rcc = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rcc.tick(0.03, [0] * 8, 0.0, 1.0)
assert rcc.channel_strip_line == 3
assert all(rcc.last_button.get(n) == x.LED_ON for n in rcc.channel_strip_line_notes)

one_sent.clear()
rcc.clear_output()
assert rcc.channel_strip_line == 0
assert all(rcc.last_button.get(n) == x.LED_OFF for n in rcc.channel_strip_line_notes)
off_sent99 = {n for (kind, n, v) in one_sent if kind == "note" and v == x.LED_OFF}
assert set(rcc.channel_strip_line_notes) <= off_sent99, off_sent99

rcc.tick(0.03, [0] * 8, 0.0, 1.0)                           # relit
assert rcc.channel_strip_line == 3
one_sent.clear()
rcc.on_midi([0x90, rcc.toggle_note, 127])                   # toggle off -> _clear_all -> _clear_rows
assert rcc.channel_strip_line == 0
assert all(rcc.last_button.get(n) == x.LED_OFF for n in rcc.channel_strip_line_notes)

# ---------------------------------------------------------------------------
# two devices, suspended: the toggle LEDs stay in sync without any tick()
# ---------------------------------------------------------------------------

# 101. while the show is suspended (the display is asleep) the main loop calls no tick() at
#      all, so every toggle LED has to be correct from the button press alone -- on both
#      devices and in both directions. No tick() runs anywhere in this block after the
#      suspension is entered.
# the module-level `cc`/`note` sinks are shadowed by loop variables in the blocks above
def mini_cc(c, v): sent.append(("cc", c, v))
def mini_note(n, v): sent.append(("note", n, v))

def _suspended_pair():
    """A connected, rendering Mini+One pair on one flag, put into display-off suspension."""
    state = x.ShowState(True)
    mini = x.MiniRenderer(cfg, mini_cc, mini_note, state=state)
    one = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw, state=state)
    mini.on_connected(); one.on_connected()
    for _ in range(3):
        mini.tick(0.03, [1.0]*8, 1.0, 1.0)
        one.tick(0.5, [1.0]*8, 1.0, 1.0, 1.0, 1.0, 1.0)
    mini.clear_output(suspending=True); one.clear_output(suspending=True)
    # suspension entry: the Mini's LED is left blinking in hardware, the One's forced solid
    assert mini.last_led == x.LED_BLINK and one.last_toggle_led == x.LED_ON
    return mini, one

def _toggle_notes(msgs, note_number):
    return [v for (kind, n, v) in msgs if kind == "note" and n == note_number]

# (a) pressed on the One: OFF then ON again, both devices correct after each press
sm101, so101 = _suspended_pair()
sent.clear(); one_sent.clear()
so101.on_midi([0x90, so101.toggle_note, 127])                    # ON -> OFF
assert sm101.enabled is False and so101.enabled is False
assert sm101.last_led == x.LED_OFF and _toggle_notes(sent, sm101.toggle_note) == [x.LED_OFF]
assert so101.last_toggle_led == x.LED_OFF and _toggle_notes(one_sent, so101.toggle_note) == [x.LED_OFF]

sent.clear(); one_sent.clear()
so101.on_midi([0x90, so101.toggle_note, 127])                    # OFF -> ON
assert sm101.enabled is True and so101.enabled is True
assert sm101.last_led == x.LED_BLINK and _toggle_notes(sent, sm101.toggle_note) == [x.LED_BLINK]
assert so101.last_toggle_led == x.LED_ON and _toggle_notes(one_sent, so101.toggle_note) == [x.LED_ON]

# (b) pressed on the Mini: the same, in both directions
sm101b, so101b = _suspended_pair()
sent.clear(); one_sent.clear()
sm101b.on_midi([0x90, sm101b.toggle_note, 127])                  # ON -> OFF
assert sm101b.enabled is False and so101b.enabled is False
assert sm101b.last_led == x.LED_OFF and _toggle_notes(sent, sm101b.toggle_note) == [x.LED_OFF]
assert so101b.last_toggle_led == x.LED_OFF and _toggle_notes(one_sent, so101b.toggle_note) == [x.LED_OFF]

sent.clear(); one_sent.clear()
sm101b.on_midi([0x90, sm101b.toggle_note, 127])                  # OFF -> ON
assert sm101b.enabled is True and so101b.enabled is True
assert sm101b.last_led == x.LED_BLINK and _toggle_notes(sent, sm101b.toggle_note) == [x.LED_BLINK]
assert so101b.last_toggle_led == x.LED_ON and _toggle_notes(one_sent, so101b.toggle_note) == [x.LED_ON]

# 102. an ON pressed while suspended does not fight the main loop's suspension entry: the
#      loop clears `suspended` when the flag goes off and so re-enters suspension on the ON,
#      calling clear_output(suspending=True) again -- which must find both LEDs already in
#      their suspended-ON state and send nothing further
sent.clear(); one_sent.clear()
sm101.clear_output(suspending=True); so101.clear_output(suspending=True)
assert _toggle_notes(sent, sm101.toggle_note) == []              # still blinking in hardware
assert _toggle_notes(one_sent, so101.toggle_note) == []          # still solid
assert sm101.last_led == x.LED_BLINK and so101.last_toggle_led == x.LED_ON

# 103. the One's blink resumes cleanly from lit once ticking starts again after an ON that
#      arrived while suspended, rather than flicking off for a frame first: _set_toggle_led
#      restarts the blink from the ON phase (so101b was switched on but never re-suspended,
#      unlike so101 above -- clear_output(suspending=True) deliberately resets to the OFF
#      phase instead, see test 79b(c))
one_sent.clear()
so101b.tick(0.05, [0]*8, 0.0, 0.0)                               # sub-period dt: no flip yet
assert so101b.last_toggle_led == x.LED_ON
so101b.tick(0.45, [0]*8, 0.0, 0.0)                               # first full 0.5 s period
assert so101b.last_toggle_led == x.LED_OFF

# ---------------------------------------------------------------------------
# the Mini's Layer LEDs on connect
# ---------------------------------------------------------------------------

# 104. connect clears BOTH Layer LEDs before lighting the configured one. The Mini blinks a
#      Layer LED in hardware once told to, so one left blinking by an earlier run configured
#      with the other `toggle_button` keeps blinking beside the real indicator unless this
#      process turns it off explicitly -- and it never addresses that note anywhere else.
def _layer_notes(msgs):
    return [(n, v) for (kind, n, v) in msgs if kind == "note" and n in (84, 85)]

cfg104b = dict(cfg); cfg104b["toggle_button"] = "B"
sent.clear()
sm104b = x.MiniRenderer(cfg104b, mini_cc, mini_note, state=x.ShowState(True))
sm104b.on_connected()
assert _layer_notes(sent) == [(84, x.LED_OFF), (85, x.LED_OFF), (85, x.LED_BLINK)], _layer_notes(sent)

cfg104a = dict(cfg); cfg104a["toggle_button"] = "A"
sent.clear()
sm104a = x.MiniRenderer(cfg104a, mini_cc, mini_note, state=x.ShowState(True))
sm104a.on_connected()
assert _layer_notes(sent) == [(84, x.LED_OFF), (85, x.LED_OFF), (84, x.LED_BLINK)], _layer_notes(sent)

# a hot-plug reconnect repeats exactly that and nothing more
sent.clear()
sm104a.on_connected()
assert _layer_notes(sent) == [(84, x.LED_OFF), (85, x.LED_OFF), (84, x.LED_BLINK)], _layer_notes(sent)

# connecting while off leaves both dark with no redundant third message
sent.clear()
sm104off = x.MiniRenderer(cfg104a, mini_cc, mini_note, state=x.ShowState(False))
sm104off.on_connected()
assert _layer_notes(sent) == [(84, x.LED_OFF), (85, x.LED_OFF)], _layer_notes(sent)
assert sm104off.last_led == x.LED_OFF

# ---------------------------------------------------------------------------
# X-Touch One: the jog wheel as the sensitivity control (what the fader is on the Mini)
# ---------------------------------------------------------------------------

# 105. CC 60 is a relative encoder, not a position: value 0x41 (65) is one detent clockwise
#      and 0x01 (1) one detent counter-clockwise, each moving fader_scale by
#      ONE_SENSITIVITY_STEP, and both ends clamp instead of running past 1.0 / 0.0
one_sent.clear()
rj = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
assert rj.fader_scale == 1.0
rj.on_midi([0xB0, 60, 65])
assert abs(rj.fader_scale - (1.0 - x.ONE_SENSITIVITY_STEP)) < 1e-9
rj.on_midi([0xB0, 60, 1])
assert abs(rj.fader_scale - 1.0) < 1e-9
for _ in range(5): rj.on_midi([0xB0, 60, 1])       # already at the top: it stays there
assert rj.fader_scale == 1.0
for _ in range(60): rj.on_midi([0xB0, 60, 65])     # a full sweep down and well past it
assert rj.fader_scale == 0.0
rj.on_midi([0xB0, 60, 1])                          # and back up one detent from the floor
assert abs(rj.fader_scale - x.ONE_SENSITIVITY_STEP) < 1e-9

# 106. the wheel scales what is rendered, at the same point in the pipeline the Mini's fader
#      scales at: 10 detents down and the ring, fed an unchanged loudness, follows it down
one_sent.clear()
rj2 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rj2.tick(0.03, [0] * 8, 1.0, 0.0)
assert [s for s in one_sent if s[0] == "cc" and s[1] == x.RING_CC_ONE][-1][2] - 32 == x.RING_MAX
for _ in range(10): rj2.on_midi([0xB0, 60, 65])
scale106 = 1.0 - 10 * x.ONE_SENSITIVITY_STEP
assert abs(rj2.fader_scale - scale106) < 1e-9
one_sent.clear()
for _ in range(x.RING_MAX): rj2.tick(0.03, [0] * 8, 1.0, 0.0)   # decay is 1/frame: let it settle
ring106 = [s for s in one_sent if s[0] == "cc" and s[1] == x.RING_CC_ONE][-1][2] - 32
assert ring106 == round(scale106 * x.RING_MAX), ring106

# 107. fader_scale multiplies the level before it becomes an LED count or a meter value, so
#      halving it halves every level-driven part alike: a band row, the nav-tier bar, the
#      encoder ring and the hardware level meter
one_sent.clear()
rj3 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rj3.tick(0.03, [0] * 8, 1.0, 1.0, band_rel_high=1.0)
assert (rj3.f1_line, rj3.nav_bar) == (len(rj3.f1_line_notes), len(rj3.nav_tiers))
assert rj3.ring_current == x.RING_MAX and rj3.last_meter_level == x.ONE_METER_MAX

rj4 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rj4.fader_scale = 0.5
rj4.tick(0.03, [0] * 8, 1.0, 1.0, band_rel_high=1.0)
assert rj4.f1_line == round(0.5 * len(rj4.f1_line_notes)) < rj3.f1_line
assert rj4.nav_bar == round(0.5 * len(rj4.nav_tiers)) < rj3.nav_bar
assert rj4.ring_current == round(0.5 * x.RING_MAX) < rj3.ring_current
assert rj4.last_meter_level == round(0.5 * x.ONE_METER_MAX) < rj3.last_meter_level

# 107b. the peak indicator reads the same scaled loudness: at half sensitivity a relative
#       loudness that lit BPM at full sensitivity no longer reaches the threshold
one_sent.clear()
rj5 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rj5.tick(0.03, [0] * 8, 0.0, 1.0)
assert rj5.peak_on is True
rj5.fader_scale = 0.5
for _ in range(20): rj5.tick(0.05, [0] * 8, 0.0, 1.0)
assert rj5.peak_on is False

# 108. sensitivity is full on construction and again on every reconnect: a relative control
#      leaves no position to read back, so a hot-plug cannot restore what it was set to
one_sent.clear()
rj6 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
assert rj6.fader_scale == 1.0
for _ in range(12): rj6.on_midi([0xB0, 60, 65])
assert rj6.fader_scale < 1.0
rj6.on_connected()
assert rj6.fader_scale == 1.0

# 109. everything else is ignored: a CC 60 value the wheel never sends, CC 60 on another
#      channel and another CC on this one all leave the sensitivity and the show untouched
rj7 = x.OneRenderer(cfg, one_default, one_cc, one_note, one_raw)
rj7.on_midi([0xB0, 60, 1])
scale109 = rj7.fader_scale
one_sent.clear()
for msg in ([0xB0, 60, 64], [0xB0, 60, 0], [0xB0, 60, 127],
            [0xB1, 60, 65], [0xB2, 60, 1],            # CC 60 on other channels
            [0xB0, 61, 65], [0xB0, 16, 1]):           # other CCs on this channel
    rj7.on_midi(msg)
assert rj7.fader_scale == scale109
assert one_sent == [] and rj7.enabled is True

print("ALL TESTS PASSED")
