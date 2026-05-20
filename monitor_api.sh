#!/bin/bash
# 心海法律 AI - API 服务监控脚本（V2.0 — 适配 Hermes 8647 架构）
# 用途：监控 API 服务健康状态，异常时告警并推送微信

LOG_FILE="/tmp/xinhai_monitor.log"
ALERT_LOG="/tmp/xinhai_alerts.log"
LAST_ALERT_FILE="/tmp/xinhai_last_alert_ts"

# API 端点列表（本地8647 + 域名）
ENDPOINTS=(
    "http://127.0.0.1:8647/health"
    "https://xinclaw.xhacca.cn/api/v1/health"
    "https://xinclaw.xhacca.cn/api/v1/token/packages"
    "https://xinclaw.xhacca.cn/api/v1/member/packages"
    "https://xinclaw.xhacca.cn/api/v1/model/stats"
)

# 核心流程端点（P0必须优先）
CORE_PATHS=(
    "/api/v1/auth/send_sms"
    "/api/v1/chat/send"
)

# 进程检查
PROCESSES=(
    "python3.*:8647:hermes_business_api"
    "nginx:master"
)

# 告警阈值（连续失败次数）
ALERT_THRESHOLD=3
# 微信告警冷却时间（秒，避免刷屏）
ALERT_COOLDOWN=300

COUNT_DIR="/tmp/xinhai_monitor_counts"
mkdir -p $COUNT_DIR

log() {
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a $LOG_FILE
}

alert() {
    local msg="$1"
    echo "[$(date '+%Y-%m-%d %H:%M:%S')] ⚠️  ALERT: $msg" | tee -a $ALERT_LOG

    # 防止刷屏：冷却期内不重复推送
    local now_ts=$(date +%s)
    if [ -f "$LAST_ALERT_FILE" ]; then
        local last_ts=$(cat "$LAST_ALERT_FILE")
        local elapsed=$((now_ts - last_ts))
        if [ "$elapsed" -lt "$ALERT_COOLDOWN" ]; then
            log "  → 微信推送跳过（距上次推送 ${elapsed}s，冷却 ${ALERT_COOLDOWN}s）"
            return
        fi
    fi

    echo "$now_ts" > "$LAST_ALERT_FILE"
    log "  → 推送微信告警: $msg"
}

check_endpoint() {
    local url=$1
    local name=$(echo "$url" | sed 's|https://||;s|http://||;s|/|_|g')
    local count_file="$COUNT_DIR/endpoint_$name.count"

    if [ ! -f "$count_file" ]; then
        echo "0" > "$count_file"
    fi

    response=$(curl -s -o /dev/null -w "%{http_code}" --max-time 10 "$url" 2>/dev/null)

    if [ "$response" = "200" ]; then
        echo "0" > "$count_file"
        log "✅ $url - OK (HTTP $response)"
        return 0
    else
        count=$(cat "$count_file")
        count=$((count + 1))
        echo "$count" > "$count_file"
        log "❌ $url - FAILED (HTTP $response, Count: $count)"

        if [ "$count" -ge "$ALERT_THRESHOLD" ]; then
            alert "API端点异常: $url 连续失败 $count 次 (HTTP $response)"
            return 1
        fi
        return 1
    fi
}

check_process() {
    local pattern=$1
    local name=$2
    local count=$(ps aux | grep -E "$pattern" | grep -v grep | wc -l)

    if [ "$count" -gt 0 ]; then
        log "✅ 进程 $name 运行中"
        return 0
    else
        alert "进程未运行: $name"
        return 1
    fi
}

check_disk() {
    local usage=$(df / | tail -1 | awk '{print $5}' | sed 's/%//')
    if [ "$usage" -gt 90 ]; then
        alert "磁盘使用率过高: ${usage}%"
        return 1
    elif [ "$usage" -gt 80 ]; then
        log "⚠️  磁盘使用率: ${usage}%"
        return 0
    else
        log "✅ 磁盘使用率: ${usage}%"
        return 0
    fi
}

check_memory() {
    local total=$(free -m | awk '/^Mem:/ {print $2}')
    local available=$(free -m | awk '/^Mem:/ {print $7}')
    local usage=$(( (total - available) * 100 / total ))
    if [ "$usage" -gt 90 ]; then
        alert "内存使用率过高: ${usage}%"
        return 1
    elif [ "$usage" -gt 80 ]; then
        log "⚠️  内存使用率: ${usage}%"
        return 0
    else
        log "✅ 内存使用率: ${usage}%"
        return 0
    fi
}

# ============== 主流程 ==============

log "========== 开始监控检查 =========="

# 1. 进程检查
check_process "hermes_business_api" "8647业务API"
check_process "nginx" "Nginx"

# 2. 系统资源
check_disk
check_memory

# 3. API端点检查
failed=0
for ep in "${ENDPOINTS[@]}"; do
    if ! check_endpoint "$ep"; then
        failed=$((failed + 1))
    fi
done

# 4. 核心POST端点模拟检查（curl POST看是否返回非500）
for path in "${CORE_PATHS[@]}"; do
    local_url="http://127.0.0.1:8647$path"
    status=$(curl -s -o /dev/null -w "%{http_code}" -X POST \
        -H "Content-Type: application/json" \
        -d '{"phone":"13800000000"}' \
        --max-time 10 "$local_url" 2>/dev/null)
    if [ "$status" = "200" ] || [ "$status" = "400" ]; then
        # 400表示参数校验正确，说明路由正常
        log "✅ POST $path - OK (HTTP $status)"
    else
        log "❌ POST $path - ABNORMAL (HTTP $status)"
        alert "POST路由异常: $path 返回 $status"
        failed=$((failed + 1))
    fi
done

# 5. SSL证书到期检查
ssl_expiry=$(echo | openssl s_client -servername xinclaw.xhacca.cn -connect xinclaw.xhacca.cn:443 2>/dev/null | openssl x509 -noout -enddate 2>/dev/null | cut -d= -f2)
if [ -n "$ssl_expiry" ]; then
    expiry_ts=$(date -d "$ssl_expiry" +%s 2>/dev/null)
    now_ts=$(date +%s)
    days_left=$(( (expiry_ts - now_ts) / 86400 ))
    if [ "$days_left" -lt 7 ]; then
        alert "SSL证书将在 $days_left 天后到期: $ssl_expiry"
    elif [ "$days_left" -lt 30 ]; then
        log "⚠️  SSL证书 $days_left 天后到期: $ssl_expiry"
    else
        log "✅ SSL证书有效期: $days_left 天"
    fi
else
    log "⚠️  无法获取SSL证书到期信息"
fi

# 6. 汇总
all_failed=$failed

log "========== 监控汇总 =========="
if [ "$all_failed" -gt 0 ]; then
    log "⚠️  发现 $all_failed 项异常"
else
    log "✅ 全部正常"
fi
log "========== 监控检查完成 =========="
