# AI 接入指南

SecFlow 的 AI 研判（Triage / Threat / Vuln / Report Agent）通过统一的 LLM
Provider 接入模型。**默认 mock 模式**可以零配置体验全流程，但真实研判需要
接入真实模型。本文档给出三种方式的完整配置与验证方法。

## 快速选择

| 方式 | 成本 | 隐私 | 能力 | 适合场景 |
|------|------|------|------|----------|
| `mock` | 免费 | — | 规则研判（有限） | 演示 / CI / 离线环境 |
| `ollama` | 免费 | 本地 | 良好 | 个人 / 内网安全运营 |
| `openai`(兼容) | 按量 | 云端 | 最强 | 生产 / 需要深度分析 |

## 方式一：Ollama（推荐入门）

```bash
# 安装 Ollama（Linux）
curl -fsSL https://ollama.com/install.sh | sh
ollama pull qwen2.5:7b        # 或 qwen2.5:14b / llama3.1:8b 等

# 确认服务
curl http://localhost:11434/api/tags
```

`.env` 配置：

```dotenv
LLM_PROVIDER=ollama
LLM_BASE_URL=http://host.docker.internal:11434   # 容器内访问宿主机；本机直跑用 http://localhost:11434
LLM_MODEL=qwen2.5:7b
```

重启：`docker compose up -d --build`（或重启 API/Worker 进程）。

## 方式二：OpenAI 兼容云端 API（DeepSeek / OpenAI / 通义等）

任意实现 `POST /v1/chat/completions` 的服务均可：

```dotenv
# DeepSeek 示例
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.deepseek.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=deepseek-chat

# OpenAI 示例
LLM_PROVIDER=openai
LLM_BASE_URL=https://api.openai.com/v1
LLM_API_KEY=sk-xxxxxxxxxxxxxxxx
LLM_MODEL=gpt-4o-mini
```

## 方式三：Mock 离线模式

```dotenv
LLM_PROVIDER=mock
```

确定性规则研判，无需网络与密钥；`datasets/evaluation/` 评测集用它也能全绿。

## 验证是否接入成功

```bash
# 1. 健康检查应返回 ok:true
curl http://localhost:8000/api/health/llm

# 2. 触发一次真实研判（force 会忽略旧结果重新调用模型）
TOKEN=$(curl -s -X POST http://localhost:8000/api/auth/login \
  -H 'Content-Type: application/json' -d '{"username":"admin","password":"Admin@123456"}' \
  | python3 -c "import sys,json;print(json.load(sys.stdin)['access_token'])")
IID=$(curl -s http://localhost:8000/api/incidents -H "Authorization: Bearer $TOKEN" \
  | python3 -c "import sys,json;print(json.load(sys.stdin)[0]['id'])")
curl -s -X POST "http://localhost:8000/api/incidents/$IID/analyze" \
  -H "Authorization: Bearer $TOKEN" -H 'Content-Type: application/json' \
  -d '{"force":true}' | python3 -m json.tool | grep -E "provider|classification|risk_level"
```

输出中 `"_provider": "openai"` / `"ollama"` 即表示真实模型已生效；
结果中的 `evidence_ids` 会绑定上下文中的真实证据（证据接地强制校验）。

## 前端引导

登录后进入 **Settings → AI 接入向导**：可查看当前配置、一键复制三种配置模板、
测试 AI 连接（调用 `/api/health/llm`）。

## 常见问题

| 现象 | 原因与解决 |
|------|-----------|
| `/api/health/llm` ok:false "Connection refused" | Ollama 未启动或地址不对（容器内用 host.docker.internal） |
| 401/403 错误 | API Key 错误或无余额 |
| 分析结果与之前一样 | 旧结果被缓存——用 `{"force": true}` 重新分析 |
| 模型返回非 JSON | 部分小模型不稳定——换更大模型（7B+），平台会自动重试修复一次 |
| 分析超时 | 调大 `LLM_TIMEOUT`（默认 120s） |
