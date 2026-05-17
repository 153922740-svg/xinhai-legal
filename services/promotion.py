"""
心海法律AI - 代理专属 AI 推广助手

为代理自动生成：推广文案、海报文案、朋友圈内容、短视频脚本
智能分析客户咨询，提供话术建议
"""

import json
import re
from typing import Dict, List, Optional
from datetime import datetime


# 内置推广文案模板库
PROMOTION_TEMPLATES = {
    "朋友圈推广": [
        {
            "title": "日常普法-劳动者权益",
            "content": "【心海法律AI·每日普法】\n\n📋 老板不给签劳动合同怎么办？\n\n根据《劳动合同法》第10条，建立劳动关系应当订立书面劳动合同。\n\n⚠️ 公司超过1个月不签合同？\n👉 从第2个月起，你可以主张双倍工资！\n\n💡 想了解具体怎么操作？\n心海法律AI 7×24小时在线解答\n扫码即可免费咨询 👇",
            "tags": ["劳动争议", "普法", "日常"]
        },
        {
            "title": "婚姻家庭-离婚冷静期",
            "content": "【心海法律AI·懂法更懂家】\n\n🏠 离婚冷静期到底怎么回事？\n\n《民法典》第1077条：\n✅ 协议离婚：申请后30天内可撤回\n✅ 期满后30天内未领证=视为撤回\n✅ 诉讼离婚：不受冷静期限制\n\n有婚姻法律问题？心海法律AI\n专业分析，保护你的合法权益 💪",
            "tags": ["婚姻家庭", "普法"]
        },
        {
            "title": "消费维权-双十一",
            "content": "【心海法律AI·消费维权指南】\n\n🛒 双十一买买买，遇到问题怎么办？\n\n1️⃣ 买到假货？→ 退一赔三！\n2️⃣ 商家不发货？→ 可要求继续履行\n3️⃣ 预付款不退？→ 涉嫌违规\n4️⃣ 大数据杀熟？→ 违法！\n\n📱 截图保存证据，心海法律AI帮你维权\n扫码→描述问题→获取专业分析",
            "tags": ["消费维权", "促销"]
        },
        {
            "title": "借贷纠纷-欠钱不还",
            "content": "【心海法律AI·债权债务】\n\n💰 朋友借钱不还怎么办？\n\n记住这3步：\n1️⃣ 收集证据：借条/转账记录/聊天记录\n2️⃣ 发送正式催收函\n3️⃣ 诉讼时效：3年！别等过期！\n\n💡 不知道证据够不够？\n把聊天记录发给心海法律AI\n30秒帮你分析胜诉率！",
            "tags": ["债权债务", "普法"]
        },
        {
            "title": "交通事故-理赔指南",
            "content": "【心海法律AI·交通事故理赔指南】\n\n🚗 出了事故别慌张，按步骤来：\n\n1️⃣ 保护现场，报警122\n2️⃣ 报保险，保留证据\n3️⃣ 治疗期间保留所有票据\n4️⃣ 伤残鉴定最好在6个月后\n\n💡 理赔计算太复杂？\n心海法律AI输入事故情况\n自动计算赔偿金额！",
            "tags": ["交通事故", "实用"]
        }
    ],
    "短视频脚本": [
        {
            "title": "30秒法律知识-租房押金",
            "script": """【画面】年轻人在出租屋愁眉苦脸
旁白：租房子押金要不回来？别急，法律给你撑腰！

【画面切换】手机屏幕显示聊天记录
旁白：根据《民法典》，房东无正当理由扣留押金，你有权要求返还并赔偿损失！

【画面】心海法律AI界面
旁白：打开心海法律AI，上传聊天记录和租赁合同
AI自动分析，告诉你胜诉率和维权路径

【结尾】扫码文字
旁白：关注心海法律AI，懂法不吃亏！""",
            "duration": 30,
            "tags": ["房产纠纷", "实用"]
        },
        {
            "title": "1分钟深度-公司裁员赔偿",
            "script": """【画面】办公室里气氛紧张
旁白：公司裁员，赔偿怎么算？别再被HR忽悠了！

【画面】出示计算表格
旁白：N+1？2N？到底哪个才是你的？
根据《劳动合同法》第47条：
- 合法裁员：N个月工资补偿
- 违法解除：2N个月赔偿金
- 协商解除：N+1个月

【画面】心海法律AI计算界面
旁白：输入你的工资和工作年限
心海法律AI帮你算清楚，该拿多少拿多少！

【结尾】扫码关注""",
            "duration": 60,
            "tags": ["劳动争议", "深度"]
        }
    ],
    "节假日营销": [
        {
            "title": "五一劳动节",
            "content": "【心海法律AI·致敬劳动者】\n\n🔧 五一劳动节快乐！\n\n劳动者权益知多少？\n✅ 法定假日加班=3倍工资\n✅ 休息日加班=2倍工资\n✅ 工作满1年有带薪年假\n\n你的权益，心海法律AI来守护\n节日特惠：新用户免费咨询！👇",
            "tags": ["节日", "促销"]
        },
        {
            "title": "春节-讨薪维权",
            "content": "【心海法律AI·安心过年】\n\n🧧 年终奖不发？工资被拖欠？\n\n别让欠薪毁了团圆年！\n\n《保障农民工工资支付条例》明确：\n✅ 工资必须按时足额支付\n✅ 拖欠工资可申请劳动监察\n✅ 恶意欠薪可能构成犯罪\n\n📱 扫码，心海法律AI帮你讨薪",
            "tags": ["节日", "劳动争议"]
        }
    ],
    "行业合作话术": [
        {
            "title": "房产中介合作",
            "content": "【心海法律AI × 房产中介专属合作】\n\n🏠 房产交易中的法律风险，专业工具来帮您！\n\n✅ 快速生成房屋租赁合同\n✅ 买卖合同条款审查\n✅ 产权纠纷即时分析\n✅ 提升客户信任度\n\n合作优势：\n📈 增加服务附加值\n🤝 提升客户转化率\n💰 专属佣金分成\n\n立即开通，免费试用30天！",
            "tags": ["合作", "房产"]
        }
    ]
}


class PromotionService:
    """代理推广助手服务"""
    
    def __init__(self, config: Dict):
        self.config = config
        self.templates = PROMOTION_TEMPLATES
    
    def get_templates(self, category: str = None, tag: str = None) -> Dict:
        """获取推广模板"""
        if category and category in self.templates:
            items = self.templates[category]
            if tag:
                items = [t for t in items if tag in t.get('tags', [])]
            return {category: items}
        
        return self.templates
    
    def generate_promotion(self, category: str, agent_name: str = None,
                           agent_code: str = None, custom_msg: str = None) -> Dict:
        """生成定制推广内容"""
        templates = self.templates.get(category, [])
        if not templates:
            return {'success': False, 'message': f'没有找到 {category} 模板'}
        
        import random
        template = random.choice(templates)
        content = template['content']
        
        # 定制化替换
        if agent_name:
            content = content.replace("心海法律AI", f"{agent_name}·心海法律AI")
        
        if agent_code:
            content = content.replace("扫码即可免费咨询 👇", 
                                     f"扫码输入邀请码【{agent_code}】免费咨询 👇")
            content = content.replace("扫码关注", f"扫码输入邀请码【{agent_code}】关注")
            content = content.replace("扫码免费咨询", f"扫码输入邀请码【{agent_code}】免费咨询")
        
        if custom_msg:
            content = f"{custom_msg}\n\n---\n{content}"
        
        return {
            'success': True,
            'title': template['title'],
            'content': content,
            'original_template': template['title'],
            'tags': template.get('tags', []),
            'word_count': len(content)
        }
    
    def generate_video_script(self, script_title: str = None) -> Dict:
        """生成短视频脚本"""
        scripts = self.templates.get("短视频脚本", [])
        if script_title:
            scripts = [s for s in scripts if script_title in s['title']]
        
        if not scripts:
            import random
            scripts = [random.choice(self.templates.get("短视频脚本", []))]
        
        template = scripts[0]
        return {
            'success': True,
            'title': template['title'],
            'script': template['script'],
            'duration': template.get('duration', 60),
            'tips': [
                "建议使用竖屏9:16拍摄",
                "前3秒一定要吸引注意力",
                "结尾加上行动号召（扫码关注）",
                "可以添加字幕提高完播率"
            ]
        }
    
    def analyze_customer_message(self, message: str) -> Dict:
        """分析客户咨询消息，提供话术建议"""
        # 简单的关键词分析
        keywords = {
            "费用": "客户关心费用问题，建议突出免费咨询、会员优惠。",
            "靠谱": "客户对服务质量有疑虑，建议强调AI+律师双保险。",
            "效果": "客户关注实际效果，可以分享成功案例。",
            "多久": "客户关心时间成本，建议说明AI即时响应优势。",
            "合同": "客户需要合同相关服务，推荐合同审查功能。",
            "起诉": "客户可能需要诉讼服务，建议引导获取完整案情。",
            "劳动": "客户涉及劳动争议，推荐劳动仲裁相关功能。",
            "婚姻": "客户涉及婚姻问题，强调隐私保护。",
            "借钱": "客户涉及借贷纠纷，推荐债权债务分析功能。",
            "交通事故": "客户涉及交通事故，推荐理赔计算功能。"
        }
        
        matched = []
        for kw, suggestion in keywords.items():
            if kw in message:
                matched.append({'keyword': kw, 'suggestion': suggestion})
        
        # 情绪分析（简单）
        negative_words = ["烦", "气", "急", "骗", "亏", "哭", "难受", "无助", "愤怒"]
        positive_words = ["谢谢", "好", "行", "明白", "嗯嗯", "不错"]
        
        sentiment = "中性"
        neg_count = sum(1 for w in negative_words if w in message)
        pos_count = sum(1 for w in positive_words if w in message)
        
        if neg_count > pos_count:
            sentiment = "负面"
        elif pos_count > neg_count:
            sentiment = "正面"
        
        response_suggestions = []
        if sentiment == "负面":
            response_suggestions.append("先安抚情绪：'我理解您的情况，别着急，我们来一步步解决'")
        
        return {
            'keywords_found': matched,
            'sentiment': sentiment,
            'suggestions': matched + [
                {'keyword': '通用', 'suggestion': '先了解完整案情，再推荐适合的功能'}
            ],
            'response_tips': response_suggestions
        }
    
    def generate_weekly_report(self, agent_name: str, stats: Dict) -> str:
        """生成代理周报"""
        now = datetime.now()
        week_num = now.isocalendar()[1]
        
        report = f"""【心海法律AI·代理周报】第{week_num}周

📊 {agent_name}，以下是本周运营数据：

━━━━━━━━━━━━━━━━
📈 业绩概览
━━━━━━━━━━━━━━━━
• 新增用户：{stats.get('new_users', 0)} 人
• 总咨询量：{stats.get('total_queries', 0)} 次
• 成交订单：{stats.get('orders', 0)} 单
• 预计佣金：{stats.get('estimated_commission', 0)} 元
• 可提现余额：{stats.get('withdrawable', 0)} 元

━━━━━━━━━━━━━━━━
🏆 本周推荐
━━━━━━━━━━━━━━━━
📌 热门法律领域：{stats.get('hot_domain', '劳动争议')}
📌 推荐推广内容：请使用"推广助手-朋友圈推广"
📌 话术技巧：突出AI即时响应，7×24小时在线

━━━━━━━━━━━━━━━━
💡 本周行动建议
━━━━━━━━━━━━━━━━
1️⃣ 每天发1条普法朋友圈
2️⃣ 邀请3位好友注册体验
3️⃣ 回复客户咨询时使用AI辅助

━━━━━━━━━━━━━━━━
心海法律AI团队 · 与您共赢
━━━━━━━━━━━━━━━━"""
        return report
