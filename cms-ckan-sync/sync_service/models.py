"""Data models for CMS-CKAN Sync Service"""

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import List, Optional, Dict, Any


class SyncStatusEnum(str, Enum):
    """Status of a sync operation"""
    PENDING = "pending"
    IN_PROGRESS = "in_progress"
    SUCCESS = "success"
    PARTIAL = "partial"  # Some records synced, some failed
    FAILED = "failed"


@dataclass
class SyncResult:
    """Result of a single model sync operation"""
    model_id: str
    status: SyncStatusEnum
    started_at: datetime
    completed_at: Optional[datetime] = None
    records_fetched: int = 0
    records_transformed: int = 0
    resources_uploaded: int = 0
    dataset_id: Optional[str] = None
    dataset_url: Optional[str] = None
    errors: List[str] = field(default_factory=list)
    warnings: List[str] = field(default_factory=list)
    dry_run: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'model_id': self.model_id,
            'status': self.status.value,
            'started_at': self.started_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None,
            'records_fetched': self.records_fetched,
            'records_transformed': self.records_transformed,
            'resources_uploaded': self.resources_uploaded,
            'dataset_id': self.dataset_id,
            'dataset_url': self.dataset_url,
            'errors': self.errors,
            'warnings': self.warnings,
            'dry_run': self.dry_run
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'SyncResult':
        """Create from dictionary"""
        return cls(
            model_id=data['model_id'],
            status=SyncStatusEnum(data['status']),
            started_at=datetime.fromisoformat(data['started_at']),
            completed_at=datetime.fromisoformat(data['completed_at']) if data.get('completed_at') else None,
            records_fetched=data.get('records_fetched', 0),
            records_transformed=data.get('records_transformed', 0),
            resources_uploaded=data.get('resources_uploaded', 0),
            dataset_id=data.get('dataset_id'),
            dataset_url=data.get('dataset_url'),
            errors=data.get('errors', []),
            warnings=data.get('warnings', []),
            dry_run=data.get('dry_run', False)
        )

    @property
    def duration_seconds(self) -> Optional[float]:
        """Calculate duration in seconds"""
        if self.completed_at and self.started_at:
            return (self.completed_at - self.started_at).total_seconds()
        return None


@dataclass
class ModelSyncStatus:
    """Current status of a model"""
    model_id: str
    cms_model_id: str
    ckan_dataset_name: str
    last_sync: Optional[SyncResult] = None
    is_syncing: bool = False

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'model_id': self.model_id,
            'cms_model_id': self.cms_model_id,
            'ckan_dataset_name': self.ckan_dataset_name,
            'last_sync': self.last_sync.to_dict() if self.last_sync else None,
            'is_syncing': self.is_syncing
        }


@dataclass
class SyncStatus:
    """Overall sync service status"""
    is_running: bool = False
    current_model: Optional[str] = None
    models: List[ModelSyncStatus] = field(default_factory=list)
    last_run: Optional[datetime] = None
    total_syncs: int = 0
    successful_syncs: int = 0
    failed_syncs: int = 0

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for JSON serialization"""
        return {
            'is_running': self.is_running,
            'current_model': self.current_model,
            'models': [m.to_dict() for m in self.models],
            'last_run': self.last_run.isoformat() if self.last_run else None,
            'total_syncs': self.total_syncs,
            'successful_syncs': self.successful_syncs,
            'failed_syncs': self.failed_syncs
        }


@dataclass
class CMSItem:
    """Represents an item from the CMS"""
    id: str
    data: Dict[str, Any]

    def get(self, key: str, default: Any = None) -> Any:
        """Get a field value"""
        return self.data.get(key, default)

    def __getitem__(self, key: str) -> Any:
        """Get a field value by key"""
        return self.data[key]

    def keys(self):
        """Get all field keys"""
        return self.data.keys()

    def items(self):
        """Get all field items"""
        return self.data.items()
