"""Les noms et les adresses du poste, pour le certificat de l'intranet et l'adresse à donner
(https://github.com/dascritch/machincast/issues/538).

Un poste de studio n'a souvent pas de nom de domaine interne, même en DHCP : l'intranet se joint alors par l'adresse IP
de sous-réseau, 10.0.0.12 par exemple ; le certificat la nomme.
"""

import ipaddress
import json
import logging
import socket
import subprocess

from machincast.i18n import _

log = logging.getLogger(__name__)

LOOPBACK = "127.0.0.1"
COMMAND = ["ip", "-json", "address", "show"]
"""Les adresses de chaque interface, par iproute2, en JSON."""


def addresses(command: list[str] = COMMAND) -> list[str]:
	"""Les adresses IP du poste, IPv4 d'abord, sans celles de lien local ; 127.0.0.1 en dernier, pour le poste lui-même."""
	found: list[str] = []
	try:
		result = subprocess.run(command, capture_output=True, text=True, check=True, timeout=5)
		interfaces = json.loads(result.stdout)
	except (OSError, subprocess.SubprocessError, ValueError) as error:
		log.info(_("addresses of the computer unreadable by iproute2, guessed: {error}").format(error=error))
		interfaces = [{"addr_info": _guessed()}]
	for interface in interfaces:
		for entry in interface.get("addr_info", []):
			local = str(entry.get("local", ""))
			if (_kept(local)) and (local not in found):
				found.append(local)
	ipv4: list[str] = []
	ipv6: list[str] = []
	for address in found:
		if ipaddress.ip_address(address).version == 4:
			ipv4.append(address)
		else:
			ipv6.append(address)
	return [*ipv4, *ipv6, LOOPBACK]


def _guessed() -> list[dict[str, str]]:
	"""Sans iproute2 : les adresses du nom d'hôte, et celle par où le poste sort vers un sous-réseau privé, sans rien
	envoyer (une socket UDP connectée n'émet aucun paquet)."""
	guessed = []
	try:
		for *_rest, address in socket.getaddrinfo(socket.gethostname(), None):
			guessed.append({"local": str(address[0])})
	except OSError:
		pass
	with socket.socket(socket.AF_INET, socket.SOCK_DGRAM) as probe:
		try:
			probe.connect(("10.255.255.255", 1))
			guessed.append({"local": str(probe.getsockname()[0])})
		except OSError:
			pass
	return guessed


def _kept(address: str) -> bool:
	"""Une adresse à nommer : ni boucle locale, ni lien local, ni illisible."""
	try:
		parsed = ipaddress.ip_address(address)
	except ValueError:
		return False
	return (not parsed.is_loopback) and (not parsed.is_link_local)


def names() -> list[str]:
	"""Les noms du poste : son nom d'hôte, et son nom de domaine interne, s'il en a un ; « localhost »."""
	found: list[str] = []
	host = socket.gethostname()
	qualified = socket.getfqdn()
	for name in (qualified, host):
		if (name != "") and (name not in found) and (not name.startswith("localhost")):
			found.append(name)
	found.append("localhost")
	return found


def domain_name(found: list[str]) -> str | None:
	"""Le nom de domaine interne du poste, parmi ses noms : un nom à point, hors localhost et .localdomain."""
	for name in found:
		if ("." in name) and (not name.endswith(".localdomain")) and (not name.startswith("localhost")):
			return name
	return None


def to_give(address: str, port: int) -> list[str]:
	"""Les adresses à donner aux postes distants : celle d'écoute, ou, si elle les écoute toutes, le nom de domaine
	interne du poste, s'il en a un, puis chacune de ses adresses."""
	hosts = [address]
	if ipaddress.ip_address(address).is_unspecified:
		hosts = []
		domain = domain_name(names())
		if domain is not None:
			hosts.append(domain)
		for found in addresses():
			if found != LOOPBACK:
				hosts.append(found)
	shown = []
	for host in hosts:
		written = host
		if ":" in host:
			written = f"[{host}]"
		shown.append(f"https://{written}:{port}/")
	return shown
