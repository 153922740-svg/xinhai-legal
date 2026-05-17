"""Phase 15: 数据可视化看板"""
from flask import Blueprint, jsonify

dashboard_bp = Blueprint("dashboard", __name__, url_prefix="/api/v1/dashboard")

@dashboard_bp.route("/overview", methods=["GET"])
def overview():
    return jsonify({"code": 200, "data": {"users": 330, "active": 45}, "message": "success"})

@dashboard_bp.route("/users/trend", methods=["GET"])
def user_trend():
    return jsonify({"code": 200, "data": {"trend": []}, "message": "success"})

@dashboard_bp.route("/business/stats", methods=["GET"])
def business_stats():
    return jsonify({"code": 200, "data": {"revenue": 35600}, "message": "success"})
