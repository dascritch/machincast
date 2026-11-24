# Broadcast: Machin player

[Administration guide](README.md) › Broadcast

- [What Machin player does](#what-machin-player-does)
- [Starting and stopping the broadcast](#starting-and-stopping-the-broadcast)
- [Simulating the broadcast](#simulating-the-broadcast)
- [State of the broadcast for the interface](#state-of-the-broadcast-for-the-interface)
- [Audio output](#audio-output)
- [AIFF files: not supported](#aiff-files-not-supported)
- [Broadcast history and log](#broadcast-history-and-log)
- [Checking the service on the on-air machine](#checking-the-service-on-the-on-air-machine)

## What Machin player does

`Machin player` broadcasts the schedule on the audio output of the configuration, continuously, until it is stopped ([#88](https://github.com/dascritch/machincast/issues/88)), files and streams. It can also simulate a period in advance, without sound or writing to the database (see [Simulating the broadcast](#simulating-the-broadcast)). On a computer dedicated to the air, it runs as a service, `machincast.service` ([INSTALL.md](../../../INSTALL.md#playout-service)), which the interface starts, stops and restarts ([Controlling the broadcast from the interface](../utilisateur/antenne.md#controlling-the-broadcast)).

## Starting and stopping the broadcast

```bash
Machin player                   # with the machincast.toml of the MachinCast directory
Machin player --config <file>
```

- **Database**: `Machin player` broadcasts the schedule of the production database (`database.production`), with the `machincast_player` role. If the database is unreachable, it stops at once with code 1 and the message `database unreachable`.
- **Output**: it plays on the output of `audio.output`, on the on-air device, `audio.device`. Without this device, it refuses to broadcast with code 2 and the message `on-air device not set`: the default device could be that of the pre-listen. It is set in `machincast.toml` or in the [preferences](../utilisateur/prise-en-main.md#preferences) of the interface ([#116](https://github.com/dascritch/machincast/issues/116)); only the `dummy` output of the trials does without it. If the output cannot be created, it stops with code 1 and the message `audio output unavailable`. The on-air device must not be the desktop's default output, and the notification sounds must be muted: otherwise, they go on air ([#250](https://github.com/dascritch/machincast/issues/250), [Preparing the on-air machine](../../../INSTALL.md#preparing-the-on-air-machine)).
- **Running**: it shows the output used, notes `start` in the log (except in simulation), then plays the sounds one after the other without intervention. Each play is written to the airplay when it starts and when it ends.
- **Stopping**: `Ctrl-C` in the terminal, or the `SIGTERM` signal (stopping a service). The current sound stops, its play is ended in the airplay, without an incident, `stop` is noted in the log, and the program stops with code 0.
- **Losing the database during the broadcast**: the output is cut, and the program stops with code 1 and the message `database error`.
- **A single `Machin player` at a time**: two broadcasts at the same time would each play their sounds and each write their airplay. A second `Machin player` launched on the same state socket is refused: it stops with code 1 and the message `broadcast refused: … another Machin player is already broadcasting`.

## Simulating the broadcast

To check a schedule before it goes on air, `Machin player` simulates what it would broadcast between two dates and times ([#21](https://github.com/dascritch/machincast/issues/21)):

```bash
Machin player --simulation "2026-10-20 06:00" "2026-10-20 22:00"
Machin player --simulation "2026-10-20 06:00" "2026-10-21 06:00" --seed 42 --name essai-mardi
```

| Option | Role |
| --- | --- |
| `--simulation START END` | Simulated period, in the machine's time: `2026-10-20 20:00`, or `2026-10-20T20:00:00`. The end must follow the start. |
| `--seed N` | Seed of the randomness: the same seed gives the same simulation, random draws included. Without a seed, each simulation draws differently. |
| `--name NAME` | Name of the files produced, without extension or `/`. By default, `simulation-` followed by the start and end dates, for instance `simulation-2026-10-20T0600-2026-10-20T2200`. |
| `--directory DIRECTORY` | Directory where to write the files produced ([#37](https://github.com/dascritch/machincast/issues/37)). By default, that of `outputs.csv` of the configuration. The simulation screen of the interface uses it for its temporary directory. |

- **Nothing is written to the database**, in the strict sense: the simulation reads the production database in a read-only transaction, where PostgreSQL refuses any writing. It starts from the real state, that is the position in each list, the cycle of each random bank and the number of plays of each sound, then keeps its own plays in memory. A sound that would reach its maximum of plays during the simulation is noted as expired in the simulation only.
- **No sound is played**, and the audio output is not opened: a simulation can run during the broadcast, on the same machine. It only lasts a few seconds for a day.
- **Durations**: they are those of the database, measured by the indexing. A stream is not contacted: the simulation assumes it holds until the end of its event.
- **Same rules as the broadcast**: priorities, clean cuts, crossfades, missing files (`file not found` incident), dead air (`dead air` warning).
- **Result**: three files in the output folder (that of `outputs.csv`, or that of `--directory`), for the whole period:
  - a CSV, with the same columns as the airplay CSV;
  - a `.pls` playlist;
  - an HTML page, with the list of the simulated warnings and incidents then the table of plays.

  The artist and the title are hidden there as on the public page (see [Outputs of the broadcast](configuration.md#outputs-of-the-broadcast)), and the location of each file, given everywhere, lets one check what will be played. A file of the same name is replaced.
- **Messages**: the simulated warnings and incidents are also shown as they come on the error output, dated and prefixed with `simulation:`. The summary, with the number of plays, warnings and incidents and the paths of the files, is shown at the end.
- **Exit codes**: 0 once the simulation is finished, even with warnings; 1 if the database is unreachable or if the files cannot be written; 2 for an invalid period or name, or for `--seed`, `--name` or `--directory` without `--simulation`.

## State of the broadcast for the interface

`Machin player` publishes its state on a Unix socket, which the interface reads to show what is on air ([#20](https://github.com/dascritch/machincast/issues/20)):

- **Location**: `player.state_socket` in the configuration, or by default, with the playout service, `/run/machincast/lecture.sock`, which the service and the accounts of the `machincast` group read ([#381](https://github.com/dascritch/machincast/issues/381)); without it, `lecture.sock` in the `machincast` folder of the account's runtime directory (`$XDG_RUNTIME_DIR`, generally `/run/user/1000`), which only the account that broadcasts can read. It disappears when the broadcast stops and when the machine restarts.
- **Content**: the running state (broadcasting, dead air or stopped), the current sound (location, start, duration, planned end, progress), the next sound (location, planned start and end, duration, whether it is healthy), and the 5 upcoming sounds after it, with the same information ([#228](https://github.com/dascritch/machincast/issues/228)). For a stream, the duration is unknown; its planned end is that of its event, where it fades out, and the next sound is the one that will take back the air at that moment ([#242](https://github.com/dascritch/machincast/issues/242)). The format is described field by field in the [specification, § 5.4](../../fr/spec.md#54-socket-détat) (French).
- **The announced next sound is the one that will play**: it is chosen from the start of the current sound, even drawn at random in a bank. It only changes if an event cuts the broadcast, if its event has ended, or if it is disabled or has expired in the meantime.
- **The upcoming sounds too** ([#228](https://github.com/dascritch/machincast/issues/228)): each one is chosen at the time it would be requested, cuts by the events included, and they will play in this order. At each change of sound, the list moves one step, and `Machin player` plans the fifth. On something unforeseen (interruption from the interface, cut that was not planned, schedule modified, dropped stream, sound no longer playable), it is recomputed entirely. The planning writes nothing, neither to the airplay nor to the log.
- **Healthy**: a file present, readable, in the `active` state, whose last play ended without an incident. A stream is not tested: its healthy state is unknown.
- **Requests**: in the other direction, the interface sends its interruption requests there ([Interrupting the air](../utilisateur/antenne.md#interrupting-the-air), [#104](https://github.com/dascritch/machincast/issues/104)).
- To see the state by hand: `socat - UNIX-CONNECT:/run/machincast/lecture.sock` with the service, otherwise `socat - UNIX-CONNECT:"${XDG_RUNTIME_DIR}/machincast/lecture.sock"` (`socat` package), one JSON line per change; `Ctrl-C` to quit.

A socket impossible to create (folder without write permission, for instance) is reported in the log by the `state socket unavailable` warning: the broadcast goes on without it.

The broadcast follows the rules below.

## Audio output

The on-air audio output is set in the configuration (`audio.output`: `pipewire`, `pulseaudio`, `alsa`, or `dummy`, the dummy output, for a trial without sound), and `install.sh` checks that it can be created. Sounds follow each other there this way ([#15](https://github.com/dascritch/machincast/issues/15)):

- **Start crossfade** of a sound: it rises gradually, from silent to full volume, during this time.
- **End crossfade** of a sound: the next sound starts that much before the end, and this one fades out gradually during this time. The two overlap.
- **Both crossfades are needed**: two sounds only overlap if the first has an end crossfade **and** the second a start crossfade. If one of them is at 0, the first plays to its end at full volume, then the second starts at once at full volume, without a fade.
- **Where crossfades come from** ([#145](https://github.com/dascritch/machincast/issues/145)): those imposed by the bank that provided the sound; otherwise those of the sound's card, if set there (0 second is one); otherwise those the bank applies by default; otherwise those of the [preferences](../utilisateur/prise-en-main.md#preferences), `[crossfades]` section of `machincast.toml`; otherwise none. For a sound played without its silences, their position around the detected start and end comes from the `fade_in_position` and `fade_out_position` keys of the same section, whatever the bank ([#234](https://github.com/dascritch/machincast/issues/234)).
- **Clean cut**: at the start of an event, the current sound stops at once, without a fade.
- **Before playing a file**, its modification date and its size are compared with those of the indexing. A difference is noted in the log as a `modified file` warning, and the file is played all the same; the next indexing, even a quick one, checks it again and updates the database. A missing file is not played: the `file not found` incident is noted in the log, and the broadcast moves on at once to the next sound. The sound is no longer offered for an hour, so as not to note the same incident at each round of the list; the next indexing will move it to the `missing` state.
- **Last-moment analysis** ([#181](https://github.com/dascritch/machincast/issues/181)): during each sound, if the **next** one is a file without a full audit since the last modification of its file ([#401](https://github.com/dascritch/machincast/issues/401)) — never audited, even if it was checked by a quick indexing, audited before the last modification of the file, or whose file has changed since —, `Machin player` launches `Machin indexer --full-audit --sound N` on it alone, in the background, without a window; its lines are added to the journal of `Machin player`. The broadcast does not wait for it: if the analysis crashes, or has not finished, the sound is played at its time. It is noted in the log, as `analysis of the next sound` info. This analysis is done even during a quick indexing or a full audit. The same sound is not requested again before an hour; a stream is never analysed.
- **In the machine's sound settings** ([#296](https://github.com/dascritch/machincast/issues/296)): under PipeWire or PulseAudio, the air appears as **MachinCast lecteur**, « Antenne » stream, the pre-listen as **MachinCast interface**, « Pré-écoute » stream, the listening to the air for the VU meter of the interface as **MachinCast interface**, « Écoute de l'antenne » stream ([#343](https://github.com/dascritch/machincast/issues/343)), and the output test of `install.sh` as **MachinCast installation**, « Son de test » stream, with the MachinCast icon, which `install.sh` installs in the account's icon theme. Without it, the Plasma sound settings only show a generic icon there. The PipeWire tools, such as `pw-top` or `pw-cli ls Node`, name the MachinCast streams the same way, rather than « python3.14 ». For any other client of the sound server, such as the one that lists the devices, `Machin_player` and `Machin_interface` also name themselves to GLib, from their launch.
- **The air stays on its device** ([#345](https://github.com/dascritch/machincast/issues/345)): under PipeWire, with an on-air device set (`audio.device`), the air never plays elsewhere. If this device disappears, the air is not sent to the machine's default output, often the pre-listen: it waits, and the current sound pauses. As soon as the device comes back, the sound resumes where it was. The machine's sound settings cannot move the air to another output either: to change it, modify `audio.device`. The VU meter likewise always listens to this device.
- **With the playout service** ([#381](https://github.com/dascritch/machincast/issues/381)): the on-air card belongs to the PipeWire of the service, hidden from the sessions of the machine. The sound settings of the session no longer show it: its level and its mute are set in the interface, **File → Broadcast service settings…**, **Audio** page. The `pulseaudio` output does not exist for the service: `install.sh --service` refuses it.
- **The audio inputs** ([#622](https://github.com/dascritch/machincast/issues/622)): the sound card inputs that MachinCast can put on air, `audio.inputs`, are chosen and named in **File → Broadcast service settings…**, **Audio** page. With the service, they belong to its PipeWire, like the on-air card: once saved, they are reserved for it at once, without running `install.sh --service` again. `pkexec` runs `python -m machincast.input_reservation --config <configuration>`, which rewrites `/etc/wireplumber/wireplumber.conf.d/50-machincast.conf` and restarts `machincast-wireplumber.service`, then the interface restarts the WirePlumber of the session.
- **Overlap**: during a crossfade, two sounds play at the same time. PipeWire and PulseAudio always mix them. With `alsa`, a device that mixes is needed, such as `default`; a direct hardware device (`hw:…`) only plays one sound at a time.

## AIFF files: not supported

MachinCast does not support AIFF (`.aiff`, `.aif`) ([#284](https://github.com/dascritch/machincast/issues/284)): the indexing ignores these files, like an unknown extension, and the file selector of the interface no longer offers them.

**Why**: GStreamer, which decodes the sounds, now and then blocks the start of an AIFF file, without an error or sound. This defect is already referenced and followed by MachinCast: [#236](https://github.com/dascritch/machincast/issues/236), [#280](https://github.com/dascritch/machincast/issues/280), [#281](https://github.com/dascritch/machincast/issues/281) and [#284](https://github.com/dascritch/machincast/issues/284). It comes neither from the file nor from MachinCast: it happens without MachinCast, on healthy AIFF files, with GStreamer 1.24 as with 1.28, that of Ubuntu 26.04. It affects the check of the indexing (`decodebin`, 44 blocked starts out of 1,000) and the former on-air player (`playbin`, 36 out of 300 in real time). The AIFF decoder, `aiffparse`, belongs to the « bad » plugins of GStreamer, those it considers still little tested.

**AIFF files already in the database** stay there, in their banks: they play, and the full audit still checks them, but without a guarantee. The on-air player, `playbin3`, never blocked on them in the measurements; a player that does not start all the same is replaced after 10 seconds by the next sound, with the `blocked playback` incident ([#281](https://github.com/dascritch/machincast/issues/281)). The check takes up a blocked decoding again up to six times ([#280](https://github.com/dascritch/machincast/issues/280)). To keep them on air for good, convert them to a supported format, FLAC or WAV, without loss: MachinCast never modifies a sound file, AIFF included ([#96](https://github.com/dascritch/machincast/issues/96)).

The measurements, and the state of the reports to GStreamer and elsewhere, are in [the guide of the development machine](../../fr/developpement/poste.md#mesurer-les-blocages-de-gstreamer) (French).

## Broadcast history and log

Each play on air is noted in the broadcast history, the **airplay** ([#17](https://github.com/dascritch/machincast/issues/17)):

- two rows per play, one at the start and one at the end, linked together;
- the location, the artist and the title of the sound, **as they were at the time of the play**, even if they are modified afterwards or if the sound is deleted;
- the bank that provided the sound, the event and the element of its list;
- on the end row, the duration actually broadcast, and whether the playback went without an incident. A sound cut short by the start of an event is not an incident.

The **log** notes the operations of the playout program, with their time, their level and what they concern (sound, bank, event):

| Nature | Level | When |
| --- | --- | --- |
| `start` | info | `Machin player` starts the broadcast; the message gives its version, its process number and its options ([#342](https://github.com/dascritch/machincast/issues/342)). |
| `end` | info or incident | `Machin player` has finished, with its exit code: info for 0, incident for 1 (an error stopped it) or 2 (invalid configuration or sound output). |
| `probable crash` | incident | At the start: the previous broadcast did not note its end (killed, deprived of power); the message gives the path of its [crash report](commandes.md#crash-reports), if there is one. |
| `stop` | info | `Machin player` stops the broadcast, on `Ctrl-C` or `SIGTERM`. |
| `clean cut` | info | An event starts and cuts the current sound. |
| `manual interruption` | info | From the interface, the current sound was skipped, the current sequence skipped, or the current event cut by the background programming ([Interrupting the air](../utilisateur/antenne.md#interrupting-the-air)); the message says which, for instance `of the sound “Café à minuit”`. The cut sound fades out during the default end crossfade of the configuration, or cleanly without it. |
| `advanced event` | info | From the interface, the next event was advanced: it took the air at once, until its planned end ([#257](https://github.com/dascritch/machincast/issues/257), [Interrupting the air](../utilisateur/antenne.md#interrupting-the-air)). The message says which and when it was planned: `of the event “Journal”, planned on 14/10/2026 at 20:30`. An ignored request leaves no row, but the journal of the program says why: `advance ignored: no next event`, or `advance ignored: the next event is “Journal”, not “Concert”` when the schedule has changed since it was shown. |
| `dead air` | warning | Nothing to broadcast: dead air. Was called `silence`: the update of the schema renames the warnings already recorded ([#291](https://github.com/dascritch/machincast/issues/291)). |
| `analysis of the next sound` | info | The next sound has not been checked in full, or its file has changed: `Machin indexer` analyses it in the background ([Audio output](#audio-output)). |
| `analysis impossible` | warning | `Machin indexer` could not be launched for the next sound; the message gives the error. The sound is played all the same. |
| `modified file` | warning | The file has changed since the indexing; it is played all the same. |
| `file not found` | incident | The file has disappeared; it is not played. |
| `interrupted playback` | incident | The playback of a file stopped on an error, whose message is noted. |
| `blocked playback` | incident | The player of a file has played nothing 10 seconds after its start; the next sound is played ([#281](https://github.com/dascritch/machincast/issues/281)). Seen on AIFF files, which are no longer supported, with the former player, `playbin`; the current player, `playbin3`, never blocked in the measurements (see [AIFF files: not supported](#aiff-files-not-supported)). Random: the sound plays normally afterwards. |
| `dead air in a sound` | incident | The current sound gives no more sound: it stayed 10 seconds under -90 dB peak ([#122](https://github.com/dascritch/machincast/issues/122), `[dead_air]` section of `machincast.toml`, set in the [preferences](../utilisateur/prise-en-main.md#preferences), « Audio » page). The message gives the location, the duration, where the dead air starts in the file and its average level: `…/jingle.flac: 10 s of dead air at 1:23.4 of the sound, average level -95.2 dB`, or `digital silence` for a file empty of any sound. Without moving to the fallback, the sound goes on. With it, a file gives the air at once to the next sound (`, the next sound is played`), its play ended as an incident; a stream gives it to its fallback event, or to the event below, and takes it back as soon as its sound comes back, with the `stream resumption` incident. Not to be confused with the `dead air` warning, nothing to broadcast. |
| `dropped stream` | incident | The feed of a stream does not answer, stopped before the end of its event, or has given no sound for 10 seconds, its connection open ([#278](https://github.com/dascritch/machincast/issues/278)); the message gives the address and the error, or « no more sound for 10 seconds, without a player error ». See [TROUBLESHOOTING.md](../../../TROUBLESHOOTING.md#a-stream-drops-but-the-station-stays-on-dead-air). |
| `stream resumption` | incident | The feed of a dropped stream, or in dead air, has come back, and the stream takes back the air; the message gives the address and the duration of the failure. |
| `expired sound` | info | A sound has reached its maximum of plays or the end of its broadcast period; the message gives the cause. |
| `state socket unavailable` | warning | The state socket cannot be created; the broadcast goes on without it. |
| `inaccessible output` | warning | An output (CSV, .pls or HTML page) cannot be written; the message gives the path and the error. |
| `skipped element` | info | An element calls again the « do not repeat » bank that has just played: it is skipped. The message gives the bank and the position of the element. |
| `event ended earlier` | warning | A show or a special has nothing playable left once the « do not repeat » bank is skipped: it ends, and the event below resumes. |
| `event start`, `event end` | info | An event takes the air, with its first sound, or leaves it, when a sound of another event starts, or when `Machin player` stops ([#153](https://github.com/dascritch/machincast/issues/153)). The message gives its name, its priority and its hours: « “Journal”, show, from 20:00 to 20:30 ». Dead air does not end the event. A show that lends its name to the background programming ([#399](https://github.com/dascritch/machincast/issues/399)) takes the air from its time, even during a sound of the background programming: « “Matinale”, show, from 20:00 to 20:30, which lends its name to “Continue” »; the background programming, which takes it back at its end, has its event start again. |
| `sequence start`, `sequence end` | info | Likewise for a sequence: « “Pub”, in “Continue” ». A sequence that comes back at once starts again. |
| `reconnection abandoned` | info | The event of a dropped stream is no longer on air: no more reconnection attempts. |

The airplay and the log are never modified or erased by the playout program: it can only add rows to them.

## Checking the service on the on-air machine

The playout service runs under its own account, `machincast`, with its PipeWire ([#381](https://github.com/dascritch/machincast/issues/381), [Playout service](../../../INSTALL.md#playout-service)). The scenarios test each piece separately; on the machine, after `./install.sh --service`, these checks are done by hand, in order.

1. **Before**: stop any `Machin player` launched by hand, then `./install.sh --simulation --service`, which shows the commands without running them. Then `./install.sh --service`: it says the machine becomes dedicated to the air and asks for it; from a home directory, it offers to move MachinCast to `/opt/machincast`, then resumes from there; it lists the sounds of the database in a home directory, and offers to move them to `/home/machincast`. Then check `ls -ld ~`: its rights have not changed, without `+`; `ls -l ~/machincast` is a link to `/opt/machincast`.
2. **Group**: log out, then log in again. `id -nG` must cite `machincast`.
3. **Restart the machine**, without opening a session: the service starts on its own. Then, with a session open:

	```bash
	systemctl status machincast-pipewire.service machincast-wireplumber.service machincast.service
	ls -l /run/machincast            # pipewire-0 and lecture.sock, owned by the machincast group
	Machin logs                       # the broadcast, live
	tail /var/log/machincast/Machin_player.log
	```

4. **On-air card**: `PIPEWIRE_RUNTIME_DIR=/run/machincast wpctl status` lists the cards of the service, the on-air one included; `wpctl status`, those of the session, without it. The sound of the air comes out of its card.
5. **Interface**: `Machin interface`; the status bar no longer says `Non-final installation`. The on-air VU meter moves, and its tooltip names « PipeWire of the broadcast service ». The on-air pre-listen is heard on the pre-listen card. **File → Broadcast service settings…**, **Audio** page: the on-air card is there, greyed out during the broadcast.
6. **Control**: **Broadcast** menu, stop, then restart the service, with an administrator's password.
7. **Protection of the machine** ([#448](https://github.com/dascritch/machincast/issues/448)): turning off or putting to sleep from the desktop menu asks for an administrator's password, and the login screen no longer offers to turn it off; a short press on the power button does nothing. `systemctl is-enabled ctrl-alt-del.target` answers `masked`.
8. **Reading the sounds**: `Machin grant-read` must end with code 0 (`echo $?`). Add to a bank a directory of `~`: the interface refuses it. A directory of `/home/machincast`: accepted without a question. `Machin grant-read ~/Musique` fails, without changing anything.
9. **Crash**: `sudo systemctl kill --signal=SIGSEGV machincast.service`; the service restarts 5 seconds later, and a report is added in `/var/log/machincast/crash-dump`, readable from the session.
10. **Removal**, if needed: `./install.sh --remove-service`, then `wpctl status` shows the on-air card again in the session; `getent passwd machincast` no longer answers anything; the machine turns off again without a password; the logs stay in `/var/log/machincast`.

A failure at a step: `journalctl --unit=machincast-pipewire.service --unit=machincast-wireplumber.service --unit=machincast.service --boot` says why.
