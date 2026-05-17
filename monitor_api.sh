#!/bin/bash
# 心海法律 AI - API 服务监控脚本
# 用途：监控 API 服务健康状态，异常时告警

LOG_FILE="/tmp/xinhai_monitor.log"
ALERT_LOG="/tmp/xinhai_alerts.log"

# API 端点列表
ENDPOINTS=(
    "http://localhost:5000/api/v1/health"
    "http://localhost:5000/api/v2/membership/health"
    "http://localhost:5000/api/v2/token/health"
    "http://localhost:5000/api/v2/dashboard/health"
    "http://localhost:5000/api/v3/document/health"
    "http://localhost:5000/api/v3/contract/health"
    "http://localhost:5000/api/v4/health"
    "http://localhost:5000/api/v5/health"
)

# 告警阈值 (连续失败次数)
ALERT_THRESHOLD=3

# 计数文件目录
COUNT_DIR="/tmp/xinhai_monitor_counts"
mkdir -p $COUNT_DIR

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

alert() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  ALERT: $1" | tee -a $ALERT_LOG
}

check_endpoint() {
    local url=$1
    local name=$(echo $url | sed 's|http://localhost:5000/||' | sed 's|/|_|g')
    local count_file="$COUNT_DIR/$name.count"
    
    # 初始化计数文件
    if [ ! -f "$count_file" ]; then
        echo "0" > "$count_file"
    fi
    
    # 检查端点
    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)
    
    if [ "$response" = "200" ]; then
        # 成功，重置计数
        echo "0" > "$count_file"
        log "✅ $url - OK (HTTP $response)"
        return 0
    else
        # 失败，增加计数
        count=$(cat "$count_file")
        count=$((count + 1))
        echo "$count" > "$count_file"
        
        log "❌ $url - FAILED (HTTP $response, Count: $count)"
        
        # 检查是否达到告警阈值
        if [ "$count" -ge "$ALERT_THRESHOLD" ]; then
            alert "$url 连续失败 $count 次 (HTTP $response)"
            return 1
        fi
        return 1
    fi
}

check_process() {
    local process_name=$1
    local count=$(ps aux | grep "$process_name" | grep -v grep | wc -l)
    
    if [ "$count" -gt 0 ]; then
        log "✅ 进程 $process_name 运行中 (PID 数量：$count)"
        return 0
    else
        alert "进程 $process_name 未运行!"
        return 1
    fi
}

check_disk() {
    local usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    
    if [ "$usage" -gt 90 ]; then
        alert "磁盘使用率过高：${usage}%"
        return 1
    elif [ "$usage" -gt 80 ]; then
        log "⚠️  磁盘使用率警告：${usage}%"
        return 0
    else
        log "✅ 磁盘使用率正常：${usage}%"
        return 0
    fi
}

check_memory() {
    local available=$(free -m | awk '/^Mem:/ {print $7}')
    local total=$(free -m | awk '/^Mem:/ {print $2}')
    local usage_percent=$(( (total - available) * 100 / total ))
    
    if [ "$usage_percent" -gt 90 ]; then
        alert "内存使用率过高：${usage_percent}%"
        return 1
    elif [ "$usage_percent" -gt 80 ]; then
        log "⚠️  内存使用率警告：${usage_percent}%"
        return 0
    else
        log "✅ 内存使用率正常：${usage_percent}%"
        return 0
    fi
}

# ============== 主监控流程 ==============

log "========== 开始监控检查 =========="

# 1. 检查进程
check_process "python app.py"
check_process "nginx"

# 2. 检查系统资源
check_disk
check_memory

# 3. 检查所有 API 端点
failed_count=0
for endpoint in "${ENDPOINTS[@]}"; do
    if ! check_endpoint "$endpoint"; then
        failed_count=$((failed_count + 1))
    fi
done

# 4. 汇总报告
total_endpoints=${#ENDPOINTS[@]}
healthy_endpoints=$((total_endpoints - failed_count))

log "========== 监控汇总 =========="
log "健康检查：$healthy_endpoints/$total_endpoints 端点正常"

if [ "$failed_count" -gt 0 ]; then
    alert "$failed_count 个 API 端点异常"
fi

log "========== 监控检查完成 =========="
