"""
AI 服务层：抽象出统一的 chat 接口，支持 mock 和多种 OpenAI 兼容 API。

设计要点：
1. 默认 mock 模式（无外部依赖），保证页面立即可用。
2. 实现 OpenAI 兼容 chat 接口，切换模型只需修改 ai_config.json。
3. 配置按 mtime 缓存，无需重启服务。
4. 调用失败自动降级为 mock，避免单次网络抖动影响实验。
"""
import json
import os

import requests


_CONFIG_PATH = os.path.join(os.path.dirname(os.path.abspath(__file__)), "ai_config.json")
_CACHE = {"mtime": 0.0, "data": None}


def _load_config() -> dict:
    """读取 ai_config.json（按 mtime 缓存）"""
    try:
        mtime = os.path.getmtime(_CONFIG_PATH)
    except OSError:
        return {"provider": "mock", "providers": {}, "agent_prompts": {}}
    if _CACHE["mtime"] == mtime and _CACHE["data"] is not None:
        return _CACHE["data"]
    with open(_CONFIG_PATH, "r", encoding="utf-8") as f:
        data = json.load(f)
    _CACHE["mtime"] = mtime
    _CACHE["data"] = data
    return data


def get_active_provider_name() -> str:
    return _load_config().get("provider", "mock")


def get_agent_prompt(agent_name: str = "default") -> str:
    cfg = _load_config()
    prompts = cfg.get("agent_prompts", {})
    return prompts.get(agent_name, prompts.get("default", ""))


def get_status() -> dict:
    """返回当前 AI 状态，供前端展示 / 调试面板使用"""
    cfg = _load_config()
    name = cfg.get("provider", "mock")
    p = cfg.get("providers", {}).get(name, {})
    return {
        "provider": name,
        "type": p.get("type", "mock"),
        "model": p.get("model", ""),
        "api_key_set": bool(p.get("api_key", "").strip()),
        "base_url": p.get("base_url", ""),
        "description": p.get("description", ""),
    }


def chat(messages, agent_name: str = "default", timeout: float = 30.0) -> dict:
    """统一 chat 接口。
    :param messages: [{"role": "user"|"assistant"|"system", "content": "..."}, ...]
    :param agent_name: H_MOA 模式下用于选择 system prompt（A/B/C）
    :return: {"ok": bool, "content": str, "provider": str, "model": str, "mock": bool, "error": str}
    """
    cfg = _load_config()
    provider_name = cfg.get("provider", "mock")
    providers = cfg.get("providers", {})
    provider_cfg = providers.get(provider_name, {})
    ptype = provider_cfg.get("type", "mock")

    has_system = any(m.get("role") == "system" for m in messages)
    sys_prompt = get_agent_prompt(agent_name)
    if sys_prompt and not has_system:
        messages = [{"role": "system", "content": sys_prompt}] + messages

    if ptype == "mock":
        return _mock_response(messages, agent_name, provider_name)
    if ptype == "openai_compatible":
        api_key = provider_cfg.get("api_key", "").strip()
        if not api_key:
            return {
                "ok": True,
                "content": _mock_reply(messages, agent_name),
                "provider": provider_name,
                "model": provider_cfg.get("model", ""),
                "mock": True,
                "error": "API key 未配置，已降级为模拟回复（请在 ai_config.json 中填写）",
            }
        return _openai_chat(messages, provider_cfg, provider_name, timeout)
    return {
        "ok": False,
        "content": _mock_reply(messages, agent_name),
        "provider": provider_name,
        "model": "",
        "mock": True,
        "error": "未知 provider 类型: " + str(ptype),
    }


def _mock_response(messages, agent_name, provider_name) -> dict:
    return {
        "ok": True,
        "content": _mock_reply(messages, agent_name),
        "provider": provider_name,
        "model": "mock",
        "mock": True,
    }


def _mock_reply(messages, agent_name) -> str:
    user_msg = ""
    for m in reversed(messages):
        if m.get("role") == "user":
            user_msg = m.get("content", "").strip()
            break
    if not user_msg:
        return "请告诉我您想了解什么～"

    role_tips = {
        "A": "【行程规划·A】",
        "B": "【本地向导·B】",
        "C": "【交通预算·C】",
    }
    prefix = role_tips.get(agent_name, "【AI 助手】")

    if any(k in user_msg for k in ["吃", "餐厅", "美食", "小吃"]):
        return prefix + " 关于「" + user_msg + "」：推荐楼外楼（西湖醋鱼，人均 150）、知味观（小吃，人均 50）、外婆家（杭帮菜，人均 80）。"
    if any(k in user_msg for k in ["住", "酒店", "民宿", "住宿"]):
        return prefix + " 关于「" + user_msg + "」：西湖周边连锁酒店 300-500 元/晚；青旅 80-150 元/位；建议提前一周预订避开周末。"
    if any(k in user_msg for k in ["交通", "地铁", "打车", "公交"]):
        return prefix + " 关于「" + user_msg + "」：杭州地铁覆盖主要景点，建议办一张交通卡（押金 20 元）；打车 3 公里内起步价 11 元。"
    if any(k in user_msg for k in ["门票", "价格", "费用", "多少钱", "预算"]):
        return prefix + " 关于「" + user_msg + "」：西湖免费；灵隐寺 30 元；雷峰塔 40 元；建议提前在官方公众号预约。"
    if any(k in user_msg for k in ["行程", "攻略", "路线", "规划", "推荐"]):
        return (prefix + " 关于「" + user_msg + "」的 3 天建议：\n"
                "Day1：西湖（断桥→白堤→孤山→雷峰塔），晚上河坊街\n"
                "Day2：灵隐寺→飞来峰→龙井村，傍晚九溪烟树\n"
                "Day3：西溪湿地 或 宋城\n"
                "预算参考：门票+餐饮+交通人均 600-1000 元")
    return (prefix + "（模拟回复）我已收到您的问题：「" + user_msg + "」。\n"
            "当前为 Mock 模式，未调用真实 AI。在 ai_config.json 中配置 API key 后将获得基于大模型的详细答复。")


def _openai_chat(messages, provider_cfg, provider_name, timeout) -> dict:
    base_url = provider_cfg.get("base_url", "").rstrip("/")
    api_key = provider_cfg.get("api_key", "").strip()
    model = provider_cfg.get("model", "gpt-3.5-turbo")
    if not base_url:
        return {
            "ok": False,
            "content": _mock_reply(messages, "default"),
            "provider": provider_name,
            "model": model,
            "mock": True,
            "error": "base_url 未配置",
        }
    url = base_url + "/chat/completions"
    headers = {
        "Content-Type": "application/json",
        "Authorization": "Bearer " + api_key,
    }
    payload = {
        "model": model,
        "messages": messages,
        "temperature": 0.7,
    }
    try:
        resp = requests.post(url, json=payload, headers=headers, timeout=timeout)
        if resp.status_code != 200:
            return {
                "ok": False,
                "content": _mock_reply(messages, "default"),
                "provider": provider_name,
                "model": model,
                "mock": True,
                "error": "HTTP " + str(resp.status_code) + ": " + resp.text[:200],
            }
        data = resp.json()
        content = data["choices"][0]["message"]["content"]
        return {
            "ok": True,
            "content": content,
            "provider": provider_name,
            "model": model,
            "mock": False,
        }
    except Exception as e:
        return {
            "ok": False,
            "content": _mock_reply(messages, "default"),
            "provider": provider_name,
            "model": model,
            "mock": True,
            "error": "调用失败: " + str(e),
        }
