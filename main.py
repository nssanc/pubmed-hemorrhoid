import feedparser
from deep_translator import GoogleTranslator
import time
from datetime import datetime
import os
import pytz
import json
import re

# ================= 配置区 =================
def get_rss_urls():
    urls = []
    if os.path.exists("feeds.txt"):
        with open("feeds.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if line and not line.startswith("#"):
                    urls.append(line)
    return urls
# =========================================

# 定义标准标题映射（英 -> 中）
# 只要遇到左边的词，就强制转换成右边的中文加粗格式
HEADER_MAPPING = {
    "BACKGROUND": "背景",
    "BACKGROUND AND PURPOSE": "背景与目的",
    "OBJECTIVE": "目的",
    "PURPOSE": "目的",
    "METHODS": "方法",
    "MATERIALS AND METHODS": "材料与方法",
    "METHODOLOGY": "方法论",
    "RESULTS": "结果",
    "FINDINGS": "发现",
    "CONCLUSION": "结论",
    "CONCLUSIONS": "结论",
    "DISCUSSION": "讨论",
    "SIGNIFICANCE": "意义",
    "INTRODUCTION": "介绍"
}

def clean_html_tags(text):
    """彻底清除 HTML 标签"""
    if not text: return ""
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<.*?>', '', text) # 去除所有剩余标签
    return text.strip()

def parse_and_translate_structured(raw_text, translator):
    """
    核心逻辑：
    1. 识别文章结构
    2. 分段拆解
    3. 逐段翻译
    4. 重新组装
    """
    if not raw_text:
        return "暂无摘要", "No abstract available"

    # 1. 预处理：清洗 HTML，提取关键词
    clean_text = clean_html_tags(raw_text)
    
    # 提取并移除 Keywords (通常在最后)
    keywords_en = ""
    kw_match = re.search(r'(?:Keywords?|Key words?)\s*[:](.*)', clean_text, re.IGNORECASE | re.DOTALL)
    if kw_match:
        keywords_en = kw_match.group(1).strip()
        clean_text = clean_text[:kw_match.start()].strip()

    # 2. 智能分段 (Magic Step)
    # 构建正则：寻找 "单词+冒号" 或 "单词+点" 的结构，且该单词在我们的标题库里
    # 例如匹配: "Background:" 或 "RESULTS."
    headers_pattern = "|".join([re.escape(k) for k in HEADER_MAPPING.keys()])
    # 正则逻辑：(行首 或 空格后) (标题词) (冒号 或 点)
    pattern = re.compile(r'(^|\n|\.\s+)\s*(' + headers_pattern + r')\s*[:\.]', re.IGNORECASE)
    
    # 使用 split 保留分隔符，这样我们能知道哪一段是哪个标题
    parts = pattern.split(clean_text)
    
    # parts[0] 是第一段之前的文字（通常是无标题的 Introduction）
    structured_content_zh = []
    structured_content_en = []
    
    # 处理第一段（如果有）
    if parts[0].strip():
        chunk = parts[0].strip()
        structured_content_en.append(chunk)
        try:
            # 第一段通常不长，直接翻
            trans = translator.translate(chunk[:3000])
            structured_content_zh.append(trans)
        except:
            structured_content_zh.append(chunk)

    # 处理后续的 "标题 + 内容" 对
    # split 后，parts 里的结构是：[前文, 分隔符, 标题, 内容, 分隔符, 标题, 内容...]
    # 我们从索引 1 开始遍历
    i = 1
    while i < len(parts) - 1:
        # parts[i] 是分隔符(换行等)，忽略
        header_raw = parts[i+1].upper() # 标题 (如 MATERIALS AND METHODS)
        content_raw = parts[i+2].strip() # 内容
        
        # 找到对应的中文标题
        header_zh = HEADER_MAPPING.get(header_raw, header_raw.capitalize())
        
        # === 英文版组装 ===
        # 格式： **Materials and methods:** ...
        en_section = f"**{header_raw.title()}:** {content_raw}"
        structured_content_en.append(en_section)
        
        # === 中文版翻译与组装 ===
        try:
            # 只翻译内容部分！标题我们直接用映射表，准确率 100%
            if content_raw:
                trans_content = translator.translate(content_raw[:4000]) # 防止超长
                zh_section = f"**{header_zh}：** {trans_content}"
                structured_content_zh.append(zh_section)
                time.sleep(0.3) # 稍微暂停防封
        except Exception as e:
            zh_section = f"**{header_zh}：** (翻译失败) {content_raw}"
            structured_content_zh.append(zh_section)
            print(f"分段翻译出错: {e}")

        i += 3 # 跳过一组 (分隔符, 标题, 内容)

    # 如果没找到任何标题（说明是无结构摘要），就回退到全文翻译
    if not structured_content_zh and clean_text:
        try:
            full_trans = translator.translate(clean_text[:4500])
            structured_content_zh.append(full_trans)
            structured_content_en.append(clean_text)
        except:
            structured_content_zh.append("翻译服务不可用")
            structured_content_en.append(clean_text)

    # 3. 翻译关键词
    keywords_zh = ""
    if keywords_en:
        try:
            keywords_zh = translator.translate(keywords_en)
        except:
            keywords_zh = keywords_en

    # 用换行符连接所有段落
    final_zh = "\n\n".join(structured_content_zh)
    final_en = "\n\n".join(structured_content_en)

    return final_zh, final_en, keywords_zh, keywords_en


def fetch_and_generate():
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    RSS_URLS = get_rss_urls()
    if not RSS_URLS:
        print("未找到 feeds.txt 或 内容为空")
        return

    translator = GoogleTranslator(source='auto', target='zh-CN')
    all_feeds_data = {}
    
    print(f"准备抓取 {len(RSS_URLS)} 个订阅源...")

    for url in RSS_URLS:
        try:
            print(f"正在连接: {url[:40]}...")
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', '未命名订阅源').replace("PubMed ", "")
            entries_data = []
            
            print(f"--> [{feed_title}] 发现 {len(feed.entries)} 篇...")
            
            for i, entry in enumerate(feed.entries):
                # 1. 标题
                title_en = entry.title
                try:
                    title_zh = translator.translate(title_en)
                except:
                    title_zh = title_en

                # 2. 核心：调用新的结构化解析函数
                raw_desc = entry.get('description', '')
                
                # 这里返回的已经是带 Markdown (**加粗**) 的文本了
                abstract_zh, abstract_en, kw_zh, kw_en = parse_and_translate_structured(raw_desc, translator)
                
                # 3. 作者
                authors = entry.get('author', 'No authors listed')

                entries_data.append({
                    "id": i,
                    "title_en": title_en,
                    "title_zh": title_zh,
                    "authors": authors,
                    "abstract_en": abstract_en,
                    "abstract_zh": abstract_zh,
                    "keywords_zh": kw_zh,
                    "keywords_en": kw_en,
                    "link": entry.link,
                    "date": entry.get('published', '')[:16]
                })
        
            all_feeds_data[feed_title] = entries_data
        except Exception as e:
            print(f"抓取 {url} 失败: {e}")

    # ================= HTML 生成部分 (优化了 CSS) =================
    json_data = json.dumps(all_feeds_data, ensure_ascii=False)
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")

    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PubMed DeepReader - {update_time}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {{ height: 100vh; overflow: hidden; }}
            .scrollbar-hide::-webkit-scrollbar {{ display: none; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
            
            /* 重点：优化 Markdown 渲染样式，模拟 PubMed 格式 */
            .prose strong {{ 
                color: #1e3a8a; /* 深蓝色 */
                font-weight: 800; 
                display: block; /* 让标题独占一行，类似图2 */
                margin-top: 1.2em; 
                margin-bottom: 0.4em;
                text-transform: uppercase;
                font-size: 0.85rem;
                letter-spacing: 0.05em;
            }}
            .prose p {{ margin-bottom: 0.8em; text-align: justify; line-height: 1.7; }}
            /* 第一段如果是引言，去掉上边距 */
            .prose p:first-of-type strong {{ margin-top: 0; }}
        </style>
    </head>
    <body class="bg-slate-100 flex flex-col" x-data="app()">
        <header class="bg-white border-b border-gray-200 h-14 flex items-center justify-between px-6 shadow-sm z-10 shrink-0">
            <div class="flex items-center gap-4">
                <div class="font-bold text-xl text-blue-900 tracking-tight">PubMed DeepReader</div>
                <div class="text-xs text-gray-400 mt-1">Updated: {update_time}</div>
            </div>
            <select x-model="currentFeed" @change="selectFeed()" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg p-2 max-w-xs">
                <template x-for="feedName in Object.keys(feeds)" :key="feedName">
                    <option :value="feedName" x-text="feedName"></option>
                </template>
            </select>
        </header>

        <div class="flex flex-1 overflow-hidden">
            <aside class="w-1/3 max-w-md bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
                <template x-for="paper in currentPapers" :key="paper.id">
                    <div @click="currentPaper = paper" 
                         :class="currentPaper.id === paper.id ? 'bg-blue-50 border-l-4 border-blue-600' : 'border-l-4 border-transparent hover:bg-gray-50'"
                         class="p-4 border-b border-gray-100 cursor-pointer transition group">
                        <h3 class="text-sm font-bold text-gray-800 line-clamp-2 leading-snug group-hover:text-blue-700" x-text="paper.title_zh"></h3>
                        <p class="text-xs text-gray-400 mt-1 truncate" x-text="paper.title_en"></p>
                    </div>
                </template>
            </aside>

            <main class="flex-1 bg-slate-50 overflow-y-auto p-6">
                <template x-if="currentPaper">
                    <div class="max-w-6xl mx-auto bg-white rounded-xl shadow-sm p-8 min-h-[90vh]">
                        <div class="border-b border-gray-100 pb-6 mb-6">
                            <h1 class="text-2xl font-bold text-gray-900 mb-2 leading-tight" x-text="currentPaper.title_zh"></h1>
                            <h2 class="text-lg text-gray-500 font-medium mb-4" x-text="currentPaper.title_en"></h2>
                            <div class="flex flex-wrap gap-4 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg border border-gray-100">
                                <span class="flex items-center">📅 <span class="ml-1" x-text="currentPaper.date"></span></span>
                                <span class="flex items-center">✍️ <span class="ml-1" x-text="currentPaper.authors"></span></span>
                                <a :href="currentPaper.link" target="_blank" class="text-blue-600 hover:underline font-bold ml-auto flex items-center">
                                    原文链接 <svg class="w-3 h-3 ml-1" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M10 6H6a2 2 0 00-2 2v10a2 2 0 002 2h10a2 2 0 002-2v-4M14 4h6m0 0v6m0-6L10 14"></path></svg>
                                </a>
                            </div>
                        </div>

                        <template x-if="currentPaper.keywords_zh">
                            <div class="mb-8 p-4 bg-blue-50/50 rounded-lg border border-blue-100">
                                <span class="text-xs font-bold text-blue-800 uppercase tracking-wide block mb-1">Keywords</span>
                                <div class="text-sm text-gray-700 font-medium">
                                    <span x-text="currentPaper.keywords_zh"></span>
                                    <div class="text-xs text-gray-400 mt-1 font-normal" x-text="currentPaper.keywords_en"></div>
                                </div>
                            </div>
                        </template>

                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-10">
                            <div>
                                <div class="flex items-center mb-4">
                                    <span class="w-1 h-6 bg-blue-600 mr-3 rounded-full"></span>
                                    <h3 class="font-bold text-xl text-gray-900">中文摘要</h3>
                                </div>
                                <div class="prose prose-sm prose-slate max-w-none text-gray-800" 
                                     x-html="marked.parse(currentPaper.abstract_zh)"></div>
                            </div>

                            <div>
                                <div class="flex items-center mb-4">
                                    <span class="w-1 h-6 bg-gray-300 mr-3 rounded-full"></span>
                                    <h3 class="font-bold text-gray-400 text-xl">Original Abstract</h3>
                                </div>
                                <div class="prose prose-sm prose-slate max-w-none text-gray-500" 
                                     x-html="marked.parse(currentPaper.abstract_en)"></div>
                            </div>
                        </div>
                    </div>
                </template>
                
                <template x-if="!currentPaper">
                    <div class="flex flex-col items-center justify-center h-full text-gray-400">
                        <svg class="w-16 h-16 mb-4 opacity-20" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="M19 20H5a2 2 0 01-2-2V6a2 2 0 012-2h10a2 2 0 012 2v1m2 13a2 2 0 01-2-2V7m2 13a2 2 0 002-2V9a2 2 0 00-2-2h-2m-4-3H9M7 16h6M7 8h6v4H7V8z"></path></svg>
                        <p>请选择左侧文章开始阅读</p>
                    </div>
                </template>
            </main>
        </div>

        <script>
            function app() {{
                return {{
                    feeds: {json_data},
                    currentFeed: '',
                    currentPapers: [],
                    currentPaper: null,
                    init() {{
                        const ks = Object.keys(this.feeds);
                        if(ks.length > 0) {{ 
                            this.currentFeed = ks[0]; 
                            this.selectFeed(); 
                        }}
                    }},
                    selectFeed() {{
                        this.currentPapers = this.feeds[this.currentFeed];
                        this.currentPaper = this.currentPapers.length > 0 ? this.currentPapers[0] : null;
                        document.querySelector('aside').scrollTop = 0;
                    }}
                }}
            }}
        </script>
    </body>
    </html>
    """
    
    with open(os.path.join(output_dir, "index.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    with open(os.path.join(output_dir, f"archive_{datetime.now(tz).strftime('%Y%m%d')}.html"), "w", encoding="utf-8") as f:
        f.write(html_content)
    print("HTML 生成完毕！")

if __name__ == "__main__":
    fetch_and_generate()
