#!/usr/bin/env python3
"""
心海法律 AI - 综合任务上下文生成器
=================================
用途：生成 delegate_task 的完整 context 字符串
支持负责人角色自动匹配 toolsets、基础设施信息自动注入

用法：
    python3 generate_task_context.py <task_name> --type <task_type> --role <角色> [options]

示例：
    python3 generate_task_context.py "用户登录接口开发" --type api_dev --role 灵指 \\
        --files "app/routes/auth.py,app/services/auth_service.py" \\
        --constraints "返回格式必须统一" --acceptance "接口返回200"
"""

import argparse
import sys
from datetime import datetime

# ============================================================
# 基础设施信息
# ============================================================
INFRA_INFO = """## 基础设施信息
- 服务器 IP: 8.218.93.213
- SSH: root / Chen0812*
- 域名: xinclaw.xhacca.cn
- 数据库: /home/admin/xinhai_legal.db
- 框架: Flask (端口 5000)
- API 前缀: /api/v1/, /api/v2/, /api/v4/, /api/v5/, /api/v6/
- Nginx 路由: 8647(业务API) / 8642(AI对话) / 8646(COO管理)
- Hermes Business API: /home/admin/hermes_business_api.py
- Hermes Gateway: /home/admin/.hermes/ (端口8642)
- COO API: /home/admin/coo_api.py (端口8646)
- 小程序 AppID: wx73612d8efb98658d"""

# ============================================================
# Agent 角色 -> toolsets 映射
# ============================================================
ROLE_TOOLSETS = {
    "蓝图": {
        "role_desc": "产品官（需求分析、原型设计）",
        "toolsets": ["terminal", "file", "browser"],
    },
    "匠心": {
        "role_desc": "设计官（UI设计、前端开发）",
        "toolsets": ["terminal", "file", "browser"],
    },
    "铸基": {
        "role_desc": "架构师（后端架构、数据库）",
        "toolsets": ["terminal", "file", "web"],
    },
    "灵指": {
        "role_desc": "编码官（功能开发）",
        "toolsets": ["terminal", "file", "execute_code"],
    },
    "明鉴": {
        "role_desc": "审查官（代码审查）",
        "toolsets": ["terminal", "file", "search_files"],
    },
    "铁壁": {
        "role_desc": "测试官（功能测试）",
        "toolsets": ["terminal", "file", "browser"],
    },
    "磐石": {
        "role_desc": "运维官（部署、监控）",
        "toolsets": ["terminal", "process"],
    },
    "求索": {
        "role_desc": "学习官（技术调研）",
        "toolsets": ["terminal", "search_files", "web"],
    },
    "铁卫": {
        "role_desc": "安全官（安全审计）",
        "toolsets": ["terminal", "file", "search_files"],
    },
}

# ============================================================
# 任务类型约束模板
# ============================================================
TASK_CONSTRAINTS_TEMPLATES = {
    "bug_fix": """- 先复现 Bug，确认问题根因
- 修改最小化，只修复问题本身
- 添加回归测试用例
- 更新 changelog""",
    "api_dev": """- 遵循 RESTful 规范
- 参数校验完整（必填、类型、格式、长度）
- 返回统一格式：{"success": bool, "data": ..., "error": str}
- 添加错误码枚举定义
- 所有接口必须有 JWT 认证（支付接口除外）""",
    "test": """- 覆盖正常流程、异常流程、边界值
- 使用真实测试数据（非 mock）
- 测试后恢复测试数据""",
    "review": """- 按严重程度分级记录问题（致命/严重/一般/建议）
- 每个问题必须给出修复建议
- 最终给出整体质量评估""",
    "doc": """- 使用 Markdown 格式
- 包含修订记录
- 与代码实现保持同步""",
    "research": """- 对比至少 2 个候选方案
- 每个方案包含优缺点分析
- 给出明确推荐方案及实施建议""",
}

# ============================================================
# 任务类型验收标准模板
# ============================================================
ACCEPTANCE_TEMPLATES = {
    "bug_fix": """1. ✅ Bug 已修复，预期行为验证通过
2. ✅ 回归测试通过，不引入新 Bug
3. ✅ 修复记录已更新""",
    "api_dev": """1. ✅ 接口返回正确的状态码和数据结构
2. ✅ 参数校验完整
3. ✅ 错误处理覆盖所有异常场景
4. ✅ 通过 curl 测试验证""",
    "test": """1. ✅ 所有测试场景通过
2. ✅ 测试报告完整（通过率、覆盖率、Bug列表）
3. ✅ 关键 Bug 已提交修复""",
    "review": """1. ✅ 所有问题已列出（按严重程度分级）
2. ✅ 每个问题有修复建议
3. ✅ 审查报告完整规范""",
    "doc": """1. ✅ 文档结构完整
2. ✅ 内容与代码一致
3. ✅ 格式规范（Markdown）""",
    "research": """1. ✅ 至少 2 个候选方案对比
2. ✅ 优缺点分析完整
3. ✅ 明确推荐方案
4. ✅ 落地实施建议""",
}


def build_delegate_context(
    task_name,
    task_type,
    role,
    files=None,
    special_constraints=None,
    custom_acceptance=None,
    extra_notes=None,
):
    """生成完整的 delegate_task context 字符串"""

    # 1. Agent 角色信息
    role_info = ROLE_TOOLSETS.get(role, {
        "role_desc": role,
        "toolsets": ["terminal", "file"],
    })

    # 2. 任务基础信息
    lines = []
    lines.append("=" * 64)
    lines.append(f"  心海法律 AI · 子 Agent 任务上下文")
    lines.append(f"  {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    lines.append("=" * 64)
    lines.append("")

    lines.append("## 任务信息")
    lines.append(f"**任务名称**: {task_name}")
    lines.append(f"**任务类型**: {task_type}")

    task_type_labels = {
        "bug_fix": "Bug 修复",
        "api_dev": "API 开发",
        "test": "测试",
        "review": "代码审查",
        "doc": "文档",
        "research": "调研",
    }
    lines.append(f"**类型说明**: {task_type_labels.get(task_type, task_type)}")
    lines.append("")

    # 3. 负责人信息
    lines.append("## 负责人")
    lines.append(f"**角色**: {role}（{role_info['role_desc']}）")
    lines.append(f"**工具集**: {', '.join(role_info['toolsets'])}")
    lines.append("")

    # 4. 相关文件
    if files:
        lines.append("## 相关文件")
        for f in files.split(","):
            f = f.strip()
            if f:
                lines.append(f"- `{f}`")
        lines.append("")

    # 5. 约束条件
    lines.append("## 约束条件")
    if special_constraints:
        lines.append(special_constraints)
        lines.append("")
    # 注入该任务类型的默认约束
    default_constraints = TASK_CONSTRAINTS_TEMPLATES.get(task_type)
    if default_constraints:
        lines.append("### 通用约束")
        lines.append(default_constraints)
        lines.append("")

    # 6. 验收标准
    lines.append("## 验收标准")
    if custom_acceptance:
        lines.append(custom_acceptance)
    else:
        default_ac = ACCEPTANCE_TEMPLATES.get(task_type, "1. ✅ 任务完成")
        lines.append(default_ac)
    lines.append("")

    # 7. 附注
    if extra_notes:
        lines.append("## 补充说明")
        lines.append(extra_notes)
        lines.append("")

    # 8. 注入基础设施信息
    lines.append(INFRA_INFO)
    lines.append("")
    lines.append("=" * 64)

    return "\n".join(lines)


def main():
    parser = argparse.ArgumentParser(
        description="心海法律 AI - 综合任务上下文生成器",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )

    parser.add_argument("task_name", help="任务名称")
    parser.add_argument("--type", "-t", required=True,
                        choices=list(TASK_CONSTRAINTS_TEMPLATES.keys()),
                        help="任务类型")
    parser.add_argument("--role", "-r", required=True,
                        choices=list(ROLE_TOOLSETS.keys()),
                        help="负责人角色")
    parser.add_argument("--files", "-f", help="相关文件路径，逗号分隔")
    parser.add_argument("--constraints", "-c", help="特殊约束条件")
    parser.add_argument("--acceptance", "-a", help="自定义验收标准")
    parser.add_argument("--notes", "-n", help="补充说明")
    parser.add_argument("--list-roles", action="store_true",
                        help="列出所有角色及其工具集")

    args = parser.parse_args()

    if args.list_roles:
        print("负责人角色列表：")
        print()
        for role, info in ROLE_TOOLSETS.items():
            tools = ", ".join(info["toolsets"])
            print(f"  {role:6s} - {info['role_desc']:25s} 工具集: [{tools}]")
        sys.exit(0)

    context = build_delegate_context(
        task_name=args.task_name,
        task_type=args.type,
        role=args.role,
        files=args.files,
        special_constraints=args.constraints,
        custom_acceptance=args.acceptance,
        extra_notes=args.notes,
    )

    print(context)


if __name__ == "__main__":
    main()
