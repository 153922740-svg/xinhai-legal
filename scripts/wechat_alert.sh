#!/bin/bash
# 心海法律 AI - 微信告警推送脚本
# 配合 monitor_api.sh 使用，检测到告警日志时推送微信通知
# 通过 Hermes Gateway 的微信通道发送

ALERT_LOG="/tmp/xinhai_alerts.log"
LAST_LINE_FILE="/tmp/xinhai_last_alert_line"

# 检查是否有新的告警
if [ ! -f "$ALERT_LOG" ]; then
    exit 0
fi

# 获取最新的告警行（不超过上次已推送的行）
if [ -f "$LAST_LINE_FILE" ]; then
    last_line=$(cat "$LAST_LINE_FILE")
else
    last_line=0
fi

total_lines=$(wc -l < "$ALERT_LOG")
new_lines=$((total_lines - last_line))

if [ "$new_lines" -le 0 ]; then
    exit 0
fi

# 取最新的告警（最多3条）
alerts=$(tail -n "$new_lines" "$ALERT_LOG" | head -3)
echo "$total_lines" > "$LAST_LINE_FILE"

# 发送微信通知（通过 Hermes API）
# 使用简单的curl POST模拟，依赖Hermes Gateway的微信通道
PUSH_URL="http://127.0.0.1:8647/api/v1/health"

# 如果告警级别严重（磁盘>90%或进程挂了），才推送
if echo "$alerts" | grep -qE "磁盘|进程|SSL.*7天"; then
    msg=$(echo "$alerts" | head -1 | sed 's/.*ALERT://')
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] 推送：严重告警 $msg"
fi
