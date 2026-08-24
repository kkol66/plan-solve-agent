# -*- coding: utf-8 -*-
"""
Plan-and-Solve 范式 · 智能行程规划助手（后端服务）

范式一句话：先画蓝图，再施工。
  - Planner（规划器）：把用户目标拆成一系列可执行的步骤列表
  - Executor（执行器）：严格按步骤逐一执行，把上一步结果传给下一步

结构：
  - backend/  : python 内置 http.server, 提供 POST /api/agent 接口
  - frontend/ : Vue2 单页, 输入城市/天数 → 展示规划步骤 + 执行结果

运行：
  pip install -r requirements.txt
  python app.py
然后浏览器打开 http://localhost:8000

注意：API Key 通过项目根目录 .env 提供（复制 .env.example 为 .env），
      切勿写入代码，也禁止提交到 git。
"""

import os
import re
import json
import ast
import requests
from openai import OpenAI
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer

BASE_DIR = os.path.dirname(os.path.abspath(__file__))   # backend/ 目录
ROOT_DIR = os.path.dirname(BASE_DIR)                     # 项目根目录


def load_env(path: str) -> None:
    """极简 .env 加载器: 把 .env 里的 KEY=VALUE 读入环境变量。"""
    if not os.path.exists(path):
        return
    with open(path, encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip().replace("\ufeff", "")  # 去掉可能存在的 UTF-8 BOM
            if key not in os.environ:  # 仅当环境变量未设置时才写入
                os.environ[key] = value.strip()


load_env(os.path.join(ROOT_DIR, ".env"))

LLM_API_KEY = os.getenv("LLM_API_KEY", "")
LLM_BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com")
LLM_MODEL = os.getenv("LLM_MODEL_ID", "deepseek-chat")


# ---------- LLM 客户端（DeepSeek，兼容 OpenAI 协议） ----------
class DeepSeekClient:
    def __init__(self):
        if not LLM_API_KEY:
            raise RuntimeError("缺少 LLM_API_KEY，请复制 .env.example 为 .env 并填写密钥。")
        self.model = LLM_MODEL
        self.client = OpenAI(api_key=LLM_API_KEY, base_url=LLM_BASE_URL)

    def think(self, messages, temperature=0.0):
        resp = self.client.chat.completions.create(
            model=self.model, messages=messages, temperature=temperature
        )
        return (resp.choices[0].message.content or "").strip()


# ---------- 工具：查询真实天气（wttr.in，无需密钥） ----------
def get_weather(city: str) -> str:
    try:
        url = f"https://wttr.in/{city}?format=j1&lang=zh"
        data = requests.get(url, timeout=10).json()
        cur = data["current_condition"][0]
        desc = cur["weatherDesc"][0]["value"]
        temp = cur["temp_C"]
        return f"{city}当前天气：{desc}，气温{temp}摄氏度"
    except Exception as e:
        return f"天气查询失败：{e}"


# ---------- 规划器 Planner ----------
PLANNER_PROMPT = """\
你是一个顶级的行程规划专家。请把用户的"旅行目标"分解成一个由多个独立步骤组成的行动计划。

要求：
- 每个步骤是既可独立执行、又按逻辑顺序排列的子任务
- 输出必须是 Python 列表格式，例如 ["步骤1", "步骤2", ...]
- 只输出列表本身，不要任何多余的解释

用户目标：{question}
"""


class Planner:
    def __init__(self, llm):
        self.llm = llm

    def plan(self, question):
        prompt = PLANNER_PROMPT.format(question=question)
        raw = self.llm.think([{"role": "user", "content": prompt}])
        m = re.search(r"\[.*\]", raw, re.DOTALL)
        if not m:
            return []
        try:
            plan = ast.literal_eval(m.group(0))
            return plan if isinstance(plan, list) else []
        except Exception:
            return []


# ---------- 执行器 Executor ----------
EXECUTOR_PROMPT = """\
你是一位顶级的行程规划执行专家。请严格按计划解决"当前步骤"，只输出该步骤的结果，不要多余解释。

# 用户目标：
{question}

# 完整计划：
{plan}

# 已完成的步骤与结果：
{history}

# 当前步骤：
{current_step}

请输出当前步骤的结果：
"""


class Executor:
    def __init__(self, llm):
        self.llm = llm

    def execute(self, question, plan):
        history = ""
        results = []
        last = ""
        for i, step in enumerate(plan):
            prompt = EXECUTOR_PROMPT.format(
                question=question,
                plan="\n".join(f"{j+1}. {s}" for j, s in enumerate(plan)),
                history=history or "无",
                current_step=step,
            )
            last = self.llm.think([{"role": "user", "content": prompt}])
            results.append({"step": step, "result": last})
            history += f"步骤{i+1}：{step}\n结果：{last}\n\n"
        return {"results": results, "answer": last}


# ---------- 组合为智能体 ----------
class PlanSolveAgent:
    def __init__(self, llm):
        self.planner = Planner(llm)
        self.executor = Executor(llm)

    def run(self, question):
        plan = self.planner.plan(question)
        if not plan:
            return {"plan": [], "results": [], "answer": "无法生成有效计划，请换个说法再试。"}
        exec_result = self.executor.execute(question, plan)
        return {
            "plan": plan,
            "results": exec_result["results"],
            "answer": exec_result["answer"],
        }


llm = DeepSeekClient()
agent = PlanSolveAgent(llm)


def run_plan_solve(city: str, days: str) -> dict:
    """根据城市和天数运行 Plan-and-Solve，返回结构化结果。"""
    weather = get_weather(city)
    try:
        nights = int(days) - 1
    except ValueError:
        nights = int(days) if days.isdigit() else 2
    question = (
        f"帮我规划{city}{days}天{nights}晚的旅行。"
        f"已知{city}当前天气：{weather}。"
        f"请给出包含景点、美食、住宿、交通的完整建议。"
    )
    result = agent.run(question)
    return {"weather": weather, "question": question, **result}


# ---------- HTTP 服务：托管页面 + 提供 API ----------
class Handler(BaseHTTPRequestHandler):
    def _cors(self):
        self.send_header("Access-Control-Allow-Origin", "*")
        self.send_header("Access-Control-Allow-Methods", "POST, GET, OPTIONS")
        self.send_header("Access-Control-Allow-Headers", "Content-Type")

    def _send_json(self, obj, status=200):
        body = json.dumps(obj, ensure_ascii=False).encode("utf-8")
        self.send_response(status)
        self.send_header("Content-Type", "application/json; charset=utf-8")
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_OPTIONS(self):
        self.send_response(200)
        self._cors()
        self.end_headers()

    def _serve_file(self, rel_path, content_type):
        full = os.path.normpath(os.path.join(ROOT_DIR, rel_path))
        if not full.startswith(ROOT_DIR):
            self._send_json({"error": "forbidden"}, status=403)
            return
        try:
            with open(full, "rb") as f:
                body = f.read()
        except FileNotFoundError:
            self._send_json({"error": "not found"}, status=404)
            return
        self.send_response(200)
        self.send_header("Content-Type", content_type)
        self.send_header("Content-Length", str(len(body)))
        self._cors()
        self.end_headers()
        self.wfile.write(body)

    def do_GET(self):
        if self.path in ("/", "/index.html"):
            self._serve_file("frontend/index.html", "text/html; charset=utf-8")
        elif self.path == "/lib/vue.js":
            self._serve_file("frontend/lib/vue.js", "application/javascript; charset=utf-8")
        else:
            self._send_json({"error": "not found"}, status=404)

    def do_POST(self):
        if self.path == "/api/agent":
            try:
                length = int(self.headers.get("Content-Length", 0))
                payload = json.loads(self.rfile.read(length).decode("utf-8"))
                city = payload.get("city", "").strip()
                days = payload.get("days", "").strip()
                if not city:
                    self._send_json({"error": "缺少 city"}, status=400)
                    return
                result = run_plan_solve(city, days or "3")
                self._send_json(result)
            except Exception as e:
                self._send_json({"error": f"服务器处理失败: {e}"}, status=500)
        else:
            self._send_json({"error": "not found"}, status=404)

    def log_message(self, fmt, *args):
        pass


def main():
    port = int(os.getenv("PORT", "8000"))
    server = ThreadingHTTPServer(("127.0.0.1", port), Handler)
    print(f"✅ 服务已启动：打开浏览器访问 http://localhost:{port}")
    print("   按 Ctrl+C 停止服务")
    server.serve_forever()


if __name__ == "__main__":
    main()
