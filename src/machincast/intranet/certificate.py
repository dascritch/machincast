"""Le certificat TLS de l'intranet (https://github.com/dascritch/machincast/issues/538).

L'intranet n'écoute qu'en HTTPS, même joint par une simple adresse IP de sous-réseau. Sans certificat donné
(intranet.certificate et intranet.key), Machin intranet en génère un auto-signé, par la commande openssl du système :
une clé EC P-256, valable 825 jours, au nom du poste, de son nom de domaine interne s'il en a un, et de chacune de ses
adresses IP. Il est refait quand il ne couvre plus une adresse du poste, après un changement d'adresse en DHCP, ou
qu'il expire dans moins de 30 jours. Un certificat donné n'est jamais touché.

Le navigateur du poste distant avertit à la première connexion, le certificat n'étant signé par aucune autorité :
l'empreinte que donne fingerprint() se vérifie au pupitre.
"""

import ipaddress
import logging
import os
import subprocess
from dataclasses import dataclass
from pathlib import Path

from machincast import created_files
from machincast.i18n import _

log = logging.getLogger(__name__)

CERTIFICATE = "certificate.pem"
KEY = "key.pem"
DAYS = 825
"""La validité d'un certificat généré : la plus longue qu'acceptent les navigateurs pour un certificat de serveur."""
RENEWAL = 30 * 24 * 3600
"""Secondes avant son expiration où un certificat généré est refait."""
TIMEOUT = 60


@dataclass(frozen=True)
class Pair:
	"""Un certificat et sa clé privée."""

	certificate: Path
	key: Path


def default(directory: Path) -> Pair:
	return Pair(directory / CERTIFICATE, directory / KEY)


def subject_names(names: list[str], addresses: list[str]) -> str:
	"""L'extension subjectAltName : chaque nom, puis chaque adresse IP."""
	entries = []
	for name in names:
		entries.append(f"DNS:{name}")
	for address in addresses:
		entries.append(f"IP:{address}")
	return ",".join(entries)


def generate(pair: Pair, names: list[str], addresses: list[str]) -> None:
	"""Un certificat auto-signé, et sa clé, lisible du seul compte : écrits à côté, puis mis en place."""
	pair.certificate.parent.mkdir(parents=True, exist_ok=True)
	key = pair.key.with_name(f".{pair.key.name}.new")
	certificate = pair.certificate.with_name(f".{pair.certificate.name}.new")
	common_name = (names[:1]) or (addresses[:1])
	command = [
		"openssl",
		"req",
		"-x509",
		"-newkey",
		"ec",
		"-pkeyopt",
		"ec_paramgen_curve:prime256v1",
		"-nodes",
		"-days",
		str(DAYS),
		"-subj",
		f"/O=MachinCast/CN={common_name[0]}",
		"-addext",
		f"subjectAltName={subject_names(names, addresses)}",
		"-addext",
		"basicConstraints=critical,CA:FALSE",
		"-addext",
		"keyUsage=critical,digitalSignature",
		"-addext",
		"extendedKeyUsage=serverAuth",
		"-keyout",
		str(key),
		"-out",
		str(certificate),
	]
	mask = os.umask(0o077)
	try:
		subprocess.run(command, capture_output=True, text=True, check=True, timeout=TIMEOUT)
	finally:
		os.umask(mask)
	key.chmod(0o600)
	# Jamais un fichier qu'il n'a pas créé ; le certificat et sa clé sont à sauvegarder
	# (https://github.com/dascritch/machincast/issues/652).
	created_files.check(pair.key)
	created_files.check(pair.certificate)
	key.replace(pair.key)  # fichier de MachinCast : la clé générée, à sa place
	certificate.replace(pair.certificate)  # fichier de MachinCast : le certificat généré, à sa place
	created_files.record([pair.certificate, pair.key])
	log.info(_("intranet certificate generated: {path}").format(path=pair.certificate))


def covered(pair: Pair, addresses: list[str]) -> bool:
	"""Le certificat existe, avec sa clé, couvre chaque adresse, et n'expire pas avant RENEWAL."""
	if (not pair.certificate.is_file()) or (not pair.key.is_file()):
		return False
	try:
		names = subprocess.run(
			["openssl", "x509", "-in", str(pair.certificate), "-noout", "-ext", "subjectAltName"],
			capture_output=True,
			text=True,
			check=True,
			timeout=TIMEOUT,
		).stdout
		lasting = subprocess.run(
			["openssl", "x509", "-in", str(pair.certificate), "-noout", "-checkend", str(RENEWAL)],
			capture_output=True,
			text=True,
			check=False,
			timeout=TIMEOUT,
		)
	except (OSError, subprocess.SubprocessError):
		return False
	if lasting.returncode != 0:
		return False
	listed = set()
	for entry in names.replace("\n", ",").split(","):
		kind, _separator, value = entry.strip().partition(":")
		if kind == "IP Address":
			listed.add(ipaddress.ip_address(value.strip()))
	for address in addresses:
		if ipaddress.ip_address(address) not in listed:
			return False
	return True


def ensure(pair: Pair, names: list[str], addresses: list[str]) -> bool:
	"""Le certificat généré est là, et couvre le poste ; dit s'il a fallu le refaire."""
	if covered(pair, addresses):
		return False
	generate(pair, names, addresses)
	return True


def fingerprint(certificate: Path) -> str:
	"""L'empreinte SHA-256 du certificat, « AB:CD:… », à comparer à celle qu'affiche le navigateur ; vide, illisible."""
	try:
		result = subprocess.run(
			["openssl", "x509", "-in", str(certificate), "-noout", "-fingerprint", "-sha256"],
			capture_output=True,
			text=True,
			check=True,
			timeout=TIMEOUT,
		)
	except (OSError, subprocess.SubprocessError):
		return ""
	return result.stdout.strip().partition("=")[2]
