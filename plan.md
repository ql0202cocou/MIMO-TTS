# MIMO-TTS v2.5 集成开源阅读（Legado）方案

## 项目概述

制作一个能在 Debian 12 中部署的 Docker 镜像，作为中间件桥梁，将开源阅读（Legado）的自定义 TTS 朗读引擎请求转发到小米 MIMO-TTS v2.5 的 Chat Completions API，提供高质量、自然的语音朗读体验。

支持多种语言和声音风格，满足不同用户的需求。

---

## 系统架构

```
┌──────────────────┐        HTTP         ┌──────────────────────┐    Chat Completions API     ┌─────────────────────────┐
│                  │  ──────────────────> │                      │  ────────────────────────> │                         │
│  Legado (Android)│                      │  Docker 中间件服务    │                            │  小米 MIMO-TTS v2.5 API  │
│  开源阅读 App     │  <────────────────── │  (Debian 12)         │  <──────────────────────── │  api.xiaomimimo.com     │
│                  │     音频流(MP3/WAV)   │                      │     Base64 音频数据         │                         │
└──────────────────┘                      └──────────────────────┘                            └─────────────────────────┘
```

---

## 技术选型

| 组件 | 技术方案 | 说明 |
|------|---------|------|
| HTTP 服务框架 | Python + FastAPI | 轻量、高性能、异步支持好 |
| MIMO-TTS 客户端 | openai Python SDK | MIMO API 兼容 OpenAI SDK 格式 |
| 容器化 | Docker (Debian 12 base) | 轻量镜像，基于 python:3.11-slim-bookworm |
| 配置管理 | 环境变量 + .env 文件 | 简单灵活，便于 Docker 部署 |
| 音频格式 | WAV → MP3 转换 | MIMO 返回 WAV，转为 MP3 供 Legado 使用 |

---

## MIMO-TTS v2.5 官方 API 规范

> 参考文档：https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5

### ⚠️ 重要说明

MIMO-TTS v2.5 **不是**标准的 OpenAI TTS API（`/v1/audio/speech`），而是使用 **Chat Completions API**（`/v1/chat/completions`）。这是本方案的核心差异。

### API 端点

```
POST https://api.xiaomimimo.com/v1/chat/completions
```

### 认证方式

```
api-key: <MIMO_API_KEY>
```

### 支持的模型

| 模型名称 | 模型 ID | 功能 | 说明 |
|---------|---------|------|------|
| MiMo-V2.5-TTS | `mimo-v2.5-tts` | 使用内置高质量音色合成语音 | 支持唱歌模式；不支持声音设计和声音克隆 |
| MiMo-V2.5-TTS-VoiceDesign | `mimo-v2.5-tts-voicedesign` | 通过文字描述自定义音色 | 无需预设音色或音频样本 |
| MiMo-V2.5-TTS-VoiceClone | `mimo-v2.5-tts-voiceclone` | 从音频样本复制任意音色 | 需要提供音频样本 |

### 内置音色列表（`mimo-v2.5-tts` 模型）

| 音色名称 | 音色 ID | 语言 | 性别 |
|---------|---------|------|------|
| MiMo-默认 | mimo_default | 中国集群默认为晓晓 | - |
| 晓晓 | 晓晓 | 中文 | 女 |
| 晓伊 | 晓伊 | 中文 | 女 |
| 云阳 | 云阳 | 中文 | 男 |
| 云逸 | 云逸 | 中文 | 男 |
| Mia | Mia | 英文 | 女 |
| Chloe | Chloe | 英文 | 女 |
| Milo | Milo | 英文 | 男 |
| Dean | Dean | 英文 | 男 |

### 请求格式（非流式调用）

```json
{
    "model": "mimo-v2.5-tts",
    "messages": [
        {
            "role": "user",
            "content": "用温暖亲切的语气朗读，语速适中"
        },
        {
            "role": "assistant",
            "content": "要朗读的文本内容"
        }
    ],
    "audio": {
        "format": "wav",
        "voice": "晓晓"
    }
}
```

### 关键调用规则

1. **合成文本必须放在 `role: assistant` 的 `content` 中**，不能放在 `user` 角色中
2. `user` 角色消息是**可选参数**，用于传递风格指令（内容不会出现在合成语音中）
3. 当使用 `mimo-v2.5-tts-voicedesign` 模型时，`user` 消息为**必填参数**
4. 音频格式支持 `wav` 和 `pcm16`（流式调用时使用 `pcm16`）

### 响应格式

响应中音频数据以 Base64 编码返回在 `message.audio.data` 字段中：

```json
{
    "choices": [{
        "message": {
            "audio": {
                "data": "<base64编码的音频数据>"
            }
        }
    }]
}
```

### Python 调用示例

```python
import os, base64
from openai import OpenAI

client = OpenAI(
    api_key=os.environ.get("MIMO_API_KEY"),
    base_url="https://api.xiaomimimo.com/v1"
)

completion = client.chat.completions.create(
    model="mimo-v2.5-tts",
    messages=[
        {
            "role": "user",
            "content": "用温暖亲切的语气朗读，语速适中"
        },
        {
            "role": "assistant",
            "content": "要朗读的文本内容"
        }
    ],
    audio={
        "format": "wav",
        "voice": "晓晓"
    }
)

message = completion.choices[0].message
audio_bytes = base64.b64decode(message.audio.data)
with open("audio_file.wav", "wb") as f:
    f.write(audio_bytes)
```

### 风格控制

MIMO-TTS v2.5 支持两种风格控制方式：

#### 1. 自然语言控制（放在 `role: user` 的 `content` 中）

通过自然语言描述，让模型理解并生成对应风格的语音。

示例指令：
- "用温暖亲切的语气朗读，语速适中"
- "播报新闻的正式语气，语速稍快"
- "东北方言，热情豪爽的语气"

#### 2. 音频标签控制（放在 `role: assistant` 的 `content` 中）

在合成文本中嵌入风格标签，实现细粒度控制：

- **整体风格标签**：放在文本开头，格式 `(风格)文本内容`
- **插入式标签**：放在文本中间任意位置

支持的风格示例：

| 风格类型 | 示例 |
|---------|------|
| 基础情绪 | 开心 / 悲伤 / 愤怒 / 恐惧 / 惊讶 / 兴奋 / 委屈 / 平静 / 冷漠 |
| 复杂情绪 | 忧郁 / 释然 / 无奈 / 内疚 / 嫉妒 / 疲惫 / 忐忑 / 动情 |
| 整体语调 | 温柔 / 冷淡 / 活泼 / 严肃 / 慵懒 / 调皮 / 低沉 / 干练 / 尖锐 |
| 音色定位 | 磁性 / 醇厚 / 清亮 / 空灵 / 天真 / 苍老 / 甜美 / 沙哑 / 优雅 |
| 角色腔调 | 夹子音 / 大姐姐音 / 正太音 / 大叔音 / 台湾腔 |
| 方言 | 东北话 / 四川话 / 河南话 / 粤语 |
| 角色扮演 | 孙悟空 / 林黛玉 |
| 唱歌 | singing |

插入式标签示例：
- `[叹气]` / `[深吸一口气]` / `[笑]` / `[啜泣]` / `[紧张]` / `[颤抖]`

---

## Legado HTTP 自定义 TTS 引擎接口规范

> 参考源码：`app/src/main/assets/defaultData/httpTTS.json`、`app/src/main/assets/web/help/md/httpTTSHelp.md`

### Legado HTTP TTS 工作原理

Legado 的 HTTP TTS **不是**简单的 HTTP 接口调用，而是一个**可编程的 HTTP 请求模板引擎**：

1. 用户在 Legado 中配置 HTTP TTS 引擎，包含 URL 和请求配置
2. Legado 内置 JS 引擎（Rhino），在朗读时动态执行模板表达式
3. Legado 根据配置向目标服务器发送 HTTP 请求
4. 服务器返回**原始音频二进制数据**，Legado 直接播放

### Legado HTTP TTS 配置格式

```json
{
    "name": "MIMO-TTS",
    "url": "http://<服务器IP>:9880/speak,{\"method\":\"GET\"}",
    "contentType": "audio/wav"
}
```

**配置字段说明：**

| 字段 | 说明 |
|------|------|
| `name` | TTS 引擎名称 |
| `url` | 格式为 `{URL},{请求配置JSON}`，用逗号分隔 |
| `contentType` | 响应音频的 MIME 类型（`audio/wav`、`audio/mpeg`） |

**请求配置 JSON 可选字段：**

| 字段 | 说明 |
|------|------|
| `method` | HTTP 方法（GET/POST），默认 GET |
| `body` | POST 请求体，支持 JS 模板表达式 |
| `headers` | 自定义请求头 |

### Legado 可用 JS 变量

在 URL 和 body 模板中可使用以下变量：

| 变量 | 说明 | 值范围 |
|------|------|--------|
| `speakText` | 当前要朗读的文本 | 字符串 |
| `speakSpeed` | 朗读速度 | 5-50（整数） |

### 模板表达式语法

使用 `{{expression}}` 嵌入 JS 表达式：

```
{{java.encodeURI(speakText)}}    // URL 编码文本
{{speakSpeed}}                    // 直接使用速度值
{{String((speakSpeed + 5) / 10)}} // JS 运算
```

### Legado 内置 TTS 示例（百度 TTS）

```json
{
    "name": "百度",
    "url": "http://tts.baidu.com/text2audio,{\"method\": \"POST\", \"body\": \"tex={{java.encodeURI(java.encodeURI(speakText))}}&spd={{(speakSpeed + 5) / 10 + 4}}&per=3&cuid=baidu_speech_demo&idx=1&cod=2&lan=zh&ctp=1&pdt=160&vol=5&aue=6&pit=5&_res_tag_=audio\"}",
    "contentType": "audio/wav"
}
```

### 对接 Legado 的服务器端设计

我们的 Docker 中间件服务需要提供一个 HTTP 端点，接收 Legado 的请求并返回原始音频二进制数据。

**推荐的 Legado 配置（GET 方式）：**

```json
{
    "name": "MIMO-TTS",
    "url": "http://<服务器IP>:9880/speak?text={{java.encodeURI(speakText)}}&speed={{speakSpeed}}",
    "contentType": "audio/wav"
}
```

**推荐的 Legado 配置（POST 方式，更可靠）：**

```json
{
    "name": "MIMO-TTS",
    "url": "http://<服务器IP>:9880/speak,{\"method\":\"POST\",\"headers\":{\"Content-Type\":\"application/json\"},\"body\":\"{\\\"text\\\":\\\"{{java.encodeURI(speakText)}}\\\",\\\"speed\\\":{{speakSpeed}}}\"}",
    "contentType": "audio/wav"
}
```

### 服务器端响应要求

- **Content-Type**: `audio/wav`（与 Legado 配置的 `contentType` 一致）
- **响应体**: 直接返回**原始音频二进制数据**（非 Base64，非 JSON）
- **不支持流式传输**: Legado 需要接收完整音频后才开始播放

### `speakSpeed` 转换逻辑

Legado 的 `speakSpeed` 范围为 5-50，需要转换为 MIMO-TTS 的风格提示：

```python
def speed_to_hint(speed: int) -> str:
    """将 Legado 的 speakSpeed (5-50) 转换为 MIMO 风格指令"""
    if speed <= 15:
        return "语速很慢，缓慢朗读"
    elif speed <= 25:
        return "语速较慢，从容朗读"
    elif speed <= 35:
        return "语速适中"
    elif speed <= 45:
        return "语速较快，紧凑朗读"
    else:
        return "语速很快，快速朗读"
```

---

## 项目文件结构

```
MIMO-TTS/
├── plan.md                  # 项目计划文档
├── Dockerfile               # Docker 镜像构建文件
├── docker-compose.yml       # Docker Compose 编排文件
├── .env.example             # 环境变量配置示例
├── requirements.txt         # Python 依赖
├── app/
│   ├── __init__.py
│   ├── main.py              # FastAPI 应用入口
│   ├── config.py            # 配置管理
│   ├── routers/
│   │   ├── __init__.py
│   │   └── tts.py           # TTS 路由处理
│   ├── services/
│   │   ├── __init__.py
│   │   └── tts_service.py   # MIMO-TTS API 调用服务
│   └── models/
│       ├── __init__.py
│       └── schemas.py       # 请求/响应数据模型
└── README.md                # 项目说明文档
```

---

## 核心功能模块

### 1. FastAPI 主应用 (`app/main.py`)

- 初始化 FastAPI 应用
- 注册路由
- 配置 CORS（允许跨域请求）
- 健康检查端点 `/health`
- 启动事件中验证 MIMO-TTS API 连通性

### 2. TTS 路由 (`app/routers/tts.py`)

核心端点：

| 端点 | 方法 | 说明 |
|------|------|------|
| `/speak` | GET/POST | Legado 调用的主端点，返回音频流 |
| `/voices` | GET | 获取可用音色列表 |
| `/health` | GET | 健康检查 |

#### `/speak` 端点详细设计

该端点接收 Legado HTTP TTS 引擎的请求，返回原始音频二进制数据。

**GET 请求参数（与 Legado 模板变量对应）：**

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| text | string | 是 | - | 要朗读的文本（来自 `speakText`，URL 编码） |
| speed | integer | 否 | 30 | 朗读速度（来自 `speakSpeed`，范围 5-50） |
| voice | string | 否 | 配置默认值 | 音色选择（晓晓/云阳/Chloe 等） |
| style | string | 否 | 配置默认值 | 风格标签（如"温柔"、"开心"） |

**POST 请求体（JSON）：**

```json
{
  "text": "要朗读的文本",
  "speed": 30,
  "voice": "晓晓",
  "style": "温柔"
}
```

**响应格式：**
- **Content-Type**: `audio/wav`（与 Legado `contentType` 配置一致）
- **响应体**: 直接返回原始音频二进制数据
- **错误响应**: HTTP 4xx/5xx 状态码 + JSON 错误信息

### 3. TTS 服务 (`app/services/tts_service.py`)

核心逻辑：

```python
import os, base64, httpx
from openai import OpenAI

class TTSService:
    def __init__(self, config):
        self.client = OpenAI(
            api_key=config.mimo_api_key,
            base_url=config.mimo_api_base_url
        )
        self.default_voice = config.default_voice
        self.default_model = config.default_model

    async def synthesize(
        self,
        text: str,
        voice: str = None,
        style_hint: str = None,
        audio_format: str = "wav"
    ) -> bytes:
        """将文本转换为音频"""
        voice = voice or self.default_voice

        messages = []

        # 用户风格指令（可选）
        if style_hint:
            messages.append({
                "role": "user",
                "content": style_hint
            })

        # 合成文本（必须放在 assistant 角色）
        messages.append({
            "role": "assistant",
            "content": text
        })

        completion = self.client.chat.completions.create(
            model=self.default_model,
            messages=messages,
            audio={
                "format": audio_format,
                "voice": voice
            }
        )

        message = completion.choices[0].message
        audio_bytes = base64.b64decode(message.audio.data)
        return audio_bytes
```

- 使用 openai Python SDK 调用 MIMO Chat Completions API
- 将返回的 Base64 音频解码为二进制
- 支持 WAV 格式直接返回（或转换为 MP3）
- 错误处理与重试机制

### 4. 配置管理 (`app/config.py`)

通过环境变量配置：

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| MIMO_TTS_API_BASE_URL | MIMO-TTS API 基础地址 | https://api.xiaomimimo.com/v1 |
| MIMO_TTS_API_KEY | API 认证密钥（必填） | - |
| MIMO_TTS_MODEL | 模型名称 | mimo-v2.5-tts |
| MIMO_TTS_DEFAULT_VOICE | 默认音色 | 晓晓 |
| MIMO_TTS_DEFAULT_STYLE | 默认风格指令 | 温柔，语速适中 |
| MIMO_TTS_TIMEOUT | 请求超时时间(秒) | 60 |
| MIMO_TTS_MAX_TEXT_LENGTH | 单次最大文本长度 | 5000 |
| OUTPUT_AUDIO_FORMAT | 输出音频格式 (wav/mp3) | wav |
| SERVER_HOST | 服务监听地址 | 0.0.0.0 |
| SERVER_PORT | 服务监听端口 | 9880 |

### 5. 数据模型 (`app/models/schemas.py`)

- `TTSRequest`: TTS 请求数据模型（text, voice, style, speed_hint）
- `VoiceInfo`: 音色信息模型
- `HealthResponse`: 健康检查响应模型

---

## Docker 部署方案

### Dockerfile

```dockerfile
FROM python:3.11-slim-bookworm

WORKDIR /app

# 安装依赖
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# 复制应用代码
COPY app/ ./app/

# 暴露端口
EXPOSE 9880

# 启动服务
CMD ["uvicorn", "app.main:app", "--host", "0.0.0.0", "--port", "9880"]
```

### docker-compose.yml

```yaml
version: '3.8'

services:
  mimo-tts-legado:
    build: .
    container_name: mimo-tts-legado
    restart: unless-stopped
    ports:
      - "9880:9880"
    environment:
      - MIMO_TTS_API_KEY=${MIMO_TTS_API_KEY}
      - MIMO_TTS_API_BASE_URL=${MIMO_TTS_API_BASE_URL:-https://api.xiaomimimo.com/v1}
      - MIMO_TTS_DEFAULT_VOICE=${MIMO_TTS_DEFAULT_VOICE:-晓晓}
      - MIMO_TTS_DEFAULT_STYLE=${MIMO_TTS_DEFAULT_STYLE:-温柔，语速适中}
    healthcheck:
      test: ["CMD", "curl", "-f", "http://localhost:9880/health"]
      interval: 30s
      timeout: 10s
      retries: 3
```

### .env.example

```env
# MIMO-TTS API 配置（必填）
MIMO_TTS_API_KEY=your_api_key_here

# API 基础地址（默认即可）
MIMO_TTS_API_BASE_URL=https://api.xiaomimimo.com/v1

# 默认音色（可选）：晓晓/晓伊/云阳/云逸/Mia/Chloe/Milo/Dean
MIMO_TTS_DEFAULT_VOICE=晓晓

# 默认风格指令（可选）
MIMO_TTS_DEFAULT_STYLE=温柔，语速适中
```

---

## 实现步骤

### 第一阶段：基础框架搭建

1. 创建项目目录结构
2. 编写 `requirements.txt`（fastapi, uvicorn, openai, pydantic, python-dotenv）
3. 实现 `config.py` 配置管理
4. 实现 `main.py` FastAPI 应用骨架
5. 实现健康检查端点 `/health`

### 第二阶段：TTS 核心功能

1. 实现 `schemas.py` 数据模型
2. 实现 `tts_service.py`，使用 openai SDK 调用 MIMO Chat Completions API
3. 实现 `/speak` 端点（GET + POST），解码 Base64 音频并返回
4. 实现 `/voices` 端点（返回内置音色列表）
5. 音频格式处理（WAV 直接返回或转 MP3）

### 第三阶段：容器化与部署

1. 编写 `Dockerfile`
2. 编写 `docker-compose.yml`
3. 编写 `.env.example`
4. 编写 `README.md`（部署说明、Legado 配置指南）

### 第四阶段：优化与完善

1. 添加错误处理与重试机制
2. 添加请求日志记录
3. 添加文本长度限制与分段处理（长文本自动分段合成后拼接）
4. 添加请求限流保护
5. 性能优化（音频缓存）
6. 支持风格标签透传（Legado 可通过参数控制朗读风格）

---

## Legado 配置指南

### 步骤

1. **部署 Docker 容器**：
   ```bash
   # 克隆项目
   git clone <repo-url>
   cd MIMO-TTS

   # 配置环境变量
   cp .env.example .env
   # 编辑 .env 填入 API Key 和可选配置

   # 启动服务
   docker-compose up -d
   ```

2. **在 Legado 中添加自定义 HTTP TTS 引擎**：

   打开 Legado → 设置 → 朗读引擎 → 点击 "+" 添加 HTTP TTS 引擎

   **配置内容（推荐 POST 方式）：**

   名称：`MIMO-TTS`

   URL：
   ```
   http://<服务器IP>:9880/speak,{"method":"POST","headers":{"Content-Type":"application/json"},"body":"{\"text\":\"{{java.encodeURI(speakText)}}\",\"speed\":{{speakSpeed}}}"}
   ```

   Content Type：`audio/wav`

   **或者使用 GET 方式（更简单）：**

   URL：
   ```
   http://<服务器IP>:9880/speak?text={{java.encodeURI(speakText)}}&speed={{speakSpeed}}
   ```

   Content Type：`audio/wav`

3. **可选：自定义音色和风格**：

   如果需要指定音色或风格，可以在 URL 中添加额外参数：

   GET 方式示例：
   ```
   http://<服务器IP>:9880/speak?text={{java.encodeURI(speakText)}}&speed={{speakSpeed}}&voice=云阳&style=磁性
   ```

   POST 方式示例：
   ```
   http://<服务器IP>:9880/speak,{"method":"POST","headers":{"Content-Type":"application/json"},"body":"{\"text\":\"{{java.encodeURI(speakText)}}\",\"speed\":{{speakSpeed}},\"voice\":\"云阳\",\"style\":\"磁性\"}"}
   ```

4. **测试连接**：配置完成后点击测试按钮，验证是否能正常返回音频

---

## 注意事项

1. **API 调用方式**：MIMO-TTS v2.5 使用 Chat Completions API（`/v1/chat/completions`），**不是**标准的 OpenAI TTS API（`/v1/audio/speech`）
2. **消息格式**：合成文本必须放在 `role: assistant` 的 `content` 中，风格指令放在 `role: user` 的 `content` 中
3. **音频格式**：API 返回 Base64 编码的 WAV 音频，需要解码后返回给 Legado
4. **流式调用**：MIMO-V2.5-TTS 系列的低延迟流式输出功能尚未开放，当前流式调用以兼容模式降级
5. **文本长度限制**：单次请求文本不宜过长（建议 ≤ 5000 字符），超长文本需分段处理
6. **网络延迟**：远程 API 调用存在网络延迟，首次请求可能较慢
7. **并发控制**：多个 Legado 客户端同时请求时需做好并发控制
8. **安全性**：API Key 通过环境变量注入，不要硬编码在代码中
9. **计费**：当前 MIMO-TTS v2.5 限时免费
10. **音频采样率**：PCM16 格式为 24kHz 单声道

---

## 待确认项

- [ ] MIMO TTS API Key 获取方式
- [ ] 服务器是否需要支持 MP3 输出（如需要，需安装 ffmpeg 进行格式转换）
- [ ] 是否需要支持声音克隆（VoiceClone）和声音设计（VoiceDesign）功能
- [ ] 是否需要支持唱歌模式
- [ ] API 是否有速率限制（rate limit）