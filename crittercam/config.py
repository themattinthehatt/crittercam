"""Configuration loading and saving."""

import tomllib
import tomli_w
from dataclasses import dataclass
from pathlib import Path


CONFIG_PATH = Path.home() / '.config' / 'crittercam' / 'config.toml'


@dataclass
class Config:
    """Runtime configuration.

    Attributes:
        data_root: root directory for the image archive and database
    """

    data_root: Path

    @property
    def db_path(self) -> Path:
        """Path to the SQLite database file."""
        return self.data_root / 'db' / 'crittercam.db'


def load(config_path: Path = CONFIG_PATH) -> Config:
    """Load configuration from a TOML file.

    Args:
        config_path: path to the config file

    Returns:
        Config instance

    Raises:
        FileNotFoundError: if the config file does not exist
        KeyError: if a required key is missing from the config file
    """
    with open(config_path, 'rb') as f:
        data = tomllib.load(f)
    return Config(data_root=Path(data['data_root']))


def save(config: Config, config_path: Path = CONFIG_PATH) -> None:
    """Save configuration to a TOML file.

    Creates parent directories if they do not exist.

    Args:
        config: Config instance to save
        config_path: path to write the config file
    """
    config_path.parent.mkdir(parents=True, exist_ok=True)
    data = {'data_root': str(config.data_root)}
    with open(config_path, 'wb') as f:
        tomli_w.dump(data, f)
