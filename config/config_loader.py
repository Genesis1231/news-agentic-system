from pathlib import Path
from typing import Any, Dict
import yaml

class ConfigLoader:
    """
    Load system configuration from a YAML file.
    """
    def __init__(
        self, 
        default_file: str | Path = Path(__file__).parent / "settings.yaml"
    ) -> None:
        self.config_file = Path(default_file)
        if not self.config_file.exists():
            raise FileNotFoundError(f"Configuration file not found: {self.config_file}")
        
        self.configuration = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from YAML file."""
        with open(self.config_file, 'r') as f:
            return yaml.safe_load(f)

    def get(self, key: str, default: Any = None) -> Any:
        """Get a configuration value by key."""
        return self.configuration.get(key, default)

# Create a global configuration instance
configuration = ConfigLoader().configuration 