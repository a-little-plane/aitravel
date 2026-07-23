"""
业务服务层：用户、分组、行为日志、问卷等
"""
import random
from datetime import datetime
from typing import Optional

from db import get_cursor


# ============================================================
# 用户服务
# ============================================================

def find_user_by_phone(phone: str) -> Optional[dict]:
    """根据手机号查找用户"""
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE phone = %s", (phone,))
        return cur.fetchone()


def get_user_by_id(user_id: int) -> Optional[dict]:
    with get_cursor() as cur:
        cur.execute("SELECT * FROM users WHERE id = %s", (user_id,))
        return cur.fetchone()


def create_user(
    phone: str,
    nickname: str,
    age: int,
    gender: str,
    education: str,
    computer_freq: str,
    ai_experience: str,
) -> int:
    """
    创建用户并自动随机分配到 H / H_SOA / H_MOA 三组
    当前项目仅实现 H 组页面，但分组逻辑按需求文档实现，便于将来扩展
    """
    user_group = _random_assign_group()
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO users
               (phone, nickname, age, gender, education,
                computer_freq, ai_experience, user_group)
               VALUES (%s,%s,%s,%s,%s,%s,%s,%s)""",
            (phone, nickname, age, gender, education,
             computer_freq, ai_experience, user_group),
        )
        return cur.lastrowid


def _random_assign_group() -> str:
    """
    1:1:1 比例随机分配
    返回: 'H' / 'H_SOA' / 'H_MOA'
    """
    return random.choice(["H", "H_SOA", "H_MOA"])


# ============================================================
# 演示观看记录
# ============================================================

def start_demo_session(user_id: int) -> int:
    """记录用户开始观看演示"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO demo_watch (user_id, start_time) VALUES (%s, NOW())",
            (user_id,),
        )
        return cur.lastrowid


def confirm_demo_understood(user_id: int) -> int:
    """
    用户点击"我已理解任务要求" → 记录结束时间与观看时长
    返回: 观看秒数
    """
    with get_cursor(commit=True) as cur:
        # 取最近一次未确认的会话
        cur.execute(
            """SELECT id, start_time FROM demo_watch
               WHERE user_id = %s AND confirmed = 0
               ORDER BY id DESC LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        demo_id = row["id"]
        cur.execute(
            """UPDATE demo_watch
               SET end_time = NOW(),
                   duration_sec = TIMESTAMPDIFF(SECOND, start_time, NOW()),
                   confirmed = 1
               WHERE id = %s""",
            (demo_id,),
        )
        # 顺便取回 duration
        cur.execute("SELECT duration_sec FROM demo_watch WHERE id = %s", (demo_id,))
        r = cur.fetchone()
        return r["duration_sec"] if r else 0


# ============================================================
# 任务执行
# ============================================================

def enter_task(user_id: int) -> int:
    """进入任务执行界面，创建新的任务会话（每次都新建，不复用旧会话）"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO task_session (user_id, enter_time) VALUES (%s, NOW())",
            (user_id,),
        )
        return cur.lastrowid


def close_unfinished_task_sessions(user_id: int):
    """关闭该用户所有未完成的任务会话（submit_time 为空）"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            """UPDATE task_session
               SET submit_time = NOW(),
                   total_sec = TIMESTAMPDIFF(SECOND, enter_time, NOW())
               WHERE user_id = %s AND submit_time IS NULL""",
            (user_id,),
        )


def get_active_task_session(user_id: int) -> Optional[dict]:
    """获取最新的未完成任务会话"""
    with get_cursor() as cur:
        cur.execute(
            """SELECT * FROM task_session
               WHERE user_id = %s AND submit_time IS NULL
               ORDER BY id DESC LIMIT 1""",
            (user_id,),
        )
        return cur.fetchone()


def submit_task_result(user_id: int, doc_content: str) -> int:
    """提交任务结果，计算用时"""
    with get_cursor(commit=True) as cur:
        cur.execute(
            """SELECT id, enter_time FROM task_session
               WHERE user_id = %s AND submit_time IS NULL
               ORDER BY id DESC LIMIT 1""",
            (user_id,),
        )
        row = cur.fetchone()
        if not row:
            return 0
        cur.execute(
            """UPDATE task_session
               SET submit_time = NOW(),
                   total_sec = TIMESTAMPDIFF(SECOND, enter_time, NOW()),
                   doc_content = %s
               WHERE id = %s""",
            (doc_content, row["id"]),
        )
        return row["id"]


# ============================================================
# 行为日志
# ============================================================

def log_behavior(user_id: int, action: str, detail: str = ""):
    with get_cursor(commit=True) as cur:
        cur.execute(
            "INSERT INTO behavior_log (user_id, action, detail) VALUES (%s,%s,%s)",
            (user_id, action, detail),
        )


# ============================================================
# 问卷
# ============================================================

def save_questionnaire(user_id: int, q1: str, q2: str):
    with get_cursor(commit=True) as cur:
        cur.execute(
            """INSERT INTO questionnaire (user_id, q1_answer, q2_answer)
               VALUES (%s,%s,%s)
               ON DUPLICATE KEY UPDATE
                 q1_answer=VALUES(q1_answer),
                 q2_answer=VALUES(q2_answer),
                 submit_time=NOW()""",
            (user_id, q1, q2),
        )


def has_submitted_survey(user_id: int) -> bool:
    with get_cursor() as cur:
        cur.execute("SELECT 1 FROM questionnaire WHERE user_id = %s LIMIT 1", (user_id,))
        return cur.fetchone() is not None
