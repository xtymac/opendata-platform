#!/usr/bin/env python3
"""
Simplified CKAN Sync Dashboard for Quick Testing
Works with SQLite for easy setup - no PostgreSQL required
"""

from flask import Flask, render_template, jsonify, request
from flask_cors import CORS
import sqlite3
import json
import datetime
import random
import os
from typing import Dict, List, Any

app = Flask(__name__)
app.config['SECRET_KEY'] = 'dev-secret-key'
CORS(app)

# SQLite database path
DB_PATH = 'ckan_sync.db'

class SimpleDashboardService:
    """Simplified service using SQLite"""

    def __init__(self):
        self.init_database()

    def get_connection(self):
        """Get SQLite connection"""
        conn = sqlite3.connect(DB_PATH)
        conn.row_factory = sqlite3.Row  # Enable dict-like access
        return conn

    def init_database(self):
        """Initialize SQLite database and tables"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Create tables
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_schedules (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                dataset_id TEXT UNIQUE NOT NULL,
                dataset_name TEXT,
                source_url TEXT,
                sync_frequency TEXT,
                source_type TEXT,
                enabled INTEGER DEFAULT 1,
                retry_count INTEGER DEFAULT 3,
                timeout INTEGER DEFAULT 300,
                last_sync TEXT,
                next_sync TEXT,
                metadata TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)

        cursor.execute("""
            CREATE TABLE IF NOT EXISTS sync_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                schedule_id INTEGER,
                dataset_id TEXT,
                start_time TEXT NOT NULL,
                end_time TEXT,
                status TEXT,
                records_processed INTEGER DEFAULT 0,
                error_message TEXT,
                details TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (schedule_id) REFERENCES sync_schedules (id)
            )
        """)

        # Check if sample data exists
        cursor.execute("SELECT COUNT(*) FROM sync_schedules")
        count = cursor.fetchone()[0]

        if count == 0:
            self.insert_sample_data(cursor)

        conn.commit()
        conn.close()

    def insert_sample_data(self, cursor):
        """Insert sample data for demonstration"""
        # Sample schedules
        schedules = [
            ('sample-api-dataset', 'Sample API Dataset', 'https://jsonplaceholder.typicode.com/posts', 'hourly', 'api'),
            ('weather-data', 'Weather Data', 'https://api.openweathermap.org/data/2.5/weather', 'hourly', 'api'),
            ('population-csv', 'Population CSV', 'https://example.com/population.csv', 'daily', 'csv'),
            ('financial-data', 'Financial Indicators', 'https://api.example.com/financial', 'daily', 'api'),
            ('sensor-data', 'IoT Sensor Data', 'https://api.example.com/sensors', 'hourly', 'api')
        ]

        for dataset_id, name, url, freq, source_type in schedules:
            cursor.execute("""
                INSERT INTO sync_schedules (dataset_id, dataset_name, source_url, sync_frequency, source_type)
                VALUES (?, ?, ?, ?, ?)
            """, (dataset_id, name, url, freq, source_type))

        # Generate sample logs
        cursor.execute("SELECT id, dataset_id FROM sync_schedules")
        schedule_data = cursor.fetchall()

        statuses = ['success', 'success', 'success', 'failed', 'success']

        for schedule_id, dataset_id in schedule_data:
            for i in range(15):  # 15 logs per dataset
                start_time = datetime.datetime.now() - datetime.timedelta(hours=i*2)
                end_time = start_time + datetime.timedelta(minutes=random.randint(1, 15))
                status = random.choice(statuses)
                records = random.randint(50, 1000) if status == 'success' else 0
                error_msg = 'Connection timeout' if status == 'failed' else None

                cursor.execute("""
                    INSERT INTO sync_logs (
                        schedule_id, dataset_id, start_time, end_time,
                        status, records_processed, error_message
                    ) VALUES (?, ?, ?, ?, ?, ?, ?)
                """, (
                    schedule_id, dataset_id,
                    start_time.isoformat(), end_time.isoformat(),
                    status, records, error_msg
                ))

    def get_overview_stats(self) -> Dict[str, Any]:
        """Get overview statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get latest status for each dataset
        cursor.execute("""
            WITH recent_syncs AS (
                SELECT
                    dataset_id,
                    status,
                    start_time,
                    end_time,
                    records_processed,
                    ROW_NUMBER() OVER (PARTITION BY dataset_id ORDER BY start_time DESC) as rn
                FROM sync_logs
            )
            SELECT
                COUNT(*) as total_datasets,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                SUM(CASE WHEN status = 'failed' THEN 1 ELSE 0 END) as failed,
                SUM(CASE WHEN status = 'running' THEN 1 ELSE 0 END) as running,
                AVG(CASE WHEN end_time IS NOT NULL
                    THEN (julianday(end_time) - julianday(start_time)) * 24 * 3600
                    ELSE 0 END) as avg_duration,
                SUM(records_processed) as total_records
            FROM recent_syncs
            WHERE rn = 1
        """)

        stats = dict(cursor.fetchone())

        # Get hourly stats for last 24 hours
        cursor.execute("""
            SELECT
                strftime('%Y-%m-%d %H:00:00', start_time) as hour,
                COUNT(*) as total,
                SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) as successful,
                ROUND(
                    100.0 * SUM(CASE WHEN status = 'success' THEN 1 ELSE 0 END) / COUNT(*),
                    2
                ) as success_rate
            FROM sync_logs
            WHERE start_time > datetime('now', '-24 hours')
            GROUP BY hour
            ORDER BY hour DESC
            LIMIT 24
        """)

        hourly_stats = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {
            'overview': stats,
            'hourly_stats': hourly_stats
        }

    def get_dataset_list(self, page: int = 1, per_page: int = 20) -> Dict[str, Any]:
        """Get paginated dataset list"""
        offset = (page - 1) * per_page
        conn = self.get_connection()
        cursor = conn.cursor()

        # Get datasets with latest sync status
        cursor.execute("""
            WITH latest_sync AS (
                SELECT
                    s.id, s.dataset_id, s.dataset_name, s.source_url,
                    s.sync_frequency, s.enabled, s.last_sync,
                    l.status as last_status, l.records_processed,
                    l.start_time as last_run, l.error_message,
                    ROW_NUMBER() OVER (PARTITION BY s.id ORDER BY l.start_time DESC) as rn
                FROM sync_schedules s
                LEFT JOIN sync_logs l ON s.id = l.schedule_id
            )
            SELECT *,
                CASE
                    WHEN last_sync IS NULL THEN 'Never'
                    WHEN last_sync > datetime('now', '-1 hour') THEN 'Recently'
                    WHEN last_sync > datetime('now', '-1 day') THEN 'Today'
                    WHEN last_sync > datetime('now', '-7 days') THEN 'This Week'
                    ELSE 'Older'
                END as sync_age
            FROM latest_sync
            WHERE rn = 1 OR rn IS NULL
            ORDER BY last_run DESC
            LIMIT ? OFFSET ?
        """, (per_page, offset))

        datasets = [dict(row) for row in cursor.fetchall()]

        # Get total count
        cursor.execute("SELECT COUNT(*) FROM sync_schedules")
        total = cursor.fetchone()[0]

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
        cursor = conn.cursor()

        # Get schedule info
        cursor.execute("SELECT * FROM sync_schedules WHERE dataset_id = ?", (dataset_id,))
        schedule = cursor.fetchone()

        if not schedule:
            conn.close()
            return None

        schedule = dict(schedule)

        # Get sync history
        cursor.execute("""
            SELECT * FROM sync_logs
            WHERE schedule_id = ?
            ORDER BY start_time DESC
            LIMIT 50
        """, (schedule['id'],))
        history = [dict(row) for row in cursor.fetchall()]

        # Get performance metrics
        cursor.execute("""
            SELECT
                AVG(CASE WHEN end_time IS NOT NULL
                    THEN (julianday(end_time) - julianday(start_time)) * 24 * 3600
                    ELSE 0 END) as avg_duration,
                AVG(records_processed) as avg_records,
                COUNT(CASE WHEN status = 'success' THEN 1 END) * 100.0 / COUNT(*) as success_rate
            FROM sync_logs
            WHERE schedule_id = ? AND end_time IS NOT NULL
        """, (schedule['id'],))
        metrics = dict(cursor.fetchone())

        conn.close()

        return {
            'schedule': schedule,
            'history': history,
            'metrics': metrics
        }

    def get_failing_datasets(self) -> List[Dict]:
        """Get datasets that are currently failing"""
        conn = self.get_connection()
        cursor = conn.cursor()

        cursor.execute("""
            WITH recent_failures AS (
                SELECT
                    s.dataset_id, s.dataset_name,
                    l.start_time, l.error_message,
                    ROW_NUMBER() OVER (PARTITION BY s.dataset_id ORDER BY l.start_time DESC) as rn
                FROM sync_schedules s
                JOIN sync_logs l ON s.id = l.schedule_id
                WHERE l.status = 'failed'
                AND l.start_time > datetime('now', '-24 hours')
            )
            SELECT dataset_id, dataset_name, start_time, error_message
            FROM recent_failures
            WHERE rn = 1
            ORDER BY start_time DESC
            LIMIT 10
        """)

        failures = [dict(row) for row in cursor.fetchall()]
        conn.close()
        return failures

    def get_calendar_events(self, start_date=None, end_date=None) -> Dict[str, Any]:
        """Get events for calendar view"""
        conn = self.get_connection()
        cursor = conn.cursor()

        if not start_date:
            start_date = datetime.datetime.now() - datetime.timedelta(days=30)
        if not end_date:
            end_date = datetime.datetime.now() + datetime.timedelta(days=30)

        cursor.execute("""
            SELECT
                l.id,
                l.dataset_id,
                s.dataset_name,
                l.start_time,
                l.end_time,
                l.status,
                l.records_processed,
                l.error_message,
                s.sync_frequency as sync_type
            FROM sync_logs l
            JOIN sync_schedules s ON l.schedule_id = s.id
            WHERE l.start_time BETWEEN ? AND ?
            ORDER BY l.start_time DESC
        """, (start_date.isoformat(), end_date.isoformat()))

        events = [dict(row) for row in cursor.fetchall()]
        conn.close()

        return {'events': events}

    def get_calendar_stats(self) -> Dict[str, Any]:
        """Get calendar statistics"""
        conn = self.get_connection()
        cursor = conn.cursor()

        # Today's sync count
        cursor.execute("""
            SELECT COUNT(*) FROM sync_logs
            WHERE date(start_time) = date('now')
        """)
        today_count = cursor.fetchone()[0]

        # This week's sync count
        cursor.execute("""
            SELECT COUNT(*) FROM sync_logs
            WHERE start_time > datetime('now', '-7 days')
        """)
        week_count = cursor.fetchone()[0]

        # Active schedules
        cursor.execute("""
            SELECT COUNT(*) FROM sync_schedules
            WHERE enabled = 1
        """)
        active_schedules = cursor.fetchone()[0]

        # Next scheduled sync (simplified)
        next_sync = datetime.datetime.now() + datetime.timedelta(hours=1)
        next_sync_str = next_sync.strftime('%H:%M')

        conn.close()

        return {
            'today_count': today_count,
            'week_count': week_count,
            'active_schedules': active_schedules,
            'next_sync': next_sync_str
        }

dashboard_service = SimpleDashboardService()

@app.route('/')
def index():
    """Render simple dashboard page"""
    return render_template('simple_dashboard.html')

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
    result = dashboard_service.get_dataset_list(page, per_page)
    return jsonify(result)

@app.route('/api/dataset/<dataset_id>')
def get_dataset(dataset_id):
    """Get dataset details"""
    detail = dashboard_service.get_dataset_detail(dataset_id)
    if not detail:
        return jsonify({'error': 'Dataset not found'}), 404
    return jsonify(detail)

@app.route('/api/failures')
def get_failures():
    """Get failing datasets"""
    failures = dashboard_service.get_failing_datasets()
    return jsonify(failures)

@app.route('/api/trigger/<dataset_id>', methods=['POST'])
def trigger_sync(dataset_id):
    """Simulate triggering a sync"""
    # This is just a simulation for demo purposes
    return jsonify({
        'success': True,
        'message': f'Sync triggered for {dataset_id} (simulated)',
        'log_id': random.randint(1000, 9999)
    })

@app.route('/calendar')
def calendar_view():
    """Render calendar view"""
    return render_template('calendar_dashboard.html')

@app.route('/api/calendar/events')
def get_calendar_events():
    """Get calendar events"""
    events = dashboard_service.get_calendar_events()
    return jsonify(events)

@app.route('/api/calendar/stats')
def get_calendar_stats():
    """Get calendar statistics"""
    stats = dashboard_service.get_calendar_stats()
    return jsonify(stats)

@app.route('/api/calendar/schedule', methods=['POST'])
def create_calendar_schedule():
    """Create new schedule (simulated)"""
    data = request.get_json()

    # Simulated response for demo
    return jsonify({
        'success': True,
        'message': 'Schedule created (demo mode)',
        'schedule_id': random.randint(100, 999)
    })

@app.route('/map')
def map_view():
    """Render interactive map view"""
    return render_template('map_dashboard.html')

@app.route('/api/map/regions')
def get_map_regions():
    """Get region data for map visualization"""
    regions = {
        "下関市": {"lat": 33.9581, "lng": 130.9408, "datasets": 45, "population": 255051},
        "宇部市": {"lat": 33.9519, "lng": 131.2469, "datasets": 38, "population": 162570},
        "山口市": {"lat": 34.1861, "lng": 131.4706, "datasets": 52, "population": 193966},
        "萩市": {"lat": 34.4083, "lng": 131.3992, "datasets": 28, "population": 44078},
        "防府市": {"lat": 34.0517, "lng": 131.5633, "datasets": 35, "population": 113979},
        "下松市": {"lat": 34.0150, "lng": 131.8728, "datasets": 22, "population": 55012},
        "岩国市": {"lat": 34.1669, "lng": 132.2200, "datasets": 41, "population": 130027},
        "光市": {"lat": 33.9622, "lng": 131.9422, "datasets": 18, "population": 49798},
        "長門市": {"lat": 34.3711, "lng": 131.1822, "datasets": 20, "population": 32259},
        "柳井市": {"lat": 33.9639, "lng": 132.1017, "datasets": 16, "population": 30770},
        "美祢市": {"lat": 34.1661, "lng": 131.2056, "datasets": 15, "population": 22789},
        "周南市": {"lat": 34.0556, "lng": 131.8061, "datasets": 42, "population": 137758},
        "山陽小野田市": {"lat": 33.9611, "lng": 131.1808, "datasets": 25, "population": 60034}
    }
    return jsonify(regions)

@app.route('/api/map/datasets/<region>')
def get_region_datasets(region):
    """Get datasets for a specific region"""
    category = request.args.get('category', 'all')

    # Generate sample datasets based on region and category
    datasets = []
    categories = {
        'population': '人口統計',
        'aed': 'AED設置場所',
        'schools': '教育施設',
        'disaster': '防災情報',
        'tourism': '観光情報',
        'facilities': '公共施設'
    }

    if category == 'all':
        for cat_key, cat_name in categories.items():
            datasets.append({
                'id': f'{region}_{cat_key}_1',
                'title': f'{region} {cat_name}データ',
                'category': cat_name,
                'records': random.randint(100, 1000),
                'last_updated': datetime.datetime.now().isoformat()
            })
    elif category in categories:
        datasets.append({
            'id': f'{region}_{category}_1',
            'title': f'{region} {categories[category]}データ',
            'category': categories[category],
            'records': random.randint(100, 1000),
            'last_updated': datetime.datetime.now().isoformat()
        })

    return jsonify({'datasets': datasets, 'total': len(datasets)})

@app.route('/api/map/search')
def search_map_datasets():
    """Search datasets across all regions"""
    query = request.args.get('q', '').lower()
    category = request.args.get('category', 'all')

    results = []
    regions = ["下関市", "宇部市", "山口市", "萩市", "防府市"]

    for region in regions:
        if not query or query in region.lower():
            results.append({
                'region': region,
                'matches': random.randint(5, 20),
                'datasets': [
                    {
                        'title': f'{region} サンプルデータ',
                        'category': '人口統計',
                        'records': random.randint(100, 500)
                    }
                ]
            })

    return jsonify({'results': results, 'total': len(results)})

if __name__ == '__main__':
    print("🚀 Starting CKAN Sync Dashboard...")
    print("📊 Dashboard URL: http://localhost:5001")
    print("📁 Database: SQLite (ckan_sync.db)")
    print("💡 This is a demo version with sample data")
    print("=" * 50)

    app.run(debug=True, host='0.0.0.0', port=5001)