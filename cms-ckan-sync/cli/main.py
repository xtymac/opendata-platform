#!/usr/bin/env python3
"""CLI entry point for CMS-CKAN Sync Service"""

import argparse
import json
import sys
from pathlib import Path

# Add parent directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from sync_service.config import load_config, validate_config
from sync_service.core import SyncService
from sync_service.models import SyncStatusEnum
from sync_service.logger import setup_logger


def print_result(result, verbose=False):
    """Print a sync result in human-readable format"""
    status_emoji = {
        SyncStatusEnum.SUCCESS: '\u2705',
        SyncStatusEnum.PARTIAL: '\u26a0\ufe0f',
        SyncStatusEnum.FAILED: '\u274c',
        SyncStatusEnum.IN_PROGRESS: '\u23f3',
        SyncStatusEnum.PENDING: '\u23f8\ufe0f'
    }

    emoji = status_emoji.get(result.status, '\u2753')
    print(f"\n{emoji} Model: {result.model_id}")
    print(f"   Status: {result.status.value}")
    print(f"   Records fetched: {result.records_fetched}")
    print(f"   Records transformed: {result.records_transformed}")
    print(f"   Resources uploaded: {result.resources_uploaded}")

    if result.dataset_url:
        print(f"   Dataset URL: {result.dataset_url}")

    if result.duration_seconds:
        print(f"   Duration: {result.duration_seconds:.2f}s")

    if result.warnings:
        print("   Warnings:")
        for warning in result.warnings:
            print(f"     - {warning}")

    if result.errors:
        print("   Errors:")
        for error in result.errors:
            print(f"     - {error}")


def main():
    parser = argparse.ArgumentParser(
        description='CMS-CKAN Sync Service - Synchronize data from Re:Earth CMS to CKAN',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog="""
Examples:
  %(prog)s                     Sync all configured models
  %(prog)s --models public_facility  Sync specific model
  %(prog)s --smart             Update existing resources by name (recommended)
  %(prog)s --dry-run           Preview without uploading
  %(prog)s --force             Delete existing resources before upload
  %(prog)s --json              Output results as JSON
  %(prog)s --status            Show current status
  %(prog)s --test              Test connections to CMS and CKAN
"""
    )

    parser.add_argument(
        '--models', '-m',
        nargs='+',
        help='Specific models to sync (default: all configured models)'
    )

    parser.add_argument(
        '--dry-run', '-n',
        action='store_true',
        help='Preview sync without uploading to CKAN'
    )

    parser.add_argument(
        '--force', '-f',
        action='store_true',
        help='Force re-upload by deleting existing resources first'
    )

    parser.add_argument(
        '--smart', '-u',
        action='store_true',
        help='Smart sync: update existing resources by name, create only if not found'
    )

    parser.add_argument(
        '--json', '-j',
        action='store_true',
        help='Output results as JSON'
    )

    parser.add_argument(
        '--status', '-s',
        action='store_true',
        help='Show current sync status and exit'
    )

    parser.add_argument(
        '--test', '-t',
        action='store_true',
        help='Test connections to CMS and CKAN'
    )

    parser.add_argument(
        '--history',
        type=int,
        metavar='N',
        help='Show last N sync history entries'
    )

    parser.add_argument(
        '--env-file',
        help='Path to .env file (default: .env in current directory)'
    )

    parser.add_argument(
        '--config-file',
        help='Path to models.yaml config file'
    )

    parser.add_argument(
        '--verbose', '-v',
        action='store_true',
        help='Enable verbose output'
    )

    args = parser.parse_args()

    # Load configuration
    try:
        config = load_config(env_file=args.env_file, models_file=args.config_file)
    except Exception as e:
        print(f"Error loading configuration: {e}", file=sys.stderr)
        sys.exit(1)

    # Validate configuration
    errors = validate_config(config)
    if errors:
        print("Configuration errors:", file=sys.stderr)
        for error in errors:
            print(f"  - {error}", file=sys.stderr)
        sys.exit(1)

    # Setup logger
    log_level = 'DEBUG' if args.verbose else config.log_level
    setup_logger(level=log_level, log_dir=config.data_dir)

    # Initialize service
    service = SyncService(config)

    # Handle --test
    if args.test:
        print("Testing connections...")
        connections = service.test_connections()

        if args.json:
            print(json.dumps(connections, indent=2))
        else:
            for name, status in connections.items():
                emoji = '\u2705' if status else '\u274c'
                print(f"  {emoji} {name.upper()}: {'Connected' if status else 'Failed'}")

        sys.exit(0 if all(connections.values()) else 1)

    # Handle --status
    if args.status:
        status = service.get_status()

        if args.json:
            print(json.dumps(status.to_dict(), indent=2))
        else:
            print("\n=== CMS-CKAN Sync Service Status ===")
            print(f"Running: {status.is_running}")
            if status.current_model:
                print(f"Current model: {status.current_model}")
            if status.last_run:
                print(f"Last run: {status.last_run.isoformat()}")
            print(f"Total syncs: {status.total_syncs}")
            print(f"Successful: {status.successful_syncs}")
            print(f"Failed: {status.failed_syncs}")

            print("\n--- Configured Models ---")
            for model in status.models:
                last_status = model.last_sync.status.value if model.last_sync else "never"
                print(f"  - {model.model_id}: {model.ckan_dataset_name} (last: {last_status})")

        sys.exit(0)

    # Handle --history
    if args.history:
        history = service.get_history(limit=args.history)

        if args.json:
            print(json.dumps([r.to_dict() for r in history], indent=2))
        else:
            print(f"\n=== Last {len(history)} Sync Results ===")
            for result in history:
                print_result(result, verbose=args.verbose)

        sys.exit(0)

    # Run sync
    print("=" * 60)
    print("CMS-CKAN Sync Service")
    print("=" * 60)

    if args.dry_run:
        print("\n** DRY RUN MODE - No data will be uploaded **\n")

    if args.force:
        print("\n** FORCE MODE - Existing resources will be deleted **\n")

    if args.smart:
        print("\n** SMART MODE - Will update existing resources by name **\n")

    # Show configured models
    if args.models:
        model_ids = args.models
        # Validate model IDs
        for model_id in model_ids:
            if model_id not in config.models:
                print(f"Error: Unknown model '{model_id}'", file=sys.stderr)
                print(f"Available models: {', '.join(config.get_all_model_ids())}", file=sys.stderr)
                sys.exit(1)
    else:
        model_ids = config.get_all_model_ids()

    print(f"Models to sync: {', '.join(model_ids)}")

    # Run sync
    if args.smart:
        # Smart mode: use sync_model_smart for each model
        results = []
        for model_id in model_ids:
            if args.dry_run:
                # For dry-run in smart mode, use regular sync with dry_run flag
                result = service.sync_model(model_id, dry_run=True)
            else:
                result = service.sync_model_smart(model_id)
            results.append(result)
    else:
        # Default mode: use sync_all
        results = service.sync_all(
            model_ids=model_ids,
            dry_run=args.dry_run,
            force=args.force
        )

    # Output results
    if args.json:
        print(json.dumps([r.to_dict() for r in results], indent=2))
    else:
        print("\n=== Sync Results ===")
        for result in results:
            print_result(result, verbose=args.verbose)

        # Summary
        success = sum(1 for r in results if r.status == SyncStatusEnum.SUCCESS)
        failed = sum(1 for r in results if r.status == SyncStatusEnum.FAILED)

        print("\n" + "=" * 60)
        print(f"Summary: {success} success, {failed} failed")
        print("=" * 60)

    # Exit with error if any failed
    if any(r.status == SyncStatusEnum.FAILED for r in results):
        sys.exit(1)

    sys.exit(0)


if __name__ == '__main__':
    main()
