#!/bin/bash
# 心海法律 AI - 自动化开发工作流脚本

set -e

echo "═══════════════════════════════════════════════"
echo "  心海法律 AI · 自动化开发工作流"
echo "═══════════════════════════════════════════════"
echo ""

# 参数检查
if [ -z "$1" ]; then
    echo "用法：./dev_workflow.sh [任务名称] [负责人]"
    echo ""
    echo "负责人选项："
    echo "  - 蓝图 (产品官)"
    echo "  - 匠心 (设计官)"
    echo "  - 铸基 (架构师)"
    echo "  - 灵指 (编码官)"
    echo "  - 明鉴 (审查官)"
    echo "  - 铁壁 (测试官)"
    echo "  - 磐石 (运维官)"
    echo "  - 求索 (学习官)"
    echo "  - 铁卫 (安全官)"
    exit 1
fi

TASK_NAME="$1"
ASSIGNEE="${2:-灵指}"
TIMESTAMP=$(date +%Y%m%d_%H%M%S)
TASK_DIR="/home/admin/xinhai_legal_api/tasks/$TASK_NAME"
LOG_FILE="/home/admin/xinhai_legal_api/logs/dev_workflow_${TIMESTAMP}.log"

echo "任务：$TASK_NAME" | tee -a "$LOG_FILE"
echo "负责人：$ASSIGNEE" | tee -a "$LOG_FILE"
echo "时间：$(date)" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 创建任务目录
mkdir -p "$TASK_DIR"

# 步骤 1: 需求分析（蓝图）
echo "【步骤 1】需求分析（蓝图）" | tee -a "$LOG_FILE"
if [ "$ASSIGNEE" = "蓝图" ] || [ -z "$ASSIGNEE" ]; then
    echo "  → 创建需求文档模板..." | tee -a "$LOG_FILE"
    cat > "$TASK_DIR/requirements.md" << EOF
# 需求文档 - $TASK_NAME

## 需求描述


## 功能点


## 技术方案


## 验收标准


**创建人**: 蓝图  
**日期**: $(date +%Y-%m-%d)
EOF
    echo "  ✅ 需求文档已创建" | tee -a "$LOG_FILE"
else
    echo "  ⏭️  跳过（非蓝图任务）" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# 步骤 2: 代码开发（灵指）
echo "【步骤 2】代码开发（灵指）" | tee -a "$LOG_FILE"
if [ "$ASSIGNEE" = "灵指" ] || [ -z "$ASSIGNEE" ]; then
    echo "  → 创建代码文件..." | tee -a "$LOG_FILE"
    echo "  ✅ 代码开发中..." | tee -a "$LOG_FILE"
else
    echo "  ⏭️  跳过（非灵指任务）" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# 步骤 3: 代码审查（明鉴）
echo "【步骤 3】代码审查（明鉴）" | tee -a "$LOG_FILE"
echo "  → 运行敏感信息扫描..." | tee -a "$LOG_FILE"
if [ -f "/home/admin/xinhai_legal_api/scripts/pre_commit_secret_scan.sh" ]; then
    bash /home/admin/xinhai_legal_api/scripts/pre_commit_secret_scan.sh "$TASK_DIR" | tee -a "$LOG_FILE"
else
    echo "  ⚠️  扫描脚本不存在" | tee -a "$LOG_FILE"
fi
echo "" | tee -a "$LOG_FILE"

# 步骤 4: 测试（铁壁）
echo "【步骤 4】功能测试（铁壁）" | tee -a "$LOG_FILE"
echo "  → 创建测试计划..." | tee -a "$LOG_FILE"
cat > "$TASK_DIR/test_plan.md" << EOF
# 测试计划 - $TASK_NAME

## 测试用例

1. 
2. 
3. 

## 测试结果

| 用例 | 状态 | 备注 |
|------|------|------|
| 1 | ⏳ 待测试 | |
| 2 | ⏳ 待测试 | |
| 3 | ⏳ 待测试 | |

**测试人**: 铁壁  
**日期**: $(date +%Y-%m-%d)
EOF
echo "  ✅ 测试计划已创建" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

# 步骤 5: 部署（磐石）
echo "【步骤 5】部署准备（磐石）" | tee -a "$LOG_FILE"
echo "  → 创建部署记录..." | tee -a "$LOG_FILE"
cat > "$TASK_DIR/deployment.md" << EOF
# 部署记录 - $TASK_NAME

## 部署信息

- 部署时间：
- 部署环境：
- 版本号：

## 部署步骤

1. 
2. 
3. 

## 验证结果

- [ ] 功能验证
- [ ] 性能验证
- [ ] 安全验证

**部署人**: 磐石  
**日期**: $(date +%Y-%m-%d)
EOF
echo "  ✅ 部署记录已创建" | tee -a "$LOG_FILE"
echo "" | tee -a "$LOG_FILE"

echo "═══════════════════════════════════════════════"
echo "  工作流执行完成"
echo "═══════════════════════════════════════════════"
echo ""
echo "任务目录：$TASK_DIR"
echo "日志文件：$LOG_FILE"
echo ""
