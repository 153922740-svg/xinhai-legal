#!/usr/bin/env python3
"""
心海法律 AI - 法律法规数据导入工具
从国家法律法规数据库(flk.npc.gov.cn)获取法律法规数据并导入知识库

用法：
  python3 import_legal_data.py                    # 交互式导入
  python3 import_legal_data.py --list              # 列出可导入的法律
  python3 import_legal_data.py --import-all        # 导入所有核心法律
  python3 import_legal_data.py --search 民法典     # 搜索法律
"""

import os
import sys
import json
import re
import time
import hashlib
import sqlite3
import urllib.request
import urllib.parse
import argparse

DB_PATH = '/home/admin/xinhai_legal_api/data/legal_kb.db'
FLAW_API = 'https://flk.npc.gov.cn/api'

# ========== 核心法律法规清单（首批100部） ==========
CORE_LAWS = [
    # 宪法及宪法相关法
    "中华人民共和国宪法", "中华人民共和国立法法", "中华人民共和国全国人民代表大会和地方各级人民代表大会选举法",
    "中华人民共和国全国人民代表大会和地方各级人民代表大会代表法", "中华人民共和国国籍法",
    "中华人民共和国国旗法", "中华人民共和国国徽法", "中华人民共和国国歌法",
    "中华人民共和国集会游行示威法", "中华人民共和国反分裂国家法",
    # 基本法律
    "中华人民共和国民法典", "中华人民共和国刑法", "中华人民共和国民事诉讼法",
    "中华人民共和国刑事诉讼法", "中华人民共和国行政诉讼法", "中华人民共和国行政处罚法",
    "中华人民共和国行政复议法", "中华人民共和国行政许可法", "中华人民共和国行政强制法",
    "中华人民共和国国家赔偿法", "中华人民共和国公司法", "中华人民共和国合伙企业法",
    "中华人民共和国个人独资企业法", "中华人民共和国企业破产法", "中华人民共和国劳动法",
    "中华人民共和国劳动合同法", "中华人民共和国社会保险法", "中华人民共和国仲裁法",
    "中华人民共和国律师法", "中华人民共和国公证法",
    # 重要普通法律
    "中华人民共和国食品安全法", "中华人民共和国药品管理法", "中华人民共和国产品质量法",
    "中华人民共和国消费者权益保护法", "中华人民共和国反不正当竞争法", "中华人民共和国反垄断法",
    "中华人民共和国商标法", "中华人民共和国专利法", "中华人民共和国著作权法",
    "中华人民共和国网络安全法", "中华人民共和国数据安全法", "中华人民共和国个人信息保护法",
    "中华人民共和国道路交通安全法", "中华人民共和国治安管理处罚法",
    "中华人民共和国未成年人保护法", "中华人民共和国妇女权益保障法",
    "中华人民共和国老年人权益保障法", "中华人民共和国城市房地产管理法",
    "中华人民共和国建筑法", "中华人民共和国招标投标法", "中华人民共和国农村土地承包法",
    "中华人民共和国土地管理法", "中华人民共和国环境保护法", "中华人民共和国保险法",
    "中华人民共和国证券法", "中华人民共和国信托法", "中华人民共和国票据法",
    "中华人民共和国海商法", "中华人民共和国商业银行法", "中华人民共和国银行业监督管理法",
    "中华人民共和国税收征收管理法", "中华人民共和国预算法", "中华人民共和国审计法",
    "中华人民共和国政府采购法", "中华人民共和国慈善法", "中华人民共和国红十字会法",
    "中华人民共和国献血法", "中华人民共和国母婴保健法", "中华人民共和国传染病防治法",
    "中华人民共和国职业病防治法", "中华人民共和国突发事件应对法",
    # 经济法
    "中华人民共和国会计法", "中华人民共和国统计法", "中华人民共和国价格法",
    "中华人民共和国拍卖法", "中华人民共和国电子签名法", "中华人民共和国电子商务法",
    "中华人民共和国广告法", "中华人民共和国乡村振兴促进法",
    # 社会法
    "中华人民共和国工会法", "中华人民共和国残疾人保障法", "中华人民共和国公益事业捐赠法",
    "中华人民共和国劳动法", "中华人民共和国劳动合同法", "中华人民共和国就业促进法",
    "中华人民共和国工伤保险条例",
    # 程序法相关
    "中华人民共和国人民调解法", "中华人民共和国劳动争议调解仲裁法",
    "中华人民共和国农村土地承包经营纠纷调解仲裁法",
]


class LegalDataImporter:
    def __init__(self, db_path=DB_PATH):
        self.db_path = db_path
        self.session = None

    def _get_conn(self):
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        return conn

    def search_npc(self, keyword, page=1, size=20):
        """搜索国家法律法规数据库"""
        url = f"{FLAW_API}/?page={page}&size={size}&title={urllib.parse.quote(keyword)}&searchType=title&sort=remain"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                data = json.loads(resp.read().decode('utf-8'))
                return data
        except Exception as e:
            print(f"  [错误] 搜索失败: {e}")
            return None

    def get_law_detail(self, law_id):
        """获取法律详情"""
        # 国家法律法规数据库的详情页
        url = f"{FLAW_API}/detail?id={law_id}"
        req = urllib.request.Request(url)
        req.add_header('User-Agent', 'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36')
        try:
            with urllib.request.urlopen(req, timeout=15) as resp:
                return json.loads(resp.read().decode('utf-8'))
        except Exception as e:
            print(f"  [错误] 获取详情失败: {e}")
            return None

    def parse_articles(self, full_text):
        """解析法律全文为条文列表"""
        articles = []
        if not full_text:
            return articles

        # 按行分割
        lines = full_text.split('\n')

        current_chapter = ''
        current_section = ''
        current_part = ''

        # 匹配章
        chapter_pattern = re.compile(r'^第[一二三四五六七八九十百]+章\s+(.*)')
        # 匹配节
        section_pattern = re.compile(r'^第[一二三四五六七八九十百]+节\s+(.*)')
        # 匹配编
        part_pattern = re.compile(r'^第[一二三四五六七八九十百]+编\s+(.*)')
        # 匹配第X条
        article_pattern = re.compile(r'^第([一二三四五六七八九十百千零〇0-9]+)条\s*(.*)')

        for line in lines:
            line = line.strip()
            if not line:
                continue

            # 编
            m = part_pattern.match(line)
            if m:
                current_part = m.group(1).strip()
                continue

            # 章
            m = chapter_pattern.match(line)
            if m:
                current_chapter = m.group(1).strip()
                continue

            # 节
            m = section_pattern.match(line)
            if m:
                current_section = m.group(1).strip()
                continue

            # 第X条
            m = article_pattern.match(line)
            if m:
                article_no_text = m.group(1)
                content = m.group(2).strip() if m.group(2) else ''

                # 中文数字转阿拉伯数字
                article_no_num = self._chinese_to_arabic(article_no_text)

                # 继续收集后续内容（同一法条可能跨多行）
                article_no_formatted = f"第{article_no_text}条"

                articles.append({
                    'part': current_part,
                    'chapter': current_chapter,
                    'section': current_section,
                    'article_no': article_no_formatted,
                    'article_no_num': article_no_num,
                    'content': content,
                    'paragraph_no': 1
                })

        return articles

    def _chinese_to_arabic(self, chinese):
        """中文数字转阿拉伯数字"""
        mapping = {
            '零': 0, '一': 1, '二': 2, '三': 3, '四': 4,
            '五': 5, '六': 6, '七': 7, '八': 8, '九': 9,
            '十': 10, '百': 100, '千': 1000, '〇': 0,
            '0': 0, '1': 1, '2': 2, '3': 3, '4': 4,
            '5': 5, '6': 6, '7': 7, '8': 8, '9': 9
        }

        # 纯数字
        if chinese.isdigit():
            return int(chinese)

        result = 0
        temp = 0
        for char in chinese:
            if char in mapping:
                num = mapping[char]
                if num >= 10:
                    if temp == 0:
                        temp = 1
                    result += temp * num
                    temp = 0
                else:
                    temp = num
        result += temp
        return result if result > 0 else 0

    def import_law(self, law_title, auto_search=True):
        """导入一部法律"""
        print(f"\n{'='*60}")
        print(f"  导入: {law_title}")
        print(f"{'='*60}")

        # 搜索
        if auto_search:
            print(f"  [搜索] 正在国家法律法规数据库搜索...")
            result = self.search_npc(law_title)
            if not result or not result.get('data'):
                print(f"  [失败] 未在数据库中搜索到'{law_title}'")
                return False

            records = result.get('data', {}).get('records', [])
            if not records:
                print(f"  [失败] 未找到匹配记录")
                return False

            # 找第一条有效记录
            target = None
            for r in records:
                if r.get('title') and law_title in r.get('title', ''):
                    # 优先选"有效"状态
                    if r.get('status') == '有效' or r.get('status') == 'effective':
                        target = r
                        break
                    if target is None:
                        target = r

            if not target:
                target = records[0]

            print(f"  [找到] {target.get('title', '')}")
            print(f"         发布机关: {target.get('authority', '')}")
            print(f"         发布日期: {target.get('publishDate', '')}")
            print(f"         状态: {target.get('status', '')}")

            # 获取详情
            law_id = target.get('id', '')
            if law_id:
                detail = self.get_law_detail(law_id)
                if detail:
                    full_text = detail.get('fullText', '') or detail.get('content', '')
                else:
                    full_text = ''
            else:
                full_text = ''
        else:
            # 手动输入数据
            print(f"  请输入{law_title}的全文（输入END结束）：")
            lines = []
            while True:
                line = input()
                if line == 'END':
                    break
                lines.append(line)
            full_text = '\n'.join(lines)
            target = {'title': law_title, 'authority': '手动录入', 'authorityLevel': 'law',
                       'publishDate': '', 'status': 'effective'}

        # 解析条文
        articles = self.parse_articles(full_text)

        if not articles:
            print(f"  [警告] 未解析出条文，尝试直接全文存储")
            articles = [{
                'part': '', 'chapter': '', 'section': '',
                'article_no': '全文', 'article_no_num': 0,
                'content': full_text[:5000] if full_text else law_title,
                'paragraph_no': 1
            }]

        print(f"  [解析] 共解析出 {len(articles)} 条条文")

        # 导入数据库
        conn = self._get_conn()
        try:
            # 计算checksum
            law_data_str = json.dumps({
                'title': target.get('title', law_title),
                'articles_count': len(articles)
            }, ensure_ascii=False)
            checksum = hashlib.md5(law_data_str.encode()).hexdigest()

            # 分类自动识别
            category = self._auto_category(law_title)

            # 插入法律主表
            cur = conn.execute("""
                INSERT INTO legal_laws (title, short_title, authority, authority_level,
                    publish_doc_no, publish_date, effective_date, status, category, tags,
                    article_count, full_text, source, checksum)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """, (
                target.get('title', law_title),
                self._short_title(target.get('title', law_title)),
                target.get('authority', '全国人民代表大会'),
                target.get('authorityLevel', 'law'),
                target.get('docNo', ''),
                target.get('publishDate', ''),
                target.get('effectiveDate', ''),
                'effective' if target.get('status', '有效') in ('有效', 'effective') else 'amended',
                category,
                f"{category}",
                len(articles),
                full_text[:50000] if full_text else '',
                'flk.npc.gov.cn',
                checksum
            ))
            law_id = cur.lastrowid

            # 插入条文
            for art in articles:
                conn.execute("""
                    INSERT INTO legal_articles (law_id, part, chapter, section,
                        article_no, article_no_num, paragraph_no, content, keywords)
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
                """, (
                    law_id, art.get('part', ''), art.get('chapter', ''), art.get('section', ''),
                    art.get('article_no', ''), art.get('article_no_num', 0),
                    art.get('paragraph_no', 1), art.get('content', ''),
                    ''
                ))

            conn.commit()
            print(f"  ✅ 导入成功！law_id={law_id}, 条文数={len(articles)}")
            return True

        except Exception as e:
            conn.rollback()
            print(f"  ❌ 导入失败: {e}")
            return False
        finally:
            conn.close()

    def _short_title(self, title):
        """提取简称"""
        title = title.replace('中华人民共和国', '').replace('中华人民共和国', '')
        return title.strip()

    def _auto_category(self, title):
        """自动分类"""
        categories = {
            '宪法': '宪法',
            '民法典': '民法', '刑法': '刑法', '民事诉讼法': '程序法', '刑事诉讼法': '程序法',
            '公司法': '商法', '合伙': '商法', '破产': '商法', '商标': '知识产权',
            '专利': '知识产权', '著作': '知识产权',
            '劳动': '劳动法', '劳动合同': '劳动法', '社会保险': '劳动法',
            '合同': '民法', '物权': '民法', '担保': '民法', '侵权': '民法',
            '婚姻': '民法', '继承': '民法', '收养': '民法',
            '行政': '行政法', '处罚': '行政法', '许可': '行政法', '强制': '行政法',
            '食品': '经济法', '药品': '经济法', '消费': '经济法',
            '安全': '刑法' if '安全' not in title else '行政法',
            '网络': '经济法', '数据': '经济法', '个人信息': '经济法',
            '交通': '行政法', '治安': '行政法',
            '未成年人': '社会法', '妇女': '社会法', '老年人': '社会法', '残疾': '社会法',
            '环境': '经济法', '保险': '商法', '证券': '商法', '银行': '商法',
        }
        for key, cat in categories.items():
            if key in title:
                return cat
        return '其他'

    def list_imported(self):
        """列出已导入的法律"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, title, category, article_count, status, publish_date
            FROM legal_laws ORDER BY id
        """).fetchall()
        conn.close()
        return [dict(r) for r in rows]

    def search_imported(self, keyword):
        """搜索已导入的法律"""
        conn = self._get_conn()
        rows = conn.execute("""
            SELECT id, title, category, article_count, status
            FROM legal_laws WHERE title LIKE ? ORDER BY id
        """, [f'%{keyword}%']).fetchall()
        conn.close()
        return [dict(r) for r in rows]


def main():
    parser = argparse.ArgumentParser(description='心海法律AI - 法律法规数据导入工具')
    parser.add_argument('--list', action='store_true', help='列出已导入的法律')
    parser.add_argument('--search', type=str, help='搜索法律')
    parser.add_argument('--import-all', action='store_true', help='导入所有核心法律')
    parser.add_argument('--import-one', type=str, help='导入指定法律')
    parser.add_argument('--interactive', action='store_true', help='交互式导入')
    args = parser.parse_args()

    importer = LegalDataImporter()

    if args.list:
        laws = importer.list_imported()
        print(f"\n已导入 {len(laws)} 部法律:")
        print("-" * 80)
        for law in laws:
            print(f"  [{law['id']}] {law['title']} ({law['category']}) - {law['article_count']}条 - {law['status']}")

    elif args.search:
        keyword = args.search
        print(f"\n搜索本地库: {keyword}")
        results = importer.search_imported(keyword)
        if results:
            for r in results:
                print(f"  [{r['id']}] {r['title']} ({r['category']}) - {r['article_count']}条")
        else:
            print("  本地库中未找到，尝试在线搜索...")
            results = importer.search_npc(keyword)
            if results and results.get('data', {}).get('records'):
                for r in results['data']['records'][:10]:
                    print(f"  {r.get('title', '')} - {r.get('authority', '')} - {r.get('status', '')}")
            else:
                print("  未找到")

    elif args.import_one:
        importer.import_law(args.import_one)

    elif args.import_all:
        total = len(CORE_LAWS)
        success = 0
        fail = 0
        for i, law_title in enumerate(CORE_LAWS, 1):
            print(f"\n[{i}/{total}] ", end='')
            try:
                if importer.import_law(law_title):
                    success += 1
                else:
                    fail += 1
            except KeyboardInterrupt:
                print("\n\n用户中断导入")
                break
            except Exception as e:
                print(f"  [异常] {e}")
                fail += 1
            # 国家法律法规数据库有限流，不要太快
            time.sleep(1)

        print(f"\n{'='*60}")
        print(f"  导入完成：成功 {success} 部，失败 {fail} 部")
        print(f"{'='*60}")

    elif args.interactive or len(sys.argv) == 1:
        print("心海法律AI - 法律法规数据导入工具")
        print("=" * 50)
        while True:
            print("\n命令: list | search <关键词> | import <法律名> | import-all | exit")
            cmd = input("> ").strip()
            if cmd == 'exit':
                break
            elif cmd == 'list':
                laws = importer.list_imported()
                print(f"\n已导入 {len(laws)} 部法律:")
                for law in laws:
                    print(f"  [{law['id']}] {law['title']} ({law['category']}) - {law['article_count']}条")
            elif cmd.startswith('search '):
                kw = cmd[7:]
                results = importer.search_imported(kw)
                if results:
                    for r in results:
                        print(f"  [{r['id']}] {r['title']} - {r['article_count']}条")
                else:
                    print("  未找到")
            elif cmd.startswith('import '):
                name = cmd[7:]
                importer.import_law(name)
            elif cmd == 'import-all':
                total = len(CORE_LAWS)
                for i, law_title in enumerate(CORE_LAWS, 1):
                    print(f"\n[{i}/{total}]")
                    importer.import_law(law_title)
                    time.sleep(1)
            else:
                print("  未知命令")

    else:
        parser.print_help()


if __name__ == '__main__':
    main()
