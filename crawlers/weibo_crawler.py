"""
微博爬虫 - 支持滚动加载和API数据即时保存
"""
import os
import time
import json
import pickle
from typing import Dict, List, Optional, Any
from datetime import datetime, timedelta
import random
from DrissionPage import ChromiumOptions, Chromium

from crawlers.base_crawler import BaseCrawler
from utils.action_click import HumanAction
from utils.logger_config import setup_logging
from config.settings import WEIBO_API_ENDPOINTS, COLLECTOR_CONFIG
import logging

setup_logging(logging.INFO)
logger = logging.getLogger(__name__)


class WeiboCrawler(BaseCrawler):
    def __init__(self, headless: bool = False, user_data_path: str = None):
        super().__init__()
        self.co = ChromiumOptions()
        
        if user_data_path:
            self.co.set_user_data_path(user_data_path)
        
        self.co.set_argument("--mute-audio")
        # 禁用图片加载以提升速度
        self.co.set_argument("--blink-settings=imagesEnabled=false")
        
        if headless:
            self.co.headless(True)
            
        self.browser = Chromium(self.co)
        
        # 尝试复用已有的微博标签页或创建新标签页
        self.tab = self._get_tab("https://weibo.com")
            
        self.bot = HumanAction(self.tab)
        
        # cookies 文件路径改为 data/cookies/weibo.pkl
        from config.settings import COOKIES_DIR
        self.cookie_file = str(COOKIES_DIR / "weibo.pkl")

    def _get_tab(self, url: str):
        """智能获取 or 创建 Tab，并确保加载"""
        # 1. 检查当前活动标签页
        current_tab = self.browser.latest_tab
        if "weibo.com" in current_tab.url:
            logger.info(f"当前页面已是目标页面: {url}")
            return current_tab

        # 2. 尝试查找已存在的标签页
        try:
            # DrissionPage 的 get_tab 可以按 url 关键词查找
            tab = self.browser.get_tab(url="weibo.com")
            if tab:
                logger.info(f"切换到已存在的页面: {tab.title}")
                tab.activate()
                return tab
        except Exception:
            pass

        # 3. 新打开标签页
        logger.info(f"新打开页面: {url}")
        tab = self.browser.new_tab(url=url)
        # 加载完稍微等一下
        time.sleep(2)
        return tab
        
        # cookies 文件路径改为 data 目录
        # cookies 文件路径改为 data/cookies/weibo.pkl
        from config.settings import COOKIES_DIR
        self.cookie_file = str(COOKIES_DIR / "weibo.pkl")

    @property
    def source_name(self) -> str:
        """数据源名称"""
        return 'weibo'

    def login(self, force_relogin: bool = False) -> None:
        """
        处理登录逻辑
        
        Args:
            force_relogin: 是否强制重新登录（删除旧 cookies）
        """
        # 如果强制重登录，删除旧 cookies
        if force_relogin and os.path.exists(self.cookie_file):
            logger.info("强制重新登录，删除旧 cookies...")
            os.remove(self.cookie_file)
        
        self.tab.get("https://weibo.com")
        self.bot.wait_random(2, 4)
        
        # 尝试加载 cookies
        if os.path.exists(self.cookie_file):
            logger.info("正在加载 Cookie...")
            try:
                with open(self.cookie_file, 'rb') as f:
                    cookies = pickle.load(f)
                    for cookie in cookies:
                        self.tab.set.cookies(cookie)
                self.tab.refresh()
                self.bot.wait_random(3, 5)
            except Exception as e:
                logger.error(f"加载 Cookie 失败: {e}")

        # 检查登录状态
        if self._is_logged_in():
            logger.info("已登录。")
        else:
            logger.info("未登录。请在浏览器中扫描二维码或手动登录。")
            
            logger.warning("未登录。由于微博登录机制复杂，已取消由于自动登录尝试。")
            
            # 直接抛出异常，由上层 main.py 捕获并发送飞书通知
            raise Exception("微博未登录或 Cookie 已过期，请手动在浏览器登录并更新 Cookie。")

    def _is_logged_in(self) -> bool:
        """检查是否已登录"""
        try:
            # 检查是否有登录按钮
            ele = self.tab.ele('text:登录', timeout=2)
            if ele:
                return False
            # 双重检查：访问需要登录的页面
            return True
        except Exception as e:
            logger.debug(f"登录状态检查异常: {e}")
            return False
    
    def _auto_login(self, username: str, password: str) -> None:
        """
        自动登录（账号密码方式）
        注意：微博可能需要验证码，此方法不一定总能成功
        """
        logger.info("尝试账号密码登录...")
        # 这里可以实现自动填写账号密码的逻辑
        # 由于微博登录较复杂（可能需要验证码），建议使用二维码扫码
        raise NotImplementedError("账号密码登录暂未实现，请使用二维码扫码登录")

    def _save_cookies(self) -> None:
        """保存Cookie"""
        full_cookies = self.tab.cookies(all_info=True)
        with open(self.cookie_file, 'wb') as f:
            pickle.dump(full_cookies, f)
        logger.info("Cookie 已保存。")

    def fetch_latest_posts(
        self,
        lookback_hours: int = 8,
        max_duration_seconds: int = None,
        resume_from_id: str = None,
        scroll_interval: tuple = None,
        no_new_data_timeout: int = 300,
        strict_time_mode: bool = False
    ) -> List[Dict[str, Any]]:
        """
        抓取"特别关注"的帖子(滚动加载版)
        
        Args:
            lookback_hours: 回溯时间(小时)，默认8小时
            max_duration_seconds: 最大采集时长(秒)，None表示不限制
            resume_from_id: 断点续传的微博ID，采集到该ID为止
            scroll_interval: 滚动间隔(秒)，默认从配置读取
            no_new_data_timeout: 无新数据超时时间(秒)
            strict_time_mode: 严格时间模式，True时仅根据时间判断停止，忽略checkpoint ID
            
        Returns:
            帖子列表
        """
        # 检查登录状态，如果未登录则自动重新登录
        logger.info("检查登录状态...")
        if not self._is_logged_in():
            logger.warning("检测到 cookies 已过期，尝试重新登录...")
            self.login(force_relogin=True)
        
        from data_manager.storage import create_storage_manager
        storage = create_storage_manager()
        
        date_key = datetime.now().strftime("%Y-%m-%d")
        api_target = WEIBO_API_ENDPOINTS['friends_timeline']
        
        if scroll_interval is None:
            scroll_interval = COLLECTOR_CONFIG.get("scroll_interval", (2, 4))
        
        logger.info(f"开始采集特别关注，回溯{lookback_hours}小时...")
        
        cutoff_time = datetime.now() - timedelta(hours=lookback_hours)
        seen_ids = set()
        collected_posts = []
        api_sequence = 0
        last_new_post_time = time.time()
        start_time = time.time()
        
        try:
            self.tab.listen.start(api_target)
            
            if not self._click_special_follow():
                logger.error("无法点击特别关注按钮")
                return collected_posts
            
            # 主采集循环
            reached_time_boundary = False
            time_boundary_reached_at = None
            grace_period_seconds = 10  # 到达时间边界后继续滚动的时间
            scroll_count = 0
            
            while True:
                # 检查终止条件
                if max_duration_seconds and (time.time() - start_time) > max_duration_seconds:
                    logger.info("达到最大采集时长，停止")
                    break
                
                # 如果已到达时间边界，检查是否超过宽限期
                if reached_time_boundary:
                    if time.time() - time_boundary_reached_at > grace_period_seconds:
                        logger.info(f"已到达时间边界，宽限期{grace_period_seconds}秒已过，停止采集")
                        break
                
                # 检查无新数据超时
                if time.time() - last_new_post_time > no_new_data_timeout:
                    logger.info(f"{no_new_data_timeout}秒无新数据，停止采集")
                    break
                
                # 先滚动页面（触发新数据加载）
                scroll_count += 1
                self.tab.scroll.down()
                
                # 短暂等待让页面加载（减少等待时间）
                time.sleep(0.5)
                
                # 尝试获取API响应（非阻塞，快速检查）
                try:
                    packet = self.tab.listen.wait(timeout=1)  # 减少超时时间
                    if packet:
                        new_count, hit_time_boundary = self._process_packet(
                            packet, storage, seen_ids, collected_posts,
                            cutoff_time, resume_from_id, api_sequence, date_key,
                            strict_time_mode
                        )
                        
                        # 首次到达时间边界
                        if hit_time_boundary and not reached_time_boundary:
                            reached_time_boundary = True
                            time_boundary_reached_at = time.time()
                            logger.info(f"到达时间边界，继续滚动{grace_period_seconds}秒以确保完整性")
                            
                        if new_count > 0:
                            last_new_post_time = time.time()
                            api_sequence += 1
                except Exception as e:
                    logger.debug(f"等待API响应: {e}")
                
                # 随机等待（减少等待时间）
                time.sleep(random.uniform(0.5, 1.5))
                
                if scroll_count % 10 == 0:
                    logger.info(f"已滚动 {scroll_count} 次，采集 {len(collected_posts)} 条帖子")
            
            
            
        except Exception as e:
            logger.error(f"采集过程出错: {e}")
            import traceback
            traceback.print_exc()
        finally:
            self.tab.listen.stop()
        
        logger.info(f"共采集 {len(collected_posts)} 篇帖子")
        
        if collected_posts:
            last_post = collected_posts[-1]
            storage.save_checkpoint(last_post.get('mblog_id', ''), date_key)
        
        return collected_posts

    def _process_packet(
        self,
        packet,
        storage,
        seen_ids,
        collected_posts,
        cutoff_time,
        resume_from_id,
        api_sequence,
        date_key,
        strict_time_mode: bool = False
    ) -> tuple[int, bool]:
        """处理单个数据包，返回 (新增帖子数, 是否到达时间边界)"""
        try:
            raw_data = packet.response.body
            
            if isinstance(raw_data, str):
                try:
                    raw_data = json.loads(raw_data)
                except:
                    return 0, False
            
            if not isinstance(raw_data, dict):
                return 0, False
            
            # 保存原始API响应
            storage.save_api_response_batch(
                url=packet.url,
                response_data=raw_data,
                sequence=api_sequence,
                date_key=date_key
            )
            
            # 解析帖子
            posts = self._parse_api_response(raw_data)
            new_count = 0
            hit_time_boundary = False
            
            for post in posts:
                mblog_id = post.get('mblog_id', '')
                
                if mblog_id in seen_ids:
                    continue
                
                # 检查时间回溯
                post_time = self._parse_time(post.get('publish_time', ''))
                if post_time and post_time < cutoff_time:
                    logger.debug(f"帖子 {mblog_id} 时间 {post_time} 早于截止时间 {cutoff_time}")
                    hit_time_boundary = True
                    # 不再continue，仍然保存这条帖子，因为可能是乱序
                
                # 检查断点（严格时间模式下跳过）
                if not strict_time_mode and resume_from_id and mblog_id == resume_from_id:
                    logger.info(f"遇到断点ID {resume_from_id}")
                    hit_time_boundary = True
                    continue
                
                seen_ids.add(mblog_id)
                post['collected_at'] = datetime.now().isoformat()
                post['date_key'] = date_key
                collected_posts.append(post)
                new_count += 1
            
            if new_count > 0:
                logger.info(f"新增 {new_count} 条帖子，累计 {len(collected_posts)} 条")
            
            return new_count, hit_time_boundary
            
        except Exception as e:
            logger.warning(f"处理数据包失败: {e}")
            return 0, False

    def _click_special_follow(self) -> bool:
        """点击特别关注按钮"""
        try:
            # 显式等待页面加载关键元素 (左侧导航栏或特别关注按钮)
            # 尝试等待最多 5 秒
            logger.info("等待'特别关注'按钮出现...")
            if self.tab.ele('text:特别关注', timeout=5):
                if self.bot.human_click(loc='text:特别关注', desc="特别关注分组"):
                    logger.info("成功点击'特别关注'")
                    return True
            else:
                logger.warning("未找到'特别关注'按钮 (超时)")
        except Exception as e:
            logger.debug(f"首次查找/点击失败: {e}")
            pass
        
        # 只有在第一次明确失败（超时或报错）后，才考虑刷新
        # 但如果页面本身就在加载中，刷新可能会导致死循环或更慢
        # 我们尝试用更宽泛的策略：查找是否有左侧导航栏
        
        logger.info("尝试刷新页面重试...")
        self.tab.refresh()
        
        try:
            # 刷新后等待时间稍长一点
            if self.tab.ele('text:特别关注', timeout=8):
                if self.bot.human_click(loc='text:特别关注', desc="特别关注分组"):
                    logger.info("重试点击成功")
                    return True
        except Exception:
            pass
        
        logger.error("无法找到并点击'特别关注'按钮")
        return False

    def _parse_api_response(self, data: Dict) -> List[Dict]:
        """解析API响应数据"""
        posts = []
        statuses = data.get('statuses', [])
        
        for status in statuses:
            if not isinstance(status, dict):
                continue
            try:
                user = status.get('user', {})
                author = user.get('screen_name', 'Unknown')
                user_id = user.get('id', '')
                mblog_id = status.get('mblogid', '')
                
                content = status.get('text_raw', '') or status.get('text', '')
                
                post_url = f"https://weibo.com/{user_id}/{mblog_id}"
                
                created_at = status.get('created_at', '')
                try:
                    dt = self._parse_time(created_at)
                    if dt:
                        created_at = dt.strftime("%Y-%m-%d %H:%M:%S")
                except Exception:
                    pass
                
                # 安全解析图片列表
                pic_ids = status.get('pic_ids', [])
                images = []
                if isinstance(pic_ids, list):
                    images = [img.get('url', '') for img in pic_ids if isinstance(img, dict)]
                
                posts.append({
                    "mblog_id": mblog_id,
                    "author": author,
                    "author_id": user_id,
                    "content": content,
                    "publish_time": created_at,
                    "url": post_url,
                    "images": images,
                    "video": status.get('page_info', {}).get('media_info', {}).get('play_url', ''),
                    "reposts_count": status.get('attitudes_count', 0),
                    "comments_count": status.get('comments_count', 0),
                    "attitudes_count": status.get('attitudes_count', 0),
                })
            except Exception as e:
                logger.warning(f"解析单条微博失败: {e}, status类型: {type(status)}, 前100字符: {str(status)[:100]}")
        
        return posts

    def _parse_time(self, time_str: str) -> Optional[datetime]:
        """解析微博时间字符串"""
        if not time_str:
            return None
        
        try:
            formats = [
                "%a %b %d %H:%M:%S %z %Y",
                "%Y-%m-%d %H:%M:%S",
                "%Y-%m-%d",
            ]
            for fmt in formats:
                try:
                    dt = datetime.strptime(time_str, fmt)
                    # 统一转换为 naive datetime (忽略时区差异，简化比较)
                    if dt.tzinfo:
                        dt = dt.replace(tzinfo=None)
                    return dt
                except:
                    continue
        except:
            pass
        
        return None

    def close(self) -> None:
        """关闭浏览器"""
        try:
            self.browser.quit()
        except:
            pass
