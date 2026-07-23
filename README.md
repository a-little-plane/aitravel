# 人机协作决策实验平台 — H 组

> 研究二：人机协作决策实验平台的功能需求文档配套实现
> **本次仅交付 H 组（人类单独决策）；H+SOA、H+MOA 组预留分组字段但暂未实现执行界面。**

## 项目说明

本平台用于开展"智能体助理决策效能"的三组间对照实验。本次开发的是 H 组的完整实验流程：

1. **登录 / 注册** —— 采集人口统计学信息（手机号、昵称、年龄、性别、受教育程度等）
2. **自动随机分组** —— 注册时系统按 1:1:1 自动分配至 H / H+SOA / H+MOA，对用户**不可见**（单盲）
3. **演示页** —— 播放任务说明视频，需点击"我已理解任务要求"才能进入任务
4. **任务执行界面（H 组）** —— 顶部常驻任务栏与计时器；左侧搜索引擎；右侧文档编辑器
5. **任务后问卷** —— 两道主观题
6. **结束页** —— 致谢并退出

## 技术栈

| 层级 | 选型 |
| --- | --- |
| 后端 | Python 3 + Flask |
| 数据库 | MySQL 8.0 |
| 数据库驱动 | PyMySQL + DBUtils（连接池） |
| 模板引擎 | Jinja2 |
| 前端 | 原生 HTML + CSS（无构建工具，零依赖） |
| 编辑器 | VS Code 或 IntelliJ IDEA |

## 目录结构

```
E:\IDEA_project\ai_travel
├── app.py                  # Flask 启动入口
├── config.py               # 全局配置（数据库连接、实验参数等）
├── db.py                   # 数据库连接池
├── services.py             # 业务服务层
├── routes.py               # 路由层（蓝图）
├── init_db.py              # 数据库初始化脚本（已执行）
├── requirements.txt        # Python 依赖
├── static/
│   └── style.css           # 全局样式
└── templates/
    ├── base.html
    ├── login.html          # 登录
    ├── register.html       # 注册
    ├── demo.html           # 演示页
    ├── task_h.html         # H 组任务执行界面
    ├── task_placeholder.html   # 其他分组占位页
    ├── survey.html         # 问卷
    └── thanks.html         # 致谢
```

## 数据表

| 表名 | 用途 |
| --- | --- |
| `users` | 用户信息（含随机分组字段 `user_group`） |
| `demo_watch` | 演示观看记录（开始 / 结束 / 观看时长） |
| `task_session` | 任务执行会话（进入 / 提交 / 用时 / 文档内容） |
| `questionnaire` | 任务后问卷 |
| `behavior_log` | 行为日志（搜索、提交等所有动作） |

## 快速开始

### 1. 启动 MySQL

确保 MySQL 8.0 已启动，密码：`yzx111223`（已写入 `config.py`）

### 2. 初始化数据库（仅首次需要）

```powershell
cd E:\IDEA_project\ai_travel
python init_db.py
```

### 3. 安装依赖（如未安装）

```powershell
pip install -r requirements.txt
```

### 4. 启动应用

```powershell
python app.py
```

启动后访问：<http://127.0.0.1:5000>

## 实验参数（在 `config.py` 中可调）

- `TASK_DAYS = 3`  — 行程天数
- `TASK_BUDGET = 3000`  — 预算（元）
- `TASK_DESTINATION = "杭州"`  — 目的地
- `DEMO_VIDEO_URL`  — 演示视频地址

## 关于分组（单盲设计）

注册时 `services.create_user` 会以 1:1:1 概率把用户分到 `H` / `H_SOA` / `H_MOA` 三组，但前端界面**始终不展示分组信息**，符合需求文档中"分组信息对参与者不可见"的单盲要求。

`H+SOA` 和 `H+MOA` 组如需上线实现，仅需新增 `templates/task_soa.html` / `templates/task_moa.html` 并扩展 `routes.py` 中的 `task_page` 路由判断即可。

## 行为日志样例

| 动作标识 | 含义 |
| --- | --- |
| `register` | 完成注册 |
| `login` | 登录 |
| `demo_confirmed` | 演示页点击"我已理解任务要求" |
| `task_enter` | 进入任务执行界面 |
| `search` | 调用搜索引擎（`detail` 字段为搜索词） |
| `task_submit` | 提交任务结果（`detail` 为文档字符数） |
| `survey_submit` | 提交问卷 |
| `logout` | 退出登录 |
