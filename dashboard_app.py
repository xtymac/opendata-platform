"""
CKAN Sync Dashboard Application
Real-time monitoring dashboard for CKAN data synchronization
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
from flask_socketio import SocketIO, emit
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import datetime
from typing import Dict, List, Any
import os


app = Flask(__name__)
app.config['SECRET_KEY'] = os.getenv('SECRET_KEY', 'dev-secret-key')
CORS(app)
socketio = SocketIO(app, cors_allowed_origins="*")


class DashboardService:
    """Service for dashboard data operations"""

    def __init__(self):
        self.db_config = {
            'host': os.getenv('DB_HOST', 'localhost'),
            'database': os.getenv('DB_NAME', 'ckan_sync'),
            'user': os.getenv('DB_USER', 'ckan'),
            'password': os.getenv('DB_PASSWORD')
        }

    def get_connection(self):
        """Get database connection"""
        return psycopg2.connect(**self.db_config)

    def get_overview_stats(self) -> Dict[str, Any]:
        """Get overview statistics"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Overall stats
            cur.execute("""
                WITH recent_syncs AS (
                    SELECT DISTINCT ON (dataset_id)
                        dataset_id, status, start_time, end_time,
                        records_processed, error_message
                    FROM sync_logs
                    ORDER BY dataset_id, start_time DESC
                )
                SELECT
                    COUNT(*) as total_datasets,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    COUNT(CASE WHEN status = 'failed' THEN 1 END) as failed,
                    COUNT(CASE WHEN status = 'running' THEN 1 END) as running,
                    COUNT(CASE WHEN status = 'pending' THEN 1 END) as pending,
                    COALESCE(AVG(EXTRACT(EPOCH FROM (end_time - start_time))), 0) as avg_duration,
                    COALESCE(SUM(records_processed), 0) as total_records,
                    COUNT(CASE WHEN start_time > NOW() - INTERVAL '1 hour' THEN 1 END) as synced_last_hour,
                    COUNT(CASE WHEN start_time > NOW() - INTERVAL '24 hours' THEN 1 END) as synced_last_day
                FROM recent_syncs
            """)
            stats = cur.fetchone()

            # Success rate over time
            cur.execute("""
                SELECT
                    DATE_TRUNC('hour', start_time) as hour,
                    COUNT(*) as total,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) as successful,
                    ROUND(
                        100.0 * COUNT(CASE WHEN status = 'success' THEN 1 END) / COUNT(*),
                        2
                    ) as success_rate
                FROM sync_logs
                WHERE start_time > NOW() - INTERVAL '24 hours'
                GROUP BY hour
                ORDER BY hour DESC
                LIMIT 24
            """)
            hourly_stats = cur.fetchall()

        conn.close()
        return {
            'overview': stats,
            'hourly_stats': hourly_stats
        }

    def get_dataset_list(self, page: int = 1, per_page: int = 20,
                        status_filter: str = None) -> Dict[str, Any]:
        """Get paginated dataset list with status"""
        offset = (page - 1) * per_page

        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Build query with optional filter
            base_query = """
                WITH latest_sync AS (
                    SELECT DISTINCT ON (s.id)
                        s.id, s.dataset_id, s.dataset_name, s.source_url,
                        s.sync_frequency, s.enabled, s.last_sync,
                        l.status as last_status, l.records_processed,
                        l.start_time as last_run, l.error_message
                    FROM sync_schedules s
                    LEFT JOIN sync_logs l ON s.id = l.schedule_id
                    ORDER BY s.id, l.start_time DESC
                )
                SELECT *,
                    CASE
                        WHEN last_sync IS NULL THEN 'Never'
                        WHEN last_sync > NOW() - INTERVAL '1 hour' THEN 'Recently'
                        WHEN last_sync > NOW() - INTERVAL '1 day' THEN 'Today'
                        WHEN last_sync > NOW() - INTERVAL '7 days' THEN 'This Week'
                        ELSE 'Older'
                    END as sync_age
                FROM latest_sync
            """

            if status_filter:
                base_query += f" WHERE last_status = '{status_filter}'"

            # Get total count
            count_query = f"SELECT COUNT(*) FROM ({base_query}) t"
            cur.execute(count_query)
            total = cur.fetchone()['count']

            # Get paginated results
            query = f"{base_query} ORDER BY last_run DESC NULLS LAST LIMIT %s OFFSET %s"
            cur.execute(query, (per_page, offset))
            datasets = cur.fetchall()

        conn.close()

        return {
            'datasets': datasets,
            'pagination': {
                'page': page,
                'per_page': per_page,
                'total': total,
                'pages': (total + per_page - 1) // per_page
            }
        }

    def get_dataset_detail(self, dataset_id: str) -> Dict[str, Any]:
        """Get detailed information for a specific dataset"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            # Get schedule info
            cur.execute("""
                SELECT * FROM sync_schedules WHERE dataset_id = %s
            """, (dataset_id,))
            schedule = cur.fetchone()

            if not schedule:
                return None

            # Get sync history
            cur.execute("""
                SELECT * FROM sync_logs
                WHERE schedule_id = %s
                ORDER BY start_time DESC
                LIMIT 50
            """, (schedule['id'],))
            history = cur.fetchall()

            # Get performance metrics
            cur.execute("""
                SELECT
                    AVG(EXTRACT(EPOCH FROM (end_time - start_time))) as avg_duration,
                    MIN(EXTRACT(EPOCH FROM (end_time - start_time))) as min_duration,
                    MAX(EXTRACT(EPOCH FROM (end_time - start_time))) as max_duration,
                    AVG(records_processed) as avg_records,
                    COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
                FROM sync_logs
                WHERE schedule_id = %s
                AND end_time IS NOT NULL
            """, (schedule['id'],))
            metrics = cur.fetchone()

            # Get recent alerts
            cur.execute("""
                SELECT * FROM alerts
                WHERE schedule_id = %s
                ORDER BY sent_at DESC
                LIMIT 10
            """, (schedule['id'],))
            alerts = cur.fetchall()

        conn.close()

        return {
            'schedule': schedule,
            'history': history,
            'metrics': metrics,
            'alerts': alerts
        }

    def get_timeline_data(self, hours: int = 24) -> List[Dict]:
        """Get timeline data for visualization"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                SELECT
                    DATE_TRUNC('hour', start_time) as time,
                    dataset_id,
                    status,
                    records_processed,
                    EXTRACT(EPOCH FROM (end_time - start_time)) as duration
                FROM sync_logs
                WHERE start_time > NOW() - INTERVAL '%s hours'
                ORDER BY start_time DESC
            """, (hours,))
            timeline = cur.fetchall()

        conn.close()
        return timeline

    def get_failing_datasets(self) -> List[Dict]:
        """Get datasets that are currently failing"""
        conn = self.get_connection()
        with conn.cursor(cursor_factory=RealDictCursor) as cur:
            cur.execute("""
                WITH recent_failures AS (
                    SELECT DISTINCT ON (s.dataset_id)
                        s.dataset_id, s.dataset_name,
                        l.start_time, l.error_message,
                        COUNT(*) OVER (PARTITION BY s.dataset_id) as failure_count
                    FROM sync_schedules s
                    JOIN sync_logs l ON s.id = l.schedule_id
                    WHERE l.status = 'failed'
                    AND l.start_time > NOW() - INTERVAL '24 hours'
                    ORDER BY s.dataset_id, l.start_time DESC
                )
                SELECT * FROM recent_failures
                ORDER BY failure_count DESC, start_time DESC
                LIMIT 10
            """)
            failures = cur.fetchall()

        conn.close()
        return failures

    def trigger_sync(self, dataset_id: str) -> Dict[str, Any]:
        """Manually trigger a sync for a dataset"""
        conn = self.get_connection()
        with conn.cursor() as cur:
            # Get schedule
            cur.execute("""
                SELECT id FROM sync_schedules WHERE dataset_id = %s
            """, (dataset_id,))
            schedule = cur.fetchone()

            if not schedule:
                return {'error': 'Dataset not found'}

            # Create pending sync log
            cur.execute("""
                INSERT INTO sync_logs (schedule_id, dataset_id, start_time, status)
                VALUES (%s, %s, %s, 'pending')
                RETURNING id
            """, (schedule[0], dataset_id, datetime.datetime.now()))

            log_id = cur.fetchone()[0]
            conn.commit()

        conn.close()

        # Emit socket event for real-time update
        socketio.emit('sync_triggered', {
            'dataset_id': dataset_id,
            'log_id': log_id,
            'timestamp': datetime.datetime.now().isoformat()
        })

        return {'success': True, 'log_id': log_id}


dashboard_service = DashboardService()


@app.route('/')
def index():
    """Render main dashboard page"""
    return render_template('dashboard.html')


@app.route('/api/stats')
def get_stats():
    """Get dashboard statistics"""
    stats = dashboard_service.get_overview_stats()
    return jsonify(stats)


@app.route('/api/datasets')
def get_datasets():
    """Get dataset list"""
    page = int(request.args.get('page', 1))
    per_page = int(request.args.get('per_page', 20))
    status_filter = request.args.get('status')

    result = dashboard_service.get_dataset_list(page, per_page, status_filter)
    return jsonify(result)


@app.route('/api/dataset/<dataset_id>')
def get_dataset(dataset_id):
    """Get dataset details"""
    detail = dashboard_service.get_dataset_detail(dataset_id)
    if not detail:
        return jsonify({'error': 'Dataset not found'}), 404
    return jsonify(detail)


@app.route('/api/timeline')
def get_timeline():
    """Get timeline data"""
    hours = int(request.args.get('hours', 24))
    timeline = dashboard_service.get_timeline_data(hours)
    return jsonify(timeline)


@app.route('/api/failures')
def get_failures():
    """Get failing datasets"""
    failures = dashboard_service.get_failing_datasets()
    return jsonify(failures)


@app.route('/api/trigger/<dataset_id>', methods=['POST'])
def trigger_sync(dataset_id):
    """Manually trigger a sync"""
    result = dashboard_service.trigger_sync(dataset_id)
    return jsonify(result)


@socketio.on('connect')
def handle_connect():
    """Handle WebSocket connection"""
    emit('connected', {'message': 'Connected to CKAN Sync Dashboard'})


@socketio.on('subscribe_dataset')
def handle_subscribe(data):
    """Subscribe to updates for a specific dataset"""
    dataset_id = data.get('dataset_id')
    # Add to room for targeted updates
    from flask_socketio import join_room
    join_room(f"dataset_{dataset_id}")
    emit('subscribed', {'dataset_id': dataset_id})


@socketio.on('unsubscribe_dataset')
def handle_unsubscribe(data):
    """Unsubscribe from dataset updates"""
    dataset_id = data.get('dataset_id')
    from flask_socketio import leave_room
    leave_room(f"dataset_{dataset_id}")
    emit('unsubscribed', {'dataset_id': dataset_id})


def broadcast_sync_update(dataset_id: str, status: str, details: Dict = None):
    """Broadcast sync update to subscribed clients"""
    socketio.emit('sync_update', {
        'dataset_id': dataset_id,
        'status': status,
        'details': details,
        'timestamp': datetime.datetime.now().isoformat()
    }, room=f"dataset_{dataset_id}")


if __name__ == '__main__':
    socketio.run(app, debug=True, host='0.0.0.0', port=5001)