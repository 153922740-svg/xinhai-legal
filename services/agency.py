"""
心海法律AI - 全国区县代理与合伙人分佣体系
"""

import json
import uuid
import hashlib
from datetime import datetime
from typing import Dict, List, Optional, Tuple
from models.db import get_db, UserModel


# 全国行政区划数据 (省/市/区)
REGIONS = {
    "北京市": {
        "code": "110000",
        "children": {
            "东城区": "110101", "西城区": "110102", "朝阳区": "110105",
            "丰台区": "110106", "石景山区": "110107", "海淀区": "110108",
            "门头沟区": "110109", "房山区": "110111", "通州区": "110112",
            "顺义区": "110113", "昌平区": "110114", "大兴区": "110115",
            "怀柔区": "110116", "平谷区": "110117", "密云区": "110118",
            "延庆区": "110119"
        }
    },
    "上海市": {
        "code": "310000",
        "children": {
            "黄浦区": "310101", "徐汇区": "310104", "长宁区": "310105",
            "静安区": "310106", "普陀区": "310107", "虹口区": "310109",
            "杨浦区": "310110", "闵行区": "310112", "宝山区": "310113",
            "嘉定区": "310114", "浦东新区": "310115", "金山区": "310116",
            "松江区": "310117", "青浦区": "310118", "奉贤区": "310120",
            "崇明区": "310151"
        }
    },
    "广东省": {
        "code": "440000",
        "children": {
            "广州市": "440100", "深圳市": "440300", "珠海市": "440400",
            "汕头市": "440500", "佛山市": "440600", "韶关市": "440200",
            "河源市": "441600", "梅州市": "441400", "惠州市": "441300",
            "汕尾市": "441500", "东莞市": "441900", "中山市": "442000",
            "江门市": "440700", "阳江市": "441700", "湛江市": "440800",
            "茂名市": "440900", "肇庆市": "441200", "清远市": "441800",
            "潮州市": "445100", "揭阳市": "445200", "云浮市": "445300"
        }
    },
    "浙江省": {
        "code": "330000",
        "children": {
            "杭州市": "330100", "宁波市": "330200", "温州市": "330300",
            "嘉兴市": "330400", "湖州市": "330500", "绍兴市": "330600",
            "金华市": "330700", "衢州市": "330800", "舟山市": "330900",
            "台州市": "331000", "丽水市": "331100"
        }
    },
    "江苏省": {
        "code": "320000",
        "children": {
            "南京市": "320100", "无锡市": "320200", "徐州市": "320300",
            "常州市": "320400", "苏州市": "320500", "南通市": "320600",
            "连云港市": "320700", "淮安市": "320800", "盐城市": "320900",
            "扬州市": "321000", "镇江市": "321100", "泰州市": "321200",
            "宿迁市": "321300"
        }
    },
    "四川省": {
        "code": "510000",
        "children": {
            "成都市": "510100", "自贡市": "510300", "攀枝花市": "510400",
            "泸州市": "510500", "德阳市": "510600", "绵阳市": "510700",
            "广元市": "510800", "遂宁市": "510900", "内江市": "511000",
            "乐山市": "511100", "南充市": "511300", "眉山市": "511400",
            "宜宾市": "511500", "广安市": "511600", "达州市": "511700",
            "雅安市": "511800", "巴中市": "511900", "资阳市": "512000"
        }
    },
    "山东省": {
        "code": "370000",
        "children": {
            "济南市": "370100", "青岛市": "370200", "淄博市": "370300",
            "枣庄市": "370400", "东营市": "370500", "烟台市": "370600",
            "潍坊市": "370700", "济宁市": "370800", "泰安市": "370900",
            "威海市": "371000", "日照市": "371100", "临沂市": "371300",
            "德州市": "371400", "聊城市": "371500", "滨州市": "371600",
            "菏泽市": "371700"
        }
    },
    "湖北省": {
        "code": "420000",
        "children": {
            "武汉市": "420100", "黄石市": "420200", "十堰市": "420300",
            "宜昌市": "420500", "襄阳市": "420600", "鄂州市": "420700",
            "荆门市": "420800", "孝感市": "420900", "荆州市": "421000",
            "黄冈市": "421100", "咸宁市": "421200", "随州市": "421300"
        }
    },
    "湖南省": {
        "code": "430000",
        "children": {
            "长沙市": "430100", "株洲市": "430200", "湘潭市": "430300",
            "衡阳市": "430400", "邵阳市": "430500", "岳阳市": "430600",
            "常德市": "430700", "张家界市": "430800", "益阳市": "430900",
            "郴州市": "431000", "永州市": "431100", "怀化市": "431200",
            "娄底市": "431300", "湘西州": "433100"
        }
    },
    "福建省": {
        "code": "350000",
        "children": {
            "福州市": "350100", "厦门市": "350200", "莆田市": "350300",
            "三明市": "350400", "泉州市": "350500", "漳州市": "350600",
            "南平市": "350700", "龙岩市": "350800", "宁德市": "350900"
        }
    },
    "河南省": {
        "code": "410000",
        "children": {
            "郑州市": "410100", "开封市": "410200", "洛阳市": "410300",
            "平顶山市": "410400", "安阳市": "410500", "鹤壁市": "410600",
            "新乡市": "410700", "焦作市": "410800", "濮阳市": "410900",
            "许昌市": "411000", "漯河市": "411100", "三门峡市": "411200",
            "南阳市": "411300", "商丘市": "411400", "信阳市": "411500",
            "周口市": "411600", "驻马店市": "411700"
        }
    },
    "河北省": {
        "code": "130000",
        "children": {
            "石家庄市": "130100", "唐山市": "130200", "秦皇岛市": "130300",
            "邯郸市": "130400", "邢台市": "130500", "保定市": "130600",
            "张家口市": "130700", "承德市": "130800", "沧州市": "130900",
            "廊坊市": "131000", "衡水市": "131100"
        }
    },
    "安徽省": {
        "code": "340000",
        "children": {
            "合肥市": "340100", "芜湖市": "340200", "蚌埠市": "340300",
            "淮南市": "340400", "马鞍山市": "340500", "淮北市": "340600",
            "铜陵市": "340700", "安庆市": "340800", "黄山市": "341000",
            "滁州市": "341100", "阜阳市": "341200", "宿州市": "341300",
            "六安市": "341500", "亳州市": "341600", "池州市": "341700",
            "宣城市": "341800"
        }
    },
    "陕西省": {
        "code": "610000",
        "children": {
            "西安市": "610100", "铜川市": "610200", "宝鸡市": "610300",
            "咸阳市": "610400", "渭南市": "610500", "延安市": "610600",
            "汉中市": "610700", "榆林市": "610800", "安康市": "610900",
            "商洛市": "611000"
        }
    },
    "辽宁省": {
        "code": "210000",
        "children": {
            "沈阳市": "210100", "大连市": "210200", "鞍山市": "210300",
            "抚顺市": "210400", "本溪市": "210500", "丹东市": "210600",
            "锦州市": "210700", "营口市": "210800", "阜新市": "210900",
            "辽阳市": "211000", "盘锦市": "211100", "铁岭市": "211200",
            "朝阳市": "211300", "葫芦岛市": "211400"
        }
    },
    "重庆市": {
        "code": "500000",
        "children": {
            "渝中区": "500103", "江北区": "500105", "沙坪坝区": "500106",
            "九龙坡区": "500107", "南岸区": "500108", "北碚区": "500109",
            "渝北区": "500112", "巴南区": "500113", "万州区": "500101",
            "涪陵区": "500102", "黔江区": "500114", "长寿区": "500115",
            "江津区": "500116", "合川区": "500117", "永川区": "500118",
            "南川区": "500119"
        }
    },
    "天津市": {
        "code": "120000",
        "children": {
            "和平区": "120101", "河东区": "120102", "河西区": "120103",
            "南开区": "120104", "河北区": "120105", "红桥区": "120106",
            "东丽区": "120110", "西青区": "120111", "津南区": "120112",
            "北辰区": "120113", "武清区": "120114", "宝坻区": "120115",
            "滨海新区": "120116", "宁河区": "120117", "静海区": "120118",
            "蓟州区": "120119"
        }
    },
    "江西省": {
        "code": "360000",
        "children": {
            "南昌市": "360100", "景德镇市": "360200", "萍乡市": "360300",
            "九江市": "360400", "新余市": "360500", "鹰潭市": "360600",
            "赣州市": "360700", "吉安市": "360800", "宜春市": "360900",
            "抚州市": "361000", "上饶市": "361100"
        }
    },
    "广西壮族自治区": {
        "code": "450000",
        "children": {
            "南宁市": "450100", "柳州市": "450200", "桂林市": "450300",
            "梧州市": "450400", "北海市": "450500", "防城港市": "450600",
            "钦州市": "450700", "贵港市": "450800", "玉林市": "450900",
            "百色市": "451000", "贺州市": "451100", "河池市": "451200",
            "来宾市": "451300", "崇左市": "451400"
        }
    },
    "云南省": {
        "code": "530000",
        "children": {
            "昆明市": "530100", "曲靖市": "530300", "玉溪市": "530400",
            "保山市": "530500", "昭通市": "530600", "丽江市": "530700",
            "普洱市": "530800", "临沧市": "530900", "楚雄州": "532300",
            "红河州": "532500", "文山州": "532600", "西双版纳州": "532800",
            "大理州": "532900", "德宏州": "533100", "怒江州": "533300",
            "迪庆州": "533400"
        }
    },
    "贵州省": {
        "code": "520000",
        "children": {
            "贵阳市": "520100", "六盘水市": "520200", "遵义市": "520300",
            "安顺市": "520400", "毕节市": "520500", "铜仁市": "520600",
            "黔西南州": "522300", "黔东南州": "522600", "黔南州": "522700"
        }
    },
    "甘肃省": {
        "code": "620000",
        "children": {
            "兰州市": "620100", "嘉峪关市": "620200", "金昌市": "620300",
            "白银市": "620400", "天水市": "620500", "武威市": "620600",
            "张掖市": "620700", "平凉市": "620800", "酒泉市": "620900",
            "庆阳市": "621000", "定西市": "621100", "陇南市": "621200",
            "临夏州": "622900", "甘南州": "623000"
        }
    },
    "黑龙江省": {
        "code": "230000",
        "children": {
            "哈尔滨市": "230100", "齐齐哈尔市": "230200", "鸡西市": "230300",
            "鹤岗市": "230400", "双鸭山市": "230500", "大庆市": "230600",
            "伊春市": "230700", "佳木斯市": "230800", "七台河市": "230900",
            "牡丹江市": "231000", "黑河市": "231100", "绥化市": "231200",
            "大兴安岭地区": "232700"
        }
    },
    "吉林省": {
        "code": "220000",
        "children": {
            "长春市": "220100", "吉林市": "220200", "四平市": "220300",
            "辽源市": "220400", "通化市": "220500", "白山市": "220600",
            "松原市": "220700", "白城市": "220800", "延边州": "222400"
        }
    },
    "山西省": {
        "code": "140000",
        "children": {
            "太原市": "140100", "大同市": "140200", "阳泉市": "140300",
            "长治市": "140400", "晋城市": "140500", "朔州市": "140600",
            "晋中市": "140700", "运城市": "140800", "忻州市": "140900",
            "临汾市": "141000", "吕梁市": "141100"
        }
    },
    "海南省": {
        "code": "460000",
        "children": {
            "海口市": "460100", "三亚市": "460200", "三沙市": "460300",
            "儋州市": "460400"
        }
    },
    "西藏自治区": {
        "code": "540000",
        "children": {
            "拉萨市": "540100", "日喀则市": "540200", "昌都市": "540300",
            "林芝市": "540400", "山南市": "540500", "那曲市": "540600",
            "阿里地区": "542500"
        }
    },
    "内蒙古自治区": {
        "code": "150000",
        "children": {
            "呼和浩特市": "150100", "包头市": "150200", "乌海市": "150300",
            "赤峰市": "150400", "通辽市": "150500", "鄂尔多斯市": "150600",
            "呼伦贝尔市": "150700", "巴彦淖尔市": "150800", "乌兰察布市": "150900",
            "兴安盟": "152200", "锡林郭勒盟": "152500", "阿拉善盟": "152900"
        }
    },
    "宁夏回族自治区": {
        "code": "640000",
        "children": {
            "银川市": "640100", "石嘴山市": "640200", "吴忠市": "640300",
            "固原市": "640400", "中卫市": "640500"
        }
    },
    "青海省": {
        "code": "630000",
        "children": {
            "西宁市": "630100", "海东市": "630200", "海北州": "632200",
            "黄南州": "632300", "海南州": "632500", "果洛州": "632600",
            "玉树州": "632700", "海西州": "632800"
        }
    },
    "新疆维吾尔自治区": {
        "code": "650000",
        "children": {
            "乌鲁木齐市": "650100", "克拉玛依市": "650200", "吐鲁番市": "650400",
            "哈密市": "650500", "阿克苏地区": "652900", "喀什地区": "653100",
            "和田地区": "653200", "昌吉州": "652300", "博尔塔拉州": "652700",
            "巴音郭楞州": "652800", "克孜勒苏州": "653000", "伊犁州": "654000",
            "塔城地区": "654200", "阿勒泰地区": "654300"
        }
    },
    "台湾省": {
        "code": "710000",
        "children": {}
    },
    "香港特别行政区": {
        "code": "810000",
        "children": {}
    },
    "澳门特别行政区": {
        "code": "820000",
        "children": {}
    }
}


class AgencyService:
    """代理与分佣服务"""
    
    def __init__(self, config: Dict):
        self.config = config
        agency_cfg = config['agency']
        self.commission_rates = agency_cfg['commission_rates']
        self.min_withdrawal = agency_cfg['min_withdrawal']
        self.levels = {l['code']: l for l in agency_cfg['levels']}
    
    def get_provinces(self) -> List[str]:
        """获取所有省份列表"""
        return list(REGIONS.keys())
    
    def get_cities(self, province: str) -> List[str]:
        """获取省份下的城市列表"""
        region = REGIONS.get(province)
        if not region:
            return []
        return list(region['children'].keys())
    
    def check_region_available(self, province: str, city: str = None, 
                                district: str = None) -> Dict:
        """检查区域是否可申请"""
        conn = get_db()
        try:
            query = "SELECT * FROM agent_regions WHERE province=? AND is_claimed=1"
            params = [province]
            
            if city:
                query += " AND city=?"
                params.append(city)
            if district:
                query += " AND district=?"
                params.append(district)
            
            existing = conn.execute(query, params).fetchone()
            
            if existing:
                agent = UserModel.get_by_id(existing['agent_id'])
                return {
                    'available': False,
                    'claimed_by': agent['real_name'] if agent else '未知',
                    'agent_level': agent['agent_level'] if agent else '未知'
                }
            return {'available': True}
        finally:
            conn.close()
    
    def apply_agent(self, user_id: int, level: str, province: str,
                    city: str = None, district: str = None,
                    company_name: str = None, contact_phone: str = None,
                    id_card_front: str = None, id_card_back: str = None) -> Dict:
        """申请成为代理"""
        level_info = self.levels.get(level)
        if not level_info:
            return {'success': False, 'message': '无效的代理级别'}
        
        # 检查区域
        check = self.check_region_available(province, city, district)
        if not check['available']:
            return {'success': False, 'message': f"该区域已被 {check['claimed_by']} 申请"}
        
        conn = get_db()
        try:
            # 生成唯一推广码
            referral_code = self._generate_referral_code(user_id, level)
            commission_rate = self.commission_rates.get(level, 0.1)
            
            # 创建代理档案
            cursor = conn.execute("""
                INSERT INTO agent_profiles (user_id, level, province, city, district,
                    commission_rate, referral_code, company_name, contact_phone,
                    id_card_front, id_card_back, status)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'pending')
            """, (user_id, level, province, city, district, commission_rate,
                  referral_code, company_name, contact_phone, id_card_front, id_card_back))
            
            # 更新用户角色
            conn.execute("""
                UPDATE users SET role='agent', agent_level=?, 
                    agent_code=?, agent_province=?, agent_city=?, agent_district=?,
                    updated_at=CURRENT_TIMESTAMP
                WHERE id=?
            """, (level, referral_code, province, city, district, user_id))
            
            conn.commit()
            
            return {
                'success': True,
                'message': '代理申请已提交，等待审核',
                'agent_id': cursor.lastrowid,
                'referral_code': referral_code,
                'commission_rate': commission_rate
            }
        except Exception as e:
            conn.rollback()
            return {'success': False, 'message': f'申请失败: {str(e)}'}
        finally:
            conn.close()
    
    def approve_agent(self, agent_profile_id: int) -> bool:
        """审核通过代理"""
        conn = get_db()
        try:
            profile = conn.execute(
                "SELECT * FROM agent_profiles WHERE id=?", (agent_profile_id,)
            ).fetchone()
            if not profile:
                return False
            
            profile = dict(profile)
            
            # 更新状态
            conn.execute("""
                UPDATE agent_profiles SET status='active', activated_at=CURRENT_TIMESTAMP 
                WHERE id=?
            """, (agent_profile_id,))
            
            # 注册区域
            conn.execute("""
                INSERT INTO agent_regions (province, city, district, agent_id, is_claimed, claimed_at)
                VALUES (?, ?, ?, ?, 1, CURRENT_TIMESTAMP)
            """, (profile['province'], profile['city'], profile.get('district'),
                  profile['user_id']))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[Agency] approve error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def calculate_commission(self, order_amount: float, 
                             agent_id: int) -> List[Dict]:
        """计算分佣 (包括上级抽成)"""
        commissions = []
        
        conn = get_db()
        try:
            agent = conn.execute(
                "SELECT * FROM agent_profiles WHERE user_id=?", (agent_id,)
            ).fetchone()
            if not agent:
                return commissions
            
            agent = dict(agent)
            rate = agent['commission_rate']
            amount = round(order_amount * rate, 2)
            
            if amount > 0:
                commissions.append({
                    'agent_id': agent['id'],
                    'amount': amount,
                    'rate': rate,
                    'level': 'direct'
                })
            
            # 上级抽成
            user = UserModel.get_by_id(agent['user_id'])
            if user and user.get('parent_agent_id'):
                parent_user = UserModel.get_by_id(user['parent_agent_id'])
                if parent_user:
                    parent_agent = conn.execute(
                        "SELECT * FROM agent_profiles WHERE user_id=?",
                        (parent_user['id'],)
                    ).fetchone()
                    if parent_agent:
                        parent_agent = dict(parent_agent)
                        partner_rate = self.commission_rates.get('partner', 0.05)
                        parent_amount = round(order_amount * partner_rate, 2)
                        if parent_amount > 0:
                            commissions.append({
                                'agent_id': parent_agent['id'],
                                'amount': parent_amount,
                                'rate': partner_rate,
                                'level': 'partner'
                            })
            
            return commissions
        finally:
            conn.close()
    
    def record_commission(self, order_id: int, order_type: str, 
                          order_amount: float, agent_id: int) -> bool:
        """记录分佣"""
        commissions = self.calculate_commission(order_amount, agent_id)
        
        conn = get_db()
        try:
            for comm in commissions:
                conn.execute("""
                    INSERT INTO agent_commissions (order_id, order_type, order_amount,
                        agent_id, commission_amount, commission_rate, level, status)
                    VALUES (?, ?, ?, ?, ?, ?, ?, 'pending')
                """, (order_id, order_type, order_amount, 
                      comm['agent_id'], comm['amount'], comm['rate'], comm['level']))
            
            conn.commit()
            return True
        except Exception as e:
            print(f"[Agency] record_commission error: {e}")
            conn.rollback()
            return False
        finally:
            conn.close()
    
    def confirm_commission(self, commission_id: int) -> bool:
        """确认分佣（可提现）"""
        conn = get_db()
        try:
            comm = conn.execute(
                "SELECT * FROM agent_commissions WHERE id=?", (commission_id,)
            ).fetchone()
            if not comm:
                return False
            
            conn.execute("""
                UPDATE agent_commissions SET status='confirmed', 
                    confirmed_at=CURRENT_TIMESTAMP WHERE id=?
            """, (commission_id,))
            
            # 更新可提现余额
            conn.execute("""
                UPDATE agent_profiles SET 
                    withdrawable_commission = withdrawable_commission + ?,
                    total_commission = total_commission + ?
                WHERE id=?
            """, (comm['commission_amount'], comm['commission_amount'], comm['agent_id']))
            
            conn.commit()
            return True
        finally:
            conn.close()
    
    def withdraw_commission(self, agent_profile_id: int, amount: float) -> Dict:
        """申请提现"""
        conn = get_db()
        try:
            agent = conn.execute(
                "SELECT * FROM agent_profiles WHERE id=?", (agent_profile_id,)
            ).fetchone()
            if not agent:
                return {'success': False, 'message': '代理不存在'}
            
            agent = dict(agent)
            
            if amount < self.min_withdrawal:
                return {
                    'success': False, 
                    'message': f'最低提现金额为 {self.min_withdrawal} 元'
                }
            
            if amount > agent['withdrawable_commission']:
                return {
                    'success': False, 
                    'message': f'可提现余额不足，当前可提现 {agent["withdrawable_commission"]} 元'
                }
            
            # TODO: 接入实际支付系统
            # 这里做模拟扣减
            conn.execute("""
                UPDATE agent_profiles SET 
                    withdrawable_commission = withdrawable_commission - ?,
                    total_withdrawn = total_withdrawn + ?
                WHERE id=?
            """, (amount, amount, agent_profile_id))
            
            conn.commit()
            return {
                'success': True,
                'message': f'提现申请已提交，金额 {amount} 元',
                'remaining': agent['withdrawable_commission'] - amount
            }
        finally:
            conn.close()
    
    def get_agent_stats(self, agent_profile_id: int) -> Dict:
        """获取代理统计"""
        conn = get_db()
        try:
            agent = conn.execute(
                "SELECT * FROM agent_profiles WHERE id=?", (agent_profile_id,)
            ).fetchone()
            if not agent:
                return {}
            
            agent = dict(agent)
            
            # 直接下级数量
            team_count = conn.execute("""
                SELECT COUNT(*) as cnt FROM agent_team WHERE agent_id=? AND level=1
            """, (agent_profile_id,)).fetchone()
            
            # 本月佣金
            first_of_month = datetime.now().replace(day=1).isoformat()
            monthly_commission = conn.execute("""
                SELECT COALESCE(SUM(commission_amount), 0) as total
                FROM agent_commissions 
                WHERE agent_id=? AND status='confirmed' AND confirmed_at >= ?
            """, (agent_profile_id, first_of_month)).fetchone()
            
            user = UserModel.get_by_id(agent['user_id'])
            
            return {
                'level': agent['level'],
                'referral_code': agent['referral_code'],
                'total_commission': agent['total_commission'],
                'withdrawable': agent['withdrawable_commission'],
                'total_withdrawn': agent['total_withdrawn'],
                'team_size': team_count['cnt'] if team_count else 0,
                'monthly_commission': monthly_commission['total'] if monthly_commission else 0,
                'status': agent['status'],
                'company_name': agent.get('company_name'),
                'region': f"{agent.get('province','')} {agent.get('city','')} {agent.get('district','')}",
                'membership': user['membership'] if user else 'free'
            }
        finally:
            conn.close()
    
    def _generate_referral_code(self, user_id: int, level: str) -> str:
        """生成唯一推广码"""
        raw = f"xh{level}{user_id}{uuid.uuid4().hex[:8]}"
        code = hashlib.md5(raw.encode()).hexdigest()[:8].upper()
        return f"XH{code}"
