#!/usr/bin/env python3
"""
心海法律 AI - 文档同步检查脚本
检查最近修改的 .py 文件对应的文档是否同步更新。

用途：Git pre-commit 阶段调用，确保代码变更同步更新文档。
位置：/home/admin/xinhai_legal_api/scripts/check_doc_sync.py
"""

import os
import sys
import subprocess
from typing import List, Tuple

PROJECT_ROOT = '/home/admin/xinhai_legal_api'
DOCS_DIR = os.path.join(PROJECT_ROOT, 'docs')


def get_staged_py_files() -> List[str]:
    """获取本次提交中暂存的 .py 文件"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=10
        )
        files = [f.strip() for f in result.stdout.splitlines() if f.strip().endswith('.py')]
        return files
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"⚠️  git diff 执行失败: {e}", file=sys.stderr)
        return []


def get_staged_docs() -> set:
    """获取本次提交中暂存的文档文件"""
    try:
        result = subprocess.run(
            ['git', 'diff', '--cached', '--name-only', '--diff-filter=ACM'],
            capture_output=True, text=True, cwd=PROJECT_ROOT, timeout=10
        )
        files = set(f.strip() for f in result.stdout.splitlines() if f.strip().startswith('docs/'))
        return files
    except (subprocess.TimeoutExpired, subprocess.CalledProcessError) as e:
        print(f"⚠️  git diff 执行失败: {e}", file=sys.stderr)
        return set()


def find_related_doc(py_file: str) -> str | None:
    """
    根据 .py 文件推断对应的文档文件名。
    映射规则：code.py → docs/CODE.md, 或 docs/api/code.md 等
    """
    base = os.path.splitext(os.path.basename(py_file))[0]
    
    # 可能的文档文件名（不区分大小写）
    candidates = [
        f"docs/{base}.md",
        f"docs/{base.lower()}.md",
        f"docs/tech_{base}.md",
        f"docs/api_{base}.md",
        f"docs/{base.replace('_', '')}.md",
    ]
    
    # 扫描 docs/ 目录下所有 .md 文件
    if os.path.isdir(DOCS_DIR):
        for doc_file in os.listdir(DOCS_DIR):
            if not doc_file.endswith('.md'):
                continue
            doc_name = os.path.splitext(doc_file)[0].lower()
            # 匹配：文件名包含基础名，或基础名包含文档名
            if base.lower() in doc_name or doc_name in base.lower():
                return f"docs/{doc_file}"
    
    for path in candidates:
        full_path = os.path.join(PROJECT_ROOT, path)
        if os.path.isfile(full_path):
            return path
    
    return None


def check_doc_sync() -> List[Tuple[str, str, str]]:
    """
    检查文档同步情况。
    返回: [(py_file, related_doc, status)]  status: 'ok' | 'missing' | 'not_staged'
    """
    py_files = get_staged_py_files()
    staged_docs = get_staged_docs()
    
    if not py_files:
        return []
    
    results = []
    for py_file in py_files:
        related_doc = find_related_doc(py_file)
        if related_doc is None:
            # 没有对应文档，跳过（并非所有 .py 都需要文档）
            continue
        
        if related_doc in staged_docs:
            results.append((py_file, related_doc, 'ok'))
        elif os.path.isfile(os.path.join(PROJECT_ROOT, related_doc)):
            # 文档存在但未暂存
            results.append((py_file, related_doc, 'not_staged'))
        else:
            # 文档不存在
            results.append((py_file, related_doc, 'missing'))
    
    return results


def main():
    """主函数"""
    print("\n📋 检查文档同步情况...")
    print("-" * 50)
    
    results = check_doc_sync()
    
    if not results:
        print("✅ 暂存文件中无需检查文档同步")
        return 0
    
    has_warning = False
    for py_file, related_doc, status in results:
        if status == 'ok':
            print(f"  ✅ {py_file} → {related_doc} (已同步)")
        elif status == 'not_staged':
            print(f"  ⚠️  {py_file} → {related_doc} (文档已存在但未暂存，请 git add)")
            has_warning = True
        elif status == 'missing':
            print(f"  ❌ {py_file} → {related_doc} (对应文档不存在)")
            has_warning = True
    
    print("-" * 50)
    
    if has_warning:
        print("\n⚠️  检测到未同步的文档，请处理后再提交。")
        return 1
    else:
        print("\n✅ 所有文档已同步")
        return 0


if __name__ == '__main__':
    sys.exit(main())
