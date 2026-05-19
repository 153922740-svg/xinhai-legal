#!/bin/bash
# Git 提交前敏感信息检测脚本
# 用法：./pre_commit_secret_scan.sh [文件路径]

set -e

echo "═══════════════════════════════════════════════"
echo "  心海法律 AI · Git 提交前敏感信息扫描"
echo "═══════════════════════════════════════════════"
echo ""

# 敏感信息模式
PATTERNS=(
    "ALIYUN_ACCESS_KEY_ID.*[A-Za-z0-9]{32}"
    "ALIYUN_ACCESS_KEY_SECRET.*[A-Za-z0-9]{32}"
    "access_key_id.*['\"][A-Za-z0-9]{32}['\"]"
    "access_key_secret.*['\"][A-Za-z0-9]{32}['\"]"
    "wechat.*mchid.*['\"][0-9]{10}['\"]"
    "wechat.*key.*['\"][A-Za-z0-9]{32}['\"]"
    "password.*['\"][^'\"]{8,}['\"]"
    "secret.*['\"][A-Za-z0-9]{16,}['\"]"
    "API_KEY.*['\"][A-Za-z0-9]{20,}['\"]"
    "Bearer [A-Za-z0-9_-]{20,}"
)

# 扫描文件
FILES_TO_SCAN="${1:-.}"
FOUND_SECRETS=0

echo "扫描路径：$FILES_TO_SCAN"
echo ""

for pattern in "${PATTERNS[@]}"; do
    if grep -rE "$pattern" "$FILES_TO_SCAN" --include="*.py" --include="*.md" --include="*.yaml" --include="*.yml" --include="*.json" 2>/dev/null; then
        echo ""
        echo "⚠️  警告：发现可能的敏感信息匹配模式：$pattern"
        FOUND_SECRETS=1
    fi
done

echo ""
echo "═══════════════════════════════════════════════"

if [ $FOUND_SECRETS -eq 1 ]; then
    echo "  ❌ 扫描失败：发现敏感信息，禁止提交！"
    echo "═══════════════════════════════════════════════"
    echo ""
    echo "处理建议："
    echo "1. 将敏感信息移至 SENSITIVE_INFO.md（不提交到 Git）"
    echo "2. 使用环境变量替代硬编码密钥"
    echo "3. 使用 .env 文件（添加到 .gitignore）"
    echo ""
    exit 1
else
    echo "  ✅ 扫描通过：未发现敏感信息"
    echo "═══════════════════════════════════════════════"
    exit 0
fi
