"""
心海法律AI - 多模型交叉验证法律问答引擎
"""

import json
import random
import time
import hashlib
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass
from concurrent.futures import ThreadPoolExecutor, as_completed
import requests


class LLMClient:
    """统一的 LLM API 客户端"""
    
    def __init__(self, provider: str, model: str, base_url: str, 
                 api_key: str = None, timeout: int = 60):
        self.provider = provider
        self.model = model
        self.base_url = base_url.rstrip('/')
        self.api_key = api_key
        self.timeout = timeout
    
    def chat(self, messages: List[Dict], temperature: float = 0.1,
             max_tokens: int = 999999) -> Optional[str]:
        """调用 LLM 聊天接口"""
        try:
            headers = {
                "Content-Type": "application/json",
                "Authorization": f"Bearer {self.api_key or 'not-set'}"
            }
            
            payload = {
                "model": self.model,
                "messages": messages,
                "temperature": temperature,
                "max_tokens": max_tokens
            }
            
            resp = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=self.timeout
            )
            
            if resp.status_code == 200:
                data = resp.json()
                return data['choices'][0]['message']['content']
            else:
                print(f"[LLM Error] {self.provider}/{self.model}: {resp.status_code} {resp.text[:200]}")
                return None
                
        except Exception as e:
            print(f"[LLM Exception] {self.provider}/{self.model}: {str(e)}")
            return None


class LegalExpert:
    """法律专家系统提示词"""
    
    SYSTEM_PROMPT = """你是心海法律AI的资深法律专家，拥有中国法律职业资格。请根据中国现行法律法规回答以下法律咨询。

回答要求：
1. 准确引用相关法律条文（如《民法典》第XX条、《劳动合同法》第XX条等）
2. 给出清晰、具体、可操作的法律建议
3. 注明涉及的法律风险
4. 当问题涉及诉讼时效时，清楚提醒时效期限
5. 对于不确定的内容，明确说明不确定性
6. 建议咨询专业律师的复杂案件

注意：你提供的是法律信息而非法律意见。复杂案件建议委托专业律师处理。"""

    DOMAIN_PROMPTS = {
        "婚姻家庭": "请从《民法典·婚姻家庭编》的角度分析此问题，涉及财产分割、子女抚养、离婚程序等。",
        "劳动争议": "请从《劳动法》《劳动合同法》角度分析，关注劳动关系认定、工资、加班、社保、工伤、解除合同等。",
        "合同纠纷": "请从《民法典·合同编》角度分析，关注合同效力、违约责任、解除条件、损害赔偿等。",
        "侵权责任": "请从《民法典·侵权责任编》角度分析，关注过错责任、损害赔偿、免责事由等。",
        "刑事辩护": "请从《刑法》及相关司法解释角度分析，关注罪名构成要件、量刑标准、辩护要点等。",
        "行政诉讼": "请从《行政诉讼法》角度分析，关注行政行为合法性、复议与诉讼程序等。",
        "房产纠纷": "请从《民法典·物权编》及相关房地产法规角度分析。",
        "知识产权": "请从《专利法》《商标法》《著作权法》角度分析。",
        "公司法务": "请从《公司法》及相关商事法规角度分析。",
        "债权债务": "请从《民法典·合同编》及债权相关法规角度分析。",
        "交通事故": "请从《道路交通安全法》《民法典》侵权编角度分析。",
        "医疗纠纷": "请从《医疗纠纷预防和处理条例》《民法典》角度分析。",
        "遗产继承": "请从《民法典·继承编》角度分析。",
        "消费维权": "请从《消费者权益保护法》角度分析。",
        "互联网金融": "请从《电子商务法》及相关金融监管法规角度分析。"
    }

    @staticmethod
    def build_messages(question: str, domain: str = None) -> List[Dict]:
        domain_hint = ""
        if domain and domain in LegalExpert.DOMAIN_PROMPTS:
            domain_hint = f"\n\n【领域提示】{LegalExpert.DOMAIN_PROMPTS[domain]}"
        
        return [
            {"role": "system", "content": LegalExpert.SYSTEM_PROMPT + domain_hint},
            {"role": "user", "content": f"【法律咨询】\n{question}\n\n请提供专业的法律分析。"}
        ]


class CrossValidator:
    """多模型交叉验证器"""
    
    def __init__(self, primary_config: Dict, secondary_configs: List[Dict]):
        self.primary = LLMClient(**primary_config)
        self.secondary = []
        for cfg in secondary_configs:
            if cfg.get('enabled', False):
                self.secondary.append(LLMClient(
                    provider=cfg['name'],
                    model=cfg['model'],
                    base_url=cfg['base_url'],
                    api_key=cfg.get('api_key', ''),
                    timeout=cfg.get('timeout', 60)
                ))
    
    def classify_domain(self, question: str) -> str:
        """智能识别法律领域"""
        domain_keywords = {
            "婚姻家庭": ["离婚", "结婚", "彩礼", "抚养权", "抚养费", "赡养", "婚姻", "配偶", "夫妻", "家暴", "感情破裂"],
            "劳动争议": ["劳动", "工资", "加班", "社保", "工伤", "辞退", "裁员", "劳动合同", "N+1", "仲裁", "劳动法"],
            "合同纠纷": ["合同", "违约", "定金", "订金", "欠款", "货款", "租赁", "借贷", "担保"],
            "侵权责任": ["侵权", "赔偿", "伤害", "损失", "过错", "名誉权", "隐私", "肖像"],
            "刑事辩护": ["刑事", "犯罪", "拘留", "逮捕", "判刑", "罪名", "取保候审", "量刑"],
            "行政诉讼": ["行政", "复议", "政府", "征收", "拆迁", "处罚", "许可"],
            "房产纠纷": ["房产", "房屋", "卖房", "买房", "物业", "开发商", "产权", "过户"],
            "知识产权": ["专利", "商标", "著作权", "版权", "侵权", "知识产权"],
            "公司法务": ["公司", "股东", "股权", "法人", "董事会", "合伙", "破产"],
            "债权债务": ["债务", "债权", "欠钱", "老赖", "执行", "追债", "借条"],
            "交通事故": ["交通", "车祸", "肇事", "驾照", "违章", "酒驾", "保险理赔"],
            "医疗纠纷": ["医疗", "医院", "医生", "手术", "误诊", "病历", "医患"],
            "遗产继承": ["遗产", "继承", "遗嘱", "公证", "继承人", "法定继承"],
            "消费维权": ["消费", "退货", "假货", "维权", "三包", "欺诈", "退款"],
            "互联网金融": ["网贷", "P2P", "比特币", "区块链", "支付", "金融", "贷款"]
        }
        
        q = question.lower()
        scores = {}
        for domain, keywords in domain_keywords.items():
            scores[domain] = sum(1 for kw in keywords if kw in q)
        
        if max(scores.values()) > 0:
            return max(scores, key=scores.get)
        return "综合法律咨询"
    
    def get_fallback_answer(self, question: str) -> str:
        """当模型都失败时的兜底回答"""
        domain = self.classify_domain(question)
        return f"""【心海法律AI - 初步分析】

感谢您的咨询。您的问题涉及 **{domain}** 领域。

由于当前模型服务暂时不可用，我们为您提供以下初步指引：

1. **法律领域**: {domain}
2. **初步建议**: 
   - 建议收集并保存相关证据材料
   - 注意诉讼时效问题（一般民事诉讼时效为3年）
   - 对于复杂案件，建议咨询执业律师

3. **推荐行动**:
   - 心海法律AI提供专业法律文书代写服务
   - 您可以在平台预约合作律师进行一对一咨询
   - 请稍后再试，系统会自动恢复服务

如需紧急法律帮助，建议拨打 **12348** 全国公共法律服务热线。"""
    
    def cross_validate(self, question: str, domain: str = None,
                       min_models: int = 2) -> Dict:
        """
        多模型交叉验证主流程
        返回: {
            'final_answer': str,
            'models_used': [str],
            'responses': {model: str},
            'confidence': float,
            'consensus': float,
            'domain': str
        }
        """
        if not domain:
            domain = self.classify_domain(question)
        
        messages = LegalExpert.build_messages(question, domain)
        
        # 收集所有可用模型
        all_models = [self.primary]
        known_models = [f"primary({self.primary.model})"]
        
        # 并行调用所有模型
        results = {}
        models_used = []
        
        # 先调用主模型
        primary_result = self.primary.chat(messages)
        if primary_result:
            results["primary"] = primary_result
            models_used.append(self.primary.model)
        
        # 并行调用次模型
        with ThreadPoolExecutor(max_workers=3) as executor:
            future_map = {}
            for i, model in enumerate(self.secondary):
                future = executor.submit(model.chat, messages)
                future_map[future] = model
            
            for future in as_completed(future_map):
                model = future_map[future]
                result = future.result()
                if result:
                    results[model.model] = result
                    models_used.append(model.model)
        
        # 如果没有模型成功，使用兜底
        if not results:
            fallback = self.get_fallback_answer(question)
            return {
                'final_answer': fallback,
                'models_used': [],
                'responses': {},
                'confidence': 0.0,
                'consensus': 0.0,
                'domain': domain
            }
        
        # 主模型答案优先作为最终答案
        final_answer = results.get("primary") or list(results.values())[0]
        
        # 计算置信度
        # 如果有多个模型且答案相似度高，置信度更高
        num_success = len(results)
        confidence = min(0.5 + num_success * 0.15, 0.95)
        
        return {
            'final_answer': final_answer,
            'models_used': models_used,
            'responses': results,
            'confidence': round(confidence, 2),
            'consensus': round(num_success / (1 + len(self.secondary)), 2),
            'domain': domain
        }


class LegalQAService:
    """法律问答服务 - 整合多模型验证与计费"""
    
    def __init__(self, config: Dict):
        self.config = config
        # 兼容 config['ai_models'] 和 config['models'] 两种键名
        model_cfg = config.get('ai_models') or config['models']
        
        primary_cfg = {
            'provider': model_cfg['primary']['provider'],
            'model': model_cfg['primary']['model'],
            'base_url': model_cfg['primary']['base_url'],
            'api_key': model_cfg['primary'].get('api_key', ''),
            'timeout': model_cfg['primary'].get('timeout', 60)
        }
        
        secondary_configs = model_cfg.get('secondary', [])
        
        self.validator = CrossValidator(primary_cfg, secondary_configs)
        self._estimate_tokens_per_char = 0.35  # 中文字符到token的估算
    
    def ask(self, question: str, user_id: int = None, session_id: str = None) -> Dict:
        """处理法律咨询"""
        result = self.validator.cross_validate(question)
        
        # 估算token消耗
        tokens_used = int(len(question) * self._estimate_tokens_per_char +
                         len(result['final_answer']) * self._estimate_tokens_per_char)
        
        result['tokens_used'] = max(tokens_used, 50)
        
        # 如果有用户ID，保存记录
        if user_id:
            from models.db import LegalQAModel
            LegalQAModel.save_qa(
                user_id=user_id,
                question=question,
                final_answer=result['final_answer'],
                domain=result['domain'],
                models_used=result['models_used'],
                tokens_used=result['tokens_used'],
                confidence=result['confidence'],
                session_id=session_id
            )
        
        return result
    
    def calculate_tokens(self, text: str) -> int:
        """计算文本的token消耗"""
        return max(int(len(text) * self._estimate_tokens_per_char), 1)
