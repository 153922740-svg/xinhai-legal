"""
心海法律 AI - 性能压力测试
使用 Locust 进行 API 负载测试
"""

from locust import HttpUser, task, between
import random
import json


class ChatUser(HttpUser):
    """模拟聊天用户"""
    wait_time = between(1, 3)
    
    @task(3)
    def send_message(self):
        """发送消息"""
        messages = [
            "公司拖欠工资怎么办？",
            "如何申请劳动仲裁？",
            "劳动合同到期不续签有补偿吗？",
            "工伤赔偿标准是什么？",
            "如何起诉离婚？"
        ]
        
        self.client.post(
            "/api/v1/chat/send",
            json={
                "message": random.choice(messages),
                "user_id": random.randint(1, 100)
            }
        )
    
    @task(1)
    def get_recommendations(self):
        """获取推荐"""
        user_id = random.randint(1, 100)
        self.client.post(f"/api/v1/recommend/user/{user_id}")


class DocumentUser(HttpUser):
    """模拟文书生成用户"""
    wait_time = between(2, 5)
    
    @task(2)
    def generate_document(self):
        """生成文书"""
        doc_types = ["劳动仲裁申请书", "民事起诉状", "律师函", "借款合同"]
        
        self.client.post(
            "/api/v1/document/generate",
            json={
                "type": random.choice(doc_types),
                "user_id": random.randint(1, 100),
                "content": "测试内容"
            }
        )


class DashboardUser(HttpUser):
    """模拟看板用户"""
    wait_time = between(5, 10)
    
    @task(1)
    def view_dashboard(self):
        """查看看板"""
        self.client.get("/api/v1/dashboard/overview")
        self.client.get("/api/v1/dashboard/users/trend")
        self.client.get("/api/v1/dashboard/business/stats")


# 压力测试配置
"""
运行命令:
locust -f tests/test_load.py --host=http://localhost:8081

测试场景:
1. 10 用户并发 - 基础负载
2. 50 用户并发 - 正常负载
3. 100 用户并发 - 高负载
4. 500 用户并发 - 压力测试

验收标准:
- API 响应时间 P95 < 500ms
- 错误率 < 1%
- 系统不崩溃
"""
