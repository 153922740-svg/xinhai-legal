#!/usr/bin/env python3
"""
心海法律 AI - 敏感信息扫描脚本（铁卫）
用途：代码提交前扫描敏感信息，防止泄露

文件位置：/home/admin/xinhai_legal_api/scripts/pre_commit_secret_scan.py
"""

import os
import re
import sys
import json
from datetime import datetime
from typing import List, Dict, Tuple

# 敏感信息模式
PATTERNS = {
    'api_key': (r'(?:api[_-]?key|apikey|api[_-]?secret)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{20,})["\']?', 'API 密钥'),
    'password': (r'(?:password|passwd|pwd)\s*[=:]\s*["\']?([^\s"\']{8,})["\']?', '密码'),
    'secret': (r'(?:secret|secret[_-]?key)\s*[=:]\s*["\']?([a-zA-Z0-9_\-]{16,})["\']?', '密钥'),
    'token': (r'(?:token|access[_-]?token|auth[_-]?token)\s*[=:]\s*["\']?([a-zA-Z0-9_\-\.]{20,})["\']?', 'Token'),
    'private_key': (r'-----BEGIN (?:RSA |EC |DSA )?PRIVATE KEY-----', '私钥'),
    'alibaba_access_key': (r'LTAI[a-zA-Z0-9]{13,}', '阿里云 AccessKey'),
    'alibaba_secret': (r'[a-zA-Z0-9]{30}', '阿里云 Secret'),
    'wechat_appid': (r'wx[a-f0-9]{8}', '微信 AppID'),
    'wechat_mchid': (r'(?:mchid|mch_id)\s*[=:]\s*["\']?(\d{10})["\']?', '微信商户号'),
    'database_url': (r'(?:mysql|postgresql|sqlite)://[^\s]+', '数据库 URL'),
    'ssh_key': (r'ssh-(?:rsa|ed25519|dss)\s+[A-Za-z0-9+/=]{100,}', 'SSH 密钥'),
    'phone_number': (r'(?:phone|mobile|tel)\s*[=:]\s*["\']?(\+?86?1[3-9]\d{9})["\']?', '手机号'),
    'id_card': (r'[1-9]\d{5}(?:18|19|20)\d{2}(?:0[1-9]|1[0-2])(?:0[1-9]|[12]\d|3[01])\d{3}[\dXx]', '身份证号'),
    'credit_card': (r'\b(?:4[0-9]{12}(?:[0-9]{3})?|5[1-5][0-9]{14}|3[47][0-9]{13})\b', '信用卡号'),
}

# 排除目录
EXCLUDE_DIRS = [
    '__pycache__', '.git', 'node_modules', 'venv', '.venv',
    '.idea', '.vscode', 'dist', 'build', '.eggs', '*.egg-info'
]

# 排除文件
EXCLUDE_FILES = [
    '*.pyc', '*.pyo', '*.so', '*.dll', '*.exe',
    '*.tar.gz', '*.zip', '*.rar', '*.7z',
    '.gitignore', '.dockerignore', '*.lock'
]


class SecretScanner:
    """敏感信息扫描器"""
    
    def __init__(self, scan_dir: str = '/home/admin/xinhai_legal_api/'):
        self.scan_dir = scan_dir
        self.findings: List[Dict] = []
        self.scanned_files = 0
        self.total_lines = 0
    
    def scan_directory(self) -> List[Dict]:
        """扫描目录"""
        print(f"\n🔍 开始扫描：{self.scan_dir}")
        print("=" * 60)
        
        for root, dirs, files in os.walk(self.scan_dir):
            # 排除目录
            dirs[:] = [d for d in dirs if not self._is_excluded_dir(d)]
            
            for file in files:
                if self._is_excluded_file(file):
                    continue
                
                file_path = os.path.join(root, file)
                self._scan_file(file_path)
        
        return self.findings
    
    def _is_excluded_dir(self, dirname: str) -> bool:
        """检查是否排除目录"""
        return dirname in EXCLUDE_DIRS or dirname.endswith('.egg-info')
    
    def _is_excluded_file(self, filename: str) -> bool:
        """检查是否排除文件"""
        import fnmatch
        for pattern in EXCLUDE_FILES:
            if fnmatch.fnmatch(filename, pattern):
                return True
        return False
    
    def _scan_file(self, file_path: str):
        """扫描单个文件"""
        try:
            with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                lines = f.readlines()
            
            self.scanned_files += 1
            self.total_lines += len(lines)
            
            for line_num, line in enumerate(lines, 1):
                findings = self._scan_line(line, file_path, line_num)
                self.findings.extend(findings)
        
        except Exception as e:
            pass  # 跳过无法读取的文件
    
    def _scan_line(self, line: str, file_path: str, line_num: int) -> List[Dict]:
        """扫描单行"""
        findings = []
        
        for pattern_name, (pattern, description) in PATTERNS.items():
            matches = re.finditer(pattern, line, re.IGNORECASE)
            for match in matches:
                # 跳过注释中的匹配
                if '#' in line and line.index('#') < match.start():
                    continue
                
                # 跳过示例/测试数据
                if 'example' in line.lower() or 'test' in line.lower() or 'demo' in line.lower():
                    continue
                
                finding = {
                    'file': file_path,
                    'line': line_num,
                    'type': pattern_name,
                    'description': description,
                    'content': line.strip()[:100],  # 限制长度
                    'severity': self._get_severity(pattern_name)
                }
                findings.append(finding)
        
        return findings
    
    def _get_severity(self, pattern_name: str) -> str:
        """获取严重程度"""
        high_severity = ['api_key', 'password', 'secret', 'token', 'private_key', 
                         'alibaba_access_key', 'alibaba_secret', 'ssh_key']
        medium_severity = ['wechat_appid', 'wechat_mchid', 'database_url']
        
        if pattern_name in high_severity:
            return 'HIGH'
        elif pattern_name in medium_severity:
            return 'MEDIUM'
        return 'LOW'
    
    def get_report(self) -> Dict:
        """生成报告"""
        high_count = sum(1 for f in self.findings if f['severity'] == 'HIGH')
        medium_count = sum(1 for f in self.findings if f['severity'] == 'MEDIUM')
        low_count = sum(1 for f in self.findings if f['severity'] == 'LOW')
        
        return {
            'scan_time': datetime.now().isoformat(),
            'scan_dir': self.scan_dir,
            'scanned_files': self.scanned_files,
            'scanned_lines': self.total_lines,
            'total_findings': len(self.findings),
            'by_severity': {
                'HIGH': high_count,
                'MEDIUM': medium_count,
                'LOW': low_count
            },
            'findings': self.findings
        }
    
    def print_report(self):
        """打印报告"""
        report = self.get_report()
        
        print("\n" + "=" * 60)
        print("  敏感信息扫描报告")
        print("=" * 60)
        print(f"扫描时间：{report['scan_time']}")
        print(f"扫描目录：{report['scan_dir']}")
        print(f"扫描文件：{report['scanned_files']}")
        print(f"扫描行数：{report['scanned_lines']:,}")
        print(f"\n发现问题：{report['total_findings']} 个")
        print(f"  🔴 高危：{report['by_severity']['HIGH']}")
        print(f"  🟡 中危：{report['by_severity']['MEDIUM']}")
        print(f"  🟢 低危：{report['by_severity']['LOW']}")
        
        if self.findings:
            print("\n详细列表:")
            print("-" * 60)
            for i, f in enumerate(self.findings[:20], 1):  # 只显示前 20 个
                severity_icon = '🔴' if f['severity'] == 'HIGH' else '🟡' if f['severity'] == 'MEDIUM' else '🟢'
                print(f"{i}. {severity_icon} [{f['description']}]")
                print(f"   文件：{f['file']}:{f['line']}")
                print(f"   内容：{f['content'][:80]}...")
                print()
            
            if len(self.findings) > 20:
                print(f"... 还有 {len(self.findings) - 20} 个问题")
        
        print("=" * 60)
        
        return report


def main():
    """主函数"""
    scan_dir = sys.argv[1] if len(sys.argv) > 1 else '/home/admin/xinhai_legal_api/'
    output_file = sys.argv[2] if len(sys.argv) > 2 else None
    
    scanner = SecretScanner(scan_dir)
    scanner.scan_directory()
    report = scanner.print_report()
    
    # 输出到文件
    if output_file:
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report, f, ensure_ascii=False, indent=2)
        print(f"\n✅ 报告已保存到：{output_file}")
    
    # 返回状态码
    if report['by_severity']['HIGH'] > 0:
        print("\n❌ 发现高危敏感信息，请立即处理！")
        sys.exit(1)
    elif report['total_findings'] > 0:
        print("\n⚠️  发现敏感信息，请检查确认！")
        sys.exit(0)
    else:
        print("\n✅ 未发现敏感信息！")
        sys.exit(0)


if __name__ == '__main__':
    main()
