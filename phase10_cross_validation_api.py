"""
Phase 10: 三模型交叉验证引擎
PRD 核心要求：99.2% 准确率

三模型架构：
- DeepSeek-V3: 主模型，生成法律分析和建议
- Qwen3-Max: 验证模型 A，验证法律条文引用准确性
- GLM-4.7: 验证模型 B，验证推理逻辑完整性

一致性裁决：
- 三方一致 → 直接输出（高置信）
- 两方一致 → 输出 + 差异分析
- 三方不一致 → 人工介入提示
"""

import os
import json
import sqlite3
import hashlib
from datetime import datetime
from flask import Blueprint, request, jsonify

phase10_bp = Blueprint('phase10', __name__)

# 模型配置（实际部署时从配置文件读取）
MODEL_CONFIGS = {
    'deepseek': {
        'name': 'DeepSeek-V3',
        'role': 'main',
        'api_key': os.environ.get('DEEPSEEK_API_KEY', 'sk_test'),
        'base_url': 'https://api.deepseek.com/v1',
        'model': 'deepseek-chat'
    },
    'qwen': {
        'name': 'Qwen3-Max',
        'role': 'validator_a',
        'api_key': os.environ.get('ALIYUN_API_KEY', 'sk_test'),
        'base_url': 'https://dashscope.aliyuncs.com/compatible-mode/v1',
        'model': 'qwen-max'
    },
    'glm': {
        'name': 'GLM-4.7',
        'role': 'validator_b',
        'api_key': os.environ.get('ZHIPU_API_KEY', 'sk_test'),
        'base_url': 'https://open.bigmodel.cn/api/paas/v4',
        'model': 'glm-4'
    }
}

# 系统提示词
LEGAL_SYSTEM_PROMPT = """你是一位专业的法律顾问，提供专业、准确、易懂的法律咨询服务。

要求：
1. 先共情，理解用户的处境和情绪
2. 用通俗易懂的语言解释法律问题
3. 引用准确的法律条文（注明具体法条）
4. 给出实操性建议
5. 提醒风险和注意事项
6. 不做胜诉承诺，不代替律师执业

回答结构：
1. 共情理解
2. 现状梳理
3. 法律依据（引用具体法条）
4. 办理/维权流程
5. 风险提示
6. 专业建议
"""

def get_db():
    db = sqlite3.connect('/home/admin/xinhai_legal.db')
    db.row_factory = sqlite3.Row
    return db

def compute_similarity(text1, text2):
    """
    计算两段文本的余弦相似度（简化版）
    实际生产环境应用 sentence-transformers 或 embedding API
    """
    # 简化版：基于关键词重叠率
    words1 = set(text1.lower())
    words2 = set(text2.lower())
    
    if not words1 or not words2:
        return 0.0
    
    intersection = len(words1 & words2)
    union = len(words1 | words2)
    
    return intersection / union if union > 0 else 0.0


def call_llm_api(model_config, messages, temperature=0.7):
    """
    调用 LLM API（模拟实现）
    实际部署时接入真实 API
    """
    # TODO: 实际调用各模型 API
    # 这里模拟返回
    
    user_message = messages[-1]['content'] if messages else ''
    
    # 模拟响应
    mock_response = {
        'deepseek': f"""【DeepSeek-V3 主模型分析】

我理解您遇到的法律问题。根据您描述的情况："{user_message[:50]}..."

【现状梳理】
根据您的描述，这是一个典型的法律咨询场景。

【法律依据】
《中华人民共和国民法典》相关规定...

【维权流程】
1. 收集证据
2. 发送律师函
3. 提起诉讼

【风险提示】
注意诉讼时效，一般民事纠纷诉讼时效为 3 年。

【专业建议】
建议您尽快采取行动，保留所有相关证据。""",

        'qwen': f"""【Qwen3-Max 法律条文验证】

经分析，该问题涉及的主要法律条文：
1. 《民法典》第 XXX 条
2. 《民事诉讼法》第 XXX 条

主模型引用的法律条文基本准确。
置信度：高""",

        'glm': f"""【GLM-4.7 推理逻辑验证】

主模型的推理逻辑链：
1. 事实认定 → 2. 法律适用 → 3. 结论推导

逻辑链条完整，推理过程合理。
置信度：高"""
    }
    
    model_name = model_config['name'].lower().replace('-', '_').replace('.', '')
    if 'deepseek' in model_name:
        return mock_response['deepseek']
    elif 'qwen' in model_name:
        return mock_response['qwen']
    elif 'glm' in model_name:
        return mock_response['glm']
    
    return mock_response['deepseek']


def consistency裁决(results):
    """
    一致性裁决器
    输入：三个模型的回答
    输出：裁决结果
    """
    deepseek = results.get('deepseek', '')
    qwen = results.get('qwen', '')
    glm = results.get('glm', '')
    
    # 计算相似度
    similarity_qw = compute_similarity(deepseek, qwen)
    similarity_gm = compute_similarity(deepseek, glm)
    similarity_qg = compute_similarity(qwen, glm)
    
    # 裁决逻辑
    if similarity_qw > 0.7 and similarity_gm > 0.7:
        # 三方一致
        return {
            'status': 'consistent',
            'confidence': 'high',
            'output': deepseek,
            'validation': '三模型交叉验证通过',
            'similarity': {
                'deepseek_qwen': round(similarity_qw, 2),
                'deepseek_glm': round(similarity_gm, 2),
                'qwen_glm': round(similarity_qg, 2)
            }
        }
    
    elif similarity_qw > 0.5 or similarity_gm > 0.5:
        # 两方一致
        if similarity_qw > similarity_gm:
            consistent_models = ['DeepSeek', 'Qwen']
        else:
            consistent_models = ['DeepSeek', 'GLM']
        
        return {
            'status': 'partial_consistent',
            'confidence': 'medium',
            'output': deepseek,
            'validation': f'{",".join(consistent_models)} 一致，已标注差异',
            'difference': '部分模型存在差异，仅供参考',
            'similarity': {
                'deepseek_qwen': round(similarity_qw, 2),
                'deepseek_glm': round(similarity_gm, 2),
                'qwen_glm': round(similarity_qg, 2)
            }
        }
    
    else:
        # 三方不一致
        return {
            'status': 'inconsistent',
            'confidence': 'low',
            'output': deepseek,
            'validation': '三模型意见不一致',
            'warning': '⚠️ 模型分析存在较大差异，建议咨询专业律师',
            'all_results': results,
            'similarity': {
                'deepseek_qwen': round(similarity_qw, 2),
                'deepseek_glm': round(similarity_gm, 2),
                'qwen_glm': round(similarity_qg, 2)
            }
        }


@phase10_bp.route('/api/v1/ai/chat/validated', methods=['POST'])
def validated_chat():
    """
    三模型交叉验证的 AI 对话
    参数：user_id, message, session_id
    """
    try:
        data = request.get_json()
        user_id = data.get('user_id')
        message = data.get('message')
        session_id = data.get('session_id')
        
        if not user_id or not message:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        # 检查是否是简单问题（跳过验证）
        simple_keywords = ['你好', '您好', '在吗', '谢谢', '再见', '会员', 'Token', '充值']
        if any(kw in message for kw in simple_keywords):
            # 简单问题，直接调用主模型
            response = call_llm_api(MODEL_CONFIGS['deepseek'], [{'role': 'user', 'content': message}])
            return jsonify({
                'code': 200,
                'success': True,
                'response': response,
                'validation': 'simple',
                'model': 'DeepSeek-V3'
            })
        
        # Step 1: 主模型生成回答
        messages = [
            {'role': 'system', 'content': LEGAL_SYSTEM_PROMPT},
            {'role': 'user', 'content': message}
        ]
        deepseek_response = call_llm_api(MODEL_CONFIGS['deepseek'], messages)
        
        # Step 2: 验证模型 A（法律条文验证）
        validator_a_prompt = f"""请作为法律专家，验证以下法律分析中引用的法律条文是否准确：

用户问题：{message}

主模型分析：
{deepseek_response}

请独立分析并指出任何法律条文引用错误。"""

        qwen_response = call_llm_api(MODEL_CONFIGS['qwen'], [{'role': 'user', 'content': validator_a_prompt}])
        
        # Step 3: 验证模型 B（推理逻辑验证）
        validator_b_prompt = f"""请作为逻辑专家，验证以下法律分析的推理逻辑是否完整：

用户问题：{message}

主模型分析：
{deepseek_response}

请独立分析并指出任何逻辑漏洞。"""

        glm_response = call_llm_api(MODEL_CONFIGS['glm'], [{'role': 'user', 'content': validator_b_prompt}])
        
        # Step 4: 一致性裁决
        validation_result = consistency裁决({
            'deepseek': deepseek_response,
            'qwen': qwen_response,
            'glm': glm_response
        })
        
        # Step 5: 缓存结果（用于相似问题）
        cache_key = hashlib.md5(message.encode()).hexdigest()
        db = get_db()
        cursor = db.cursor()
        cursor.execute('''
            INSERT INTO response_cache (cache_key, user_message, response, validation_status, confidence, created_at)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (
            cache_key,
            message,
            validation_result['output'],
            validation_result['status'],
            validation_result['confidence'],
            datetime.now().isoformat()
        ))
        db.commit()
        db.close()
        
        # 构建响应
        response_data = {
            'code': 200,
            'success': True,
            'response': validation_result['output'],
            'validation': validation_result['validation'],
            'confidence': validation_result['confidence'],
            'model': 'DeepSeek-V3 + Qwen3-Max + GLM-4.7',
            'cross_validation': True
        }
        
        if validation_result['status'] == 'inconsistent':
            response_data['warning'] = validation_result.get('warning', '')
        
        return jsonify(response_data)
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'请求失败：{str(e)}'}), 500


@phase10_bp.route('/api/v1/ai/cache', methods=['GET'])
def get_cached_response():
    """
    获取缓存的相似问题回答
    参数：message
    """
    try:
        message = request.args.get('message', '')
        if not message:
            return jsonify({'code': 400, 'message': '缺少参数'}), 400
        
        cache_key = hashlib.md5(message.encode()).hexdigest()
        
        db = get_db()
        cursor = db.cursor()
        
        # 查找完全匹配的缓存
        cursor.execute('''
            SELECT * FROM response_cache WHERE cache_key = ?
            ORDER BY created_at DESC LIMIT 1
        ''', (cache_key,))
        
        cached = cursor.fetchone()
        
        if cached:
            db.close()
            return jsonify({
                'code': 200,
                'message': 'success',
                'data': {
                    'hit': 'exact',
                    'response': cached['response'],
                    'validation_status': cached['validation_status'],
                    'confidence': cached['confidence']
                }
            })
        
        # TODO: 查找相似问题（需要 embedding 支持）
        # cursor.execute('SELECT * FROM response_cache ORDER BY created_at DESC LIMIT 10')
        # ... 计算相似度 ...
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {'hit': 'miss'}
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


@phase10_bp.route('/api/v1/model/stats', methods=['GET'])
def get_model_stats():
    """
    获取模型调用统计
    """
    try:
        db = get_db()
        cursor = db.cursor()
        
        # 总调用数
        cursor.execute('SELECT COUNT(*) as count FROM response_cache')
        total_calls = cursor.fetchone()['count']
        
        # 各置信度分布
        cursor.execute('''
            SELECT confidence, COUNT(*) as count
            FROM response_cache
            GROUP BY confidence
        ''')
        confidence_dist = [dict(row) for row in cursor.fetchall()]
        
        # 验证状态分布
        cursor.execute('''
            SELECT validation_status, COUNT(*) as count
            FROM response_cache
            GROUP BY validation_status
        ''')
        validation_dist = [dict(row) for row in cursor.fetchall()]
        
        db.close()
        
        return jsonify({
            'code': 200,
            'message': 'success',
            'data': {
                'total_calls': total_calls,
                'confidence_distribution': confidence_dist,
                'validation_distribution': validation_dist
            }
        })
        
    except Exception as e:
        return jsonify({'code': 500, 'message': f'查询失败：{str(e)}'}), 500


# ============== 数据库初始化 ==============

def init_phase10_tables():
    """
    初始化 Phase 10 数据库表
    """
    db = get_db()
    cursor = db.cursor()
    
    # 响应缓存表
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS response_cache (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            cache_key TEXT NOT NULL UNIQUE,
            user_message TEXT NOT NULL,
            response TEXT NOT NULL,
            validation_status TEXT,
            confidence TEXT,
            created_at TEXT NOT NULL
        )
    ''')
    
    db.commit()
    db.close()
    print("Phase 10 数据库表初始化完成")


if __name__ == '__main__':
    init_phase10_tables()
    print("Phase 10 三模型交叉验证引擎就绪")
    print("\n请配置以下环境变量:")
    print("  - DEEPSEEK_API_KEY")
    print("  - ALIYUN_API_KEY")
    print("  - ZHIPU_API_KEY")
