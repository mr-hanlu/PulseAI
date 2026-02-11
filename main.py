"""
AI热点监控系统 - 主程序入口
"""
import argparse
import logging
import sys
import os

sys.path.append(os.path.dirname(os.path.abspath(__file__)))

from crawlers.weibo_crawler import WeiboCrawler
from data_manager.storage import create_storage_manager
from analyzer.content_analyzer import ContentAnalyzer
from utils.logger_config import setup_logging
from utils.notifier import send_feishu_notification

setup_logging(logging.INFO)
logger = logging.getLogger("Main")

def handle_error(error_msg: str):
    """处理错误并发送通知"""
    logger.error(error_msg)
    send_feishu_notification(
        success=False,
        message=error_msg,
        data={}
    )

def main():
    parser = argparse.ArgumentParser(description="微博 AI 热点智能体")
    parser.add_argument("--login", action="store_true", help="运行登录流程")
    parser.add_argument("--crawl", action="store_true", help="抓取特别关注列表")
    parser.add_argument("--analyze", action="store_true", help="分析本地数据")
    parser.add_argument("--all", action="store_true", help="运行完整流程 (登录检查 -> 抓取 -> 分析)")
    parser.add_argument("--headless", action="store_true", help="在无头模式下运行浏览器 (不显示界面)")
    parser.add_argument("--lookback-hours", type=int, default=8, help="回溯时间(小时)，默认8小时")
    parser.add_argument("--max-duration", type=int, default=None, help="最大采集时长(秒)")
    parser.add_argument("--strict-time", action="store_true", help="严格时间模式，仅根据时间判断停止，忽略checkpoint ID")
    parser.add_argument("--close-browser", action="store_true", help="完成后关闭浏览器")
    
    args = parser.parse_args()
    
    storage = create_storage_manager()
    
    if args.login:
        crawler = WeiboCrawler(headless=False)
        try:
            crawler.login()
        finally:
            crawler.close()
            
    if args.crawl or args.all:
        crawler = WeiboCrawler(headless=args.headless)
        try:
            crawler.login()
            
            posts = crawler.fetch_latest_posts(
                lookback_hours=args.lookback_hours,
                max_duration_seconds=args.max_duration,
                strict_time_mode=args.strict_time
            )
            
            if posts:
                logger.info(f"抓取了 {len(posts)} 篇帖子。")
                storage.save_posts(posts)
            else:
                logger.warning("未找到帖子。")
        except Exception as e:
            error_msg = f"抓取失败: {e}"
            handle_error(error_msg)
            import traceback
            traceback.print_exc()
        finally:
            if args.close_browser:
                crawler.close()
            else:
                logger.info("浏览器保持打开状态，请手动关闭或使用 --close-browser 参数")
            
    if args.analyze or args.all:
        # 计算时间范围
        from datetime import datetime, timedelta
        end_time = datetime.now()
        start_time = end_time - timedelta(hours=args.lookback_hours)
        time_range_start = start_time.strftime("%Y-%m-%d %H:%M:%S")
        time_range_end = end_time.strftime("%Y-%m-%d %H:%M:%S")
        
        logger.info(f"加载分析数据，时间范围: {time_range_start} - {time_range_end}")
        
        data = storage.load_posts(
            start_time=time_range_start,
            end_time=time_range_end
        )
        
        if not data:
            logger.error("未找到可分析的数据。")
            return
            
        analyzer = ContentAnalyzer()
        report = analyzer.analyze_posts(
            data, 
            storage=storage,
            time_range_start=time_range_start,
            time_range_end=time_range_end,
            source='weibo'
        )
        
        print("\n" + "="*40)
        print(report)
        print("="*40 + "\n")
        
        # 发送飞书通知 (成功)
        send_feishu_notification(
            success=True,
            message="AI热点监控完成",
            data={
                "post_count": len(data),
                "start_time": time_range_start,
                "end_time": time_range_end,
                "content": report
            }
        )

    if not any([args.login, args.crawl, args.analyze, args.all]):
        parser.print_help()


if __name__ == "__main__":
    main()
