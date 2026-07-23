"""
路由层：注册蓝图，提供登录、注册、演示、任务、问卷等接口
"""
from functools import wraps
import os
import re
import time
from datetime import datetime

import requests as http_requests
from bs4 import BeautifulSoup

from flask import (
    Blueprint, render_template, request, redirect, url_for,
    session, jsonify, flash,
)

import services
import ai_service
from config import Config


# 登录拦截
def login_required(fn):
    @wraps(fn)
    def wrapper(*args, **kwargs):
        if "user_id" not in session:
            return redirect(url_for("auth.login_page"))
        return fn(*args, **kwargs)
    return wrapper


# ============================================================
# 认证模块：登录 + 注册
# ============================================================
auth_bp = Blueprint("auth", __name__, url_prefix="")

PHONE_RE = __import__("re").compile(r"^1[3-9]\d{9}$")


@auth_bp.route("/login", methods=["GET"])
def login_page():
    # 始终展示登录页，不自动跳转
    return render_template("login.html")


@auth_bp.route("/login", methods=["POST"])
def login_post():
    phone = (request.form.get("phone") or "").strip()
    if not PHONE_RE.match(phone):
        flash("请输入有效的11位手机号", "error")
        return render_template("login.html", phone=phone)

    user = services.find_user_by_phone(phone)
    if not user:
        flash("该手机号尚未注册，请先注册", "error")
        return render_template("login.html", phone=phone)

    session.clear()
    session["user_id"] = user["id"]
    session["phone"] = user["phone"]
    services.log_behavior(user["id"], "login", phone)
    return redirect(url_for("demo.demo_page"))


@auth_bp.route("/register", methods=["GET"])
def register_page():
    return render_template("register.html")


@auth_bp.route("/register", methods=["POST"])
def register_post():
    phone = (request.form.get("phone") or "").strip()
    nickname = (request.form.get("nickname") or "").strip()
    age_raw = (request.form.get("age") or "").strip()
    gender = (request.form.get("gender") or "").strip()
    education = (request.form.get("education") or "").strip()
    computer_freq = (request.form.get("computer_freq") or "").strip()
    ai_experience = (request.form.get("ai_experience") or "").strip()

    # 校验
    errors = []
    if not PHONE_RE.match(phone):
        errors.append("手机号格式不正确")
    if not nickname:
        errors.append("请输入昵称")
    if not age_raw.isdigit() or not (10 <= int(age_raw) <= 100):
        errors.append("年龄需为 10-100 之间的整数")
    if gender not in ("男", "女"):
        errors.append("请选择性别")
    if education not in ("大专", "本科", "硕士", "博士"):
        errors.append("请选择受教育程度")
    if errors:
        for e in errors:
            flash(e, "error")
        return render_template(
            "register.html",
            phone=phone, nickname=nickname, age=age_raw,
            gender=gender, education=education,
            computer_freq=computer_freq, ai_experience=ai_experience,
        )

    # 是否已注册
    if services.find_user_by_phone(phone):
        flash("该手机号已注册，请直接登录", "error")
        return render_template("register.html", phone=phone)

    user_id = services.create_user(
        phone=phone,
        nickname=nickname,
        age=int(age_raw),
        gender=gender,
        education=education,
        computer_freq=computer_freq or "未填写",
        ai_experience=ai_experience or "未填写",
    )
    # 注册成功后直接进入演示页（跳过登录）
    session.clear()
    session["user_id"] = user_id
    session["phone"] = phone
    services.log_behavior(user_id, "register", "group_assigned")
    services.log_behavior(user_id, "login_after_register", phone)
    return redirect(url_for("demo.demo_page"))


@auth_bp.route("/logout")
def logout():
    if session.get("user_id"):
        services.log_behavior(session["user_id"], "logout")
    session.clear()
    return redirect(url_for("auth.login_page"))


# ============================================================
# 演示页
# ============================================================
demo_bp = Blueprint("demo", __name__, url_prefix="/demo")


@demo_bp.route("/", methods=["GET"])
@login_required
def demo_page():
    user = services.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login_page"))
    # 开始观看演示
    services.start_demo_session(user["id"])
    return render_template(
        "demo.html",
        user=user,
        video_url=Config.DEMO_VIDEO_URL,
        instruction=Config.TASK_INSTRUCTION,
    )


@demo_bp.route("/confirm", methods=["POST"])
@login_required
def confirm_understood():
    user_id = session["user_id"]
    duration = services.confirm_demo_understood(user_id)
    services.log_behavior(user_id, "demo_confirmed", f"watched_{duration}s")
    # 进入任务执行界面（task_page 会自动创建新会话）
    return redirect(url_for("task.task_page"))


# ============================================================
# 任务执行界面（H 组）
# ============================================================
task_bp = Blueprint("task", __name__, url_prefix="/task")


@task_bp.route("/", methods=["GET"])
@login_required
def task_page():
    user = services.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login_page"))

    # 每次打开都创建新的任务会话：先关闭旧的未完成会话，再新建
    services.close_unfinished_task_sessions(user["id"])
    services.enter_task(user["id"])
    task = services.get_active_task_session(user["id"])
    services.log_behavior(user["id"], "task_enter", f"group={user['user_group']}")

    # 按 user_group 分发到对应模板
    group = user["user_group"]
    if group == "H":
        template_name = "task_h.html"
    elif group == "H_SOA":
        template_name = "task_soa.html"
    elif group == "H_MOA":
        template_name = "task_moa.html"
    else:
        return render_template(
            "task_placeholder.html",
            user=user,
            message=f"您当前所属分组为 {group}，对应执行界面暂未上线",
        )

    return render_template(
        template_name,
        user=user,
        task=task,
        instruction=Config.TASK_INSTRUCTION,
        ai_status=ai_service.get_status(),
    )


@task_bp.route("/chat", methods=["POST"])
@login_required
def chat():
    """AI 对话接口：H_SOA / H_MOA 共用"""
    user_id = session["user_id"]
    agent = (request.form.get("agent") or "default").strip()
    message = (request.form.get("message") or "").strip()

    if not message:
        return jsonify({"ok": False, "error": "消息内容为空"})

    # agent 合法性校验
    if agent not in ("default", "A", "B", "C"):
        agent = "default"

    # H 组不应该调用此接口（防止越权）
    user = services.get_user_by_id(user_id)
    if not user or user["user_group"] == "H":
        return jsonify({"ok": False, "error": "当前分组不支持 AI 对话"})

    # 行为日志：先记用户消息
    services.log_behavior(
        user_id, "ai_chat_user",
        f"group={user['user_group']};agent={agent};len={len(message)};msg={message[:80]}"
    )

    # 调用 AI
    result = ai_service.chat(
        messages=[{"role": "user", "content": message}],
        agent_name=agent,
        timeout=30.0,
    )

    # 行为日志：记 AI 回复
    services.log_behavior(
        user_id, "ai_chat_ai",
        f"group={user['user_group']};agent={agent};provider={result.get('provider')};mock={result.get('mock')};len={len(result.get('content', ''))}"
    )

    return jsonify(result)


@task_bp.route("/ai-status", methods=["GET"])
def ai_status():
    """公开接口：返回当前 AI 配置状态（前端角标用）"""
    return jsonify(ai_service.get_status())


@task_bp.route("/search", methods=["POST"])
@login_required
def search():
    """搜索引擎：DuckDuckGo 为主，Bing 为兜底"""
    keyword = (request.form.get("keyword") or "").strip()
    user_id = session["user_id"]
    services.log_behavior(user_id, "search", keyword)
    if not keyword:
        return jsonify({"ok": False, "error": "请输入搜索关键词"})

    results = _ddg_search(keyword)
    # DuckDuckGo 无结果时，自动用 Bing 兜底
    if len(results) <= 1:
        results = _bing_search(keyword)
    return jsonify({"ok": True, "results": results, "keyword": keyword, "count": len(results)})


def _ddg_search(keyword: str, num: int = 10) -> list:
    """
    抓取 DuckDuckGo 搜索结果页并解析出标题、链接、摘要
    DuckDuckGo 对服务器端请求友好，中文搜索结果质量高
    """
    from urllib.parse import unquote, parse_qs, urlparse

    url = "https://html.duckduckgo.com/html/"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    params = {"q": keyword}

    try:
        resp = http_requests.get(url, params=params, headers=headers, timeout=10)
        resp.encoding = "utf-8"
    except Exception as e:
        return []

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    # DuckDuckGo 结果容器：div.result 或 div.web-result
    for item in soup.select("div.result, div.web-result"):
        # 标题
        title_tag = item.select_one("a.result__a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)

        # 链接：DuckDuckGo 会将真实 URL 包装在跳转链接中
        raw_link = title_tag.get("href", "")
        link = raw_link
        if "uddg=" in raw_link:
            parsed = urlparse(raw_link)
            qs = parse_qs(parsed.query)
            if "uddg" in qs:
                link = unquote(qs["uddg"][0])

        # 摘要
        snippet = ""
        snippet_node = item.select_one("a.result__snippet") or item.select_one("div.result__snippet")
        if snippet_node:
            snippet = snippet_node.get_text(strip=True)

        if title:
            results.append({
                "title": title,
                "url": link,
                "snippet": snippet or "（无摘要）",
            })

    return results[:num]


def _bing_search(keyword: str, num: int = 10) -> list:
    """
    抓取必应搜索结果页并解析（作为 DuckDuckGo 的兜底）
    """
    url = "https://www.bing.com/search"
    headers = {
        "User-Agent": (
            "Mozilla/5.0 (Windows NT 10.0; Win64; x64) "
            "AppleWebKit/537.36 (KHTML, like Gecko) "
            "Chrome/120.0.0.0 Safari/537.36"
        ),
        "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,*/*;q=0.8",
        "Accept-Language": "zh-CN,zh;q=0.9,en;q=0.8",
    }
    params = {"q": keyword, "count": str(num), "setlang": "zh-CN"}

    try:
        resp = http_requests.get(url, params=params, headers=headers, timeout=10)
        resp.encoding = "utf-8"
    except Exception as e:
        return [{"title": "搜索请求失败", "url": "", "snippet": f"网络错误: {e}"}]

    soup = BeautifulSoup(resp.text, "html.parser")
    results = []

    for item in soup.select("li.b_algo"):
        title_tag = item.select_one("h2 a")
        if not title_tag:
            continue
        title = title_tag.get_text(strip=True)
        link = title_tag.get("href", "")

        snippet = ""
        snippet_node = item.select_one("div.b_caption p") or item.select_one("p")
        if snippet_node:
            snippet = snippet_node.get_text(strip=True)
        if not snippet:
            full_text = item.get_text(separator=" ", strip=True)
            snippet = full_text.replace(title, "").strip()[:200]

        if title:
            results.append({
                "title": title,
                "url": link,
                "snippet": snippet or "（无摘要）",
            })

    if not results:
        results.append({
            "title": "未找到相关结果",
            "url": "",
            "snippet": f"搜索「{keyword}」未返回结果，请尝试更换关键词。"
        })

    return results[:num]


@task_bp.route("/submit", methods=["POST"])
@login_required
def submit_task():
    user_id = session["user_id"]
    doc_content = request.form.get("doc_content", "")
    services.log_behavior(user_id, "task_submit", f"len={len(doc_content)}")
    services.submit_task_result(user_id, doc_content)
    return redirect(url_for("survey.survey_page"))


@task_bp.route("/save", methods=["POST"])
@login_required
def save_doc():
    """将文档内容保存为 HTML 文件到服务器本地（供实验数据收集）"""
    user_id = session["user_id"]
    doc_content = request.form.get("doc_content", "")
    doc_format = request.form.get("format", "html")  # html / txt

    # 保存目录：项目下的 saved_docs/
    save_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "saved_docs")
    os.makedirs(save_dir, exist_ok=True)

    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    ext = "html" if doc_format == "html" else "txt"
    filename = f"user{user_id}_{timestamp}.{ext}"
    filepath = os.path.join(save_dir, filename)

    if doc_format == "html":
        full_html = (
            "<!DOCTYPE html>\n<html>\n<head>\n<meta charset='utf-8'>\n"
            f"<title>行程规划 - 用户{user_id}</title>\n</head>\n<body>\n"
            f"{doc_content}\n</body>\n</html>"
        )
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_html)
    else:
        # 纯文本：去除 HTML 标签
        plain = re.sub(r"<[^>]+>", "", doc_content)
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(plain)

    services.log_behavior(user_id, "doc_save", f"{filename} ({ext})")
    return jsonify({
        "ok": True,
        "filename": filename,
        "filepath": filepath,
        "message": f"文档已保存到服务器：{filename}"
    })


# ============================================================
# 问卷
# ============================================================
survey_bp = Blueprint("survey", __name__, url_prefix="/survey")


@survey_bp.route("/", methods=["GET"])
@login_required
def survey_page():
    user = services.get_user_by_id(session["user_id"])
    if not user:
        session.clear()
        return redirect(url_for("auth.login_page"))
    return render_template("survey.html", user=user)


@survey_bp.route("/submit", methods=["POST"])
@login_required
def submit_survey():
    user_id = session["user_id"]
    q1 = (request.form.get("q1") or "").strip()
    q2 = (request.form.get("q2") or "").strip()
    if not q1 or not q2:
        flash("请完整填写问卷中的两项", "error")
        return redirect(url_for("survey.survey_page"))
    services.save_questionnaire(user_id, q1, q2)
    services.log_behavior(user_id, "survey_submit")
    return render_template("thanks.html", user=services.get_user_by_id(user_id))
