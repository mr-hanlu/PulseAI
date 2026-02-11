import requests
import json
import logging
import re
from typing import Dict, Any
from config.settings import WEBHOOK_ADDRESS

logger = logging.getLogger(__name__)

def send_feishu_notification(
    success: bool,
    message: str,
    data: Dict[str, Any] = None
):
    """
    发送飞书 Webhook 通知
    
    Args:
        success: 是否成功
        message: 消息提示
        data: 数据内容, 包含 content, start_time, end_time, post_count 等
    """
    if not WEBHOOK_ADDRESS:
        logger.debug("未配置 Webhook_address，跳过飞书通知")
        return

    headers = {
        "Content-Type": "application/json"
    }
    
    payload = {
        "success": success,
        "message": message,
        "data": data or {}
    }
    
    # 飞书消息格式优化：将Markdown标题转换为绿色字体
    if payload["data"] and "content" in payload["data"] and isinstance(payload["data"]["content"], str):
        payload["data"]["content"] = re.sub(
            r"^##\s+(.+)$", 
            r"<font color='green'>\1</font>", 
            payload["data"]["content"], 
            flags=re.MULTILINE
        )
    
    try:
        logger.info(f"正在发送飞书通知: {json.dumps(payload, ensure_ascii=False)}")
        response = requests.post(WEBHOOK_ADDRESS, headers=headers, json=payload, timeout=10)
        response.raise_for_status()
        logger.info("飞书通知发送成功")
    except Exception as e:
        logger.error(f"飞书通知发送失败: {e}")
