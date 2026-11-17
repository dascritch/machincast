# Indexing: Machin indexer

[Administration guide](README.md) › Indexing

- [What Machin indexer does](#what-machin-indexer-does)
- [Feeding a bank](#feeding-a-bank)
- [Quick indexing and full audit](#quick-indexing-and-full-audit)
- [Verdicts of the check of a file](#verdicts-of-the-check-of-a-file)
- [States of a sound](#states-of-a-sound)
- [Tags and metadata](#tags-and-metadata)
- [Silence detection](#silence-detection)
- [What the indexing shows](#what-the-indexing-shows)

## What Machin indexer does

`Machin indexer` does two things, in this order:

1. it records the files put in the directories of the banks, and places them in their bank;
2. it checks that the files of the sounds are present and healthy, updates their duration and their tags, and changes their state if needed.

It never modifies the sound files themselves, and never deletes a sound from the database.

It is launched from a terminal, or from the **Maintenance** menu of the interface ([Launching the indexing from the interface](../utilisateur/sonores.md#indexing-from-the-interface)), which does exactly the same work.

## Feeding a bank

Feeding a bank comes down to putting files in one of its directories, then launching `Machin indexer` ([#9](https://github.com/dascritch/machincast/issues/9)). The directories of a bank are chosen in [its card](../utilisateur/sonores.md#card-of-a-bank), in the interface ([#31](https://github.com/dascritch/machincast/issues/31)); a bank can have several, and the same directory can feed several banks.

- **Subdirectories**: they are all browsed, in the order of their name. A symbolic link to another directory is not followed, to avoid loops; the directory of a bank can, for its part, be a link.
- **Formats**: `.mp3`, `.m4a`, `.aac`, `.ogg`, `.flac`, `.wav`, whether the extension is written in lower or upper case. The other files (covers, texts, `.mp4` videos…) are ignored, AIFF (`.aiff`, `.aif`) included: it is not supported, because of a GStreamer defect (see [AIFF files: not supported](diffusion.md#aiff-files-not-supported)).
- **Hidden files**: a file or a directory whose name starts with a dot is ignored, like the `._*.mp3` files macOS writes on a shared disk.
- **New file**: it becomes a sound in the `preview` state, added **at the end of the list** of the bank, then decoded in the same indexing. The files of the same run are added in the order of their path.
- **File already known**: it is never recorded twice, even found by several banks. It is added at the end of the list of each bank it is not a member of yet.
- **Sound removed by hand from a bank**: as long as its file stays in one of the directories of the bank, the next indexing **puts it back**, at the end of the list. To remove it for good, the file must be moved out of its directories. The [card of the bank](../utilisateur/sonores.md#card-of-a-bank) reminds of it on removal.
- **Durations of the bank** ([#195](https://github.com/dascritch/machincast/issues/195)): a bank that has a minimum or maximum duration ([card of the bank](../utilisateur/sonores.md#card-of-a-bank)) only keeps the sounds within its durations, bounds included.
  - A sound already known, of known duration, outside its durations, is not added to it, even if its file is in one of its directories.
  - A new file, or a sound of duration still unknown, only enters it once decoded, at the end of the indexing, and only if it is within its durations ([#210](https://github.com/dascritch/machincast/issues/210)). Otherwise, it never goes through it: no line, no attachment, no removal in the report. The same directory can thus feed a bank of short jingles and a bank of long songs without each file being announced as removed from the other. If the indexing is stopped before decoding it, its duration stays unknown and it enters.
  - **Each indexing**, quick or full, removes from the bank the sounds that were already there, of known duration, which are outside its durations, **even added by hand**: tightened durations apply from the next indexing. `Machin indexer --sound N` does it for this single sound. A stopped indexing removes nothing, nor does the check of the files added from the interface.
  - The duration compared is the full duration of the file, even typed by hand in the card of the sound, never that without its silences. A sound of unknown duration, such as a stream, is never removed.
  - A removed sound stays in the database, in its other banks, sequences and events, and its file is not touched. Each removal has its line ([What the indexing shows](#what-the-indexing-shows)).
  - A card of the bank open during the indexing puts the sound back on saving; the next indexing removes it again.
- **Directory not found**: it is reported on the error output, with the name of the bank, and the other banks are indexed normally. An unreadable subdirectory is reported the same way.
- **Moved file**: at its new location, it is a new sound; the old one moves to the `missing` state.

## Quick indexing and full audit

| Command | What is checked |
| --- | --- |
| `Machin indexer` | **Quick indexing**, by default. Are decoded, and their tags read, the sounds in the `preview` state, that is newly found, and those whose file has changed since its last check: its modification date or its size differs ([#10](https://github.com/dascritch/machincast/issues/10)). A pre-recorded show replaced under the same name, for instance synchronised from another machine, is thus checked again: new duration, new tags, except the fields typed by hand. For the others, only the presence of the file is verified: a file that has disappeared is spotted all the same, and its sound becomes `missing`. A moved file is recorded as a new sound, at its new location, if it is in the directory of a bank. |
| `Machin indexer --full-audit` | **Full audit**: the sounds of file type are decoded in full. It is it, and it alone, that measures the silences at the start and the end of each file ([Silence detection](#silence-detection)). It does not decode a sound **already audited at the same silence threshold, whose file has not changed since** ([#206](https://github.com/dascritch/machincast/issues/206)): a line counts them, `120 sounds already audited at the -40 dB threshold, with unchanged files: not decoded; --force decodes all the sounds`. It thus stays short on a large library, and redoes everything after a change of the silence threshold. To launch after the first indexing, then from time to time. |
| `Machin indexer --full-audit --force` | **Forced full audit**: all the sounds of file type are decoded, even already audited and unchanged. It is this one that spots a file damaged after its audit without its date or its size having changed, a disk corruption for instance. `--force` without `--full-audit` is refused with code 2. |
| Audit requested from the interface | **A few sounds in full**, without auditing the whole library ([#114](https://github.com/dascritch/machincast/issues/114)): the right-click in the Sounds or Banks lists marks the chosen sounds, and the **next indexing, even a quick one**, decodes them in full and measures their silences, then erases the mark; a sound already audited at the same threshold, with an unchanged file, is not decoded again ([#206](https://github.com/dascritch/machincast/issues/206)) ([Acting on several sounds or banks](../utilisateur/listes.md#acting-on-several-sounds-or-banks)). |
| `Machin indexer --full-audit --sound N` | **A single sound**, number N, decoded in full ([#181](https://github.com/dascritch/machincast/issues/181)): no browsing of the directories, no audit document; its anomalies are shown on the error output. It takes no lock: it runs even during a quick indexing and a full audit ([#401](https://github.com/dascritch/machincast/issues/401)). An unknown sound, or a stream, is refused with code 1. This is how `Machin player` has the sound it is going to play checked, at the last moment ([Broadcast: Machin player](diffusion.md#what-machin-player-does)). Without `--full-audit`, the sound is only decoded if it is in preview or if its file has changed; with it, only if it has not already been audited at the same threshold, with an unchanged file, except with `--force`. |
| `Machin indexer --window` | The same indexing, quick or full (with `--full-audit`), which shows its log in a window instead of the terminal: this is how the interface launches it ([Launching the indexing from the interface](../utilisateur/sonores.md#indexing-from-the-interface)). A graphical display is needed. |

**With the playout service** ([#455](https://github.com/dascritch/machincast/issues/455)), the quick indexing runs every hour, and the full audit every day, after the purge, at the hour of `schedule.daily`, 10:00 by default ([Playout service](../../../INSTALL.md#playout-service)); without a service, or with `--no-timers`, they are launched by hand or from the interface.

**A single quick indexing and a single full audit at a time** on a database ([#401](https://github.com/dascritch/machincast/issues/401)), whether launched from a terminal, the interface or another machine: a second indexing of the same mode stops at once, without touching anything, with code 3 ([#455](https://github.com/dascritch/machincast/issues/455)) and the message `indexing refused: another quick indexing is running on this database`, or `indexing refused: another full audit is running on this database`. It can be launched again once the first is finished. A quick indexing and a full audit, for their part, run together; if they find the same new file, it is recorded only once. `--sound` takes no lock.

The decoding is done without playing the sound, much faster than real time: about ten minutes of sound in less than a second. A full audit of a large library can still take time.

Streams are never checked.

## Verdicts of the check of a file

Before decoding it, the indexer reads the **real type** of the file in its first bytes, with libmagic, without trusting its extension ([#121](https://github.com/dascritch/machincast/issues/121)). This type is recorded in the database, for instance `audio/mpeg`, `audio/flac`, or `video/mp4` for an `.m4a`. A type that is not sound (text, image, PDF…) gives the `unsupported` verdict at once, without decoding. A type that libmagic does not recognise, such as an empty file, lets the decoding decide.

Each file examined receives one of these verdicts:

| Verdict | Meaning |
| --- | --- |
| `healthy` | The file decodes entirely. Its decoded duration, its modification date and its size are recorded. |
| `damaged` | The file decodes, but data is missing: a break in the continuity of the sound, or a decoded duration shorter than the one announced by the file's header (truncated file, lost frames). |
| `unsupported` | The type of the file is not sound, whatever its extension: a text or an image renamed `.mp3`, for instance. The file is not decoded, and the problem gives its type (« of type text/plain, this is not a sound file »). |
| `unreadable` | The file is not sound, it is empty or its container is broken, no sound could be decoded, or the decoding no longer progresses for 30 seconds (disk or network share blocked). |
| `not found` | No file at the recorded location: it was deleted or moved. |

A decoding that produces no sound in 2.5 seconds is started again from the beginning, up to six times: a sleeping network disk thus has 15 seconds to answer, and an AIFF file already in the database, whose start GStreamer sometimes blocks, is not wrongly declared unreadable ([#280](https://github.com/dascritch/machincast/issues/280)). This GStreamer defect is known and followed: see [AIFF files: not supported](diffusion.md#aiff-files-not-supported).

Until the fix of [#149](https://github.com/dascritch/machincast/issues/149), an indexing of more than a few hundred files exhausted the file descriptors of the system: the console repeated `GStreamer-CRITICAL` messages (`gst_bus_timed_pop_filtered`, `gst_poll_get_read_gpollfd`), and the following files, even healthy, were declared `unreadable` (« decoding blocked at the start »). After the update, a **full audit** decodes them again: the healthy sounds moved to `corrupt` become `active` again, and the report counts them among the reinstated ones. These messages should no longer appear; if they come back, it is to be reported in a ticket.

A few defects escape the check: altered bytes in a WAV, which has neither checksum nor frames; a WAV, an Ogg, an MP3 without a duration in its header or a raw AAC (`.aac`), truncated, which decodes as a shorter but healthy file.

## States of a sound

| State | Meaning | Playable | How it leaves it |
| --- | --- | --- | --- |
| `preview` | File newly found, not decoded yet. | no | By the indexer, at the first healthy decoding: it becomes `active`. |
| `active` | Sound in service. | yes, within its broadcast period and under its maximum of plays | — |
| `disabled` | Taken off air by a human choice, in the interface. | no | Through the interface only. |
| `expired` | Maximum of plays reached, or broadcast period over: set by `Machin player` ([#18](https://github.com/dascritch/machincast/issues/18)). | no | Through the interface only. |
| `corrupt` | File `damaged` or `unreadable`. | no | Automatically, when the indexer finds the file healthy again: it becomes `active` again. |
| `unsupported` | File whose type is not sound ([#121](https://github.com/dascritch/machincast/issues/121)). | no | Automatically, when the file is replaced by real sound: the next indexing decodes it, and it becomes `active` again. The interface can also move it to `active` or `disabled`. |
| `missing` | File `not found`. | no | Through the interface only. A moved file is indexed again as a new sound. |

The indexer only changes the state of a sound in `preview`, `active`, `corrupt` or `unsupported`:

| State before | File `healthy` | File `damaged` or `unreadable` | File `unsupported` | File `not found` |
| --- | --- | --- | --- | --- |
| `preview`, `active`, `corrupt`, `unsupported` | `active` | `corrupt` | `unsupported` | `missing` |
| `disabled`, `expired`, `missing` | unchanged | unchanged, anomaly reported | unchanged, anomaly reported | unchanged, anomaly reported |

The report counts separately the sounds moved to `unsupported`, and counts among the reinstated ones those that become `active` again.

The indexer never deletes a sound from the database.

## Tags and metadata

For a `healthy` file, the indexer reads the tags of the file during the decoding, and cleans them like the texts typed in the interface ([#108](https://github.com/dascritch/machincast/issues/108), [Graphical interface](commandes.md#graphical-interface-machin-interface)): ID3 (MP3), Vorbis comments (Ogg, FLAC), MP4 atoms (M4A) and INFO chunk (WAV, which only bears the artist, the title, the album, the genre and the year).

| Field of the sound | Tag read |
| --- | --- |
| `artist` | artist, truncated to 255 characters |
| `title` | title, truncated to 255 characters |
| `year` | year of the release date. A timestamp with a time, such as the creation date some M4A files announce, is never taken for the year of the song. |
| `album` | album |
| `album_artist` | album artist |
| `genre` | genre |
| `composer` | composer |
| `label` | organisation (Vorbis `ORGANIZATION`) or publisher (ID3 `TPUB`) |
| `track` | track number |

The fields follow the tags of the file: a tag removed from the file empties the field at the next run. **A field changed by hand in the interface is never overwritten again** by the indexer ([Card of a sound](../utilisateur/sonores.md#card-of-a-sound)). The tags of a defective file are not read, and the values in the database stay as they are.

## Silence detection

A file can start or end with silence: a passage under the threshold, a breath, the end of a reverb. Not to hear them on air, the broadcast can play a sound without them ([#146](https://github.com/dascritch/machincast/issues/146)). **The file is never modified**: only the durations of its silences are noted in the database ([Sound files are never modified](configuration.md#sound-files-are-never-modified)).

- **Measure**: the [full audit](#quick-indexing-and-full-audit), `Machin indexer --full-audit`, measures the peak level of each 10 ms slice of each healthy file, on its loudest channel. The **detected start** is the silence before the first slice that reaches the threshold; the **detected end**, the silence after the last one, counted from the end of the file. The last-moment analysis of `Machin player` is a full audit: it measures them too. The quick indexing does not measure them.
- **Threshold**: `silences.threshold` in `machincast.toml`, set in the [preferences](../utilisateur/prise-en-main.md#preferences), « Crossfades » page: from -100 dB included to 0 dB excluded, -40 dB by default, 0 dB being full scale. Changing it in the preferences launches `Machin indexer --window --full-audit` at once ([#401](https://github.com/dascritch/machincast/issues/401)); changed by hand in `machincast.toml`, a full audit must be launched by hand, because `Machin player` does not have a sound audited for a changed threshold. A file that never reaches the threshold has no detected silence, and is played in full. The section used to be called `[blancs]`: still read, it makes a warning be written to the journal, and the preferences rename it `[silences]` ([#291](https://github.com/dascritch/machincast/issues/291)).
- **When the detection applies**: never by default. A sound is played without its silences if its [card](../utilisateur/sonores.md#card-of-a-sound) enables it, or if the [bank](../utilisateur/sonores.md#card-of-a-bank) that provided it enables it. A sound placed directly in an event or a sequence therefore follows its own setting. Streams are never concerned.
- **Playing**: its [crossfades](diffusion.md#audio-output) are placed around its detected start and end ([#234](https://github.com/dascritch/machincast/issues/234)): by default, the fade-in ends at the detected start, and the fade-out starts at the detected end; « starts », « is under way » or « ends » are set in the [preferences](../utilisateur/prise-en-main.md#preferences) (`crossfades.fade_in_position`, `crossfades.fade_out_position`), for all sounds. Playback extends into the silences as far as the fades overflow into them, without ever leaving the file. Its duration on air is that of this played part. The estimated time of the next sound, the airplay and the [simulation](diffusion.md#simulating-the-broadcast) follow these durations.
- **Without detected silence**: a side without detected silence is not trimmed. A sound never audited, for instance added by a quick indexing, is therefore played in full, even if the detection applies: launch a full audit after adding sounds or enabling the detection. Silences that, together, would leave nothing of the sound are ignored.
- **Correction by hand**: the detected start and end are corrected in the card of the sound; the full audit no longer changes them afterwards.
- **What does not take it into account**: the minimum and maximum durations of a bank ([#147](https://github.com/dascritch/machincast/issues/147)) are compared with the full duration of the file.

## What the indexing shows

One line per sound indexed, as the indexing goes ([#120](https://github.com/dascritch/machincast/issues/120)), with the path of the file and its status. On the standard output, the files found in the directories of the banks, then each file decoded healthy, with the name of the sound when its tags give one, and what its state becomes, then the new files of duration still unknown, once decoded, in only the banks whose durations they respect, or alone if they respect none ([#210](https://github.com/dascritch/machincast/issues/210)), then each sound already a member of a bank, removed because it is outside its durations ([#195](https://github.com/dascritch/machincast/issues/195)):

```text
2026-10-15T08:15:00+02:00 /musique/jingles/intro.flac: new sound, added to bank Jingles
2026-10-15T08:15:00+02:00 /musique/titres/cafe.flac: attached to bank Nuit
2026-10-15T08:15:00+02:00 /musique/jingles/intro.flac: analysis…
2026-10-15T08:15:00+02:00   healthy, Radio Machin – Générique; sound now active
2026-10-15T08:15:00+02:00 /musique/titres/cafe.flac: analysis…
2026-10-15T08:15:00+02:00   healthy, Les Gaufres – Café à minuit; state active kept
2026-10-15T08:15:00+02:00 /musique/titres/aube.flac: analysis…
2026-10-15T08:15:00+02:00   healthy, Aube – Matin clair; sound now active
2026-10-15T08:15:00+02:00 /musique/titres/aube.flac: new sound, added to bank Nuit
2026-10-15T08:15:00+02:00 /musique/titres/mix.flac: removed from bank Nuit, duration 1:02:05 longer than its maximum, 8:00
```

Each analysis opens with the path of the file, `analysis…`, when it starts: if the indexing crashes in the decoder, the last of these lines says on which file ([#413](https://github.com/dascritch/machincast/issues/413)). Its result follows, indented, without repeating the path. In quick indexing, a sound that is neither new nor in preview is not decoded, and therefore has no line, unless its file has disappeared. The result of a defective file, with the problem and its consequence, goes to the error output; in a terminal, it follows the line that opens its analysis:

```text
2026-10-15T08:15:00+02:00 /musique/jingles/intro.mp3: analysis…
2026-10-15T08:15:00+02:00   damaged: 2 continuity break(s) while decoding, some data was lost; sound now corrupt
2026-10-15T08:15:00+02:00 /musique/fond/nappe.flac: analysis…
2026-10-15T08:15:00+02:00   not found: no file at this location; state disabled kept
```

An unexpected error during the check of a sound, or an examination that lasts more than **10 minutes** (file on a blocked network share, decoder that no longer gives control back), is an **incident** ([#401](https://github.com/dascritch/machincast/issues/401)): the sound is left as it is, without changing state or check date, and the indexing moves on to the next. The incident is reported on the error output, and in the audit document, with the `incident` verdict:

```text
2026-10-15T08:15:00+02:00 /musique/titres/long.flac: analysis…
2026-10-15T08:15:00+02:00   incident, check abandoned after 10 minutes; sound left as it is
```

The report then ends with the number of incidents (`; 1 incident`). A sound in incident is taken up again at the next indexing; an incident that comes back on the same file is to be examined by hand. The sounds are to be kept on a local disk of the machine: a network share can block their reading, at indexing as on air.

Then the report, on the standard output:

```text
2026-10-15T08:15:00+02:00 quick indexing: 3 new sounds, 1 attachment, 0 removals; 3 sounds checked; 1 corrupt, 0 unsupported, 1 missing, 0 reinstated, 3 out of preview
```

The new sounds are the files recorded for the first time; the attachments, the sounds already known added to a bank they were not a member of; the removals, the sounds already members of a bank, removed because they are outside its durations ([Feeding a bank](#feeding-a-bank)). The sounds checked are those that were decoded; the other numbers count the changes of state.

Finally, the path of the **audit document** of the run ([#11](https://github.com/dascritch/machincast/issues/11)):

```text
2026-10-15T08:15:00+02:00 audit document: /tmp/machincast-audit-2026-10-15T08:15:00.csv, /tmp/machincast-audit-2026-10-15T08:15:00.html
```

Each indexing, quick or full, launched from a terminal or the interface, writes this document in `/tmp`, in two formats: a `.csv` for a spreadsheet (separated by semicolons) and an `.html` for a browser. It is named with the local date and time of its launch. It only lists the **anomalies**, one line per defective file: date of the run, path of the file, verdict (`damaged`, `unreadable`, `not found`, `unsupported`, `incident`), problem and consequence for the sound. Normal operations do not appear. The last line of the CSV, with the `report` verdict, bears the report of the run; without anomaly, it is the only one. Bank directories not found stay on the error output. The document is not written when the indexing is interrupted (missing decoder, lost database, another indexing of the same mode running). If it cannot be written, the indexing reports it on the error output and still goes to its end. `/tmp` is emptied when the machine restarts: copy elsewhere the documents to keep.

If GStreamer has no decoder for a format, the check stops and names the packages to install, without changing the state of the sounds: the file has nothing to do with it.
