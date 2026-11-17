# MachinCast

*[Version française](README.fr.md)*

**Version 0.9.0**, released on 2026-10-28, first published version, ahead of 1.0: [what it brings](RELEASE.md), and [its archive](https://github.com/dascritch/machincast/releases/tag/v0.9.0).

Automated audio playout system for radio continuity, on Linux: it keeps the station on air outside live shows, from banks of sounds, external *feeds* and scheduled events. The service tolerates failing sources, has fallback scenarios, and keeps its business services apart. Sound files are immutable, any treatment is done without modifying them. 

![a discotheque](doc/banner.jpg)

MachinCast speaks English and French, following the language of the session: its interface, messages and help ([INSTALL.md](INSTALL.md#choosing-the-language), [#360](https://github.com/dascritch/machincast/issues/360)). The detailed guides are in French for now.

- **On-air team**: the [on-air guide](doc/fr/utilisateur/README.md) (French), to schedule and follow the station from the graphical interface
- **Station administrator**: [INSTALL.md](INSTALL.md) for the installation, then the [administration guide](doc/fr/administration/README.md) (French)
- **Developer**: the [development guide](doc/fr/developpement/README.md) (French), with the [functional specification](doc/fr/spec.md), [its architecture](doc/fr/architecture.md), and the [project rules](doc/fr/regles/developpement.md); [CONTRIBUTING.md](CONTRIBUTING.md) for the screens and the translations
- **When something fails**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md), the known failures, their causes and what to check

![Screenshot of the MachinCast control interface](https://github.com/dascritch/machincast/raw/main/doc/fr/captures/accueil.png)

## Features

- Management of an hourly schedule
- Management of special editions and prioritization of shows
- Management of the number of rotations and of the broadcast periods of sounds
- Relay of an external stream, with incident and back-to-live scenarios
- Detection of the start and end of a sound
- Crossfade, set globally and per sound
- Sound banks played sequentially or in fair random order, with an option against back-to-back plays
- Preview of the live feed, of programmes and of sounds
- Graphical interface independent of the on-air playout service
- Audit of the sounds
- Dead air management, with fallback to a backup programme
- Immutable audio files, real-time processing

### Coming next

- Sending sound and show names to external services
- Playing out a stream pilot
- Automated mixing of a pre-recorded show made of segments
- Audio sources input through a sound card
- Metadata mixing
- Remote recording in MP3, Ogg, M4A, DASH and HLS

## Use cases

- On-air continuity in the master control room
- Feeding the audio input of a transmitter from a stream, with a backup
- Producing an event streaming radio
- Inserting local programmes and advertising slots into a syndicated network
- Sound system of a venue open to the public

## Recommended setup

A graphical Linux system, with the PipeWire sound server, ideally Debian or Ubuntu LTS, and two separate sound outputs, one of them a <q>good quality</q> one, for the feed to the station's final control room or its master control.

Technical requirements:

- a dedicated machine, with the playout service installed in production mode ([INSTALL.md](INSTALL.md#playout-service));
- a processor of 1 GHz at least;
- 2 GB of RAM;
- 50 GB of disk space for the sounds.

## Background

I am a volunteer host at [Radio &lt;FMR&gt;](https://radio-fmr.net), a community radio station in Toulouse, France. \
At one time I was in charge of the station's technical maintenance and of training its volunteers. I currently produce [CPU Carré Petit Utile, a show about technology](https://cpu.pm), besides being a [software solutions architect](https://dascritch.com). I was recently asked to review the station's production chain, which runs on a very tight budget.

Our station uses minimal radio automation software to run its continuous music feed and its outside broadcasts. But this software is old, no longer maintained, proprietary, riddled with bugs, unergonomic, and badly lacks some features.

For more than 15 years we have tried to move to one tool after another. Either they were too complicated, or the supposedly free tools closed up and became SaaS offerings.

I thought it simpler to write such a tool from scratch, knowing our practices, our equipment, the missing features and the most common handling mistakes of the people who run it perfectly well. The tool does not produce a stream directly: the audio output of a professional sound card (balanced analog XLR, SPDIF or AES3) goes to a final control room, and to technical tools for the DAB+ and RDS displays.

If, as a radio station, another organization or an individual, you have decided to install this software, please do get in touch to talk about your experience, your use case, and the setup you fitted it into.

## Authors

- [Xavier Mouton-Dubosc aka `dascritch`](https://dascritch.com)
- Claude.AI

Building code with and by an AI is [part of a future episode of CPU, and will be documented as such](https://cpu.pm). The code was written by Claude.AI under strong code quality constraints (TDD, BDD, E2E, failure tolerance, incident recovery, formatting).

## License

[GPLv3](LICENSE)

© [Xavier Mouton-Dubosc aka DaScritch](https://dascritch.com) for [Radio &lt;FMR&gt;](https://radio-fmr.net)

## Tribute

To those who have hung up the microphone for good, and who helped create our station's sound:

 - Patrick Chabouté "Docteur rock"
 - Pascal Bouche "Raskal"
 - Fabrice Serin "DJ Tro"

To the hosts, volunteers, supporters, and to the artists past and future who have kept Radio &lt;FMR&gt; on air.

Grown with ♡ in Toulouse, France.
