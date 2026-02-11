"""
数据存储管理器 - 支持SQLite和原始API数据存储
"""
import json
import os
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Any
from contextlib import contextmanager

from config.settings import DATA_DIR, CHECKPOINTS_DIR
from utils.logger_config import setup_logging
import logging

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


class SQLiteManager:
    """SQLite数据库管理器"""

    def __init__(self, db_name: str = "weibo_data.db"):
        self.db_path = DATA_DIR / db_name
        self._init_db()

    def _init_db(self):
        """初始化数据库表"""
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS posts (
                    mblog_id TEXT PRIMARY KEY,
                    author TEXT,
                    author_id TEXT,
                    content TEXT,
                    publish_time TEXT,
                    url TEXT,
                    images TEXT,
                    video TEXT,
                    reposts_count INTEGER,
                    comments_count INTEGER,
                    attitudes_count INTEGER,
                    collected_at TEXT,
                    date_key TEXT,
                    source TEXT DEFAULT 'weibo'
                )
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS raw_api_responses (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    url TEXT,
                    response_data TEXT,
                    collected_at TEXT,
                    date_key TEXT
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_date 
                ON posts(date_key)
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_posts_time 
                ON posts(publish_time)
            """)
            conn.execute("""
                CREATE TABLE IF NOT EXISTS analysis_reports (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    date_key TEXT NOT NULL,
                    report_content TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    post_count INTEGER DEFAULT 0,
                    time_range_start TEXT,
                    time_range_end TEXT,
                    source TEXT DEFAULT 'weibo'
                )
            """)
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_reports_date 
                ON analysis_reports(date_key)
            """)
            logger.info(f"数据库初始化完成: {self.db_path}")

    @contextmanager
    def _get_connection(self):
        """获取数据库连接"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"数据库操作失败: {e}")
            raise
        finally:
            conn.close()

    def save_posts(self, posts: List[Dict], date_key: str = None) -> int:
        """保存微博帖子到数据库"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        saved_count = 0
        with self._get_connection() as conn:
            for post in posts:
                try:
                    conn.execute("""
                        INSERT OR REPLACE INTO posts 
                        (mblog_id, author, author_id, content, publish_time, url,
                         images, video, reposts_count, comments_count, attitudes_count,
                         collected_at, date_key)
                        VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """, (
                        post.get('mblog_id'),
                        post.get('author'),
                        post.get('author_id'),
                        post.get('content'),
                        post.get('publish_time'),
                        post.get('url'),
                        json.dumps(post.get('images', []), ensure_ascii=False),
                        post.get('video'),
                        post.get('reposts_count', 0),
                        post.get('comments_count', 0),
                        post.get('attitudes_count', 0),
                        datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                        date_key
                    ))
                    saved_count += 1
                except Exception as e:
                    logger.warning(f"保存帖子失败 {post.get('mblog_id')}: {e}")
            
            logger.info(f"成功保存 {saved_count} 条帖子到数据库")
            return saved_count

    def save_raw_api_response(self, url: str, response_data: Any, date_key: str = None):
        """保存原始API响应"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            conn.execute("""
                INSERT INTO raw_api_responses (url, response_data, collected_at, date_key)
                VALUES (?, ?, ?, ?)
            """, (
                url,
                json.dumps(response_data, ensure_ascii=False),
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                date_key
            ))
            logger.debug(f"保存原始API响应: {url}")

    def get_posts_by_time_range(
        self, 
        start_time: str = None, 
        end_time: str = None,
        date_key: str = None
    ) -> List[Dict]:
        """按时间范围获取帖子"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        query = "SELECT * FROM posts WHERE date_key = ?"
        params = [date_key]
        
        if start_time:
            query += " AND publish_time >= ?"
            params.append(start_time)
        if end_time:
            query += " AND publish_time <= ?"
            params.append(end_time)
        
        query += " ORDER BY publish_time DESC"
        
        with self._get_connection() as conn:
            cursor = conn.execute(query, params)
            rows = cursor.fetchall()
            
            posts = []
            for row in rows:
                post = dict(row)
                post['images'] = json.loads(post['images']) if post['images'] else []
                posts.append(post)
            
            return posts

    def get_last_post_info(self, date_key: str = None) -> Optional[Dict]:
        """获取指定日期的最后一条帖子信息（用于断点续传）"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM posts 
                WHERE date_key = ? 
                ORDER BY publish_time ASC 
                LIMIT 1
            """, (date_key,))
            
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def get_all_posts(self, date_key: str = None) -> List[Dict]:
        """获取所有帖子"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        return self.get_posts_by_time_range(date_key=date_key)

    def save_analysis_report(
        self, 
        report_content: str, 
        post_count: int = 0,
        date_key: str = None,
        time_range_start: str = None,
        time_range_end: str = None,
        source: str = 'weibo'
    ) -> int:
        """保存AI分析报告"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            cursor = conn.execute("""
                INSERT INTO analysis_reports 
                (date_key, report_content, created_at, post_count, time_range_start, time_range_end, source)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (
                date_key,
                report_content,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                post_count,
                time_range_start,
                time_range_end,
                source
            ))
            logger.info(f"已保存AI分析报告: {date_key}, 分析了 {post_count} 条帖子")
            return cursor.lastrowid

    def get_analysis_reports(self, date_key: str = None, limit: int = 10) -> List[Dict]:
        """获取AI分析报告"""
        with self._get_connection() as conn:
            if date_key:
                cursor = conn.execute("""
                    SELECT * FROM analysis_reports 
                    WHERE date_key = ? 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (date_key, limit))
            else:
                cursor = conn.execute("""
                    SELECT * FROM analysis_reports 
                    ORDER BY created_at DESC
                    LIMIT ?
                """, (limit,))
            
            rows = cursor.fetchall()
            return [dict(row) for row in rows]

    def get_analysis_report_by_id(self, report_id: int) -> Optional[Dict]:
        """根据ID获取分析报告"""
        with self._get_connection() as conn:
            cursor = conn.execute("""
                SELECT * FROM analysis_reports 
                WHERE id = ?
            """, (report_id,))
            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        
        with self._get_connection() as conn:
            conn.execute("DELETE FROM posts WHERE date_key < ?", (cutoff_date,))
            conn.execute("DELETE FROM raw_api_responses WHERE date_key < ?", (cutoff_date,))
            logger.info(f"已清理 {cutoff_date} 之前的数据")


class StorageManager:
    """存储管理器 - 支持JSON和SQLite双模式"""

    def __init__(self, use_sqlite: bool = True):
        self.sqlite = SQLiteManager() if use_sqlite else None
        self.checkpoints_dir = CHECKPOINTS_DIR

    def _ensure_dirs(self):
        """确保必要的目录存在"""
        for dir_path in [self.checkpoints_dir]:
            dir_path.mkdir(parents=True, exist_ok=True)

    def save_raw_data_json(self, data: List[Dict], prefix: str = "weibo", date_key: str = None):
        """(Deprecated) 保存解析后的数据为JSON"""
        pass

    def save_raw_api_response(
        self, 
        url: str, 
        response_data: Any, 
        sequence: int = 0,
        date_key: str = None
    ):
        """(Deprecated) 保存原始API响应为JSON文件"""
        pass

    def save_checkpoint(self, mblog_id: str, date_key: str = None):
        """保存断点信息"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        filepath = self.checkpoints_dir / f"checkpoint_{date_key}.txt"
        try:
            with open(filepath, 'w', encoding='utf-8') as f:
                f.write(mblog_id)
            logger.info(f"断点已保存: {mblog_id}")
        except Exception as e:
            logger.error(f"保存断点失败: {e}")

    def get_checkpoint(self, date_key: str = None) -> Optional[str]:
        """获取断点信息"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        filepath = self.checkpoints_dir / f"checkpoint_{date_key}.txt"
        if filepath.exists():
            try:
                with open(filepath, 'r', encoding='utf-8') as f:
                    return f.read().strip()
            except Exception as e:
                logger.error(f"读取断点失败: {e}")
        return None

    def save_posts(
        self, 
        posts: List[Dict], 
        date_key: str = None,
        save_raw_api: bool = True
    ) -> int:
        """
        保存帖子数据
        
        Args:
            posts: 帖子列表
            date_key: 日期标识
            save_raw_api: 是否保存原始API响应
        """
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        count = 0
        if self.sqlite:
            count = self.sqlite.save_posts(posts, date_key)
        
        self.save_raw_data_json(posts, date_key=date_key)
        
        return count

    def save_api_response_batch(
        self, 
        url: str, 
        response_data: Any, 
        sequence: int,
        date_key: str = None
    ):
        """批量保存API响应"""
        if self.sqlite:
            self.sqlite.save_raw_api_response(url, response_data, date_key)
        
        self.save_raw_api_response(url, response_data, sequence, date_key)

    def load_posts(
        self, 
        date_key: str = None,
        start_time: str = None,
        end_time: str = None
    ) -> List[Dict]:
        """加载帖子数据"""
        if not date_key:
            date_key = datetime.now().strftime("%Y-%m-%d")
        
        if self.sqlite:
            return self.sqlite.get_posts_by_time_range(
                start_time=start_time,
                end_time=end_time,
                date_key=date_key
            )
        
        filepath = self.raw_dir / f"weibo_{date_key}.json"
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8') as f:
                return json.load(f)
        
        return []

    def save_analysis_report(
        self, 
        report_content: str, 
        post_count: int = 0,
        date_key: str = None,
        time_range_start: str = None,
        time_range_end: str = None,
        source: str = 'weibo'
    ) -> int:
        """保存AI分析报告"""
        if self.sqlite:
            return self.sqlite.save_analysis_report(
                report_content, post_count, date_key, 
                time_range_start, time_range_end, source
            )
        return 0

    def get_analysis_reports(self, date_key: str = None, limit: int = 10) -> List[Dict]:
        """获取AI分析报告"""
        if self.sqlite:
            return self.sqlite.get_analysis_reports(date_key, limit)
        return []

    def get_analysis_report_by_id(self, report_id: int) -> Optional[Dict]:
        """根据ID获取分析报告"""
        if self.sqlite:
            return self.sqlite.get_analysis_report_by_id(report_id)
        return None

    def cleanup_old_data(self, days: int = 7):
        """清理旧数据"""
        if self.sqlite:
            self.sqlite.cleanup_old_data(days)
        
        cutoff_date = (datetime.now() - timedelta(days=days)).strftime("%Y-%m-%d")
        for date_dir in self.raw_api_dir.iterdir():
            if date_dir.is_dir() and date_dir.name < cutoff_date:
                import shutil
                shutil.rmtree(date_dir)
                logger.info(f"已清理目录: {date_dir}")


def create_storage_manager(use_sqlite: bool = True) -> StorageManager:
    """工厂函数"""
    return StorageManager(use_sqlite=use_sqlite)
