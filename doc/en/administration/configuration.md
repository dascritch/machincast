# Configuration and rights

[Administration guide](README.md) › Configuration and rights

- [Configuration](#configuration)
- [Sound files are never modified](#sound-files-are-never-modified)
- [Outputs of the broadcast](#outputs-of-the-broadcast)
- [Interface settings, per account](#interface-settings-per-account)
- [Expiry duration](#expiry-duration)
- [Rights of each program in the database](#rights-of-each-program-in-the-database)

## Configuration

Each program reads its configuration from the `machincast.toml` file **of the MachinCast directory**, whatever the directory it is launched from ([#76](https://github.com/dascritch/machincast/issues/76)). `Machin --help` shows its full path. Another configuration, also placed in the MachinCast directory, is designated with `--config`.

The commented template is `machincast.exemple.toml`, and the [table of keys of the specification](../../fr/spec.md#9-configuration) (French) gives the type and the role of each one. Any unknown key is refused, to detect typing errors: the program then stops with code 2 and a message that names the file and the key, for instance:

```text
2026-10-15T08:15:00+02:00 invalid configuration: /home/xavier/machincast/machincast.toml: unknown key audio.sortei
```

The relative paths of the file (CSV, HTML and .pls outputs) are understood from the directory of the configuration file.

## Sound files are never modified

MachinCast only **reads** the sound files ([#96](https://github.com/dascritch/machincast/issues/96)). None of its programs deletes, renames, moves or replaces them, nor writes to them, whatever happens to their entry in the database:

- a sound moved to the `missing`, `disabled`, `expired` or `corrupt` state keeps its file as it is;
- a sound whose location, artist or title changes keeps its file as it is;
- a sound deleted from the database, from [its card](../utilisateur/listes.md#deleting-an-element), keeps its file: if it is still in the directory of a bank, the next indexing records it again, as a new sound in the `preview` state, then `active` once checked.

Deleting a sound file from the disk remains a human decision, taken outside MachinCast.

For the same reason, an output cannot be placed on a sound file. The configuration refuses a path of `outputs.csv`, `outputs.pls`, `outputs.html` or `player.state_socket` that ends with the extension of a sound file (`.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, `.aiff`, `.aif`, in upper as in lower case), with exit code 2:

```text
2026-10-15T08:15:00+02:00 invalid configuration: /home/xavier/machincast/machincast.toml: key outputs.csv: “musique/airplay.mp3” bears the extension of a sound file, and MachinCast never writes to a sound file
```

If an output were nevertheless to fall on such a path, it is not written: it is reported in the log by the `inaccessible output` warning, which mentions a protected sound file, and the broadcast goes on. Likewise, the state socket is then not opened: the `state socket unavailable` warning is noted, and the broadcast goes on without it. The files of a simulation always end with `.csv`, `.pls` or `.html`: whatever their name, they never replace a sound file.

## Outputs of the broadcast

`Machin player` publishes what it broadcasts on several outputs ([#19](https://github.com/dascritch/machincast/issues/19)), at the paths of the `[outputs]` section of the configuration, understood from the directory of the configuration file (by default, the `sorties` folder of the MachinCast directory, created if needed):

| Output | For whom | Content |
| --- | --- | --- |
| Standard output | team | A line `on air: artist – title (event)` at each play, and a line at each start or end of an event or a sequence, as in the log: `event start: “Journal”, show, from 20:00 to 20:30` ([#153](https://github.com/dascritch/machincast/issues/153)). |
| Error output | team | The warnings and incidents of the log, and the errors of the program. |
| CSV (`outputs.csv`) | team | One file per day, named with its date: `airplay.csv` gives `airplay-2026-10-15.csv`. One line per finished play: start, end, duration, artist, title, location, event, sequence, bank, without incident (yes or no). Separator `;`, opens directly in LibreOffice or Excel. Never rewritten. |
| `.pls` playlist (`outputs.pls`) | team | The last 100 files played, streams included, from the oldest to the most recent: to listen again to what has played. |
| HTML page (`outputs.html`) | public | The sound on air and the 20 previous ones, with the time. Static page, to publish on the station's website; it reloads on its own every 30 seconds and never shows the location of a file. |

**Hiding the artist and the title.** On the public page only, the artist and the title of a play can be hidden. The choice is made at five levels: the event, then the sequence that played the sound ([#99](https://github.com/dascritch/machincast/issues/99)), then the bank that provided it, then the sound, then `metadata.hide` in the configuration. The first level set decides: an event that says « show » prevails over a sound that says « hide ». Hidden, the artist and the title give way to the first public name set, in the same order: that of the event, then of the sequence, then of the bank; if there is none, to `metadata.public_text`. The other outputs always say everything.

An output impossible to write (folder without write permission, full disk) is reported once in the log by the `inaccessible output` warning, with the path and the error. The broadcast goes on.

## Interface settings, per account

The interface keeps, for each account, the layout of the columns of each of its tables: their order, the hidden columns and the chosen widths ([#207](https://github.com/dascritch/machincast/issues/207), [Table columns](../utilisateur/listes.md#table-columns)). It is not a setting of the machine: it is not in `machincast.toml`, but in `~/.config/machincast/vues.ini` (or `$XDG_CONFIG_HOME/machincast/vues.ini`), one section per table, such as `[liste-sonores]` or `[fiche-banque-sonores]`. Deleting this file gives all the tables of the account their original layout back; « Reset the columns », in the interface, does it for a single one. A layout kept for other columns, by a previous version of MachinCast, is forgotten.

## Expiry duration

`database.retention` ([#268](https://github.com/dascritch/machincast/issues/268)) is the duration, in whole days, 1 at least, after which [`Machin purge`](commandes.md#database-purge-machin-purge) erases from the database the airplay plays, the rows of the log, and the elements deleted or whose file has disappeared. 60 days by default; a decimal number, a text or 0 are refused (code 2). The interface also sets it, **File → Interface preferences…**, **Database** page, which writes it to the `[database]` section, and the card of a deleted element gives the day it will be erased.

```toml
[database]
retention = 90
```

## Rights of each program in the database

Each program acts in the database with its own rights: the account that launches it has access to nothing by itself, and the program assumes its PostgreSQL role from the connection. A program therefore cannot do more than what follows, even launched by an account that has the three roles.

| Program | PostgreSQL role | What it can do |
| --- | --- | --- |
| `Machin player` | `machincast_player` | Read the programming, sequences included; move a sound to `expired`; add rows to the airplay and the log, without ever modifying or deleting them. |
| `Machin indexer` | `machincast_indexer` | Read the banks and their directories; add and update sounds, place them in the banks, and remove from them those outside their durations; note the end of the browsing of each directory. It deletes no sound, and only adds its starts and ends to the log ([Starts and ends in the log](commandes.md#starts-and-ends-in-the-log)). |
| `Machin interface` | `machincast_interface` | Modify everything in the sounds, the banks, the sequences and the events; read the airplay and the log, without modifying them. |

`Machin maintenance-db`, `Machin backup-db`, `Machin restore-db` and `Machin purge` assume no role: they act as owner of the database, which the MachinCast account is. Only the purge erases rows of the airplay and the log.

The details, table by table, are in the [specification, § 3.2](../../fr/spec.md#32-rôles-et-droits) (French). Adding another account is described in [INSTALL.md](../../../INSTALL.md#adding-another-account).
