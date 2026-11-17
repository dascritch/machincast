# Administration guide

*[Version française](../../fr/administration/README.md)*

This guide is for the administrator of the playout machine: it describes the MachinCast command-line programs, their configuration, their messages and their rights. It does not require knowing the code.

- **Installing, updating, uninstalling**: [INSTALL.md](../../../INSTALL.md), with the playout service and [When something goes wrong](../../../INSTALL.md#when-something-goes-wrong).
- **Using the graphical interface**, for the on-air team: the [on-air guide](../utilisateur/README.md).

The messages of the programs are shown in the language of the session; this guide quotes them in English, as an English session shows them.

## Contents

1. [Commands and messages](commandes.md): the `Machin` command, the interface, the service log, the exit codes.
2. [Configuration and rights](configuration.md): the `machincast.toml` file, the outputs of the broadcast, the protection of the sound files, the rights in the database.
3. [Indexing: Machin indexer](indexation.md): recording and checking the sound files, on the command line.
4. [Broadcast: Machin player](diffusion.md): broadcasting and simulating on the command line, the state socket, the audio output, the history and the log.

## What does not exist yet

| Missing | Ticket |
| --- | --- |
| Extending a stream whose live show overruns | [#47](https://github.com/dascritch/machincast/issues/47) |
