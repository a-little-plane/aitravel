"""
初始化数据库脚本：创建数据库 ai_travel 及全部表结构
"""
import pymysql

DB_CONFIG = {
    "host": "127.0.0.1",
    "port": 3306,
    "user": "root",
    "password": "yzx111223",
    "charset": "utf8mb4",
}

DB_NAME = "ai_travel"

SCHEMA_SQL = [
    # 用户表
    """
    CREATE TABLE IF NOT EXISTS users (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        phone           VARCHAR(20) NOT NULL UNIQUE COMMENT '手机号(登录账号)',
        nickname        VARCHAR(50) DEFAULT NULL COMMENT '昵称',
        age             INT DEFAULT NULL COMMENT '年龄',
        gender          VARCHAR(10) DEFAULT NULL COMMENT '性别',
        education       VARCHAR(20) DEFAULT NULL COMMENT '受教育程度',
        computer_freq   VARCHAR(30) DEFAULT NULL COMMENT '计算机使用频率',
        ai_experience   VARCHAR(30) DEFAULT NULL COMMENT 'AI工具使用经验',
        user_group      VARCHAR(10) NOT NULL DEFAULT 'H' COMMENT '随机分组:H / H_SOA / H_MOA',
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='用户表'
    """,
    # 演示观看记录表
    """
    CREATE TABLE IF NOT EXISTS demo_watch (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        start_time      DATETIME NOT NULL,
        end_time        DATETIME DEFAULT NULL,
        duration_sec    INT DEFAULT NULL COMMENT '演示观看时长(秒)',
        confirmed       TINYINT(1) NOT NULL DEFAULT 0 COMMENT '是否点击我已理解',
        INDEX idx_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='演示观看记录'
    """,
    # 任务执行记录表
    """
    CREATE TABLE IF NOT EXISTS task_session (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        enter_time      DATETIME NOT NULL COMMENT '进入执行界面时间',
        submit_time     DATETIME DEFAULT NULL COMMENT '提交任务结果时间',
        total_sec       INT DEFAULT NULL COMMENT '用时(秒)',
        doc_content     LONGTEXT COMMENT '文档编辑器最终内容(供后续分析)',
        INDEX idx_user (user_id)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务执行会话'
    """,
    # 问卷表
    """
    CREATE TABLE IF NOT EXISTS questionnaire (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id         BIGINT NOT NULL UNIQUE,
        q1_answer       TEXT COMMENT '问题1回答',
        q2_answer       TEXT COMMENT '问题2回答',
        submit_time     DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='任务后主观问卷'
    """,
    # 行为日志表
    """
    CREATE TABLE IF NOT EXISTS behavior_log (
        id              BIGINT AUTO_INCREMENT PRIMARY KEY,
        user_id         BIGINT NOT NULL,
        action          VARCHAR(50) NOT NULL COMMENT '动作标识',
        detail          TEXT COMMENT '附加信息(如搜索词、文档快照等)',
        created_at      DATETIME NOT NULL DEFAULT CURRENT_TIMESTAMP,
        INDEX idx_user (user_id),
        INDEX idx_action (action)
    ) ENGINE=InnoDB DEFAULT CHARSET=utf8mb4 COMMENT='行为日志'
    """,
]


def main():
    conn = pymysql.connect(**DB_CONFIG)
    try:
        with conn.cursor() as cur:
            # 创建数据库
            cur.execute(
                f"CREATE DATABASE IF NOT EXISTS {DB_NAME} "
                f"DEFAULT CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci"
            )
            print(f"[OK] 数据库 {DB_NAME} 已就绪")
        conn.commit()

        # 切换到目标库
        conn.select_db(DB_NAME)
        with conn.cursor() as cur:
            for sql in SCHEMA_SQL:
                cur.execute(sql)
            print(f"[OK] 共 {len(SCHEMA_SQL)} 张表已就绪")
        conn.commit()
    finally:
        conn.close()


if __name__ == "__main__":
    main()
