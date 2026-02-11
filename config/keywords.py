"""
AI关键词配置文件
支持字符串和正则表达式（以 r"" 开头或包含正则特殊字符）
"""

AI_CORE_KEYWORDS = [
    # 核心术语
    "AI", "人工智能", "大模型", "LLM", "神经网络", "Deep Learning", "Machine Learning",
    "AGI", "AIGC", "Generative AI", "生成式AI",
    
    # 知名模型与公司
    "GPT", "ChatGPT", "OpenAI", "Sora",
    "Claude", "Anthropic",
    "Gemini", "Google DeepMind",
    "Llama", "Meta AI",
    "DeepSeek", "幻方量化",
    "Mistral", "Mixtral",
    "Qwen", "通义千问", "Alibaba Cloud",
    "GLM", "ChatGLM", "智谱AI",
    "Kimi", "Moonshot", "月之暗面",
    "Baichuan", "百川智能",
    
    # 技术与架构
    "Transformer", "Attention Mechanism", "MoE", "Mixture of Experts",
    "RAG", "Retrieval Augmented Generation",
    "Agent", "智能体", "Multi-Agent",
    "Embedding", "Vector Database", "向量数据库",
    "Fine-tuning", "微调", "RLHF", "DPO", "PPO",
    "Quantization", "量化", "GGML", "GGUF",
    "LoRA", "QLoRA",
    "Diffusion Model", "Stable Diffusion", "Midjourney",
    "Vision Transformer", "ViT", "Multimodal", "多模态",
    
    # 正则表达式示例 (以 r'...' 格式书写，实际上这里是字符串列表，但在分析器中会作为正则处理)
    r"GPT-[345]",
    r"Llama\s*[23]",
    r"Claude\s*[23](\.\d)?",
    r"Gemini\s*(Pro|Ultra|Nano)?",
    r"DeepSeek-V\d+",
    r"Qwen-\d+B",
    
    # 应用领域
    "Coding Assistant", "Copilot", "AI编程",
    "AI Search", "AI搜索", "Perplexity",
    "Embodied AI", "具身智能", "Robot",
    "Autonomous Driving", "自动驾驶", "FSD",
]
