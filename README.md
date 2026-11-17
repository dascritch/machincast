# MachinCast

*[Version française](README.fr.md)*

**Version 0.9.1**, released on 2026-11-17, ahead of 1.0: [what it brings](RELEASE.md), and [its archive](https://github.com/dascritch/machincast/releases/tag/v0.9.1).

Automated audio playout system for radio continuity, on Linux: it keeps the station on air outside live shows, from banks of sounds, external *feeds* and scheduled events. The service tolerates failing sources, has fallback scenarios, and keeps its business services apart. Sound files are immutable, any treatment is done without modifying them.

![a discotheque](doc/banner.jpg)

MachinCast speaks English and French, following the language of the session: its interface, messages and help ([INSTALL.md](INSTALL.md#choosing-the-language), [#360](https://github.com/dascritch/machincast/issues/360)).

- **On-air team**: the [on-air guide](doc/en/utilisateur/README.md), to schedule and follow the station from the graphical interface
- **Station administrator**: [INSTALL.md](INSTALL.md) for the installation, then the [administration guide](doc/en/administration/README.md)
- **Developer**: the [development guide](doc/fr/developpement/README.md) (French), with the [functional specification](doc/fr/spec.md), [its architecture](doc/fr/architecture.md), and the [project rules](doc/fr/regles/developpement.md); [CONTRIBUTING.md](CONTRIBUTING.md) for the screens and the translations
- **When something fails**: [TROUBLESHOOTING.md](TROUBLESHOOTING.md), the known failures, their causes and what to check

![Screenshot of the MachinCast control interface](https://github.com/dascritch/machincast/raw/main/doc/fr/captures/accueil.png)

## Use cases

- Station continuity in the master control room
- Feeding the audio input of a transmitter from a stream, with a fallback
- Producing an event-based streamed radio
- Inserting local programmes and advertising slots on a syndicated network
- Sound for a space open to the public

[What MachinCast does not do: see this chapter on its design](doc/fr/architecture.md#91-ce-que-nest-pas-machincast) (French)

## Features

- Management of a schedule
- Management of special editions and prioritisation of shows
- Management of the number of rotations and of the broadcast periods of the sounds
- Relaying an external stream, with incident and live-resumption scenarios
- Detection of the start and the end of a sound
- Crossfade set globally and per sound
- Sound banks played sequentially or in fair random order, with an option against back-to-back plays
- Pre-listen of the live output, of the programmes and of the sounds
- Graphical interface independent from the on-air playout service
- Audit of the sounds
- Handling of dead air, with a fallback programme
- Immutable audio files, real-time treatments

## Recommended setup

A graphical Linux system, with the PipeWire sound server, ideally Debian or Ubuntu LTS, and two separate sound outputs, one of them a <q>good quality</q> one, for the feed to the station's final control room or its master control.

Technical requirements:

- a dedicated machine, with the playout service installed in production mode ([INSTALL.md](INSTALL.md#playout-service));
- a processor of 1 GHz at least;
- 2 GB of RAM;
- 50 GB of disk space for the sounds.

![a side by side comparison. On the left, a service mode, in light theme in english. On the right, a test mode, in dark theme in French](doc/side_by_side.jpg)

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
