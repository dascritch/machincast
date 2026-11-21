# Commands and messages

[Administration guide](README.md) › Commands and messages

- [Launching the programs: Machin](#launching-the-programs-machin)
- [Graphical interface: Machin interface](#graphical-interface-machin-interface)
- [Database maintenance: Machin maintenance-db](#database-maintenance-machin-maintenance-db)
- [Database export and reimport: Machin backup-db, Machin restore-db](#database-export-and-reimport-machin-backup-db-machin-restore-db)
- [Database purge: Machin purge](#database-purge-machin-purge)
- [Regular tasks: Machin tasks](#regular-tasks-machin-tasks)
- [Reading by the playout service: Machin grant-read](#reading-by-the-playout-service-machin-grant-read)
- [Following the journal: Machin logs](#following-the-journal-machin-logs)
- [Messages and exit codes](#messages-and-exit-codes)
- [Starts and ends in the log](#starts-and-ends-in-the-log)
- [Crash reports](#crash-reports)

## Launching the programs: Machin

All the MachinCast programs are launched by a single command, `Machin`, installed by `install.sh` for the whole system. It is used from any directory, without activating a Python environment.

```bash
Machin indexer                     # launches Machin_indexer
Machin indexer --full-audit     # the options that follow the program are passed to it
Machin --help                         # full help
```

| Command | Role |
| --- | --- |
| `Machin player` | Broadcast of the air, normally launched as a service ([Playout service](../../../INSTALL.md#playout-service)). |
| `Machin indexer` | Recording of the files put in the directories of the banks, checking of the sound files and update of the database. |
| `Machin interface` | [Graphical interface](#graphical-interface-machin-interface) for supervision and programming: the air, the schedule, the [lists](../utilisateur/listes.md#lists) and the cards, the simulation, the airplay and the incidents ([on-air guide](../utilisateur/README.md)). |
| `Machin maintenance-db` | [Maintenance of the production database](#database-maintenance-machin-maintenance-db): backup, check of the schema and the roles, optimisation. |
| `Machin backup-db` | [Export of the production database](#database-export-and-reimport-machin-backup-db-machin-restore-db): a dated backup, without changing anything. |
| `Machin restore-db FILE` | [Reimport of a backup](#database-export-and-reimport-machin-backup-db-machin-restore-db) into a new, empty database. |
| `Machin purge` | [Purge of the production database](#database-purge-machin-purge): erases what is past the expiry duration, never a file. |
| `Machin grant-read` | [Reading of the sounds by the playout service](#reading-by-the-playout-service-machin-grant-read), which runs under its own account. |
| `Machin logs` | Live following of the journal of the playout service. |
| `Machin tasks` | [Regular tasks](#regular-tasks-machin-tasks): what is due, launched every quarter of an hour by the service's timer. |

**Options of `Machin`**, placed before the name of the program:

| Option | Effect |
| --- | --- |
| `--config FILE` or `--config=FILE` | Configuration file to pass to the program, instead of `machincast.toml` (see [Configuration](configuration.md#configuration)). Placed after the name of the program, the option is passed to it as is, with the same effect. |
| `-h` | Minimal help, in two lines. |
| `--help` | Full help: programs, options, examples and exit codes. It also shows the path of the `machincast.toml` read by default. |
| `--binaries` | List of the programs, one per line. The completion uses it. |

**Options common to each program**, placed after its name:

| Option | Effect |
| --- | --- |
| `-h`, `--help` | Help of the program, for instance `Machin indexer --help`. |
| `--version` | Version of MachinCast, for instance `Machin_indexer (MachinCast) 0.9.1`. |
| `--config FILE` | Configuration file to read. |

**Completion.** In a bash terminal, the Tab key completes the names of the programs and `logs`, the options of `Machin`, the files after `--config`, the options of each program (read from its help) and the common options of `journalctl` after `logs`. It needs the `bash-completion` package, which `install.sh` installs. Without installation, `source bash-completion/Machin` loads it into the current terminal.

## Graphical interface: Machin interface

`Machin interface` opens the graphical interface of the on-air team; its use is described in the [on-air guide](../utilisateur/README.md), which its **Help → Documentation** menu opens in the web browser.

- **Database**: it connects to the production database (`database.production`), with the `machincast_interface` role ([Rights of each program in the database](configuration.md#rights-of-each-program-in-the-database)). Without a database, it opens an error window, « MachinCast: database unreachable », which leads to [When something goes wrong](../../../INSTALL.md#when-something-goes-wrong) and gives the PostgreSQL error in its details; when it closes, `Machin interface` stops with code 1. The message `database unreachable` (or `database error`, for an account without rights) is also shown on the error output. Without a graphical display, in an SSH session for instance, only this message is shown.
- **Same account and same configuration as the broadcast**: the On air tab follows the broadcast through its state socket, which, with the playout service, only the accounts of the `machincast` group open, and, without it, only the account that broadcasts ([State of the broadcast for the interface](diffusion.md#state-of-the-broadcast-for-the-interface)). The **Broadcast** menu controls the playout service, with the authentication of the service's polkit rule ([Playout service](../../../INSTALL.md#playout-service)), or, without a service, a trial broadcast launched in a terminal.
- **Settings**: **File → Interface preferences…** and **File → Broadcast service settings…** write to the `[crossfades]`, `[audio]`, `[silences]`, `[dead_air]`, `[interface]`, `[schedule]`, `[backup]` and `[database]` (the `retention` key only) sections of `machincast.toml`, which keeps its comments and its other settings; the « Getting started » window writes `audio.output`, `audio.device`, `audio.preview` and `interface.suggestions`. A file that cannot be written leaves the settings as they are, and the status bar says why. A new application icon (`interface.icon`, [#111](https://github.com/dascritch/machincast/issues/111)) also rewrites the `machincast.desktop` shortcuts already installed, in `~/.local/share/applications` and on the desktop, without creating any; the image itself is neither copied nor modified.
- **Your installation**: **Help → Your installation…** opens the team's document ([#451](https://github.com/dascritch/machincast/issues/451)) in the first text editor present among `kate`, `kwrite`, `gnome-text-editor`, `gedit`, `mousepad`, `xed`, `pluma` and `featherpad`; otherwise in the application the desktop associates with text files (`xdg-mime query default text/plain`), launched by `gio launch` (`libglib2.0-bin` package), never in that of `.md` files, often a viewer ([#491](https://github.com/dascritch/machincast/issues/491)). To impose another, associate it with text files: `xdg-mime default org.kde.kate.desktop text/plain`.
- **Indexing**: the **Maintenance** menu launches `Machin indexer --window`, with the configuration of the interface, in its own program ([Indexing: Machin indexer](indexation.md)).
- **Simulation**: the Simulation tab launches `Machin player --simulation`, with the configuration of the interface, its files in a temporary directory (`--directory`) erased when the tab closes ([Simulating the broadcast](diffusion.md#simulating-the-broadcast)).

## Database maintenance: Machin maintenance-db

`Machin maintenance-db` ([#127](https://github.com/dascritch/machincast/issues/127)) maintains the production database (`database.production`), in three steps, in order:

1. **Backup**: `pg_dump` copies the database into a new dated file, `<database>-<YYYY-MM-DDTHH-MM-SS>.dump`, in the PostgreSQL custom format. It is written to the backup directory, `backup.directory`, the account's home directory by default ([#347](https://github.com/dascritch/machincast/issues/347)), or to that of `--backups`, created if needed. No backup is erased: old ones are deleted by hand. **A failed backup stops the maintenance**, without changing anything.
2. **Schema**: the missing migrations are applied, as `install.sh` does. A database that had received the fifteen old migrations, merged since into the single schema, keeps its data, and the maintenance announces it; a database left at an old intermediate migration is left as it is, with `schema impossible to update: …`, after its backup ([#314](https://github.com/dascritch/machincast/issues/314), [Updating](../../../INSTALL.md#updating)). Then each of the three MachinCast roles must be assumable by the account. A missing or unauthorised role is reported, with the two commands an administrator runs to authorise it.
3. **Optimisation**: `VACUUM (ANALYZE)` recovers the space of erased rows and updates the statistics that guide PostgreSQL. The broadcast can go on meanwhile.

The account that launches it must be that of MachinCast, owner of the database: it needs no particular right on the server. It is also launched from the interface, **Maintenance → Database maintenance…** menu. The interface first asks for confirmation, giving the directory where the backup will be saved (the backup directory of its configuration), which the « Choose the location… » button can change. It then opens it in a terminal window, with the configuration of the interface and this directory (`--backups`); the window stays open at the end, until it is closed.

```bash
Machin maintenance-db
Machin maintenance-db --backups /srv/sauvegardes/machincast
```

| Option | Effect |
| --- | --- |
| `--backups DIRECTORY` | Backup directory, instead of `backup.directory`. |
| `--keep-open` | Once the maintenance is finished, keeps the terminal open until it is closed (or `Ctrl-D`, `Ctrl-C`); Enter does nothing there. The interface uses it, so that the report stays readable. |

It ends with `maintenance finished` (code 0), or with `maintenance finished, with anomalies` (code 1) when a role is missing. An unreachable database, an impossible backup or a schema impossible to update also give code 1.

**Restoring a backup.** It is made by the `pg_dump` of the server's version, `/usr/lib/postgresql/<version>/bin/pg_dump` ([#384](https://github.com/dascritch/machincast/issues/384)), otherwise by that of the `PATH`: the `pg_dump` of the `PATH` is the most recent installed, and its backup would not read with an older `pg_restore` (`unsupported version (1.16) in file header`). On a new machine, `./install.sh` offers to reimport it into the database it creates; by hand, `Machin restore-db` ([Export and reimport](#database-export-and-reimport-machin-backup-db-machin-restore-db)). To only look at it, it is read with the server's `pg_restore`, into a new database, to compare before replacing anything:

```bash
sudo -u postgres createdb --owner="$(id -un)" machincast_restauree
pg_restore --dbname=machincast_restauree --no-owner ~/machincast-2026-10-22T08-30-00.dump
```

## Database export and reimport: Machin backup-db, Machin restore-db

To start again quickly after a failure, on this machine or on another ([#347](https://github.com/dascritch/machincast/issues/347)):

1. **Export**: `Machin backup-db` backs up the production database, like the first step of the maintenance, without changing anything else: `pg_dump` of the server's version, in the PostgreSQL custom format, into a new dated file, `<database>-<YYYY-MM-DDTHH-MM-SS>.dump`, of the backup directory (`backup.directory`, the account's home directory by default; `--backups DIRECTORY` for another). The interface also launches it, without a terminal, **Maintenance → Export the database…** menu; the status bar says where the backup is saved, or why it could not be. The directory is set in **File → Broadcast service settings…**, **Backup** page, which also copies `machincast.toml`, under a dated name, where it is chosen, such as a USB key.
2. **Reimport**: on the new machine, `./install.sh` creates the production database, then offers to reimport a backup ([Reimporting a backup](../../../INSTALL.md#reimporting-a-backup)). By hand, into an empty database:

```bash
Machin backup-db
Machin backup-db --backups /media/cle/radio
Machin restore-db /media/cle/radio/machincast-2026-11-17T10-00-00.dump
```

`Machin restore-db FILE` first checks the backup, and refuses:

- a file not found, or that is not a MachinCast backup: `pg_restore` does not read it, or the MachinCast tables and the register of its migrations are missing from it;
- a backup of a newer version of MachinCast, some of whose migrations are unknown to the installed one: `… comes from a newer version of MachinCast (unknown migrations: …): update MachinCast first`;
- a production database that is not empty: **a database is never overwritten**. To start again from a backup on a machine already installed, the database is first deleted, after a last backup (`sudo -u postgres dropdb machincast`, with the name of `database.production`); `./install.sh` recreates it, then offers the reimport.

Then the `pg_restore` of the server's version reimports it in a single transaction: a failure leaves the database empty. Its tables come back to the account that reimports it, with the rights of the MachinCast roles, which `./install.sh` has created on the server. A backup of an older version finally receives the migrations it lacks. Code 0 if everything is done, 1 otherwise; `Machin backup-db` likewise. The sound files are not in the backup: they are copied separately, to the same paths.

## Database purge: Machin purge

`Machin purge` ([#268](https://github.com/dascritch/machincast/issues/268)) erases from the production database (`database.production`) what is past the **expiry duration**, `database.retention`, 60 days by default, counted from the time of the launch:

- the airplay plays finished before this limit; a play started before and finished after stays whole;
- the rows of the log from before this limit;
- the sounds, banks, sequences and events [deleted from the interface](../utilisateur/listes.md#deleting-an-element) for longer: they can no longer be restored;
- the sounds whose file the indexing found missing (`missing` state) for longer;
- the [skipped sessions](../utilisateur/grille.md#calendar) from before this limit ([#273](https://github.com/dascritch/machincast/issues/273)), which no longer serve any purpose; the report does not count them.

The more recent plays of an erased sound keep its location, its artist and its title, copied at the time of the play. **Only rows of the database are erased**: no sound file, no directory ([Sound files are never modified](configuration.md#sound-files-are-never-modified)). A file still present in the directory of a bank is indexed again, as a new sound. Everything is erased at once, or nothing: an error leaves the database as it is.

```bash
Machin purge
```

It says, and writes to the database log, `purge` row, what it has erased, for instance:

```text
2026-12-20T12:00:03+01:00 purge of database machincast, beyond 60 days (before 21/10/2026 12:00): 412 airplay plays, 37 log rows, 2 sounds, 1 bank, 0 sequences, 1 event erased
```

Code 0 when the purge is done; 1 if the database is unreachable, or on a database error: nothing is then erased. Like the maintenance, it is launched with the MachinCast account, owner of the database, which erases without assuming a role.

**The duration** is set in `machincast.toml` ([Configuration](configuration.md#expiry-duration)), or in the interface, **File → Interface preferences…**, **Database** page. **With the playout service** (`./install.sh --service`), a systemd timer launches it every day at the hour of `schedule.daily`, 10:00 by default, set in **File → Broadcast service settings…**, **Tasks** page, then the full audit ([Playout service](../../../INSTALL.md#playout-service), [#455](https://github.com/dascritch/machincast/issues/455)); its messages are read with `journalctl --unit=machincast-tasks.service`. Without a service, or with `--no-timers`, it is launched by hand.

## Regular tasks: Machin tasks

`Machin tasks` ([#455](https://github.com/dascritch/machincast/issues/455)) launches the regular tasks that are due, and nothing else. **With the playout service** (`./install.sh --service`, unless `--no-timers`), the systemd timer `machincast-tasks.timer` launches it every quarter of an hour, under the MachinCast account ([Playout service](../../../INSTALL.md#playout-service)). Today, one task:

- **the daily task**, once a day from the hour of `schedule.daily`, 10:00 by default, set in **File → Broadcast service settings…**, **Tasks** page: `Machin purge`, then `Machin indexer --full-audit`. It replaces the noon purge. `python -m machincast.schedule claim` says whether it is due, and notes its run in the service's state directory, `/var/lib/machincast-tasks`: a missed task, machine off, runs at the quarter of an hour that follows its start; a failed task is not retried before the next day.

What each run does is in the wrapper, not in the systemd unit: a task can be added there, or the timer change its period, without touching the other. `Machin tasks` takes no argument, except `--config FILE` before `tasks`, passed to each task. It is normally launched by its unit, which gives it its state directory; by hand, without it, it exits with code 2.

Code 0 when nothing was due, or everything that was succeeded: a full audit already running, launched from the interface, is not a failure; otherwise, that of the first failed task, which stops the daily task (a failed purge is not followed by the audit); 127 without the MachinCast venv. Its messages are read with `journalctl --unit=machincast-tasks.service`.

## Reading by the playout service: Machin grant-read

The playout service runs under its own account, `machincast` ([#381](https://github.com/dascritch/machincast/issues/381), [Playout service](../../../INSTALL.md#playout-service)): it only reads the sounds if the machine's rights allow it. It **never** reads a home directory, and MachinCast never changes the rights of a home directory, nor of a system tree (`/etc`, `/bin`, `/sbin`, `/usr`, `/boot`, `/media`, `/mnt`…): the sounds are put in `/home/machincast`, which it already reads. A library can also be below `/home/machincast`, `/opt`, `/srv` or `/var`, provided their root can already be crossed: `Machin grant-read` never changes it, nor the system directories of `/var` (`lib`, `log`, `cache`, `spool`…). For these directories, and any other outside the sensitive trees, `Machin grant-read` gives it the reading:

```bash
Machin grant-read                          # the bank directories and the added files of the production database
Machin grant-read /data/sonores/jingles    # only these paths
```

For each path, it gives the `machincast` account, through ACLs (`setfacl`, `acl` package):

- the **crossing** (`x`) of the parent directories that lack it, without the right to list their content;
- the **reading** (`r`, and `x` for directories) of the path, of everything it contains, and, through the default ACL of a directory, of the files that will be added to it.

Nothing else changes: neither the owner, nor the rights of its group or of the others, nor the content or the date of any file ([Sound files are never modified](configuration.md#sound-files-are-never-modified)). `ls -l` then shows a `+` after the rights, and `getfacl` details them. A path already readable is only announced. A change that would touch a sensitive tree is **refused**, and nothing is changed:

```text
/home/radio/sons: refused, it is in /home/radio, where MachinCast never changes any right
put the sound files in /home/machincast, which the broadcast service reads
```

`setfacl` only changes what belongs to the account that runs it. A directory of another account is reported, with the command an administrator runs, for instance:

```text
/data/partage: machincast cannot cross it, and it belongs to another account
an administrator can run: sudo setfacl --modify=u:machincast:x /data/partage
```

Code 0 when the service reads everything; 1 otherwise, or without a `machincast` account: the service is not installed, and `Machin player` reads with the account that launches it. From the interface, **Maintenance → Let the broadcast service read the sound files…** launches it in a terminal, on the database of the interface; adding a directory to a bank, or files, always accepts what the service already reads, refuses what it does not read in a home directory, checks that the service reads the others, and otherwise offers to let it read them. During the broadcast, a file the service does not read is not played: the database log says so as a warning, `unreadable file`, with its path.

## Following the journal: Machin logs

Each program also writes its messages to its file in `/var/log/machincast/`, `Machin_player.log`, `Machin_indexer.log`, `Machin_interface.log`…, each line preceded by its time and its level, `INFO`, `WARNING` or `ERROR` ([#381](https://github.com/dascritch/machincast/issues/381)). An unexpected error, such as a page of the intranet answering 500, keeps its traceback under its line, on the error output as in this file, and so in `journalctl` for a service ([#574](https://github.com/dascritch/machincast/issues/574)). `install.sh` creates this directory, owned by the `machincast` group, shared by the account of the playout service and yours: each reads what the other writes there. `logrotate` rotates these files every week.

`Machin logs` follows live the journal of the playout service, `machincast.service`. The options that follow are passed to `journalctl`, for instance:

```bash
Machin logs --since "1 hour ago" --priority=warning
```

Reading this journal requires belonging to the `systemd-journal` group, which `install.sh` does, effective after the machine restarts. As long as the playout service is not installed ([#22](https://github.com/dascritch/machincast/issues/22), [Playout service](../../../INSTALL.md#playout-service)), the journal is empty: `Machin player`, launched by hand, writes in its terminal. `Ctrl-C` stops the following.

## Messages and exit codes

Each message starts with its time, in ISO 8601, to the second, with the machine's time offset, for instance `2026-10-23T07:55:19+02:00 on air: Frédéric Galliano – Multiples Un (Fil musical)` ([#253](https://github.com/dascritch/machincast/issues/253)); it replaces the name of the program, which preceded it. The service journal (`Machin logs`) adds its own time in front. Information, such as the summary of an indexing, goes to the standard output; anomalies and errors, to the error output. A script can thus keep them separately.

| Code | Meaning |
| --- | --- |
| 0 | The program went to its end. For the indexing, even if sounds changed state: these are anomalies, not errors. |
| 1 | Database unreachable or lost (for `Machin interface`, at launch), missing GStreamer decoder, `Machin indexer --window` without a graphical display, audio output unavailable, another `Machin player` already broadcasting, database maintenance unfinished or with a missing role, database purge impossible, or function not written yet. |
| 2 | Invalid configuration, or incorrect call (unknown option, `--config` without a file, option refused with another). |
| 3 | `Machin indexer`: another indexing of the same mode is already running on the database; this one stops at once, without touching anything. Not a failure for the timers of the tasks ([#455](https://github.com/dascritch/machincast/issues/455)). |
| 127 | Program or `journalctl` not found, reported by `Machin`. |

The common error messages and their solution are in the [When something goes wrong](../../../INSTALL.md#when-something-goes-wrong) table of `INSTALL.md`.

## Starts and ends in the log

`Machin player`, `Machin indexer`, `Machin maintenance-db` and `Machin purge` each note their launches in their journal and in the database log, which the interface shows ([#341](https://github.com/dascritch/machincast/issues/341), [#342](https://github.com/dascritch/machincast/issues/342) for `Machin player`, outside simulation). A wrong move or a crash can be found there, with the time:

```text
2026-11-04T03:00:02+01:00 start: Machin_indexer 0.9.1, pid 4812: --full-audit
2026-11-04T03:12:47+01:00 end: Machin_indexer, pid 4812: exit code 0
```

- **The start**, nature `start`, at the information level: the program, its version, its process number (pid) and its options.
- **The end**, nature `end`: the same pid, and the [exit code](#messages-and-exit-codes). It is at the information level for code 0, as an **incident** for any other code, such as the 2 of a refused option, and can then be read in the **Incidents** tab of the interface.
- **A probable crash**, nature `probable crash`, as an incident: at the next launch of a program, if its previous start did not note an end and its process no longer runs. The program was killed, stopped by a signal, or the machine turned off along the way: `Machin_purge, pid 3920, started on 03/11/2026 at 12:00, did not log its end`. If it left a [crash report](#crash-reports), the message ends with its path: `; crash report /var/log/machincast/crash-dump/Machin_purge-2026-11-03T12-00-00-3920.txt`. A previous launch still running is not one. The playout service stopped by `systemctl stop`, or by the button of the interface, notes its end; killed or deprived of power, it notes the probable crash at its restart.

`Machin indexer --sound N`, which `Machin player` launches before each sound it is going to play, notes neither start nor end. `Machin maintenance-db --keep-open`, launched from the interface, notes its end before its window stays open: closing it is not a crash. An invalid configuration does not say which database to reach: only the journal talks about it. An unreachable database does not prevent the program from running: the journal says its start was not noted in the database.

## Crash reports

When a MachinCast program crashes, it leaves a **crash report** in `/var/log/machincast/crash-dump/`, with the logs ([#381](https://github.com/dascritch/machincast/issues/381)), or, on a machine where this directory does not exist, in `crash-dump/` of the MachinCast directory; if it cannot write in either, in `/tmp/machincast/crash-dump/`, emptied when the machine restarts ([#342](https://github.com/dascritch/machincast/issues/342)). The journal reports it: `crash report written: /var/log/machincast/crash-dump/Machin_player-2026-11-09T14-03-12-4242.txt`. The name gives the program, the time of its start and its process number, the same as in the log.

This report is made for the developers: **attach it to the ticket** that reports the problem. It contains:

- the program, its version, its options, the time of its start and that of the crash;
- the Python stack;
- what PostgreSQL, GStreamer or the system answered, if they are involved, and the versions of the tools;
- for `Machin indexer`, the file it was examining;
- for `Machin interface`, the on-air and pre-listen sound cards, the output of `wpctl status`, the tab shown and the sound in pre-listen;
- for `Machin player`, the on-air sound card, the output of `wpctl status`, and the previous sounds, the one on air and the next 5 announced: event, sequence, bank, artist and title, file.

A program that stops suddenly, on a GStreamer or Qt error, or killed by `kill -9`, cannot write its whole report: it only leaves the stack of its threads. `Machin` completes it right after ([#413](https://github.com/dascritch/machincast/issues/413)); deprived of power, its **next launch** completes it. Its end then says `End: unknown`, and it gives what can still be found: the versions, the sound cards of the configuration file and the output of `wpctl status` for the broadcast and the interface, then the last lines of the program's journal, which say what was playing, the file the indexing was analysing, the tab shown or the sound in pre-listen. Launched in a terminal, a program does not write to the journal: these lines are then missing. Reports pile up: erase them when the ticket is dealt with. A hidden file ending with `.en-cours` is the report of a program still running; do not erase it.
