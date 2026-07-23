"""全局配置"""
import os


class Config:
    # Flask
    SECRET_KEY = os.environ.get("AI_TRAVEL_SECRET", "ai_travel_experiment_secret_key_2026")

    # 数据库
    DB_HOST = os.environ.get("DB_HOST", "127.0.0.1")
    DB_PORT = int(os.environ.get("DB_PORT", 3306))
    DB_USER = os.environ.get("DB_USER", "root")
    DB_PASSWORD = os.environ.get("DB_PASSWORD", "yzx111223")
    DB_NAME = os.environ.get("DB_NAME", "ai_travel")

    # 启动
    HOST = "0.0.0.0"
    PORT = 5000
    DEBUG = True

    # 实验参数（按需求文档：3 日、3000 元）
    TASK_DAYS = 3
    TASK_BUDGET = 3000
    TASK_DESTINATION = "杭州"
    TASK_INSTRUCTION = (
        f"帮我规划一个{TASK_DESTINATION}{TASK_DAYS}日游行程，预算{TASK_BUDGET}元。"
        f"要求：搜索当前{TASK_DESTINATION}历史文化景点及其门票价格；"
        f"生成一份Word格式的行程表。"
    )

    # 演示视频（占位）
    DEMO_VIDEO_URL = (
        "https://www.w3.org/2010/05/sintel/trailer.mp4"
    )
