# MIMO-TTS Legado Bridge

将[开源阅读（Legado）](https://github.com/gedoor/legado)的自定义 TTS 朗读引擎请求转发到小米 [MIMO-TTS v2.5](https://platform.xiaomimimo.com/docs/zh-CN/usage-guide/speech-synthesis-v2.5) 的 Chat Completions API，提供高质量、自然的语音朗读体验。

## 系统架构

```
┌──────────────────┐        HTTP         ┌──────────────────────┐    Chat Completions API     ┌─────────────────────────┐
│                  │  ──────────────────> │                      │  ────────────────────────> │                         │
│  Legado (Android)│                      │  Docker 中间件服务    │                            │  小米 MIMO-TTS v2.5 API  │
│  开源阅读 App     │  <────────────────── │  (Debian 12)         │  <──────────────────────── │  api.xiaomimimo.com     │
│                  │     音频流(WAV)       │                      │     Base64 音频数据         │                         │
└──────────────────┘                      └──────────────────────┘                            └─────────────────────────┘
```

## 快速开始

### 1. 部署 Docker 容器

```bash
# 克隆项目
git clone <repo-url>
cd MIMO-TTS

# 配置环境变量
cp .env.example .env
# 编辑 .env 填入你的 MIMO API Key
```

编辑 `.env` 文件，至少填入 `MIMO_TTS_API_KEY`：

```env
MIMO_TTS_API_KEY=your_actual_api_key_here
```

### 2. 启动服务

```bash
# 构建并启动
docker-compose up -d

# 查看日志
docker-compose logs -f

# 停止服务
docker-compose down
```

### 3. 验证服务

```bash
# 健康检查
curl http://localhost:9880/health

# 查看可用音色
curl http://localhost:9880/voices

# 测试语音合成
curl "http://localhost:9880/speak?text=你好世界" --output test.wav
```

## Legado 配置指南

### 步骤

1. 打开 Legado → 设置 → 朗读引擎 → 点击 "+" 添加 HTTP TTS 引擎

2. 配置引擎信息：

   **名称**：`MIMO-TTS`

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

3. 可选：指定音色和风格

   GET 方式：
   ```
   http://<服务器IP>:9880/speak?text={{java.encodeURI(speakText)}}&speed={{speakSpeed}}&voice=云阳&style=磁性
   ```

   POST 方式：
   ```
   http://<服务器IP>:9880/speak,{"method":"POST","headers":{"Content-Type":"application/json"},"body":"{\"text\":\"{{java.encodeURI(speakText)}}\",\"speed\":{{speakSpeed}},\"voice\":\"云阳\",\"style\":\"磁性\"}"}
   ```

4. 配置完成后点击测试按钮，验证是否能正常返回音频

## API 端点

| 端点 | 方法 | 说明 |
|------|------|------|
| `/speak` | GET | 朗读文本，返回音频二进制数据 |
| `/speak` | POST | 朗读文本，返回音频二进制数据 |
| `/voices` | GET | 获取可用音色列表 |
| `/health` | GET | 健康检查 |

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

## 风格控制

支持通过自然语言描述控制朗读风格，常见风格示例：

- **基础情绪**：开心 / 悲伤 / 愤怒 / 惊讶 / 兴奋 / 平静
- **整体语调**：温柔 / 冷淡 / 活泼 / 严肃 / 慵懒 / 调皮
- **音色定位**：磁性 / 醇厚 / 清亮 / 空灵 / 甜美 / 沙哑
- **角色腔调**：夹子音 / 大姐姐音 / 正太音 / 大叔音 / 台湾腔
- **方言**：东北话 / 四川话 / 河南话 / 粤语

## 环境变量

| 环境变量 | 说明 | 默认值 |
|---------|------|--------|
| MIMO_TTS_API_KEY | API 认证密钥（**必填**） | - |
| MIMO_TTS_API_BASE_URL | MIMO-TTS API 基础地址 | https://api.xiaomimimo.com/v1 |
| MIMO_TTS_MODEL | 模型名称 | mimo-v2.5-tts |
| MIMO_TTS_DEFAULT_VOICE | 默认音色 | 晓晓 |
| MIMO_TTS_DEFAULT_STYLE | 默认风格指令 | 温柔，语速适中 |
| MIMO_TTS_TIMEOUT | 请求超时时间(秒) | 60 |
| MIMO_TTS_MAX_TEXT_LENGTH | 单次最大文本长度 | 5000 |
| OUTPUT_AUDIO_FORMAT | 输出音频格式 (wav/mp3) | wav |
| SERVER_HOST | 服务监听地址 | 0.0.0.0 |
| SERVER_PORT | 服务监听端口 | 9880 |

## 本地开发

```bash
# 安装依赖
pip install -r requirements.txt

# 配置环境变量
cp .env.example .env
# 编辑 .env

# 启动开发服务器
python -m app.main
# 或者使用 uvicorn
uvicorn app.main:app --host 0.0.0.0 --port 9880 --reload
```

## 注意事项

1. **API 调用方式**：MIMO-TTS v2.5 使用 Chat Completions API（`/v1/chat/completions`），**不是**标准的 OpenAI TTS API（`/v1/audio/speech`）
2. **消息格式**：合成文本必须放在 `role: assistant` 的 `content` 中，风格指令放在 `role: user` 的 `content` 中
3. **音频格式**：API 返回 Base64 编码的 WAV 音频，服务端解码后返回原始二进制数据给 Legado
4. **文本长度限制**：单次请求文本建议 ≤ 5000 字符，超长文本会自动分段合成后拼接
5. **计费**：当前 MIMO-TTS v2.5 限时免费

## 许可证

MIT License