# CKAN Sync Dashboard - Quick Start Guide

A real-time monitoring dashboard for CKAN data synchronization with automated scheduling, monitoring, and alerting.

## 🚀 Quick Test (Simplified Version)

For immediate testing without database setup:

```bash
# 1. Install dependencies
pip install flask flask-cors axios

# 2. Run the simplified dashboard
python simplified_dashboard.py

# 3. Open browser
# Visit: http://localhost:5001
```

The simplified version uses SQLite and includes sample data for immediate testing.

## 📊 Test Link

**Dashboard URL: http://localhost:5001**

## 🏗️ Full Setup (PostgreSQL Version)

### Prerequisites
- Python 3.8+
- PostgreSQL 12+
- CKAN instance (optional for testing)

### Installation Steps

1. **Install Dependencies**
   ```bash
   pip install -r dashboard_requirements.txt
   ```

2. **Database Setup**
   ```bash
   # Create PostgreSQL database
   createdb ckan_sync

   # Copy and configure environment
   cp .env.example .env
   # Edit .env with your database credentials
   ```

3. **Initialize Database**
   ```bash
   python setup_database.py
   ```

4. **Run Dashboard**
   ```bash
   python dashboard_app.py
   ```

5. **Access Dashboard**
   - Open: http://localhost:5001
   - View real-time sync status
   - Monitor performance metrics
   - Manage dataset schedules

## 📋 Features

### Dashboard Features
- ✅ Real-time sync status monitoring
- 📈 Performance metrics and charts
- 🔄 Manual sync triggers
- 📊 Historical timeline view
- ⚠️ Failure analysis panel
- 📱 Mobile-responsive design

### Sync System Features
- 🕐 Flexible scheduling (hourly, daily, weekly, monthly)
- 🔗 Multiple data source support (API, CSV, JSON, XML, Database)
- 🔄 Automatic retries with backoff
- 📧 Multi-channel alerts (Email, Slack, Webhook)
- 📝 Detailed logging and error tracking
- 🎯 CKAN API integration

## 🔧 Configuration

### Environment Variables (.env)
```bash
# CKAN Configuration
CKAN_URL=http://localhost:5000
CKAN_API_KEY=your-api-key

# Database
DB_HOST=localhost
DB_NAME=ckan_sync
DB_USER=postgres
DB_PASSWORD=your-password

# Alerts (Optional)
EMAIL_ENABLED=true
SLACK_ENABLED=false
WEBHOOK_ENABLED=false
```

## 📱 Dashboard Interface

### Main Dashboard
- **Overview Stats**: Total datasets, success rate, records synced
- **Live Status**: Current sync operations
- **Performance Chart**: Success rate over time
- **Dataset List**: All configured datasets with status
- **Failure Panel**: Recent failures with error details

### Dataset Management
- View detailed sync history
- Manual sync triggers
- Performance metrics
- Error analysis
- Schedule configuration

## 🔄 Sync Operations

### Creating a Sync Schedule
```python
from ckan_sync_system import CKANSyncManager, SyncSchedule

# Initialize manager
config = {...}  # Your configuration
manager = CKANSyncManager(config)

# Create schedule
schedule = SyncSchedule(
    dataset_id='my-dataset',
    dataset_name='My Dataset',
    source_url='https://api.example.com/data',
    sync_frequency='hourly',
    source_type='api'
)

manager.create_schedule(schedule)
```

### Supported Data Sources
- **API**: REST APIs returning JSON
- **CSV**: CSV files from URLs
- **JSON**: JSON data endpoints
- **XML**: XML data sources
- **Database**: SQL database connections
- **CKAN**: Other CKAN instances

## 📊 Monitoring & Alerts

### Alert Channels
- **Email**: SMTP-based notifications
- **Slack**: Webhook integration
- **Custom Webhooks**: REST API notifications

### Alert Types
- Sync failures
- Performance degradation
- Schedule missed
- Daily/weekly summaries

## 🔍 API Endpoints

### Dashboard API
```bash
# Get overview statistics
GET /api/stats

# Get dataset list
GET /api/datasets?page=1&per_page=20

# Get dataset details
GET /api/dataset/{dataset_id}

# Get failure list
GET /api/failures

# Trigger manual sync
POST /api/trigger/{dataset_id}
```

## 🚀 Production Deployment

### Using Apache Airflow (Recommended)
```bash
# Install Airflow
pip install apache-airflow

# Copy DAG file
cp airflow_ckan_dag.py $AIRFLOW_HOME/dags/

# Configure connections in Airflow UI
# - ckan_sync_db: PostgreSQL connection
# - slack_webhook: Slack webhook (optional)
```

### Using Cron (Simple)
```bash
# Add to crontab
0 * * * * cd /path/to/ckan && python ckan_sync_system.py
```

## 🛠️ Troubleshooting

### Common Issues

1. **Database Connection Error**
   - Check PostgreSQL is running
   - Verify credentials in .env
   - Ensure database exists

2. **CKAN API Error**
   - Verify CKAN_URL is accessible
   - Check API key permissions
   - Test with: `curl $CKAN_URL/api/3/action/status_show`

3. **Dashboard Not Loading**
   - Check Flask is running on port 5001
   - Verify no firewall blocking
   - Check browser console for errors

### Debug Mode
```bash
# Run with debug logging
export FLASK_DEBUG=1
python dashboard_app.py
```

## 📈 Performance Tips

### Database Optimization
- Regular cleanup of old logs
- Index maintenance
- Connection pooling for high load

### Sync Optimization
- Adjust timeout values
- Configure appropriate retry counts
- Use parallel processing for multiple datasets

## 🔒 Security Considerations

- Secure API keys in environment variables
- Use HTTPS in production
- Implement proper authentication
- Regular security updates

## 📞 Support

- Check logs in `sync_logs` table
- Review error messages in dashboard
- Monitor system resources
- Validate data source connectivity

## 🎯 Next Steps

1. Configure your CKAN instance connection
2. Add your actual data sources
3. Set up alerting channels
4. Configure production deployment
5. Monitor and optimize performance

---

**Demo Dashboard**: Perfect for testing and demonstration
**Full System**: Production-ready with all features