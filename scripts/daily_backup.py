#!/home/admin/xinhai_legal_api/venv/bin/python3
"""心海法律 AI 每日自动备份脚本

功能：
1. 数据库备份（压缩存储，保留最近30天）
2. 代码备份（git bundle，保留最近7天）
3. 配置文件备份
4. 清理过期备份
5. 推送备份报告到微信

执行时间：每天 03:00
"""

import json
import os
import shutil
import subprocess
import sys
import tarfile
import gzip
from datetime import datetime, timedelta

# ============ 配置 ============
BASE_DIR = "/home/admin/xinhai_legal_api"
BACKUP_ROOT = "/home/admin/backups"
DB_PATHS = [
    "/home/admin/xinhai_legal_api/data/xinhai_legal.db",
    "/home/admin/xinhai_legal.db",
]
CODE_DIR = "/home/admin/xinhai_legal_api"
CONFIG_FILES = [
    "/home/admin/.hermes/config.yaml",
    "/www/wwwroot/xinclaw-law/hermes_business_api.py",
    "/www/wwwroot/xinclaw-law/docs/PRD_终版.md",
    "/www/wwwroot/xinclaw-law/docs/DEV_PROGRESS.md",
]

RETENTION_DAYS = {
    "db": 30,
    "code": 7,
    "config": 14,
}

# ============ 工具函数 ============
def today():
    return datetime.now().strftime("%Y%m%d")

def log(msg):
    ts = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    print(f"[{ts}] {msg}")

def run_cmd(cmd, timeout=120):
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)
        return result.returncode == 0, result.stdout.strip()[:200]
    except Exception as e:
        return False, str(e)

def ensure_dir(path):
    os.makedirs(path, exist_ok=True)


def backup_database():
    """备份所有数据库文件"""
    results = []
    db_backup_dir = os.path.join(BACKUP_ROOT, "db")
    ensure_dir(db_backup_dir)

    for db_path in DB_PATHS:
        if not os.path.exists(db_path):
            results.append({"path": db_path, "status": "SKIP", "size": 0, "reason": "文件不存在"})
            continue

        db_name = os.path.basename(db_path).replace(".db", "")
        backup_name = f"{db_name}_{today()}.db.gz"
        backup_path = os.path.join(db_backup_dir, backup_name)

        # gzip 压缩备份
        original_size = os.path.getsize(db_path)
        with open(db_path, "rb") as f_in:
            with gzip.open(backup_path, "wb") as f_out:
                shutil.copyfileobj(f_in, f_out)

        compressed_size = os.path.getsize(backup_path)
        ratio = compressed_size / original_size * 100 if original_size > 0 else 0

        results.append({
            "path": db_path,
            "status": "OK",
            "original_size": original_size,
            "compressed_size": compressed_size,
            "ratio": f"{ratio:.1f}%",
        })
        log(f"  ✅ 备份数据库: {db_path} ({original_size}→{compressed_size}字节, {ratio:.1f}%)")

    return results


def backup_code():
    """使用 git bundle 备份代码"""
    code_backup_dir = os.path.join(BACKUP_ROOT, "code")
    ensure_dir(code_backup_dir)

    bundle_name = f"code_{today()}.bundle"
    bundle_path = os.path.join(code_backup_dir, bundle_name)

    ok, msg = run_cmd(["git", "-C", CODE_DIR, "bundle", "create", bundle_path, "--all"])

    if ok:
        size = os.path.getsize(bundle_path)
        log(f"  ✅ 备份代码: {bundle_path} ({size}字节)")
        return {"status": "OK", "path": bundle_path, "size": size}
    else:
        log(f"  ❌ 代码备份失败: {msg}")
        return {"status": "FAIL", "error": msg}


def backup_config():
    """备份配置文件"""
    config_backup_dir = os.path.join(BACKUP_ROOT, "config")
    ensure_dir(config_backup_dir)

    results = []
    for cfg_path in CONFIG_FILES:
        if not os.path.exists(cfg_path):
            results.append({"path": cfg_path, "status": "SKIP"})
            continue

        cfg_name = os.path.basename(cfg_path)
        backup_name = f"{cfg_name}.{today()}.bak"
        backup_path = os.path.join(config_backup_dir, backup_name)

        shutil.copy2(cfg_path, backup_path)
        results.append({"path": cfg_path, "status": "OK", "size": os.path.getsize(backup_path)})
        log(f"  ✅ 备份配置: {cfg_path} → {backup_path}")

    return results


def cleanup_old_backups():
    """清理过期备份"""
    cleaned = []

    for category, days in RETENTION_DAYS.items():
        backup_dir = os.path.join(BACKUP_ROOT, category)
        if not os.path.exists(backup_dir):
            continue

        cutoff = datetime.now() - timedelta(days=days)
        count = 0

        for f in os.listdir(backup_dir):
            fpath = os.path.join(backup_dir, f)
            if os.path.isfile(fpath):
                mtime = datetime.fromtimestamp(os.path.getmtime(fpath))
                if mtime < cutoff:
                    os.remove(fpath)
                    count += 1

        if count > 0:
            log(f"  清理 {category} 过期备份: {count} 个")
            cleaned.append({"category": category, "removed": count})

    return cleaned


def get_backup_summary(db_results, code_result, config_results, cleaned):
    """生成备份报告摘要"""
    summary_parts = []
    summary_parts.append("📦 **每日备份报告**")
    summary_parts.append(f"📅 日期: {today()}")

    # 数据库
    db_ok = sum(1 for r in db_results if r["status"] == "OK")
    db_total = len(db_results)
    summary_parts.append(f"💾 **数据库**: {db_ok}/{db_total} 成功")
    for r in db_results:
        if r["status"] == "OK":
            summary_parts.append(f"  • {os.path.basename(r['path'])}: {r['original_size']}→{r['compressed_size']}字节 ({r['ratio']})")

    # 代码
    if code_result["status"] == "OK":
        summary_parts.append(f"📁 **代码**: 已打包 ({code_result['size']}字节)")
    else:
        summary_parts.append(f"📁 **代码**: ❌ 失败")

    # 配置
    cfg_ok = sum(1 for r in config_results if r["status"] == "OK")
    cfg_total = len([r for r in config_results if r["path"] in CONFIG_FILES])
    summary_parts.append(f"⚙️ **配置**: {cfg_ok}/{cfg_total} 成功")

    # 清理
    total_cleaned = sum(r.get("removed", 0) for r in cleaned)
    if total_cleaned > 0:
        summary_parts.append(f"🧹 **清理**: {total_cleaned} 个过期备份")

    # 磁盘
    disk = shutil.disk_usage(BACKUP_ROOT)
    free_gb = disk.free / (1024**3)
    total_gb = disk.total / (1024**3)
    summary_parts.append(f"💿 **磁盘**: {free_gb:.1f}GB 可用 / {total_gb:.1f}GB")

    return "\n".join(summary_parts)


def main():
    log(f"🚀 开始每日备份 ({today()})")
    ensure_dir(BACKUP_ROOT)

    # 1. 备份数据库
    log("[1/4] 备份数据库...")
    db_results = backup_database()

    # 2. 备份代码
    log("[2/4] 备份代码...")
    code_result = backup_code()

    # 3. 备份配置
    log("[3/4] 备份配置...")
    config_results = backup_config()

    # 4. 清理过期备份
    log("[4/4] 清理过期备份...")
    cleaned = cleanup_old_backups()

    # 生成摘要
    summary = get_backup_summary(db_results, code_result, config_results, cleaned)
    log(f"\n{summary}")

    # 保存摘要到文件
    summary_path = os.path.join(BACKUP_ROOT, f"backup_report_{today()}.md")
    with open(summary_path, "w") as f:
        f.write(summary)
    log(f"📝 报告保存: {summary_path}")

    # JSON 用于推送
    db_ok = sum(1 for r in db_results if r["status"] == "OK")
    report = {
        "date": today(),
        "db": {"ok": db_ok, "total": len(db_results)},
        "code": code_result["status"],
        "config": {"ok": len([r for r in config_results if r["status"] == "OK"]), "total": len([r for r in config_results if r["path"] in CONFIG_FILES])},
        "cleaned": cleaned,
        "disk_free_gb": round(shutil.disk_usage(BACKUP_ROOT).free / (1024**3), 1),
    }

    print(f"\nJSON_OUTPUT:{json.dumps(report)}")
    return 0 if code_result["status"] == "OK" and db_ok > 0 else 1


if __name__ == "__main__":
    db_ok = 0
    sys.exit(main())
