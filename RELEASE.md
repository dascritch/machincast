# MachinCast releases

*[Version française](RELEASE.fr.md)*

Published versions, most recent first. Procedure: [doc/fr/developpement/release.md](doc/fr/developpement/release.md) (French).

## 0.9.1 — 2026-11-23

A consolidation release: MachinCast speaks French and English, the playout service runs under its own account, the interface gains in comfort, and the database is backed up and taken back on a new machine.

### To know before updating

- **English names**: the commands (`Machin player`, `Machin indexer`…), their options, the keys of `machincast.toml` and the database schema are in English ([#352](https://github.com/dascritch/machincast/issues/352), [#356](https://github.com/dascritch/machincast/issues/356), [#357](https://github.com/dascritch/machincast/issues/357), [#358](https://github.com/dascritch/machincast/issues/358), [#359](https://github.com/dascritch/machincast/issues/359), [#367](https://github.com/dascritch/machincast/issues/367), [#368](https://github.com/dascritch/machincast/issues/368)). An old `machincast.toml` is refused, and a database with the old schema does not update: the configuration is redone from the template, and the databases are recreated ([Updating](INSTALL.md#updating)).
- **Playout service**: it now runs under its own account, with its own PipeWire, and no longer reads home directories; `./install.sh --service` updates it, and offers to move MachinCast and the sounds out of a home directory ([#381](https://github.com/dascritch/machincast/issues/381), [#376](https://github.com/dascritch/machincast/issues/376)).

### Languages

- The interface, the messages, the help, `Machin` and `install.sh` speak the language of the session, French or English ([#360](https://github.com/dascritch/machincast/issues/360)); so does what is new in the version ([#369](https://github.com/dascritch/machincast/issues/369)).
- The top-level documents are in English, with their French source, and the documentation is organised by language ([#355](https://github.com/dascritch/machincast/issues/355)); the on-air guide and the administration guide are translated into English, in `doc/en`.

### On-air playout

- The « breaking » priority, above the specials ([#402](https://github.com/dascritch/machincast/issues/402)), and what an event does at the end of its list ([#350](https://github.com/dascritch/machincast/issues/350)).
- Going back to the start of the sound, or restarting the event, from the Broadcast menu ([#366](https://github.com/dascritch/machincast/issues/366)); cutting the air from the next sound, by the fallback or by a feed ([#323](https://github.com/dascritch/machincast/issues/323)).
- A fallback that calls on an external stream is reported ([#403](https://github.com/dascritch/machincast/issues/403)); the buffer of a feed is set, and the On air tab shows how full it is ([#351](https://github.com/dascritch/machincast/issues/351)).
- The air resumes after its audio output disappears ([#237](https://github.com/dascritch/machincast/issues/237)); a dummy output plays on a virtual card, which the VU meter listens to ([#400](https://github.com/dascritch/machincast/issues/400)).
- Banks in the order of the file names of their sounds, from A to Z or from Z to A ([#454](https://github.com/dascritch/machincast/issues/454)).
- A show can lend its name to the background programming until its end time, empty list included, when the team cannot take the air on time ([#399](https://github.com/dascritch/machincast/issues/399)).

### Interface

- The On air tab, with the indicator of the service and of the broadcast, and the emoji of its actions ([#322](https://github.com/dascritch/machincast/issues/322), [#344](https://github.com/dascritch/machincast/issues/344)).
- Tabs remembered from one launch to the next ([#321](https://github.com/dascritch/machincast/issues/321)), movable ([#405](https://github.com/dascritch/machincast/issues/405)), with titles limited to 40 characters ([#398](https://github.com/dascritch/machincast/issues/398)), and new shortcuts: Ctrl+W, Ctrl+S, Ctrl+Enter, Ctrl+Shift+T ([#428](https://github.com/dascritch/machincast/issues/428)).
- The pre-listen in a separate window ([#325](https://github.com/dascritch/machincast/issues/325)), and the calendar as a day or week view, with the zoom on the hours ([#326](https://github.com/dascritch/machincast/issues/326)).
- Lists and tables: anomaly column on the left ([#327](https://github.com/dascritch/machincast/issues/327)), CSV export ([#329](https://github.com/dascritch/machincast/issues/329)), full-text filter ([#393](https://github.com/dascritch/machincast/issues/393)), alternating rows ([#412](https://github.com/dascritch/machincast/issues/412)), and paged reading of long lists ([#383](https://github.com/dascritch/machincast/issues/383)).
- Cards: empty list as a warning, clearer hiding ([#328](https://github.com/dascritch/machincast/issues/328)), greyed out while saving and closed when it succeeds ([#382](https://github.com/dascritch/machincast/issues/382)).
- The card of a sound: start and end set on the timeline ([#330](https://github.com/dascritch/machincast/issues/330)), relations to remove ([#331](https://github.com/dascritch/machincast/issues/331)), and the full check offered, with going back to the file values ([#388](https://github.com/dascritch/machincast/issues/388)).
- The interface preferences and the broadcast service settings, separated according to what restarts the broadcast ([#389](https://github.com/dascritch/machincast/issues/389)); the silence threshold on the Crossfades page ([#324](https://github.com/dascritch/machincast/issues/324)); choosing the sound cards at launch ([#339](https://github.com/dascritch/machincast/issues/339)).
- The status of the sound indexings ([#392](https://github.com/dascritch/machincast/issues/392)), and the version window, with its links ([#332](https://github.com/dascritch/machincast/issues/332)).
- Help → « Your installation », the team's editable document, opened in a text editor, and the team link ([#451](https://github.com/dascritch/machincast/issues/451), [#491](https://github.com/dascritch/machincast/issues/491)).
- More responsive: the VU meter pauses while the session sleeps, and waits no longer freeze the window ([#346](https://github.com/dascritch/machincast/issues/346), [#387](https://github.com/dascritch/machincast/issues/387), [#345](https://github.com/dascritch/machincast/issues/345), [#343](https://github.com/dascritch/machincast/issues/343)); more stable ([#413](https://github.com/dascritch/machincast/issues/413), [#320](https://github.com/dascritch/machincast/issues/320)).

### Backup and recovery

- `Machin backup-db` exports the database, also from Maintenance → Export the database…; on a new machine, `install.sh` offers to reimport it; the Backup page of the broadcast service settings also copies `machincast.toml` ([#347](https://github.com/dascritch/machincast/issues/347)).

### Installation and administration

- The timers of the service: the quick indexing every hour, and every day, at the set hour, the purge then the full audit ([#455](https://github.com/dascritch/machincast/issues/455)).
- The on-air machine does not turn off, restart or suspend without an administrator's password ([#448](https://github.com/dascritch/machincast/issues/448)).
- `Machin grant-read` lets the service read the sounds; uninstalling never removes a directory that contains sounds ([#381](https://github.com/dascritch/machincast/issues/381), [#430](https://github.com/dascritch/machincast/issues/430)).
- `Machin logs` follows the service journal ([#459](https://github.com/dascritch/machincast/issues/459)); the starts and stops of the programs are noted ([#341](https://github.com/dascritch/machincast/issues/341)); a crash leaves a report ([#342](https://github.com/dascritch/machincast/issues/342)).
- The indexing lock per mode: quick and full can run together ([#401](https://github.com/dascritch/machincast/issues/401)).

### Documentation and quality

- The documentation reread from end to end ([#461](https://github.com/dascritch/machincast/issues/461)), made more precise ([#338](https://github.com/dascritch/machincast/issues/338)), the arc42 architecture document ([#446](https://github.com/dascritch/machincast/issues/446)), and the contribution guide renamed `CONTRIBUTING.md` ([#456](https://github.com/dascritch/machincast/issues/456)).
- Code quality: locked dependencies, functions and classes split, queries grouped, sturdier tests ([#340](https://github.com/dascritch/machincast/issues/340), [#390](https://github.com/dascritch/machincast/issues/390), [#437](https://github.com/dascritch/machincast/issues/437), [#438](https://github.com/dascritch/machincast/issues/438), [#439](https://github.com/dascritch/machincast/issues/439), [#440](https://github.com/dascritch/machincast/issues/440), [#441](https://github.com/dascritch/machincast/issues/441), [#442](https://github.com/dascritch/machincast/issues/442), [#443](https://github.com/dascritch/machincast/issues/443), [#444](https://github.com/dascritch/machincast/issues/444), [#445](https://github.com/dascritch/machincast/issues/445), [#384](https://github.com/dascritch/machincast/issues/384), [#470](https://github.com/dascritch/machincast/issues/470)); tests targeted per ticket ([#408](https://github.com/dascritch/machincast/issues/408)) and the `preprod`, `qualif`, `main` branch flow ([#480](https://github.com/dascritch/machincast/issues/480)).

### Thanks

To Xavier Mouton-Dubosc ([dascritch](https://github.com/dascritch)), broadcasting manager of [Radio &lt;FMR&gt; 89.1 Toulouse](https://radio-fmr.net), who asked for each of these improvements, reported each problem and reviewed each change.

## 0.9.0 — 2026-10-28

First published version, ahead of 1.0: everything MachinCast does, feature by feature.

### On-air playout: Machin player

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
