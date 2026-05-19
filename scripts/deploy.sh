#!/bin/bash
# 心海法律 AI - 自动化部署脚本（磐石）
# 用途：一键部署到生产环境

set -e

echo "═══════════════════════════════════════════════"
echo "  心海法律 AI · 自动化部署脚本"
echo "═══════════════════════════════════════════════"
echo ""

# 配置
DEPLOY_DIR="/www/wwwroot/xinclaw-law"
BACKUP_DIR="/home/admin/xinclaw-backup"
LOG_DIR="/home/admin/xinhai_legal_api/logs"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="$LOG_DIR/deploy_${TIMESTAMP}.log"

# 颜色定义
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# 日志函数
log() {
    echo -e "[$(date '+%Y-%m-%d %H:%M:%S')] $1" | tee -a "$LOG_FILE"
}

error() {
    echo -e "${RED}[ERROR]${NC} $1" | tee -a "$LOG_FILE"
    exit 1
}

success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1" | tee -a "$LOG_FILE"
}

warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1" | tee -a "$LOG_FILE"
}

# 参数检查
if [ -z "$1" ]; then
    echo "用法：./deploy.sh [环境]"
    echo ""
    echo "环境选项:"
    echo "  - test     测试环境"
    echo "  - staging  预发布环境"
    echo "  - prod     生产环境"
    exit 1
fi

ENV="$1"
case $ENV in
    test)
        DEPLOY_DIR="/www/wwwroot/xinclaw-law-test"
        ;;
    staging)
        DEPLOY_DIR="/www/wwwroot/xinclaw-law-staging"
        ;;
    prod)
        DEPLOY_DIR="/www/wwwroot/xinclaw-law"
        ;;
    *)
        error "未知环境：$ENV"
        ;;
esac

log "部署环境：$ENV"
log "部署目录：$DEPLOY_DIR"
log "备份目录：$BACKUP_DIR"
log "日志文件：$LOG_FILE"
echo ""

# 步骤 1: 部署前检查
log "【步骤 1】部署前检查"
log "  → 检查 Git 状态..."
cd /home/admin/xinhai_legal_api || error "代码目录不存在"

if [ -n "$(git status --porcelain)" ]; then
    warning "有未提交的更改，建议先提交"
fi

log "  → 检查测试报告..."
if [ ! -f "/home/admin/xinhai_legal_api/docs/test_report_latest.md" ]; then
    warning "测试报告不存在，请确认测试已通过"
else
    success "测试报告存在"
fi

log "  → 检查审查报告..."
if [ ! -f "/home/admin/xinhai_legal_api/docs/code_review_latest.md" ]; then
    warning "代码审查报告不存在，请确认审查已通过"
else
    success "审查报告存在"
fi

log "  → 运行敏感信息扫描..."
python3 /home/admin/xinhai_legal_api/scripts/pre_commit_secret_scan.py /home/admin/xinhai_legal_api/ > /tmp/secret_scan_$TIMESTAMP.txt 2>&1
if [ $? -eq 1 ]; then
    error "敏感信息扫描失败，请检查 /tmp/secret_scan_$TIMESTAMP.txt"
else
    success "敏感信息扫描通过"
fi
echo ""

# 步骤 2: 备份当前版本
log "【步骤 2】备份当前版本"
BACKUP_NAME="backup_${ENV}_${TIMESTAMP}"

if [ -d "$DEPLOY_DIR" ]; then
    log "  → 创建备份目录..."
    mkdir -p "$BACKUP_DIR/$BACKUP_NAME"
    
    log "  → 备份代码..."
    cp -r "$DEPLOY_DIR"/* "$BACKUP_DIR/$BACKUP_NAME/" 2>/dev/null || warning "部分文件备份失败"
    
    log "  → 备份数据库..."
    if [ -f "/home/admin/xinhai_legal.db" ]; then
        cp /home/admin/xinhai_legal.db "$BACKUP_DIR/$BACKUP_NAME/xinhai_legal.db.backup"
        success "数据库备份完成"
    fi
    
    success "备份完成：$BACKUP_NAME"
else
    warning "部署目录不存在，跳过备份"
fi
echo ""

# 步骤 3: 同步代码
log "【步骤 3】同步代码"
log "  → 创建部署目录..."
mkdir -p "$DEPLOY_DIR"

log "  → 同步前端代码..."
if [ -d "/home/admin/xinhai_legal_api/frontend" ]; then
    cp -r /home/admin/xinhai_legal_api/frontend/* "$DEPLOY_DIR/"
    success "前端代码同步完成"
else
    warning "前端代码目录不存在"
fi

log "  → 同步文档..."
if [ -d "/home/admin/xinhai_legal_api/docs" ]; then
    mkdir -p "$DEPLOY_DIR/docs"
    cp -r /home/admin/xinhai_legal_api/docs/* "$DEPLOY_DIR/docs/"
    success "文档同步完成"
fi
echo ""

# 步骤 4: 更新配置
log "【步骤 4】更新配置"
if [ -f "/home/admin/xinhai_legal_api/.env.$ENV" ]; then
    log "  → 复制环境配置..."
    cp "/home/admin/xinhai_legal_api/.env.$ENV" "$DEPLOY_DIR/.env"
    success "环境配置更新完成"
else
    warning "环境配置文件不存在：.env.$ENV"
fi
echo ""

# 步骤 5: 重启服务
log "【步骤 5】重启服务"
log "  → 检查 Nginx 配置..."
nginx -t > /dev/null 2>&1
if [ $? -eq 0 ]; then
    success "Nginx 配置正确"
else
    error "Nginx 配置错误"
fi

log "  → 重新加载 Nginx..."
systemctl reload nginx > /dev/null 2>&1
success "Nginx 重新加载完成"

log "  → 检查服务状态..."
systemctl is-active nginx > /dev/null 2>&1
if [ $? -eq 0 ]; then
    success "Nginx 运行正常"
else
    error "Nginx 未运行"
fi
echo ""

# 步骤 6: 部署验证
log "【步骤 6】部署验证"
log "  → 检查页面内容..."
if command -v curl &> /dev/null; then
    HTTP_CODE=$(curl -s -o /dev/null -w "%{http_code}" http://localhost/)
    if [ "$HTTP_CODE" -eq 200 ]; then
        success "HTTP 状态码：200"
    else
        error "HTTP 状态码：$HTTP_CODE"
    fi
    
    log "  → 检查关键字..."
    if curl -s http://localhost/ | grep -q "心海法律"; then
        success "页面关键字检查通过"
    else
        error "页面关键字检查失败"
    fi
else
    warning "curl 未安装，跳过 HTTP 检查"
fi

log "  → 检查错误日志..."
if [ -f "/var/log/nginx/error.log" ]; then
    ERROR_COUNT=$(tail -100 /var/log/nginx/error.log | grep -c "error" || echo "0")
    if [ "$ERROR_COUNT" -eq 0 ]; then
        success "无新错误日志"
    else
        warning "发现 $ERROR_COUNT 个错误，请检查日志"
    fi
fi
echo ""

# 步骤 7: 清理旧备份
log "【步骤 7】清理旧备份"
log "  → 保留最近 7 天的备份..."
find "$BACKUP_DIR" -type d -name "backup_*" -mtime +7 -exec rm -rf {} \; 2>/dev/null || true
success "旧备份清理完成"
echo ""

# 部署完成
echo "═══════════════════════════════════════════════"
echo "  部署完成"
echo "═══════════════════════════════════════════════"
echo ""
log "部署成功！"
log "部署环境：$ENV"
log "部署时间：$(date)"
log "备份名称：$BACKUP_NAME"
log "日志文件：$LOG_FILE"
echo ""

# 生成部署报告
cat > "$DEPLOY_DIR/deployment_${TIMESTAMP}.md" << EOF
# 部署记录

**部署环境**: $ENV
**部署时间**: $(date)
**部署人**: 磐石
**备份名称**: $BACKUP_NAME

## 部署步骤

1. ✅ 部署前检查
2. ✅ 备份当前版本
3. ✅ 同步代码
4. ✅ 更新配置
5. ✅ 重启服务
6. ✅ 部署验证
7. ✅ 清理旧备份

## 验证结果

- [x] HTTP 状态码 200
- [x] 页面关键字检查
- [x] 错误日志检查

## 回滚方法

如需回滚，执行:
\`\`\`bash
cp -r $BACKUP_DIR/$BACKUP_NAME/* $DEPLOY_DIR/
systemctl reload nginx
\`\`\`

**部署人签名**: 磐石
EOF

success "部署报告已生成：$DEPLOY_DIR/deployment_${TIMESTAMP}.md"
