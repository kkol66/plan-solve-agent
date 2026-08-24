# 🧭 行程规划助手 · Plan-and-Solve Agent

一个基于大语言模型（DeepSeek）的 **Plan-and-Solve 范式智能体**，用于智能规划旅行行程。
它不像普通聊天机器人那样"想到哪说到哪"，而是**先规划一张步骤清单，再一步步执行**，让复杂任务更有条理、更稳定。

> 本项目是《Hello-Agents》第 4 章「Plan-and-Solve 范式」的实战实现，并配套了完整的前端界面。

---

## ✨ 核心能力

- 🗺️ **先规划，后执行**：Planner 先把旅行目标拆成清晰的步骤清单，Executor 再严格按清单逐一完成
- 🌤️ **真实天气**：通过免费的 wttr.in 获取实时天气，作为行程规划的上下文依据
- 📋 **可视化过程**：前端清晰展示"规划步骤 → 逐步执行 → 最终建议"的完整链路
- 🖥️ **前后端分离**：Vue 前端负责交互展示，Python 后端提供智能体能力
- 🔐 **安全密钥管理**：API Key 通过 `.env` 环境变量注入，不写入代码、不进仓库

---

## 🧠 工作原理（Plan-and-Solve 范式）

如果说 **ReAct** 是"走一步看一步"的侦探，那么 **Plan-and-Solve** 就是"先画蓝图再施工"的建筑师。

```
① 规划（Planner）  把用户目标拆成结构化的步骤列表 ["步骤1", "步骤2", ...]
② 执行（Executor）  严格按列表逐条执行，把上一步结果传给下一步
③ 合成             综合所有步骤，得出最终答案
```

**核心区别**：ReAct 靠"观察结果"随时调整方向；Plan-and-Solve 则**先把步骤写死成清单**，再按部就班执行，适合需要长远规划、步骤清晰的复杂任务。

---

## 🏗️ 技术栈

| 层 | 技术 |
|---|---|
| 前端 | Vue 2 · 本地引入（无 CDN，可完全离线） |
| 后端 | Python 3 · 标准库 `http.server`（零 Web 框架依赖） |
| LLM | DeepSeek（兼容 OpenAI Chat Completions 协议） |
| 真实数据 | wttr.in（免费天气，无需密钥） |
| 依赖 | `requests` · `openai` |

---

## 📁 项目结构

```
plan-solve-agent/
├── backend/
│   └── app.py              # 后端：Planner + Executor + API + 静态托管
├── frontend/
│   ├── index.html          # Vue2 前端：输入城市/天数 → 展示规划过程
│   └── lib/
│       └── vue.js          # 本地 Vue 2.7.16（离线可用）
├── .env.example            # 环境变量模板（复制为 .env 后填写）
├── .env                    # 本地密钥（仅本机使用，不进仓库）
├── .gitignore
└── requirements.txt
```

---

## 🚀 快速开始

### 1. 安装依赖
```bash
pip install -r requirements.txt
```

### 2. 配置密钥
```bash
# Windows
copy .env.example .env
# macOS / Linux
cp .env.example .env
```

编辑 `.env`，填入你的 DeepSeek 密钥：
```ini
LLM_API_KEY=sk-你的DeepSeek密钥
LLM_MODEL_ID=deepseek-chat
LLM_BASE_URL=https://api.deepseek.com
```
> 密钥获取：https://platform.deepseek.com

### 3. 启动服务
```bash
cd backend
python app.py
```

### 4. 打开页面
访问 **http://localhost:8000**，输入城市（如"厦门"）和天数，点击"开始规划"。

---

## 🎬 使用示例

| 输入 | Agent 会做的事 |
|---|---|
| 城市：厦门，天数：3 | 查询实时天气 → 规划"查景点/排行程/订住宿/吃美食"等步骤 → 逐条执行 → 给出完整建议 |
| 城市：北京，天数：2 | 同上，根据北京实际情况生成对应行程 |

> 页面会清晰展示"📋 规划步骤 → ▶️ 逐步执行 → ✅ 最终建议"整个链路，
> 直观体会 Plan-and-Solve"先谋后动"的思维方式。

---

## 🔐 安全说明

- 所有 API 密钥通过 `.env` 文件或系统环境变量注入，**代码中不含任何密钥**
- `.env` 仅用于本机，请勿分享或提交真实密钥

---

## 📜 License

MIT
