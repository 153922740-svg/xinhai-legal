# 第二阶段技能包（文档生成 + 性能优化 + 安全编码）

**版本**: V1.0  
**创建日期**: 2026-05-19  
**负责人**: 墨言 + 铸基 + 铁卫  
**目标**: 综合评分达到 80/100

---

## 文档生成技能 (doc-generator)

**负责人**: 墨言（内容官）

### 功能
1. 自动生成 API 文档
2. 自动生成 README
3. 自动生成变更日志
4. 自动生成用户手册

### 实现

```python
#!/usr/bin/env python3
"""文档生成器 - /home/admin/xinhai_legal_api/skills/doc_generator.py"""

import ast
import os
from datetime import datetime

class DocGenerator:
    """文档生成器"""
    
    def generate_api_doc(self, file_path: str) -> str:
        """生成 API 文档"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        doc = f"# API 文档 - {os.path.basename(file_path)}\n\n"
        doc += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n\n"
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                docstring = ast.get_docstring(node) or '无说明'
                args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                
                doc += f"## `{node.name}({', '.join(args)})`\n\n"
                doc += f"**说明**: {docstring[:200]}...\n\n"
                doc += f"**参数**:\n"
                for arg in args:
                    doc += f"- `{arg}`: \n"
                doc += "\n"
        
        return doc
    
    def generate_readme(self, project_dir: str) -> str:
        """生成 README"""
        readme = "# 项目说明\n\n"
        readme += f"**更新时间**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        readme += "## 项目结构\n\n"
        
        for root, dirs, files in os.walk(project_dir):
            level = root.replace(project_dir, '').count(os.sep)
            indent = ' ' * 2 * level
            readme += f"{indent}{os.path.basename(root)}/\n"
            sub_indent = ' ' * 2 * (level + 1)
            for file in files[:5]:  # 只显示前 5 个文件
                readme += f"{sub_indent}{file}\n"
        
        return readme
    
    def generate_changelog(self, git_log: str) -> str:
        """生成变更日志"""
        changelog = "# 变更日志\n\n"
        changelog += f"**生成时间**: {datetime.now().strftime('%Y-%m-%d')}\n\n"
        changelog += git_log[:2000]  # 限制长度
        
        return changelog


if __name__ == '__main__':
    import sys
    generator = DocGenerator()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        if file_path.endswith('.py'):
            doc = generator.generate_api_doc(file_path)
        else:
            doc = generator.generate_readme(file_path)
        print(doc)
```

---

## 性能优化技能 (performance-opt)

**负责人**: 铸基（架构师）

### 功能
1. 性能瓶颈分析
2. 数据库查询优化
3. 代码性能优化
4. 缓存策略建议

### 实现

```python
#!/usr/bin/env python3
"""性能优化器 - /home/admin/xinhai_legal_api/skills/performance_optimizer.py"""

import cProfile
import pstats
import io
from typing import Dict

class PerformanceOptimizer:
    """性能优化器"""
    
    def profile_function(self, func, *args, **kwargs) -> Dict:
        """分析函数性能"""
        profiler = cProfile.Profile()
        profiler.enable()
        
        result = func(*args, **kwargs)
        
        profiler.disable()
        
        # 获取统计
        stream = io.StringIO()
        stats = pstats.Stats(profiler, stream=stream)
        stats.sort_stats('cumulative')
        stats.print_stats(20)
        
        return {
            'result': result,
            'profile': stream.getvalue()
        }
    
    def analyze_slow_query(self, query: str) -> Dict:
        """分析慢查询"""
        analysis = {
            'query': query,
            'issues': [],
            'suggestions': []
        }
        
        query_upper = query.upper()
        
        if 'SELECT *' in query_upper:
            analysis['issues'].append('使用 SELECT * 而不是指定列')
            analysis['suggestions'].append('指定需要的列名')
        
        if 'WHERE' not in query_upper:
            analysis['issues'].append('缺少 WHERE 条件')
            analysis['suggestions'].append('添加 WHERE 条件限制结果集')
        
        if 'LIKE \'%' in query:
            analysis['issues'].append('使用前导通配符，无法使用索引')
            analysis['suggestions'].append('考虑使用全文索引')
        
        if 'ORDER BY' in query_upper and 'LIMIT' not in query_upper:
            analysis['issues'].append('ORDER BY 没有 LIMIT')
            analysis['suggestions'].append('添加 LIMIT 限制结果数')
        
        return analysis
    
    def get_optimization_tips(self, code: str) -> list:
        """获取优化建议"""
        tips = []
        
        if 'for line in open(' in code:
            tips.append('使用 with open() 而不是直接 open()')
        
        if '.append(' in code and 'list' not in code:
            tips.append('考虑使用列表推导式代替循环 append')
        
        if 'global ' in code:
            tips.append('减少 global 变量使用')
        
        return tips


if __name__ == '__main__':
    optimizer = PerformanceOptimizer()
    
    # 示例：分析慢查询
    query = "SELECT * FROM users WHERE name LIKE '%test%' ORDER BY created_at"
    analysis = optimizer.analyze_slow_query(query)
    
    print("🐌 慢查询分析")
    print("=" * 60)
    print(f"查询：{analysis['query'][:80]}...")
    print(f"\n问题:")
    for issue in analysis['issues']:
        print(f"  ❌ {issue}")
    print(f"\n建议:")
    for suggestion in analysis['suggestions']:
        print(f"  ✅ {suggestion}")
```

---

## 安全编码技能 (secure-coding)

**负责人**: 铁卫（安全官）

### 功能
1. 安全代码检查
2. 漏洞扫描
3. 安全编码建议
4. 安全测试生成

### 实现

```python
#!/usr/bin/env python3
"""安全编码检查器 - /home/admin/xinhai_legal_api/skills/secure_coding.py"""

import re
from typing import List, Dict

class SecureCodingChecker:
    """安全编码检查器"""
    
    # 安全问题模式
    SECURITY_PATTERNS = {
        'sql_injection': (r'execute\(.*%.*\)|execute\(.*\+.*\)', 'SQL 注入风险'),
        'command_injection': (r'os\.system\(.*%.*\)|subprocess\.call\(.*\+.*\)', '命令注入风险'),
        'path_traversal': (r'open\(.*\+.*\)|open\(.*%.*\)', '路径遍历风险'),
        'hardcoded_secret': (r'password\s*=\s*["\'][^"\']+["\']|api_key\s*=\s*["\'][^"\']+["\']', '硬编码密钥'),
        'weak_crypto': (r'MD5|SHA1|DES', '弱加密算法'),
        'eval_exec': (r'eval\(|exec\(', 'eval/exec 风险'),
        'pickle': (r'pickle\.loads?\(', 'pickle 反序列化风险'),
    }
    
    def check_file(self, file_path: str) -> List[Dict]:
        """检查文件安全问题"""
        issues = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            for pattern_name, (pattern, description) in self.SECURITY_PATTERNS.items():
                if re.search(pattern, line):
                    issues.append({
                        'type': pattern_name,
                        'line': line_num,
                        'description': description,
                        'content': line.strip()[:100],
                        'severity': self._get_severity(pattern_name)
                    })
        
        return issues
    
    def _get_severity(self, pattern_name: str) -> str:
        """获取严重程度"""
        high = ['sql_injection', 'command_injection', 'eval_exec', 'pickle']
        medium = ['path_traversal', 'hardcoded_secret']
        
        if pattern_name in high:
            return 'HIGH'
        elif pattern_name in medium:
            return 'MEDIUM'
        return 'LOW'
    
    def get_secure_alternatives(self, issue_type: str) -> str:
        """获取安全替代方案"""
        alternatives = {
            'sql_injection': '使用参数化查询：cursor.execute("SELECT * FROM t WHERE id = ?", (id,))',
            'command_injection': '使用 subprocess 并传入列表：subprocess.run(["ls", "-l"])',
            'path_traversal': '使用 os.path.join 并验证路径：os.path.abspath(path)',
            'hardcoded_secret': '使用环境变量：os.environ.get("API_KEY")',
            'weak_crypto': '使用 bcrypt 或 argon2：bcrypt.hashpw(password, bcrypt.gensalt())',
            'eval_exec': '使用 ast.literal_eval 代替 eval()',
            'pickle': '使用 json 代替 pickle 进行序列化',
        }
        return alternatives.get(issue_type, '请查阅安全编码规范')


if __name__ == '__main__':
    import sys
    
    checker = SecureCodingChecker()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        issues = checker.check_file(file_path)
        
        print(f"🔍 安全检查：{file_path}")
        print("=" * 60)
        
        if issues:
            print(f"发现 {len(issues)} 个安全问题:\n")
            for issue in issues[:10]:
                print(f"[{issue['severity']}] {issue['description']}")
                print(f"  行 {issue['line']}: {issue['content'][:60]}...")
                print(f"  建议：{checker.get_secure_alternatives(issue['type'])}\n")
        else:
            print("✅ 未发现安全问题")
```

---

## 使用指南

```bash
# 文档生成
python3 /home/admin/xinhai_legal_api/skills/doc_generator.py /home/admin/xinhai_legal_api/token_optimizer.py

# 性能优化
python3 /home/admin/xinhai_legal_api/skills/performance_optimizer.py

# 安全检查
python3 /home/admin/xinhai_legal_api/skills/secure_coding.py /home/admin/xinhai_legal_api/token_optimizer.py
```

---

**维护人**: 墨言 + 铸基 + 铁卫  
**最后更新**: 2026-05-19
