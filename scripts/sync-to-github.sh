#!/bin/bash
set -e
REPO_DIR="/home/ubuntu/opendata-platform"

# Ensure repo exists
if [ ! -d "$REPO_DIR/.git" ]; then
    echo "Error: $REPO_DIR is not a git repository"
    exit 1
fi

cd "$REPO_DIR"

# Pull remote updates first (avoid conflicts)
git pull --rebase origin main || true

# Sync each project (exclude .git to prevent nested repos)
echo "Syncing ckan-stack..."
rsync -av --delete --exclude='.git/' --exclude='.env' --exclude='secrets/' --exclude='.ckan-local/' --exclude='webmaps/' --exclude='.dev/' \
    /home/ubuntu/ckan-stack/ ckan-stack/

echo "Syncing cms-ckan-sync..."
rsync -av --delete --exclude='.git/' --exclude='.env' --exclude='data/*.log' --exclude='data/sync_history.json' \
    /home/ubuntu/cms-ckan-sync/ cms-ckan-sync/

echo "Syncing ckanext-plateau-harvester..."
rsync -av --delete --exclude='.git/' --exclude='__pycache__/' \
    /home/ubuntu/ckanext-plateau-harvester/ ckanext-plateau-harvester/

echo "Syncing ec2-scheduler..."
rsync -av --delete --exclude='.git/' --exclude='.terraform/' --exclude='*.tfstate*' --exclude='*.zip' \
    /home/ubuntu/ec2-scheduler/ ec2-scheduler/

echo "Syncing docs..."
rsync -av --delete --exclude='.git/' /home/ubuntu/doc/ docs/

echo "Syncing scripts..."
rsync -av /home/ubuntu/*.py /home/ubuntu/*.sh scripts/ 2>/dev/null || true

# Commit and push
git add -A
if ! git diff --cached --quiet; then
    git commit -m "Sync from EC2 $(TZ=Asia/Tokyo date '+%Y-%m-%d %H:%M')"
    git push origin main
    echo "Changes pushed to GitHub"
else
    echo "No changes to commit"
fi
