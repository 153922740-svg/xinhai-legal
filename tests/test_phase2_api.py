"""
心海法律 AI - Phase 2 会员系统 API 测试脚本
"""

import requests
import json

BASE_URL = 'http://localhost:5000'

def test_membership_plans():
    """测试获取会员方案"""
    print("\n=== 测试：获取会员方案 ===")
    response = requests.get(f'{BASE_URL}/api/v2/membership/plans')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_create_user():
    """创建测试用户"""
    print("\n=== 测试：创建测试用户 ===")
    response = requests.post(f'{BASE_URL}/api/v4/user/register', json={
        'username': f'test_user_{int(__import__("time").time())}',
        'password': 'Test123456',
        'phone': '13800138000'
    })
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    if data['code'] == 200:
        return data['data']['user_id']
    return None


def test_membership_status(user_id):
    """测试获取会员状态"""
    print(f"\n=== 测试：获取会员状态 (user_id={user_id}) ===")
    response = requests.get(f'{BASE_URL}/api/v2/membership/status', params={'user_id': user_id})
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_create_membership_order(user_id):
    """测试创建会员订单"""
    print(f"\n=== 测试：创建会员订单 (user_id={user_id}) ===")
    response = requests.post(f'{BASE_URL}/api/v2/membership/order', json={
        'user_id': user_id,
        'plan': 'monthly'
    })
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    if data['code'] == 200:
        return data['data']['order_id']
    return None


def test_get_order(order_id):
    """测试查询订单"""
    print(f"\n=== 测试：查询订单 (order_id={order_id}) ===")
    response = requests.get(f'{BASE_URL}/api/v2/membership/order/{order_id}')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_token_balance(user_id):
    """测试查询 Token 余额"""
    print(f"\n=== 测试：查询 Token 余额 (user_id={user_id}) ===")
    response = requests.get(f'{BASE_URL}/api/v2/token/balance', params={'user_id': user_id})
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_token_pricing():
    """测试查询 Token 价格"""
    print("\n=== 测试：查询 Token 价格 ===")
    response = requests.get(f'{BASE_URL}/api/v2/token/pricing')
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_dashboard_metrics():
    """测试数据看板"""
    print("\n=== 测试：数据看板核心指标 ===")
    response = requests.get(f'{BASE_URL}/api/v2/dashboard/metrics/overview', params={'days': 7})
    data = response.json()
    print(f"Status: {response.status_code}")
    print(f"Response: {json.dumps(data, indent=2, ensure_ascii=False)}")
    return data['code'] == 200


def test_health_checks():
    """测试所有健康检查"""
    print("\n=== 测试：健康检查 ===")
    endpoints = [
        '/api/v2/membership/health',
        '/api/v2/token/health',
        '/api/v2/payment/health',
        '/api/v2/dashboard/health'
    ]
    
    all_ok = True
    for endpoint in endpoints:
        response = requests.get(f'{BASE_URL}{endpoint}')
        data = response.json()
        status = '✅' if data.get('status') == 'ok' else '❌'
        print(f"{status} {endpoint}: {data.get('status')}")
        if data.get('status') != 'ok':
            all_ok = False
    
    return all_ok


def main():
    """运行所有测试"""
    print("=" * 60)
    print("心海法律 AI - Phase 2 会员系统 API 测试")
    print("=" * 60)
    
    results = []
    
    # 1. 健康检查
    results.append(('健康检查', test_health_checks()))
    
    # 2. 会员方案
    results.append(('会员方案', test_membership_plans()))
    
    # 3. Token 价格
    results.append(('Token 价格', test_token_pricing()))
    
    # 4. 数据看板
    results.append(('数据看板', test_dashboard_metrics()))
    
    # 5. 创建测试用户并测试完整流程
    user_id = test_create_user()
    if user_id:
        results.append(('会员状态', test_membership_status(user_id)))
        results.append(('Token 余额', test_token_balance(user_id)))
        order_id = test_create_membership_order(user_id)
        if order_id:
            results.append(('订单查询', test_get_order(order_id)))
    
    # 汇总结果
    print("\n" + "=" * 60)
    print("测试结果汇总")
    print("=" * 60)
    for name, passed in results:
        status = '✅ 通过' if passed else '❌ 失败'
        print(f"{status} - {name}")
    
    total = len(results)
    passed = sum(1 for _, p in results if p)
    print(f"\n总计：{passed}/{total} 测试通过")
    
    return passed == total


if __name__ == '__main__':
    success = main()
    exit(0 if success else 1)
