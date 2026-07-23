"""
端到端冒烟测试：覆盖登录→注册→演示→任务→问卷全流程
需要先启动 app.py 并监听在 5000 端口
"""
import re
import time
import requests

BASE = "http://127.0.0.1:5000"


def must_ok(resp, *codes):
    if resp.status_code not in codes:
        raise AssertionError(
            f"unexpected status {resp.status_code} @ {resp.url}\n"
            f"body: {resp.text[:300]}"
        )
    return resp


def main():
    s = requests.Session()

    # 1. 根路径 → 跳登录
    r = must_ok(s.get(BASE + "/", allow_redirects=False), 302)
    print(f"[1] GET /  -> {r.status_code} -> {r.headers.get('Location')}")

    # 2. 登录页
    r = must_ok(s.get(BASE + "/login"), 200)
    assert "登录界面" in r.text
    assert 'name="phone"' in r.text
    print("[2] GET /login -> 200  含'登录界面'与手机号输入框")

    # 3. 未注册手机号登录失败
    r = must_ok(s.post(BASE + "/login", data={"phone": "13900000001"}, allow_redirects=True), 200)
    assert "尚未注册" in r.text
    print("[3] POST /login 未注册手机号 -> 200 + 提示尚未注册")

    # 4. 注册页
    r = must_ok(s.get(BASE + "/register"), 200)
    assert "注册界面" in r.text
    for k in ("phone", "nickname", "age", "gender", "education",
              "computer_freq", "ai_experience"):
        assert f'name="{k}"' in r.text, f"register 缺字段 {k}"
    print("[4] GET /register -> 200  含全部注册字段")

    # 5. 提交注册（用时间戳保证手机号唯一）
    phone = f"138{int(time.time()) % 100000000:08d}"
    payload = {
        "phone": phone,
        "nickname": "测试同学",
        "age": "23",
        "gender": "男",
        "education": "本科",
        "computer_freq": "每天",
        "ai_experience": "偶尔使用",
    }
    r = must_ok(s.post(BASE + "/register", data=payload, allow_redirects=False), 302)
    assert r.headers.get("Location", "").endswith("/login")
    print(f"[5] POST /register -> 302 -> {r.headers.get('Location')}")

    # 6. 登录成功
    r = must_ok(s.post(BASE + "/login", data={"phone": payload["phone"]},
                       allow_redirects=False), 302)
    assert "/demo" in r.headers.get("Location", "")
    print(f"[6] POST /login -> 302 -> {r.headers.get('Location')}")

    # 7. 演示页
    r = must_ok(s.get(BASE + "/demo/"), 200)
    assert "演示界面" in r.text
    assert "我已理解任务要求" in r.text
    assert "<video" in r.text
    print("[7] GET /demo/ -> 200  含视频与确认按钮")

    # 8. 确认理解
    r = must_ok(s.post(BASE + "/demo/confirm", allow_redirects=False), 302)
    assert "/task" in r.headers.get("Location", "")
    print(f"[8] POST /demo/confirm -> 302 -> {r.headers.get('Location')}")

    # 8.5 强制把测试用户设为 H 组（H 组页面是本次交付重点）
    import pymysql
    conn = pymysql.connect(
        host="127.0.0.1", port=3306, user="root",
        password="yzx111223", database="ai_travel",
    )
    with conn.cursor() as cur:
        cur.execute("UPDATE users SET user_group='H' WHERE phone=%s", (phone,))
    conn.commit()
    conn.close()
    print("[8.5] 强制设置 user_group='H'（测试需要）")

    # 9. 任务页
    r = must_ok(s.get(BASE + "/task/"), 200)
    assert "百度一下" in r.text
    assert "内置的文本编辑器" in r.text
    assert "提交任务结果" in r.text
    assert "帮我规划一个杭州3日游行程" in r.text
    print("[9] GET /task/ -> 200  含搜索/编辑器/提交按钮/任务说明")

    # 10. 搜索接口
    r = must_ok(s.post(BASE + "/task/search", data={"keyword": "西湖"}), 200)
    js = r.json()
    assert js.get("ok") is True
    assert len(js.get("results", [])) >= 1
    print(f"[10] POST /task/search -> 200 keyword='{js.get('keyword')}' results={len(js['results'])}")

    # 11. 提交任务
    doc = "杭州3日游行程：\n第1天：西湖 + 雷峰塔\n第2天：灵隐寺 + 飞来峰\n第3天：宋城"
    r = must_ok(s.post(BASE + "/task/submit", data={"doc_content": doc},
                       allow_redirects=False), 302)
    assert "/survey" in r.headers.get("Location", "")
    print(f"[11] POST /task/submit -> 302 -> {r.headers.get('Location')}")

    # 12. 问卷页
    r = must_ok(s.get(BASE + "/survey/"), 200)
    assert "问卷" in r.text and 'name="q1"' in r.text and 'name="q2"' in r.text
    print("[12] GET /survey/ -> 200  含 q1/q2 输入项")

    # 13. 提交问卷
    r = must_ok(s.post(BASE + "/survey/submit",
                       data={"q1": "整体体验流畅", "q2": "希望增加更多景点信息"},
                       allow_redirects=True), 200)
    assert "感谢您参与" in r.text
    print("[13] POST /survey/submit -> 200 含致谢页")

    # 14. 退出
    r = must_ok(s.get(BASE + "/logout", allow_redirects=False), 302)
    assert r.headers.get("Location", "").endswith("/login")
    print(f"[14] GET /logout -> 302 -> {r.headers.get('Location')}")

    # 15. 重复手机号注册应被拒
    r = must_ok(s.post(BASE + "/register", data=payload), 200)
    assert "已注册" in r.text
    print(f"[15] 重复手机号注册 -> 200 含'已注册'提示")

    print("\nALL TESTS PASSED")


if __name__ == "__main__":
    main()
