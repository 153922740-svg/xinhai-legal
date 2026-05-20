"""
Phase 14: 智能推荐系统
- 用户个性化推荐（基于历史文书类型）
- 相似案例推荐（基于同类型文书）
- 热门法律文书推荐
"""

import sqlite3
import json
from datetime import datetime
from flask import Blueprint, jsonify, request

recommendation_bp = Blueprint("recommendation", __name__, url_prefix="/api/v1/recommend")

DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


@recommendation_bp.route("/user/<int:user_id>", methods=["POST"])
def recommend_for_user(user_id):
    """
    为用户推荐相关内容
    基于：用户最近的文书类型 + 热门文书
    """
    try:
        limit = request.args.get('limit', 10, type=int)
        db = get_db()
        
        # 1. 获取用户最近使用的文书类型
        recent_types = db.execute('''
            SELECT DISTINCT doc_type FROM documents 
            WHERE user_id = ? AND doc_type IS NOT NULL AND doc_type != ''
            ORDER BY created_at DESC LIMIT 5
        ''', (user_id,)).fetchall()
        
        user_types = [r['doc_type'] for r in recent_types]
        
        # 2. 基于用户类型推荐同类文书
        recommendations = []
        if user_types:
            placeholders = ','.join(['?'] * len(user_types))
            docs = db.execute(f'''
                SELECT id, doc_type, created_at, user_id 
                FROM documents 
                WHERE doc_type IN ({placeholders}) AND user_id != ?
                ORDER BY created_at DESC LIMIT ?
            ''', (*user_types, user_id, limit))
            
            for doc in docs:
                recommendations.append({
                    'type': 'document',
                    'id': doc['id'],
                    'sub_type': doc['doc_type'],
                    'reason': '基于您使用的同类文书',
                    'score': 0.9
                })
        
        # 3. 补充最新文书
        if len(recommendations) < limit:
            remaining = limit - len(recommendations)
            existing_ids = [r['id'] for r in recommendations] if recommendations else [0]
            placeholders = ','.join(['?'] * len(existing_ids))
            
            docs = db.execute(f'''
                SELECT id, doc_type, created_at
                FROM documents 
                WHERE id NOT IN ({placeholders})
                ORDER BY created_at DESC LIMIT ?
            ''', (*existing_ids, remaining))
            
            for doc in docs:
                recommendations.append({
                    'type': 'document',
                    'id': doc['id'],
                    'sub_type': doc['doc_type'],
                    'reason': '最新文书',
                    'score': 0.7
                })
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'user_id': user_id,
                'recommendations': recommendations
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'推荐失败：{str(e)}'}), 500


@recommendation_bp.route("/cases/<string:case_id>", methods=["GET"])
def similar_cases(case_id):
    """
    推荐相似案例/文书
    基于：同类型文书
    """
    try:
        limit = request.args.get('limit', 6, type=int)
        db = get_db()
        
        # 查找源文书的类型
        source = db.execute('''
            SELECT id, doc_type, created_at 
            FROM documents WHERE CAST(id AS TEXT) = ?
        ''', (case_id,)).fetchone()
        
        if not source:
            db.close()
            return jsonify({
                'code': 200, 
                'data': {'similar_cases': []}, 
                'message': '源文书不存在'
            })
        
        similar = []
        
        # 同类型推荐
        if source['doc_type']:
            docs = db.execute('''
                SELECT id, doc_type, created_at
                FROM documents 
                WHERE doc_type = ? AND id != ?
                ORDER BY created_at DESC LIMIT ?
            ''', (source['doc_type'], source['id'], limit))
            
            for doc in docs:
                similar.append({
                    'id': doc['id'],
                    'doc_type': doc['doc_type'],
                    'match_type': 'same_type',
                    'created_at': doc['created_at']
                })
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'source': {
                    'id': source['id'],
                    'doc_type': source['doc_type']
                },
                'similar_cases': similar
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@recommendation_bp.route("/hot", methods=["GET"])
def hot_documents():
    """获取最新文书列表"""
    try:
        limit = request.args.get('limit', 10, type=int)
        db = get_db()
        
        docs = db.execute('''
            SELECT id, doc_type, created_at
            FROM documents 
            WHERE doc_type IS NOT NULL AND doc_type != ''
            ORDER BY created_at DESC LIMIT ?
        ''', (limit,))
        
        hot_list = [{
            'id': doc['id'],
            'doc_type': doc['doc_type'],
            'created_at': doc['created_at']
        } for doc in docs]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'hot_documents': hot_list
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@recommendation_bp.route("/click", methods=["POST"])
def record_click():
    """记录推荐点击"""
    try:
        data = request.get_json() or {}
        user_id = data.get('user_id')
        target_id = data.get('target_id')
        target_type = data.get('target_type', 'document')
        
        if not all([user_id, target_id]):
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        db = get_db()
        db.execute('''
            UPDATE user_recommendations 
            SET is_clicked = 1 
            WHERE user_id = ? AND target_id = ? AND target_type = ?
        ''', (user_id, target_id, target_type))
        db.commit()
        db.close()
        
        return jsonify({'code': 200, 'message': '记录成功'})
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'记录失败：{str(e)}'}), 500
