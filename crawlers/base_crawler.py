from abc import ABC, abstractmethod
from typing import List, Dict
import logging

class BaseCrawler(ABC):
    def __init__(self):
        self.logger = logging.getLogger(self.__class__.__name__)

    @property
    @abstractmethod
    def source_name(self) -> str:
        """数据源名称，如 'weibo', 'twitter' 等"""
        pass

    @abstractmethod
    def login(self):
        """处理登录逻辑"""
        pass

    @abstractmethod
    def fetch_latest_posts(self, **kwargs) -> List[Dict]:
        """抓取最新帖子，返回统一格式的帖子列表"""
        pass
    
    @abstractmethod
    def close(self):
        """清理资源"""
        pass
