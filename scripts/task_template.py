#!/usr/bin/env python3
"""
心海法律 AI - 任务模板化脚本
=============================
用途：COO 快速生成 delegate_task 用的 context 字符串
用法：
    python3 task_template.py <task_type> [options]

支持的任务类型：
    bug_fix     - Bug修复
    api_dev     - API开发
    test        - 测试
    review      - 代码审查
    doc         - 文档
    research    - 调研

示例：
    python3 task_template.py api_dev --path "/api/v1/user/login" --params "phone,code" --response "{token,user_id}" --files "phase4_user_auth_api.py"
    python3 task_template.py bug_fix --bug "Nginx路由8642指向已停止端口" --files "/etc/nginx/sites-enabled/default" --expected "返回200"
    python3 task_template.py test --feature "用户登录" --scenarios "手机号验证码登录,密码登录" --data "phone=13800138000,code=123456"
    python3 task_template.py review --files "app/routes/auth.py,app/services/auth_service.py" --type "security"
    python3 task_template.py doc --doc_type "API文档" --refs "API_DOCUMENTATION.md" --output "docs/api_v2.md"
    python3 task_template.py research --topic "DeepSeek R1模型API接入" --scope "接口规范、定价、性能对比" --deliverable "技术方案"
"""

import argparse
import sys
from datetime import datetime

# ============================================================
# 基础设施信息（自动注入到每个模板中）
# ============================================================
INFRA_INFO = """## 基础设施信息
- 服务器 IP: 8.218.93.213
- SSH: root / Chen0812*
- 域名: xinclaw.xhacca.cn
- 数据库: /home/admin/xinhai_legal.db
- 框架: Flask (端口 5000)
- API 前缀:
  - /api/v1/ (旧版)
  - /api/v2/ (旧版)
  - /api/v4/ (旧版)
  - /api/v5/ (旧版)
  - /api/v6/ (COO 管理后台)
- Nginx 路由: 8647(业务API) / 8642(AI对话) / 8646(COO管理)
- Hermes Business API: /home/admin/hermes_business_api.py
- Hermes Gateway: /home/admin/.hermes/ (端口8642)
- COO API: /home/admin/coo_api.py (端口8646)
- 小程序 AppID: wx73612d8efb98658d"""


def get_role_toolsets(role_name):
    """根据负责人角色返回匹配的工具集"""
    toolsets = {
        "灵指": ["terminal", "file", "execute_code"],
        "铁壁": ["terminal", "file", "browser"],
        "明鉴": ["terminal", "file", "search_files"],
        "铸基": ["terminal", "file", "web"],
        "蓝图": ["terminal", "file", "browser"],
        "匠心": ["terminal", "file", "browser"],
        "磐石": ["terminal", "process"],
        "求索": ["terminal", "search_files", "web"],
        "铁卫": ["terminal", "file", "search_files"],
    }
    return toolsets.get(role_name, ["terminal", "file"])


def build_context(parts):
    """构建最终的 context 字符串"""
    lines = []
    lines.append("=" * 64)
    lines.append("  心海法律 AI - 子 Agent 任务上下文")
    lines.append("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 64)
    lines.append("")
    for p in parts:
        lines.append(p)
        lines.append("")
    lines.append(INFRA_INFO)
    lines.append("")
    lines.append("=" * 64)
    return "\n".join(lines)


# ============================================================
# 模板生成函数
# ============================================================

def template_bug_fix(args):
    """Bug 修复模板"""
    parts = []
    parts.append("## 任务类型: Bug 修复")
    parts.append(f"### Bug 描述\n{args.bug}")
    parts.append(f"### 相关文件\n{args.files}")
    parts.append(f"### 预期行为\n{args.expected}")
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("### 验收标准\n1. Bug 复现步骤确认\n2. 修复后预期行为验证\n3. 不影响已有功能\n4. 添加对应测试用例")
    return build_context(parts)


def template_api_dev(args):
    """API 开发模板"""
    parts = []
    parts.append("## 任务类型: API 开发")
    parts.append(f"### 接口路径\n{args.path}")
    if args.method:
        parts.append(f"### 请求方法\n{args.method}")
    parts.append(f"### 请求参数\n{args.params}")
    parts.append(f"### 响应格式\n{args.response}")
    if args.files:
        parts.append(f"### 参考文件\n{args.files}")
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("""### 验收标准
1. 接口返回正确状态码和数据结构
2. 参数校验完整（必填、类型、长度）
3. 错误处理覆盖所有异常场景
4. 符合接口设计文档规范
5. 通过 curl 测试验证""")
    return build_context(parts)


def template_test(args):
    """测试模板"""
    parts = []
    parts.append("## 任务类型: 功能测试")
    parts.append(f"### 被测功能\n{args.feature}")
    parts.append(f"### 测试场景\n{args.scenarios}")
    if args.data:
        parts.append(f"### 测试数据\n{args.data}")
    if args.files:
        parts.append(f"### 相关文件\n{args.files}")
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("""### 验收标准
1. 每个测试场景通过
2. 边界值测试通过
3. 异常输入测试通过
4. 测试报告完整（通过率、覆盖率、Bug列表）""")
    return build_context(parts)


def template_review(args):
    """代码审查模板"""
    review_types = {
        "security": "### 审查重点\n- SQL 注入风险\n- XSS 跨站脚本\n- 敏感信息泄露\n- 认证授权漏洞\n- 支付安全",
        "performance": "### 审查重点\n- 时间复杂度（避免 O(n²) 及以上）\n- 数据库查询优化（N+1 问题）\n- 缓存使用\n- 资源释放",
        "style": "### 审查重点\n- PEP8 代码规范\n- 函数文档字符串\n- 命名规范\n- 代码可读性\n- 注释完整性",
    }
    parts = []
    parts.append("## 任务类型: 代码审查")
    parts.append(f"### 审查文件\n{args.files}")
    parts.append(f"### 审查类型\n{args.type}")
    parts.append(review_types.get(args.type, review_types["security"]))
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("""### 验收标准
1. 列出所有发现的问题（按严重程度分级）
2. 对每个问题给出修复建议
3. 审查报告完整规范""")
    return build_context(parts)


def template_doc(args):
    """文档模板"""
    parts = []
    parts.append("## 任务类型: 文档编写")
    parts.append(f"### 文档类型\n{args.doc_type}")
    parts.append(f"### 参考文档\n{args.refs if args.refs else '(无)'}")
    parts.append(f"### 输出路径\n{args.output}")
    if args.files:
        parts.append(f"### 相关文件\n{args.files}")
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("""### 验收标准
1. 文档结构完整（目录、正文、附录）
2. 内容准确（与代码实现一致）
3. 语言清晰易懂
4. 格式规范（Markdown）""")
    return build_context(parts)


def template_research(args):
    """调研模板"""
    parts = []
    parts.append("## 任务类型: 技术调研")
    parts.append(f"### 调研主题\n{args.topic}")
    parts.append(f"### 调研范围\n{args.scope if args.scope else '(无明确范围)'}")
    parts.append(f"### 交付物格式\n{args.deliverable if args.deliverable else '调研报告（Markdown）'}")
    if args.files:
        parts.append(f"### 参考资料\n{args.files}")
    if args.notes:
        parts.append(f"### 补充说明\n{args.notes}")
    parts.append("""### 验收标准
1. 对比至少 2 个候选方案
2. 每个方案包含优缺点分析
3. 给出明确推荐方案及理由
4. 包含落地实施建议""")
    return build_context(parts)


# ============================================================
# 主入口
# ============================================================

TEMPLATES = {
    "bug_fix": {
        "help": "Bug 修复任务",
        "func": template_bug_fix,
        "args": [
            (("--bug",), {"required": True, "help": "Bug 描述"}),
            (("--files",), {"required": True, "help": "相关文件路径（逗号分隔）"}),
            (("--expected",), {"required": True, "help": "预期行为"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
    "api_dev": {
        "help": "API 开发任务",
        "func": template_api_dev,
        "args": [
            (("--path",), {"required": True, "help": "接口路径"}),
            (("--method",), {"required": False, "default": "POST", "help": "请求方法 (GET/POST/PUT/DELETE)"}),
            (("--params",), {"required": True, "help": "请求参数说明"}),
            (("--response",), {"required": True, "help": "响应格式说明"}),
            (("--files",), {"required": False, "help": "参考文件路径（逗号分隔）"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
    "test": {
        "help": "测试任务",
        "func": template_test,
        "args": [
            (("--feature",), {"required": True, "help": "被测功能"}),
            (("--scenarios",), {"required": True, "help": "测试场景（逗号分隔）"}),
            (("--data",), {"required": False, "help": "测试数据"}),
            (("--files",), {"required": False, "help": "相关文件路径"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
    "review": {
        "help": "代码审查任务",
        "func": template_review,
        "args": [
            (("--files",), {"required": True, "help": "审查文件路径（逗号分隔）"}),
            (("--type",), {"required": True, "choices": ["security", "performance", "style"], "help": "审查类型"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
    "doc": {
        "help": "文档编写任务",
        "func": template_doc,
        "args": [
            (("--doc_type",), {"required": True, "help": "文档类型（API文档/设计文档/测试报告等）"}),
            (("--refs",), {"required": False, "help": "参考文档路径（逗号分隔）"}),
            (("--output",), {"required": True, "help": "输出路径"}),
            (("--files",), {"required": False, "help": "相关文件路径"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
    "research": {
        "help": "技术调研任务",
        "func": template_research,
        "args": [
            (("--topic",), {"required": True, "help": "调研主题"}),
            (("--scope",), {"required": False, "help": "调研范围"}),
            (("--deliverable",), {"required": False, "help": "交付物格式"}),
            (("--files",), {"required": False, "help": "参考资料路径"}),
            (("--notes",), {"required": False, "help": "补充说明"}),
        ],
    },
}


def main():
    parser = argparse.ArgumentParser(
        description="心海法律 AI - 任务上下文模板生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument(
        "task_type",
        choices=list(TEMPLATES.keys()),
        help="任务类型",
    )
    parser.add_argument(
        "--list-types",
        action="store_true",
        help="列出所有任务类型",
    )

    # 先解析 task_type
    known, remaining = parser.parse_known_args()

    if known.list_types:
        print("支持的任务类型：")
        for t, info in TEMPLATES.items():
            print(f"  {t:12s} - {info['help']}")
        print(f"\n用法示例：")
        print(f"  python3 {sys.argv[0]} api_dev --path ...")
        print(f"  python3 {sys.argv[0]} bug_fix --bug ...")
        sys.exit(0)

    template = TEMPLATES.get(known.task_type)
    if not template:
        print(f"错误：不支持的任务类型 '{known.task_type}'", file=sys.stderr)
        print(f"可用类型: {', '.join(TEMPLATES.keys())}", file=sys.stderr)
        sys.exit(1)

    # 构建子解析器
    sub_parser = argparse.ArgumentParser(
        prog=f"{sys.argv[0]} {known.task_type}",
        description=template["help"],
    )
    for argspec in template["args"]:
        positional, kwargs = argspec
        sub_parser.add_argument(*positional, **kwargs)

    args = sub_parser.parse_args(remaining)

    # 生成 context
    context = template["func"](args)
    print(context)


if __name__ == "__main__":
    main()
