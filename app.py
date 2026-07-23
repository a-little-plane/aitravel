"""
人机协作决策实验平台 — 启动入口
（H 组：人类单独决策，无 AI 助理；H+SOA、H+MOA 暂未实现）

启动:  python app.py
默认地址: http://127.0.0.1:5000
"""
from flask import Flask, redirect, url_for, session

from config import Config
from db import init_pool, close_pool
from routes import auth_bp, demo_bp, task_bp, survey_bp

app = Flask(__name__)
app.config.from_object(Config)

# 注册蓝图
app.register_blueprint(auth_bp)
app.register_blueprint(demo_bp)
app.register_blueprint(task_bp)
app.register_blueprint(survey_bp)


@app.route("/")
def index():
    # 实验平台：根路径直接进入登录页
    # 注册页(/register)保留可访问，但不作为默认入口
    session.clear()
    return redirect(url_for("auth.login_page"))


@app.teardown_appcontext
def _teardown(exception=None):
    # 使用连接池，不需要在每次请求关闭连接
    pass


if __name__ == "__main__":
    init_pool()
    try:
        print("=" * 60)
        print(" 人机协作决策实验平台 — H 组")
        print(f" 访问地址: http://{Config.HOST}:{Config.PORT}")
        print("=" * 60)
        app.run(host=Config.HOST, port=Config.PORT, debug=Config.DEBUG)
    finally:
        close_pool()
