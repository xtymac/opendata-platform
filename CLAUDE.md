# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a customized CKAN (Open Source Data Portal) instance with custom modifications for dataset management, group/organization handling, and enhanced UI features. CKAN is built on Python/Flask with PostgreSQL backend and Solr for search functionality.

## Development Commands

### Testing
```bash
# Run all tests with pytest
python -m pytest

# Run specific test modules
python -m pytest ckan/tests/

# Run tests with custom configuration
python -m pytest --ckan-ini=test-core.ini

# Run tests in parallel (for CI)
python -m pytest --splits 2 --group 1 --splitting-algorithm least_duration
```

### CKAN Server
```bash
# Run CKAN development server
ckan -c ckan.ini run

# Initialize database
ckan -c ckan.ini db init

# Create admin user
ckan user add admin email=admin@example.com password=admin123
ckan sysadmin add admin

# Run with specific config
ckan -c test-core.ini run
```

### Docker Deployment
```bash
# Quick Docker setup (includes PostgreSQL, Solr, etc.)
./docker-setup.sh

# Manual Docker Compose
docker-compose up -d
```

### Code Quality
```bash
# Run linting with ruff
ruff check .

# Type checking with pyright
pyright

# Type checking with mypy (limited to ckan/ directory)
mypy ckan/
```

## Architecture Overview

### Core Data Model (/workspace/ckan/model/)
- **Package** (`package.py`): Core dataset entity with metadata fields (title, description, etc.) and JSONB extras for custom fields
- **Resource** (`resource.py`): Files/URLs attached to datasets, with structured metadata columns (url, format, description) plus JSONB extras
- **Group/Organization** (`group.py`): Hierarchical organizations and thematic groups for dataset categorization
- **Tag** (`tag.py`): Tagging system with vocabulary support
- **User** (`user.py`): User accounts and authentication

### Views Layer (/workspace/ckan/views/)
- **dataset.py**: Dataset CRUD operations and form handling
- **resource.py**: Resource management and file uploads
- **group.py**: Group/organization management
- **api.py**: REST API endpoints

### Extensions System (/workspace/ckanext/)
Built-in extensions include:
- **datastore**: Database storage for structured data
- **datapusher**: Automatic data importing
- **tabledesigner**: Enhanced tabular data editing
- **stats**: Usage analytics
- **multilingual**: Multi-language support

### Custom Modifications
- **Groups handling**: Enhanced JavaScript for dataset-group associations (`/workspace/ckan/public/base/javascript/groups-handler.js`)
- **Template customizations**: Modified package forms in `/workspace/ckan/templates/package/snippets/`
- **Utility scripts**: Group management (`create_groups.py`), duplicate cleanup (`remove_duplicates.py`)

## Configuration Files

- **test-core.ini**: Test environment configuration with PostgreSQL test databases
- **pyproject.toml**: Python packaging, pytest configuration, code quality tools (ruff, pyright, mypy)
- **docker-setup.sh**: Automated Docker deployment script

## Database Architecture

CKAN uses PostgreSQL with the following key patterns:
- **Structured columns** for core metadata (efficient queries, indexing)
- **JSONB fields** for flexible custom metadata (package.extras, resource.extras)
- **Foreign key relationships** maintaining data integrity
- **State management** for soft deletes and workflow states

## Key Development Patterns

1. **Plugin Architecture**: Extend functionality via IPlugin interfaces
2. **Action API**: All operations go through action functions in `ckan/logic/action/`
3. **Authorization**: Permission checks via auth functions in `ckan/logic/auth/`
4. **Template Inheritance**: Jinja2 templates with block-based customization
5. **Configuration Declaration**: Type-safe config in `ckan/config/declaration/`

## Custom Scripts Usage

```bash
# Check groups/organizations structure
python check_groups_orgs.py

# Create predefined groups
python create_groups.py

# Remove duplicate datasets
python remove_duplicates.py
```

## Testing Strategy

- **Unit tests**: Individual component testing
- **Integration tests**: API and database interaction testing
- **Functional tests**: End-to-end workflow testing
- **Custom markers**: `@pytest.mark.ckan_config`, `@pytest.mark.with_plugins`

Tests are configured to use `test-core.ini` with separate test databases to avoid data contamination.