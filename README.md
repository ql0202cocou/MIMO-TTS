# MIMO-TTS Legado (作者已无MIMO模型，归档)

将[开源阅读（Legado）](https://github.com/gedoor/legado)的自定义 TTS 朗读引擎请求转发到小米 [MIMO-TTS v2.5](https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5) 的 Chat Completions API，提供高质量、自然的语音朗读体验。

使用 Rust 重写，内存占用更低，启动更快。

## 系统架构

```
┌─────────────────────────┐                  ┌─────────────────────────┐                  ┌─────────────────────────┐
│                         │     --> HTTP     │                         │  Chat Completions  │                         │
│  Legado (Android)       │     -->          │  Docker (Rust)          │  --> API           │  小米 MIMO-TTS v2.5     │
│  开源阅读 App            │     <--          │  Debian 12              │  <--               │  API                    │
│                         │  音频流(WAV)      │                         │  Base64 音频数据    │                         │
└─────────────────────────┘                  └─────────────────────────┘                  └─────────────────────────┘
```

## 快速开始

### 1. 部署 Docker 容器

```bash
# 克隆项目
git clone <repo-url>
cd MIMO-TTS

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的配置
```

编辑 `.env` 文件：

```env
API_BASE_URL=https://api.xiaomimimo.com/v1
API_KEY=your_mimo_api_key_here
USERNAME=your_username
PASSWORD=your_password
```

### 2. 启动服务

```bash
# 构建并启动
docker compose up -d

# 查看日志
docker compose logs -f

# 停止服务
docker compose down
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:9880/health

# 查看可用音色
curl -u your_username:your_password http://localhost:9880/voices

# 测试语音合成
curl -u your_username:your_password "http://localhost:9880/speak?text=你好世界" --output test.wav
```

## Legado 配置指南

### 方法一：自动导入（推荐）

1. 确保服务已启动
2. 在手机浏览器访问 `http://服务器IP:9880/legado`
3. 下载 JSON 文件
4. 在 Legado 中导入朗读引擎配置
5. 首次朗读时 Legado 会弹出登录框，输入 `USERNAME` 和 `PASSWORD` 即可

### 方法二：手动配置

1. 打开 Legado → 设置 → 朗读引擎 → 点击 "+" 添加 HTTP TTS 引擎

2. 配置引擎信息：

   **推荐 GET 方式（更简单）**：

   ```
   URL: http://<服务器IP>:9880/speak?text={{java.encodeURI(speakText)}}&speed={{speakSpeed}}
   Content Type: audio/wav
   ```

   **推荐 POST 方式（更可靠，适合长文本）**：

   ```
   URL: http://<服务器IP>:9880/speak,{"method":"POST","headers":{"Content-Type":"application/json"},"body":"{\"text\":\"{{java.encodeURI(speakText)}}\",\"speed\":{{speakSpeed}}}"}
   Content Type: audio/wav
   ```

3. 配置完成后点击测试按钮，Legado 会提示输入用户名和密码

## API 端点

| 端点 | 方法 | 认证 | 说明 |
|------|------|------|------|
| `/speak` | GET | Basic Auth | 朗读文本，返回音频二进制数据 |
| `/speak` | POST | Basic Auth | 朗读文本，返回音频二进制数据 |
| `/voices` | GET | Basic Auth | 获取可用音色列表 |
| `/legado` | GET | 无 | 获取 Legado 引擎导入配置 |
| `/health` | GET | 无 | 健康检查 |

### `/speak` GET 参数

| 参数 | 类型 | 必填 | 默认值 | 说明 |
|------|------|------|--------|------|
| text | string | 是 | - | 要朗读的文本（URL 编码） |
| speed | integer | 否 | 30 | 朗读速度（5-50） |
| voice | string | 否 | 晓晓 | 音色选择 |
| style | string | 否 | 温柔，语速适中 | 风格标签 |

### `/speak` POST 请求体

```json
{
  "text": "要朗读的文本",
  "speed": 30,
  "voice": "晓晓",
  "style": "温柔"
}
```

## 可用音色

| 音色名称 | 音色 ID | 语言 | 性别 |
|---------|---------|------|------|
| MiMo-默认 | mimo_default | 中文 | - |
| 晓晓 | 晓晓 | 中文 | 女 |
| 晓伊 | 晓伊 | 中文 | 女 |
| 云阳 | 云阳 | 中文 | 男 |
| 云逸 | 云逸 | 中文 | 男 |
| Mia | Mia | 英文 | 女 |
| Chloe | Chloe | 英文 | 女 |
| Milo | Milo | 英文 | 男 |
| Dean | Dean | 英文 | 男 |

## 环境变量

| 环境变量 | 必填 | 说明 | 默认值 |
|---------|------|------|--------|
| API_BASE_URL | 是 | MIMO-TTS API 基础地址 | https://api.xiaomimimo.com/v1 |
| API_KEY | 是 | MIMO-TTS API Key | - |
| USERNAME | 是 | Basic Auth 用户名 | - |
| PASSWORD | 是 | Basic Auth 密码 | - |
| MODEL | 否 | 模型名称 | mimo-v2.5-tts |
| DEFAULT_VOICE | 否 | 默认音色 | 晓晓 |
| DEFAULT_STYLE | 否 | 默认风格指令 | 温柔，语速适中 |
| TIMEOUT_SECS | 否 | 请求超时时间(秒) | 60 |
| MAX_TEXT_LENGTH | 否 | 单次最大文本长度 | 5000 |
| OUTPUT_FORMAT | 否 | 输出音频格式 (wav/mp3/pcm16) | wav |
| RATE_LIMIT_PER_MINUTE | 否 | 速率限制 | 60 |
| MAX_REQUEST_SIZE | 否 | 最大请求体大小（字节） | 1048576 |
| LOG_LEVEL | 否 | 日志级别 | info |

## 认证说明

本服务使用 **HTTP Basic Auth** 进行认证：

- `USERNAME` 和 `PASSWORD` 环境变量配置认证凭据
- 如果任一为空，则禁用认证（不推荐用于生产环境）
- Legado 原生支持 Basic Auth，首次请求时会自动弹出登录框
- 使用常量时间比较防止时序攻击

## 技术栈

- **语言**：Rust
- **Web 框架**：axum
- **异步运行时**：tokio
- **HTTP 客户端**：reqwest
- **音频处理**：hound（纯 Rust WAV 处理）
- **容器化**：Docker & Docker Compose（多阶段构建）

## 许可证

MIT License
