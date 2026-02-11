import logging
import json
import requests
import re
from config.settings import LLM_CONFIG
from config.keywords import AI_CORE_KEYWORDS

class ContentAnalyzer:
    def __init__(self, api_key=None, provider="openai"):
        self.logger = logging.getLogger(__name__)
        # 优先使用传入的 api_key，否则使用配置文件
        self.api_key = api_key if api_key else LLM_CONFIG.get("api_key")
        self.base_url = LLM_CONFIG.get("base_url")
        self.model = LLM_CONFIG.get("model_name")

    def analyze_posts(self, posts, storage=None, time_range_start=None, time_range_end=None, source='weibo'):
        """
        使用 LLM 分析帖子列表并返回结构化报告。
        
        Args:
            posts: 帖子列表
            storage: StorageManager 实例，用于保存分析结果
            time_range_start: 分析的起始时间
            time_range_end: 分析的结束时间
            source: 数据来源
        """
        self.logger.info(f"正在分析 {len(posts)} 篇帖子...")
        
        if not posts:
            return "本次没有采集到任何帖子。"

        # 1. 本地关键词过滤
        filtered_posts = self._filter_posts(posts)
        if not filtered_posts:
            self.logger.info("本地过滤后无 AI 相关内容，跳过 LLM 分析。")
            report = "本地过滤后无 AI/科技相关热点。"
            if storage:
                storage.save_analysis_report(
                    report, len(posts), 
                    time_range_start=time_range_start,
                    time_range_end=time_range_end,
                    source=source
                )
            return report
            
        self.logger.info(f"过滤后剩余 {len(filtered_posts)}/{len(posts)} 篇相关帖子，准备发送给 LLM...")

        # 简化数据以节省 Context
        simplified_posts = []
        for p in filtered_posts:
            simplified_posts.append({
                "author": p.get("author"),
                "content": p.get("content"),
                "url": p.get("url"),
                "time": p.get("publish_time", p.get("scraped_at"))
            })
            
        posts_text = json.dumps(simplified_posts, ensure_ascii=False, indent=2)
        
        # 防止过长 (简单截断，生产环境应更严谨)
        if len(posts_text) > 10000:
            posts_text = posts_text[:10000] + "...(truncated)"
        
        time_range_info = ""
        if time_range_start and time_range_end:
            time_range_info = f"\n分析时间段: {time_range_start} ~ {time_range_end}\n"
        
        prompt = f"""
请分析以下微博帖子数据，提取与 "AI", "人工智能", "大模型", "LLM", "Agent", "ChatGPT", "DeepSeek", "Sora" 等科技前沿相关的热点内容。
{time_range_info}
数据如下:
{posts_text}

**重要要求**：请按**话题**聚合相关内容，而不是逐条列出。

输出格式示例：
## 话题1: DeepSeek R1 开源
**核心观点**: DeepSeek发布R1模型，性能超越GPT-4，引发业界关注
**相关帖子**:
- [@AI科技评论](链接1): 详细测评数据
- [@机器之心](链接2): 技术架构解读
- [@量子位](链接3): 行业影响分析

## 话题2: Sora 视频生成更新
**核心观点**: OpenAI更新Sora模型，视频生成质量提升
**相关帖子**:
- [@作者A](链接): 观点摘要

**注意事项**:
1. 如果多个帖子讨论同一个话题（如"DeepSeek R1"），请合并到一个话题下
2. 每个话题下列出所有相关帖子的作者和链接
3. 忽略与 AI/科技无关的内容
4. 如果所有帖子均无关，输出 "**今日无 AI 相关热点**"
"""
        
        try:
            report = self._call_llm(prompt)
            # 保存分析结果到数据库
            if storage:
                storage.save_analysis_report(
                    report, len(filtered_posts),
                    time_range_start=time_range_start,
                    time_range_end=time_range_end,
                    source=source
                )
            return report
        except Exception as e:
            self.logger.error(f"LLM 分析失败: {e}")
            error_report = f"报告生成失败。错误信息: {e}\n\n(请检查 settings.py 中的 API Key配置)"
            if storage:
                storage.save_analysis_report(
                    error_report, len(posts),
                    time_range_start=time_range_start,
                    time_range_end=time_range_end,
                    source=source
                )
            return error_report

    def _call_llm(self, prompt):
        # 检查是否是默认占位符
        if not self.api_key or "YOUR_API_KEY" in self.api_key:
             self.logger.warning("未配置有效的 API Key。返回模拟结果。")
             return self._mock_result()
             
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        # 处理 Base URL 格式
        base = self.base_url.rstrip('/')
        url = f"{base}/chat/completions"
        # url = f"{base}"
            
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的科技情报分析师，擅长从社交媒体数据中提取AI热点。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": 0.3
        }
        
        self.logger.info(f"正在调用 LLM: {self.model} at {base}")
        try:
            response = requests.post(url, headers=headers, json=payload, timeout=200)
            response.raise_for_status()
            result = response.json()
            return result['choices'][0]['message']['content']
        except requests.exceptions.RequestException as e:
            self.logger.error(f"API 请求异常: {e}")
            if hasattr(e, 'response') and e.response:
                self.logger.error(f"服务端返回: {e.response.text}")
            raise

    def _mock_result(self):
        """
        ### 核心摘要
        1. **DeepSeek 新模型发布**: 社区热议 DeepSeek-V3 的性能表现。
        2. **英伟达财报发布**: 股价波动引发 AI 算力投资讨论。
        
        ### 详细解读
        - **[示例作者](https://weibo.com)**: 这是一个模拟的分析条目...
        """

    def _filter_posts(self, posts):
        """
        基于本地关键词库过滤帖子
        """
        filtered = []
        
        # 预编译关键词正则
        patterns = []
        for kw in AI_CORE_KEYWORDS:
            try:
                # 尝试直接编译，使用 IGNORECASE 忽略大小写
                pattern = re.compile(kw, re.IGNORECASE)
                patterns.append(pattern)
            except re.error:
                # 如果编译失败，回退到转义字符串匹配，同样忽略大小写
                self.logger.warning(f"关键词 '{kw}' 正则编译失败，降级为普通字符串匹配")
                patterns.append(re.compile(re.escape(kw), re.IGNORECASE))

        for post in posts:
            content = post.get("content", "") or ""
            author = post.get("author", "") or ""
            
            # 组合搜索文本
            text_to_search = f"{content} {author}"
            
            is_relevant = False
            for pattern in patterns:
                if pattern.search(text_to_search):
                    is_relevant = True
                    break
            
            if is_relevant:
                filtered.append(post)
                
        return filtered
