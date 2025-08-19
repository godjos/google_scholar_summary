# Google Scholar 邮件通知处理器

自动化处理 Google Scholar Alerts 邮件，使用大模型 API 对论文进行分析和摘要。

## 功能特点

- 连接 QQ 邮箱并获取 Google Scholar 通知邮件
- 解析邮件内容，提取论文标题、链接和摘要
- 使用大模型 API（如 OpenAI GPT、Google Gemini）对论文进行分析
- 生成中文摘要、研究亮点和潜在应用领域
- 将结果导出为 CSV 文件
- **增量处理支持**：使用 SQLite 数据库存储已处理邮件和论文信息，避免重复处理
- **持久化存储**：所有处理过的论文都会保存在数据库中，便于后续查询和分析
- **流式处理**：支持大量邮件的分批处理，降低内存占用，提高处理效率

## 项目结构

```
.
├── app.py                  # 主程序入口
├── requirements.txt        # 项目依赖
├── .env.example           # 环境变量示例文件
├── README.md              # 说明文档
└── src/                   # 源代码目录
    ├── __init__.py        # 包初始化文件
    ├── config.py          # 配置管理模块
    ├── email_client.py    # 邮箱客户端模块
    ├── paper_parser.py    # 论文解析模块
    ├── llm_client.py      # 大模型客户端模块
    ├── data_manager.py    # 数据管理模块
    ├── scholar_alert_processor.py  # 早期版本的完整脚本
    └── utils/             # 工具类目录（预留）
```

## 环境要求

- Python 3.7+
- QQ邮箱账户并开启IMAP服务

## 安装步骤

1. 克隆或下载本项目
2. 安装依赖包：
   ```bash
   pip install -r requirements.txt
   ```

## 使用方法

1. 在QQ邮箱中开启IMAP服务并生成授权码
   - 登录QQ邮箱
   - 进入设置 > 账户
   - 开启"IMAP/SMTP服务"
   - 按提示发送短信获取授权码

2. 复制 `.env.example` 文件为 `.env` 并配置环境变量：
   ```bash
   cp .env.example .env
   ```
   然后编辑 `.env` 文件，填入实际的配置信息

3. 运行脚本：
   ```bash
   python app.py
   ```

## 配置说明

### 邮箱配置
- `QQ_EMAIL_ADDRESS`: 你的QQ邮箱地址
- `QQ_EMAIL_AUTH_CODE`: QQ邮箱授权码（不是登录密码）
- `EMAIL_FOLDER`: 邮箱文件夹名称，默认为inbox

### 大模型API配置
- `LLM_API_KEY`: 大模型API密钥（支持OpenAI或Google AI Platform）
- `LLM_API_BASE_URL`: API基础URL，默认为https://api.openai.com
- `LLM_MODEL_NAME`: 模型名称，默认为gpt-3.5-turbo
- `LLM_API_PATH`: API路径，默认为v1/chat/completions

### 配置项说明

| 配置项 | 说明 | 默认值 |
|--------|------|--------|
| QQ_EMAIL_ADDRESS | QQ 邮箱地址 | your_email@qq.com |
| QQ_EMAIL_AUTH_CODE | QQ 邮箱授权码 | your_qq_email_auth_code |
| LLM_API_KEY | 大模型 API 密钥 | your_api_key |
| LLM_API_BASE_URL | 大模型 API 基础 URL | https://api.openai.com/v1 |
| LLM_MODEL_NAME | 大模型名称 | gpt-3.5-turbo |
| LLM_API_PATH | API 路径 | v1/chat/completions |
| MAX_EMAILS | 最大处理邮件数 | 10 |
| OUTPUT_FILE | 输出文件名 | scholar_results.csv |
| EMAIL_FOLDER | 邮箱文件夹 | inbox |
| USE_LLM | 是否使用大模型处理 | true |
| DATABASE_PATH | SQLite 数据库路径 | scholar_data.db |

## 输出文件

程序会生成一个 CSV 文件（默认为 `scholar_results.csv`），包含以下字段：

- 标题：论文标题
- 链接：论文链接
- 原始摘要：论文的原始英文摘要
- 中文摘要：使用大模型生成的中文摘要（当 USE_LLM=true 时）
- 研究亮点：论文的研究亮点（当 USE_LLM=true 时）
- 应用领域：论文的潜在应用领域（当 USE_LLM=true 时）

当 USE_LLM=false 时，中文摘要、研究亮点和应用领域字段将为空。

## 流式处理机制

为了更好地处理大量邮件，系统采用流式处理机制：

1. **分批获取**：将大量邮件分批获取，每批默认处理5封邮件
2. **即时处理**：每批邮件获取后立即处理，无需等待所有邮件加载完成
3. **阶段性保存**：每处理完一批邮件就保存一次结果，提高容错性
4. **内存优化**：避免一次性加载大量邮件导致的内存占用过高问题
## 数据库功能

本项目引入了 SQLite 数据库来支持大量数据处理和持久化存储：

1. **增量处理**：系统会记录已处理的邮件 ID，避免重复处理相同邮件
2. **论文存储**：所有处理过的论文信息都会保存在数据库中
3. **避免重复**：通过论文链接唯一标识，避免重复存储相同论文
4. **流式处理**：支持大量邮件的分批处理，每批处理完成后即时保存结果

数据库包含三个表：
- `processed_emails`：存储已处理的邮件 ID
- `papers`：存储所有处理过的论文信息
- `email_paper_relations`：存储邮件与论文的关联关系
## 大模型处理开关

系统支持通过配置项 `USE_LLM` 控制是否使用大模型进行论文分析：

- 当 `USE_LLM=true` 时，系统会调用大模型 API 对论文进行分析，生成中文摘要、研究亮点和应用领域
- 当 `USE_LLM=false` 时，系统仅收集论文基本信息，不调用大模型 API，节省 API 调用成本

这个功能特别适用于以下场景：
1. 用户只想收集论文基本信息，不需要深入分析
2. 用户希望节省大模型 API 调用成本
3. 用户在没有网络连接的环境中收集论文，后续再进行分析


## 自定义

你可以根据需要修改以下部分：

1. 邮件解析逻辑（[src/paper_parser.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/paper_parser.py)中的[extract_paper_info](file:///home/HiNAS/mrz/code/google_scholar_summary/src/paper_parser.py#L27-L66)方法）
2. 大模型提示词（[src/llm_client.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/llm_client.py)中的[get_paper_analysis](file:///home/HiNAS/mrz/code/google_scholar_summary/src/llm_client.py#L37-L83)方法）
3. 输出格式和内容（[src/data_manager.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/data_manager.py)中的相关方法）
4. 支持其他邮箱服务商（修改[src/config.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/config.py)和[src/email_client.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/email_client.py)）

## 支持的大模型提供商

- OpenAI (GPT 系列)
- Google (Gemini 系列)
- 其他兼容 OpenAI API 格式的模型提供商