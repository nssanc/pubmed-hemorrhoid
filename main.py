import feedparser
from deep_translator import GoogleTranslator
from Bio import Entrez
import time
from datetime import datetime
import os
import pytz
import json
import re

# ================= 配置区 =================
# 必须设置一个邮箱，这是 PubMed API 的要求（用于追踪滥用）
# 你可以随便填一个，或者填真实的
Entrez.email = "2368112905@qq.com" 

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

def get_pmid_from_link(link):
    """从链接中提取 PMID (例如 https://pubmed.ncbi.nlm.nih.gov/38169999/ -> 38169999)"""
    match = re.search(r'pubmed.ncbi.nlm.nih.gov/(\d+)', link)
    if match:
        return match.group(1)
    return None

def fetch_details_from_api(pmid_list):
    """
    使用 Biopython 调用 PubMed API 批量获取详细摘要结构
    """
    if not pmid_list:
        return {}
    
    print(f"正在调用 API 获取 {len(pmid_list)} 篇文章的详细摘要...")
    results_map = {}
    
    try:
        # efetch 用于获取详细记录
        handle = Entrez.efetch(db="pubmed", id=pmid_list, rettype="xml", retmode="xml")
        records = Entrez.read(handle)
        handle.close()
        
        # PubmedArticle 是一个列表
        articles = records.get('PubmedArticle', [])
        
        for article in articles:
            try:
                medline = article['MedlineCitation']
                pmid = str(medline['PMID'])
                article_data = medline['Article']
                
                # 1. 提取摘要
                abstract_parts = []
                if 'Abstract' in article_data and 'AbstractText' in article_data['Abstract']:
                    # AbstractText 是一个列表，每一项可能包含 Label 属性
                    # 例如: <AbstractText Label="BACKGROUND">...</AbstractText>
                    for item in article_data['Abstract']['AbstractText']:
                        text_content = str(item)
                        # 获取 Label (例如 BACKGROUND, METHODS)
                        label = item.attributes.get('Label', None)
                        
                        if label:
                            abstract_parts.append({"label": label, "text": text_content})
                        else:
                            # 如果没有 Label，就当做普通段落
                            abstract_parts.append({"label": None, "text": text_content})
                
                # 2. 提取关键词
                keywords = []
                if 'KeywordList' in medline and len(medline['KeywordList']) > 0:
                    for kw in medline['KeywordList'][0]:
                        keywords.append(str(kw))

                results_map[pmid] = {
                    "abstract_parts": abstract_parts,
                    "keywords": keywords
                }
                
            except Exception as e:
                print(f"解析 PMID {pmid} 出错: {e}")
                
    except Exception as e:
        print(f"API 请求失败: {e}")
        
    return results_map

def process_and_translate(pmid, api_data, fallback_abstract, translator):
    """
    结合 API 数据进行翻译和组装
    """
    # 标题映射表
    LABEL_MAPPING = {
        "BACKGROUND": "背景", "OBJECTIVE": "目的", "METHODS": "方法",
        "RESULTS": "结果", "CONCLUSION": "结论", "CONCLUSIONS": "结论",
        "DISCUSSION": "讨论", "SIGNIFICANCE": "意义", "INTRODUCTION": "介绍"
    }

    structured_zh = []
    structured_en = []
    
    # 优先使用 API 数据
    if api_data and api_data.get('abstract_parts'):
        parts = api_data['abstract_parts']
        for part in parts:
            label_en = part['label'] # 可能是 None
            text_en = part['text']
            
            # 组装英文
            if label_en:
                structured_en.append(f"**{label_en.title()}:** {text_en}")
            else:
                structured_en.append(text_en)
            
            # 组装并翻译中文
            try:
                trans_text = translator.translate(text_en[:3000])
                if label_en:
                    # 尝试匹配中文标题
                    label_zh = LABEL_MAPPING.get(label_en.upper(), label_en.capitalize())
                    structured_zh.append(f"**{label_zh}：** {trans_text}")
                else:
                    structured_zh.append(trans_text)
                time.sleep(0.2)
            except:
                structured_zh.append(text_en)
                
    else:
        # 如果 API 没数据 (比如文章太老或者 API 失败)，回退到 RSS 的 description
        clean_desc = re.sub(r'<.*?>', '', fallback_abstract).strip()
        structured_en.append(clean_desc)
        try:
            structured_zh.append(translator.translate(clean_desc[:4000]))
        except:
            structured_zh.append("翻译失败")

    # 处理关键词
    kw_en_str = ""
    kw_zh_str = ""
    if api_data and api_data.get('keywords'):
        kws = api_data['keywords']
        kw_en_str = ", ".join(kws)
        try:
            # 批量翻译关键词
            kw_zh_str = translator.translate(kw_en_str[:1000])
        except:
            kw_zh_str = kw_en_str

    return "\n\n".join(structured_zh), "\n\n".join(structured_en), kw_zh_str, kw_en_str


def fetch_and_generate():
    output_dir = "docs"
    if not os.path.exists(output_dir):
        os.makedirs(output_dir)

    RSS_URLS = get_rss_urls()
    if not RSS_URLS:
        print("未找到 feeds.txt")
        return

    translator = GoogleTranslator(source='auto', target='zh-CN')
    all_feeds_data = {}
    
    print(f"准备处理 {len(RSS_URLS)} 个订阅源...")

    for url in RSS_URLS:
        try:
            print(f"正在读取 RSS: {url[:40]}...")
            feed = feedparser.parse(url)
            feed_title = feed.feed.get('title', '未命名').replace("PubMed ", "")
            
            entries_data = []
            pmid_list = []
            temp_entries = []

            # 1. 第一遍循环：收集所有 PMID
            for entry in feed.entries:
                pmid = get_pmid_from_link(entry.link)
                if pmid:
                    pmid_list.append(pmid)
                temp_entries.append({
                    "entry": entry,
                    "pmid": pmid
                })
            
            # 2. 批量从 API 获取详细数据 (这是关键步骤！)
            print(f"--> [{feed_title}] 正在从 PubMed API 下载 {len(pmid_list)} 篇详细结构...")
            api_details = fetch_details_from_api(pmid_list)
            
            # 3. 第二遍循环：结合 API 数据生成内容
            for item in temp_entries:
                entry = item['entry']
                pmid = item['pmid']
                
                # 标题翻译
                try:
                    title_zh = translator.translate(entry.title)
                except:
                    title_zh = entry.title
                
                # 获取该 PMID 对应的 API 数据
                detail = api_details.get(pmid)
                
                # 处理摘要 (API 优先)
                abs_zh, abs_en, kw_zh, kw_en = process_and_translate(
                    pmid, detail, entry.get('description', ''), translator
                )

                entries_data.append({
                    "id": pmid if pmid else entry.link,
                    "title_en": entry.title,
                    "title_zh": title_zh,
                    "authors": entry.get('author', 'No authors'),
                    "abstract_en": abs_en,
                    "abstract_zh": abs_zh,
                    "keywords_zh": kw_zh,
                    "keywords_en": kw_en,
                    "link": entry.link,
                    "date": entry.get('published', '')[:16]
                })
                
            all_feeds_data[feed_title] = entries_data
            
        except Exception as e:
            print(f"处理 {url} 失败: {e}")

    # ================= HTML 生成 (保持之前的样式) =================
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
            .prose strong {{ 
                color: #1e3a8a; font-weight: 800; display: block; 
                margin-top: 1.2em; margin-bottom: 0.4em;
                text-transform: uppercase; font-size: 0.85rem; letter-spacing: 0.05em;
            }}
            .prose p {{ margin-bottom: 0.8em; text-align: justify; line-height: 1.7; }}
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
                        <p>请选择左侧文章开始阅读</p>
                    </div>
                </template>
            </main>
        </div>
        <script>
            function app() {{
                return {{
                    feeds: {json_data}, currentFeed: '', currentPapers: [], currentPaper: null,
                    init() {{ const ks = Object.keys(this.feeds); if(ks.length > 0) {{ this.currentFeed = ks[0]; this.selectFeed(); }} }},
                    selectFeed() {{ this.currentPapers = this.feeds[this.currentFeed]; this.currentPaper = this.currentPapers.length > 0 ? this.currentPapers[0] : null; document.querySelector('aside').scrollTop = 0; }}
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
