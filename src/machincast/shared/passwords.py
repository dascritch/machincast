"""Les mots de passe des comptes de l'intranet et de l'API (https://github.com/dascritch/machincast/issues/537).

Un mot de passe n'est jamais gardé : seule son empreinte scrypt salée l'est, par la bibliothèque standard, sous la
forme « scrypt$n$r$p$sel$empreinte », sel et empreinte en base64. L'interface la calcule ; le serveur intranet la
vérifie, en temps constant.
"""

import base64
import hashlib
import hmac
import secrets

MINIMUM_LENGTH = 12
"""Le moins de caractères d'un mot de passe."""
PREFIX = "scrypt"
COST = 2**14
BLOCK = 8
PARALLELISM = 1
SALT_BYTES = 16
HASH_BYTES = 32
MEMORY = 64 * 1024 * 1024
"""La mémoire permise à scrypt : au-delà de ce que demandent COST et BLOCK, 16 Mio."""


def _derive(password: str, salt: bytes, cost: int, block: int, parallelism: int) -> bytes:
	return hashlib.scrypt(
		password.encode("utf-8"),
		salt=salt,
		n=cost,
		r=block,
		p=parallelism,
		maxmem=MEMORY,
		dklen=HASH_BYTES,
	)


def _text(raw: bytes) -> str:
	return base64.b64encode(raw).decode("ascii")


def acceptable(password: str) -> bool:
	"""Un mot de passe assez long."""
	return len(password) >= MINIMUM_LENGTH


def digest(password: str) -> str:
	"""L'empreinte salée d'un mot de passe, à garder en base."""
	salt = secrets.token_bytes(SALT_BYTES)
	derived = _derive(password, salt, COST, BLOCK, PARALLELISM)
	return f"{PREFIX}${COST}${BLOCK}${PARALLELISM}${_text(salt)}${_text(derived)}"


def matches(password: str, stored: str) -> bool:
	"""Le mot de passe correspond à l'empreinte gardée ; faux pour une empreinte illisible."""
	parts = stored.split("$")
	if (len(parts) != 6) or (parts[0] != PREFIX):
		return False
	try:
		cost, block, parallelism = int(parts[1]), int(parts[2]), int(parts[3])
		salt = base64.b64decode(parts[4], validate=True)
		expected = base64.b64decode(parts[5], validate=True)
		derived = _derive(password, salt, cost, block, parallelism)
	except ValueError:
		return False
	return hmac.compare_digest(derived, expected)
