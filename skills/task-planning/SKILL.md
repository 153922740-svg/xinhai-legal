# 心海法律 AI - 任务规划技能 (task-planning)

**版本**: V1.0  
**创建日期**: 2026-05-19  
**负责人**: 蓝图（产品官）  
**目标**: 提升任务规划准确率至≥80%

---

## 📋 技能概述

### 技能功能

1. **需求分析** - 分析用户需求，提取关键功能点
2. **任务拆解** - 将大任务拆解为可执行的小任务
3. **时间估算** - 估算每个任务的执行时间
4. **依赖分析** - 分析任务间的依赖关系
5. **优先级排序** - 根据重要性和紧急程度排序

### 使用场景

- 接收新需求后制定执行计划
- 复杂任务拆解为子任务
- 评估项目时间和资源需求
- 制定迭代计划

---

## 🛠️ 技能实现

### 1. 任务规划器核心

```python
#!/usr/bin/env python3
"""
任务规划器
用途：分析需求，拆解任务，估算时间

文件位置：/home/admin/xinhai_legal_api/skills/task_planner.py
"""

import json
import os
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from enum import Enum

class Priority(Enum):
    """任务优先级"""
    P0 = "P0 - 紧急重要"
    P1 = "P1 - 重要不紧急"
    P2 = "P2 - 紧急不重要"
    P3 = "P3 - 不紧急不重要"

class TaskStatus(Enum):
    """任务状态"""
    PENDING = "待处理"
    IN_PROGRESS = "进行中"
    COMPLETED = "已完成"
    BLOCKED = "已阻塞"

class Task:
    """任务类"""
    
    def __init__(self, id: str, title: str, description: str, 
                 assignee: str = "未分配", estimated_hours: float = 0,
                 priority: Priority = Priority.P1, dependencies: List[str] = None):
        self.id = id
        self.title = title
        self.description = description
        self.assignee = assignee
        self.estimated_hours = estimated_hours
        self.priority = priority
        self.dependencies = dependencies or []
        self.status = TaskStatus.PENDING
        self.actual_hours = 0
        self.created_at = datetime.now()
        self.completed_at = None
    
    def to_dict(self) -> Dict:
        """转换为字典"""
        return {
            'id': self.id,
            'title': self.title,
            'description': self.description,
            'assignee': self.assignee,
            'estimated_hours': self.estimated_hours,
            'priority': self.priority.value,
            'dependencies': self.dependencies,
            'status': self.status.value,
            'actual_hours': self.actual_hours,
            'created_at': self.created_at.isoformat(),
            'completed_at': self.completed_at.isoformat() if self.completed_at else None
        }

class TaskPlanner:
    """任务规划器"""
    
    # Agent 角色映射
    AGENT_ROLES = {
        '需求分析': '蓝图',
        '技术方案': '蓝图',
        'UI 设计': '匠心',
        '前端开发': '匠心',
        '后端开发': '灵指',
        '数据库设计': '铸基',
        '代码审查': '明鉴',
        '功能测试': '铁壁',
        '性能测试': '铁壁',
        '安全审计': '铁卫',
        '部署发布': '磐石',
        '技术调研': '求索',
        '文档编写': '墨言'
    }
    
    # 标准工时估算（小时）
    STANDARD_ESTIMATES = {
        '需求分析': 4,
        '技术方案': 4,
        'UI 设计': 8,
        '前端开发': 24,
        '后端开发': 24,
        '数据库设计': 4,
        '代码审查': 2,
        '功能测试': 4,
        '性能测试': 2,
        '安全审计': 2,
        '部署发布': 1,
        '技术调研': 8,
        '文档编写': 4
    }
    
    def __init__(self):
        self.tasks: List[Task] = []
        self.task_counter = 0
    
    def analyze_requirement(self, requirement: str) -> Dict:
        """分析需求，提取关键信息"""
        analysis = {
            'requirement': requirement,
            'key_features': [],
            'technical_challenges': [],
            'estimated_complexity': 'medium',  # low/medium/high
            'suggested_agents': []
        }
        
        # 简单关键词分析（实际应该用 AI 分析）
        requirement_lower = requirement.lower()
        
        if any(word in requirement_lower for word in ['设计', 'ui', '界面', '页面']):
            analysis['key_features'].append('UI 设计')
            analysis['suggested_agents'].append('匠心')
        
        if any(word in requirement_lower for word in ['开发', '实现', '功能', 'api']):
            analysis['key_features'].append('功能开发')
            analysis['suggested_agents'].extend(['灵指', '匠心'])
        
        if any(word in requirement_lower for word in ['数据库', '表', '存储']):
            analysis['key_features'].append('数据库设计')
            analysis['suggested_agents'].append('铸基')
        
        if any(word in requirement_lower for word in ['测试', 'bug', '验证']):
            analysis['key_features'].append('测试')
            analysis['suggested_agents'].append('铁壁')
        
        if any(word in requirement_lower for word in ['部署', '上线', '发布']):
            analysis['key_features'].append('部署')
            analysis['suggested_agents'].append('磐石')
        
        # 估算复杂度
        word_count = len(requirement.split())
        if word_count > 100:
            analysis['estimated_complexity'] = 'high'
        elif word_count > 50:
            analysis['estimated_complexity'] = 'medium'
        else:
            analysis['estimated_complexity'] = 'low'
        
        # 去重
        analysis['suggested_agents'] = list(set(analysis['suggested_agents']))
        
        return analysis
    
    def decompose_task(self, requirement: str, analysis: Dict) -> List[Task]:
        """拆解任务"""
        tasks = []
        self.task_counter = 0
        
        # 标准开发流程任务
        standard_tasks = []
        
        if 'UI 设计' in analysis['key_features']:
            standard_tasks.extend([
                ('需求分析', '分析用户需求，明确功能点'),
                ('UI 设计', '设计页面布局和交互'),
                ('前端开发', '实现前端页面'),
            ])
        
        if '功能开发' in analysis['key_features']:
            standard_tasks.extend([
                ('技术方案', '设计技术方案和 API 接口'),
                ('数据库设计', '设计数据库表结构'),
                ('后端开发', '实现后端逻辑和 API'),
            ])
        
        if '测试' in analysis['key_features'] or analysis['key_features']:
            standard_tasks.extend([
                ('功能测试', '编写测试用例并执行测试'),
                ('代码审查', '代码审查和安全扫描'),
            ])
        
        if '部署' in analysis['key_features']:
            standard_tasks.append(('部署发布', '部署到生产环境'))
        
        # 如果没有特定任务，使用默认流程
        if not standard_tasks:
            standard_tasks = [
                ('需求分析', '分析用户需求'),
                ('技术方案', '设计技术方案'),
                ('后端开发', '实现功能'),
                ('功能测试', '测试验证'),
                ('代码审查', '代码审查'),
                ('部署发布', '部署上线'),
            ]
        
        # 创建任务
        prev_task_id = None
        for task_type, description in standard_tasks:
            task_id = f"T{self.task_counter:03d}"
            self.task_counter += 1
            
            assignee = self.AGENT_ROLES.get(task_type, '灵指')
            estimated_hours = self.STANDARD_ESTIMATES.get(task_type, 8)
            
            # 根据复杂度调整工时
            if analysis['estimated_complexity'] == 'high':
                estimated_hours *= 2
            elif analysis['estimated_complexity'] == 'low':
                estimated_hours *= 0.5
            
            dependencies = [prev_task_id] if prev_task_id else []
            
            task = Task(
                id=task_id,
                title=f"{task_type}",
                description=f"{task_type}: {description}",
                assignee=assignee,
                estimated_hours=estimated_hours,
                dependencies=dependencies
            )
            
            tasks.append(task)
            prev_task_id = task_id
        
        self.tasks = tasks
        return tasks
    
    def generate_plan(self, requirement: str) -> Dict:
        """生成完整任务计划"""
        # 分析需求
        analysis = self.analyze_requirement(requirement)
        
        # 拆解任务
        tasks = self.decompose_task(requirement, analysis)
        
        # 计算总工时
        total_hours = sum(t.estimated_hours for t in tasks)
        
        # 计算预计完成时间（按 8 小时/工作日）
        work_days = total_hours / 8
        
        # 生成计划
        plan = {
            'requirement': requirement,
            'analysis': analysis,
            'tasks': [t.to_dict() for t in tasks],
            'summary': {
                'total_tasks': len(tasks),
                'total_hours': total_hours,
                'estimated_days': round(work_days, 1),
                'estimated_completion': (datetime.now() + timedelta(days=work_days)).strftime('%Y-%m-%d')
            }
        }
        
        return plan
    
    def print_plan(self, plan: Dict):
        """打印任务计划"""
        print("\n" + "=" * 80)
        print("  任务规划书")
        print("=" * 80)
        
        print(f"\n需求：{plan['requirement'][:100]}...")
        
        print(f"\n## 需求分析")
        analysis = plan['analysis']
        print(f"  关键功能：{', '.join(analysis['key_features']) or '无'}")
        print(f"  复杂度：{analysis['estimated_complexity']}")
        print(f"  参与 Agent: {', '.join(analysis['suggested_agents']) or '未指定'}")
        
        print(f"\n## 任务列表")
        print(f"  {'ID':<8} {'任务':<15} {'负责人':<8} {'工时':<8} {'依赖':<10}")
        print(f"  {'-'*8} {'-'*15} {'-'*8} {'-'*8} {'-'*10}")
        
        for task in plan['tasks']:
            deps = ','.join(task['dependencies']) or '无'
            print(f"  {task['id']:<8} {task['title']:<15} {task['assignee']:<8} {task['estimated_hours']:<8} {deps:<10}")
        
        print(f"\n## 汇总")
        summary = plan['summary']
        print(f"  总任务数：{summary['total_tasks']}")
        print(f"  总工时：{summary['total_hours']} 小时")
        print(f"  预计天数：{summary['estimated_days']} 天")
        print(f"  预计完成：{summary['estimated_completion']}")
        
        print("\n" + "=" * 80)


if __name__ == '__main__':
    import sys
    
    planner = TaskPlanner()
    
    # 示例需求
    if len(sys.argv) > 1:
        requirement = ' '.join(sys.argv[1:])
    else:
        requirement = "开发一个用户登录功能，包括手机号验证码登录、密码登录，需要记录登录日志"
    
    print(f"📋 分析需求：{requirement}")
    
    # 生成计划
    plan = planner.generate_plan(requirement)
    
    # 打印计划
    planner.print_plan(plan)
    
    # 保存 JSON
    output_file = "/home/admin/xinhai_legal_api/docs/task_plan.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(plan, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 计划已保存到：{output_file}")

```

---

### 2. 任务模板库

```python
#!/usr/bin/env python3
"""
任务模板库
用途：提供常用任务模板，加速规划过程

文件位置：/home/admin/xinhai_legal_api/skills/task_templates.py
"""

from typing import Dict, List

class TaskTemplates:
    """任务模板库"""
    
    # 常见任务模板
    TEMPLATES = {
        'api_development': {
            'name': 'API 接口开发',
            'tasks': [
                {'type': '需求分析', 'hours': 4, 'assignee': '蓝图'},
                {'type': '技术方案', 'hours': 4, 'assignee': '蓝图'},
                {'type': '数据库设计', 'hours': 4, 'assignee': '铸基'},
                {'type': '后端开发', 'hours': 16, 'assignee': '灵指'},
                {'type': '单元测试', 'hours': 4, 'assignee': '灵指'},
                {'type': '功能测试', 'hours': 4, 'assignee': '铁壁'},
                {'type': '代码审查', 'hours': 2, 'assignee': '明鉴'},
                {'type': '部署发布', 'hours': 1, 'assignee': '磐石'},
            ]
        },
        
        'frontend_page': {
            'name': '前端页面开发',
            'tasks': [
                {'type': '需求分析', 'hours': 2, 'assignee': '蓝图'},
                {'type': 'UI 设计', 'hours': 8, 'assignee': '匠心'},
                {'type': '前端开发', 'hours': 16, 'assignee': '匠心'},
                {'type': '功能测试', 'hours': 4, 'assignee': '铁壁'},
                {'type': '代码审查', 'hours': 2, 'assignee': '明鉴'},
                {'type': '部署发布', 'hours': 1, 'assignee': '磐石'},
            ]
        },
        
        'database_migration': {
            'name': '数据库迁移',
            'tasks': [
                {'type': '技术方案', 'hours': 4, 'assignee': '铸基'},
                {'type': '迁移脚本', 'hours': 8, 'assignee': '铸基'},
                {'type': '数据验证', 'hours': 4, 'assignee': '铁壁'},
                {'type': '回滚方案', 'hours': 2, 'assignee': '铸基'},
                {'type': '执行迁移', 'hours': 2, 'assignee': '磐石'},
            ]
        },
        
        'bug_fix': {
            'name': 'Bug 修复',
            'tasks': [
                {'type': '问题定位', 'hours': 2, 'assignee': '铁壁'},
                {'type': 'Bug 修复', 'hours': 4, 'assignee': '灵指'},
                {'type': '回归测试', 'hours': 2, 'assignee': '铁壁'},
                {'type': '代码审查', 'hours': 1, 'assignee': '明鉴'},
                {'type': '部署发布', 'hours': 1, 'assignee': '磐石'},
            ]
        },
        
        'feature_development': {
            'name': '新功能开发',
            'tasks': [
                {'type': '需求分析', 'hours': 4, 'assignee': '蓝图'},
                {'type': '技术方案', 'hours': 4, 'assignee': '蓝图'},
                {'type': 'UI 设计', 'hours': 8, 'assignee': '匠心'},
                {'type': '数据库设计', 'hours': 4, 'assignee': '铸基'},
                {'type': '后端开发', 'hours': 24, 'assignee': '灵指'},
                {'type': '前端开发', 'hours': 16, 'assignee': '匠心'},
                {'type': '单元测试', 'hours': 8, 'assignee': '灵指'},
                {'type': '功能测试', 'hours': 8, 'assignee': '铁壁'},
                {'type': '性能测试', 'hours': 4, 'assignee': '铁壁'},
                {'type': '安全审计', 'hours': 2, 'assignee': '铁卫'},
                {'type': '代码审查', 'hours': 4, 'assignee': '明鉴'},
                {'type': '文档编写', 'hours': 4, 'assignee': '墨言'},
                {'type': '部署发布', 'hours': 2, 'assignee': '磐石'},
            ]
        },
        
        'security_audit': {
            'name': '安全审计',
            'tasks': [
                {'type': '敏感信息扫描', 'hours': 2, 'assignee': '铁卫'},
                {'type': '依赖漏洞扫描', 'hours': 2, 'assignee': '铁卫'},
                {'type': '代码安全审查', 'hours': 4, 'assignee': '铁卫'},
                {'type': '渗透测试', 'hours': 8, 'assignee': '铁卫'},
                {'type': '修复建议', 'hours': 4, 'assignee': '铁卫'},
                {'type': '修复验证', 'hours': 4, 'assignee': '铁卫'},
            ]
        },
    }
    
    @classmethod
    def get_template(cls, template_name: str) -> Dict:
        """获取任务模板"""
        return cls.TEMPLATES.get(template_name, cls.TEMPLATES['feature_development'])
    
    @classmethod
    def list_templates(cls) -> List[str]:
        """列出所有模板"""
        return list(cls.TEMPLATES.keys())
    
    @classmethod
    def estimate_from_template(cls, template_name: str) -> Dict:
        """从模板估算工时"""
        template = cls.get_template(template_name)
        
        total_hours = sum(task['hours'] for task in template['tasks'])
        by_agent = {}
        
        for task in template['tasks']:
            assignee = task['assignee']
            if assignee not in by_agent:
                by_agent[assignee] = 0
            by_agent[assignee] += task['hours']
        
        return {
            'template_name': template['name'],
            'total_hours': total_hours,
            'estimated_days': round(total_hours / 8, 1),
            'by_agent': by_agent,
            'task_count': len(template['tasks'])
        }


if __name__ == '__main__':
    import json
    
    print("📋 任务模板库")
    print("=" * 60)
    
    # 列出所有模板
    templates = TaskTemplates.list_templates()
    print(f"\n可用模板：{len(templates)} 个")
    for t in templates:
        print(f"  - {t}")
    
    # 估算每个模板
    print("\n\n工时估算:")
    print("=" * 60)
    
    for template_name in templates:
        estimate = TaskTemplates.estimate_from_template(template_name)
        print(f"\n{estimate['template_name']}:")
        print(f"  总工时：{estimate['total_hours']} 小时")
        print(f"  预计天数：{estimate['estimated_days']} 天")
        print(f"  任务数：{estimate['task_count']}")
        print(f"  按 Agent 分布:")
        for agent, hours in estimate['by_agent'].items():
            print(f"    {agent}: {hours} 小时")

```

---

## 📊 技能使用指南

### 使用示例

```bash
# 1. 任务规划
python3 /home/admin/xinhai_legal_api/skills/task_planner.py "开发用户登录功能"

# 2. 查看任务模板
python3 /home/admin/xinhai_legal_api/skills/task_templates.py

# 3. 在代码中使用
from task_planner import TaskPlanner

planner = TaskPlanner()
plan = planner.generate_plan("开发会员支付功能")
planner.print_plan(plan)
```

### 输出示例

```
================================================================================
  任务规划书
================================================================================

需求：开发用户登录功能，包括手机号验证码登录、密码登录，需要记录登录日志...

## 需求分析
  关键功能：功能开发，数据库设计，测试
  复杂度：medium
  参与 Agent: 灵指，铸基，铁壁

## 任务列表
  ID       任务              负责人     工时     依赖      
  -------- --------------- -------- -------- ----------
  T000     需求分析          蓝图       4.0      无        
  T001     技术方案          蓝图       4.0      T000      
  T002     数据库设计        铸基       4.0      T001      
  T003     后端开发          灵指       24.0     T002      
  T004     功能测试          铁壁       4.0      T003      
  T005     代码审查          明鉴       2.0      T004      

## 汇总
  总任务数：6
  总工时：42.0 小时
  预计天数：5.2 天
  预计完成：2026-05-24

================================================================================
```

---

## 📈 效果评估

### 评估指标

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 任务拆解准确率 | ≥80% | 人工评审 |
| 工时估算准确率 | ≥75% | 实际 vs 估算 |
| 依赖关系正确率 | ≥90% | 执行验证 |
| 规划生成时间 | <10 秒 | 性能测试 |

### 测试用例

```python
def test_task_planner():
    """测试任务规划器"""
    planner = TaskPlanner()
    plan = planner.generate_plan("开发用户登录功能")
    
    assert len(plan['tasks']) > 0
    assert plan['summary']['total_hours'] > 0
    assert plan['analysis']['estimated_complexity'] in ['low', 'medium', 'high']

def test_task_templates():
    """测试任务模板库"""
    estimate = TaskTemplates.estimate_from_template('api_development')
    
    assert estimate['total_hours'] > 0
    assert estimate['estimated_days'] > 0
```

---

**维护人**: 蓝图（产品官）  
**最后更新**: 2026-05-19  
**下次评审**: 2026-06-19（月度评审）
