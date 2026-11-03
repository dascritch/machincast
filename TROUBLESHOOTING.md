# Troubleshooting

*[Version française](TROUBLESHOOTING.fr.md)*

The known failures of MachinCast, their causes, what to check, and the scenarios that watch for them. The log messages are read with `Machin logs` (playout), or in the **Incidents** tab of the interface. MachinCast's messages are in French for now: they are quoted here as they appear, followed by their meaning.

## A stream drops, but the station stays on dead air

**Symptom**: a stream drops, for instance when the network is cut. The station stays on dead air, without falling back to the fallback event or to the music feed, and the log records no `flux tombé` (stream dropped). When the network comes back, the stream does not resume: playout has to be restarted.

**Cause** ([#278](https://github.com/dascritch/machincast/issues/278)): the stream is served over **HTTP/2**, often behind an nginx server, like France Inter's. Over HTTP/2, libsoup 3, the library through which GStreamer reads streams, does not report that a connection no longer delivers anything ([libsoup issue 256](https://gitlab.gnome.org/GNOME/libsoup/-/issues/256), [libsoup issue 367](https://gitlab.gnome.org/GNOME/libsoup/-/issues/367), [libsoup issue 296](https://gitlab.gnome.org/GNOME/libsoup/-/issues/296)): the player waits forever, without an error. A stream served over HTTP/1.1, such as a direct Icecast, is not affected. The stream type (MP3, AAC) plays no part. Another player built on GStreamer worked around the same defect in the same way ([sone issue 252](https://github.com/lullabyX/sone/issues/252)).

**What MachinCast does**:

- It reads all its streams over HTTP/1.1: the `SOUP_FORCE_HTTP1` variable is set when each of its programs starts. The 10-second connection timeout then applies, and the player reports the dropped stream.
- It also considers dropped a stream whose playback no longer moves for **10 seconds**, the same watchdog delay as for stalled playback and for the connection of an HTTP/1.1 stream, even if the player reports nothing. The log then records `flux tombé`: « plus de son depuis 10 secondes, sans erreur du lecteur » (no sound for 10 seconds, without a player error).
- Reconnection resumes the stream as soon as sound comes back.

**To check**:

- A stream's HTTP version: `curl -I <address>`. The first line says `HTTP/2 200` or `HTTP/1.1 200`.
- The log during the failure: `Machin logs`. A `flux tombé` must appear about ten seconds after the cut, a little later if the player had sound buffered, then `reprise du flux` (stream resumed) once it is back.
- If the station still stays on dead air without `flux tombé`, open an issue with the log, the stream address and the response of `curl -I`.

## The interface closes suddenly: preview, audio preferences, locked session, screens asleep

**Symptom**: the interface closes without a message, when opening the preview, changing its output, opening the « Audio » page of the preferences, or when coming back from a locked session or sleeping screens. The terminal, if there is one, shows `Fatal Python error: Aborted`, `Segmentation fault` or `double free or corruption`, in `gst_device_monitor_stop`, `g_slist_delete_link`, or a PipeWire thread (`libgstpipewire.so`, `libpipewire-module-metadata.so`); `coredumpctl list` keeps a trace of it.

**Cause**: a defect of GStreamer 1.28.0 to 1.28.2, the one in Ubuntu 26.04 ([#289](https://github.com/dascritch/machincast/issues/289)). Listing the audio devices stopped the device monitor before it had finished starting. Since [#289](https://github.com/dascritch/machincast/issues/289), MachinCast waits for that start, and the list is also complete. GStreamer 1.28.3 fixes the defect on its side. With PipeWire 1.6.2, stopping the monitor while outputs appear or disappear, like an HDMI output when the screen goes to sleep, also killed the interface ([#305](https://github.com/dascritch/machincast/issues/305)): since then, the interface keeps a single monitor, open until it closes.

**To check**:

- The MachinCast version: an installation from before [#305](https://github.com/dascritch/machincast/issues/305) is updated with `git pull`, then `./install.sh`.
- The interface log: « le moniteur de périphériques n'a pas fini de démarrer en 5 secondes » (the device monitor did not finish starting within 5 seconds) means that a device provider, PipeWire, PulseAudio or ALSA, takes too long to answer. The list may then be incomplete; the interface does not close. Check that the sound server is running: `systemctl --user status pipewire`.
- `python -m tests.mesures_peripheriques --bascule`, from the repository, measures the defect on the machine, while an output appears and disappears ([Mesurer la liste des périphériques audio](doc/fr/developpement/poste.md#mesurer-la-liste-des-périphériques-audio), French).

**Scenario that watches for it**: « La liste des périphériques du poste, en boucle, ne fait jamais tomber son processus », in `tests/features/peripheriques_liste.feature`, on every test run.

## Desktop sounds go on air

**Symptom**: a notification, the sound of a video, a video call or the browser can be heard on air, over the playout.

**Cause** ([#250](https://github.com/dascritch/machincast/issues/250)): the on-air device is the desktop's default output, the one used by every program that does not choose one. MachinCast plays no part: `Machin lecture` plays on `audio.peripherique`, whatever the default output.

**To check**:

- `pactl get-default-sink` must not give the identifier of `audio.peripherique`. Otherwise, choose another default output, and mute notification sounds: see [Preparing the on-air machine](INSTALL.md#preparing-the-on-air-machine).
- `wpctl status`, under PipeWire, lists in « Streams » the programs that are playing, and on which output.

## The preview stops, or the VU meter reopens, when a screen wakes up

**Symptom**: when coming back from a locked session or a sleeping screen, the preview has stopped (« Lecture impossible : … », playback impossible), or the on-air VU meter says for a while « Indisponible : le port de monitoring ne donne plus rien depuis 3 secondes. » (unavailable: the monitoring port has given nothing for 3 seconds).

**Cause**: when the screen goes to sleep, audio outputs disappear, like the HDMI screen's, and the machine's sound server can interrupt the running streams. The preview then stops, and says so ([#259](https://github.com/dascritch/machincast/issues/259)); the VU meter does not keep its last levels, and reopens its port every 5 seconds, until sound comes back ([#311](https://github.com/dascritch/machincast/issues/311)). Playout is not affected.

**To check**:

- That the screen of the on-air machine does not go to sleep: see [Preparing the on-air machine](INSTALL.md#preparing-the-on-air-machine) ([#250](https://github.com/dascritch/machincast/issues/250)).
- Restart the preview once the sound is back. If the VU meter stays unavailable for more than 10 seconds, check that the sound server is running (`systemctl --user status pipewire`), then open an issue with the console output of `Machin interface`.

## The station switches to the preview output when the session locks

**Symptom**: when the session locks or the screen turns off, the station leaves its device and goes to the machine's default output, often the preview.

**Cause** ([#345](https://github.com/dascritch/machincast/issues/345)): on sleep, WirePlumber, which manages PipeWire's outputs, can change a sound card's profile, for instance to prefer an output it considers available. The profile change removes the on-air output for a while. PipeWire then sent the station to the default output.

**What MachinCast does**: under PipeWire, the station is locked to `audio.peripherique` (`node.dont-fallback`, `node.linger`, `node.dont-move`). It never goes to another output, and the machine's sound settings cannot move it there. While its device is missing, the current sound pauses, without an error; it resumes where it was as soon as the device comes back. The VU meter likewise always listens to that device.

**To check**:

- The MachinCast version: an installation from before [#345](https://github.com/dascritch/machincast/issues/345) is updated with `git pull`, then `./install.sh`.
- The lock of the on-air stream, during playout: `pw-dump` must show, on the node whose `application.name` is « MachinCast lecteur » and which has a `target.object`, the on-air device and `true` for `node.dont-fallback`, `node.linger` and `node.dont-move`.
- While locked, `pw-top`, from another machine over SSH: the **MachinCast lecteur** line must never appear under another output than the on-air one.
- `pw-mon`, started before locking, shows whether the card's profile changes: in that case, the on-air output disappears then comes back, and the station is silent meanwhile.

**Scenarios that watch for it**: `tests/features/sortie_verrouillee.feature`, on a separate PipeWire and WirePlumber, on every test run; skipped if `pipewire` and `wireplumber` are not installed.

## Scenarios to run before a release

Some scenarios run neither with `pytest` nor with `bin/Machin dev-test`: they are slow, or need a separate server. They are marked `@release`, and are run before each release ([#208](https://github.com/dascritch/machincast/issues/208)), and after any update of GStreamer or libsoup:

```bash
.venv/bin/pytest -m release
```

They need the test dependencies (`./install.sh --dev`, or `pip install --editable ".[dev]"`, which installs hypercorn) and `openssl`.

| Feature | What it checks | If it fails |
| --- | --- | --- |
| `tests/features/flux_http2.feature` ([#278](https://github.com/dascritch/machincast/issues/278)) | A local server serves an AAC stream over HTTP/2, encrypted, which freezes after 3 seconds. Read the way MachinCast reads it, it is served over HTTP/1.1, and the player reports it as an error at most 15 seconds after the freeze. Read over HTTP/2, the player reports nothing, but MachinCast's watchdog sees the frozen voice. | On « servi en HTTP/1.1 » (served over HTTP/1.1) or « en erreur » (in error): `SOUP_FORCE_HTTP1` no longer has an effect, the failure above may come back. On « toujours en cours » (still running) over HTTP/2: libsoup now reports the freeze over HTTP/2, and forcing HTTP/1.1 can be reconsidered, in an issue. |
