#!/bin/bash

# 自動偵測目前檔案所在目錄
PROJECT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
LOG_FILE="$PROJECT_DIR/logs/scan_log.txt"

# 建立 logs 資料夾 (如果不存在)
mkdir -p "$PROJECT_DIR/logs"

echo "========================================" >> "$LOG_FILE"
echo "執行時間: $(date)" >> "$LOG_FILE"
echo "工作目錄: $PROJECT_DIR" >> "$LOG_FILE"

# 切換目錄
cd "$PROJECT_DIR" || { echo "無法進入目錄 $PROJECT_DIR" >> "$LOG_FILE"; exit 1; }

# 啟動虛擬環境 (venv)
if [ -d "venv" ]; then
    source venv/bin/activate
    echo "使用虛擬環境 (venv)..." >> "$LOG_FILE"
else
    echo "警告: 找不到 venv，嘗試使用系統 Python..." >> "$LOG_FILE"
fi

# Step 1: 資料更新 (對應 TEJ 複製貼上的 price_daily.csv)
if [ -f "price_daily.csv" ]; then
    echo "偵測到 price_daily.csv，正在更新資料庫..." >> "$LOG_FILE"
    python3 update_data.py >> "$LOG_FILE" 2>&1
    
    if [ $? -eq 0 ]; then
        echo "資料庫更新成功。" >> "$LOG_FILE"
    else
        echo "資料庫更新失敗！" >> "$LOG_FILE"
    fi
else
    echo "未發現 price_daily.csv，略過更新。" >> "$LOG_FILE"
fi

# Step 2: 執行策略掃描
echo "執行策略掃描程式 (live_strategy_scanner.py)..." >> "$LOG_FILE"
python3 live_strategy_scanner.py >> "$LOG_FILE" 2>&1

EXIT_CODE=$?

if [ $EXIT_CODE -eq 0 ]; then
    echo "全流程成功結束: $(date)" >> "$LOG_FILE"
    osascript -e 'display notification "營收策略掃描完成！報告已生成。" with title "策略掃描機器人"'
else
    echo "掃描程式回報錯誤 (代碼 $EXIT_CODE): $(date)" >> "$LOG_FILE"
    osascript -e 'display notification "策略執行失敗，請開啟 logs/scan_log.txt 檢查。" with title "策略報錯"'
fi

echo "========================================" >> "$LOG_FILE"
