# OpenData Platform

CKAN-based open data platform deployment configuration.

## Project Structure

- `ckan-stack/` - CKAN Docker deployment configuration
- `cms-ckan-sync/` - CMS to CKAN data synchronization service
- `ckanext-plateau-harvester/` - PLATEAU data harvester extension
- `ec2-scheduler/` - EC2 auto-scheduling (Terraform)
- `docs/` - Project documentation
- `scripts/` - Utility scripts

## Quick Start

1. Copy environment file:
   ```bash
   cp ckan-stack/.env.example ckan-stack/.env
   # Edit .env with your values
   ```

2. Start services:
   ```bash
   cd ckan-stack
   docker compose up -d
   ```

3. Access CKAN at https://opendata.uixai.org

## Documentation

See `docs/` directory for detailed documentation.
