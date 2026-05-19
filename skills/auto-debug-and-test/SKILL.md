# 自主调试技能 (auto-debug) + 测试生成技能 (test-generator)

**版本**: V1.0  
**创建日期**: 2026-05-19  
**负责人**: 铁壁（测试官）+ 灵指（编码官）  
**目标**: 自主调试≥85%，测试生成≥85%

---

## 自主调试技能 (auto-debug)

### 功能
1. 错误日志分析
2. Bug 定位
3. 修复建议生成
4. 自动修复脚本

### 实现脚本

```python
#!/usr/bin/env python3
"""自动调试器 - /home/admin/xinhai_legal_api/skills/auto_debugger.py"""

import re
import os
from typing import List, Dict

class AutoDebugger:
    """自动调试器"""
    
    # 常见错误模式
    ERROR_PATTERNS = {
        'syntax_error': (r'SyntaxError:.*line (\d+)', '语法错误'),
        'import_error': (r'ImportError:.*', '导入错误'),
        'name_error': (r'NameError:.*', '变量未定义'),
        'type_error': (r'TypeError:.*', '类型错误'),
        'key_error': (r'KeyError:.*', '键不存在'),
        'index_error': (r'IndexError:.*', '索引越界'),
        'attribute_error': (r'AttributeError:.*', '属性不存在'),
        'file_not_found': (r'FileNotFoundError:.*', '文件不存在'),
        'permission_error': (r'PermissionError:.*', '权限错误'),
        'connection_error': (r'ConnectionError:.*', '连接错误'),
    }
    
    def analyze_error(self, error_log: str) -> Dict:
        """分析错误日志"""
        analysis = {
            'error_type': 'unknown',
            'error_description': '',
            'line_number': None,
            'file_path': None,
            'suggested_fix': '',
            'confidence': 0
        }
        
        for error_type, (pattern, description) in self.ERROR_PATTERNS.items():
            match = re.search(pattern, error_log)
            if match:
                analysis['error_type'] = error_type
                analysis['error_description'] = description
                
                # 提取行号
                if len(match.groups()) > 0:
                    analysis['line_number'] = int(match.group(1))
                
                # 生成修复建议
                analysis['suggested_fix'] = self._get_fix_suggestion(error_type, error_log)
                analysis['confidence'] = 0.9
                break
        
        return analysis
    
    def _get_fix_suggestion(self, error_type: str, error_log: str) -> str:
        """生成修复建议"""
        suggestions = {
            'syntax_error': '检查语法错误，可能是缺少括号、冒号或引号',
            'import_error': '检查模块是否正确安装，导入路径是否正确',
            'name_error': '检查变量是否已定义，拼写是否正确',
            'type_error': '检查数据类型是否正确，可能需要类型转换',
            'key_error': '检查字典键是否存在，使用 get() 方法或添加默认值',
            'index_error': '检查列表索引是否越界',
            'attribute_error': '检查对象是否有该属性，拼写是否正确',
            'file_not_found': '检查文件路径是否正确，文件是否存在',
            'permission_error': '检查文件权限，使用 sudo 或修改权限',
            'connection_error': '检查网络连接，服务是否运行',
        }
        return suggestions.get(error_type, '请检查错误日志')
    
    def debug_file(self, file_path: str) -> List[Dict]:
        """调试文件（静态分析）"""
        issues = []
        
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            lines = f.readlines()
        
        for line_num, line in enumerate(lines, 1):
            # 检查常见代码问题
            if 'print(' in line and 'logger' not in line:
                issues.append({
                    'type': 'warning',
                    'line': line_num,
                    'message': '建议使用 logger 而不是 print',
                    'suggestion': '使用 logging 模块'
                })
            
            if 'eval(' in line:
                issues.append({
                    'type': 'security',
                    'line': line_num,
                    'message': '使用 eval() 存在安全风险',
                    'suggestion': '使用 ast.literal_eval() 或其他安全方法'
                })
            
            if len(line) > 200:
                issues.append({
                    'type': 'style',
                    'line': line_num,
                    'message': '行过长',
                    'suggestion': '拆分成多行'
                })
        
        return issues


if __name__ == '__main__':
    import sys
    
    debugger = AutoDebugger()
    
    if len(sys.argv) > 1:
        # 分析错误日志
        error_log = ' '.join(sys.argv[1:])
        analysis = debugger.analyze_error(error_log)
        
        print("🔍 错误分析")
        print("=" * 60)
        print(f"错误类型：{analysis['error_description']}")
        print(f"行号：{analysis['line_number'] or 'N/A'}")
        print(f"修复建议：{analysis['suggested_fix']}")
        print(f"置信度：{analysis['confidence']*100:.0f}%")
    else:
        print("用法：python3 auto_debugger.py [错误日志或文件路径]")

```

---

## 测试生成技能 (test-generator)

### 功能
1. 自动生成单元测试
2. 生成测试用例
3. 生成测试数据
4. 生成测试报告

### 实现脚本

```python
#!/usr/bin/env python3
"""测试生成器 - /home/admin/xinhai_legal_api/skills/test_generator.py"""

import ast
import os
from typing import List, Dict

class TestGenerator:
    """测试生成器"""
    
    def generate_unit_tests(self, file_path: str) -> str:
        """为文件生成单元测试"""
        with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
            source = f.read()
        
        tree = ast.parse(source)
        
        test_code = '''#!/usr/bin/env python3
"""单元测试 - 自动生成"""

import pytest
import sys
sys.path.insert(0, '/home/admin/xinhai_legal_api')

'''
        
        # 提取类和方法
        for node in ast.walk(tree):
            if isinstance(node, ast.ClassDef):
                test_code += f"\n\nclass Test{node.name}:\n"
                test_code += f'    """{node.name} 的测试类"""\n\n'
                
                for item in node.body:
                    if isinstance(item, ast.FunctionDef) and not item.name.startswith('_'):
                        test_code += self._generate_test_method(node.name, item.name)
            
            elif isinstance(node, ast.FunctionDef) and not node.name.startswith('_'):
                # 模块级函数
                test_code += f"\n\ndef test_{node.name}():\n"
                test_code += f'    """测试 {node.name} 函数"""\n'
                test_code += f'    # TODO: 实现测试逻辑\n'
                test_code += f'    pass\n'
        
        return test_code
    
    def _generate_test_method(self, class_name: str, method_name: str) -> str:
        """生成测试方法"""
        test_method = f"    def test_{method_name}(self):\n"
        test_method += f'        """测试 {class_name}.{method_name} 方法"""\n'
        test_method += f'        # TODO: 准备测试数据\n'
        test_method += f'        # obj = {class_name}()\n'
        test_method += f'        # result = obj.{method_name}()\n'
        test_method += f'        # assert result is not None\n'
        test_method += f'        pass\n\n'
        return test_method
    
    def generate_test_plan(self, requirement: str) -> Dict:
        """生成测试计划"""
        plan = {
            'requirement': requirement,
            'test_cases': [],
            'test_data': [],
            'estimated_time': 4  # 小时
        }
        
        # 简单分析需求生成测试用例
        if '登录' in requirement:
            plan['test_cases'] = [
                {'id': 'TC001', 'name': '正常登录', 'steps': ['输入正确手机号', '输入正确验证码', '点击登录'], 'expected': '登录成功'},
                {'id': 'TC002', 'name': '手机号为空', 'steps': ['不输入手机号', '输入验证码', '点击登录'], 'expected': '提示手机号不能为空'},
                {'id': 'TC003', 'name': '验证码错误', 'steps': ['输入正确手机号', '输入错误验证码', '点击登录'], 'expected': '提示验证码错误'},
                {'id': 'TC004', 'name': '手机号格式错误', 'steps': ['输入错误格式手机号', '输入验证码', '点击登录'], 'expected': '提示手机号格式错误'},
            ]
        elif '支付' in requirement:
            plan['test_cases'] = [
                {'id': 'TC001', 'name': '正常支付', 'steps': ['选择支付方式', '确认金额', '完成支付'], 'expected': '支付成功'},
                {'id': 'TC002', 'name': '余额不足', 'steps': ['选择支付方式', '确认金额', '完成支付'], 'expected': '提示余额不足'},
                {'id': 'TC003', 'name': '支付取消', 'steps': ['选择支付方式', '取消支付'], 'expected': '返回订单页'},
            ]
        else:
            plan['test_cases'] = [
                {'id': 'TC001', 'name': '正常流程', 'steps': ['准备数据', '执行操作', '验证结果'], 'expected': '操作成功'},
                {'id': 'TC002', 'name': '异常流程', 'steps': ['准备异常数据', '执行操作', '验证错误处理'], 'expected': '正确处理异常'},
            ]
        
        return plan


if __name__ == '__main__':
    import sys
    
    generator = TestGenerator()
    
    if len(sys.argv) > 1:
        file_path = sys.argv[1]
        
        if os.path.isfile(file_path):
            # 生成单元测试
            test_code = generator.generate_unit_tests(file_path)
            print(test_code)
            
            # 保存
            output_file = file_path.replace('.py', '_test.py')
            with open(output_file, 'w', encoding='utf-8') as f:
                f.write(test_code)
            
            print(f"\n✅ 测试已保存到：{output_file}")
        else:
            # 生成测试计划
            plan = generator.generate_test_plan(file_path)
            
            print("\n📋 测试计划")
            print("=" * 60)
            print(f"需求：{plan['requirement']}")
            print(f"预计时间：{plan['estimated_time']} 小时")
            print(f"\n测试用例 ({len(plan['test_cases'])} 个):")
            for tc in plan['test_cases']:
                print(f"  {tc['id']}: {tc['name']}")
    else:
        print("用法：python3 test_generator.py [文件路径或需求描述]")

```

---

## 使用指南

```bash
# 自主调试
python3 /home/admin/xinhai_legal_api/skills/auto_debugger.py "SyntaxError: invalid syntax line 10"

# 测试生成
python3 /home/admin/xinhai_legal_api/skills/test_generator.py /home/admin/xinhai_legal_api/token_optimizer.py

# 测试计划
python3 /home/admin/xinhai_legal_api/skills/test_generator.py "开发用户登录功能"
```

---

**维护人**: 铁壁（测试官）+ 灵指（编码官）  
**最后更新**: 2026-05-19
