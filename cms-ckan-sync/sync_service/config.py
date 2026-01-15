"""Configuration loader for CMS-CKAN Sync Service"""

import json
import os
from dataclasses import dataclass, field
from pathlib import Path
from typing import Dict, List, Optional, Any

import yaml
from dotenv import load_dotenv


# Runtime settings file path
RUNTIME_SETTINGS_FILE = "settings.json"


@dataclass
class CKANDatasetConfig:
    """CKAN dataset configuration"""
    name: str
    title: str
    notes: str = ""
    license_id: str = "cc-by"
    tags: List[Dict[str, str]] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for CKAN API"""
        return {
            'name': self.name,
            'title': self.title,
            'notes': self.notes,
            'license_id': self.license_id,
            'tags': self.tags
        }


@dataclass
class ModelConfig:
    """Configuration for a single CMS model to sync"""
    cms_model_id: str
    ckan_dataset: CKANDatasetConfig
    field_mappings: Dict[str, str] = field(default_factory=dict)
    geometry_field: Optional[str] = None
    exclude_fields: List[str] = field(default_factory=list)
    webhook_model_keys: List[str] = field(default_factory=list)  # For webhook model key mapping


@dataclass
class Config:
    """Main configuration class"""
    # CMS settings
    cms_base_url: str
    cms_token: str

    # CKAN settings
    ckan_url: str
    ckan_token: str
    ckan_organization: str

    # Web UI settings
    web_host: str = "0.0.0.0"
    web_port: int = 8080
    web_auth_username: str = "admin"
    web_auth_password: str = ""

    # General settings
    log_level: str = "INFO"
    data_dir: str = "./data"

    # Webhook settings
    webhook_secret: str = ""  # For HMAC signature verification

    # CKAN Cookie Auth settings
    ckan_auth_enabled: bool = True
    ckan_auth_require_sysadmin: bool = True

    # Model configurations
    models: Dict[str, ModelConfig] = field(default_factory=dict)

    def get_model(self, model_id: str) -> Optional[ModelConfig]:
        """Get model configuration by ID"""
        return self.models.get(model_id)

    def get_all_model_ids(self) -> List[str]:
        """Get list of all configured model IDs"""
        return list(self.models.keys())


def _parse_model_config(model_id: str, model_data: Dict[str, Any]) -> ModelConfig:
    """Parse a single model configuration from YAML data"""
    ckan_data = model_data.get('ckan_dataset', {})
    ckan_dataset = CKANDatasetConfig(
        name=ckan_data.get('name', model_id),
        title=ckan_data.get('title', model_id),
        notes=ckan_data.get('notes', ''),
        license_id=ckan_data.get('license_id', 'cc-by'),
        tags=ckan_data.get('tags', [])
    )

    return ModelConfig(
        cms_model_id=model_data.get('cms_model_id', model_id),
        ckan_dataset=ckan_dataset,
        field_mappings=model_data.get('field_mappings', {}),
        geometry_field=model_data.get('geometry_field'),
        exclude_fields=model_data.get('exclude_fields', []),
        webhook_model_keys=model_data.get('webhook_model_keys', [])
    )


def load_config(env_file: Optional[str] = None, models_file: Optional[str] = None) -> Config:
    """
    Load configuration from environment variables and YAML files.

    Args:
        env_file: Path to .env file (optional, defaults to .env in current dir)
        models_file: Path to models.yaml file (optional, defaults to config/models.yaml)

    Returns:
        Config object with all settings loaded
    """
    # Load environment variables
    if env_file:
        load_dotenv(env_file)
    else:
        load_dotenv()

    # Determine base path for config files
    base_path = Path(__file__).parent.parent

    # Load models configuration
    if models_file is None:
        models_file = base_path / "config" / "models.yaml"
    else:
        models_file = Path(models_file)

    models: Dict[str, ModelConfig] = {}

    if models_file.exists():
        with open(models_file, 'r', encoding='utf-8') as f:
            models_data = yaml.safe_load(f) or {}

        for model_id, model_data in models_data.get('models', {}).items():
            models[model_id] = _parse_model_config(model_id, model_data)

    # Create config object
    config = Config(
        # CMS settings
        cms_base_url=os.getenv('CMS_API_BASE_URL', ''),
        cms_token=os.getenv('CMS_API_TOKEN', ''),

        # CKAN settings
        ckan_url=os.getenv('CKAN_URL', ''),
        ckan_token=os.getenv('CKAN_API_TOKEN', ''),
        ckan_organization=os.getenv('CKAN_ORGANIZATION', ''),

        # Web UI settings
        web_host=os.getenv('WEB_HOST', '0.0.0.0'),
        web_port=int(os.getenv('WEB_PORT', '8080')),
        web_auth_username=os.getenv('WEB_AUTH_USERNAME', 'admin'),
        web_auth_password=os.getenv('WEB_AUTH_PASSWORD', ''),

        # General settings
        log_level=os.getenv('LOG_LEVEL', 'INFO'),
        data_dir=os.getenv('DATA_DIR', './data'),

        # Webhook settings
        webhook_secret=os.getenv('WEBHOOK_SECRET', ''),

        # CKAN Cookie Auth settings
        ckan_auth_enabled=os.getenv('CKAN_AUTH_ENABLED', 'true').lower() == 'true',
        ckan_auth_require_sysadmin=os.getenv('CKAN_AUTH_REQUIRE_SYSADMIN', 'true').lower() == 'true',

        # Models
        models=models
    )

    return config


def validate_config(config: Config) -> List[str]:
    """
    Validate configuration and return list of errors.

    Args:
        config: Configuration to validate

    Returns:
        List of error messages (empty if valid)
    """
    errors = []

    if not config.cms_base_url:
        errors.append("CMS_API_BASE_URL is required")

    # CMS token is optional for public projects
    # if not config.cms_token:
    #     errors.append("CMS_API_TOKEN is required")

    if not config.ckan_url:
        errors.append("CKAN_URL is required")

    if not config.ckan_token:
        errors.append("CKAN_API_TOKEN is required")

    if not config.ckan_organization:
        errors.append("CKAN_ORGANIZATION is required")

    if not config.models:
        errors.append("No models configured in models.yaml")

    return errors


def get_runtime_settings_path() -> Path:
    """Get the path to runtime settings file."""
    # Default to ./data/settings.json
    data_dir = Path(os.getenv('DATA_DIR', './data'))
    data_dir.mkdir(parents=True, exist_ok=True)
    return data_dir / RUNTIME_SETTINGS_FILE


def load_runtime_config() -> Dict[str, Any]:
    """
    Load runtime configuration from settings.json.

    Returns:
        Dictionary with runtime settings, falling back to .env values
    """
    # Load .env first for defaults
    load_dotenv()

    # Default values from environment
    config = {
        "cms_url": os.getenv('CMS_API_BASE_URL', ''),
        "cms_token": os.getenv('CMS_API_TOKEN', ''),
        "ckan_url": os.getenv('CKAN_URL', ''),
        "ckan_token": os.getenv('CKAN_API_TOKEN', ''),
        "ckan_organization": os.getenv('CKAN_ORGANIZATION', '')
    }

    # Load runtime settings if file exists
    settings_file = get_runtime_settings_path()
    if settings_file.exists():
        try:
            with open(settings_file, 'r', encoding='utf-8') as f:
                runtime_settings = json.load(f)
                # Override with runtime settings (only if set)
                for key, value in runtime_settings.items():
                    if value:  # Only override if value is not empty
                        config[key] = value
        except Exception:
            pass  # Fall back to .env values

    return config


def save_runtime_config(settings: Dict[str, Any]) -> None:
    """
    Save runtime configuration to settings.json.

    Args:
        settings: Dictionary with settings to save
    """
    settings_file = get_runtime_settings_path()

    # Ensure directory exists
    settings_file.parent.mkdir(parents=True, exist_ok=True)

    # Save settings
    with open(settings_file, 'w', encoding='utf-8') as f:
        json.dump(settings, f, indent=2)

    # Set file permissions to be more secure (owner read/write only)
    try:
        os.chmod(settings_file, 0o600)
    except Exception:
        pass  # May not work on all platforms
