"""Core sync service logic"""

import json
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path

# JST timezone
JST = ZoneInfo("Asia/Tokyo")

def now_jst():
    """Get current time in JST"""
    return datetime.now(JST)

def now_jst_str():
    """Get current time in JST as formatted string: YYYY-MM-DD HH:MM:SS JST"""
    return datetime.now(JST).strftime("%Y-%m-%d %H:%M:%S JST")

from typing import List, Optional, Dict, Any

from .config import Config, ModelConfig
from .cms_client import CMSClient, CMSError
from .ckan_client import CKANClient, CKANError
from .transformers import json_to_csv, json_to_geojson, has_geometry_data
from .models import SyncResult, SyncStatus, SyncStatusEnum, ModelSyncStatus
from .logger import get_logger, setup_logger

log = get_logger("cms_ckan_sync.core")


class SyncService:
    """
    Core sync service that orchestrates data synchronization from CMS to CKAN.

    Shared by both CLI and Web UI.
    """

    def __init__(self, config: Config):
        """
        Initialize sync service.

        Args:
            config: Service configuration
        """
        self.config = config

        # Setup logger
        setup_logger(level=config.log_level, log_dir=config.data_dir)

        # Initialize clients
        self.cms_client = CMSClient(config.cms_base_url, config.cms_token)
        self.ckan_client = CKANClient(
            config.ckan_url,
            config.ckan_token,
            config.ckan_organization
        )

        # State
        self._is_syncing = False
        self._current_model: Optional[str] = None
        self._history: List[SyncResult] = []

        # Load history
        self._load_history()

    def _get_history_file(self) -> Path:
        """Get path to history file"""
        data_dir = Path(self.config.data_dir)
        data_dir.mkdir(parents=True, exist_ok=True)
        return data_dir / "sync_history.json"

    def _load_history(self) -> None:
        """Load sync history from file"""
        history_file = self._get_history_file()

        if history_file.exists():
            try:
                with open(history_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    self._history = [SyncResult.from_dict(r) for r in data]
                log.debug(f"Loaded {len(self._history)} history entries")
            except Exception as e:
                log.warning(f"Failed to load history: {e}")
                self._history = []

    def _save_history(self) -> None:
        """Save sync history to file"""
        history_file = self._get_history_file()

        try:
            # Keep only last 100 entries
            self._history = self._history[-100:]

            with open(history_file, 'w', encoding='utf-8') as f:
                json.dump([r.to_dict() for r in self._history], f, indent=2)
        except Exception as e:
            log.warning(f"Failed to save history: {e}")

    def _add_to_history(self, result: SyncResult) -> None:
        """Add result to history and save"""
        self._history.append(result)
        self._save_history()

    def sync_model(
        self,
        model_id: str,
        dry_run: bool = False,
        force: bool = False,
        update_resource_id: Optional[str] = None
    ) -> SyncResult:
        """
        Sync a single model from CMS to CKAN.

        Args:
            model_id: Model identifier (from config)
            dry_run: If True, don't actually upload to CKAN
            force: If True, delete existing resources before upload
            update_resource_id: If provided, update this existing resource instead of creating new

        Returns:
            SyncResult with operation details
        """
        result = SyncResult(
            model_id=model_id,
            status=SyncStatusEnum.IN_PROGRESS,
            started_at=now_jst(),
            dry_run=dry_run
        )

        model_config = self.config.get_model(model_id)
        if not model_config:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"Model not found in configuration: {model_id}")
            result.completed_at = now_jst()
            return result

        self._current_model = model_id
        log.info(f"Starting sync for model: {model_id} (dry_run={dry_run}, force={force})")

        try:
            # Step 1: Fetch CSV directly from CMS (preserves column order)
            log.info(f"Fetching CSV from CMS model: {model_config.cms_model_id}")
            csv_content = self.cms_client.fetch_csv(model_config.cms_model_id)

            # Count records from CSV
            csv_lines = csv_content.strip().split('\n')
            record_count = len(csv_lines) - 1  # Exclude header
            result.records_fetched = record_count
            result.records_transformed = record_count

            if record_count == 0:
                result.status = SyncStatusEnum.SUCCESS
                result.warnings.append("No data found in CMS model")
                result.completed_at = now_jst()
                return result

            # Step 2: Fetch JSON data for GeoJSON generation (if geometry field is configured)
            geojson_content = None
            if model_config.geometry_field:
                log.info("Fetching JSON data for GeoJSON generation...")
                cms_data = self.cms_client.fetch_all_items(model_config.cms_model_id)
                if has_geometry_data(cms_data, model_config.geometry_field):
                    log.info("Transforming data to GeoJSON...")
                    geojson_data = json_to_geojson(
                        cms_data,
                        model_config.geometry_field,
                        properties_exclude=model_config.exclude_fields
                    )
                    if geojson_data:
                        geojson_content = json.dumps(geojson_data, ensure_ascii=False, indent=2)

            if dry_run:
                log.info("Dry run mode - skipping CKAN upload")
                result.status = SyncStatusEnum.SUCCESS
                result.warnings.append("Dry run - no data uploaded")
                result.completed_at = now_jst()
                return result

            # Step 3: Create/Update CKAN dataset
            dataset_name = model_config.ckan_dataset.name
            dataset_info = {
                'name': dataset_name,
                'title': model_config.ckan_dataset.title,
                'notes': model_config.ckan_dataset.notes,
                'owner_org': self.config.ckan_organization,
                'license_id': model_config.ckan_dataset.license_id,
                'tags': model_config.ckan_dataset.tags
            }

            log.info(f"Creating/updating CKAN dataset: {dataset_name}")
            dataset = self.ckan_client.create_or_update_dataset(dataset_name, dataset_info)
            result.dataset_id = dataset['id']
            result.dataset_url = f"{self.config.ckan_url}/dataset/{dataset_name}"

            # Step 4: Delete existing resources if force
            csv_resource_name = f"{dataset_name}_data"
            geojson_resource_name = f"{dataset_name}_geo"

            if force:
                log.info("Force mode - deleting existing resources")
                resource_names = [csv_resource_name]
                if geojson_content:
                    resource_names.append(geojson_resource_name)
                self.ckan_client.delete_resources_by_name(dataset['id'], resource_names)

            # Step 5: Upload or update resources
            if update_resource_id:
                # Update mode: update existing resource
                log.info(f"Updating existing resource: {update_resource_id}")
                try:
                    self.ckan_client.update_resource(
                        resource_id=update_resource_id,
                        content=csv_content.encode('utf-8'),
                        name=csv_resource_name,
                        format='csv',
                        description=f"Data in CSV format (synced from CMS at {now_jst_str()})"
                    )
                    result.resources_uploaded += 1
                except CKANError as e:
                    # If update fails, try delete and recreate
                    log.warning(f"Resource update failed, trying delete+create: {e}")
                    try:
                        self.ckan_client.delete_resource(update_resource_id)
                    except Exception:
                        pass
                    self.ckan_client.upload_resource(
                        package_id=dataset['id'],
                        name=csv_resource_name,
                        content=csv_content.encode('utf-8'),
                        format='csv',
                        description=f"Data in CSV format (synced from CMS at {now_jst_str()})"
                    )
                    result.resources_uploaded += 1
            else:
                # Create mode: upload new resources
                log.info(f"Uploading CSV resource: {csv_resource_name}")
                self.ckan_client.upload_resource(
                    package_id=dataset['id'],
                    name=csv_resource_name,
                    content=csv_content.encode('utf-8'),
                    format='csv',
                    description=f"Data in CSV format (synced from CMS at {now_jst_str()})"
                )
                result.resources_uploaded += 1

            if geojson_content and not update_resource_id:
                # Only upload GeoJSON for create mode (not update mode)
                log.info(f"Uploading GeoJSON resource: {geojson_resource_name}")
                self.ckan_client.upload_resource(
                    package_id=dataset['id'],
                    name=geojson_resource_name,
                    content=geojson_content.encode('utf-8'),
                    format='geojson',
                    description=f"Geographic data in GeoJSON format (synced from CMS at {now_jst_str()})"
                )
                result.resources_uploaded += 1

            result.status = SyncStatusEnum.SUCCESS
            log.info(f"Sync completed successfully for model: {model_id}")

        except CMSError as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"CMS error: {e}")
            log.error(f"CMS error during sync: {e}")

        except CKANError as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"CKAN error: {e}")
            log.error(f"CKAN error during sync: {e}")

        except Exception as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"Unexpected error: {e}")
            log.exception(f"Unexpected error during sync: {e}")

        finally:
            result.completed_at = now_jst()
            self._current_model = None
            self._add_to_history(result)

        return result

    def sync_model_smart(self, model_id: str) -> SyncResult:
        """
        Smart sync: find existing resource by name, update if found, create if not.

        This method is designed for webhook/scheduled sync where we want to
        automatically update existing resources rather than creating duplicates.

        Resource naming convention: {dataset_name}_data (matches sync_model behavior)

        Args:
            model_id: Model identifier (from config)

        Returns:
            SyncResult with operation details
        """
        model_config = self.config.get_model(model_id)
        if not model_config:
            # Model not found - return error result (don't sync_all)
            log.warning(f"Smart sync: model {model_id} not found in config")
            return SyncResult(
                model_id=model_id,
                status=SyncStatusEnum.FAILED,
                started_at=now_jst(),
                completed_at=now_jst(),
                errors=[f"Model not found in configuration: {model_id}"]
            )

        # Get or create dataset first
        dataset_name = model_config.ckan_dataset.name
        dataset_info = {
            'name': dataset_name,
            'title': model_config.ckan_dataset.title,
            'notes': model_config.ckan_dataset.notes,
            'owner_org': self.config.ckan_organization,
            'license_id': model_config.ckan_dataset.license_id,
            'tags': model_config.ckan_dataset.tags
        }

        try:
            log.info(f"Smart sync: ensuring dataset exists: {dataset_name}")
            dataset = self.ckan_client.create_or_update_dataset(dataset_name, dataset_info)

            # Resource name matches sync_model naming: {dataset_name}_data
            csv_resource_name = f"{dataset_name}_data"

            # Find existing resource by exact name and format
            existing_resource = self.ckan_client.find_resource_by_name(
                dataset['id'],
                csv_resource_name,
                format='CSV'
            )

            if existing_resource:
                # Update existing resource
                log.info(f"Smart sync: updating existing resource {existing_resource['id']} for {model_id}")
                return self.sync_model(
                    model_id,
                    update_resource_id=existing_resource['id']
                )
            else:
                # Create new resource
                log.info(f"Smart sync: creating new resource for {model_id}")
                return self.sync_model(model_id)

        except CKANError as e:
            log.error(f"Smart sync failed for {model_id}: {e}")
            return SyncResult(
                model_id=model_id,
                status=SyncStatusEnum.FAILED,
                started_at=now_jst(),
                completed_at=now_jst(),
                errors=[f"CKAN error: {e}"]
            )

    def sync_all(
        self,
        model_ids: Optional[List[str]] = None,
        dry_run: bool = False,
        force: bool = False,
        update_resource_id: Optional[str] = None
    ) -> List[SyncResult]:
        """
        Sync multiple models from CMS to CKAN.

        Args:
            model_ids: List of model IDs to sync (None = all configured models)
            dry_run: If True, don't actually upload to CKAN
            force: If True, delete existing resources before upload
            update_resource_id: If provided, update this existing resource instead of creating new

        Returns:
            List of SyncResult for each model
        """
        if self._is_syncing:
            log.warning("Sync already in progress")
            return []

        self._is_syncing = True
        results = []

        try:
            # Determine which models to sync
            if model_ids is None:
                model_ids = self.config.get_all_model_ids()

            log.info(f"Starting sync for {len(model_ids)} models")

            for model_id in model_ids:
                result = self.sync_model(model_id, dry_run=dry_run, force=force, update_resource_id=update_resource_id)
                results.append(result)

            # Summary
            success = sum(1 for r in results if r.status == SyncStatusEnum.SUCCESS)
            failed = sum(1 for r in results if r.status == SyncStatusEnum.FAILED)
            log.info(f"Sync completed: {success} success, {failed} failed")

        finally:
            self._is_syncing = False

        return results

    def get_status(self) -> SyncStatus:
        """
        Get current sync service status.

        Returns:
            SyncStatus with current state
        """
        model_statuses = []

        for model_id, model_config in self.config.models.items():
            # Find last sync for this model
            last_sync = None
            for result in reversed(self._history):
                if result.model_id == model_id:
                    last_sync = result
                    break

            model_statuses.append(ModelSyncStatus(
                model_id=model_id,
                cms_model_id=model_config.cms_model_id,
                ckan_dataset_name=model_config.ckan_dataset.name,
                last_sync=last_sync,
                is_syncing=(self._current_model == model_id)
            ))

        # Calculate stats
        total = len(self._history)
        successful = sum(1 for r in self._history if r.status == SyncStatusEnum.SUCCESS)
        failed = sum(1 for r in self._history if r.status == SyncStatusEnum.FAILED)

        last_run = None
        if self._history:
            last_run = max(r.started_at for r in self._history)

        return SyncStatus(
            is_running=self._is_syncing,
            current_model=self._current_model,
            models=model_statuses,
            last_run=last_run,
            total_syncs=total,
            successful_syncs=successful,
            failed_syncs=failed
        )

    def get_history(self, limit: int = 10) -> List[SyncResult]:
        """
        Get recent sync history.

        Args:
            limit: Maximum number of results to return

        Returns:
            List of recent SyncResult entries
        """
        return list(reversed(self._history[-limit:]))

    def test_connections(self) -> Dict[str, bool]:
        """
        Test connections to CMS and CKAN.

        Returns:
            Dictionary with connection status for each service
        """
        return {
            'cms': self.cms_client.test_connection(),
            'ckan': self.ckan_client.test_connection()
        }

    def sync_flexible(self, request: Any) -> SyncResult:
        """
        Sync with flexible source/target configuration.

        Supports:
        - Creating new datasets or adding to existing ones
        - Creating new resources or updating existing ones
        - Custom field mappings

        Args:
            request: FlexSyncRequest with sync configuration

        Returns:
            SyncResult with operation details
        """
        result = SyncResult(
            model_id=request.cms_model_id,
            status=SyncStatusEnum.IN_PROGRESS,
            started_at=now_jst(),
            dry_run=request.dry_run
        )

        self._is_syncing = True
        self._current_model = request.cms_model_id

        try:
            # Step 1: Fetch data from CMS
            log.info(f"Fetching data from CMS model: {request.cms_model_id}")
            cms_data = self.cms_client.fetch_all_items(request.cms_model_id)
            result.records_fetched = len(cms_data)

            if not cms_data:
                result.status = SyncStatusEnum.SUCCESS
                result.warnings.append("No data found in CMS model")
                result.completed_at = now_jst()
                return result

            # Step 2: Apply field mappings
            field_mappings = {}
            exclude_fields = []
            for mapping in request.field_mappings:
                if mapping.ckan_field is None:
                    exclude_fields.append(mapping.cms_field)
                elif mapping.ckan_field != mapping.cms_field:
                    field_mappings[mapping.cms_field] = mapping.ckan_field

            # Step 3: Transform data
            log.info("Transforming data to CSV...")
            csv_content = json_to_csv(
                cms_data,
                field_mappings=field_mappings,
                exclude_fields=exclude_fields
            )
            result.records_transformed = len(cms_data)

            # Check for geometry data and transform to GeoJSON
            geojson_content = None
            if request.include_geojson and request.geometry_field:
                if has_geometry_data(cms_data, request.geometry_field):
                    log.info("Transforming data to GeoJSON...")
                    geojson_data = json_to_geojson(
                        cms_data,
                        request.geometry_field,
                        properties_exclude=exclude_fields
                    )
                    if geojson_data:
                        geojson_content = json.dumps(geojson_data, ensure_ascii=False, indent=2)

            if request.dry_run:
                log.info("Dry run mode - skipping CKAN upload")
                result.status = SyncStatusEnum.SUCCESS
                result.warnings.append("Dry run - no data uploaded")
                result.completed_at = now_jst()
                return result

            # Step 4: Handle target dataset
            if request.target_mode == "new_dataset":
                # Create new dataset
                dataset_name = request.new_dataset_name or request.cms_model_id
                dataset_info = {
                    'name': dataset_name,
                    'title': request.new_dataset_title or dataset_name,
                    'notes': f'Data synced from CMS model: {request.cms_model_id}',
                    'owner_org': self.config.ckan_organization,
                    'license_id': 'cc-by'
                }

                log.info(f"Creating CKAN dataset: {dataset_name}")
                dataset = self.ckan_client.create_or_update_dataset(dataset_name, dataset_info)
                dataset_id = dataset['id']
                result.dataset_id = dataset_id
                result.dataset_url = f"{self.config.ckan_url}/dataset/{dataset_name}"

            else:
                # Use existing dataset
                dataset_id = request.existing_dataset_id
                existing = self.ckan_client.get_dataset(dataset_id)
                if not existing:
                    raise CKANError(f"Dataset not found: {dataset_id}")
                result.dataset_id = existing['id']
                result.dataset_url = f"{self.config.ckan_url}/dataset/{existing['name']}"

            # Step 5: Upload/Update resources
            resource_name = request.resource_name or request.cms_model_id

            if request.resource_mode == "update" and request.existing_resource_id:
                # Update existing resource
                log.info(f"Updating existing resource: {request.existing_resource_id}")
                try:
                    self.ckan_client.update_resource(
                        resource_id=request.existing_resource_id,
                        content=csv_content.encode('utf-8'),
                        name=resource_name,
                        format='csv',
                        description=f"Data synced from CMS at {now_jst_str()}"
                    )
                    result.resources_uploaded += 1
                except CKANError as e:
                    # If update fails, try delete and recreate
                    log.warning(f"Resource update failed, trying delete+create: {e}")
                    try:
                        self.ckan_client.delete_resource(request.existing_resource_id)
                    except Exception:
                        pass
                    self.ckan_client.upload_resource(
                        package_id=dataset_id,
                        name=resource_name,
                        content=csv_content.encode('utf-8'),
                        format='csv',
                        description=f"Data synced from CMS at {now_jst_str()}"
                    )
                    result.resources_uploaded += 1
            else:
                # Create new resource
                log.info(f"Creating new CSV resource: {resource_name}")
                self.ckan_client.upload_resource(
                    package_id=dataset_id,
                    name=resource_name,
                    content=csv_content.encode('utf-8'),
                    format='csv',
                    description=f"Data synced from CMS at {now_jst_str()}"
                )
                result.resources_uploaded += 1

            # Upload GeoJSON if available
            if geojson_content:
                geojson_resource_name = f"{resource_name}_geo"
                log.info(f"Creating GeoJSON resource: {geojson_resource_name}")
                self.ckan_client.upload_resource(
                    package_id=dataset_id,
                    name=geojson_resource_name,
                    content=geojson_content.encode('utf-8'),
                    format='geojson',
                    description=f"Geographic data synced from CMS at {now_jst_str()}"
                )
                result.resources_uploaded += 1

            result.status = SyncStatusEnum.SUCCESS
            log.info(f"Flexible sync completed successfully for model: {request.cms_model_id}")

        except CMSError as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"CMS error: {e}")
            log.error(f"CMS error during flexible sync: {e}")

        except CKANError as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"CKAN error: {e}")
            log.error(f"CKAN error during flexible sync: {e}")

        except Exception as e:
            result.status = SyncStatusEnum.FAILED
            result.errors.append(f"Unexpected error: {e}")
            log.exception(f"Unexpected error during flexible sync: {e}")

        finally:
            result.completed_at = now_jst()
            self._current_model = None
            self._is_syncing = False
            self._add_to_history(result)

        return result
