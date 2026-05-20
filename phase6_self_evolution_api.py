"""
Phase 6: 自进化能力 API
- 用户反馈收集（点赞/点踩）
- Badcase 自动标记
- 模型优化机制
"""

import os
import sqlite3
from datetime import datetime
from flask import Blueprint, request, jsonify

phase6_bp = Blueprint('phase6', __name__)

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

# ============== 反馈收集 ==============

@phase6_bp.route('/api/v1/feedback/submit', methods=['POST'])
def submit_feedback():
    """
    提交用户反馈
    参数：message_id, rating (1-5), comment, user_id
    """
    try:
        data = request.get_json()
        
        if not data.get('message_id'):
            return jsonify({'code': 400, 'message': '缺少 message_id'}), 400
        
        if not data.get('rating'):
            return jsonify({'code': 400, 'message': '缺少评分 rating'}), 400
        
        rating = int(data.get('rating'))
        if rating < 1 or rating > 5:
            return jsonify({'code': 400, 'message': '评分必须在 1-5 之间'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO feedbacks (message_id, user_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('message_id'),
            data.get('user_id', 'anonymous'),
            rating,
            data.get('comment', ''),
            datetime.now().isoformat()
        ))
        
        db.commit()
        feedback_id = cursor.lastrowid
        db.close()
        
        # 如果是低分反馈（1-2 星），自动标记为 Badcase
        if rating <= 2:
            mark_as_badcase(data.get('message_id'), data.get('comment', ''))
        
        return jsonify({
            'code': 200,
            'message': '反馈提交成功',
            'data': {'feedback_id': feedback_id}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'反馈提交失败：{str(e)}'}), 500


@phase6_bp.route('/api/v1/feedback/quick', methods=['POST'])
def quick_feedback():
    """
    快速反馈（点赞/点踩）
    参数：message_id, type (like/dislike), user_id
    """
    try:
        data = request.get_json()
        
        if not data.get('message_id'):
            return jsonify({'code': 400, 'message': '缺少 message_id'}), 400
        
        feedback_type = data.get('type')
        if feedback_type not in ['like', 'dislike']:
            return jsonify({'code': 400, 'message': 'type 必须是 like 或 dislike'}), 400
        
        rating = 5 if feedback_type == 'like' else 1
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO feedbacks (message_id, user_id, rating, comment, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('message_id'),
            data.get('user_id', 'anonymous'),
            rating,
            '' if feedback_type == 'like' else '用户点踩',
            datetime.now().isoformat()
        ))
        
        db.commit()
        feedback_id = cursor.lastrowid
        db.close()
        
        # 点踩自动标记为 Badcase
        if feedback_type == 'dislike':
            mark_as_badcase(data.get('message_id'), '用户点踩')
        
        return jsonify({
            'code': 200,
            'message': '反馈成功',
            'data': {'feedback_id': feedback_id}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'反馈失败：{str(e)}'}), 500


def mark_as_badcase(message_id, reason):
    """
    将低分回答标记为 Badcase
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 查询消息内容
        cursor.execute('SELECT session_id, content FROM chat_messages WHERE id = ?', (message_id,))
        row = cursor.fetchone()
        
        if row:
            session_id, content = row['session_id'], row['content']
            
            # 插入 badcases 表
            cursor.execute('''
                INSERT INTO badcases (message_id, session_id, content, reason, status, created_at)
                VALUES (?, ?, ?, ?, 'pending', ?)
            ''', (message_id, session_id, content, reason, datetime.now().isoformat()))
            
            db.commit()
        
        db.close()
        
    except Exception as e:
        print(f"标记 Badcase 失败：{e}")


# ============== Badcase 管理 ==============

@phase6_bp.route('/api/v1/badcases/list', methods=['GET'])
def list_badcases():
    """
    获取 Badcase 列表
    参数：status (pending/reviewed/fixed), page, limit
    """
    try:
        status = request.args.get('status', 'pending')
        page = int(request.args.get('page', 1))
        limit = int(request.args.get('limit', 20))
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT b.*, u.username
            FROM badcases b
            LEFT JOIN users u ON b.user_id = u.id
            WHERE b.status = ?
            ORDER BY b.created_at DESC
            LIMIT ? OFFSET ?
        ''', (status, limit, (page-1)*limit))
        
        badcases = [dict(row) for row in cursor.fetchall()]
        
        # 获取总数
        cursor.execute('SELECT COUNT(*) as count FROM badcases WHERE status = ?', (status,))
        total = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total': total,
                'page': page,
                'limit': limit,
                'items': badcases
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase6_bp.route('/api/v1/badcases/review', methods=['POST'])
def review_badcase():
    """
    审核 Badcase
    参数：badcase_id, reviewer_id, review_comment, action (keep/ignore)
    """
    try:
        data = request.get_json()
        
        if not data.get('badcase_id'):
            return jsonify({'code': 400, 'message': '缺少 badcase_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE badcases
            SET status = 'reviewed',
                reviewer_id = ?,
                review_comment = ?,
                reviewed_at = ?
            WHERE id = ?
        ''', (
            data.get('reviewer_id'),
            data.get('review_comment', ''),
            datetime.now().isoformat(),
            data.get('badcase_id')
        ))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '审核完成'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'审核失败：{str(e)}'}), 500


@phase6_bp.route('/api/v1/badcases/fix', methods=['POST'])
def fix_badcase():
    """
    标记 Badcase 已修复
    参数：badcase_id, fix_description, model_version
    """
    try:
        data = request.get_json()
        
        if not data.get('badcase_id'):
            return jsonify({'code': 400, 'message': '缺少 badcase_id'}), 400
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            UPDATE badcases
            SET status = 'fixed',
                fix_description = ?,
                model_version = ?,
                fixed_at = ?
            WHERE id = ?
        ''', (
            data.get('fix_description', ''),
            data.get('model_version', ''),
            datetime.now().isoformat(),
            data.get('badcase_id')
        ))
        
        db.commit()
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '已标记为修复'
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'操作失败：{str(e)}'}), 500


# ============== 模型迭代 ==============

@phase6_bp.route('/api/v1/model/iterations', methods=['GET'])
def get_model_iterations():
    """
    获取模型迭代历史
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            SELECT * FROM model_iterations
            ORDER BY created_at DESC
        ''')
        
        iterations = [dict(row) for row in cursor.fetchall()]
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'iterations': iterations}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase6_bp.route('/api/v1/model/iterate', methods=['POST'])
def create_model_iteration():
    """
    创建新的模型迭代记录
    参数：version, description, training_data_count, metrics
    """
    try:
        data = request.get_json()
        
        db = get_db()
        cursor = db.cursor()
        
        cursor.execute('''
            INSERT INTO model_iterations (version, description, training_data_count, metrics, created_at)
            VALUES (?, ?, ?, ?, ?)
        ''', (
            data.get('version', 'v1.0'),
            data.get('description', ''),
            data.get('training_data_count', 0),
            data.get('metrics', '{}'),
            datetime.now().isoformat()
        ))
        
        db.commit()
        iteration_id = cursor.lastrowid
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '模型迭代记录创建成功',
            'data': {'iteration_id': iteration_id}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'创建失败：{str(e)}'}), 500


# ============== 自动学习循环 ==============

@phase6_bp.route('/api/v1/auto-analysis', methods=['POST'])
def auto_analysis():
    """
    自动分析待处理的 Badcase，按问题类型分组，生成今日分析报告
    触发方式：手动调用，或由 cron 定时触发
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 1. 统计待处理 Badcase 数量
        cursor.execute('SELECT COUNT(*) as count FROM badcases WHERE status = ?', ('pending',))
        pending_count = cursor.fetchone()['count']
        
        # 2. 按问题原因分组
        cursor.execute('''
            SELECT reason, COUNT(*) as count 
            FROM badcases 
            WHERE status = 'pending' 
            GROUP BY reason 
            ORDER BY count DESC
        ''')
        reason_stats = [dict(row) for row in cursor.fetchall()]
        
        # 3. 今日新增
        cursor.execute('''
            SELECT COUNT(*) as count FROM badcases 
            WHERE DATE(created_at) = DATE('now')
        ''')
        today_new = cursor.fetchone()['count']
        
        # 4. 7 天趋势
        cursor.execute('''
            SELECT DATE(created_at) as day, COUNT(*) as count, 
                   SUM(CASE WHEN status = 'fixed' THEN 1 ELSE 0 END) as fixed_count
            FROM badcases 
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY day
        ''')
        trend = [dict(row) for row in cursor.fetchall()]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': '分析完成',
            'data': {
                'pending_count': pending_count,
                'today_new': today_new,
                'by_reason': reason_stats,
                'trend_7d': trend,
                'analyzed_at': datetime.now().isoformat()
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'分析失败：{str(e)}'}), 500


@phase6_bp.route('/api/v1/feedback/trend', methods=['GET'])
def feedback_trend():
    """获取反馈趋势数据（7天）"""
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 反馈趋势
        cursor.execute('''
            SELECT DATE(created_at) as day, 
                   COUNT(*) as total,
                   AVG(rating) as avg_rating,
                   SUM(CASE WHEN rating <= 2 THEN 1 ELSE 0 END) as negative_count
            FROM feedbacks 
            WHERE created_at >= DATE('now', '-7 days')
            GROUP BY DATE(created_at)
            ORDER BY day
        ''')
        trend = [dict(row) for row in cursor.fetchall()]
        
        # 总概览
        cursor.execute('SELECT COUNT(*) as total, AVG(rating) as avg FROM feedbacks')
        overview = dict(cursor.fetchone())
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'overview': overview,
                'trend_7d': trend
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500

@phase6_bp.route('/api/v1/feedback/stats', methods=['GET'])
def get_feedback_stats():
    """
    获取反馈统计
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 总反馈数
        cursor.execute('SELECT COUNT(*) as count FROM feedbacks')
        total_feedbacks = cursor.fetchone()['count']
        
        # 平均评分
        cursor.execute('SELECT AVG(rating) as avg_rating FROM feedbacks')
        avg_rating = cursor.fetchone()['avg_rating'] or 0
        
        # 各评分分布
        cursor.execute('''
            SELECT rating, COUNT(*) as count
            FROM feedbacks
            GROUP BY rating
            ORDER BY rating
        ''')
        rating_distribution = [dict(row) for row in cursor.fetchall()]
        
        # Badcase 统计
        cursor.execute('SELECT COUNT(*) as count FROM badcases WHERE status = ?', ('pending',))
        pending_badcases = cursor.fetchone()['count']
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total_feedbacks': total_feedbacks,
                'average_rating': round(avg_rating, 2),
                'rating_distribution': rating_distribution,
                'pending_badcases': pending_badcases
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase6_tables():
    """
    初始化 Phase 6 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 反馈表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS feedbacks (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            user_id TEXT,
            rating INTEGER NOT NULL,
            comment TEXT DEFAULT '',
            created_at TEXT NOT NULL
        )
    ''')
    
    # Badcase 表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS badcases (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            message_id TEXT NOT NULL,
            session_id TEXT,
            user_id TEXT,
            content TEXT,
            reason TEXT,
            status TEXT DEFAULT 'pending',
            reviewer_id TEXT,
            review_comment TEXT,
            reviewed_at TEXT,
            fix_description TEXT,
            model_version TEXT,
            fixed_at TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    # 模型迭代记录表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS model_iterations (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            version TEXT NOT NULL,
            description TEXT,
            training_data_count INTEGER DEFAULT 0,
            metrics TEXT DEFAULT '{}',
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 6 数据库表初始化完成")


if __name__ == '__main__':
    init_phase6_tables()
    print("Phase 6 自进化能力 API 模块就绪")
