#!/bin/bash
# Task 1.4: Auto-Backup Script Setup
# Hourly backup of critical Excel files and model checkpoints

BACKUP_DIR="./backups"
EXCEL_FILE="output/Loan4U_QC_v1.1_FINAL.xlsx"
MODELS_DIR="models"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)

mkdir -p "$BACKUP_DIR/hourly"
mkdir -p "$BACKUP_DIR/daily"

backup_excel() {
    if [ -f "$EXCEL_FILE" ]; then
        cp "$EXCEL_FILE" "$BACKUP_DIR/hourly/excel_${TIMESTAMP}.xlsx"
        echo "✅ Excel backup: $BACKUP_DIR/hourly/excel_${TIMESTAMP}.xlsx"
    fi
}

backup_models() {
    find "$MODELS_DIR" -name "*.joblib" -o -name "*.pkl" | \
    while read model; do
        cp "$model" "$BACKUP_DIR/hourly/$(basename $model)_${TIMESTAMP}.bak"
    done
    echo "✅ Models backup complete"
}

cleanup_old_backups() {
    # Keep only last 168 hourly backups (7 days)
    find "$BACKUP_DIR/hourly" -type f -mtime +7 -delete
    echo "✅ Cleanup: Removed backups older than 7 days"
}

# Create backup metadata
create_metadata() {
    cat > "$BACKUP_DIR/backup_metadata.json" << EOF
{
  "timestamp": "$(date -Iseconds)",
  "excel_file": "$EXCEL_FILE",
  "models_dir": "$MODELS_DIR",
  "backup_dir": "$BACKUP_DIR",
  "retention_days": 7,
  "status": "OK"
}
EOF
    echo "✅ Metadata saved"
}

main() {
    echo "============================================================"
    echo "TASK 1.4: AUTO-BACKUP SETUP"
    echo "============================================================"

    backup_excel
    backup_models
    cleanup_old_backups
    create_metadata

    echo ""
    echo "✅ TASK 1.4 COMPLETE: Backup Scripts Ready"
    echo "   Cron schedule: 0 * * * * /path/to/task_1_4_auto_backup_setup.sh"
    echo "   (Run every hour)"
}

main
