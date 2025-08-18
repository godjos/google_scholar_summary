# Google Scholar 邮件通知处理器

该工具通过连接QQ邮箱，获取Google Scholar Alerts邮件，并使用大模型API对论文进行分析和摘要。

## 功能特点

1. 自动连接QQ邮箱并获取Google Scholar通知邮件
2. 解析邮件内容，提取论文标题、链接和摘要
3. 使用大模型API（如OpenAI GPT）对论文进行分析
4. 生成中文摘要、研究亮点和潜在应用领域
5. 将结果导出为CSV文件

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

### 大模型API配置
- `LLM_API_KEY`: 大模型API密钥（支持OpenAI或Google AI Platform）

### 其他配置
- `MAX_EMAILS`: 最大处理邮件数，默认为10
- `OUTPUT_FILE`: 输出文件名，默认为scholar_results.csv

## 输出文件

脚本运行后会生成一个CSV文件（默认为`scholar_results.csv`），包含以下字段：
- `title`: 论文标题
- `link`: 论文链接
- `abstract`: 原始摘要
- `chinese_abstract`: 中文摘要
- `highlights`: 研究亮点
- `applications`: 潜在应用领域

## 模块说明

### app.py
主程序入口，协调各模块工作

### src/config.py
配置管理模块，负责加载和管理应用程序配置

### src/email_client.py
邮箱客户端模块，负责连接邮箱、搜索和获取邮件内容

### src/paper_parser.py
论文解析模块，负责从邮件内容中提取论文信息

### src/llm_client.py
大模型客户端模块，负责调用大模型API进行论文分析

### src/data_manager.py
数据管理模块，负责处理和存储数据

## 自定义

你可以根据需要修改以下部分：

1. 邮件解析逻辑（[src/paper_parser.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/paper_parser.py)中的[extract_paper_info](file:///home/HiNAS/mrz/code/google_scholar_summary/src/paper_parser.py#L27-L66)方法）
2. 大模型提示词（[src/llm_client.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/llm_client.py)中的[get_paper_analysis](file:///home/HiNAS/mrz/code/google_scholar_summary/src/llm_client.py#L26-L76)方法）
3. 输出格式和内容（[src/data_manager.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/data_manager.py)中的相关方法）
4. 支持其他邮箱服务商（修改[src/config.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/config.py)和[src/email_client.py](file:///home/HiNAS/mrz/code/google_scholar_summary/src/email_client.py)）