"""Les codes d'une application d'authentification, TOTP (RFC 6238), le second facteur de l'intranet
(https://github.com/dascritch/machincast/issues/601).

Une clé de 20 octets aléatoires, écrite en base32 sans « = » : 32 caractères, de A à Z et de 2 à 7. Un code de 6 chiffres
par pas de 30 secondes, par HMAC-SHA1, comme l'attendent les applications d'authentification courantes ; un code est
accepté s'il est celui du pas en cours, ou du pas d'avant ou d'après, pour une horloge un peu décalée.
"""

import base64
import hashlib
import hmac
import secrets
import struct
from datetime import datetime
from urllib.parse import quote

STEP = 30
"""Secondes d'un pas : un nouveau code toutes les 30 secondes."""
DIGITS = 6
SECRET_BYTES = 20
DRIFT = 1
"""Pas d'avance ou de retard acceptés, de part et d'autre du pas en cours."""


def secret() -> str:
	"""Une nouvelle clé, en base32 : 32 caractères."""
	return base64.b32encode(secrets.token_bytes(SECRET_BYTES)).decode("ascii").rstrip("=")


def step(at: datetime) -> int:
	"""Le pas de cet instant."""
	return int(at.timestamp()) // STEP


def _code(key: str, counter: int) -> str:
	raw = base64.b32decode(key + "=" * (-len(key) % 8))
	digest = hmac.new(raw, struct.pack(">Q", counter), hashlib.sha1).digest()
	offset = digest[-1] & 0x0F
	value = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
	return str(value % (10**DIGITS)).zfill(DIGITS)


def code(key: str, at: datetime) -> str:
	"""Le code de cet instant."""
	return _code(key, step(at))


def matching_step(key: str, given: str, at: datetime) -> int | None:
	"""Le pas du code saisi, espaces ignorées, s'il est celui de cet instant, à DRIFT pas près ; None sinon."""
	cleaned = given.strip().replace(" ", "")
	now = step(at)
	found = None
	for counter in range(now - DRIFT, now + DRIFT + 1):
		if hmac.compare_digest(_code(key, counter), cleaned):
			found = counter
	return found


def uri(issuer: str, name: str, key: str) -> str:
	"""L'adresse otpauth:// que lit une application d'authentification, par exemple d'un QR code."""
	label = quote(f"{issuer}:{name}", safe=":")
	return f"otpauth://totp/{label}?secret={key}&issuer={quote(issuer, safe='')}"
