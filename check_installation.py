#!/usr/bin/env python3
"""
安裝檢查腳本 - 驗證所有依賴和配置
"""

import os
import sys
import json
from pathlib import Path


def check_installation():
    """檢查應用安裝情況"""

    print("\n" + "=" * 60)
    print("🔍 AI 財經監控平台 - 安裝檢查")
    print("=" * 60 + "\n")

    checks = {
        "環境檢查": check_environment,
        "文件檢查": check_files,
        "Python 套件": check_packages,
        "配置檢查": check_config,
        "端口檢查": check_ports,
    }

    results = {}
    for category, check_func in checks.items():
        print(f"\n📋 {category}:")
        results[category] = check_func()

    # 總結
    print("\n" + "=" * 60)
    print("📊 檢查結果總結")
    print("=" * 60)

    all_passed = True
    for category, result in results.items():
        status = "✅ 通過" if result["passed"] else "⚠️ 需要注意"
        print(f"{category:20} {status}")
        for item, status_text in result.get("items", {}).items():
            symbol = "✓" if status_text.get("ok") else "✗"
            print(f"  {symbol} {item:40} {status_text.get('message', '')}")

        if not result["passed"]:
            all_passed = False

    print("\n" + "=" * 60)
    if all_passed:
        print("✅ 所有檢查通過！應用已準備就緒。")
        print("\n下一步：")
        print("  1. 執行: start.bat")
        print("  2. 訪問: http://localhost:8000")
    else:
        print("⚠️ 部分檢查失敗，請查看上方的提示。")
    print("=" * 60 + "\n")


def check_environment():
    """檢查系統環境"""
    result = {"passed": True, "items": {}}

    # Python 版本
    py_version = f"{sys.version_info.major}.{sys.version_info.minor}"
    ok = sys.version_info >= (3, 8)
    result["items"]["Python 版本"] = {
        "ok": ok,
        "message": f"({py_version}) {'✓' if ok else '需要 3.8+'}",
    }

    # 虛擬環境
    in_venv = hasattr(sys, "real_prefix") or (
        hasattr(sys, "base_prefix") and sys.base_prefix != sys.prefix
    )
    result["items"]["虛擬環境"] = {
        "ok": in_venv,
        "message": "✓ 已激活" if in_venv else "⚠️ 未激活（不必須）",
    }

    # 當前目錄
    has_index = os.path.exists("index.html")
    result["items"]["項目目錄"] = {
        "ok": has_index,
        "message": "✓ 正確位置" if has_index else "✗ 位置不正確",
    }

    result["passed"] = all(
        item["ok"]
        for item in result["items"].values()
        if "not" not in item.get("message", "").lower()
    )
    return result


def check_files():
    """檢查必要文件"""
    result = {"passed": True, "items": {}}

    required_files = [
        "index.html",
        "styles.css",
        "script.js",
        "api_server.py",
        "main.py",
        "data_engine.py",
    ]

    for file in required_files:
        exists = os.path.exists(file)
        result["items"][file] = {
            "ok": exists,
            "message": "✓ 存在" if exists else "✗ 缺失",
        }
        if not exists:
            result["passed"] = False

    return result


def check_packages():
    """檢查 Python 套件"""
    result = {"passed": True, "items": {}}

    packages = [
        "flask",
        "flask_cors",
        "requests",
        "beautifulsoup4",
        "dotenv",
        "langchain",
    ]

    for package in packages:
        try:
            __import__(package)
            result["items"][package] = {"ok": True, "message": "✓ 已安裝"}
        except ImportError:
            result["items"][package] = {"ok": False, "message": "✗ 未安裝"}
            result["passed"] = False

    if not result["passed"]:
        print("\n    💡 提示：執行以下命令安裝缺失套件")
        print(
            "    pip install flask flask-cors requests beautifulsoup4 python-dotenv langchain"
        ),

    return result


def check_config():
    """檢查配置文件"""
    result = {"passed": True, "items": {}}

    # .env 文件
    has_env = os.path.exists(".env")
    result["items"][".env 文件"] = {
        "ok": has_env,
        "message": "✓ 存在" if has_env else "⚠️ 不存在（需要 API 密鑰）",
    }

    # requirements.txt
    has_req = os.path.exists("requirements.txt")
    result["items"]["requirements.txt"] = {
        "ok": has_req,
        "message": "✓ 存在" if has_req else "⚠️ 不存在",
    }

    # .env 內容檢查
    if has_env:
        with open(".env", "r") as f:
            content = f.read()
            has_key = "GEMINI_API_KEY=" in content or "API_KEY=" in content
            result["items"]["API 密鑰配置"] = {
                "ok": has_key,
                "message": "✓ 已配置" if has_key else "✗ 缺失",
            }
            if not has_key:
                result["passed"] = False

    return result


def check_ports():
    """檢查端口可用性"""
    result = {"passed": True, "items": {}}

    import socket

    def is_port_available(port):
        sock = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        try:
            sock.bind(("localhost", port))
            sock.close()
            return True
        except:
            return False

    ports = {"Flask API (5000)": 5000, "Web 伺服器 (8000)": 8000}

    for name, port in ports.items():
        available = is_port_available(port)
        result["items"][name] = {
            "ok": available,
            "message": "✓ 可用" if available else "✗ 被佔用",
        }
        if not available:
            result["passed"] = False

    if not result["passed"]:
        print("\n    💡 提示：某些端口被佔用")
        print("    Windows: netstat -ano | findstr :PORT")
        print("    Mac/Linux: lsof -i :PORT")

    return result


if __name__ == "__main__":
    try:
        check_installation()
    except Exception as e:
        print(f"❌ 檢查出錯: {e}")
        sys.exit(1)
