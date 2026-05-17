#!/usr/bin/env python3
"""
心海法律AI - 模型效果监控脚本
功能：
  1. 监控模型效果（响应质量、置信度、Token消耗）
  2. 记录用户满意度统计
  3. A/B测试分析
  4. 输出监控报告

使用方式：
  python3.11 model_monitoring.py [--days N] [--output FILE]

定期执行建议 (crontab):
  0 2 * * * /usr/bin/python3.11 /root/xinhai-legal/scripts/model_monitoring.py >> /var/log/model_monitoring.log 2>&1
"""

import sqlite3
import json
import os
import sys
import argparse
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from collections import defaultdict

# ============ 配置 ============
DB_PATH = '/root/xinhai-legal/data/xinhai_legal.db'
DEFAULT_DAYS = 7  # 默认分析最近7天

# ============ 数据库连接 ============
def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA journal_mode=WAL")
    return conn


# ============ 1. 模型效果监控 ============
def get_model_performance(conn, days: int) -> Dict:
    """获取模型效果指标"""
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 基本统计
    cursor = conn.execute("""
        SELECT 
            COUNT(*) as total_queries,
            AVG(confidence) as avg_confidence,
            AVG(tokens_used) as avg_tokens,
            SUM(tokens_used) as total_tokens,
            COUNT(CASE WHEN is_verified = 1 THEN 1 END) as verified_count,
            COUNT(CASE WHEN feedback_score IS NOT NULL THEN 1 END) as feedback_count
        FROM legal_qa
        WHERE created_at >= ?
    """, (since,))
    
    row = cursor.fetchone()
    total = row['total_queries'] if row else 0
    
    result = {
        'period_days': days,
        'since': since,
        'total_queries': total,
        'avg_confidence': round(row['avg_confidence'], 4) if row['avg_confidence'] else 0,
        'avg_tokens_per_query': round(row['avg_tokens'], 1) if row['avg_tokens'] else 0,
        'total_tokens_consumed': row['total_tokens'] or 0,
        'verified_answers': row['verified_count'] or 0,
        'feedback_received': row['feedback_count'] or 0,
    }
    
    if total > 0:
        result['verification_rate'] = round(result['verified_answers'] / total * 100, 2)
        result['feedback_rate'] = round(result['feedback_received'] / total * 100, 2)
    
    # 按模型分组统计
    cursor = conn.execute("""
        SELECT models_used, confidence, tokens_used, feedback_score
        FROM legal_qa
        WHERE created_at >= ?
    """, (since,))
    
    model_stats = defaultdict(lambda: {
        'count': 0, 'confidence_sum': 0, 'tokens_sum': 0,
        'feedback_scores': []
    })
    
    for row in cursor.fetchall():
        try:
            models = json.loads(row['models_used']) if row['models_used'] else ['unknown']
        except (json.JSONDecodeError, TypeError):
            models = ['unknown']
        
        for model in models:
            stats = model_stats[model]
            stats['count'] += 1
            stats['confidence_sum'] += row['confidence'] or 0
            stats['tokens_sum'] += row['tokens_used'] or 0
            if row['feedback_score'] is not None:
                stats['feedback_scores'].append(row['feedback_score'])
    
    result['by_model'] = {}
    for model, stats in model_stats.items():
        n = stats['count']
        avg_fb = round(sum(stats['feedback_scores']) / len(stats['feedback_scores']), 2) if stats['feedback_scores'] else None
        result['by_model'][model] = {
            'query_count': n,
            'avg_confidence': round(stats['confidence_sum'] / n, 4) if n else 0,
            'avg_tokens': round(stats['tokens_sum'] / n, 1) if n else 0,
            'avg_feedback_score': avg_fb,
            'feedback_count': len(stats['feedback_scores']),
        }
    
    # 按领域分组统计
    cursor = conn.execute("""
        SELECT domain, COUNT(*) as cnt, AVG(confidence) as avg_conf, AVG(tokens_used) as avg_tok
        FROM legal_qa
        WHERE created_at >= ?
        GROUP BY domain
        ORDER BY cnt DESC
    """, (since,))
    
    result['by_domain'] = {}
    for row in cursor.fetchall():
        domain = row['domain'] or '未分类'
        result['by_domain'][domain] = {
            'query_count': row['cnt'],
            'avg_confidence': round(row['avg_conf'], 4) if row['avg_conf'] else 0,
            'avg_tokens': round(row['avg_tok'], 1) if row['avg_tok'] else 0,
        }
    
    return result


# ============ 2. 用户满意度统计 ============
def get_satisfaction_stats(conn, days: int) -> Dict:
    """获取用户满意度统计"""
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 满意度分布
    cursor = conn.execute("""
        SELECT feedback_score, COUNT(*) as cnt
        FROM legal_qa
        WHERE created_at >= ? AND feedback_score IS NOT NULL
        GROUP BY feedback_score
        ORDER BY feedback_score
    """, (since,))
    
    score_distribution = {}
    total_feedback = 0
    weighted_sum = 0
    
    for row in cursor.fetchall():
        score = row['feedback_score']
        cnt = row['cnt']
        score_distribution[str(score)] = cnt
        total_feedback += cnt
        weighted_sum += score * cnt
    
    avg_score = round(weighted_sum / total_feedback, 2) if total_feedback else 0
    
    # 满意率 (score >= 4)
    satisfied = sum(cnt for score, cnt in score_distribution.items() if int(score) >= 4)
    satisfaction_rate = round(satisfied / total_feedback * 100, 2) if total_feedback else 0
    
    # 不满意原因
    cursor = conn.execute("""
        SELECT feedback_score, feedback_comment, domain
        FROM legal_qa
        WHERE created_at >= ? AND feedback_score IS NOT NULL AND feedback_score <= 2
        ORDER BY feedback_score
    """, (since,))
    
    negative_feedback = []
    for row in cursor.fetchall():
        negative_feedback.append({
            'score': row['feedback_score'],
            'comment': row['feedback_comment'],
            'domain': row['domain'],
        })
    
    # 每日满意度趋势
    cursor = conn.execute("""
        SELECT 
            DATE(created_at) as date,
            COUNT(*) as total,
            AVG(feedback_score) as avg_score,
            COUNT(CASE WHEN feedback_score >= 4 THEN 1 END) as satisfied
        FROM legal_qa
        WHERE created_at >= ? AND feedback_score IS NOT NULL
        GROUP BY DATE(created_at)
        ORDER BY date
    """, (since,))
    
    daily_trend = []
    for row in cursor.fetchall():
        total = row['total']
        daily_trend.append({
            'date': row['date'],
            'avg_score': round(row['avg_score'], 2) if row['avg_score'] else 0,
            'satisfaction_rate': round(row['satisfied'] / total * 100, 2) if total else 0,
            'feedback_count': total,
        })
    
    return {
        'total_feedback': total_feedback,
        'avg_score': avg_score,
        'satisfaction_rate': satisfaction_rate,
        'score_distribution': score_distribution,
        'negative_feedback_count': len(negative_feedback),
        'negative_feedback_sample': negative_feedback[:5],  # 最近5条
        'daily_trend': daily_trend,
    }


# ============ 3. A/B测试分析 ============
def get_ab_test_results(conn, days: int) -> Dict:
    """A/B测试分析 - 比较不同模型组合的效果"""
    since = (datetime.now() - timedelta(days=days)).strftime('%Y-%m-%d %H:%M:%S')
    
    # 获取所有问答记录，按模型组合分组
    cursor = conn.execute("""
        SELECT 
            models_used,
            models_votes,
            confidence,
            tokens_used,
            feedback_score,
            is_verified
        FROM legal_qa
        WHERE created_at >= ?
    """, (since,))
    
    model_groups = defaultdict(lambda: {
        'count': 0,
        'confidence_sum': 0,
        'tokens_sum': 0,
        'verified_count': 0,
        'feedback_scores': [],
        'votes_data': [],
    })
    
    for row in cursor.fetchall():
        # 模型组合作为分组键
        try:
            models = json.loads(row['models_used']) if row['models_used'] else []
        except (json.JSONDecodeError, TypeError):
            models = []
        
        group_key = '+'.join(sorted(models)) if models else 'single_model'
        stats = model_groups[group_key]
        stats['count'] += 1
        stats['confidence_sum'] += row['confidence'] or 0
        stats['tokens_sum'] += row['tokens_used'] or 0
        stats['verified_count'] += row['is_verified'] or 0
        if row['feedback_score'] is not None:
            stats['feedback_scores'].append(row['feedback_score'])
        
        # 收集投票数据
        try:
            votes = json.loads(row['models_votes']) if row['models_votes'] else {}
        except (json.JSONDecodeError, TypeError):
            votes = {}
        if votes:
            stats['votes_data'].append(votes)
    
    # 计算每组指标
    ab_results = {}
    for group_key, stats in model_groups.items():
        n = stats['count']
        avg_fb = round(sum(stats['feedback_scores']) / len(stats['feedback_scores']), 2) if stats['feedback_scores'] else None
        
        # 计算模型投票一致性
        vote_consistency = 0
        if stats['votes_data']:
            consistent_count = 0
            for votes in stats['votes_data']:
                if len(votes) > 0:
                    max_votes = max(votes.values())
                    total_votes = sum(votes.values())
                    if total_votes > 0 and max_votes == total_votes:
                        consistent_count += 1
            vote_consistency = round(consistent_count / len(stats['votes_data']) * 100, 2) if stats['votes_data'] else 0
        
        ab_results[group_key] = {
            'query_count': n,
            'avg_confidence': round(stats['confidence_sum'] / n, 4) if n else 0,
            'avg_tokens': round(stats['tokens_sum'] / n, 1) if n else 0,
            'verification_rate': round(stats['verified_count'] / n * 100, 2) if n else 0,
            'avg_feedback_score': avg_fb,
            'feedback_count': len(stats['feedback_scores']),
            'vote_consistency': vote_consistency,
        }
    
    # 找出最佳模型组合
    best_group = None
    best_score = -1
    for group_key, metrics in ab_results.items():
        if metrics['avg_feedback_score'] is not None and metrics['feedback_count'] >= 3:
            composite = (
                metrics['avg_feedback_score'] * 0.4 +
                (metrics['avg_confidence'] * 5) * 0.3 +  # normalize confidence to 5-point scale
                metrics['vote_consistency'] / 100 * 5 * 0.3  # normalize consistency
            )
            if composite > best_score:
                best_score = composite
                best_group = group_key
    
    return {
        'test_groups': ab_results,
        'best_model_combination': best_group,
        'best_composite_score': round(best_score, 2) if best_score > -1 else None,
        'recommendation': f"推荐使用 {best_group} 模型组合" if best_group else "数据不足，暂无推荐",
    }


# ============ 4. 整体健康度评估 ============
def get_health_check(conn) -> Dict:
    """系统健康度检查"""
    # 数据库大小
    db_size = os.path.getsize(DB_PATH) if os.path.exists(DB_PATH) else 0
    
    # 各表记录数
    tables = ['users', 'legal_qa', 'legal_cases', 'knowledge_base', 'token_transactions']
    table_counts = {}
    for table in tables:
        try:
            cursor = conn.execute(f"SELECT COUNT(*) FROM {table}")
            table_counts[table] = cursor.fetchone()[0]
        except sqlite3.OperationalError:
            table_counts[table] = -1
    
    # 最近活跃度 (24小时内)
    recent = (datetime.now() - timedelta(hours=24)).strftime('%Y-%m-%d %H:%M:%S')
    cursor = conn.execute("SELECT COUNT(*) FROM legal_qa WHERE created_at >= ?", (recent,))
    recent_queries = cursor.fetchone()[0]
    
    cursor = conn.execute("SELECT COUNT(*) FROM users WHERE created_at >= ?", (recent,))
    recent_users = cursor.fetchone()[0]
    
    # 异常检测
    alerts = []
    
    # 置信度异常低
    cursor = conn.execute("""
        SELECT COUNT(*) FROM legal_qa 
        WHERE confidence < 0.3 AND created_at >= ?
    """, (recent,))
    low_conf = cursor.fetchone()[0]
    if low_conf > 0:
        alerts.append(f"⚠️ 发现 {low_conf} 条低置信度回答(confidence<0.3)，需人工审核")
    
    # Token消耗异常
    cursor = conn.execute("""
        SELECT user_id, SUM(tokens_used) as total_tokens
        FROM legal_qa
        WHERE created_at >= ?
        GROUP BY user_id
        HAVING total_tokens > 100000
    """, (recent,))
    heavy_users = cursor.fetchall()
    for row in heavy_users:
        alerts.append(f"⚠️ 用户 {row['user_id']} 24小时内消耗 {row['total_tokens']} tokens")
    
    return {
        'timestamp': datetime.now().strftime('%Y-%m-%d %H:%M:%S'),
        'database_size_mb': round(db_size / 1024 / 1024, 2),
        'table_counts': table_counts,
        'last_24h_queries': recent_queries,
        'last_24h_new_users': recent_users,
        'alerts': alerts if alerts else ['✅ 系统运行正常，无异常'],
    }


# ============ 报告输出 ============
def generate_report(days: int, output_file: Optional[str] = None):
    """生成监控报告"""
    print("=" * 70)
    print(f"心海法律AI - 模型效果监控报告")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"分析周期: 最近 {days} 天")
    print("=" * 70)
    
    try:
        conn = get_db()
    except Exception as e:
        print(f"\n❌ 数据库连接失败: {e}")
        return
    
    # 1. 健康检查
    print("\n" + "─" * 50)
    print("📊 系统健康状态")
    print("─" * 50)
    health = get_health_check(conn)
    print(f"  数据库大小: {health['database_size_mb']} MB")
    print(f"  24小时查询数: {health['last_24h_queries']}")
    print(f"  24小时新增用户: {health['last_24h_new_users']}")
    print(f"  数据表记录数:")
    for table, count in health['table_counts'].items():
        status = "✅" if count >= 0 else "❌"
        print(f"    {status} {table}: {count}")
    print(f"  告警:")
    for alert in health['alerts']:
        print(f"    {alert}")
    
    # 2. 模型效果
    print("\n" + "─" * 50)
    print("🤖 模型效果分析")
    print("─" * 50)
    perf = get_model_performance(conn, days)
    print(f"  总查询数: {perf['total_queries']}")
    if perf['total_queries'] > 0:
        print(f"  平均置信度: {perf['avg_confidence']}")
        print(f"  平均Token消耗: {perf['avg_tokens_per_query']}")
        print(f"  总Token消耗: {perf['total_tokens_consumed']}")
        print(f"  验证率: {perf.get('verification_rate', 0)}%")
        print(f"  反馈率: {perf.get('feedback_rate', 0)}%")
        
        if perf['by_model']:
            print(f"\n  📈 各模型表现:")
            for model, stats in perf['by_model'].items():
                print(f"    [{model}]")
                print(f"      查询数: {stats['query_count']}, "
                      f"置信度: {stats['avg_confidence']}, "
                      f"Token: {stats['avg_tokens']}, "
                      f"满意度: {stats['avg_feedback_score'] or 'N/A'}")
        
        if perf['by_domain']:
            print(f"\n  📋 各领域分布:")
            for domain, stats in list(perf['by_domain'].items())[:10]:
                print(f"    {domain}: {stats['query_count']}次, "
                      f"置信度: {stats['avg_confidence']}")
    else:
        print("  📭 暂无查询数据")
    
    # 3. 用户满意度
    print("\n" + "─" * 50)
    print("😊 用户满意度统计")
    print("─" * 50)
    sat = get_satisfaction_stats(conn, days)
    print(f"  反馈总数: {sat['total_feedback']}")
    if sat['total_feedback'] > 0:
        print(f"  平均评分: {sat['avg_score']}/5")
        print(f"  满意率(≥4分): {sat['satisfaction_rate']}%")
        print(f"  评分分布:")
        for score, count in sorted(sat['score_distribution'].items()):
            bar = "█" * count
            print(f"    {score}分: {bar} ({count})")
        
        if sat['negative_feedback_sample']:
            print(f"\n  ❌ 差评样本(≤2分):")
            for fb in sat['negative_feedback_sample'][:3]:
                comment = fb['comment'] or '无评论'
                print(f"    评分:{fb['score']} 领域:{fb['domain'] or '未知'} 评论:{comment[:50]}")
        
        if sat['daily_trend']:
            print(f"\n  📊 每日满意度趋势:")
            for day in sat['daily_trend'][-7:]:  # 最近7天
                print(f"    {day['date']}: 评分{day['avg_score']}, 满意率{day['satisfaction_rate']}%")
    else:
        print("  📭 暂无满意度反馈数据")
    
    # 4. A/B测试
    print("\n" + "─" * 50)
    print("🧪 A/B测试分析")
    print("─" * 50)
    ab = get_ab_test_results(conn, days)
    if ab['test_groups']:
        for group, metrics in ab['test_groups'].items():
            print(f"  [{group}]")
            print(f"    查询数: {metrics['query_count']}, "
                  f"置信度: {metrics['avg_confidence']}, "
                  f"验证率: {metrics['verification_rate']}%, "
                  f"投票一致性: {metrics['vote_consistency']}%")
        print(f"\n  🏆 推荐: {ab['recommendation']}")
    else:
        print("  📭 暂无A/B测试数据（需要多模型交叉验证记录）")
    
    print("\n" + "=" * 70)
    print("报告结束")
    print("=" * 70)
    
    # 保存到文件
    if output_file:
        report_data = {
            'generated_at': datetime.now().isoformat(),
            'period_days': days,
            'health': health,
            'performance': perf,
            'satisfaction': sat,
            'ab_test': ab,
        }
        os.makedirs(os.path.dirname(output_file) if os.path.dirname(output_file) else '.', exist_ok=True)
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(report_data, f, ensure_ascii=False, indent=2)
        print(f"\n📄 报告已保存至: {output_file}")
    
    conn.close()
    
    # 记录本次监控执行日志
    log_dir = '/root/xinhai-legal/data'
    log_path = os.path.join(log_dir, 'monitoring_log.jsonl')
    try:
        log_entry = {
            'timestamp': datetime.now().isoformat(),
            'type': 'model_monitoring',
            'days': days,
            'total_queries': perf['total_queries'],
            'avg_confidence': perf['avg_confidence'],
            'satisfaction_rate': sat.get('satisfaction_rate', 0),
            'alerts_count': len([a for a in health['alerts'] if a.startswith('⚠️')]),
        }
        with open(log_path, 'a', encoding='utf-8') as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + '\n')
    except Exception:
        pass  # 日志写入失败不影响主流程


# ============ 主入口 ============
if __name__ == '__main__':
    parser = argparse.ArgumentParser(description='心海法律AI - 模型效果监控')
    parser.add_argument('--days', type=int, default=DEFAULT_DAYS, help='分析最近N天数据')
    parser.add_argument('--output', type=str, default=None, help='输出JSON报告文件路径')
    args = parser.parse_args()
    
    try:
        generate_report(args.days, args.output)
    except Exception as e:
        print(f"\n❌ 监控脚本执行出错: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
