"""
Apache Airflow DAG for CKAN Data Synchronization
Provides advanced scheduling and workflow management
"""

from datetime import datetime, timedelta
from typing import Dict, Any

from airflow import DAG
from airflow.operators.python import PythonOperator
from airflow.operators.bash import BashOperator
from airflow.operators.email import EmailOperator
from airflow.providers.postgres.operators.postgres import PostgresOperator
from airflow.providers.postgres.hooks.postgres import PostgresHook
from airflow.providers.slack.operators.slack_webhook import SlackWebhookOperator
from airflow.utils.task_group import TaskGroup
from airflow.models import Variable
from airflow.exceptions import AirflowException

import json
import logging
import requests
import ckanapi


logger = logging.getLogger(__name__)


default_args = {
    'owner': 'ckan-admin',
    'depends_on_past': False,
    'start_date': datetime(2024, 1, 1),
    'email': ['admin@example.com'],
    'email_on_failure': True,
    'email_on_retry': False,
    'retries': 2,
    'retry_delay': timedelta(minutes=5),
    'execution_timeout': timedelta(minutes=30),
}


def get_active_schedules(**context):
    """Fetch active sync schedules from database"""
    pg_hook = PostgresHook(postgres_conn_id='ckan_sync_db')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    cursor.execute("""
        SELECT id, dataset_id, dataset_name, source_url, source_type
        FROM sync_schedules
        WHERE enabled = true
        AND (
            (sync_frequency = 'hourly' AND EXTRACT(MINUTE FROM NOW()) < 5)
            OR (sync_frequency = 'daily' AND EXTRACT(HOUR FROM NOW()) = 0)
            OR (sync_frequency = 'weekly' AND EXTRACT(DOW FROM NOW()) = 1 AND EXTRACT(HOUR FROM NOW()) = 0)
            OR (sync_frequency = 'monthly' AND EXTRACT(DAY FROM NOW()) = 1 AND EXTRACT(HOUR FROM NOW()) = 0)
        )
    """)

    schedules = cursor.fetchall()
    cursor.close()
    conn.close()

    # Push to XCom for downstream tasks
    schedule_list = [
        {
            'id': s[0],
            'dataset_id': s[1],
            'dataset_name': s[2],
            'source_url': s[3],
            'source_type': s[4]
        }
        for s in schedules
    ]

    context['task_instance'].xcom_push(key='schedules', value=schedule_list)
    logger.info(f"Found {len(schedule_list)} schedules to process")
    return schedule_list


def sync_dataset(schedule: Dict[str, Any], **context):
    """Sync a single dataset"""
    ckan_url = Variable.get("ckan_url")
    ckan_api_key = Variable.get("ckan_api_key")

    ckan = ckanapi.RemoteCKAN(ckan_url, apikey=ckan_api_key)

    dataset_id = schedule['dataset_id']
    source_url = schedule['source_url']
    source_type = schedule['source_type']

    try:
        # Log sync start
        pg_hook = PostgresHook(postgres_conn_id='ckan_sync_db')
        conn = pg_hook.get_conn()
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO sync_logs (schedule_id, dataset_id, start_time, status)
            VALUES (%s, %s, %s, 'running')
            RETURNING id
        """, (schedule['id'], dataset_id, datetime.now()))

        log_id = cursor.fetchone()[0]
        conn.commit()

        # Perform sync based on source type
        if source_type == 'api':
            records = sync_from_api(ckan, dataset_id, source_url)
        elif source_type == 'csv':
            records = sync_from_csv(ckan, dataset_id, source_url)
        elif source_type == 'database':
            records = sync_from_database(ckan, dataset_id, source_url)
        else:
            records = sync_generic(ckan, dataset_id, source_url)

        # Update sync log with success
        cursor.execute("""
            UPDATE sync_logs
            SET end_time = %s, status = 'success', records_processed = %s
            WHERE id = %s
        """, (datetime.now(), records, log_id))

        # Update schedule last_sync
        cursor.execute("""
            UPDATE sync_schedules
            SET last_sync = %s
            WHERE id = %s
        """, (datetime.now(), schedule['id']))

        conn.commit()
        cursor.close()
        conn.close()

        logger.info(f"Successfully synced {dataset_id}: {records} records")
        return {'status': 'success', 'records': records}

    except Exception as e:
        # Log failure
        cursor.execute("""
            UPDATE sync_logs
            SET end_time = %s, status = 'failed', error_message = %s
            WHERE id = %s
        """, (datetime.now(), str(e), log_id))
        conn.commit()
        cursor.close()
        conn.close()

        logger.error(f"Failed to sync {dataset_id}: {str(e)}")
        raise AirflowException(f"Sync failed for {dataset_id}: {str(e)}")


def sync_from_api(ckan, dataset_id: str, source_url: str) -> int:
    """Sync data from REST API"""
    response = requests.get(source_url, timeout=300)
    response.raise_for_status()

    data = response.json()
    records_count = len(data) if isinstance(data, list) else 1

    # Update CKAN dataset
    try:
        dataset = ckan.action.package_show(id=dataset_id)

        # Update or create resource
        resource_exists = False
        for resource in dataset.get('resources', []):
            if resource.get('format') == 'JSON':
                ckan.action.resource_patch(
                    id=resource['id'],
                    last_modified=datetime.now().isoformat()
                )
                resource_exists = True
                break

        if not resource_exists:
            ckan.action.resource_create(
                package_id=dataset_id,
                format='JSON',
                name='API Data',
                url=source_url,
                last_modified=datetime.now().isoformat()
            )

    except Exception as e:
        logger.error(f"Failed to update CKAN dataset: {e}")
        raise

    return records_count


def sync_from_csv(ckan, dataset_id: str, source_url: str) -> int:
    """Sync CSV data"""
    import pandas as pd
    import tempfile

    df = pd.read_csv(source_url)
    records_count = len(df)

    # Save to temporary file
    with tempfile.NamedTemporaryFile(mode='w', suffix='.csv', delete=False) as tmp:
        df.to_csv(tmp, index=False)
        tmp_path = tmp.name

    try:
        # Upload to CKAN
        with open(tmp_path, 'rb') as f:
            ckan.action.resource_create(
                package_id=dataset_id,
                upload=f,
                format='CSV',
                name=f'CSV Data - {datetime.now().strftime("%Y%m%d")}',
                last_modified=datetime.now().isoformat()
            )
    finally:
        import os
        os.unlink(tmp_path)

    return records_count


def sync_from_database(ckan, dataset_id: str, connection_string: str) -> int:
    """Sync from database"""
    import pandas as pd
    import sqlalchemy

    # Parse connection string for query
    engine = sqlalchemy.create_engine(connection_string)
    query = "SELECT * FROM data_table"  # Should be configurable

    df = pd.read_sql(query, engine)
    records_count = len(df)

    # Convert to JSON for CKAN
    data = df.to_dict('records')

    # Update dataset
    ckan.action.package_patch(
        id=dataset_id,
        extras=[{
            'key': 'last_db_sync',
            'value': datetime.now().isoformat()
        }]
    )

    return records_count


def sync_generic(ckan, dataset_id: str, source_url: str) -> int:
    """Generic sync for unknown types"""
    response = requests.get(source_url, timeout=300)
    response.raise_for_status()

    # Store as generic resource
    import tempfile
    with tempfile.NamedTemporaryFile(delete=False) as tmp:
        tmp.write(response.content)
        tmp_path = tmp.name

    try:
        with open(tmp_path, 'rb') as f:
            ckan.action.resource_create(
                package_id=dataset_id,
                upload=f,
                format='DATA',
                name=f'Data - {datetime.now().strftime("%Y%m%d")}',
                url=source_url,
                last_modified=datetime.now().isoformat()
            )
    finally:
        import os
        os.unlink(tmp_path)

    return 1


def check_sync_health(**context):
    """Check overall sync health and send alerts if needed"""
    pg_hook = PostgresHook(postgres_conn_id='ckan_sync_db')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    # Check for failed syncs in last hour
    cursor.execute("""
        SELECT COUNT(*) as failed_count,
               array_agg(dataset_id) as failed_datasets
        FROM sync_logs
        WHERE status = 'failed'
        AND start_time > NOW() - INTERVAL '1 hour'
    """)

    result = cursor.fetchone()
    failed_count = result[0]
    failed_datasets = result[1] or []

    if failed_count > 0:
        context['task_instance'].xcom_push(
            key='alert_needed',
            value=True
        )
        context['task_instance'].xcom_push(
            key='failed_datasets',
            value=failed_datasets
        )

    # Get sync statistics
    cursor.execute("""
        SELECT
            COUNT(DISTINCT dataset_id) as total_datasets,
            COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
            COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
            AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration
        FROM sync_logs
        WHERE start_time > NOW() - INTERVAL '24 hours'
    """)

    stats = cursor.fetchone()
    cursor.close()
    conn.close()

    return {
        'total_datasets': stats[0],
        'successful': stats[1],
        'failed': stats[2],
        'avg_duration': stats[3],
        'failed_datasets': failed_datasets
    }


def update_dashboard_cache(**context):
    """Update cached dashboard data"""
    pg_hook = PostgresHook(postgres_conn_id='ckan_sync_db')
    conn = pg_hook.get_conn()
    cursor = conn.cursor()

    # Generate dashboard JSON
    cursor.execute("""
        WITH dataset_status AS (
            SELECT DISTINCT ON (dataset_id)
                s.dataset_id,
                s.dataset_name,
                l.status,
                l.start_time as last_sync,
                l.records_processed
            FROM sync_schedules s
            LEFT JOIN sync_logs l ON s.id = l.schedule_id
            ORDER BY dataset_id, l.start_time DESC
        )
        SELECT json_build_object(
            'datasets', json_agg(dataset_status),
            'updated_at', NOW()
        )
        FROM dataset_status
    """)

    dashboard_data = cursor.fetchone()[0]

    # Store in cache table or Redis
    cursor.execute("""
        INSERT INTO dashboard_cache (key, data, updated_at)
        VALUES ('main_dashboard', %s, NOW())
        ON CONFLICT (key) DO UPDATE
        SET data = EXCLUDED.data, updated_at = EXCLUDED.updated_at
    """, (json.dumps(dashboard_data),))

    conn.commit()
    cursor.close()
    conn.close()

    logger.info("Dashboard cache updated")


# Main DAG definition
dag = DAG(
    'ckan_sync_pipeline',
    default_args=default_args,
    description='CKAN Data Synchronization Pipeline',
    schedule_interval='0 * * * *',  # Run hourly
    catchup=False,
    max_active_runs=1,
    tags=['ckan', 'data-sync'],
)

# Task definitions
fetch_schedules = PythonOperator(
    task_id='fetch_schedules',
    python_callable=get_active_schedules,
    dag=dag,
)

# Dynamic task mapping for parallel sync
with TaskGroup('sync_datasets', dag=dag) as sync_group:
    sync_tasks = PythonOperator.partial(
        task_id='sync_dataset',
        python_callable=sync_dataset,
        dag=dag,
    ).expand(op_kwargs=[{'schedule': s} for s in "{{ ti.xcom_pull(task_ids='fetch_schedules', key='schedules') }}"])

health_check = PythonOperator(
    task_id='check_health',
    python_callable=check_sync_health,
    dag=dag,
    trigger_rule='all_done',
)

update_dashboard = PythonOperator(
    task_id='update_dashboard',
    python_callable=update_dashboard_cache,
    dag=dag,
)

# Alert tasks
send_failure_alert = SlackWebhookOperator(
    task_id='send_slack_alert',
    slack_webhook_conn_id='slack_webhook',
    message="""
    :warning: CKAN Sync Failures Detected
    Failed Datasets: {{ ti.xcom_pull(task_ids='check_health', key='failed_datasets') }}
    Check the dashboard for details.
    """,
    dag=dag,
    trigger_rule='one_failed',
)

send_success_summary = EmailOperator(
    task_id='send_summary_email',
    to=['admin@example.com'],
    subject='CKAN Sync Daily Summary',
    html_content="""
    <h2>CKAN Sync Summary</h2>
    <p>Stats: {{ ti.xcom_pull(task_ids='check_health') }}</p>
    """,
    dag=dag,
    trigger_rule='all_success',
)

# Cleanup old logs
cleanup_logs = PostgresOperator(
    task_id='cleanup_old_logs',
    postgres_conn_id='ckan_sync_db',
    sql="""
        DELETE FROM sync_logs
        WHERE start_time < NOW() - INTERVAL '30 days';

        DELETE FROM alerts
        WHERE sent_at < NOW() - INTERVAL '7 days';
    """,
    dag=dag,
)

# Task dependencies
fetch_schedules >> sync_group >> health_check
health_check >> [update_dashboard, send_failure_alert, send_success_summary]
health_check >> cleanup_logs