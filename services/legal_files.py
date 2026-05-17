"""
心海法律AI - 用户个人法律档案管理与维权提醒功能
"""

import json
import hashlib
from datetime import datetime, date, timedelta
from typing import Dict, List, Optional
from models.db import get_db, UserModel


# 法律时效数据库
STATUTE_OF_LIMITATIONS = {
    "民事诉讼": "《民法典》第188条：向人民法院请求保护民事权利的诉讼时效期间为三年",
    "劳动争议仲裁": "《劳动争议调解仲裁法》第27条：劳动争议仲裁时效为一年，自知道或应当知道权利被侵害之日起计算",
    "行政诉讼": "《行政诉讼法》第46条：直接向法院提起诉讼的，应在知道或应当知道行政行为之日起六个月内提出",
    "行政复议": "《行政复议法》第9条：自知道该具体行政行为之日起六十日内提出行政复议申请",
    "交通事故赔偿": "《民法典》第188条：人身损害赔偿诉讼时效三年，从知道或者应当知道权利被侵害之日起计算",
    "医疗纠纷": "《民法典》第188条：医疗损害赔偿诉讼时效三年",
    "欠款追讨": "《民法典》第188条：有约定还款日期的，从到期日起三年；无约定的，从宽限期届满起三年",
    "离婚诉讼": "不受诉讼时效限制，但财产分割通常应在离婚后一年内提出",
    "继承纠纷": "《民法典》第1124条：继承权纠纷提起诉讼的期限为三年，自继承人知道或应当知道其权利被侵犯之日起计算",
    "知识产权侵权": "《专利法》第74条：侵犯专利权的诉讼时效为三年；《商标法》第45条：五年",
    "工伤认定": "《工伤保险条例》第17条：用人单位应在30日内申请，职工方应在一年内申请",
    "国家赔偿": "《国家赔偿法》第39条：两年，自知道或者应当知道国家机关及其工作人员行使职权时的行为侵犯其合法权益之日起计算",
    "欠税追缴": "《税收征收管理法》第52条：三年，特殊情况可延长至五年",
    "产品质量": "《民法典》第188条：三年；《产品质量法》第45条：因产品存在缺陷造成损害的诉讼时效为二年"
}


class LegalFileService:
    """法律档案管理服务"""
    
    def get_user_cases(self, user_id: int, status: str = None) -> List[Dict]:
        """获取用户案件列表"""
        conn = get_db()
        try:
            query = "SELECT * FROM legal_cases WHERE user_id=?"
            params = [user_id]
            if status:
                query += " AND status=?"
                params.append(status)
            query += " ORDER BY updated_at DESC"
            
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def get_case_detail(self, case_id: int) -> Optional[Dict]:
        """获取案件详情"""
        conn = get_db()
        try:
            case = conn.execute(
                "SELECT * FROM legal_cases WHERE id=?", (case_id,)
            ).fetchone()
            if not case:
                return None
            
            case = dict(case)
            
            # 获取相关文档
            docs = conn.execute(
                "SELECT * FROM legal_docs WHERE case_id=? ORDER BY created_at DESC",
                (case_id,)
            ).fetchall()
            case['docs'] = [dict(d) for d in docs]
            
            # 获取时间线
            timeline = conn.execute(
                "SELECT * FROM legal_timeline WHERE case_id=? ORDER BY event_date DESC",
                (case_id,)
            ).fetchall()
            case['timeline'] = [dict(t) for t in timeline]
            
            # 获取提醒
            reminders = conn.execute(
                "SELECT * FROM rights_reminders WHERE case_id=? AND status='active' ORDER BY due_date ASC",
                (case_id,)
            ).fetchall()
            case['reminders'] = [dict(r) for r in reminders]
            
            # 解析关键日期
            if case.get('key_dates'):
                try:
                    case['key_dates'] = json.loads(case['key_dates'])
                except:
                    case['key_dates'] = {}
            else:
                case['key_dates'] = {}
            
            return case
        finally:
            conn.close()
    
    def create_case(self, user_id: int, title: str, description: str = None,
                    case_type: str = None, domain: str = None,
                    opponent_name: str = None, claim_amount: float = None,
                    key_date: str = None, key_date_desc: str = None) -> Dict:
        """创建案件"""
        conn = get_db()
        try:
            # 生成案件编号
            case_number = f"XH{datetime.now().strftime('%Y%m%d')}{user_id:04d}{int(datetime.now().timestamp()) % 1000:03d}"
            
            key_dates = {}
            if key_date and key_date_desc:
                key_dates[key_date] = key_date_desc
            
            cursor = conn.execute("""
                INSERT INTO legal_cases (user_id, case_number, title, description,
                    case_type, domain, opponent_name, claim_amount, 
                    key_dates, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'active')
            """, (user_id, case_number, title, description, case_type, domain,
                  opponent_name, claim_amount, json.dumps(key_dates) if key_dates else None))
            
            case_id = cursor.lastrowid
            
            # 自动添加创建事件到时间线
            conn.execute("""
                INSERT INTO legal_timeline (user_id, case_id, event_type, title, description, event_date)
                VALUES (?, ?, 'created', '案件创建', ?, ?)
            """, (user_id, case_id, description or title, date.today().isoformat()))
            
            conn.commit()
            
            return {
                'success': True,
                'case_id': case_id,
                'case_number': case_number
            }
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()
    
    def update_case(self, case_id: int, **kwargs) -> bool:
        """更新案件信息"""
        if not kwargs:
            return False
        
        conn = get_db()
        try:
            # 如果 key_dates 是 dict，转为 JSON
            if 'key_dates' in kwargs and isinstance(kwargs['key_dates'], dict):
                kwargs['key_dates'] = json.dumps(kwargs['key_dates'])
            
            sets = ', '.join(f"{k}=?" for k in kwargs)
            values = list(kwargs.values()) + [case_id]
            conn.execute(
                f"UPDATE legal_cases SET {sets}, updated_at=CURRENT_TIMESTAMP WHERE id=?",
                values
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def add_timeline_event(self, user_id: int, case_id: int, event_type: str,
                           title: str, description: str = None,
                           event_date: str = None) -> Dict:
        """添加时间线事件"""
        if not event_date:
            event_date = date.today().isoformat()
        
        conn = get_db()
        try:
            cursor = conn.execute("""
                INSERT INTO legal_timeline (user_id, case_id, event_type, title, description, event_date)
                VALUES (?, ?, ?, ?, ?, ?)
            """, (user_id, case_id, event_type, title, description, event_date))
            conn.commit()
            
            # 更新案件更新时间
            conn.execute(
                "UPDATE legal_cases SET updated_at=CURRENT_TIMESTAMP WHERE id=?",
                (case_id,)
            )
            
            return {'success': True, 'event_id': cursor.lastrowid}
        except Exception as e:
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()
    
    def upload_document(self, user_id: int, case_id: int, doc_type: str,
                        title: str, content: str = None, file_content: str = None,
                        tags: List[str] = None) -> Dict:
        """上传法律文档"""
        conn = get_db()
        try:
            file_hash = None
            if file_content:
                file_hash = hashlib.md5(file_content.encode()).hexdigest()
            
            cursor = conn.execute("""
                INSERT INTO legal_docs (user_id, case_id, doc_type, title, content,
                    file_hash, tags)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (user_id, case_id, doc_type, title, content or file_content,
                  file_hash, json.dumps(tags) if tags else None))
            conn.commit()
            
            # 记录时间线
            conn.execute("""
                INSERT INTO legal_timeline (user_id, case_id, event_type, 
                    title, description, event_date)
                VALUES (?, ?, 'document', ?, ?, ?)
            """, (user_id, case_id, f'上传文档: {title}', f'类型: {doc_type}', date.today().isoformat()))
            
            conn.commit()
            return {'success': True, 'doc_id': cursor.lastrowid}
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': str(e)}
        finally:
            conn.close()


class RightsReminderService:
    """维权提醒服务"""
    
    def __init__(self, config: Dict):
        self.config = config
    
    def add_reminder(self, user_id: int, case_id: int, title: str,
                     description: str, reminder_type: str,
                     due_date: str, remind_before_days: int = 7) -> Dict:
        """添加维权提醒"""
        from models.db import RightsReminderModel
        
        # 验证提醒类型
        valid_types = ['statute_of_limitations', 'court_date', 'evidence_deadline',
                       'appeal_deadline', 'payment_due', 'custom']
        if reminder_type not in valid_types:
            return {'success': False, 'message': f'无效的提醒类型，可选: {", ".join(valid_types)}'}
        
        try:
            reminder_id = RightsReminderModel.create_reminder(
                user_id, case_id, title, description, reminder_type,
                due_date, remind_before_days
            )
            return {
                'success': True,
                'reminder_id': reminder_id,
                'message': f'提醒已设置，将在到期前{remind_before_days}天开始提醒'
            }
        except Exception as e:
            return {'success': False, 'message': str(e)}
    
    def get_statute_info(self, case_type: str) -> str:
        """获取诉讼时效信息"""
        # 模糊匹配
        for key, info in STATUTE_OF_LIMITATIONS.items():
            if case_type in key or key in case_type:
                return info
        return "《民法典》第188条：一般民事诉讼时效为三年，法律另有规定的除外"
    
    def auto_suggest_reminders(self, case_id: int) -> List[Dict]:
        """根据案件信息自动建议提醒"""
        from models.db import get_db
        conn = get_db()
        try:
            case = conn.execute(
                "SELECT * FROM legal_cases WHERE id=?", (case_id,)
            ).fetchone()
            if not case:
                return []
            
            case = dict(case)
            suggestions = []
            today = date.today()
            
            # 根据案件领域推荐提醒
            domain_reminders = {
                "劳动争议": {
                    'type': 'statute_of_limitations',
                    'title': '劳动仲裁时效提醒',
                    'desc': '劳动争议仲裁时效为1年，请尽快申请',
                    'due': (today + timedelta(days=330)).isoformat()
                },
                "合同纠纷": {
                    'type': 'statute_of_limitations',
                    'title': '合同纠纷诉讼时效提醒',
                    'desc': '一般合同纠纷诉讼时效为3年',
                    'due': (today + timedelta(days=1065)).isoformat()
                },
                "交通事故": {
                    'type': 'statute_of_limitations',
                    'title': '人身损害赔偿时效提醒',
                    'desc': '人身损害赔偿诉讼时效为3年',
                    'due': (today + timedelta(days=1065)).isoformat()
                }
            }
            
            if case.get('domain') and case['domain'] in domain_reminders:
                r = domain_reminders[case['domain']]
                suggestions.append({
                    'title': r['title'],
                    'description': r['desc'],
                    'reminder_type': r['type'],
                    'due_date': r['due'],
                    'remind_before_days': 30
                })
            
            # 如果有开庭日期，添加提醒
            if case.get('key_dates'):
                try:
                    dates = json.loads(case['key_dates'])
                    for dt, desc in dates.items():
                        suggestions.append({
                            'title': f'关键日期提醒: {desc}',
                            'description': f'案件"{case["title"]}"的关键日期',
                            'reminder_type': 'custom',
                            'due_date': dt,
                            'remind_before_days': 7
                        })
                except:
                    pass
            
            return suggestions
        finally:
            conn.close()
    
    def check_due_reminders(self, days: int = 3) -> List[Dict]:
        """检查到期的提醒"""
        from models.db import RightsReminderModel
        return RightsReminderModel.get_due_reminders(days)
    
    def dismiss_reminder(self, reminder_id: int) -> bool:
        """忽略提醒"""
        conn = get_db()
        try:
            conn.execute(
                "UPDATE rights_reminders SET status='dismissed' WHERE id=?",
                (reminder_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()
    
    def complete_reminder(self, reminder_id: int) -> bool:
        """完成提醒"""
        conn = get_db()
        try:
            conn.execute(
                "UPDATE rights_reminders SET status='completed' WHERE id=?",
                (reminder_id,)
            )
            conn.commit()
            return True
        finally:
            conn.close()


class LegalKnowledgeBase:
    """法律知识库"""
    
    def __init__(self, db_path: str = None):
        self.db_path = db_path
    
    def search(self, keyword: str, domain: str = None, limit: int = 10) -> List[Dict]:
        """搜索法律知识"""
        conn = get_db()
        try:
            query = """
                SELECT * FROM knowledge_base 
                WHERE (title LIKE ? OR content LIKE ? OR keywords LIKE ?)
            """
            params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']
            
            if domain:
                query += " AND domain=?"
                params.append(domain)
            
            query += " ORDER BY created_at DESC LIMIT ?"
            params.append(limit)
            
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def search_law(self, keyword: str, category: str = None) -> List[Dict]:
        """搜索法律法规"""
        conn = get_db()
        try:
            query = """
                SELECT * FROM law_articles
                WHERE (law_name LIKE ? OR article_number LIKE ? OR content LIKE ? OR summary LIKE ?)
            """
            params = [f'%{keyword}%', f'%{keyword}%', f'%{keyword}%', f'%{keyword}%']
            
            if category:
                query += " AND category=?"
                params.append(category)
            
            query += " ORDER BY law_name, article_number LIMIT 20"
            
            rows = conn.execute(query, params).fetchall()
            return [dict(r) for r in rows]
        finally:
            conn.close()
    
    def seed_knowledge(self):
        """初始化知识库数据"""
        # 获取db_path
        db_path = self.db_path
        knowledge_items = [
            {
                "title": "劳动仲裁申请流程",
                "content": """劳动仲裁是解决劳动争议的必经前置程序。

申请流程：
1. 提交申请书：向用人单位所在地的劳动人事争议仲裁委员会提交
2. 受理审查：仲裁委员会在5个工作日内决定是否受理
3. 开庭审理：受理后45日内作出裁决
4. 不服裁决：15日内可向法院起诉

所需材料：
- 仲裁申请书（写明诉求和事实理由）
- 身份证明
- 证据材料（劳动合同、工资单、考勤记录等）
- 用人单位工商信息

注意：仲裁时效为1年，从知道或应当知道权利被侵害之日起计算。""",
                "domain": "劳动争议",
                "keywords": json.dumps(["劳动仲裁", "劳动争议", "仲裁申请", "劳动法"]),
                "law_reference": "《劳动争议调解仲裁法》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "离婚方式及条件",
                "content": """离婚有两种方式：

一、协议离婚
- 双方自愿且对子女抚养、财产分割达成一致
- 需到民政局办理离婚登记
- 《民法典》第1077条：30天冷静期
- 冷静期满后30日内双方需共同到场领证

二、诉讼离婚
- 一方不同意或无法达成协议
- 向有管辖权的法院起诉
- 法院调解无效后判决

准予离婚的情形（《民法典》第1079条）：
1. 重婚或与他人同居
2. 实施家庭暴力或虐待
3. 有赌博、吸毒等恶习屡教不改
4. 感情不和分居满2年
5. 其他导致感情破裂的情形

注意：女方在怀孕期间、分娩后一年内或终止妊娠后六个月内，男方不得提出离婚。""",
                "domain": "婚姻家庭",
                "keywords": json.dumps(["离婚", "协议离婚", "诉讼离婚", "婚姻法"]),
                "law_reference": "《民法典·婚姻家庭编》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "民间借贷纠纷处理指南",
                "content": """民间借贷纠纷处理指南：

一、证据收集
1. 借条/欠条原件
2. 转账记录（银行、微信、支付宝）
3. 现金交付的收据
4. 聊天记录、通话录音（需合法取得）
5. 催收记录

二、诉讼时效
- 有约定还款日：到期日起3年
- 无约定：出借人可随时要求还款，从宽限期届满起3年
- 超过时效可能丧失胜诉权

三、利息问题
- 有约定：不超过LPR的4倍（约14.8%/年）受保护
- 无约定：视为无利息
- 超过36%：属于高利贷，超过部分无效

四、追讨步骤
1. 发送正式催收函/律师函
2. 申请支付令（简易程序）
3. 提起诉讼
4. 申请强制执行""",
                "domain": "债权债务",
                "keywords": json.dumps(["借贷", "欠款", "利息", "高利贷", "借条"]),
                "law_reference": "《民法典·合同编》《最高人民法院关于审理民间借贷案件适用法律若干问题的规定》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "欠薪维权指南",
                "content": "公司拖欠工资维权指南：\n\n一、法律依据\n《劳动法》第50条：工资应当以货币形式按月支付给劳动者本人，不得克扣或者无故拖欠。\n《劳动合同法》第85条：用人单位拖欠劳动报酬的，劳动行政部门责令限期支付；逾期不支付的，责令按应付金额50%-100%加付赔偿金。\n\n二、维权步骤\n1. 协商：先与公司沟通，要求支付欠薪\n2. 投诉：向当地劳动监察大队投诉（12333热线）\n3. 仲裁：申请劳动仲裁（时效1年）\n4. 诉讼：不服仲裁结果可向法院起诉\n\n三、证据收集\n- 劳动合同/工作证/工牌\n- 考勤记录/打卡记录\n- 工资单/银行流水\n- 聊天记录/邮件（证明工资标准）\n- 录音（需合法取得）\n\n四、风险提示\n- 不要主动辞职（影响经济补偿金）\n- 保存好所有证据原件\n- 仲裁不收费",
                "domain": "劳动争议",
                "keywords": json.dumps(["欠薪", "拖欠工资", "工资", "劳动报酬"]),
                "law_reference": "《劳动法》《劳动合同法》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "工伤认定与赔偿",
                "content": "工伤认定与赔偿指南：\n\n一、工伤认定条件（《工伤保险条例》第14条）\n1. 工作时间工作场所内因工作原因受到事故伤害\n2. 工作时间前后在工作场所内从事预备性或收尾性工作受伤害\n3. 因履行工作职责受到暴力等意外伤害\n4. 患职业病\n5. 因工外出期间受到伤害\n6. 上下班途中非本人主要责任交通事故\n\n二、申请时限\n- 用人单位：30日内\n- 职工本人/近亲属：1年内\n\n三、赔偿项目\n- 医疗费、护理费、伙食补助费\n- 停工留薪期工资\n- 一次性伤残补助金（7-27个月工资）\n- 一次性医疗补助金+就业补助金\n- 死亡：丧葬补助金+供养亲属抚恤金+一次性工亡补助金\n\n四、维权流程\n1. 治疗并保存病历\n2. 向人社局申请工伤认定\n3. 劳动能力鉴定\n4. 协商赔偿或申请仲裁",
                "domain": "劳动争议",
                "keywords": json.dumps(["工伤", "工伤认定", "工伤赔偿", "职业病"]),
                "law_reference": "《工伤保险条例》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "交通事故赔偿标准",
                "content": "交通事故赔偿指南：\n\n一、责任认定\n- 交警出具《交通事故认定书》，划分责任比例\n- 不服可在3日内申请复核\n\n二、赔偿项目（《民法典》第1179条）\n1. 医疗费\n2. 误工费：因事故减少的收入\n3. 护理费\n4. 交通费\n5. 营养费\n6. 住院伙食补助费\n7. 残疾赔偿金：按伤残等级×当地人均收入×20年\n8. 死亡赔偿金：当地人均收入×20年\n9. 精神损害抚慰金\n10. 财产损失\n\n三、保险理赔\n1. 交强险先赔付（有责：医疗1.8万+死亡18万+财产2000）\n2. 商业三者险赔付超出部分\n\n四、诉讼时效：3年",
                "domain": "交通事故",
                "keywords": json.dumps(["交通事故", "车祸", "赔偿", "责任认定"]),
                "law_reference": "《民法典》《道路交通安全法》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "合同违约处理指南",
                "content": "合同违约处理指南：\n\n一、违约类型（《民法典》第577条）\n1. 不履行\n2. 不完全履行\n3. 迟延履行\n4. 预期违约\n\n二、违约救济方式\n1. 继续履行\n2. 赔偿损失：实际损失+可得利益损失\n3. 支付违约金\n4. 定金罚则：给付方违约不得返还，收受方违约双倍返还\n5. 解除合同\n\n三、注意事项\n- 违约金过高可请求法院调低（超过实际损失30%）\n- 定金不超过合同总价20%\n- 诉讼时效：3年\n- 保留合同原件、付款凭证等证据",
                "domain": "合同纠纷",
                "keywords": json.dumps(["合同违约", "违约", "合同纠纷", "违约金"]),
                "law_reference": "《民法典·合同编》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "辞退与经济补偿",
                "content": "辞退与经济补偿指南：\n\n一、合法辞退情形\n1. 协商一致解除（N）\n2. 员工严重违纪（无补偿）\n3. 不能胜任工作（提前30天通知或N+1）\n4. 经济性裁员（N）\n5. 合同期满不续签（N）\n\n二、经济补偿金计算（N）\n- 每工作满1年支付1个月工资\n- 6个月以上不满1年按1年算\n- 不满6个月支付半个月工资\n- 月工资超社平工资3倍的，按3倍算，最高12年\n\n三、赔偿金（2N）\n- 违法解除劳动合同支付2倍经济补偿金\n- 包括：无正当理由辞退、孕期辞退、医疗期辞退\n\n四、特殊情况\n- 孕期、产期、哺乳期女职工不得辞退\n- 医疗期内不得辞退\n- 工伤1-6级不得解除劳动关系",
                "domain": "劳动争议",
                "keywords": json.dumps(["辞退", "开除", "经济补偿", "N+1", "违法解除"]),
                "law_reference": "《劳动合同法》",
                "source": "心海法律AI知识库"
            },
            {
                "title": "婚姻财产分割",
                "content": "离婚财产分割指南：\n\n一、共同财产范围（《民法典》第1062条）\n- 工资、奖金、劳务报酬\n- 生产经营投资收益\n- 知识产权收益\n- 继承或受赠的财产（遗嘱指定归一方除外）\n- 婚后购置的房产、车辆等\n\n二、个人财产范围（不分割）\n- 婚前个人财产\n- 因身体伤害获得的赔偿金\n- 遗嘱或赠与指定归个人的财产\n\n三、房产分割原则\n1. 婚前全款买房：归一方\n2. 婚前首付+婚后还贷：房子归首付方，补偿还贷+增值的一半\n3. 婚后共同买房：各50%\n4. 父母出资：登记在子女名下视为赠与\n\n四、共同债务\n- 为家庭日常生活所负的债务\n- 共同经营所负的债务",
                "domain": "婚姻家庭",
                "keywords": json.dumps(["离婚财产", "财产分割", "房产分割", "共同财产"]),
                "law_reference": "《民法典·婚姻家庭编》",
                "source": "心海法律AI知识库"
            }
        ]

        conn = get_db(db_path)
        try:
            for item in knowledge_items:
                conn.execute("""
                    INSERT OR IGNORE INTO knowledge_base 
                    (title, content, domain, keywords, law_reference, source)
                    VALUES (?, ?, ?, ?, ?, ?)
                """, (item['title'], item['content'], item['domain'],
                      item['keywords'], item['law_reference'], item['source']))
            conn.commit()
            return len(knowledge_items)
        finally:
            conn.close()
