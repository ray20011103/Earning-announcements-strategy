#!/bin/bash

# 設定專案路徑
PROJECT_DIR="/Users/ray/Library/CloudStorage/OneDrive-NationalChengChiUniversity/營收策略"
LOG_FILE="$PROJECT_DIR/logs/scan_log.txt"

# 取得現在時間
echo "========================================" >> "$LOG_FILE"
echo "Starting Process: $(date)" >> "$LOG_FILE"

# 切換目錄
cd "$PROJECT_DIR" || { echo "Failed to cd to $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# 啟動虛擬環境 (venv)
if [ -d "venv" ]; then
    source venv/bin/activate
fi

# Step 1: 檢查並更新股價資料
if [ -f "price_daily.csv" ]; then
    echo "Found price_daily.csv. Updating database..." >> "$LOG_FILE"
    python3 update_data.py >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "Data Update Successful." >> "$LOG_FILE"
    else
        echo "Data Update Failed! Check log." >> "$LOG_FILE"
        # 即使更新失敗，可能還是可以用舊資料跑掃描，或者選擇中止
        # 這裡選擇繼續，但發出警告
    fi
else
    echo "No price_daily.csv found. Skipping data update." >> "$LOG_FILE"
fi

# Step 2: 執行策略掃描
echo "Running Strategy Scanner..." >> "$LOG_FILE"
python3 live_strategy_scanner.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "Process Finished Successfully: $(date)" >> "$LOG_FILE"
    # Mac Notification
    osascript -e 'display notification "營收策略掃描完成！" with title "Strategy Bot"'
else
    echo "Scanner Failed with exit code $EXIT_CODE: $(date)" >> "$LOG_FILE"
    osascript -e 'display notification "策略執行失敗，請檢查 Log。" with title "Strategy Bot Error"'
fi

echo "========================================" >> "$LOG_FILE"
