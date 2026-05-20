#!/usr/bin/env python3
"""
心海法律 AI - 代码骨架索引工具
==============================
功能：扫描项目目录，用 ast 模块解析 Python 源码，输出结构化代码索引。

用法：
    python3 code_skeleton.py --output json          # JSON 格式输出
    python3 code_skeleton.py --output text          # 树形结构输出
    python3 code_skeleton.py --refresh              # 强制刷新缓存
"""

import ast
import os
import sys
import json
import time
import hashlib
import argparse

PROJECT_ROOT = '/home/admin/xinhai_legal_api'
CACHE_FILE = '/tmp/code_skeleton_cache.json'
CACHE_TTL = 3600  # 1小时

# ============================================================
# 排除目录
# ============================================================
EXCLUDE_DIRS = {'venv', '__pycache__', '.git', '.mypy_cache',
                '.pytest_cache', 'node_modules', '.env', 'dist', 'build'}

EXCLUDE_FILES = {'__init__.py', 'venv'}


def get_project_name():
    return os.path.basename(PROJECT_ROOT.rstrip('/'))


def walk_py_files(root):
    """扫描项目目录，返回所有 .py 文件路径列表（排除 excluded 目录）"""
    files = []
    for dirpath, dirnames, filenames in os.walk(root):
        # 排除目录：原地修改 dirnames 以避免 os.walk 进入
        dirnames[:] = [d for d in dirnames if d not in EXCLUDE_DIRS]
        # 跳过 venv 本身的目录（绝对路径匹配）
        if any(excl in dirpath.split(os.sep) for excl in EXCLUDE_DIRS):
            continue
        for f in filenames:
            if f.endswith('.py') and f not in EXCLUDE_FILES:
                full_path = os.path.join(dirpath, f)
                files.append(full_path)
    return sorted(files)


def _get_qualified_name(node, parent_name=''):
    """尝试从节点构建限定名（用于嵌套类）"""
    name = getattr(node, 'name', None)
    if not name:
        return ''
    if parent_name:
        return f'{parent_name}.{name}'
    return name


def _extract_docstring(node):
    """提取节点的 docstring"""
    if (node.body and isinstance(node.body[0], ast.Expr)
            and isinstance(node.body[0].value, (ast.Constant, ast.Str))):
        return node.body[0].value.s if hasattr(node.body[0].value, 's') else node.body[0].value.value
    return ''


def parse_file(filepath):
    """用 ast 解析单个 Python 文件，返回结构化信息"""
    result = {
        'path': os.path.relpath(filepath, PROJECT_ROOT),
        'lines': 0,
        'classes': [],
        'functions': [],
        'api_endpoints': [],
        'database_tables': [],
        'imports': [],
    }

    try:
        with open(filepath, 'r', encoding='utf-8', errors='replace') as f:
            content = f.read()
    except Exception as e:
        result['parse_error'] = str(e)
        return result

    result['lines'] = content.count('\n') + 1

    try:
        tree = ast.parse(content, filename=filepath)
    except SyntaxError as e:
        result['parse_error'] = str(e)
        return result

    # 用于收集装饰器的 helper
    def _is_route_decorator(decorator):
        """判断是否为路由装饰器 @app.route / @bp.route / @router.get/post/put/delete"""
        if isinstance(decorator, ast.Call):
            func = decorator.func
            if isinstance(func, ast.Attribute):
                attr_name = func.attr
                # @app.route(...) / @bp.route(...)
                if attr_name == 'route':
                    return True
                # @router.get / @router.post / @router.put / @router.delete
                if attr_name in ('get', 'post', 'put', 'delete', 'patch'):
                    return True
                # @bp.get / @bp.post 等
                if attr_name in ('get', 'post', 'put', 'delete', 'patch'):
                    return True
            elif isinstance(func, ast.Call):
                # 处理 @api.route('/path')(decorator_func) 这种嵌套
                inner = func.func
                if isinstance(inner, ast.Attribute) and inner.attr == 'route':
                    return True
        return False

    def _extract_route_path(decorator):
        """从路由装饰器中提取路径"""
        if isinstance(decorator, ast.Call):
            args = decorator.args
            if args:
                val = args[0]
                if isinstance(val, ast.Constant) and isinstance(val.value, str):
                    return val.value
                if isinstance(val, ast.Str):
                    return val.s
            # 查找 keywords 中的 path 参数
            for kw in decorator.keywords:
                if kw.arg == 'path':
                    if isinstance(kw.value, ast.Constant) and isinstance(kw.value.value, str):
                        return kw.value.value
                    if isinstance(kw.value, ast.Str):
                        return kw.value.s
        return ''

    def _extract_route_methods(decorator):
        """从路由装饰器中提取 HTTP 方法"""
        if isinstance(decorator, ast.Call):
            func = decorator.func
            # @router.get / @router.post 等 -> 方法从属性名推断
            if isinstance(func, ast.Attribute):
                method_map = {
                    'get': 'GET', 'post': 'POST', 'put': 'PUT',
                    'delete': 'DELETE', 'patch': 'PATCH',
                }
                if func.attr in method_map:
                    return [method_map[func.attr]]

            # @app.route(..., methods=['GET', 'POST'])
            for kw in decorator.keywords:
                if kw.arg == 'methods' and isinstance(kw.value, (ast.List, ast.Tuple)):
                    methods = []
                    for elt in kw.value.elts:
                        if isinstance(elt, ast.Constant) and isinstance(elt.value, str):
                            methods.append(elt.value)
                        elif isinstance(elt, ast.Str):
                            methods.append(elt.s)
                    if methods:
                        return methods
        return ['GET']  # 默认 GET

    def _extract_table_names(body_text):
        """从 CREATE TABLE 语句中提取表名"""
        import re
        tables = []
        # 匹配 CREATE TABLE IF NOT EXISTS table_name 或 CREATE TABLE table_name
        pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
        for match in re.finditer(pattern, body_text, re.IGNORECASE):
            tables.append(match.group(1))
        return tables

    # 遍历 AST 节点
    for node in ast.walk(tree):
        # 类定义
        if isinstance(node, ast.ClassDef):
            cls_info = {
                'name': node.name,
                'methods': [],
                'decorators': [],
                'docstring': _extract_docstring(node)[:200],
                'line': node.lineno,
            }
            # 提取类的方法
            for item in node.body:
                if isinstance(item, (ast.FunctionDef, ast.AsyncFunctionDef)):
                    cls_info['methods'].append(item.name)
                # 嵌套类
                elif isinstance(item, ast.ClassDef):
                    cls_info['methods'].append(f'class {item.name}')

            result['classes'].append(cls_info)

        # 函数定义（最外层）
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 只处理最外层的函数（不在类内的）
            if not isinstance(getattr(node, 'parent', None), ast.ClassDef):
                # 设置 parent 关系
                pass

    # 第二次遍历：正确识别最外层函数（通过手动跟踪）
    for node in ast.walk(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 检查是否在类内部
            in_class = False
            for parent in ast.walk(tree):
                if isinstance(parent, ast.ClassDef):
                    for child in parent.body:
                        if child is node:
                            in_class = True
                            break
                if in_class:
                    break
            if not in_class:
                func_info = {
                    'name': node.name,
                    'decorators': [],
                    'docstring': _extract_docstring(node)[:200],
                    'line': node.lineno,
                }
                result['functions'].append(func_info)

    # 第三次遍历：提取路由和装饰器信息
    for node in ast.iter_child_nodes(tree):
        if isinstance(node, (ast.FunctionDef, ast.AsyncFunctionDef)):
            # 检查装饰器
            for dec in node.decorator_list:
                if _is_route_decorator(dec):
                    path = _extract_route_path(dec)
                    methods = _extract_route_methods(dec)
                    full_path = path  # 可能不完整，稍后从父节点推断
                    func_name = node.name
                    result['api_endpoints'].append({
                        'function': func_name,
                        'path': path,
                        'methods': methods,
                        'line': node.lineno,
                    })

    # 提取数据库表：在源码字符串中搜索 CREATE TABLE
    import re
    table_pattern = r'CREATE\s+TABLE\s+(?:IF\s+NOT\s+EXISTS\s+)?(\w+)'
    for match in re.findall(table_pattern, content, re.IGNORECASE):
        if match not in result['database_tables']:
            result['database_tables'].append(match)

    return result


def get_cache_hash():
    """生成缓存哈希（基于文件修改时间）"""
    hasher = hashlib.md5()
    for root, dirs, files in os.walk(PROJECT_ROOT):
        dirs[:] = [d for d in dirs if d not in EXCLUDE_DIRS]
        if any(excl in root.split(os.sep) for excl in EXCLUDE_DIRS):
            continue
        for f in files:
            if f.endswith('.py') and f not in EXCLUDE_FILES:
                fp = os.path.join(root, f)
                try:
                    mtime = os.path.getmtime(fp)
                    hasher.update(f'{fp}:{mtime}'.encode())
                except OSError:
                    pass
    return hasher.hexdigest()


def load_cache():
    """加载缓存（如果有效）"""
    if not os.path.exists(CACHE_FILE):
        return None
    try:
        with open(CACHE_FILE, 'r', encoding='utf-8') as f:
            cache = json.load(f)
        age = time.time() - cache.get('timestamp', 0)
        if age < CACHE_TTL:
            # 验证哈希
            current_hash = get_cache_hash()
            if cache.get('hash') == current_hash:
                return cache['data']
        print("[缓存过期，重新扫描]", file=sys.stderr)
        return None
    except (json.JSONDecodeError, KeyError, ValueError) as e:
        print(f"[缓存读取失败: {e}]", file=sys.stderr)
        return None


def save_cache(data):
    """保存缓存"""
    try:
        cache = {
            'timestamp': time.time(),
            'hash': get_cache_hash(),
            'data': data,
        }
        with open(CACHE_FILE, 'w', encoding='utf-8') as f:
            json.dump(cache, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print(f"[缓存写入失败: {e}]", file=sys.stderr)


def _module_name_from_path(rel_path):
    """根据相对路径推断模块名"""
    # 映射已知文件到有意义的名字
    name_map = {
        'app.py': '统一路由入口',
        'phase4_user_auth_api.py': '用户认证',
        'phase2_member_api.py': '会员系统',
        'phase2_token_billing.py': 'Token计费',
        'phase2_payment_wechat.py': '微信支付',
        'phase2_dashboard_api.py': '数据看板',
        'phase3_ai_chat_api.py': 'AI对话',
        'phase3_document_generator.py': '文书生成',
        'phase3_contract_review.py': '合同审查',
        'phase5_input_enhance_api.py': '输入增强',
        'phase5_input_enhance_v2.py': '输入增强V2',
        'phase6_self_evolution_api.py': '自进化系统',
        'phase7_partner_system_api.py': '合伙人系统',
        'phase8_user_auth_api.py': '用户认证V8',
        'phase9_integral_system_api.py': '积分系统',
        'phase10_cross_validation_api.py': '交叉验证',
        'phase11_document_enhance_api.py': '文档增强',
        'phase13_history_api.py': '历史记录',
        'phase14_recommendation.py': '智能推荐',
        'phase15_dashboard.py': '运营看板',
        'models/db.py': '数据库模型',
        'services/auth.py': '认证服务',
        'services/billing.py': '计费服务',
        'services/chat_router.py': '对话路由',
        'chroma_search.py': '语义搜索',
        'long_term_memory.py': '长期记忆',
        'skills/knowledge_manager.py': '知识管理',
        'skills/snippet_manager.py': '片段管理',
        'skills/quality_dashboard.py': '质量看板',
    }
    if rel_path in name_map:
        return name_map[rel_path]

    # 按目录划分
    parts = rel_path.split(os.sep)
    if parts[0] == 'models':
        return '数据模型'
    if parts[0] == 'services':
        return '业务服务'
    if parts[0] == 'skills':
        return '技能模块'
    if parts[0] == 'scripts':
        return '工具脚本'
    # 默认用文件名去掉扩展名
    name = os.path.splitext(parts[-1])[0]
    return name.replace('_', ' ').title()


def build_index(files_info, force_refresh=False):
    """构建完整索引"""
    # 尝试缓存
    if not force_refresh:
        cached = load_cache()
        if cached:
            return cached

    total_lines = 0
    modules_dict = {}  # module_name -> module data

    all_api_endpoints = []
    all_database_tables = set()

    for info in files_info:
        total_lines += info['lines']
        rel_path = info['path']
        mname = _module_name_from_path(rel_path)

        if mname not in modules_dict:
            modules_dict[mname] = {
                'name': mname,
                'files': [],
            }

        file_entry = {
            'path': rel_path,
            'lines': info['lines'],
            'classes': [c['name'] for c in info.get('classes', [])],
            'functions': [f['name'] + '()' for f in info.get('functions', [])],
        }
        modules_dict[mname]['files'].append(file_entry)

        # 收集 API 端点
        for ep in info.get('api_endpoints', []):
            path = ep.get('path', '')
            methods = ep.get('methods', ['GET'])
            for method in methods:
                all_api_endpoints.append({
                    'path': path,
                    'method': method,
                    'file': rel_path,
                    'line': ep.get('line', 0),
                })

        # 收集数据库表
        for t in info.get('database_tables', []):
            all_database_tables.add(t)

    # 排序模块
    modules = sorted(modules_dict.values(), key=lambda m: m['name'])

    index = {
        'project': get_project_name(),
        'total_files': len(files_info),
        'total_lines': total_lines,
        'modules': modules,
        'api_endpoints': sorted(all_api_endpoints, key=lambda x: (x['path'], x['method'])),
        'database_tables': sorted(all_database_tables),
    }

    # 保存缓存
    save_cache(index)
    return index


def format_json(index):
    """输出 JSON 格式"""
    return json.dumps(index, ensure_ascii=False, indent=2)


def format_text(index):
    """输出树形结构"""
    lines = []
    lines.append('=' * 64)
    lines.append(f'  心海法律 AI - 代码骨架索引')
    lines.append(f'  项目: {index["project"]}')
    lines.append(f'  文件数: {index["total_files"]}  |  总行数: {index["total_lines"]}')
    lines.append('=' * 64)
    lines.append('')

    # 模块树
    lines.append('📦 模块结构')
    lines.append('─' * 40)
    for mod in index['modules']:
        lines.append(f'  📁 {mod["name"]}')
        for f in mod['files']:
            lines.append(f'    📄 {f["path"]}  ({f["lines"]} 行)')
            if f['classes']:
                classes_str = ', '.join(f['classes'][:8])
                if len(f['classes']) > 8:
                    classes_str += f' ... (+{len(f["classes"])-8})'
                lines.append(f'      🏷 类: {classes_str}')
            if f['functions']:
                funcs_str = ', '.join(f['functions'][:10])
                if len(f['functions']) > 10:
                    funcs_str += f' ... (+{len(f["functions"])-10})'
                lines.append(f'      ⚡ 函数: {funcs_str}')
    lines.append('')

    # API 端点列表
    lines.append('🔌 API 端点')
    lines.append('─' * 60)
    if index['api_endpoints']:
        for ep in index['api_endpoints']:
            lines.append(f'  {ep["method"]:6s} {ep["path"]:40s} [{ep["file"]}:{ep["line"]}]')
    else:
        lines.append('  (无检测到路由装饰器 - 如需精确路由，请参考 app.py 的蓝图注册)')
    lines.append('')

    # 数据库表
    lines.append('🗄  数据库表')
    lines.append('─' * 40)
    if index['database_tables']:
        for t in index['database_tables']:
            lines.append(f'  📋 {t}')
    else:
        lines.append('  (未发现 CREATE TABLE 语句)')
    lines.append('')

    # 统计信息
    lines.append('─' * 40)
    total_classes = sum(len(f['classes']) for mod in index['modules'] for f in mod['files'])
    total_functions = sum(len(f['functions']) for mod in index['modules'] for f in mod['files'])
    lines.append(f'  统计: {total_classes} 个类, {total_functions} 个函数/方法, '
                 f'{len(index["api_endpoints"])} 个API端点, {len(index["database_tables"])} 个数据库表')
    lines.append('=' * 64)

    return '\n'.join(lines)


def main():
    parser = argparse.ArgumentParser(
        description='心海法律 AI - 代码骨架索引工具',
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=__doc__,
    )
    parser.add_argument('--output', '-o', choices=['json', 'text'], default='json',
                        help='输出格式 (默认: json)')
    parser.add_argument('--refresh', '-r', action='store_true',
                        help='强制重新扫描，不使用缓存')
    parser.add_argument('--file', '-f', type=str, default=None,
                        help='只扫描指定文件（逗号分隔）')

    args = parser.parse_args()

    # 获取文件列表
    if args.file:
        file_list = [os.path.join(PROJECT_ROOT, f.strip()) for f in args.file.split(',')]
        existing = [f for f in file_list if os.path.exists(f)]
        if not existing:
            print(f"错误：未找到指定的文件: {args.file}", file=sys.stderr)
            sys.exit(1)
        py_files = existing
    else:
        py_files = walk_py_files(PROJECT_ROOT)

    print(f"[扫描 {len(py_files)} 个 .py 文件...]", file=sys.stderr)

    # 解析每个文件
    files_info = []
    for fp in py_files:
        info = parse_file(fp)
        files_info.append(info)
        if info.get('parse_error'):
            print(f"  ⚠ {info['path']}: 解析错误 - {info['parse_error']}", file=sys.stderr)

    # 构建索引
    index = build_index(files_info, force_refresh=args.refresh)

    # 输出
    if args.output == 'json':
        print(format_json(index))
    else:
        print(format_text(index))


if __name__ == '__main__':
    main()
