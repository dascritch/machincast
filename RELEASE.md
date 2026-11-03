# MachinCast releases

*[Version française](RELEASE.fr.md)*

Published versions, most recent first. Procedure: [doc/fr/developpement/release.md](doc/fr/developpement/release.md) (French).

## 0.9.0 — 2026-10-28

First published version, ahead of 1.0: everything MachinCast does, feature by feature.

### On-air playout: Machin lecture

- The active event, by the priorities and times of the schedule ([#12](https://github.com/dascritch/machincast/issues/12)), and the choice of a sound in a bank, sequential or random ([#13](https://github.com/dascritch/machincast/issues/13)).
- The running order of an event's playlist, and the transitions from one event to the next ([#14](https://github.com/dascritch/machincast/issues/14)), through the playout loop ([#88](https://github.com/dascritch/machincast/issues/88)).
- The GStreamer audio engine, with crossfades ([#15](https://github.com/dascritch/machincast/issues/15)), and the position of the fades relative to a sound's silences ([#234](https://github.com/dascritch/machincast/issues/234)).
- Streams, their drop-outs and recovery, and their fallback event ([#16](https://github.com/dascritch/machincast/issues/16)).
- The airplay and the log ([#17](https://github.com/dascritch/machincast/issues/17)), with the starts and ends of events and sequences ([#153](https://github.com/dascritch/machincast/issues/153)).
- Automatic expiry of sounds ([#18](https://github.com/dascritch/machincast/issues/18)).
- Metadata hiding, and the outputs: airplay as CSV, `.pls` playlist and public HTML page ([#19](https://github.com/dascritch/machincast/issues/19)).
- The state socket, which the interface follows ([#20](https://github.com/dascritch/machincast/issues/20)).
- Simulation of a playout period ([#21](https://github.com/dascritch/machincast/issues/21)).
- The "do not repeat" bank ([#63](https://github.com/dascritch/machincast/issues/63)), and sequences, reusable series of sounds and banks ([#99](https://github.com/dascritch/machincast/issues/99)).
- The immediate playlist: the next sound and the ones after it, reserved in advance ([#228](https://github.com/dascritch/machincast/issues/228)).
- A sound played without its silences at the start and the end ([#146](https://github.com/dascritch/machincast/issues/146)).
- Last-minute analysis of a sound never fully checked ([#181](https://github.com/dascritch/machincast/issues/181)).
- Dead air in a sound, logged, which can switch to the fallback ([#122](https://github.com/dascritch/machincast/issues/122)).
- MachinCast's name in the desktop's sound settings, under PipeWire and PulseAudio ([#296](https://github.com/dascritch/machincast/issues/296)).

### Scheduling and on air, from the interface

- The home screen: current sound, next sound, airplay ([#23](https://github.com/dascritch/machincast/issues/23), [#144](https://github.com/dascritch/machincast/issues/144)), with the timelines of the current and the next sound ([#230](https://github.com/dascritch/machincast/issues/230)), the upcoming sounds, and an Airplay tab that can be configured and exported ([#244](https://github.com/dascritch/machincast/issues/244)).
- The on-air VU meter, with its "Clipping" and "Dead air" lights ([#24](https://github.com/dascritch/machincast/issues/24), [#191](https://github.com/dascritch/machincast/issues/191)).
- Control of the playout service ([#25](https://github.com/dascritch/machincast/issues/25)).
- Interrupting the station: skipping the sound, the sequence or the event ([#104](https://github.com/dascritch/machincast/issues/104)), and bringing the next event forward ([#257](https://github.com/dascritch/machincast/issues/257)).
- The schedule calendar ([#36](https://github.com/dascritch/machincast/issues/36)), by week ([#118](https://github.com/dascritch/machincast/issues/118)), in the colours of the event types ([#293](https://github.com/dascritch/machincast/issues/293)), as a permanent tab ([#307](https://github.com/dascritch/machincast/issues/307)).
- Skipping a session of a recurring event, and restoring it ([#273](https://github.com/dascritch/machincast/issues/273), [#295](https://github.com/dascritch/machincast/issues/295)).
- A change to the schedule applies on air at once ([#266](https://github.com/dascritch/machincast/issues/266)).
- A guaranteed music feed ([#39](https://github.com/dascritch/machincast/issues/39)), and suggestions at start-up ([#119](https://github.com/dascritch/machincast/issues/119), [#231](https://github.com/dascritch/machincast/issues/231)).
- The incidents screen ([#35](https://github.com/dascritch/machincast/issues/35)) and the simulation screen ([#37](https://github.com/dascritch/machincast/issues/37)).

### Sounds, banks, sequences, events and feeds

- Lists with search ([#26](https://github.com/dascritch/machincast/issues/26)), multiple selection ([#114](https://github.com/dascritch/machincast/issues/114)), sorting of durations, dates and priorities ([#272](https://github.com/dascritch/machincast/issues/272), [#302](https://github.com/dascritch/machincast/issues/302)), and global search ([#27](https://github.com/dascritch/machincast/issues/27), [#105](https://github.com/dascritch/machincast/issues/105)).
- The detail screens of a sound ([#28](https://github.com/dascritch/machincast/issues/28), [#125](https://github.com/dascritch/machincast/issues/125)), a bank ([#31](https://github.com/dascritch/machincast/issues/31), [#143](https://github.com/dascritch/machincast/issues/143)), an event ([#32](https://github.com/dascritch/machincast/issues/32), [#140](https://github.com/dascritch/machincast/issues/140)) and a sequence ([#112](https://github.com/dascritch/machincast/issues/112), [#138](https://github.com/dascritch/machincast/issues/138)), with their input errors highlighted ([#270](https://github.com/dascritch/machincast/issues/270)).
- Feeds, reusable stream addresses ([#34](https://github.com/dascritch/machincast/issues/34), [#252](https://github.com/dascritch/machincast/issues/252)).
- Adding sounds ([#30](https://github.com/dascritch/machincast/issues/30)), and duplicating an event, a sequence or a bank ([#130](https://github.com/dascritch/machincast/issues/130)).
- Deletion with its references ([#33](https://github.com/dascritch/machincast/issues/33)), deferred and restorable ([#267](https://github.com/dascritch/machincast/issues/267)); a sound file is never deleted ([#96](https://github.com/dascritch/machincast/issues/96)).
- Minimum and maximum durations of a bank's sounds ([#147](https://github.com/dascritch/machincast/issues/147), [#210](https://github.com/dascritch/machincast/issues/210)).
- Preview on a separate output ([#29](https://github.com/dascritch/machincast/issues/29), [#116](https://github.com/dascritch/machincast/issues/116)), with the file's timeline ([#224](https://github.com/dascritch/machincast/issues/224)), from any sound row ([#226](https://github.com/dascritch/machincast/issues/226)), and preview of the on-air output ([#245](https://github.com/dascritch/machincast/issues/245), [#256](https://github.com/dascritch/machincast/issues/256)).
- Typed texts cleaned up when saved ([#108](https://github.com/dascritch/machincast/issues/108)).

### The interface, day to day

- The main menu ([#117](https://github.com/dascritch/machincast/issues/117)) and the preferences: default crossfades, devices, thresholds ([#145](https://github.com/dascritch/machincast/issues/145)).
- Tabs opened on demand ([#180](https://github.com/dascritch/machincast/issues/180)), their keyboard shortcuts ([#192](https://github.com/dascritch/machincast/issues/192)), and their refresh ([#148](https://github.com/dascritch/machincast/issues/148)).
- Table columns, fitted, reorderable, hideable and remembered ([#207](https://github.com/dascritch/machincast/issues/207)).
- Emoji that underline the intent of actions ([#294](https://github.com/dascritch/machincast/issues/294)).
- A choice of application icon, and the desktop shortcut ([#62](https://github.com/dascritch/machincast/issues/62), [#111](https://github.com/dascritch/machincast/issues/111), [#213](https://github.com/dascritch/machincast/issues/213)).

### Indexing sounds

- Checking a file by fully decoding it, and its duration ([#7](https://github.com/dascritch/machincast/issues/7)); reading its tags ([#8](https://github.com/dascritch/machincast/issues/8)); its real type ([#121](https://github.com/dascritch/machincast/issues/121)).
- Recursive indexing of bank directories ([#9](https://github.com/dascritch/machincast/issues/9)), which spots deleted, moved or changed files ([#10](https://github.com/dascritch/machincast/issues/10)), and adds or removes a sound from a bank by its duration ([#195](https://github.com/dascritch/machincast/issues/195)).
- The audit report of anomalies, as CSV and HTML ([#11](https://github.com/dascritch/machincast/issues/11)), and the indexing log ([#120](https://github.com/dascritch/machincast/issues/120)).
- The states of a sound ([#66](https://github.com/dascritch/machincast/issues/66)), quick indexing and the full audit ([#69](https://github.com/dascritch/machincast/issues/69)), optimised ([#206](https://github.com/dascritch/machincast/issues/206)).
- Indexing started from the interface ([#38](https://github.com/dascritch/machincast/issues/38)).

### Installation and administration

- The installation script `install.sh` ([#40](https://github.com/dascritch/machincast/issues/40)), which interrupts running programs ([#254](https://github.com/dascritch/machincast/issues/254)), and the systemd playout service ([#22](https://github.com/dascritch/machincast/issues/22)).
- The `Machin` command: calling the programs, help and completion ([#6](https://github.com/dascritch/machincast/issues/6)), and the `machincast.toml` configuration ([#2](https://github.com/dascritch/machincast/issues/2), [#76](https://github.com/dascritch/machincast/issues/76)).
- The PostgreSQL database, and one role per program ([#3](https://github.com/dascritch/machincast/issues/3), [#4](https://github.com/dascritch/machincast/issues/4)).
- Database maintenance: backup, schema, optimisation ([#127](https://github.com/dascritch/machincast/issues/127)), and pruning of what is past the retention period ([#268](https://github.com/dascritch/machincast/issues/268), [#269](https://github.com/dascritch/machincast/issues/269)).
- The information of each published version: what's new at start-up, version, release guide ([#208](https://github.com/dascritch/machincast/issues/208)), and its `.tar.gz` archive ([#41](https://github.com/dascritch/machincast/issues/41)).

### Thanks

To Xavier Mouton-Dubosc ([dascritch](https://github.com/dascritch)), broadcasting manager of [Radio &lt;FMR&gt; 89.1 Toulouse](https://radio-fmr.net), who asked for each of these features, reported every problem and reviewed every change.
