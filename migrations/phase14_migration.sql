-- Phase 14 数据库迁移
CREATE TABLE IF NOT EXISTS user_behaviors (id INTEGER PRIMARY KEY, user_id INTEGER, action_type TEXT, target_id TEXT, created_at TIMESTAMP);
CREATE TABLE IF NOT EXISTS recommendations (id INTEGER PRIMARY KEY, user_id INTEGER, recommendation_type TEXT, content_id TEXT, clicked INTEGER DEFAULT 0, created_at TIMESTAMP);
CREATE INDEX idx_behaviors_user ON user_behaviors(user_id);
CREATE INDEX idx_recommendations_user ON recommendations(user_id);
