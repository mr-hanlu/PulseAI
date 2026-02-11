# 🤖 AI 热点监控系统

一个基于微博"特别关注"的 AI 科技热点智能监控与分析系统。通过爬虫采集微博数据，利用 LLM 进行智能分析，自动生成按话题聚合的热点报告。

## ✨ 功能特性

- 🔍 **智能采集**：基于 DrissionPage 的微博爬虫，支持滚动加载和 API 拦截
- 🕐 **灵活回溯**：支持指定时间范围采集，自动去重和断点续传
- 🤖 **AI 分析**：集成 LLM 进行内容分析，按话题聚合多个信源
- 📊 **数据存储**：SQLite 数据库存储，支持多数据源标识
- 🌐 **Web 展示**：Flask Web 界面，可视化展示分析报告
- 🔐 **安全可靠**：环境变量管理敏感信息，自动重新登录机制
- 🔧 **易于扩展**：抽象基类设计，方便添加新数据源（Twitter、知乎等）

## 📋 环境要求

- Python 3.8+
- Chrome/Chromium 浏览器
- LLM API（支持 OpenAI 兼容接口）

## 🚀 快速开始

### 1. 克隆项目

```bash
git clone <your-repo-url>
cd find_hot
```

### 2. 安装依赖

```bash
pip install -r requirements.txt
```

### 3. 配置环境变量

复制环境变量模板并填入配置：

```bash
cp .env.example .env
```

编辑 `.env` 文件：

```env
# 微博账号（可选，如果已有 cookies 可不填）
WEIBO_USERNAME=your_weibo_username
WEIBO_PASSWORD=your_weibo_password

# LLM API 配置（必填）
LLM_API_KEY=your_api_key_here
LLM_BASE_URL=https://api.openai.com/v1
LLM_MODEL_NAME=gpt-4
```

### 4. 首次登录

首次运行需要扫码登录微博：

```bash
python -m main --crawl
```

浏览器会自动打开，请扫码登录。登录成功后 cookies 会自动保存，下次无需重新登录。

### 5. 运行完整流程

```bash
# 采集 + 分析
python -m main --all --lookback-hours 8
```

### 6. 查看报告

启动 Web 服务：

```bash
python web/app.py
```

访问 http://localhost:8000 查看分析报告。

## 📖 使用指南

### 命令行参数

```bash
python -m main [选项]

选项:
  --crawl              仅采集数据
  --analyze            仅分析数据
  --all                采集 + 分析
  --lookback-hours N   回溯时间（小时），默认 8
  --max-duration N     最大采集时长（秒）
  --strict-time        严格时间模式，忽略 checkpoint
  --headless           无头模式运行
  --close-browser      完成后关闭浏览器
```

### 使用示例

#### 1. 采集最近 24 小时的数据

```bash
python -m main --crawl --lookback-hours 24
```

#### 2. 严格时间模式采集（忽略断点）

```bash
python -m main --crawl --strict-time --lookback-hours 8
```

#### 3. 无头模式运行（生产环境）

```bash
python -m main --all --headless --close-browser
```

#### 4. 仅分析已采集的数据

```bash
python -m main --analyze
```

## 🏗️ 项目结构

```
find_hot/
├── analyzer/              # 内容分析模块
│   └── content_analyzer.py
├── config/                # 配置文件
│   ├── keywords.py        # 关键词配置
│   └── settings.py        # 全局配置
├── crawlers/              # 爬虫模块
│   ├── base_crawler.py    # 抽象基类
│   └── weibo_crawler.py   # 微博爬虫
├── data_manager/          # 数据管理
│   └── storage.py         # 数据存储
├── scripts/               # 工具脚本
│   └── migrate_db.py      # 数据库迁移
├── web/                   # Web 界面
│   ├── app.py
│   └── templates/
├── main.py                # 主程序入口
├── .env.example           # 环境变量模板
├── .gitignore
├── requirements.txt
└── README.md

## 📂 目录说明

- **`data/raw/`**: 存放爬虫抓取的原始数据（如 HTML、截图），用于调试。
- **`data/raw_api/`**: 存放拦截到的原始 API 响应 JSON，保留最原始的数据格式。
- **`data/processed/`**: 存放处理后的中间数据（如有）。
- **`data/cookies/`**: 存放各个网站的 Cookies 文件（如 `weibo.pkl`, `twitter.pkl`）。
- **`data/checkpoints/`**: 存放断点信息，记录上次采集到的位置，支持断点续传。
- **`data/weibo_data.db`**: SQLite 数据库文件，存储所有帖子和分析报告。
```

## 🔧 核心模块

### 1. 爬虫模块 (`crawlers/`)

- **BaseCrawler**: 抽象基类，定义统一接口
- **WeiboCrawler**: 微博爬虫实现
  - API 拦截获取原始数据
  - 自动滚动加载
  - Cookies 过期自动重登录

### 2. 分析模块 (`analyzer/`)

- **ContentAnalyzer**: 内容分析器
  - 本地关键词过滤
  - LLM 智能分析
  - 话题聚合输出

### 3. 数据管理 (`data_manager/`)

- **StorageManager**: 统一存储接口
  - SQLite 数据库
  - JSON 文件备份
  - 多数据源支持

### 4. Web 界面 (`web/`)

- Flask 应用
- 报告列表和详情展示
- Markdown 渲染

## 🔐 安全说明

- ✅ 所有敏感信息通过环境变量管理
- ✅ `.env` 文件已加入 `.gitignore`
- ✅ Cookies 自动保存，无需明文存储密码
- ✅ 支持自动重新登录

## ❓ 常见问题

### 1. Cookies 过期怎么办？

系统会自动检测并重新登录。如果自动登录失败，删除 `cookies.pkl` 后重新运行：

```bash
rm cookies.pkl
python -m main --crawl
```

### 2. 如何添加新的数据源？

继承 `BaseCrawler` 并实现抽象方法：

```python
from crawlers.base_crawler import BaseCrawler

class TwitterCrawler(BaseCrawler):
    @property
    def source_name(self) -> str:
        return 'twitter'
    
    def fetch_latest_posts(self, **kwargs):
        # 实现采集逻辑
        pass
```

### 3. 如何自定义分析 Prompt？

编辑 `analyzer/content_analyzer.py` 中的 `prompt` 变量。

### 4. 数据库迁移

如果更新了数据库 schema，运行迁移脚本：

```bash
python scripts/migrate_db.py
```

### 5. 最新消息自动同步飞书
配置 .env 的 WEBHOOK_ADDRESS
飞书官方文档：https://www.feishu.cn/hc/zh-CN/articles/807992406756-webhook-%E8%A7%A6%E5%8F%91%E5%99%A8

参数列表
`{"success": true,"message": "获取成功","data":{"content":"xxxxxx","start_time":"","end_time":"","post_count":7}}`

## 🛠️ 开发指南

### 运行测试

```bash
# 测试爬虫
python -m main --crawl --lookback-hours 1

# 测试分析
python -m main --analyze

# 测试 Web 界面
python web/app.py
```

### 代码规范

- 遵循 PEP 8
- 使用类型注解
- 添加详细的文档字符串

## 📝 更新日志

### v2.0.0 (2026-02-05)

- ✨ 新增环境变量配置
- ✨ 新增自动重新登录机制
- ✨ 新增话题聚合分析
- ✨ 新增时间段记录
- ✨ 改进爬虫滚动逻辑
- ✨ 提升代码扩展性

### v1.0.0

- 🎉 初始版本发布

## 📄 许可证

MIT License

## 🤝 贡献

欢迎提交 Issue 和 Pull Request！

## 📧 联系方式

如有问题，请提交 Issue。
