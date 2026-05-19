# 心海法律 AI - 代码理解技能 (code-understanding)

**版本**: V1.0  
**创建日期**: 2026-05-19  
**负责人**: 求索（学习官）+ 灵指（编码官）  
**目标**: 提升代码理解准确率至≥80%

---

## 📋 技能概述

### 技能功能

1. **代码摘要生成** - 自动生成函数/类的摘要说明
2. **代码依赖分析** - 分析模块间的依赖关系
3. **代码复杂度评估** - 评估代码复杂度和可维护性
4. **代码意图理解** - 理解代码的业务意图
5. **相似代码检索** - 查找相似的代码片段

### 使用场景

- 新成员快速理解代码库
- 代码审查时理解代码意图
- 重构前分析代码依赖
- 查找相似代码避免重复造轮子

---

## 🛠️ 技能实现

### 1. 代码摘要生成

```python
#!/usr/bin/env python3
"""
代码摘要生成器
用途：自动生成函数/类的摘要说明
"""

import ast
import os
from typing import List, Dict

class CodeSummarizer:
    """代码摘要生成器"""
    
    def __init__(self):
        self.supported_extensions = ['.py']
    
    def summarize_file(self, file_path: str) -> Dict:
        """总结单个文件"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        summary = {
            'file': file_path,
            'classes': [],
            'functions': [],
            'imports': [],
            'lines': len(source.split('\n'))
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                summary['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': [n.name for n in node.body if isinstance(n, ast.FunctionDef)]
                })
            
            elif isinstance(node, ast.FunctionDef):
                # 获取文档字符串
                docstring = ast.get_docstring(node) or ''
                
                # 获取参数
                args = [arg.arg for arg in node.args.args if arg.arg != 'self']
                
                summary['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'args': args,
                    'docstring': docstring[:200],  # 限制长度
                    'docstring_summary': self._extract_summary(docstring)
                })
            
            elif isinstance(node, ast.Import):
                for alias in node.names:
                    summary['imports'].append(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                for alias in node.names:
                    summary['imports'].append(f"{node.module}.{alias.name}")
        
        return summary
    
    def _extract_summary(self, docstring: str) -> str:
        """从文档字符串提取摘要（第一句）"""
        if not docstring:
            return ''
        
        # 取第一句
        sentences = docstring.split('.')
        if sentences:
            return sentences[0].strip() + '.'
        return docstring[:100]
    
    def summarize_directory(self, directory: str) -> List[Dict]:
        """总结目录下所有文件"""
        summaries = []
        
        for root, dirs, files in os.walk(directory):
            for file in files:
                if any(file.endswith(ext) for ext in self.supported_extensions):
                    file_path = os.path.join(root, file)
                    summary = self.summarize_file(file_path)
                    summaries.append(summary)
        
        return summaries
    
    def generate_report(self, summaries: List[Dict]) -> str:
        """生成代码理解报告"""
        report = "# 代码理解报告\n\n"
        
        total_files = len(summaries)
        total_classes = sum(len(s['classes']) for s in summaries)
        total_functions = sum(len(s['functions']) for s in summaries)
        total_lines = sum(s['lines'] for s in summaries)
        
        report += f"## 统计概览\n\n"
        report += f"- 文件数：{total_files}\n"
        report += f"- 类数：{total_classes}\n"
        report += f"- 函数数：{total_functions}\n"
        report += f"- 总行数：{total_lines:,}\n\n"
        
        report += "## 文件详情\n\n"
        for summary in summaries:
            report += f"### {summary['file']}\n\n"
            report += f"- 行数：{summary['lines']}\n"
            report += f"- 导入：{len(summary['imports'])}\n"
            report += f"- 类：{len(summary['classes'])}\n"
            report += f"- 函数：{len(summary['functions'])}\n\n"
            
            if summary['classes']:
                report += "**类**:\n"
                for cls in summary['classes']:
                    report += f"- `{cls['name']}` ({len(cls['methods'])} 个方法)\n"
                report += "\n"
            
            if summary['functions']:
                report += "**主要函数**:\n"
                for func in summary['functions'][:10]:  # 只显示前 10 个
                    doc_summary = func['docstring_summary'] or '无文档'
                    report += f"- `{func['name']}({', '.join(func['args'])})` - {doc_summary}\n"
                report += "\n"
        
        return report


if __name__ == '__main__':
    import sys
    import json
    
    summarizer = CodeSummarizer()
    
    if len(sys.argv) < 2:
        print("用法：python3 code_summarizer.py [目录路径]")
        sys.exit(0)
    
    directory = sys.argv[1]
    
    print(f"📂 分析目录：{directory}")
    summaries = summarizer.summarize_directory(directory)
    
    print(f"\n✅ 分析完成：{len(summaries)} 个文件")
    
    # 生成报告
    report = summarizer.generate_report(summaries)
    print(report)
    
    # 保存 JSON
    output_file = "/home/admin/xinhai_legal_api/docs/code_understanding_report.json"
    with open(output_file, 'w', encoding='utf-8') as f:
        json.dump(summaries, f, ensure_ascii=False, indent=2)
    
    print(f"\n✅ 报告已保存到：{output_file}")

```

---

### 2. 代码依赖分析

```python
#!/usr/bin/env python3
"""
代码依赖分析器
用途：分析模块间的依赖关系
"""

import ast
import os
from typing import Dict, List, Set
from collections import defaultdict

class DependencyAnalyzer:
    """代码依赖分析器"""
    
    def __init__(self):
        self.dependencies = defaultdict(set)
    
    def analyze_file(self, file_path: str) -> Set[str]:
        """分析单个文件的依赖"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        tree = ast.parse(source)
        deps = set()
        
        for node in ast.walk(tree):
            if isinstance(node, ast.Import):
                for alias in node.names:
                    deps.add(alias.name)
            
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    deps.add(node.module)
        
        self.dependencies[file_path] = deps
        return deps
    
    def analyze_directory(self, directory: str) -> Dict[str, Set[str]]:
        """分析目录下所有文件的依赖"""
        for root, dirs, files in os.walk(directory):
            for file in files:
                if file.endswith('.py'):
                    file_path = os.path.join(root, file)
                    self.analyze_file(file_path)
        
        return dict(self.dependencies)
    
    def generate_dependency_graph(self) -> str:
        """生成依赖关系图（文本格式）"""
        graph = "# 代码依赖关系图\n\n"
        
        for file, deps in sorted(self.dependencies.items()):
            if deps:
                graph += f"### `{file}`\n\n"
                graph += "**依赖**:\n"
                for dep in sorted(deps):
                    graph += f"- `{dep}`\n"
                graph += "\n"
        
        return graph
    
    def find_circular_dependencies(self) -> List[List[str]]:
        """查找循环依赖"""
        # 简化实现：查找直接循环依赖 A->B->A
        circular = []
        
        for file1, deps1 in self.dependencies.items():
            for file2 in deps1:
                if file2 in self.dependencies:
                    deps2 = self.dependencies[file2]
                    if file1 in deps2:
                        circular.append([file1, file2])
        
        return circular


if __name__ == '__main__':
    import sys
    
    analyzer = DependencyAnalyzer()
    
    if len(sys.argv) < 2:
        print("用法：python3 dependency_analyzer.py [目录路径]")
        sys.exit(0)
    
    directory = sys.argv[1]
    
    print(f"📂 分析目录：{directory}")
    analyzer.analyze_directory(directory)
    
    # 生成依赖图
    graph = analyzer.generate_dependency_graph()
    print(graph)
    
    # 查找循环依赖
    circular = analyzer.find_circular_dependencies()
    if circular:
        print("\n⚠️  发现循环依赖:")
        for cycle in circular:
            print(f"  {' -> '.join(cycle)}")
    else:
        print("\n✅ 未发现循环依赖")

```

---

### 3. 代码复杂度评估

```python
#!/usr/bin/env python3
"""
代码复杂度评估器
用途：评估代码复杂度和可维护性
"""

import ast
import os
from typing import Dict, List

class ComplexityAnalyzer:
    """代码复杂度评估器"""
    
    def __init__(self):
        self.results = []
    
    def analyze_file(self, file_path: str) -> Dict:
        """分析单个文件的复杂度"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        metrics = {
            'file': file_path,
            'lines': len(source.split('\n')),
            'functions': [],
            'classes': [],
            'avg_complexity': 0,
            'max_complexity': 0,
            'maintainability_index': 0
        }
        
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                complexity = self._calculate_complexity(node)
                metrics['functions'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'complexity': complexity,
                    'lines': node.end_lineno - node.lineno + 1 if hasattr(node, 'end_lineno') else 0
                })
                
                metrics['max_complexity'] = max(metrics['max_complexity'], complexity)
            
            elif isinstance(node, ast.ClassDef):
                method_count = sum(1 for n in node.body if isinstance(n, ast.FunctionDef))
                metrics['classes'].append({
                    'name': node.name,
                    'line': node.lineno,
                    'methods': method_count
                })
        
        # 计算平均复杂度
        if metrics['functions']:
            metrics['avg_complexity'] = sum(f['complexity'] for f in metrics['functions']) / len(metrics['functions'])
        
        # 计算可维护性指数（简化版）
        metrics['maintainability_index'] = self._calculate_maintainability(metrics)
        
        self.results.append(metrics)
        return metrics
    
    def _calculate_complexity(self, node: ast.FunctionDef) -> int:
        """计算函数复杂度（圈复杂度）"""
        complexity = 1  # 基础复杂度
        
        for child in ast.walk(node):
            # 条件语句增加复杂度
            if isinstance(child, (ast.If, ast.While, ast.For, ast.ExceptHandler)):
                complexity += 1
            
            # 逻辑运算符增加复杂度
            elif isinstance(child, ast.BoolOp):
                complexity += len(child.values) - 1
            
            # 三元表达式增加复杂度
            elif isinstance(child, ast.IfExp):
                complexity += 1
        
        return complexity
    
    def _calculate_maintainability(self, metrics: Dict) -> float:
        """计算可维护性指数（0-100）"""
        # 简化公式
        avg_complexity = metrics['avg_complexity']
        avg_lines = sum(f['lines'] for f in metrics['functions']) / max(len(metrics['functions']), 1)
        
        # 复杂度越低，行数越少，可维护性越高
        score = 100 - (avg_complexity * 5) - (avg_lines * 0.5)
        return max(0, min(100, score))  # 限制在 0-100 之间
    
    def generate_report(self) -> str:
        """生成复杂度报告"""
        report = "# 代码复杂度报告\n\n"
        
        total_files = len(self.results)
        avg_complexity = sum(r['avg_complexity'] for r in self.results) / max(total_files, 1)
        avg_maintainability = sum(r['maintainability_index'] for r in self.results) / max(total_files, 1)
        
        report += "## 总体指标\n\n"
        report += f"- 文件数：{total_files}\n"
        report += f"- 平均复杂度：{avg_complexity:.2f}\n"
        report += f"- 平均可维护性指数：{avg_maintainability:.2f}/100\n\n"
        
        report += "## 高复杂度函数（需要重构）\n\n"
        
        high_complexity_functions = []
        for metrics in self.results:
            for func in metrics['functions']:
                if func['complexity'] > 10:  # 复杂度>10 认为需要重构
                    high_complexity_functions.append({
                        'file': metrics['file'],
                        'function': func['name'],
                        'complexity': func['complexity'],
                        'lines': func['lines']
                    })
        
        if high_complexity_functions:
            # 按复杂度排序
            high_complexity_functions.sort(key=lambda x: x['complexity'], reverse=True)
            
            for item in high_complexity_functions[:20]:  # 显示前 20 个
                report += f"- `{item['file']}:{item['function']}` "
                report += f"(复杂度：{item['complexity']}, 行数：{item['lines']})\n"
        else:
            report += "✅ 未发现高复杂度函数\n"
        
        return report


if __name__ == '__main__':
    import sys
    
    analyzer = ComplexityAnalyzer()
    
    if len(sys.argv) < 2:
        print("用法：python3 complexity_analyzer.py [目录路径]")
        sys.exit(0)
    
    directory = sys.argv[1]
    
    print(f"📂 分析目录：{directory}")
    
    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.py'):
                file_path = os.path.join(root, file)
                analyzer.analyze_file(file_path)
    
    # 生成报告
    report = analyzer.generate_report()
    print(report)

```

---

## 📊 技能使用指南

### 使用示例

```bash
# 1. 代码摘要生成
python3 /home/admin/xinhai_legal_api/skills/code_summarizer.py /home/admin/xinhai_legal_api/

# 2. 代码依赖分析
python3 /home/admin/xinhai_legal_api/skills/dependency_analyzer.py /home/admin/xinhai_legal_api/

# 3. 代码复杂度评估
python3 /home/admin/xinhai_legal_api/skills/complexity_analyzer.py /home/admin/xinhai_legal_api/
```

### 输出示例

```
# 代码理解报告

## 统计概览
- 文件数：57
- 类数：15
- 函数数：254
- 总行数：17,188

## 文件详情
### /home/admin/xinhai_legal_api/token_optimizer.py
- 行数：350
- 导入：8
- 类：1
- 函数：12

**类**:
- `TokenOptimizer` (12 个方法)

**主要函数**:
- `get_cached_response(question)` - 获取缓存的回答
- `cache_response(question, response, tokens_used)` - 缓存回答
- `record_token_usage(endpoint, tokens_in, tokens_out)` - 记录 Token 使用
...
```

---

## 📈 效果评估

### 评估指标

| 指标 | 目标值 | 测量方式 |
|------|--------|---------|
| 摘要准确率 | ≥80% | 人工评审 |
| 依赖分析准确率 | ≥90% | 对比手动分析 |
| 复杂度评估准确率 | ≥85% | 与人工评估对比 |
| 响应时间 | <5 秒 | 性能测试 |

### 测试用例

```python
def test_code_summarizer():
    """测试代码摘要生成"""
    summarizer = CodeSummarizer()
    summary = summarizer.summarize_file('/home/admin/xinhai_legal_api/token_optimizer.py')
    
    assert len(summary['classes']) > 0
    assert len(summary['functions']) > 0
    assert summary['lines'] > 0

def test_dependency_analyzer():
    """测试代码依赖分析"""
    analyzer = DependencyAnalyzer()
    deps = analyzer.analyze_file('/home/admin/xinhai_legal_api/token_optimizer.py')
    
    assert 'sqlite3' in deps or 'sqlite3' in str(deps)

def test_complexity_analyzer():
    """测试代码复杂度评估"""
    analyzer = ComplexityAnalyzer()
    metrics = analyzer.analyze_file('/home/admin/xinhai_legal_api/token_optimizer.py')
    
    assert metrics['avg_complexity'] > 0
    assert 0 <= metrics['maintainability_index'] <= 100
```

---

**维护人**: 求索（学习官）+ 灵指（编码官）  
**最后更新**: 2026-05-19  
**下次评审**: 2026-06-19（月度评审）
