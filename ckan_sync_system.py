#!/usr/bin/env python3
"""
CKAN Automated Data Sync System
Handles scheduling, harvesting, monitoring, and alerting for CKAN datasets
"""

import os
import json
import logging
import datetime
import requests
import smtplib
import traceback
from typing import Dict, List, Optional, Any
from dataclasses import dataclass, asdict
from enum import Enum
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart

import schedule
import psycopg2
from psycopg2.extras import RealDictCursor
import ckanapi
from slack_sdk import WebClient
from slack_sdk.errors import SlackApiError


logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)


class SyncStatus(Enum):
    PENDING = "pending"
    RUNNING = "running"
    SUCCESS = "success"
    FAILED = "failed"
    PARTIAL = "partial"


class AlertChannel(Enum):
    EMAIL = "email"
    SLACK = "slack"
    WEBHOOK = "webhook"


@dataclass
class SyncSchedule:
    dataset_id: str
    dataset_name: str
    source_url: str
    sync_frequency: str  # cron expression or schedule string
    source_type: str  # api, csv, xml, json, etc.
    enabled: bool = True
    retry_count: int = 3
    timeout: int = 300
    last_sync: Optional[datetime.datetime] = None
    next_sync: Optional[datetime.datetime] = None
    metadata: Dict = None


@dataclass
class SyncLog:
    schedule_id: int
    dataset_id: str
    start_time: datetime.datetime
    end_time: Optional[datetime.datetime]
    status: SyncStatus
    records_processed: int = 0
    error_message: Optional[str] = None
    details: Optional[Dict] = None


class CKANSyncManager:
    """Main orchestrator for CKAN data synchronization"""

    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.ckan = ckanapi.RemoteCKAN(
            config['ckan_url'],
            apikey=config['ckan_api_key']
        )
        self.db = self._init_database()
        self.alerter = AlertManager(config)
        self.harvester = DataHarvester(self.ckan, config)

    def _init_database(self):
        """Initialize PostgreSQL connection and tables"""
        conn = psycopg2.connect(
            host=self.config['db_host'],
            database=self.config['db_name'],
            user=self.config['db_user'],
            password=self.config['db_password']
        )

        with conn.cursor() as cur:
            cur.execute("""
                CREATE TABLE IF NOT EXISTS sync_schedules (
                    id SERIAL PRIMARY KEY,
                    dataset_id VARCHAR(255) UNIQUE NOT NULL,
                    dataset_name VARCHAR(255),
                    source_url TEXT,
                    sync_frequency VARCHAR(100),
                    source_type VARCHAR(50),
                    enabled BOOLEAN DEFAULT true,
                    retry_count INT DEFAULT 3,
                    timeout INT DEFAULT 300,
                    last_sync TIMESTAMP,
                    next_sync TIMESTAMP,
                    metadata JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS sync_logs (
                    id SERIAL PRIMARY KEY,
                    schedule_id INT REFERENCES sync_schedules(id),
                    dataset_id VARCHAR(255),
                    start_time TIMESTAMP NOT NULL,
                    end_time TIMESTAMP,
                    status VARCHAR(20),
                    records_processed INT DEFAULT 0,
                    error_message TEXT,
                    details JSONB,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            cur.execute("""
                CREATE TABLE IF NOT EXISTS alerts (
                    id SERIAL PRIMARY KEY,
                    schedule_id INT REFERENCES sync_schedules(id),
                    alert_type VARCHAR(50),
                    channel VARCHAR(20),
                    recipient TEXT,
                    message TEXT,
                    sent_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    status VARCHAR(20)
                )
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_logs_dataset
                ON sync_logs(dataset_id, start_time DESC)
            """)

            cur.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_schedules_next
                ON sync_schedules(next_sync) WHERE enabled = true
            """)

        conn.commit()
        return conn

    def create_schedule(self, schedule: SyncSchedule) -> int:
        """Create a new sync schedule for a dataset"""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO sync_schedules (
                    dataset_id, dataset_name, source_url, sync_frequency,
                    source_type, enabled, retry_count, timeout, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s)
                ON CONFLICT (dataset_id) DO UPDATE SET
                    dataset_name = EXCLUDED.dataset_name,
                    source_url = EXCLUDED.source_url,
                    sync_frequency = EXCLUDED.sync_frequency,
                    source_type = EXCLUDED.source_type,
                    enabled = EXCLUDED.enabled,
                    retry_count = EXCLUDED.retry_count,
                    timeout = EXCLUDED.timeout,
                    metadata = EXCLUDED.metadata,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING id
            """, (
                schedule.dataset_id, schedule.dataset_name, schedule.source_url,
                schedule.sync_frequency, schedule.source_type, schedule.enabled,
                schedule.retry_count, schedule.timeout,
                json.dumps(schedule.metadata) if schedule.metadata else None
            ))
            schedule_id = cur.fetchone()[0]

        self.db.commit()
        logger.info(f"Created schedule {schedule_id} for dataset {schedule.dataset_id}")
        return schedule_id

    def sync_dataset(self, schedule_id: int) -> SyncLog:
        """Execute sync for a specific dataset"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM sync_schedules WHERE id = %s
            """, (schedule_id,))
            schedule_data = cur.fetchone()

        if not schedule_data:
            raise ValueError(f"Schedule {schedule_id} not found")

        sync_log = SyncLog(
            schedule_id=schedule_id,
            dataset_id=schedule_data['dataset_id'],
            start_time=datetime.datetime.now(),
            end_time=None,
            status=SyncStatus.RUNNING
        )

        log_id = self._log_sync_start(sync_log)

        try:
            result = self.harvester.harvest(
                dataset_id=schedule_data['dataset_id'],
                source_url=schedule_data['source_url'],
                source_type=schedule_data['source_type'],
                timeout=schedule_data['timeout']
            )

            sync_log.end_time = datetime.datetime.now()
            sync_log.status = SyncStatus.SUCCESS
            sync_log.records_processed = result.get('records_processed', 0)
            sync_log.details = result

            self._update_last_sync(schedule_id)

        except Exception as e:
            sync_log.end_time = datetime.datetime.now()
            sync_log.status = SyncStatus.FAILED
            sync_log.error_message = str(e)
            sync_log.details = {'traceback': traceback.format_exc()}

            self.alerter.send_failure_alert(schedule_data, sync_log)
            logger.error(f"Sync failed for dataset {schedule_data['dataset_id']}: {e}")

        self._log_sync_end(log_id, sync_log)
        return sync_log

    def _log_sync_start(self, sync_log: SyncLog) -> int:
        """Log the start of a sync operation"""
        with self.db.cursor() as cur:
            cur.execute("""
                INSERT INTO sync_logs (
                    schedule_id, dataset_id, start_time, status
                ) VALUES (%s, %s, %s, %s)
                RETURNING id
            """, (
                sync_log.schedule_id, sync_log.dataset_id,
                sync_log.start_time, sync_log.status.value
            ))
            log_id = cur.fetchone()[0]
        self.db.commit()
        return log_id

    def _log_sync_end(self, log_id: int, sync_log: SyncLog):
        """Update sync log with completion details"""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE sync_logs SET
                    end_time = %s,
                    status = %s,
                    records_processed = %s,
                    error_message = %s,
                    details = %s
                WHERE id = %s
            """, (
                sync_log.end_time, sync_log.status.value,
                sync_log.records_processed, sync_log.error_message,
                json.dumps(sync_log.details) if sync_log.details else None,
                log_id
            ))
        self.db.commit()

    def _update_last_sync(self, schedule_id: int):
        """Update last sync timestamp for a schedule"""
        with self.db.cursor() as cur:
            cur.execute("""
                UPDATE sync_schedules SET
                    last_sync = CURRENT_TIMESTAMP,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = %s
            """, (schedule_id,))
        self.db.commit()

    def get_pending_syncs(self) -> List[Dict]:
        """Get all schedules that need to be synced"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM sync_schedules
                WHERE enabled = true
                AND (next_sync IS NULL OR next_sync <= CURRENT_TIMESTAMP)
                ORDER BY next_sync ASC
            """)
            return cur.fetchall()

    def get_sync_history(self, dataset_id: str, limit: int = 100) -> List[Dict]:
        """Get sync history for a dataset"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT l.*, s.dataset_name
                FROM sync_logs l
                JOIN sync_schedules s ON l.schedule_id = s.id
                WHERE l.dataset_id = %s
                ORDER BY l.start_time DESC
                LIMIT %s
            """, (dataset_id, limit))
            return cur.fetchall()

    def get_dashboard_stats(self) -> Dict:
        """Get statistics for dashboard display"""
        with self.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH recent_syncs AS (
                    SELECT DISTINCT ON (dataset_id)
                        dataset_id, status, start_time, end_time, records_processed
                    FROM sync_logs
                    ORDER BY dataset_id, start_time DESC
                )
                SELECT
                    COUNT(*) as total_datasets,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration,
                    SUM(records_processed) as total_records
                FROM recent_syncs
            """)
            stats = cur.fetchone()

            cur.execute("""
                SELECT s.*,
                    (SELECT status FROM sync_logs
                     WHERE schedule_id = s.id
                     ORDER BY start_time DESC LIMIT 1) as last_status
                FROM sync_schedules s
                WHERE enabled = true
                ORDER BY last_sync DESC
                LIMIT 10
            """)
            recent = cur.fetchall()

            return {
                'overview': stats,
                'recent_syncs': recent
            }


class DataHarvester:
    """Handles the actual data harvesting from various sources"""

    def __init__(self, ckan_client: ckanapi.RemoteCKAN, config: Dict):
        self.ckan = ckan_client
        self.config = config

    def harvest(self, dataset_id: str, source_url: str,
                source_type: str, timeout: int = 300) -> Dict:
        """Main harvest method that delegates to specific harvesters"""

        harvesters = {
            'api': self._harvest_api,
            'csv': self._harvest_csv,
            'json': self._harvest_json,
            'xml': self._harvest_xml,
            'database': self._harvest_database,
            'ckan': self._harvest_ckan
        }

        harvester = harvesters.get(source_type, self._harvest_generic)
        return harvester(dataset_id, source_url, timeout)

    def _harvest_api(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Harvest data from REST API"""
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        records_count = len(data) if isinstance(data, list) else 1

        # Update dataset resources
        self._update_dataset_resource(dataset_id, data, 'api')

        return {
            'records_processed': records_count,
            'source': source_url,
            'type': 'api'
        }

    def _harvest_csv(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Harvest CSV data"""
        import pandas as pd

        df = pd.read_csv(source_url)
        records_count = len(df)

        # Convert to CKAN-compatible format
        resource_data = df.to_dict('records')

        self._update_dataset_resource(dataset_id, resource_data, 'csv')

        return {
            'records_processed': records_count,
            'source': source_url,
            'type': 'csv',
            'columns': df.columns.tolist()
        }

    def _harvest_json(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Harvest JSON data"""
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()

        data = response.json()
        records_count = len(data) if isinstance(data, list) else 1

        self._update_dataset_resource(dataset_id, data, 'json')

        return {
            'records_processed': records_count,
            'source': source_url,
            'type': 'json'
        }

    def _harvest_xml(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Harvest XML data"""
        import xml.etree.ElementTree as ET

        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()

        root = ET.fromstring(response.content)
        records_count = len(root)

        # Convert XML to dict
        data = self._xml_to_dict(root)

        self._update_dataset_resource(dataset_id, data, 'xml')

        return {
            'records_processed': records_count,
            'source': source_url,
            'type': 'xml'
        }

    def _harvest_database(self, dataset_id: str, connection_str: str, timeout: int) -> Dict:
        """Harvest from database using connection string"""
        import pandas as pd
        import sqlalchemy

        engine = sqlalchemy.create_engine(connection_str)

        # Parse query from connection string metadata
        query = "SELECT * FROM target_table"  # This should come from config

        df = pd.read_sql(query, engine)
        records_count = len(df)

        resource_data = df.to_dict('records')
        self._update_dataset_resource(dataset_id, resource_data, 'database')

        return {
            'records_processed': records_count,
            'source': 'database',
            'type': 'database'
        }

    def _harvest_ckan(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Harvest from another CKAN instance"""
        remote_ckan = ckanapi.RemoteCKAN(source_url)

        # Get remote dataset
        remote_dataset = remote_ckan.action.package_show(id=dataset_id)

        # Update local dataset
        self.ckan.action.package_patch(
            id=dataset_id,
            notes=remote_dataset.get('notes'),
            tags=remote_dataset.get('tags'),
            resources=remote_dataset.get('resources')
        )

        return {
            'records_processed': len(remote_dataset.get('resources', [])),
            'source': source_url,
            'type': 'ckan'
        }

    def _harvest_generic(self, dataset_id: str, source_url: str, timeout: int) -> Dict:
        """Generic harvester for unknown types"""
        response = requests.get(source_url, timeout=timeout)
        response.raise_for_status()

        # Store raw content as resource
        self._create_resource_from_content(dataset_id, response.content, source_url)

        return {
            'records_processed': 1,
            'source': source_url,
            'type': 'generic',
            'content_length': len(response.content)
        }

    def _update_dataset_resource(self, dataset_id: str, data: Any, format: str):
        """Update or create resource for dataset"""
        try:
            # Get existing dataset
            dataset = self.ckan.action.package_show(id=dataset_id)

            # Find or create resource
            resource = None
            for res in dataset.get('resources', []):
                if res.get('format', '').lower() == format.lower():
                    resource = res
                    break

            if resource:
                # Update existing resource
                self.ckan.action.resource_patch(
                    id=resource['id'],
                    last_modified=datetime.datetime.now().isoformat(),
                    datastore_active=True
                )
            else:
                # Create new resource
                self.ckan.action.resource_create(
                    package_id=dataset_id,
                    format=format,
                    name=f"Harvested {format.upper()} data",
                    last_modified=datetime.datetime.now().isoformat(),
                    datastore_active=True
                )

            logger.info(f"Updated resource for dataset {dataset_id}")

        except Exception as e:
            logger.error(f"Failed to update resource: {e}")
            raise

    def _create_resource_from_content(self, dataset_id: str, content: bytes, source_url: str):
        """Create a resource from raw content"""
        import tempfile

        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(content)
            tmp_path = tmp.name

        try:
            self.ckan.action.resource_create(
                package_id=dataset_id,
                upload=open(tmp_path, 'rb'),
                url=source_url,
                name="Harvested content",
                last_modified=datetime.datetime.now().isoformat()
            )
        finally:
            os.unlink(tmp_path)

    def _xml_to_dict(self, element):
        """Convert XML element to dictionary"""
        result = {}

        for child in element:
            if len(child) == 0:
                result[child.tag] = child.text
            else:
                result[child.tag] = self._xml_to_dict(child)

        return result


class AlertManager:
    """Handles alerts and notifications"""

    def __init__(self, config: Dict):
        self.config = config
        self.email_config = config.get('email', {})
        self.slack_config = config.get('slack', {})
        self.webhook_config = config.get('webhooks', {})

        if self.slack_config.get('token'):
            self.slack_client = WebClient(token=self.slack_config['token'])
        else:
            self.slack_client = None

    def send_failure_alert(self, schedule: Dict, sync_log: SyncLog):
        """Send alert for failed sync"""
        message = self._format_failure_message(schedule, sync_log)

        # Send to all configured channels
        if self.email_config.get('enabled'):
            self._send_email(
                self.email_config['recipients'],
                f"CKAN Sync Failed: {schedule['dataset_name']}",
                message
            )

        if self.slack_config.get('enabled') and self.slack_client:
            self._send_slack(
                self.slack_config['channel'],
                message
            )

        if self.webhook_config.get('enabled'):
            self._send_webhook(
                self.webhook_config['url'],
                {
                    'dataset_id': schedule['dataset_id'],
                    'dataset_name': schedule['dataset_name'],
                    'status': 'failed',
                    'error': sync_log.error_message,
                    'timestamp': sync_log.end_time.isoformat() if sync_log.end_time else None
                }
            )

    def send_success_summary(self, stats: Dict):
        """Send daily/weekly success summary"""
        message = self._format_summary_message(stats)

        if self.email_config.get('summary_enabled'):
            self._send_email(
                self.email_config['summary_recipients'],
                "CKAN Sync Summary Report",
                message
            )

    def _format_failure_message(self, schedule: Dict, sync_log: SyncLog) -> str:
        """Format failure message"""
        return f"""
        Dataset Sync Failed

        Dataset: {schedule['dataset_name']} ({schedule['dataset_id']})
        Source: {schedule['source_url']}
        Started: {sync_log.start_time}
        Failed: {sync_log.end_time}
        Error: {sync_log.error_message}

        Please check the logs for more details.
        """

    def _format_summary_message(self, stats: Dict) -> str:
        """Format summary message"""
        overview = stats['overview']
        return f"""
        CKAN Sync Summary

        Total Datasets: {overview['total_datasets']}
        Successful: {overview['successful']}
        Failed: {overview['failed']}
        Currently Running: {overview['running']}
        Average Duration: {overview['avg_duration']:.2f} seconds
        Total Records Processed: {overview['total_records']}

        Recent Syncs:
        {self._format_recent_syncs(stats['recent_syncs'])}
        """

    def _format_recent_syncs(self, recent_syncs: List[Dict]) -> str:
        """Format recent syncs for message"""
        lines = []
        for sync in recent_syncs:
            status_emoji = "✅" if sync['last_status'] == 'success' else "❌"
            lines.append(f"  {status_emoji} {sync['dataset_name']} - {sync['last_sync']}")
        return "\n".join(lines)

    def _send_email(self, recipients: List[str], subject: str, body: str):
        """Send email alert"""
        try:
            msg = MIMEMultipart()
            msg['From'] = self.email_config['from']
            msg['To'] = ', '.join(recipients)
            msg['Subject'] = subject

            msg.attach(MIMEText(body, 'plain'))

            with smtplib.SMTP(self.email_config['smtp_host'],
                             self.email_config['smtp_port']) as server:
                if self.email_config.get('smtp_tls'):
                    server.starttls()
                if self.email_config.get('smtp_user'):
                    server.login(
                        self.email_config['smtp_user'],
                        self.email_config['smtp_password']
                    )
                server.send_message(msg)

            logger.info(f"Email sent to {recipients}")

        except Exception as e:
            logger.error(f"Failed to send email: {e}")

    def _send_slack(self, channel: str, message: str):
        """Send Slack alert"""
        try:
            response = self.slack_client.chat_postMessage(
                channel=channel,
                text=message,
                blocks=[
                    {
                        "type": "section",
                        "text": {
                            "type": "mrkdwn",
                            "text": message
                        }
                    }
                ]
            )
            logger.info(f"Slack message sent to {channel}")

        except SlackApiError as e:
            logger.error(f"Failed to send Slack message: {e}")

    def _send_webhook(self, url: str, payload: Dict):
        """Send webhook notification"""
        try:
            response = requests.post(url, json=payload, timeout=10)
            response.raise_for_status()
            logger.info(f"Webhook sent to {url}")

        except Exception as e:
            logger.error(f"Failed to send webhook: {e}")


class DashboardAPI:
    """REST API for dashboard"""

    def __init__(self, sync_manager: CKANSyncManager):
        self.sync_manager = sync_manager

    def get_dashboard_data(self) -> Dict:
        """Get all dashboard data"""
        stats = self.sync_manager.get_dashboard_stats()

        # Add timeline data
        with self.sync_manager.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed
                FROM sync_logs
                WHERE start_time > NOW() - INTERVAL '24 hours'
                GROUP BY hour
                ORDER BY hour DESC
            """)
            timeline = cur.fetchall()

        return {
            'stats': stats,
            'timeline': timeline,
            'last_updated': datetime.datetime.now().isoformat()
        }

    def get_dataset_details(self, dataset_id: str) -> Dict:
        """Get detailed info for a specific dataset"""
        history = self.sync_manager.get_sync_history(dataset_id, limit=50)

        with self.sync_manager.db.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT * FROM sync_schedules WHERE dataset_id = %s
            """, (dataset_id,))
            schedule = cur.fetchone()

        return {
            'schedule': schedule,
            'history': history
        }


def main():
    """Main entry point for the sync system"""

    # Load configuration
    config = {
        'ckan_url': os.getenv('CKAN_URL', 'http://localhost:5000'),
        'ckan_api_key': os.getenv('CKAN_API_KEY'),
        'db_host': os.getenv('DB_HOST', 'localhost'),
        'db_name': os.getenv('DB_NAME', 'ckan_sync'),
        'db_user': os.getenv('DB_USER', 'ckan'),
        'db_password': os.getenv('DB_PASSWORD'),
        'email': {
            'enabled': os.getenv('EMAIL_ENABLED', 'false').lower() == 'true',
            'smtp_host': os.getenv('SMTP_HOST', 'localhost'),
            'smtp_port': int(os.getenv('SMTP_PORT', '25')),
            'smtp_tls': os.getenv('SMTP_TLS', 'false').lower() == 'true',
            'smtp_user': os.getenv('SMTP_USER'),
            'smtp_password': os.getenv('SMTP_PASSWORD'),
            'from': os.getenv('EMAIL_FROM', 'ckan-sync@example.com'),
            'recipients': os.getenv('EMAIL_RECIPIENTS', '').split(',')
        },
        'slack': {
            'enabled': os.getenv('SLACK_ENABLED', 'false').lower() == 'true',
            'token': os.getenv('SLACK_TOKEN'),
            'channel': os.getenv('SLACK_CHANNEL', '#ckan-alerts')
        },
        'webhooks': {
            'enabled': os.getenv('WEBHOOK_ENABLED', 'false').lower() == 'true',
            'url': os.getenv('WEBHOOK_URL')
        }
    }

    # Initialize sync manager
    sync_manager = CKANSyncManager(config)

    # Run pending syncs
    pending = sync_manager.get_pending_syncs()
    logger.info(f"Found {len(pending)} pending syncs")

    for schedule in pending:
        try:
            sync_manager.sync_dataset(schedule['id'])
        except Exception as e:
            logger.error(f"Failed to sync schedule {schedule['id']}: {e}")

    # Send summary if configured
    if datetime.datetime.now().hour == 9:  # Send at 9 AM
        stats = sync_manager.get_dashboard_stats()
        sync_manager.alerter.send_success_summary(stats)


if __name__ == "__main__":
    main()