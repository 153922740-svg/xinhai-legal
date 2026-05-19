#!/bin/bash
# 子 Agent 调用问题诊断脚本

echo "═══════════════════════════════════════════════"
echo "  心海法律 AI · 子 Agent 调用问题诊断"
echo "═══════════════════════════════════════════════"
echo ""

# 1. 检查主配置
echo "【1】检查主配置文件"
echo "-------------------------------------------"
if [ -f /home/admin/.hermes/config.yaml ]; then
    echo "✅ config.yaml 存在"
    grep -A5 "^model:" /home/admin/.hermes/config.yaml | head -6
else
    echo "❌ config.yaml 不存在"
fi
echo ""

# 2. 检查环境变量
echo "【2】检查 API Key 环境变量"
echo "-------------------------------------------"
if [ -n "$ALIBABA_API_KEY" ]; then
    echo "✅ ALIBABA_API_KEY 已设置"
    echo "   值：${ALIBABA_API_KEY:0:10}..."
else
    echo "❌ ALIBABA_API_KEY 未设置"
fi

if [ -n "$DASHSCOPE_API_KEY" ]; then
    echo "✅ DASHSCOPE_API_KEY 已设置"
    echo "   值：${DASHSCOPE_API_KEY:0:10}..."
else
    echo "⚠️  DASHSCOPE_API_KEY 未设置"
fi
echo ""

# 3. 测试 API 连接
echo "【3】测试阿里云 API 连接"
echo "-------------------------------------------"
if [ -n "$ALIBABA_API_KEY" ]; then
    RESPONSE=$(curl -s -X POST https://dashscope.aliyuncs.com/compatible-mode/v1/chat/completions \
        -H "Content-Type: application/json" \
        -H "Authorization: Bearer $ALIBABA_API_KEY" \
        -d '{"model":"qwen-plus","messages":[{"role":"user","content":"test"}]}' | head -c 200)
    
    if echo "$RESPONSE" | grep -q "error"; then
        echo "❌ API 调用失败：$RESPONSE"
    else
        echo "✅ API 调用成功"
    fi
else
    echo "⚠️  跳过测试（API Key 未设置）"
fi
echo ""

# 4. 检查 delegate_task 配置
echo "【4】检查 delegate_task 配置"
echo "-------------------------------------------"
grep -r "delegate_task" /home/admin/.hermes/config.yaml 2>/dev/null || echo "无特殊配置"
echo ""

# 5. 检查子 Agent 日志
echo "【5】检查最近的子 Agent 调用日志"
echo "-------------------------------------------"
if [ -d /home/admin/.hermes/logs ]; then
    ls -lt /home/admin/.hermes/logs/*.log 2>/dev/null | head -5
else
    echo "⚠️  日志目录不存在"
fi
echo ""

echo "═══════════════════════════════════════════════"
echo "  诊断完成"
echo "═══════════════════════════════════════════════"
