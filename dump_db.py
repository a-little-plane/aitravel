"""查看当前数据库中的全部记录（便于核对实验数据）"""
import pymysql

conn = pymysql.connect(
    host="127.0.0.1", port=3306, user="root",
    password="yzx111223", database="ai_travel",
    cursorclass=pymysql.cursors.DictCursor,
)

tables = ["users", "demo_watch", "task_session", "questionnaire", "behavior_log"]

try:
    with conn.cursor() as cur:
        for t in tables:
            cur.execute(f"SELECT COUNT(*) AS n FROM {t}")
            n = cur.fetchone()["n"]
            print(f"\n========== {t}  ({n} rows) ==========")
            cur.execute(f"SELECT * FROM {t} ORDER BY id DESC LIMIT 5")
            for row in cur.fetchall():
                # 截断长文本
                row_disp = {
                    k: (str(v)[:60] + "..." if isinstance(v, str) and len(v) > 60 else v)
                    for k, v in row.items()
                }
                print(row_disp)
finally:
    conn.close()
