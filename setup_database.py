#!/usr/bin/env python3
"""
Database setup script for CKAN Sync Dashboard
Creates necessary tables and sample data
"""

import os
import psycopg2
from psycopg2.extras import RealDictCursor
import json
import datetime
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

def create_database_if_not_exists():
    """Create the database if it doesn't exist"""
    try:
        # Connect to postgres database to create our database
        conn = psycopg2.connect(
            host=os.getenv('DB_HOST', 'localhost'),
            database='postgres',
            user=os.getenv('DB_USER', 'postgres'),
            password=os.getenv('DB_PASSWORD', 'postgres')
        )
        conn.autocommit = True

        with conn.cursor() as cur:
            db_name = os.getenv('DB_NAME', 'ckan_sync')

            # Check if database exists
            cur.execute("""
                SELECT 1 FROM pg_database WHERE datname = %s
            """, (db_name,))

            if not cur.fetchone():
                cur.execute(f'CREATE DATABASE "{db_name}"')
                print(f"Created database: {db_name}")
            else:
                print(f"Database {db_name} already exists")

        conn.close()
        return True

    except psycopg2.Error as e:
        print(f"Error creating database: {e}")
        return False

def get_connection():
    """Get database connection"""
    return psycopg2.connect(
        host=os.getenv('DB_HOST', 'localhost'),
        database=os.getenv('DB_NAME', 'ckan_sync'),
        user=os.getenv('DB_USER', 'postgres'),
        password=os.getenv('DB_PASSWORD', 'postgres')
    )

def create_tables():
    """Create all necessary tables"""
    conn = get_connection()

    with conn.cursor() as cur:
        # Create sync_schedules table
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

        # Create sync_logs table
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

        # Create alerts table
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

        # Create dashboard_cache table
        cur.execute("""
            CREATE TABLE IF NOT EXISTS dashboard_cache (
                key VARCHAR(100) PRIMARY KEY,
                data JSONB,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """)

        # Create indexes
        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_logs_dataset
            ON sync_logs(dataset_id, start_time DESC)
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_schedules_next
            ON sync_schedules(next_sync) WHERE enabled = true
        """)

        cur.execute("""
            CREATE INDEX IF NOT EXISTS idx_sync_logs_status
            ON sync_logs(status, start_time DESC)
        """)

    conn.commit()
    conn.close()
    print("Tables created successfully")

def insert_sample_data():
    """Insert sample data for testing"""
    conn = get_connection()

    with conn.cursor() as cur:
        # Check if sample data already exists
        cur.execute("SELECT COUNT(*) FROM sync_schedules")
        count = cur.fetchone()[0]

        if count > 0:
            print("Sample data already exists, skipping...")
            conn.close()
            return

        # Sample schedules
        sample_schedules = [
            {
                'dataset_id': 'sample-api-dataset',
                'dataset_name': 'Sample API Dataset',
                'source_url': 'https://jsonplaceholder.typicode.com/posts',
                'sync_frequency': 'hourly',
                'source_type': 'api',
                'metadata': {'description': 'Sample JSON API data'}
            },
            {
                'dataset_id': 'sample-csv-dataset',
                'dataset_name': 'Sample CSV Dataset',
                'source_url': 'https://raw.githubusercontent.com/datasets/population/master/data/population.csv',
                'sync_frequency': 'daily',
                'source_type': 'csv',
                'metadata': {'description': 'Population data CSV'}
            },
            {
                'dataset_id': 'weather-data',
                'dataset_name': 'Weather Data',
                'source_url': 'https://api.openweathermap.org/data/2.5/weather?q=London',
                'sync_frequency': 'hourly',
                'source_type': 'api',
                'metadata': {'description': 'Weather API data'}
            },
            {
                'dataset_id': 'financial-indicators',
                'dataset_name': 'Financial Indicators',
                'source_url': 'https://api.example.com/financial/indicators',
                'sync_frequency': 'daily',
                'source_type': 'api',
                'enabled': False,
                'metadata': {'description': 'Financial market indicators'}
            }
        ]

        for schedule in sample_schedules:
            cur.execute("""
                INSERT INTO sync_schedules (
                    dataset_id, dataset_name, source_url, sync_frequency,
                    source_type, enabled, metadata
                ) VALUES (%s, %s, %s, %s, %s, %s, %s)
            """, (
                schedule['dataset_id'],
                schedule['dataset_name'],
                schedule['source_url'],
                schedule['sync_frequency'],
                schedule['source_type'],
                schedule.get('enabled', True),
                json.dumps(schedule['metadata'])
            ))

        # Sample logs for realistic dashboard
        cur.execute("SELECT id, dataset_id FROM sync_schedules")
        schedules = cur.fetchall()

        # Generate some sample sync logs
        import random
        statuses = ['success', 'success', 'success', 'failed', 'success']  # 80% success rate

        for schedule_id, dataset_id in schedules:
            for i in range(10):  # 10 recent syncs per dataset
                start_time = datetime.datetime.now() - datetime.timedelta(hours=i*2)
                end_time = start_time + datetime.timedelta(minutes=random.randint(1, 15))
                status = random.choice(statuses)
                records = random.randint(50, 1000) if status == 'success' else 0
                error_msg = 'Connection timeout' if status == 'failed' else None

                cur.execute("""
                    INSERT INTO sync_logs (
                        schedule_id, dataset_id, start_time, end_time,
                        status, records_processed, error_message
                    ) VALUES (%s, %s, %s, %s, %s, %s, %s)
                """, (
                    schedule_id, dataset_id, start_time, end_time,
                    status, records, error_msg
                ))

    conn.commit()
    conn.close()
    print("Sample data inserted successfully")

def main():
    """Main setup function"""
    print("Setting up CKAN Sync Dashboard database...")

    # Create database
    if not create_database_if_not_exists():
        print("Failed to create database. Please check your PostgreSQL configuration.")
        return False

    try:
        # Create tables
        create_tables()

        # Insert sample data
        insert_sample_data()

        print("\n✅ Database setup completed successfully!")
        print("\nNext steps:")
        print("1. Copy .env.example to .env and configure your settings")
        print("2. Run: pip install -r dashboard_requirements.txt")
        print("3. Run: python dashboard_app.py")
        print("4. Open http://localhost:5001 in your browser")

        return True

    except psycopg2.Error as e:
        print(f"Database error: {e}")
        return False
    except Exception as e:
        print(f"Unexpected error: {e}")
        return False

if __name__ == "__main__":
    main()