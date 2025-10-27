#!/bin/bash

# SQLite Backup Script for TradeProject
# Creates timestamped backups of the trading database

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_DIR="$(dirname "$SCRIPT_DIR")"

DB_PATH="$PROJECT_DIR/mac_coordinator/data/trades.db"
BACKUP_DIR="$PROJECT_DIR/backups"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
BACKUP_FILE="$BACKUP_DIR/trades_$TIMESTAMP.db"

mkdir -p "$BACKUP_DIR"

if [ ! -f "$DB_PATH" ]; then
    echo "Error: Database file not found at $DB_PATH"
    exit 1
fi

echo "Backing up database..."
echo "Source: $DB_PATH"
echo "Destination: $BACKUP_FILE"

cp "$DB_PATH" "$BACKUP_FILE"

if [ $? -eq 0 ]; then
    echo "Backup completed successfully"
    
    BACKUP_SIZE=$(du -h "$BACKUP_FILE" | cut -f1)
    echo "Backup size: $BACKUP_SIZE"
    
    CSV_PATH="$PROJECT_DIR/mac_coordinator/data/trades.csv"
    if [ -f "$CSV_PATH" ]; then
        CSV_BACKUP="$BACKUP_DIR/trades_$TIMESTAMP.csv"
        cp "$CSV_PATH" "$CSV_BACKUP"
        echo "CSV backup: $CSV_BACKUP"
    fi
    
    find "$BACKUP_DIR" -name "trades_*.db" -mtime +30 -delete
    echo "Cleaned up backups older than 30 days"
    
else
    echo "Error: Backup failed"
    exit 1
fi

exit 0
