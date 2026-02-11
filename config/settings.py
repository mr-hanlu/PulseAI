"""
AI热点监控系统 - 全局配置
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# 加载环境变量
load_dotenv()

# 项目根目录
BASE_DIR = Path(__file__).parent.parent

# 数据目录
DATA_DIR = BASE_DIR / "data"
# RAW_DATA_DIR = DATA_DIR / "raw"
# RAW_API_DIR = DATA_DIR / "raw_api"
# PROCESSED_DATA_DIR = DATA_DIR / "processed"
COOKIES_DIR = DATA_DIR / "cookies"
CHECKPOINTS_DIR = DATA_DIR / "checkpoints"

# 确保目录存在
# for dir_path in [RAW_DATA_DIR, RAW_API_DIR, PROCESSED_DATA_DIR, COOKIES_DIR, CHECKPOINTS_DIR]:
for dir_path in [COOKIES_DIR, CHECKPOINTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# 微博账号配置（从环境变量读取）
WEIBO_ACCOUNT = {
    "username": os.getenv("WEIBO_USERNAME", ""),
    "password": os.getenv("WEIBO_PASSWORD", ""),
}

# 微博 API 端点配置
WEIBO_API_ENDPOINTS = {
    "friends_timeline": "ajax/feed/groupstimeline",  # 特别关注时间线
}

# 采集配置
COLLECTOR_CONFIG = {
    "lookback_hours": 8,  # 默认回溯时间(小时)，可传参修改
    "max_duration_seconds": None,  # 最大采集时长(秒)，None表示不限制
    "scroll_interval": (1, 3),  # 滚动间隔(秒)
    "no_new_data_timeout": 300,  # 无新数据超时时间(秒)
    "relevance_threshold": 0.6,  # 相关性阈值
}

# 日志配置
LOG_CONFIG = {
    "level": "INFO",
    "format": "%(asctime)s - %(levelname)s - %(module)s:%(lineno)d行： %(message)s",
    "datefmt": "%Y-%m-%d %H:%M:%S",
}

# 浏览器配置
BROWSER_CONFIG = {
    "headless": False,  # 首次登录时设为False以便观察
    "load_images": False,  # 不加载图片提升速度
    "user_data_path": os.getenv("BROWSER_USER_DATA_PATH", None),
}

# LLM 大模型配置（从环境变量读取）
LLM_CONFIG = {
    "api_key": os.getenv("LLM_API_KEY", ""),
    "base_url": os.getenv("LLM_BASE_URL", ""),
    "model_name": os.getenv("LLM_MODEL_NAME", ""),
}

# 飞书 Webhook 配置
WEBHOOK_ADDRESS = os.getenv("WEBHOOK_ADDRESS", "")
