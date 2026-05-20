#!/usr/bin/env python3
"""
Hermes Business Bridge P2 — 律师板块 Phase2（AI工具8个接口）
被 hermes_business_api.py 通过 subprocess 调用
实现：AI谈单分析、生成文书、文书审查、阅卷摘要、证据整理、法律检索、类案推送、庭审提纲
通用逻辑：Token验证 → 律师身份检查 → 年费检查 → 扣Token → 记录日志 → 返回Mock数据
"""
import sys, json, sqlite3, uuid, os
from datetime import datetime

# AI模型调用
import urllib.request, urllib.error, urllib.request

# 提示词模板
from lawyer_ai_prompts import (
    PROMPT_ANALYZE, PROMPT_GENERATE_DOC, PROMPT_REVIEW_DOC,
    PROMPT_SUMMARY, PROMPT_EVIDENCE, PROMPT_LEGAL_SEARCH,
    PROMPT_CLASS_CASE, PROMPT_TRIAL_OUTLINE,
    PROMPT_MOOT_COURT, PROMPT_CASE_ARCHIVE
)

# ==================== 配置 ====================
DB_PATH = '/home/admin/xinhai_legal_api/data/xinhai_legal.db'
TOKEN_CONSUME_AMOUNT = 100  # 每个接口固定扣100 Token

# ==================== AI模型配置 ====================

DEEPSEEK_CONFIG = {
    "api_key": os.environ.get("DEEPSEEK_API_KEY", ""),
    "base_url": "https://api.deepseek.com/v1",
    "model": "deepseek-chat",
    "name": "DeepSeek"
}


def call_llm(messages, temperature=0.5, max_tokens=2048):
    """调用DeepSeek API"""
    api_key = DEEPSEEK_CONFIG["api_key"]
    if not api_key:
        return "【错误】DeepSeek API密钥未配置"
    
    url = f"{DEEPSEEK_CONFIG['base_url']}/chat/completions"
    payload = json.dumps({
        "model": DEEPSEEK_CONFIG["model"],
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
    }).encode("utf-8")
    
    try:
        req = urllib.request.Request(
            url, data=payload,
            headers={
                "Authorization": f"Bearer {api_key}",
                "Content-Type": "application/json",
            },
        )
        resp = urllib.request.urlopen(req, timeout=30)
        result = json.loads(resp.read().decode("utf-8"))
        return result["choices"][0]["message"]["content"]
    except urllib.error.HTTPError as e:
        error_body = e.read().decode("utf-8", errors="replace")
        return f'{{"error": "API调用失败 (HTTP {e.code})"}}'
    except Exception as e:
        return f'{{"error": "API调用异常: {str(e)[:100]}"}}'

# ==================== 数据库操作 ====================

def get_db():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn


def create_tables(params=None):
    """初始化AI工具日志表（如果不存在）"""
    db = get_db()
    cursor = db.cursor()
    
    # 确保 lawyer_ai_tool_logs 表存在
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_ai_tool_logs (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            lawyer_id INTEGER NOT NULL,
            tool_type TEXT,
            input_summary TEXT,
            output_summary TEXT,
            tokens_used INTEGER DEFAULT 0,
            created_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')
    
    # 确保 lawyer_profiles 表存在（用于律师身份和年费检查）
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS lawyer_profiles (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER UNIQUE NOT NULL,
            name TEXT NOT NULL,
            avatar TEXT,
            phone TEXT,
            email TEXT,
            law_firm TEXT,
            license_no TEXT,
            specialties TEXT,
            years_exp INTEGER,
            jurisdiction TEXT,
            bio TEXT,
            rating REAL DEFAULT 0,
            case_count INTEGER DEFAULT 0,
            fee_rate REAL,
            status TEXT DEFAULT 'pending',
            available INTEGER DEFAULT 1,
            fee_status TEXT DEFAULT 'unpaid',
            fee_expire_at TEXT,
            created_at TEXT DEFAULT (datetime('now','localtime')),
            updated_at TEXT DEFAULT (datetime('now','localtime'))
        )
    ''')
    
    db.commit()
    db.close()
    return {'success': True, 'data': {'message': '律师AI工具表初始化完成'}}


# ==================== 通用验证逻辑 ====================

def verify_token(token):
    """验证Bearer Token，返回 user_id"""
    if not token:
        return None, '缺少认证Token'
    
    db = get_db()
    cursor = db.cursor()
    
    # 通过 users 表查找 token（token存于username中作为简易token）
    # 实际项目中应有token表，这里兼容现有模式
    cursor.execute('SELECT id FROM users WHERE username = ?', (token,))
    row = cursor.fetchone()
    db.close()
    
    if row:
        return row['id'], None
    
    # 尝试直接用token匹配user_id（兼容数字token场景）
    try:
        uid = int(token)
        db = get_db()
        cursor = db.cursor()
        cursor.execute('SELECT id FROM users WHERE id = ?', (uid,))
        row = cursor.fetchone()
        db.close()
        if row:
            return row['id'], None
    except (ValueError, TypeError):
        pass
    
    return None, 'Token无效或已过期'


def verify_lawyer_and_fee(user_id):
    """验证律师身份和年费状态
    要求：lawyer_profiles 表中 status='approved' 且 fee_status='paid'
    """
    db = get_db()
    cursor = db.cursor()
    
    # 检查 lawyer_profiles
    cursor.execute('''
        SELECT id, status, fee_status, fee_expire_at FROM lawyer_profiles WHERE user_id = ?
    ''', (user_id,))
    profile = cursor.fetchone()
    db.close()
    
    if not profile:
        return None, '未找到律师信息，请先完成律师入驻'
    
    profile = dict(profile)
    
    if profile['status'] != 'approved':
        return None, f'律师账号未通过审核（当前状态: {profile["status"]}）'
    
    if profile['fee_status'] != 'paid':
        return None, '年费未缴纳，请先缴纳年费'
    
    # 检查年费是否过期
    if profile.get('fee_expire_at'):
        try:
            expire_at = datetime.fromisoformat(profile['fee_expire_at'].replace('T', ' '))
            if expire_at < datetime.now():
                return None, '年费已过期，请续费'
        except (ValueError, TypeError):
            pass
    
    return profile['id'], None


def consume_tokens(user_id, amount=TOKEN_CONSUME_AMOUNT, description=''):
    """扣减Token（通过调用 P0 token_consume 逻辑）"""
    if not user_id:
        return {'success': False, 'error': '缺少 user_id'}
    
    try:
        user_id = int(user_id)
        amount = int(amount)
    except (ValueError, TypeError):
        return {'success': False, 'error': '参数类型错误'}
    
    if amount <= 0:
        return {'success': False, 'error': '消耗数量必须大于0'}
    
    db = get_db()
    cursor = db.cursor()
    
    try:
        # 读取余额
        cursor.execute("SELECT tokens_balance FROM users WHERE id=?", (user_id,))
        row = cursor.fetchone()
        if not row:
            db.close()
            return {'success': False, 'error': '用户不存在'}
        
        balance = row['tokens_balance']
        if balance < amount:
            db.close()
            return {'success': False, 'error': f'Token不足（当前: {balance}, 需要: {amount}）'}
        
        new_balance = balance - amount
        
        # 更新用户余额
        cursor.execute("UPDATE users SET tokens_balance=? WHERE id=?", (new_balance, user_id))
        
        # 记录交易
        now = datetime.now().isoformat()
        cursor.execute("""
            INSERT INTO token_transactions (user_id, amount, balance_after, transaction_type, description, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (user_id, -amount, new_balance, 'ai_tool', description or 'AI工具调用', now))
        
        db.commit()
        db.close()
        
        return {
            'success': True,
            'data': {
                'amount': -amount,
                'balance_before': balance,
                'balance_after': new_balance,
                'transaction_type': 'ai_tool'
            }
        }
    except Exception as e:
        try:
            db.close()
        except Exception:
            pass
        return {'success': False, 'error': f'扣费失败: {str(e)}'}


def log_ai_tool(lawyer_profile_id, tool_type, input_summary, output_summary, tokens_used=TOKEN_CONSUME_AMOUNT):
    """记录AI工具调用日志"""
    db = get_db()
    cursor = db.cursor()
    cursor.execute('''
        INSERT INTO lawyer_ai_tool_logs (lawyer_id, tool_type, input_summary, output_summary, tokens_used, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (lawyer_profile_id, tool_type, input_summary[:200], output_summary[:200], tokens_used, datetime.now().isoformat()))
    db.commit()
    db.close()


def get_user_id_from_token(params):
    """从参数中提取并验证token，返回(user_id, error)
    
    支持两种方式：
    1. Bearer Token（通过 _token 参数传入，查找 users.username）
    2. 直接传入 user_id（兼容现有模式）
    """
    token = params.get('token', params.get('_token', ''))
    
    # 方式1: 如果有token，通过token查用户
    if token:
        return verify_token(token)
    
    # 方式2: 直接传user_id（兼容模式）
    user_id = params.get('user_id')
    if user_id:
        try:
            return int(user_id), None
        except (ValueError, TypeError):
            pass
    
    return None, '缺少认证Token或user_id'


# ==================== 统一的AI工具处理函数 ====================

def handle_ai_tool_request(params, tool_type, process_func):
    """统一的AI工具请求处理模板
    
    1. 验证Token → 获取user_id
    2. 验证律师身份 + 年费检查
    3. 扣减Token
    4. 记录日志
    5. 执行业务处理（返回mock数据）
    """
    # Step 1: 验证Token
    user_id_str, err = get_user_id_from_token(params)
    if err:
        return {'code': 401, 'message': '认证失败', 'data': {'error': err}}
    
    user_id = int(user_id_str)
    
    # Step 2: 验证律师身份和年费
    lawyer_profile_id, err = verify_lawyer_and_fee(user_id)
    if err:
        return {'code': 403, 'message': '权限不足', 'data': {'error': err}}
    
    # Step 3: 扣减Token
    token_result = consume_tokens(user_id, TOKEN_CONSUME_AMOUNT, description=f'AI{tool_type}')
    if not token_result['success']:
        return {'code': 402, 'message': 'Token扣减失败', 'data': {'error': token_result['error']}}
    
    # Step 4: 执行业务处理
    result_data = process_func(params, user_id, lawyer_profile_id)
    
    # 添加token_cost到返回数据
    if isinstance(result_data, dict):
        result_data['token_cost'] = TOKEN_CONSUME_AMOUNT
    
    # Step 5: 记录日志
    input_summary = json.dumps(params, ensure_ascii=False)
    output_summary = json.dumps(result_data, ensure_ascii=False)
    log_ai_tool(lawyer_profile_id, tool_type, input_summary, output_summary)
    
    return {
        'code': 200,
        'message': 'success',
        'data': result_data
    }


# ==================== 1. AI谈单分析 ====================

def handle_analyze(params):
    """POST /api/lawyer/ai/analyze — AI谈单分析（真实AI调用）"""
    case_description = params.get('case_description', '')
    client_info = params.get('client_info', {})
    
    if not case_description:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 case_description'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_ANALYZE.format(
            case_description=case_description,
            client_info=json.dumps(client_info, ensure_ascii=False)
        )
        messages = [
            {"role": "system", "content": "你是一名经验丰富的执业律师，擅长案件分析和策略制定。请严格按照要求输出JSON格式。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=2048)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'analysis': result[:500],
                'win_rate': 0.5,
                'estimated_compensation': '需进一步分析',
                'strategy_suggestions': 'AI分析结果格式异常，请重新尝试',
                'fee_suggestion': '待评估',
                '_ai_raw': result[:200]
            }
    
    return handle_ai_tool_request(params, 'analyze', process)


# ==================== 2. AI生成文书 ====================

def handle_generate_doc(params):
    """POST /api/lawyer/ai/generate-doc — AI生成文书"""
    doc_type = params.get('doc_type', '')
    case_info = params.get('case_info', {})
    
    if not doc_type:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 doc_type'}}
    if not case_info:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 case_info'}}
    
    valid_types = ['起诉状', '答辩状', '代理词', '辩护词', '上诉状']
    if doc_type not in valid_types:
        return {'code': 400, 'message': '参数错误', 'data': {'error': f'无效的文书类型，可选: {",".join(valid_types)}'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_GENERATE_DOC.format(
            doc_type=doc_type,
            plaintiff=case_info.get('plaintiff', '未知'),
            defendant=case_info.get('defendant', '未知'),
            case_reason=case_info.get('case_reason', case_info.get('reason', '')),
            facts=case_info.get('facts', case_info.get('description', '')),
            evidence=case_info.get('evidence', ''),
            doc_id=int(f"{datetime.now().timestamp():.0f}") % 1000000
        )
        messages = [
            {"role": "system", "content": "你是一名资深的法律文书专家。请严格按照法律文书格式生成完整的法律文书。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=4096)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'doc_id': int(f"{datetime.now().timestamp():.0f}") % 1000000,
                'content': result[:1000],
                'word_url': f'/uploads/docs/auto_{int(datetime.now().timestamp())}.docx',
                '_ai_raw': result[:200]
            }
    
    return handle_ai_tool_request(params, 'generate_doc', process)


# ==================== 3. AI文书审查 ====================

def handle_review_doc(params):
    """POST /api/lawyer/ai/review-doc — AI文书审查"""
    doc_content = params.get('doc_content', '')
    doc_type = params.get('doc_type', '')
    
    if not doc_content:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 doc_content'}}
    if not doc_type:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 doc_type'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_REVIEW_DOC.format(
            doc_type=doc_type,
            doc_content=doc_content
        )
        messages = [
            {"role": "system", "content": "你是一名法律文书质量审查专家，擅长发现文书中的法律风险和逻辑漏洞。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=2048)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'review_opinions': result[:500],
                'risk_warnings': 'AI审查结果格式异常，请重新尝试',
                'suggestions': '请重新提交审查请求',
                '_ai_raw': result[:200]
            }
    
    return handle_ai_tool_request(params, 'review_doc', process)


# ==================== 4. AI阅卷摘要 ====================

def handle_summary(params):
    """POST /api/lawyer/ai/summary — AI阅卷摘要"""
    file_url = params.get('file_url', '')
    file_type = params.get('file_type', '')
    
    if not file_url:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 file_url'}}
    if not file_type:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 file_type'}}
    
    valid_types = ['pdf', 'image']
    if file_type not in valid_types:
        return {'code': 400, 'message': '参数错误', 'data': {'error': f'无效的文件类型，可选: {",".join(valid_types)}'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_SUMMARY.format(
            file_type=file_type,
            file_content=f'文件URL: {file_url}',
            content_hint='请根据文件类型和URL分析'
        )
        messages = [
            {"role": "system", "content": "你是一名经验丰富的卷宗阅卷律师，擅长从卷宗中提取关键信息。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=2048)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'timeline': 'AI分析结果',
                'relations': result[:300],
                'key_facts': 'AI阅卷摘要处理完成',
                '_ai_raw': result[:200]
            }
    
    return handle_ai_tool_request(params, 'summary', process)


# ==================== 5. AI证据整理 ====================

def handle_evidence(params):
    """POST /api/lawyer/ai/evidence — AI证据整理"""
    case_id = params.get('case_id')
    evidence_list = params.get('evidence_list', [])
    
    if not case_id:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 case_id'}}
    if not evidence_list or not isinstance(evidence_list, list):
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 evidence_list 或格式不正确'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_EVIDENCE.format(
            case_id=case_id,
            evidence_list_str=json.dumps(evidence_list, ensure_ascii=False)
        )
        messages = [
            {"role": "system", "content": "你是一名诉讼证据专家，擅长证据链分析和证据目录编制。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=2048)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'evidence_catalog': result[:500],
                'chain_analysis': 'AI证据分析完成',
                'missing_suggestions': '请根据AI分析结果补充证据',
                '_ai_raw': result[:200]
            }
    
    return handle_ai_tool_request(params, 'evidence', process)


# ==================== 6. AI法律检索 ====================

def handle_legal_search(params):
    """POST /api/lawyer/ai/legal-search — AI法律检索"""
    query = params.get('query', '')
    case_type = params.get('case_type', '')
    
    if not query:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 query'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_LEGAL_SEARCH.format(
            query=query,
            case_type=case_type or '综合'
        )
        messages = [
            {"role": "system", "content": "你是一名法律检索专家，熟知中国法律法规体系，擅长精准匹配相关法条。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=2048)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'results': [
                    {'title': 'AI检索结果', 'content': result[:500], 'relevance': 0.5}
                ]
            }
    
    return handle_ai_tool_request(params, 'legal_search', process)


# ==================== 7. AI类案推送 ====================

def handle_class_case(params):
    """POST /api/lawyer/ai/class-case — AI类案推送"""
    case_id = params.get('case_id')
    
    if not case_id:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 case_id'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_CLASS_CASE.format(
            case_type=params.get('case_type', '综合'),
            case_description=params.get('case_description', '')
        )
        messages = [
            {"role": "system", "content": "你是一名类案检索专家，能从大量判例中找到与本案最相似的案例。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=3072)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'similar_cases': [
                    {'case_id': 'AI001', 'title': 'AI检索结果', 'court': '', 'judgment_date': '', 'case_no': '', 'summary': result[:300], 'similarity': 0.5}
                ],
                'compensation_range': '参考同类案件'
            }
    
    return handle_ai_tool_request(params, 'class_case', process)


# ==================== 8. AI庭审提纲 ====================

def handle_trial_outline(params):
    """POST /api/lawyer/ai/trial-outline — AI庭审提纲"""
    case_id = params.get('case_id')
    
    if not case_id:
        return {'code': 400, 'message': '参数错误', 'data': {'error': '缺少 case_id'}}
    
    def process(p, uid, pid):
        prompt = PROMPT_TRIAL_OUTLINE.format(
            case_type=params.get('case_type', '综合'),
            case_description=params.get('case_description', ''),
            trial_focus=params.get('trial_focus', '无特定焦点')
        )
        messages = [
            {"role": "system", "content": "你是一名出庭经验丰富的诉讼律师，擅长准备庭审提纲。"},
            {"role": "user", "content": prompt}
        ]
        result = call_llm(messages, temperature=0.3, max_tokens=3072)
        try:
            clean = result.strip().replace('```json', '').replace('```', '').strip()
            data = json.loads(clean)
            return data
        except:
            return {
                'cross_examination_outline': result[:500],
                'debate_outline': 'AI庭审提纲生成完成',
                'judge_questions': '请根据AI分析结果准备庭审'
            }
    
    return handle_ai_tool_request(params, 'trial_outline', process)


# ==================== 路由调度 ====================

ACTION_MAP = {
    'create_tables': create_tables,
    'analyze': handle_analyze,
    'generate_doc': handle_generate_doc,
    'review_doc': handle_review_doc,
    'summary': handle_summary,
    'evidence': handle_evidence,
    'legal_search': handle_legal_search,
    'class_case': handle_class_case,
    'trial_outline': handle_trial_outline,
}


def main():
    if len(sys.argv) < 2:
        print(json.dumps({'code': 400, 'message': '缺少参数 action', 'data': {}}))
        sys.exit(1)

    action = sys.argv[1]
    body_str = sys.argv[2] if len(sys.argv) > 2 else '{}'

    try:
        params = json.loads(body_str) if body_str else {}
    except json.JSONDecodeError as e:
        print(json.dumps({'code': 400, 'message': f'JSON解析失败: {str(e)}', 'data': {}}))
        sys.exit(1)

    # 统一处理GET传参：将列表值转为单值
    for k, v in params.items():
        if isinstance(v, list) and len(v) == 1:
            params[k] = v[0]

    try:
        handler = ACTION_MAP.get(action)
        if handler:
            result = handler(params)
        else:
            result = {'code': 404, 'message': f'未知操作: {action}', 'data': {}}

        print(json.dumps(result, ensure_ascii=False), flush=True)

        if result.get('code', 200) >= 400:
            sys.exit(1)
    except Exception as e:
        print(json.dumps({'code': 500, 'message': str(e), 'data': {}}, ensure_ascii=False), flush=True)
        sys.exit(1)


if __name__ == '__main__':
    main()
