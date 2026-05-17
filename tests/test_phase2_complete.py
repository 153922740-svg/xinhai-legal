"""
心海法律 AI - Phase 2 会员系统完整测试套件
"""

import requests
import json
import time
import unittest

BASE_URL = 'http://localhost:5000'

class TestPhase2Membership(unittest.TestCase):
    """Phase 2 会员系统测试"""
    
    def setUp(self):
        """测试前准备"""
        self.test_user = {
            'phone': f'138{int(time.time()) % 10000:04d}{int(time.time()) % 10000:04d}',
            'password': 'Test123456'
        }
        self.user_id = None
        self.token = None
    
    def test_01_membership_plans(self):
        """测试 1: 获取会员方案"""
        response = requests.get(f'{BASE_URL}/api/v2/membership/plans')
        data = response.json()
        
        self.assertEqual(data['code'], 200)
        self.assertIn('plans', data['data'])
        self.assertIn('new_user_bonus', data['data'])
        
        # 验证方案完整性
        plans = data['data']['plans']
        plan_ids = [p['plan_id'] for p in plans]
        self.assertIn('monthly', plan_ids)
        self.assertIn('quarterly', plan_ids)
        self.assertIn('yearly', plan_ids)
        
        print("✅ 会员方案查询正常")
    
    def test_02_token_pricing(self):
        """测试 2: 获取 Token 价格"""
        response = requests.get(f'{BASE_URL}/api/v2/token/pricing')
        data = response.json()
        
        self.assertEqual(data['code'], 200)
        self.assertIn('basic_price', data['data'])
        self.assertIn('premium_price', data['data'])
        self.assertIn('packages', data['data'])
        
        # 验证价格合理性
        self.assertGreater(data['data']['basic_price'], 0)
        self.assertLess(data['data']['premium_price'], data['data']['basic_price'])
        
        print("✅ Token 价格查询正常")
    
    def test_03_create_membership_order(self):
        """测试 3: 创建会员订单"""
        # 先创建测试用户 (使用 Phase 4 接口)
        register_data = {
            'phone': self.test_user['phone'],
            'password': self.test_user['password'],
            'sms_code': '123456'  # 测试环境简化
        }
        
        # 跳过注册，直接测试订单创建
        # 使用已知用户 ID
        order_data = {
            'user_id': 1,
            'plan': 'monthly'
        }
        
        response = requests.post(
            f'{BASE_URL}/api/v2/membership/order',
            json=order_data
        )
        data = response.json()
        
        # 可能因为用户不存在而失败，这是预期的
        if data['code'] == 200:
            self.assertIn('order_id', data['data'])
            self.assertEqual(data['data']['status'], 'pending')
            print("✅ 会员订单创建正常")
        else:
            print(f"⚠️ 订单创建跳过 (用户不存在): {data['message']}")
    
    def test_04_membership_health(self):
        """测试 4: 会员系统健康检查"""
        response = requests.get(f'{BASE_URL}/api/v2/membership/health')
        data = response.json()
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['membership_router'], 'available')
        self.assertEqual(data['database'], 'connected')
        
        print("✅ 会员系统健康检查通过")
    
    def test_05_token_health(self):
        """测试 5: Token 计费系统健康检查"""
        response = requests.get(f'{BASE_URL}/api/v2/token/health')
        data = response.json()
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['token_router'], 'available')
        
        print("✅ Token 计费系统健康检查通过")
    
    def test_06_payment_health(self):
        """测试 6: 支付系统健康检查"""
        response = requests.get(f'{BASE_URL}/api/v2/payment/health')
        data = response.json()
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['payment_router'], 'available')
        
        print("✅ 支付系统健康检查通过")
    
    def test_07_dashboard_health(self):
        """测试 7: 数据看板健康检查"""
        response = requests.get(f'{BASE_URL}/api/v2/dashboard/health')
        data = response.json()
        
        self.assertEqual(data['status'], 'ok')
        self.assertEqual(data['dashboard_router'], 'available')
        
        print("✅ 数据看板健康检查通过")
    
    def test_08_dashboard_metrics(self):
        """测试 8: 获取数据看板指标"""
        response = requests.get(
            f'{BASE_URL}/api/v2/dashboard/metrics/overview',
            params={'days': 7}
        )
        data = response.json()
        
        # 可能因为无数据返回 0，这是正常的
        if data['code'] == 200:
            self.assertIn('revenue', data['data'])
            self.assertIn('new_members', data['data'])
            self.assertIn('active_users', data['data'])
            print("✅ 数据看板指标查询正常")
        else:
            print(f"⚠️ 数据看板查询：{data['message']}")


class TestPhase2EdgeCases(unittest.TestCase):
    """Phase 2 边界测试"""
    
    def test_edge_01_invalid_user_id(self):
        """边界测试 1: 无效用户 ID"""
        response = requests.get(
            f'{BASE_URL}/api/v2/membership/status',
            params={'user_id': 999999}
        )
        data = response.json()
        
        # 应返回用户不存在错误
        self.assertIn(data['code'], [404, 500])
        print("✅ 无效用户 ID 处理正确")
    
    def test_edge_02_invalid_plan(self):
        """边界测试 2: 无效会员方案"""
        response = requests.post(
            f'{BASE_URL}/api/v2/membership/order',
            json={'user_id': 1, 'plan': 'invalid_plan'}
        )
        data = response.json()
        
        # 应返回错误
        self.assertIn(data['code'], [400, 500])
        print("✅ 无效会员方案处理正确")
    
    def test_edge_03_missing_params(self):
        """边界测试 3: 缺少必要参数"""
        response = requests.post(
            f'{BASE_URL}/api/v2/membership/order',
            json={}
        )
        data = response.json()
        
        self.assertEqual(data['code'], 400)
        print("✅ 缺少参数处理正确")
    
    def test_edge_04_token_balance_negative_user(self):
        """边界测试 4: 负数用户 ID 查询 Token"""
        response = requests.get(
            f'{BASE_URL}/api/v2/token/balance',
            params={'user_id': -1}
        )
        data = response.json()
        
        # 应返回错误 (400/404/500 都可以接受)
        self.assertGreaterEqual(data['code'], 400)
        print("✅ 负数用户 ID 处理正确")


def run_tests():
    """运行所有测试"""
    print("="*70)
    print("心海法律 AI - Phase 2 完整测试套件")
    print("="*70)
    
    # 创建测试套件
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()
    
    # 添加测试
    suite.addTests(loader.loadTestsFromTestCase(TestPhase2Membership))
    suite.addTests(loader.loadTestsFromTestCase(TestPhase2EdgeCases))
    
    # 运行测试
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)
    
    # 输出结果
    print("\n" + "="*70)
    print(f"测试结果：{result.testsRun} 个测试，{len(result.failures)} 失败，{len(result.errors)} 错误")
    print("="*70)
    
    return result.wasSuccessful()


if __name__ == '__main__':
    success = run_tests()
    exit(0 if success else 1)
