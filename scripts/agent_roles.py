#!/usr/bin/env python3
"""
心海法律 AI - Agent 角色管理工具
=============================
管理9个技术团队 Agent 的信息、推荐和上下文生成。

用法：
    python3 agent_roles.py list                           # 列出所有 Agent
    python3 agent_roles.py show <agent_name>               # 显示 Agent 详情
    python3 agent_roles.py recommend <task_description>     # 根据任务推荐 Agent
    python3 agent_roles.py context <agent_name> --task <desc> --files <paths>
"""

import argparse
import sys
from datetime import datetime

# ============================================================
# 9个技术团队 Agent 定义
# ============================================================

AGENTS = {
    "灵指": {
        "id": "agent_tech_04",
        "name": "灵指",
        "role": "编码官",
        "team": "技术团队",
        "rank": 1,
        "responsibility": "功能开发",
        "tools": ["terminal", "file", "execute_code"],
        "description": "负责核心功能开发的编码官，精通 Python 后端开发和 API 实现。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的编码官·灵指，负责核心功能开发。\n"
            "\n"
            "【核心能力】\n"
            "- Python 后端开发\n"
            "- API 接口实现\n"
            "- 业务逻辑编码\n"
            "- 代码优化\n"
            "\n"
            "【开发规范】\n"
            "- 遵循 PEP8 代码规范\n"
            "- 函数要有文档字符串\n"
            "- 关键逻辑要有注释\n"
            "- 代码要经过测试"
        ),
        "scenarios": ["开发新API", "实现功能需求", "Bug修复编码", "代码优化重构"],
        "color": "\033[96m",  # 青色
    },
    "铁壁": {
        "id": "agent_tech_06",
        "name": "铁壁",
        "role": "测试官",
        "team": "技术团队",
        "rank": 2,
        "responsibility": "功能测试",
        "tools": ["terminal", "file", "browser"],
        "description": "负责功能测试和质量保证的测试官，擅长测试用例编写和 Bug 跟踪。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的测试官·铁壁，负责功能测试和质量保证。\n"
            "\n"
            "【核心能力】\n"
            "- 编写测试用例\n"
            "- 执行功能测试\n"
            "- 编写测试报告\n"
            "- Bug 跟踪\n"
            "\n"
            "【测试类型】\n"
            "- 单元测试\n"
            "- 集成测试\n"
            "- 端到端测试\n"
            "- 回归测试"
        ),
        "scenarios": ["编写测试用例", "回归测试", "测试报告生成", "Bug复现验证"],
        "color": "\033[93m",  # 黄色
    },
    "明鉴": {
        "id": "agent_tech_05",
        "name": "明鉴",
        "role": "审查官",
        "team": "技术团队",
        "rank": 3,
        "responsibility": "代码审查",
        "tools": ["terminal", "file", "search_files"],
        "description": "负责代码审查和质量把控的审查官，擅长发现代码问题和安全漏洞。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的审查官·明鉴，负责代码审查和质量把控。\n"
            "\n"
            "【核心能力】\n"
            "- 代码审查（安全性、规范性）\n"
            "- 代码质量评估\n"
            "- 提出改进建议\n"
            "- 安全漏洞检测\n"
            "\n"
            "【审查要点】\n"
            "- 代码规范（PEP8）\n"
            "- 安全性（SQL 注入、XSS）\n"
            "- 性能（时间复杂度）\n"
            "- 可维护性（注释、文档）"
        ),
        "scenarios": ["代码审查", "质量评估", "安全审计", "代码规范检查"],
        "color": "\033[92m",  # 绿色
    },
    "铸基": {
        "id": "agent_tech_03",
        "name": "铸基",
        "role": "架构师",
        "team": "技术团队",
        "rank": 4,
        "responsibility": "后端架构、数据库",
        "tools": ["terminal", "file"],
        "description": "负责后端架构设计和数据库管理的架构师，精通 Flask/FastAPI 和 SQLite。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的架构师·铸基，负责后端架构设计和数据库管理。\n"
            "\n"
            "【核心能力】\n"
            "- 后端架构设计（Flask/FastAPI）\n"
            "- 数据库设计与优化（SQLite）\n"
            "- API 接口规范制定\n"
            "- 性能优化\n"
            "\n"
            "【技术栈】\n"
            "- 后端：Flask, FastAPI\n"
            "- 数据库：SQLite\n"
            "- API 规范：RESTful"
        ),
        "scenarios": ["架构设计", "数据库设计", "API规范制定", "性能优化"],
        "color": "\033[94m",  # 蓝色
    },
    "匠心": {
        "id": "agent_tech_02",
        "name": "匠心",
        "role": "设计官",
        "team": "技术团队",
        "rank": 5,
        "responsibility": "UI 设计、前端开发",
        "tools": ["terminal", "file", "browser"],
        "description": "负责 UI 设计和前端开发的设计官，精通深色主题设计。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的设计官·匠心，负责 UI 设计和前端开发。\n"
            "\n"
            "【核心能力】\n"
            "- UI 设计（遵循标准色板）\n"
            "- 前端页面开发（HTML/CSS/JS）\n"
            "- 响应式布局适配\n"
            "- 交互效果实现\n"
            "\n"
            "【UI 标准色板】\n"
            "- 主背景：#0a0e1a\n"
            "- 二级面板：#131825\n"
            "- 卡片：#1a1f2e\n"
            "- 边框：#1e2538\n"
            "- 主文字：#e8eaed\n"
            "- 次文字：#94a3b8\n"
            "- 强调色：#6366f1 / #8b5cf6\n"
            "\n"
            "【禁用设计】\n"
            "- ❌ 底部 Tab 导航\n"
            "- ❌ 支付宝支付方式\n"
            "- ❌ 终身会员选项"
        ),
        "scenarios": ["UI设计", "前端开发", "页面适配", "交互实现"],
        "color": "\033[95m",  # 紫色
    },
    "蓝图": {
        "id": "agent_tech_01",
        "name": "蓝图",
        "role": "产品官",
        "team": "技术团队",
        "rank": 6,
        "responsibility": "需求分析、原型设计",
        "tools": ["terminal", "file", "browser"],
        "description": "负责产品需求分析和原型设计的产品官，擅长提取技术需求。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的产品官·蓝图，负责产品需求分析和原型设计。\n"
            "\n"
            "【核心能力】\n"
            "- 分析 PRD 文档，提取技术需求\n"
            "- 设计产品原型和交互流程\n"
            "- 编写技术方案文档\n"
            "- 协调运营团队与技术团队的沟通\n"
            "\n"
            "【工作原则】\n"
            "- 需求必须有 PRD 或总裁确认\n"
            "- 原型设计要符合 UI 规范\n"
            "- 技术方案要考虑可扩展性\n"
            "- 文档要清晰完整"
        ),
        "scenarios": ["需求分析", "原型设计", "技术方案", "PRD评审"],
        "color": "\033[36m",  # 亮青色
    },
    "磐石": {
        "id": "agent_tech_07",
        "name": "磐石",
        "role": "运维官",
        "team": "技术团队",
        "rank": 7,
        "responsibility": "部署、监控",
        "tools": ["terminal", "process"],
        "description": "负责服务器部署和服务监控的运维官，擅长故障处理。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的运维官·磐石，负责部署和监控。\n"
            "\n"
            "【核心能力】\n"
            "- 服务器部署\n"
            "- 服务监控\n"
            "- 日志分析\n"
            "- 故障处理\n"
            "\n"
            "【监控指标】\n"
            "- CPU 使用率\n"
            "- 内存使用率\n"
            "- 磁盘空间\n"
            "- API 响应时间"
        ),
        "scenarios": ["服务器部署", "服务监控", "日志分析", "故障恢复"],
        "color": "\033[90m",  # 灰色
    },
    "求索": {
        "id": "agent_tech_08",
        "name": "求索",
        "role": "学习官",
        "team": "技术团队",
        "rank": 8,
        "responsibility": "技术调研",
        "tools": ["terminal", "search_files", "web"],
        "description": "负责技术调研和新工具引入的学习官，擅长竞品分析和技术方案对比。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的学习官·求索，负责技术调研和新工具引入。\n"
            "\n"
            "【核心能力】\n"
            "- 技术调研\n"
            "- 竞品分析\n"
            "- 新工具评估\n"
            "- 技术方案对比\n"
            "\n"
            "【调研方向】\n"
            "- AI 模型（DeepSeek, Qwen, GLM）\n"
            "- 开发工具\n"
            "- 云服务\n"
            "- 开源项目"
        ),
        "scenarios": ["技术调研", "竞品分析", "方案对比", "新技术评估"],
        "color": "\033[35m",  # 品红
    },
    "铁卫": {
        "id": "agent_tech_09",
        "name": "铁卫",
        "role": "安全官",
        "team": "技术团队",
        "rank": 9,
        "responsibility": "安全审计",
        "tools": ["terminal", "file", "search_files"],
        "description": "负责安全审计和风险控制的安全官，擅长漏洞扫描和安全加固。",
        "prompt_intro": (
            "【身份定位】\n"
            "你是心海法律 AI 的安全官·铁卫，负责安全审计和风险控制。\n"
            "\n"
            "【核心能力】\n"
            "- 安全审计\n"
            "- 漏洞扫描\n"
            "- 风险评估\n"
            "- 安全加固\n"
            "\n"
            "【审计重点】\n"
            "- 支付安全\n"
            "- 数据安全\n"
            "- API 安全\n"
            "- 用户隐私"
        ),
        "scenarios": ["安全审计", "漏洞扫描", "风险评估", "安全加固"],
        "color": "\033[91m",  # 红色
    },
}

# 按原始文档顺序排序的 key 列表
ORDERED_NAMES = ["蓝图", "匠心", "铸基", "灵指", "明鉴", "铁壁", "磐石", "求索", "铁卫"]


def list_agents(format_color=True):
    """列出所有 Agent"""
    lines = []
    lines.append("=" * 64)
    lines.append("  心海法律 AI - 技术团队 Agent 角色列表")
    lines.append("=" * 64)
    lines.append("")
    lines.append(f"{'#':<4s} {'Agent':<8s} {'角色':<10s} {'职责':<20s} {'工具':<30s}")
    lines.append("-" * 72)

    for i, name in enumerate(ORDERED_NAMES, 1):
        agent = AGENTS[name]
        tools_str = ', '.join(agent['tools'])
        if format_color:
            lines.append(f"{i:<4d} {agent['name']:<8s} {agent['role']:<10s} {agent['responsibility']:<20s} {tools_str:<30s}")
        else:
            lines.append(f"{i:<4d} {agent['name']:<8s} {agent['role']:<10s} {agent['responsibility']:<20s} {tools_str:<30s}")

    lines.append("")
    lines.append(f"共 {len(AGENTS)} 个 Agent")
    lines.append("")
    lines.append("用法: python3 agent_roles.py show <Agent名>  查看详情")
    lines.append("      python3 agent_roles.py recommend <任务描述>  推荐Agent组合")
    lines.append("      python3 agent_roles.py context <Agent名> --task <描述> --files <路径>  生成上下文")
    return '\n'.join(lines)


def show_agent(name):
    """显示指定 Agent 的详细信息"""
    agent = AGENTS.get(name)
    if not agent:
        # 尝试模糊匹配
        matches = [k for k in AGENTS if name in k]
        if len(matches) == 1:
            agent = AGENTS[matches[0]]
            name = matches[0]
        else:
            return f"错误：未找到 Agent '{name}'。可用: {', '.join(AGENTS.keys())}"

    lines = []
    lines.append("=" * 64)
    lines.append(f"  {agent['name']}（{agent['role']}）")
    lines.append("=" * 64)
    lines.append(f"  ID:   {agent['id']}")
    lines.append(f"  团队: {agent['team']}")
    lines.append(f"  角色: {agent['role']}")
    lines.append(f"  职责: {agent['responsibility']}")
    lines.append(f"  工具: {', '.join(agent['tools'])}")
    lines.append(f"  描述: {agent['description']}")
    lines.append(f"  场景: {'、'.join(agent['scenarios'])}")
    lines.append("")
    lines.append("-" * 64)
    lines.append("  Prompt 简介")
    lines.append("-" * 64)
    for p in agent['prompt_intro'].split('\n'):
        lines.append(f"  {p}")
    lines.append("")
    lines.append("=" * 64)
    return '\n'.join(lines)


def recommend_agents(task_description):
    """根据任务描述推荐最优 Agent 组合"""
    task_lower = task_description.lower()

    # 关键词 -> 推荐 Agent 列表（权重排序）
    recommendations = [
        # (权重, [agent_names], 理由)
        (100, ["灵指"], ["编码实现", "功能开发"]),
        (90, ["铁壁"], ["测试验证", "质量保证"]),
        (80, ["明鉴"], ["代码审查", "质量把控"]),
        (70, ["铸基"], ["架构设计", "数据库"]),
        (60, ["蓝图"], ["需求分析", "产品设计"]),
        (50, ["匠心"], ["UI设计", "前端开发"]),
        (40, ["磐石"], ["部署运维", "监控"]),
        (30, ["求索"], ["技术调研", "方案对比"]),
        (20, ["铁卫"], ["安全审计", "漏洞扫描"]),
    ]

    # 关键词映射
    keyword_scores = {
        "bug": [(100, ["灵指"]), (90, ["明鉴"]), (80, ["铁壁"])],
        "修复": [(100, ["灵指"]), (90, ["明鉴"]), (80, ["铁壁"])],
        "测试": [(90, ["铁壁"]), (60, ["明鉴"])],
        "部署": [(90, ["磐石"]), (50, ["铸基"])],
        "监控": [(90, ["磐石"])],
        "安全": [(90, ["铁卫"]), (70, ["明鉴"])],
        "审计": [(90, ["铁卫"]), (60, ["明鉴"])],
        "漏洞": [(90, ["铁卫"]), (70, ["明鉴"])],
        "UI": [(90, ["匠心"]), (50, ["蓝图"])],
        "设计": [(80, ["匠心"]), (60, ["蓝图"])],
        "前端": [(90, ["匠心"])],
        "架构": [(90, ["铸基"]), (60, ["蓝图"])],
        "数据库": [(90, ["铸基"])],
        "需求": [(90, ["蓝图"]), (50, ["铸基"])],
        "原型": [(90, ["蓝图"]), (50, ["匠心"])],
        "调研": [(90, ["求索"])],
        "调研": [(90, ["求索"])],
        "搜索": [(70, ["求索"]), (60, ["明鉴"])],
        "审查": [(90, ["明鉴"]), (70, ["铁卫"])],
        "review": [(90, ["明鉴"]), (70, ["铁卫"])],
        "api": [(90, ["灵指"]), (70, ["铸基"])],
        "接口": [(90, ["灵指"]), (70, ["铸基"])],
        "注册": [(90, ["灵指"]), (60, ["铁壁"])],
        "登录": [(90, ["灵指"]), (60, ["铁壁"])],
        "支付": [(90, ["灵指"]), (80, ["铁卫"]), (60, ["铁壁"])],
        "性能": [(80, ["铸基"]), (70, ["灵指"]), (60, ["铁壁"])],
        "优化": [(80, ["灵指"]), (70, ["铸基"]), (60, ["铁壁"])],
        "文档": [(80, ["蓝图"]), (50, ["求索"])],
    }

    # 累加得分
    agent_scores = {}
    for agent_name in AGENTS:
        agent_scores[agent_name] = 0

    matched_keywords = []
    for keyword, scores in keyword_scores.items():
        if keyword in task_lower:
            matched_keywords.append(keyword)
            for score, names in scores:
                for name in names:
                    agent_scores[name] = agent_scores.get(name, 0) + score

    # 如果没有关键词匹配，使用默认推荐
    if not matched_keywords:
        # 默认：灵指 + 铁壁 + 明鉴
        agent_scores["灵指"] = 70
        agent_scores["铁壁"] = 50
        agent_scores["明鉴"] = 40
        agent_scores["铸基"] = 30
        reason = "通用任务（默认推荐）"
    else:
        reason = f"匹配关键词: {', '.join(matched_keywords)}"

    # 按分数排序
    sorted_agents = sorted(agent_scores.items(), key=lambda x: -x[1])
    top_agents = [(n, s) for n, s in sorted_agents if s > 0]

    # 取前3-5名
    main_agents = top_agents[:5]
    main_names = [n for n, s in main_agents]

    lines = []
    lines.append("=" * 64)
    lines.append(f"  Agent 推荐 - 任务: {task_description}")
    lines.append("=" * 64)
    lines.append(f"  {reason}")
    lines.append("")
    lines.append(f"  推荐 Agent 组合:")
    lines.append("-" * 40)

    for i, (name, score) in enumerate(main_agents, 1):
        agent = AGENTS[name]
        bar = '█' * min(int(score / 10), 10) + '░' * max(0, 10 - min(int(score / 10), 10))
        lines.append(f"  {i}. {agent['name']:<4s} ({agent['role']:<6s}) [{bar}] {score:3d}分")
        lines.append(f"     职责: {agent['responsibility']}")
        lines.append(f"     工具: {', '.join(agent['tools'])}")

    lines.append("")
    lines.append(f"  执行流程建议:")
    flow_order = ORDERED_NAMES  # 按照开发流程排序
    flow_suggested = [n for n in flow_order if n in main_names]
    if flow_suggested:
        lines.append(f"  {' → '.join(flow_suggested)}")
    else:
        lines.append(f"  {' → '.join(main_names[:3])}")

    lines.append("")
    lines.append("=" * 64)
    return '\n'.join(lines)


def build_context(name, task_desc=None, files=None, format_color=False):
    """为指定 Agent 生成任务上下文"""
    agent = AGENTS.get(name)
    if not agent:
        return f"错误：未找到 Agent '{name}'。可用: {', '.join(AGENTS.keys())}"

    lines = []
    lines.append("=" * 64)
    lines.append("  心海法律 AI - 子 Agent 任务上下文")
    lines.append("  " + datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
    lines.append("=" * 64)
    lines.append("")

    # Agent 身份
    lines.append(f"## Agent: {agent['name']}（{agent['role']}）")
    lines.append(f"- ID: {agent['id']}")
    lines.append(f"- 团队: {agent['team']}")
    lines.append(f"- 职责: {agent['responsibility']}")
    lines.append(f"- 工具: {', '.join(agent['tools'])}")
    lines.append("")

    if task_desc:
        lines.append(f"### 任务描述\n{task_desc}")
        lines.append("")

    if files:
        lines.append(f"### 相关文件\n{files}")
        lines.append("")

    # Agent Prompt
    lines.append("### Agent Prompt")
    for p in agent['prompt_intro'].split('\n'):
        lines.append(f"> {p}")
    lines.append("")

    # 基础设施信息
    lines.append("## 基础设施信息")
    lines.append("- 服务器 IP: 8.218.93.213")
    lines.append("- SSH: root / Chen0812*")
    lines.append("- 域名: xinclaw.xhacca.cn")
    lines.append("- 数据库: /home/admin/xinhai_legal.db")
    lines.append("- 框架: Flask (端口 5000)")
    lines.append("- API 前缀:")
    lines.append("  - /api/v1/ (旧版)")
    lines.append("  - /api/v2/ (旧版)")
    lines.append("  - /api/v4/ (旧版)")
    lines.append("  - /api/v5/ (旧版)")
    lines.append("  - /api/v6/ (COO 管理后台)")
    lines.append("- Nginx 路由: 8647(业务API) / 8642(AI对话) / 8646(COO管理)")
    lines.append("- Hermes Business API: /home/admin/hermes_business_api.py")
    lines.append("- Hermes Gateway: /home/admin/.hermes/ (端口8642)")
    lines.append("- COO API: /home/admin/coo_api.py (端口8646)")
    lines.append("- 小程序 AppID: wx73612d8efb98658d")
    lines.append("")

    # 验收标准
    if task_desc:
        lines.append("### 验收标准")
        lines.append("1. 任务目标完成")
        lines.append("2. 代码规范符合 PEP8")
        lines.append("3. 关键逻辑有注释和文档字符串")
        lines.append("4. 不影响已有功能")
        lines.append("")

    lines.append("=" * 64)
    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='心海法律 AI - Agent 角色管理工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    subparsers = parser.add_subparsers(dest='command', help='可用命令')

    # list
    subparsers.add_parser('list', help='列出所有 Agent')

    # show
    show_parser = subparsers.add_parser('show', help='显示 Agent 详细信息')
    show_parser.add_argument('agent_name', help='Agent 名称（如 灵指）')

    # recommend
    rec_parser = subparsers.add_parser('recommend', help='根据任务描述推荐 Agent')
    rec_parser.add_argument('task_description', help='任务描述文本')

    # context
    ctx_parser = subparsers.add_parser('context', help='生成 Agent 任务上下文')
    ctx_parser.add_argument('agent_name', help='Agent 名称')
    ctx_parser.add_argument('--task', '-t', default=None, help='任务描述')
    ctx_parser.add_argument('--files', '-f', default=None, help='相关文件路径')

    args = parser.parse_args()

    if args.command == 'list':
        print(list_agents())

    elif args.command == 'show':
        print(show_agent(args.agent_name))

    elif args.command == 'recommend':
        print(recommend_agents(args.task_description))

    elif args.command == 'context':
        print(build_context(args.agent_name, args.task, args.files))

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
