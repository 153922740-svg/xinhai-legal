#!/bin/bash
# 心海法律 AI · 增强版自动化开发工作流（V2.0）
# 用途：全自动化开发流程 - 需求→开发→审查→测试→部署→知识沉淀

set -e

TIMESTAMP=$(date +%Y%m%d_%H%M%S)
LOG_FILE="/home/admin/xinhai_legal_api/logs/workflow_${TIMESTAMP}.log"
TASK_NAME="${1:-未命名任务}"
TASK_DIR="/home/admin/xinhai_legal_api/tasks/${TASK_NAME}_${TIMESTAMP}"
KNOWLEDGE_DB="/home/admin/xinhai_legal_api/knowledge_base.db"
SNIPPET_DB="/home/admin/xinhai_legal_api/code_snippets.db"

# 颜色
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
RED='\033[0;31m'
CYAN='\033[0;36m'
NC='\033[0m'

log() { echo -e "$(date '+%H:%M:%S') ${CYAN}[WORKFLOW]${NC} $1" | tee -a "$LOG_FILE"; }
ok()  { echo -e "$(date '+%H:%M:%S') ${GREEN}[✅]${NC} $1" | tee -a "$LOG_FILE"; }
warn(){ echo -e "$(date '+%H:%M:%S') ${YELLOW}[⚠️]${NC} $1" | tee -a "$LOG_FILE"; }
fail(){ echo -e "$(date '+%H:%M:%S') ${RED}[❌]${NC} $1" | tee -a "$LOG_FILE"; }

mkdir -p "$TASK_DIR"

echo ""
echo "═══════════════════════════════════════════════"
echo "  心海法律 AI · 增强版开发工作流"
echo "  任务：$TASK_NAME"
echo "  时间：$(date '+%Y-%m-%d %H:%M:%S')"
echo "═══════════════════════════════════════════════"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 1: 需求分析（蓝图）
# ═══════════════════════════════════════════════
log "【步骤 1/8】需求分析（蓝图）"
mkdir -p "$TASK_DIR/requirements"
cat > "$TASK_DIR/requirements/requirements.md" << EOF
# 需求文档 - $TASK_NAME

## 需求描述
${2:-待补充}

## 功能点
- 

## 验收标准
- 

**创建人**: 蓝图
**日期**: $(date +%Y-%m-%d)
EOF

# 自动搜索知识库中相关条目
if [ -f "$KNOWLEDGE_DB" ]; then
    python3 -c "
import sqlite3, sys
conn = sqlite3.connect('$KNOWLEDGE_DB')
c = conn.cursor()
try:
    c.execute(\"SELECT title, content FROM knowledge_fts WHERE knowledge_fts MATCH ? ORDER BY rank LIMIT 3\", (sys.argv[1],))
    rows = c.fetchall()
    if rows:
        print('\\n📚 相关知识条目：')
        for r in rows:
            print(f'  - {r[0]}')
except: pass
" "$TASK_NAME" 2>/dev/null | tee -a "$LOG_FILE"
fi
ok "需求文档已创建"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 2: 搜索代码片段（灵指）
# ═══════════════════════════════════════════════
log "【步骤 2/8】搜索相关代码片段（灵指）"
if [ -f "$SNIPPET_DB" ]; then
    python3 -c "
import sqlite3, sys
conn = sqlite3.connect('$SNIPPET_DB')
c = conn.cursor()
try:
    c.execute('SELECT title, description FROM snippets_fts WHERE fts MATCH ? ORDER BY rank LIMIT 5', (sys.argv[1],))
    rows = c.fetchall()
    if rows:
        print('\\n📋 可复用的代码片段：')
        for r in rows:
            print(f'  - {r[0]}: {r[1][:80]}')
    else:
        print('  (暂无可复用片段)')
except: pass
" "$TASK_NAME" 2>/dev/null | tee -a "$LOG_FILE"
fi
ok "搜索完成"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 3: 代码开发（灵指）
# ═══════════════════════════════════════════════
log "【步骤 3/8】代码开发（灵指）"
mkdir -p "$TASK_DIR/src"
touch "$TASK_DIR/src/main.py"
ok "代码开发目录已创建（等待灵指完成）"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 4: 单元测试（灵指）
# ═══════════════════════════════════════════════
log "【步骤 4/8】单元测试（灵指）"
mkdir -p "$TASK_DIR/tests"
cat > "$TASK_DIR/tests/test_main.py" << EOF
#!/usr/bin/env python3
"""单元测试 - $TASK_NAME"""
import pytest

class TestMain:
    def test_basic(self):
        assert True
EOF
ok "测试模板已创建"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 5: 代码审查（明鉴）
# ═══════════════════════════════════════════════
log "【步骤 5/8】代码审查（明鉴）"

# 敏感信息扫描
SCAN_RESULT="/tmp/secret_scan_${TIMESTAMP}.txt"
python3 /home/admin/xinhai_legal_api/scripts/pre_commit_secret_scan.py "$TASK_DIR" > "$SCAN_RESULT" 2>&1
if grep -q "发现高危" "$SCAN_RESULT" 2>/dev/null; then
    fail "敏感信息扫描未通过！"
    cat "$SCAN_RESULT"
    exit 1
else
    ok "敏感信息扫描通过"
fi

# 语法检查
for f in $(find "$TASK_DIR" -name "*.py"); do
    if python3 -m py_compile "$f" 2>/dev/null; then
        ok "语法检查通过：$f"
    else
        fail "语法错误：$f"
        exit 1
    fi
done

cat > "$TASK_DIR/review/review_report.md" << EOF
# 代码审查报告 - $TASK_NAME

**审查人**: 明鉴
**时间**: $(date '+%Y-%m-%d %H:%M:%S')

## 审查结果

| 项 | 状态 |
|---|------|
| 敏感信息扫描 | ✅ 通过 |
| 语法检查 | ✅ 通过 |

**审查结论**: ⏳ 等待灵指完成开发后重新审查
EOF
ok "代码审查通过"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 6: 功能测试（铁壁）
# ═══════════════════════════════════════════════
log "【步骤 6/8】功能测试（铁壁）"
if [ -f "$TASK_DIR/tests/test_main.py" ]; then
    cd "$TASK_DIR" && python3 -m pytest tests/ -v > "$TASK_DIR/tests/test_result.txt" 2>&1 || true
    ok "测试执行完成"
    cat "$TASK_DIR/tests/test_result.txt" | tail -5
fi
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 7: 知识沉淀
# ═══════════════════════════════════════════════
log "【步骤 7/8】知识沉淀"
# 自动将本次任务记入知识库
python3 -c "
import sqlite3
conn = sqlite3.connect('$KNOWLEDGE_DB')
c = conn.cursor()
c.execute('''
    INSERT INTO knowledge_items (title, content, category, tags, author)
    VALUES (?, ?, ?, ?, ?)
''', ('$TASK_NAME (开发记录)', f'任务时间：$(date '+%Y-%m-%d %H:%M')\\n路径：$TASK_DIR', 'tech', '自动沉淀, 开发记录', 'workflow'))
c.execute('INSERT INTO knowledge_fts (rowid, title, content, tags) VALUES (?, ?, ?, ?)',
          (c.lastrowid, '$TASK_NAME (开发记录)', f'任务时间：$(date '+%Y-%m-%d %H:%M')\\n路径：$TASK_DIR', '自动沉淀, 开发记录'))
conn.commit()
print('✅ 已自动沉淀到知识库')
" 2>/dev/null
ok "知识沉淀完成"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 步骤 8: 部署准备（磐石）
# ═══════════════════════════════════════════════
log "【步骤 8/8】部署准备（磐石）"
cat > "$TASK_DIR/deploy/deployment.md" << EOF
# 部署记录 - $TASK_NAME

## 部署信息
- 环境：test
- 版本：$TIMESTAMP
- 任务目录：$TASK_DIR

## 验证清单
- [ ] 代码审查通过
- [ ] 测试通过
- [ ] 安全扫描通过
- [ ] 部署完成
- [ ] 验证正常

**准备人**: 磐石
**时间**: $(date '+%Y-%m-%d %H:%M:%S')
EOF
ok "部署准备完成"
echo "" | tee -a "$LOG_FILE"

# ═══════════════════════════════════════════════
# 完成
# ═══════════════════════════════════════════════
echo ""
echo "═══════════════════════════════════════════════"
echo "  工作流执行完成"
echo "═══════════════════════════════════════════════"
echo ""
log "任务名称：$TASK_NAME"
log "任务目录：$TASK_DIR"
log "日志文件：$LOG_FILE"
log "知识库：✅ 已自动沉淀"
echo ""
echo "下一步："
echo "  1. 查看任务目录：cd $TASK_DIR"
echo "  2. 灵指完成开发"
echo "  3. 明鉴审查代码"
echo "  4. 铁壁执行测试"
echo "  5. 磐石部署上线"
echo ""
