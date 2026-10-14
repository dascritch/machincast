"""MachinCast : système automatisé de diffusion sonore pour radio."""

from importlib.metadata import PackageNotFoundError, version

try:
	__version__ = version("machincast")
except PackageNotFoundError:  # exécution depuis les sources sans installation
	__version__ = "0.0.0"
