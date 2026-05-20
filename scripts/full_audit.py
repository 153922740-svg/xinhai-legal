#!/usr/bin/env python3
"""
心海法律 AI - 全量审计脚本
执行全面的代码和项目审计，输出JSON格式报告。

审计维度：
  1. 代码语法检查
  2. 文档完整性检查
  3. 接口注册表完整性
  4. 测试覆盖率（文件级别）
  5. 制度违规记录

用法：
  python3 scripts/full_audit.py                    # 输出到控制台
  python3 scripts/full_audit.py --save             # 输出到 audit_reports/ 目录
  python3 scripts/full_audit.py --output report.json  # 输出到指定路径

位置：/home/admin/xinhai_legal_api/scripts/full_audit.py
"""

import os
import sys
import ast
import json
import re
import fnmatch
import subprocess
import argparse
from datetime import datetime
from typing import Dict, List, Any

PROJECT_ROOT = '/home/admin/xinhai_legal_api'
AUDIT_REPORTS_DIR = os.path.join(PROJECT_ROOT, 'audit_reports')
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')
TESTS_DIR = os.path.join(PROJECT_ROOT, 'tests')

# 排除目录
EXCLUDE_DIRS = {'venv', '__pycache__', '.git', '.mypy_cache',
                '.pytest_cache', 'node_modules', '.env', 'dist',
                'build', 'audit_reports', 'logs', 'data'}

# 排除文件模式
EXCLUDE_FILES_PATTERNS = ['*.pyc', '*.pyo', '*.so', '*.dll', '*.exe',
                          '*.tar.gz', '*.zip', '*.rar', '*.7z',
                          '*.lock', '*.log']


def should_exclude(path: str) -> bool:
    """检查路径是否应排除"""
    rel = os.path.relpath(path, PROJECT_ROOT)
    parts = rel.split(os.sep)
    for part in parts:
        if part in EXCLUDE_DIRS:
            return True
    for pattern in EXCLUDE_FILES_PATTERNS:
        if fnmatch.fnmatch(os.path.basename(path), pattern):
            return True
    return False


def find_py_files(root: str = PROJECT_ROOT) -> List[str]:
    """查找所有 .py 文件（排除虚拟环境等）"""
    py_files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 原地修改 dirnames 以排除目录
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        for f in filenames:
            if f.endswith('.py'):
                full = os.path.join(dirpath, f)
                if not should_exclude(full):
                    py_files.append(full)
    return py_files


# ─── 审计模块 1: 代码语法检查 ──────────────────────────────

def audit_syntax(py_files: List[str]) -> Dict[str, Any]:
    """检查所有 .py 文件的语法"""
    results = {
        'total_files': len(py_files),
        'passed': 0,
        'failed': 0,
        'errors': []
    }
    for fp in py_files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                source = f.read()
            ast.parse(source)
            results['passed'] += 1
        except SyntaxError as e:
            results['failed'] += 1
            rel = os.path.relpath(fp, PROJECT_ROOT)
            results['errors'].append({
                'file': rel,
                'line': e.lineno,
                'message': str(e)
            })
    return results


# ─── 审计模块 2: 文档完整性 ──────────────────────────────

def audit_docs(py_files: List[str]) -> Dict[str, Any]:
    """检查文档完整性：每个核心 .py 是否有对应的文档"""
    if not os.path.isdir(DOCS_DIR):
        return {
            'total_docs': 0,
            'total_py_modules': 0,
            'documented': 0,
            'undocumented': [],
            'warning': 'docs/ 目录不存在'
        }
    
    doc_files = [f for f in os.listdir(DOCS_DIR) if f.endswith('.md')]
    doc_names = set(os.path.splitext(f)[0].lower() for f in doc_files)
    
    # 只检查项目根目录下的顶级 .py 模块和 services/、models/ 等核心目录
    undocumented = []
    for fp in py_files:
        rel = os.path.relpath(fp, PROJECT_ROOT)
        base = os.path.splitext(os.path.basename(fp))[0].lower()
        
        # 检查是否有匹配的文档名
        matched = False
        for dn in doc_names:
            if base in dn or dn in base:
                matched = True
                break
        
        # 如果文件名包含 test_ 则不需要文档
        if base.startswith('test_') or base == '__init__':
            continue
        
        if not matched:
            undocumented.append(rel)
    
    return {
        'total_docs': len(doc_files),
        'total_py_modules': len(py_files),
        'documented': len(py_files) - len(undocumented),
        'undocumented': undocumented[:30]  # 最多显示30个
    }


# ─── 审计模块 3: 接口注册表完整性 ──────────────────────────

def audit_api_registry() -> Dict[str, Any]:
    """扫描所有 .py 文件中的 API 路由注册"""
    api_pattern = re.compile(
        r'@(?:app|router|api)\.(?:get|post|put|delete|patch)\([\'\"]([^\'\"]+)[\'\"]',
        re.IGNORECASE
    )
    route_pattern = re.compile(
        r'(?:\.add_url_rule|\.route)\s*\([\'\"]([^\'\"]+)[\'\"]',
        re.IGNORECASE
    )
    
    routes = []
    py_files = find_py_files()
    
    for fp in py_files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                content = f.read()
            
            for pattern in [api_pattern, route_pattern]:
                for m in pattern.finditer(content):
                    rel = os.path.relpath(fp, PROJECT_ROOT)
                    routes.append({
                        'file': rel,
                        'route': m.group(1)
                    })
        except Exception:
            continue
    
    return {
        'total_routes': len(routes),
        'routes': routes
    }


# ─── 审计模块 4: 测试覆盖率（文件级别） ──────────────────────

def audit_test_coverage(py_files: List[str]) -> Dict[str, Any]:
    """检查测试覆盖率：核心 .py 是否有对应的测试文件"""
    if not os.path.isdir(TESTS_DIR):
        return {
            'total_tests': 0,
            'total_modules': 0,
            'covered': 0,
            'uncovered': [],
            'warning': 'tests/ 目录不存在'
        }
    
    test_files = set()
    for f in os.listdir(TESTS_DIR):
        if f.endswith('.py') and f.startswith('test_'):
            # test_xxx.py → xxx
            test_files.add(f[5:-3].lower())
    
    coverable = []
    uncovered = []
    for fp in py_files:
        rel = os.path.relpath(fp, PROJECT_ROOT)
        base = os.path.splitext(os.path.basename(fp))[0].lower()
        
        if base.startswith('test_') or base == '__init__':
            continue
        
        coverable.append(rel)
        
        # 是否被覆盖
        matched = False
        for tf in test_files:
            if base in tf or tf in base:
                matched = True
                break
        if not matched:
            uncovered.append(rel)
    
    return {
        'total_tests': len(test_files),
        'total_modules': len(coverable),
        'covered': len(coverable) - len(uncovered),
        'uncovered': uncovered[:30]
    }


# ─── 审计模块 5: 制度违规记录 ──────────────────────────────

def audit_policy_violations(py_files: List[str]) -> Dict[str, Any]:
    """扫描代码中的潜在制度违规（硬编码、不安全操作等）"""
    violations = []
    
    # 检查模式
    patterns = {
        'hardcoded_password': (re.compile(r'password\s*=\s*[\"\'][^\"\']+[\"\']', re.IGNORECASE), '硬编码密码'),
        'eval_exec': (re.compile(r'\b(?:eval|exec|compile)\s*\('), '使用 eval/exec'),
        'unsafe_pickle': (re.compile(r'\b(?:pickle\.loads?)\s*\('), '不安全的 pickle 反序列化'),
        'print_debug': (re.compile(r'print\s*\(\s*[\"\']?[Dd][Ee][Bb][Uu][Gg]'), '遗留 debug print'),
        'todo_fixme': (re.compile(r'#\s*(?:TODO|FIXME|HACK|XXX)\b'), '遗留 TODO/FIXME'),
        'raw_sql': (re.compile(r'(?:execute|executescript)\s*\(\s*[\"\']'), '原始 SQL 执行'),
    }
    
    for fp in py_files:
        try:
            with open(fp, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
        except Exception:
            continue
        
        for i, line in enumerate(lines, 1):
            for key, (pattern, desc) in patterns.items():
                if pattern.search(line):
                    rel = os.path.relpath(fp, PROJECT_ROOT)
                    # 跳过测试文件和 venv
                    if 'venv/' in rel or rel.startswith('tests/'):
                        continue
                    violations.append({
                        'file': rel,
                        'line': i,
                        'type': key,
                        'description': desc,
                        'content': line.strip()[:100]
                    })
                    break  # 每行只报一个违规
    
    # 按类型统计
    by_type: Dict[str, int] = {}
    for v in violations:
        by_type[v['type']] = by_type.get(v['type'], 0) + 1
    
    return {
        'total_violations': len(violations),
        'by_type': by_type,
        'violations': violations[:50]  # 最多显示50条
    }


# ─── 主审计函数 ──────────────────────────────────────────

def run_full_audit() -> Dict[str, Any]:
    """执行全量审计"""
    start_time = datetime.now()
    print("🔍 开始全量审计...\n")
    
    py_files = find_py_files()
    print(f"  扫描到 {len(py_files)} 个 Python 文件\n")
    
    # 各模块审计
    syntax_result = audit_syntax(py_files)
    print(f"  ✅ 语法检查: {syntax_result['passed']} passed, {syntax_result['failed']} failed")
    
    docs_result = audit_docs(py_files)
    print(f"  ✅ 文档检查: {docs_result['documented']}/{docs_result['total_py_modules']} 有文档")
    
    api_result = audit_api_registry()
    print(f"  ✅ 接口检查: 发现 {api_result['total_routes']} 个路由")
    
    coverage_result = audit_test_coverage(py_files)
    print(f"  ✅ 测试覆盖: {coverage_result['covered']}/{coverage_result['total_modules']} 模块有测试")
    
    policy_result = audit_policy_violations(py_files)
    print(f"  ✅ 制度检查: 发现 {policy_result['total_violations']} 个潜在违规")
    
    elapsed = (datetime.now() - start_time).total_seconds()
    
    # 综合评分（0-100）
    score = 100
    if syntax_result['failed'] > 0:
        score -= syntax_result['failed'] * 20
    if docs_result.get('warning'):
        score -= 10
    if len(docs_result.get('undocumented', [])) > 0:
        score -= len(docs_result['undocumented']) * 2
    if len(coverage_result.get('uncovered', [])) > 0:
        score -= len(coverage_result['uncovered']) * 2
    if policy_result['total_violations'] > 0:
        score -= policy_result['total_violations'] * 3
    score = max(0, min(100, score))
    
    report = {
        'report_id': f"AUDIT-{datetime.now().strftime('%Y%m%d-%H%M%S')}",
        'timestamp': datetime.now().isoformat(),
        'project': '心海法律 AI',
        'project_root': PROJECT_ROOT,
        'audit_duration_seconds': round(elapsed, 2),
        'overall_score': score,
        'sections': {
            'syntax_check': syntax_result,
            'docs_integrity': docs_result,
            'api_registry': api_result,
            'test_coverage': coverage_result,
            'policy_violations': policy_result
        }
    }
    
    return report


def print_report(report: Dict[str, Any]):
    """打印审计报告到控制台"""
    print("\n" + "=" * 60)
    print(f"  心海法律 AI - 全量审计报告")
    print(f"  {report['report_id']}")
    print("=" * 60)
    print(f"  时间: {report['timestamp']}")
    print(f"  耗时: {report['audit_duration_seconds']} 秒")
    print(f"  综合评分: {report['overall_score']}/100")
    print("=" * 60)
    
    s = report['sections']
    
    # 语法
    sx = s['syntax_check']
    status = '✅' if sx['failed'] == 0 else '❌'
    print(f"\n{status} 代码语法: {sx['passed']}/{sx['total_files']} 通过")
    for err in sx['errors']:
        print(f"     ❌ {err['file']}:{err['line']} - {err['message']}")
    
    # 文档
    dc = s['docs_integrity']
    if dc.get('warning'):
        print(f"\n⚠️  文档完整性: {dc['warning']}")
    else:
        print(f"\n📋 文档完整性: {dc['documented']}/{dc['total_py_modules']} 有文档")
        for ud in dc.get('undocumented', [])[:10]:
            print(f"     📄 缺少文档: {ud}")
        if len(dc.get('undocumented', [])) > 10:
            print(f"     ... 还有 {len(dc['undocumented']) - 10} 个缺少文档")
    
    # 接口
    ar = s['api_registry']
    print(f"\n🔌 接口注册: 发现 {ar['total_routes']} 个路由")
    
    # 测试
    tc = s['test_coverage']
    if tc.get('warning'):
        print(f"\n⚠️  测试覆盖: {tc['warning']}")
    else:
        print(f"\n🧪 测试覆盖: {tc['covered']}/{tc['total_modules']} 有测试")
        for uc in tc.get('uncovered', [])[:10]:
            print(f"     🔴 无测试: {uc}")
        if len(tc.get('uncovered', [])) > 10:
            print(f"     ... 还有 {len(tc['uncovered']) - 10} 个无测试")
    
    # 制度
    pv = s['policy_violations']
    print(f"\n🚨 制度违规: {pv['total_violations']} 个")
    for v in pv.get('violations', [])[:10]:
        print(f"     ⚠️  {v['file']}:{v['line']} [{v['description']}]")
        print(f"         {v['content']}")
    if len(pv.get('violations', [])) > 10:
        print(f"     ... 还有 {len(pv['violations']) - 10} 个")
    
    print("\n" + "=" * 60)
    print(f"  综合评分: {report['overall_score']}/100")
    if report['overall_score'] >= 80:
        print("  状态: ✅ 良好")
    elif report['overall_score'] >= 60:
        print("  状态: ⚠️  一般")
    else:
        print("  状态: ❌ 需整改")
    print("=" * 60)


def save_report(report: Dict[str, Any], output_path: str = None):
    """保存审计报告到文件"""
    if output_path is None:
        os.makedirs(AUDIT_REPORTS_DIR, exist_ok=True)
        output_path = os.path.join(
            AUDIT_REPORTS_DIR,
            f"audit_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        )
    
    with open(output_path, 'w', encoding='utf-8') as f:
        json.dump(report, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 审计报告已保存到: {output_path}")
    return output_path


def main():
    parser = argparse.ArgumentParser(description='心海法律 AI - 全量审计脚本')
    parser.add_argument('--save', action='store_true',
                       help='保存报告到 audit_reports/ 目录')
    parser.add_argument('--output', '-o', type=str, default=None,
                       help='保存报告到指定路径')
    args = parser.parse_args()
    
    report = run_full_audit()
    print_report(report)
    
    if args.output:
        save_report(report, args.output)
    elif args.save:
        save_report(report)
    
    # 返回状态码：有严重问题返回1
    s = report['sections']
    if s['syntax_check']['failed'] > 0:
        return 1
    if report['overall_score'] < 50:
        return 1
    return 0


if __name__ == '__main__':
    sys.exit(main())
