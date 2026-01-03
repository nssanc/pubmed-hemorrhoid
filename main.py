import feedparser
from deep_translator import GoogleTranslator
import time
from datetime import datetime
import os
import pytz
import json
import re

# =========================================
# 不再需要在代码里硬编码链接了
# 程序会自动读取同目录下的 feeds.txt
# =========================================

def get_rss_urls():
    """读取 feeds.txt 文件中的链接"""
    urls = []
    if os.path.exists("feeds.txt"):
        with open("feeds.txt", "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                # 忽略空行和以 # 开头的注释行
                if line and not line.startswith("#"):
                    urls.append(line)
    return urls

def process_text_structure(text):
    """(保持原有的清洗逻辑不变)"""
    if not text:
        return "", "", ""
    text = text.replace("<b>", "").replace("</b>", "")
    text = re.sub(r'<br\s*/?>', '\n', text)
    text = re.sub(r'<p>', '\n', text)
    text = re.sub(r'</p>', '\n', text)
    text = re.sub(r'<.*?>', '', text)
    keywords = ""
    keywords_match = re.search(r'(Keywords?:|Key words?:)(.*)', text, re.IGNORECASE | re.DOTALL)
    if keywords_match:
        keywords = keywords_match.group(2).strip()
        text = text[:keywords_match.start()]
    text = re.sub(r'Copyright ©.*', '', text, flags=re.IGNORECASE)
    headers = ["Abstract", "Background and purpose", "Background", "Objective", "Purpose",
               "Materials and methods", "Methods", "Design", "Results", "Findings",
               "Conclusion", "Conclusions", "Discussion"]
    structured_text = text.strip()
    for header in headers:
        pattern = re.compile(r'(^|\n|\.\s)\s*(' + re.escape(header) + r')\s*[:\.]', re.IGNORECASE)
        structured_text = pattern.sub(r'\n\n🟢 \2: ', structured_text)
    return structured_text, keywords

def fetch_and_generate():
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    # === 修改点：这里调用函数读取文件 ===
    RSS_URLS = get_rss_urls() 
    
    if not RSS_URLS:
        print("警告：feeds.txt 为空或未找到，请添加订阅链接！")
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
            
            # (以下逻辑保持完全不变)
            print(f"--> [{feed_title}] 发现 {len(feed.entries)} 篇文章...")
            
            for i, entry in enumerate(feed.entries):
                title_en = entry.title
                try:
                    title_zh = translator.translate(title_en)
                except:
                    title_zh = title_en
                
                raw_description = entry.get('description', '')
                abstract_en_structured, keywords_en = process_text_structure(raw_description)
                
                abstract_zh = "暂无摘要"
                if abstract_en_structured:
                    if len(abstract_en_structured) > 4500:
                        abstract_en_structured = abstract_en_structured[:4500] + "..."
                    try:
                        abstract_zh = translator.translate(abstract_en_structured)
                        abstract_zh = abstract_zh.replace("🟢", "\n\n**").replace("：", "：** ").replace(":", ":** ")
                        key_map = {"背景": "Background", "方法": "Methods", "结果": "Results", "结论": "Conclusion"}
                        for ch_key, en_key in key_map.items():
                             if f"{ch_key}" in abstract_zh and "**" not in abstract_zh:
                                  abstract_zh = abstract_zh.replace(ch_key, f"\n\n**{ch_key}**")
                    except:
                        abstract_zh = "翻译服务暂时不可用。"

                keywords_zh = ""
                if keywords_en:
                    try:
                        keywords_zh = translator.translate(keywords_en)
                    except:
                        keywords_zh = keywords_en

                entries_data.append({
                    "id": i,
                    "title_en": title_en,
                    "title_zh": title_zh,
                    "authors": entry.get('author', 'No authors listed'),
                    "abstract_en": abstract_en_structured.replace("🟢", ""),
                    "abstract_zh": abstract_zh,
                    "keywords_en": keywords_en,
                    "keywords_zh": keywords_zh,
                    "link": entry.link,
                    "date": entry.get('published', '')[:16]
                })
                time.sleep(0.2)
            
            all_feeds_data[feed_title] = entries_data
        except Exception as e:
            print(f"抓取 {url} 失败: {e}")

    # 生成 HTML (保持不变，省略重复代码以节省空间，请确保下面的 HTML 生成部分还在)
    json_data = json.dumps(all_feeds_data, ensure_ascii=False)
    tz = pytz.timezone('Asia/Shanghai')
    update_time = datetime.now(tz).strftime("%Y-%m-%d %H:%M")
    
    # ... 这里是你原来的 HTML 模板代码 ...
    # (为了代码简洁，我这里不重复贴 HTML 模板了，记得保留原文件里的 html_content 部分)
    # 只要把原来的 RSS_URLS = ... 删掉，加上 get_rss_urls() 函数即可。
    
    # 既然你可能直接复制，我把最关键的 HTML 写入部分补上以防万一：
    html_content = f"""
    <!DOCTYPE html>
    <html lang="zh-CN">
    <head>
        <meta charset="UTF-8">
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <title>PubMed 深度阅读 - {update_time}</title>
        <script src="https://cdn.tailwindcss.com"></script>
        <script defer src="https://cdn.jsdelivr.net/npm/alpinejs@3.x.x/dist/cdn.min.js"></script>
        <script src="https://cdn.jsdelivr.net/npm/marked/marked.min.js"></script>
        <style>
            body {{ height: 100vh; overflow: hidden; }}
            .scrollbar-hide::-webkit-scrollbar {{ display: none; }}
            ::-webkit-scrollbar {{ width: 6px; }}
            ::-webkit-scrollbar-track {{ background: #f1f1f1; }}
            ::-webkit-scrollbar-thumb {{ background: #cbd5e1; border-radius: 3px; }}
            .prose strong {{ color: #1e40af; font-weight: 800; display: block; margin-top: 1em; margin-bottom: 0.2em; }}
            .prose p {{ margin-bottom: 0.5em; text-align: justify; }}
        </style>
    </head>
    <body class="bg-gray-100 flex flex-col" x-data="app()">
        <header class="bg-white border-b border-gray-200 h-14 flex items-center justify-between px-6 shadow-sm z-10 shrink-0">
            <div class="flex items-center gap-4">
                <div class="font-bold text-xl text-blue-800 flex items-center gap-2">PubMed DeepReader</div>
                <div class="text-xs text-gray-400 mt-1">更新: {update_time}</div>
            </div>
            <div class="flex items-center gap-2">
                <select x-model="currentFeed" @change="selectFeed()" class="bg-gray-50 border border-gray-300 text-gray-900 text-sm rounded-lg block p-2">
                    <template x-for="feedName in Object.keys(feeds)" :key="feedName">
                        <option :value="feedName" x-text="feedName"></option>
                    </template>
                </select>
            </div>
        </header>
        <div class="flex flex-1 overflow-hidden">
            <aside class="w-1/3 max-w-md bg-white border-r border-gray-200 flex flex-col overflow-y-auto">
                <template x-for="paper in currentPapers" :key="paper.id">
                    <div @click="currentPaper = paper" 
                         :class="currentPaper.id === paper.id ? 'bg-blue-50 border-l-4 border-blue-600' : 'border-l-4 border-transparent hover:bg-gray-50'"
                         class="p-4 border-b border-gray-100 cursor-pointer transition duration-150">
                        <h3 class="text-sm font-bold text-gray-800 line-clamp-2 leading-snug" x-text="paper.title_zh"></h3>
                        <p class="text-xs text-gray-500 mt-1 truncate" x-text="paper.title_en"></p>
                    </div>
                </template>
            </aside>
            <main class="flex-1 bg-gray-50 overflow-y-auto p-6">
                <template x-if="currentPaper">
                    <div class="max-w-5xl mx-auto bg-white rounded-xl shadow-sm p-8 min-h-[90vh]">
                        <div class="border-b border-gray-100 pb-6 mb-6">
                            <h1 class="text-2xl font-bold text-gray-900 mb-2 leading-tight" x-text="currentPaper.title_zh"></h1>
                            <h2 class="text-lg text-gray-500 font-medium mb-4" x-text="currentPaper.title_en"></h2>
                            <div class="flex flex-wrap gap-4 text-xs text-gray-500 bg-gray-50 p-3 rounded-lg">
                                <span class="flex items-center">📅 <span class="ml-1" x-text="currentPaper.date"></span></span>
                                <span class="flex items-center">👥 <span class="ml-1" x-text="currentPaper.authors"></span></span>
                                <a :href="currentPaper.link" target="_blank" class="text-blue-600 hover:underline font-bold ml-auto">🔗 View on PubMed</a>
                            </div>
                        </div>
                        <template x-if="currentPaper.keywords_zh">
                            <div class="mb-6">
                                <span class="text-xs font-bold text-blue-600 uppercase tracking-wide">Keywords</span>
                                <div class="mt-1 text-sm text-gray-700 italic">
                                    <span x-text="currentPaper.keywords_zh"></span>
                                    <span class="text-gray-400 mx-2">/</span>
                                    <span class="text-gray-400" x-text="currentPaper.keywords_en"></span>
                                </div>
                            </div>
                        </template>
                        <div class="grid grid-cols-1 lg:grid-cols-2 gap-8">
                            <div>
                                <h3 class="font-bold text-gray-900 text-lg mb-3 flex items-center"><span class="w-1 h-6 bg-blue-600 mr-2 rounded"></span> 中文摘要</h3>
                                <div class="prose prose-sm prose-blue text-gray-800 leading-relaxed bg-blue-50/50 p-5 rounded-lg border border-blue-100" x-html="marked.parse(currentPaper.abstract_zh)"></div>
                            </div>
                            <div>
                                <h3 class="font-bold text-gray-400 text-lg mb-3 flex items-center"><span class="w-1 h-6 bg-gray-300 mr-2 rounded"></span> Abstract</h3>
                                <div class="prose prose-sm text-gray-600 leading-relaxed whitespace-pre-wrap p-5" x-html="currentPaper.abstract_en.replace(/🟢 /g, '').replace(/(\w+:)/g, '<strong>$1</strong>')"></div>
                            </div>
                        </div>
                    </div>
                </template>
            </main>
        </div>
        <script>
            function app() {{
                return {{ feeds: {json_data}, currentFeed: '', currentPapers: [], currentPaper: null,
                    init() {{ const ks = Object.keys(this.feeds); if(ks.length>0) {{ this.currentFeed=ks[0]; this.selectFeed(); }} }},
                    selectFeed() {{ this.currentPapers = this.feeds[this.currentFeed]; this.currentPaper = this.currentPapers.length>0?this.currentPapers[0]:null; document.querySelector('aside').scrollTop=0; }}
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
