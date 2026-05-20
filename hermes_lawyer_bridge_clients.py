#!/usr/bin/env python3
"""客户管理 Bridge - 从 cases/entrust_orders 提取客户列表"""
import sys, json, sqlite3, os

DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def json_response(code=200, message='success', data=None):
    return json.dumps({'code': code, 'message': message, 'data': data}, ensure_ascii=False)

def clients_list(query_str):
    """获取律师的客户列表"""
    try:
        query = json.loads(query_str) if query_str else {}
    except:
        query = {}
    
    lawyer_id = query.get('lawyer_id') or query.get('user_id')
    if not lawyer_id:
        return json_response(400, '缺少 lawyer_id')
    
    db = get_db()
    cursor = db.cursor()
    
    # 从 lawyer_cases 提取当事人（opponent）
    cursor.execute('''
        SELECT DISTINCT opponent as name, '案件当事人' as source, 
               COUNT(*) as case_count, MAX(updated_at) as last_contact,
               GROUP_CONCAT(DISTINCT type) as case_types
        FROM lawyer_cases 
        WHERE lawyer_id = ? AND opponent IS NOT NULL AND opponent != ''
        GROUP BY opponent
        ORDER BY last_contact DESC
    ''', (lawyer_id,))
    opponent_rows = cursor.fetchall()
    
    # 从 entrust_orders 关联 users 表提取委托客户
    cursor.execute('''
        SELECT DISTINCT u.full_name as name, u.phone, '委托客户' as source,
               COUNT(*) as case_count, MAX(e.created_at) as last_contact,
               GROUP_CONCAT(DISTINCT e.service_type) as case_types
        FROM entrust_orders e
        JOIN users u ON e.user_id = u.id
        WHERE e.lawyer_id = ? AND (u.full_name IS NOT NULL AND u.full_name != '')
        GROUP BY u.id
        ORDER BY last_contact DESC
    ''', (lawyer_id,))
    client_rows = cursor.fetchall()
    
    # 从 lawyer_cases 查 user_id 关联的用户
    cursor.execute('''
        SELECT DISTINCT u.id, u.full_name as name, u.phone, '案件客户' as source,
               COUNT(*) as case_count, MAX(lc.updated_at) as last_contact,
               GROUP_CONCAT(DISTINCT lc.type) as case_types
        FROM lawyer_cases lc
        JOIN users u ON lc.user_id = u.id
        WHERE lc.lawyer_id = ? AND (u.full_name IS NOT NULL AND u.full_name != '')
        GROUP BY u.id
        ORDER BY last_contact DESC
    ''', (lawyer_id,))
    user_rows = cursor.fetchall()
    
    db.close()
    
    # 合并去重
    seen = set()
    items = []
    
    for row in opponent_rows:
        name = row['name']
        if name in seen: continue
        seen.add(name)
        items.append({
            'name': name,
            'phone': '',
            'source': '案件当事人',
            'case_count': row['case_count'],
            'case_types': row['case_types'] or '',
            'last_contact': row['last_contact'] or ''
        })
    
    for row in user_rows:
        name = row['name']
        if name in seen: continue
        seen.add(name)
        items.append({
            'name': name,
            'phone': row['phone'] or '',
            'source': '委托客户',
            'case_count': row['case_count'],
            'case_types': row['case_types'] or '',
            'last_contact': row['last_contact'] or ''
        })
    
    # 搜索过滤
    keyword = query.get('keyword', '').strip()
    if keyword:
        items = [i for i in items if keyword.lower() in i['name'].lower()]
    
    return json_response(data={'total': len(items), 'list': items})


if __name__ == '__main__':
    if len(sys.argv) < 3:
        print(json_response(400, '参数不足'))
        sys.exit(0)
    action = sys.argv[1]
    data_str = sys.argv[2]
    if action == 'clients_list':
        print(clients_list(data_str))
    else:
        print(json_response(400, f'未知操作: {action}'))
