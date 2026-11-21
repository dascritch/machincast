# Security of the service and application accounts

[Administration guide](README.md) › Security

*[Version française](../../fr/administration/securite.md)*

- [Principle: one account per use](#principle-one-account-per-use)
- [The accounts of the computer](#the-accounts-of-the-computer)
- [The roles in the database](#the-roles-in-the-database)
- [The sockets of Machin player](#the-sockets-of-machin-player)
- [The intranet server, open to the network](#the-intranet-server-open-to-the-network)
- [What needs an administrator](#what-needs-an-administrator)
- [The sound files](#the-sound-files)
- [Test mode, without the service](#test-mode-without-the-service)
- [Known limits](#known-limits)

## Principle: one account per use

MachinCast runs no program with more rights than it needs. Each program has its system account, and each account takes in the database only the role of its program. A mistake or a flaw in a program therefore only gives what that program can already do.

This is what `./install.sh --service` sets up, on a computer dedicated to the on-air output ([#381](https://github.com/dascritch/machincast/issues/381), [#549](https://github.com/dascritch/machincast/issues/549)). Without the service, on a trial computer, everything runs under the account that launches the programs: see [Test mode](#test-mode-without-the-service).

## The accounts of the computer

| Account | What it runs | Its groups | It reads | It writes |
| --- | --- | --- | --- | --- |
| **The MachinCast account**, the one that installs it | The interface, Machin indexer, the regular tasks (purge, indexing, audit), the database maintenance | `machincast`, `systemd-journal` | The repository, the banks, the logs of the service | Its configuration files, the backups; it owns the production and test databases |
| **`machincast`**, the broadcast service | Machin player, its PipeWire and its WirePlumber | `machincast` | The repository, `/home/machincast`, the banks that `Machin grant-read` gave it to read | `/run/machincast`, `/var/log/machincast`, `/var/lib/machincast` |
| **`machincast-intranet`**, the intranet server | Machin intranet | `machincast-intranet` only | The repository and `machincast.toml`, the database as the `machincast_intranet` role, its socket of Machin player | `/var/lib/machincast-intranet`, its certificate, and nothing else |

- `machincast` and `machincast-intranet` are system accounts, without password or shell: nobody logs in to them.
- The MachinCast account joins the `machincast` group, to read the logs of the service, pre-listen to the on-air output and drive Machin player from the interface. It also joins `systemd-journal`, to read the journal of the service.
- **`machincast-intranet` is not in the `machincast` group.** That group gives the PipeWire of the service, through which sound could be played on air without going through Machin player, as well as the logs, the crash reports and the sound files of `/home/machincast`. The intranet server needs none of these.
- `./install.sh --remove-service` removes both system accounts and their roles in the database.

## The roles in the database

MachinCast connects to PostgreSQL only through the Unix socket, with **peer** authentication: the system account is the login role, without password.

- Four **group roles**, without login, one per program: `machincast_player`, `machincast_indexer`, `machincast_interface` and `machincast_intranet`. Their rights, table by table, are in [Rights of each program in the database](configuration.md#rights-of-each-program-in-the-database).
- Each account can **take** the roles of its programs, **without inheriting their rights** (`WITH INHERIT FALSE, SET TRUE`). Connected, it has access to nothing; each program takes its role as soon as it connects.

| Account | Roles it can take |
| --- | --- |
| The MachinCast account | All four, and it owns the databases |
| `machincast` | `machincast_player` only |
| `machincast-intranet` | `machincast_intranet` only |

**Why separate accounts, and not only roles.** Taking a role bounds the queries of a program that behaves. But a hijacked program, running arbitrary code, could leave that role and get back all the rights of its account. The MachinCast account, which owns the databases, therefore never runs the server open to the network.

The `machincast_intranet` role only reads, except the sessions of the intranet, of which it only changes the validation columns. It cannot accept a connection in place of the desk: only the interface can ([#547](https://github.com/dascritch/machincast/issues/547)).

## The sockets of Machin player

Machin player publishes its state and receives requests (cutting the on-air output, interrupting, inserting, advancing the next event…) through two Unix sockets, with the same protocol.

| Socket | Directory, rights | Who connects | The requests |
| --- | --- | --- | --- |
| `/run/machincast/lecture.sock`, the state socket | `2770`, group `machincast`; the socket in `0660` | Machin player, the interface of the MachinCast account | Without an account: a request that names an API account is ignored |
| `/run/machincast-intranet/intranet.sock`, the socket of the intranet | `2750`, owned by `machincast` and the `machincast-intranet` group; the socket in `0660` | The intranet server only | Each request names the API account that makes it, mandatory |

- A socket does not separate reading from writing: whoever can connect can also send requests. That is why the intranet server has a socket of its own, rather than a place in the `machincast` group.
- Machin player believes the account of a request only on the socket of the intranet, where nobody else connects. The intranet server takes it from the session of the person logged in.
- The log of the database tells, for each on-air action requested, where it comes from (`interface` or `intranet`) and which API account made it. The name of the account stays, even once the account is deleted.

## The intranet server, open to the network

Machin intranet is the only MachinCast program that listens to the network. It is **switched off by default**, and is switched on in **File → Service settings…**, **Intranet** page ([Commands and messages](commandes.md)).

**The transport**

- HTTPS only: no answer in clear. Without a certificate given, Machin intranet generates a self-signed one, whose fingerprint the journal gives, to compare with the one the browser shows at the first connection.
- Each answer forbids the browser to come back in clear, to show the page in a frame, to load a resource from elsewhere or to keep the page in cache. A form sent from another site is refused.

**The connections**

- Only the accounts of the **API** tab connect. Passwords have at least 12 characters, and the database keeps only their salted scrypt hash.
- An unknown name, a disabled account or a wrong password get the same answer, in the same time.
- **Each connection is decided at the desk**: the orange banner of the interface tells who asks to connect, from where and with which browser. **Accept** shows a 6-digit code, to give to the person; **Refuse** closes the door. Before the acceptance, no code is even tried ([#547](https://github.com/dascritch/machincast/issues/547)).
- Five wrong codes from the same address or the same account make it wait a quarter of an hour, and an account has only two connections waiting at a time: a stolen password is not enough to force the code.
- A session lasts 12 hours by default. Changing the password of an account, or disabling it, ends all its sessions, which enabling it again does not revive ([#548](https://github.com/dascritch/machincast/issues/548)).
- The session cookie is never sent in clear, nor read by a script of the page, nor sent from another site; the database keeps only its hash.

**The partitioning of the unit** (`machincast-intranet.service`)

- The whole system is read-only, the repository and `machincast.toml` included; only its state directory, `/var/lib/machincast-intranet`, is writable.
- No personal directory is visible, no device, no kernel capability.
- Only Unix, IP and netlink sockets are allowed (netlink to read the addresses of the computer), and only the system calls of an ordinary service.
- `systemd-analyze security machincast-intranet` measures this partitioning.

Its messages go to the system journal: `journalctl -u machincast-intranet`.

## What needs an administrator

- **Installing or removing the service**, `./install.sh --service` or `--remove-service`, asks for `sudo`: accounts, units, rules and fragments of the system. install.sh runs with your own account, and asks for `sudo` only for these steps.
- **Starting, stopping or restarting** the broadcast service or the intranet server from the interface: the polkit rule allows it to the MachinCast account only, with the password of an administrator. It allows nothing else, nor on another unit.
- **Powering off, rebooting or suspending the computer** asks for the password of an administrator, from any account; the power keys, the lid and Ctrl+Alt+Del on the console are ignored ([#448](https://github.com/dascritch/machincast/issues/448)).

## The sound files

- **MachinCast never writes, renames, moves, replaces or deletes a sound file**, nor a bank directory: deleting a sound or a bank only removes its entry in the database ([#96](https://github.com/dascritch/machincast/issues/96)). See [Sound files are never modified](configuration.md#sound-files-are-never-modified).
- The only exception is moving the sound files out of a personal directory, explicitly accepted at `./install.sh --service`.
- `Machin grant-read` gives only the `machincast` account the reading of the banks, through ACLs, without changing the owner nor the rights of the group. It refuses to touch the rights of a personal directory or of a system tree (`/etc`, `/usr`, `/media`, `/mnt`…) ([#381](https://github.com/dascritch/machincast/issues/381)).
- The intranet server reads no sound file: its API only gives what is in the database.

## Test mode, without the service

Without `./install.sh --service`, on a trial computer, all programs run under the account that launches them. The **Intranet** page of the settings reminds it.

| | With the service | In test mode |
| --- | --- | --- |
| Machin player | As `machincast`, with its PipeWire | As your account, in a terminal |
| Machin intranet | As `machincast-intranet`, partitioned unit | As your account, in a terminal, without partitioning |
| Roles in the database | One per account | Your account takes each of them, but it also owns the databases |
| Sockets of Machin player | In `/run/machincast` and `/run/machincast-intranet`, to their groups | In `$XDG_RUNTIME_DIR/machincast`, private to your account |
| Messages | System journal, and `/var/log/machincast` for Machin player | The terminal, and `/var/log/machincast` if your account can write there |

The protocol of the sockets is the same: the API account stays mandatory on the socket of the intranet, and the log tells where each action comes from. Test mode is for trying MachinCast and the intranet, **not for opening the computer to the network of the radio**.

## Known limits

- The self-signed certificate is made again when an address of the computer changes, in DHCP: each browser must then accept it again, comparing its fingerprint. A certificate given by the certificate authority of the radio (`intranet.certificate` and `intranet.key`) avoids it.
- Machin intranet listens by default on all the addresses of the computer (`intranet.address`, `0.0.0.0`). On a computer that also has a public address, better limit it to the one of the network of the radio.
- The findings of the security review still to fix are followed in [#546](https://github.com/dascritch/machincast/issues/546).
