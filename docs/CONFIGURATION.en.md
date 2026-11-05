# Configuration

Environment variables and model setup. Install steps are in [Operations](OPERATIONS.en.md). The full Chinese reference is [配置说明](CONFIGURATION.md).

## Configuration

### Config Management

TestPilot supports:

1.**Environment variables** (`.env`)
2.**Web-based Config Center**

Vector-store keys, retrieval modes, and the config matrix are in the Chinese [配置说明](CONFIGURATION.md). Model examples below match `.env.example`.  

### AI Model Config Examples

```bash
# OpenAI
DEFAULT_COMPANY=OPENAI
OPENAI_API_KEY=sk-your-openai-key
OPENAI_MODEL=gpt-5

# Google Gemini
DEFAULT_COMPANY=GEMINI
GEMINI_API_KEY=your-gemini-api-key
GEMINI_MODEL=gemini-3.8-flash

# DeepSeek
DEFAULT_COMPANY=DEEPSEEK
DEEPSEEK_API_KEY=your-deepseek-key
DEEPSEEK_MODEL=deepseek-flash

# Qwen
DEFAULT_COMPANY=QWEN
QWEN_API_KEY=your-qwen-api-key
QWEN_BASE_URL=https://dashscope.aliyuncs.com/compatible-mode/v1
QWEN_MODEL=qwen-flash
QWEN_TEMPERATURE=0.7
QWEN_TIMEOUT=60

# Anthropic / Claude
# Messages API, not an OpenAI-compatible base URL. Keys start with sk-ant-.
# Enable only ENABLE_ANTHROPIC and set DEFAULT_COMPANY to match.
ENABLE_ANTHROPIC=true
ENABLE_OPENAI=false
ENABLE_DEEPSEEK=false
ENABLE_OLLAMA=false
ENABLE_GEMINI=false
ENABLE_QWEN=false
DEFAULT_COMPANY=ANTHROPIC
ANTHROPIC_API_KEY=sk-ant-your-key
ANTHROPIC_BASE_URL=https://api.anthropic.com
ANTHROPIC_MODEL=claude-sonnet-5-5
TR_ANTHROPIC_MAX_TOKENS=8000

# Token limits (defaults when DB has no entry; prefer Config Center)
TR_MAX_TOKENS=8000
MAX_TOKENS=4000
TOKEN_MAX_PER_SESSION=50000
TOKEN_MAX_CALLS_PER_SESSION=100

# Ollama (local)
DEFAULT_COMPANY=OLLAMA
OLLAMA_BASE_URL=http://localhost:11434
OLLAMA_MODEL=llama2
```

Current Claude models `claude-opus-5-5`, `claude-sonnet-5-5`, `claude-haiku-5-5`, and `claude-fable-5-1` reject `temperature`, `top_p`, and `top_k`. Calls send `max_tokens` only. Short names `opus`, `sonnet`, `haiku`, and `fable`, plus retired ids such as `claude-3-*`, `claude-sonnet-4-5`, and `claude-opus-4-1`, map to those current models. If `ANTHROPIC_MODEL` is empty, the default is `claude-sonnet-5-5`. Enable only one `ENABLE_*` provider at a time.

