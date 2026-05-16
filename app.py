import streamlit as st
import json
import os
import random
import re
import io
import zipfile
import pandas as pd
import altair as alt
import streamlit.components.v1 as components
from openai import OpenAI
import openai  # 显式导入以捕获精准的 API 异常

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"

# ================= 1. 引擎初始化 =================
st.set_page_config(page_title="DBH 上帝大脑 v3.5", layout="wide", initial_sidebar_state="expanded")

# 全局 高奢拟态 UI (彻底修复字体看不清 Bug)
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {background-color: transparent !important;} 
    .block-container {padding-top: 2rem; padding-bottom: 2rem;}
    
    ::-webkit-scrollbar {width: 6px; height: 6px;}
    ::-webkit-scrollbar-track {background: transparent;}
    ::-webkit-scrollbar-thumb {background: rgba(150, 150, 150, 0.3); border-radius: 10px;}
    ::-webkit-scrollbar-thumb:hover {background: rgba(150, 150, 150, 0.6);}
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("""
    <div style='text-align: center; padding: 0px 0 15px 0;'>
        <h1 style='font-size: 26px; font-weight: 800; background: -webkit-linear-gradient(45deg, #4CAF50, #2196F3); -webkit-background-clip: text; -webkit-text-fill-color: transparent; margin: 0;'>DBH. OS</h1>
        <p style='font-size: 11px; color: #888; margin: 0; letter-spacing: 2px;'>GOD'S BRAIN HUB</p>
    </div>
    """, unsafe_allow_html=True)
    
    user_api_key = st.text_input("🔑 DeepSeek API Key", type="password", value="sk-0275d85e2cd348d09b81fb01321b0147")
    if not user_api_key:
        st.warning("👈 请输入 API Key 启动引擎")
        st.stop()
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")

if "theme_choice" not in st.session_state: st.session_state.theme_choice = "🌌 沉浸极光 (灰调)"

if st.session_state.theme_choice == "🌌 沉浸极光 (灰调)":
    st.markdown("""<style>
        .stApp {
            background: linear-gradient(135deg, #1A1D24 0%, #1E2329 40%, #22303C 80%, #2A3C46 100%) !important;
            color: #F8FAFC !important;
        }
        [data-testid="stSidebar"] {
            background-color: #171A21 !important;
            border-right: 1px solid rgba(255, 255, 255, 0.05) !important;
        }
        input[type="text"], textarea, div[data-baseweb="select"] * {
            color: #FFFFFF !important;
            -webkit-text-fill-color: #FFFFFF !important; 
        }
        .stTextInput>div>div>input, .stTextArea>div>textarea, div[data-baseweb="select"]>div {
            background-color: rgba(255, 255, 255, 0.08) !important; 
            border: 1px solid rgba(255, 255, 255, 0.2) !important;
            border-radius: 8px !important;
        }
        div.stButton > button {
            background: rgba(255,255,255,0.05) !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            color: #FFFFFF !important;
            border-radius: 8px !important;
            transition: all 0.3s;
        }
        div.stButton > button:hover {
            background: rgba(255,255,255,0.15) !important;
            border-color: rgba(255, 255, 255, 0.3) !important;
        }
        h1, h2, h3, h4, h5, h6, p, span, label { color: #E2E8F0 !important; }
        .streamlit-expanderHeader { background-color: rgba(255,255,255,0.05) !important; border-radius: 8px !important; }
        div[data-testid="stExpander"] { border: 1px solid rgba(255,255,255,0.08) !important; border-radius: 8px !important; background: rgba(0,0,0,0.15) !important; }
    </style>""", unsafe_allow_html=True)
elif st.session_state.theme_choice == "🌙 极简暗夜":
    st.markdown("""<style>
        .stApp { background-color: #121212 !important; color: #E0E0E0 !important; } 
        input[type="text"], textarea, div[data-baseweb="select"] * { color: #FFFFFF !important; -webkit-text-fill-color: #FFFFFF !important; }
        .stTextInput>div>div>input, .stTextArea>div>textarea { background-color: #2D2D2D !important; border: 1px solid #444 !important; border-radius: 8px !important; } 
        p, h1, h2, h3, h4, h5, h6, span, label { color: #E0E0E0 !important; }
        div.stButton > button { border-radius: 8px !important; background-color: #2D2D2D !important; color: #FFF !important; border: 1px solid #444 !important; }
    </style>""", unsafe_allow_html=True)

# ================= 1.2 /humanizer-zh 核心去AI味提示词定义 =================
HUMANIZER_SYSTEM_PROMPT = """
你是一个顶尖的网文总编辑，内置了精密的 `/humanizer-zh` 人性化改写引擎。
你的核心任务是彻底消除文本中的 AI 写作痕迹，让文字呈现真实人类的鲜活、力量与复杂细节。

【铁律一：严禁使用的 AI 词汇及句式】
1. 绝对不要出现以下词汇：此外、至关重要、深入探讨、强调、持久的、增强、培养、获得、突出、相互作用、复杂性、格局、织锦、证明、充满活力、宝贵的、见证、不仅是……更是……。
2. 消除内容模式：拒绝无病呻吟地强调宏大意义或长远趋势，拒绝宣传和广告式的夸张语言，拒绝空洞的通用积极结论。
3. 消除语言风格：拒绝三段式法则排比、拒绝过度使用粗体和破折号、拒绝使用任何 Emoji 表情。

【铁律二：人性化写作原则】
1. 细节鲜活：用具体的金手指机制、人物动作、情绪反应、具体的数字（如：兜里剩的3块钱）代替抽象概括。
2. 节奏变化：长短句交错，允许市井气、大白话或符合人设的粗粝感，不要像机器一样结构完美。
3. 有观点与反应：文字中要带有个体对事件的即时情绪和主观反应，而不是客观冷漠的报告。
"""

# ================= 1.5 强力数据自愈 =================
def clean_json(text):
    if not text: return "{}"
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^
```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

def normalize_char(data):
    if not isinstance(data, dict):
        data = {"physical":"健康", "magic":"充盈", "status":str(data)[:10], "inventory":[], "tags":[], "appearance":"", "voice":"", "faction":"", "ability":"", "weakness":"", "background":str(data), "motivation":"", "role":"未分类", "stats": {"武力": 50, "智力": 50, "防御": 50, "敏捷": 50, "魅力": 50, "气运": 50}}
    for key in ["tags", "inventory"]:
        val = data.get(key, [])
        if isinstance(val, str): data[key] = [val]
        elif not isinstance(val, list): data[key] = []
    for key in ["physical", "magic", "status", "appearance", "voice", "faction", "ability", "weakness", "background", "motivation", "role"]:
        if key not in data or not isinstance(data[key], str): data[key] = str(data.get(key, ""))
    if not data.get("role"): data["role"] = "未分类"
    if "stats" not in data or not isinstance(data["stats"], dict):
        data["stats"] = {"武力": 50, "智力": 50, "防御": 50, "敏捷": 50, "魅力": 50, "气运": 50}
    return data

def deduplicate_relationships(world_data):
    unique_rels = []
    seen = set()
    for r in world_data.get("_relationships", []):
        if not r.get("source") or not r.get("target"): continue
        pair = tuple(sorted([r["source"], r["target"]]))
        if pair not in seen:
            seen.add(pair)
            unique_rels.append(r)
    world_data["_relationships"] = unique_rels

def create_backup_zip(book_name):
    buf = io.BytesIO()
    files = ["library.json", f"{book_name}_world.json", f"{book_name}_chapters.json", f"{book_name}_timeline.json", f"{book_name}_clues.json", f"{book_name}_materials.json", f"{book_name}_kanban.json", f"{book_name}_global_outline.txt", f"{book_name}_local_outline.txt", f"{book_name}_synopsis.txt"]
    with zipfile.ZipFile(buf, "w") as z:
        for f in files:
            if os.path.exists(f): z.write(f)
    return buf.getvalue()

if not os.path.exists("materials"): os.makedirs("materials")

def handle_api_error(e):
    if isinstance(e, openai.APIStatusError):
        if e.status_code == 402:
            st.error("⚠️ 核心引擎报错：DeepSeek 账户余额不足，请登录开放平台充值后再试。")
        elif e.status_code == 401:
            st.error("⚠️ 核心引擎报错：API Key 无效，请检查左侧边栏配置。")
        else:
            st.error(f"⚠️ 核心引擎请求失败 (状态码 {e.status_code}): {e.message}")
    else:
        st.error(f"⚠️ 发生未知错误: {str(e)}")

# ================= 2. 藏书馆与管理 =================
LIBRARY_FILE = "library.json"
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
def load_text(file):
    return open(file, "r", encoding="utf-8").read() if os.path.exists(file) else ""
def rename_book_files(old_name, new_name):
    suffixes = ["_chapters.json", "_world.json", "_timeline.json", "_clues.json", "_materials.json", "_kanban.json", "_global_outline.txt", "_local_outline.txt", "_synopsis.txt"]
    for suf in suffixes:
        if os.path.exists(old_name + suf): os.rename(old_name + suf, new_name + suf)

if not os.path.exists(LIBRARY_FILE): save_json(LIBRARY_FILE, ["我的第一部小说"])
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

if "active_book" not in st.session_state: st.session_state.active_book = books[0] if books else None
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "multi_drafts" not in st.session_state: st.session_state.multi_drafts = []
if "rebuild_text" not in st.session_state: st.session_state.rebuild_text = ""

# ================= 极简侧边栏重构 =================
with st.sidebar:
    st.markdown("---")
    active_idx = books.index(st.session_state.active_book) if st.session_state.active_book in books else 0
    selected_book = st.selectbox("📚 切换当前作品", books, index=active_idx)
    st.session_state.active_book = selected_book

    with st.expander("➕ 新建与导入书籍"):
        tab_new, tab_import = st.tabs(["新建", "导入"])
        with tab_new:
            new_book = st.text_input("新书名：", key="new_book_input")
            if st.button("✨ 创建", use_container_width=True) and new_book:
                if new_book not in books:
                    books.append(new_book); save_json(LIBRARY_FILE, books); st.session_state.active_book = new_book; st.rerun()
        with tab_import:
            uploaded_file = st.file_uploader("选择 TXT", type=["txt"], label_visibility="collapsed")
            split_method = st.radio("分章策略", ["智能正则", "全文不分章"], horizontal=True)
            if uploaded_file and st.button("🚀 解析入库", type="primary", use_container_width=True):
                with st.spinner("处理中..."):
                    new_name = uploaded_file.name.replace(".txt", "")
                    base_name = new_name; counter = 1
                    while new_name in books:
                        new_name = f"{base_name}_{counter}"; counter += 1
                    content = uploaded_file.read().decode("utf-8", errors="ignore")
                    new_chapters = []
                    if split_method == "智能正则":
                        chunks = re.split(r'\n[ \t]*?(第[零一二三四五六七八九十百千万0-9]+[章节回幕][^\n]*)\n', "\n" + content)
                        if chunks[0].strip(): new_chapters.append({"title": "引子/序言", "content": chunks[0].strip()})
                        for i in range(1, len(chunks), 2): new_chapters.append({"title": chunks[i].strip(), "content": chunks[i+1].strip() if i+1 < len(chunks) else ""})
                    else: new_chapters.append({"title": "全文", "content": content})
                    books.append(new_name); save_json(LIBRARY_FILE, books)
                    save_json(f"{new_name}_chapters.json", new_chapters)
                    save_json(f"{new_name}_world.json", {"_relationships": []})
                    save_json(f"{new_name}_timeline.json", [])
                    save_json(f"{new_name}_clues.json", [])
                    save_json(f"{new_name}_materials.json", [])
                    save_json(f"{new_name}_kanban.json", [{"lane": "第一卷", "events": ["在此添加大纲"]}])
                    open(f"{new_name}_synopsis.txt", "w", encoding="utf-8").write("")
                    st.session_state.active_book = new_name; st.success("导入成功！"); st.rerun()

    st.markdown("---")
    nav_main = st.selectbox("🧭 核心模块", ["✍️ 码字与章节", "🧠 世界与设定", "🛡️ 质检与数据", "✨ 灵感与工坊"])
    
    if nav_main == "✍️ 码字与章节":
        app_mode = st.selectbox("📂 选定功能面板", ["作品概览与简介", "连载写作台", "沉浸阅读与批注", "卡片大纲看板", "目录精修与评估"])
    elif nav_main == "🧠 世界与设定":
        app_mode = st.selectbox("📂 选定功能面板", ["角色图鉴与关系网", "编年史时间轴", "设定提炼引擎"])
    elif nav_main == "🛡️ 质检与数据":
        app_mode = st.selectbox("📂 选定功能面板", ["逻辑体检与防吃书", "数据分析仪表盘"])
    elif nav_main == "✨ 灵感与工坊":
        app_mode = st.selectbox("📂 选定功能面板", ["灵感与素材库", "全自动同人番外"])

# ================= 3. 数据加载 =================
if not st.session_state.active_book: st.stop()
cur_book = st.session_state.active_book

WORLD_FILE = f"{cur_book}_world.json"
CHAPTERS_FILE = f"{cur_book}_chapters.json"
BUFFER_FILE = f"{cur_book}_buffer.txt"
TIMELINE_FILE = f"{cur_book}_timeline.json"
CLUES_FILE = f"{cur_book}_clues.json"
MATERIALS_FILE = f"{cur_book}_materials.json"
KANBAN_FILE = f"{cur_book}_kanban.json"
BOOK_OUTLINE_FILE = f"{cur_book}_global_outline.txt"
CHAPTER_OUTLINE_FILE = f"{cur_book}_local_outline.txt"
SYNOPSIS_FILE = f"{cur_book}_synopsis.txt"

for f in [WORLD_FILE, CHAPTERS_FILE, TIMELINE_FILE, CLUES_FILE, MATERIALS_FILE]:
    if not os.path.exists(f): save_json(f, {} if f == WORLD_FILE else [])
if not os.path.exists(KANBAN_FILE): save_json(KANBAN_FILE, [{"lane": "第一卷", "events": ["主角遭遇危机"]}])
if not os.path.exists(SYNOPSIS_FILE): open(SYNOPSIS_FILE, "w", encoding="utf-8").write("")

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)
with open(TIMELINE_FILE, "r", encoding="utf-8") as f: timeline_data = json.load(f)
with open(CLUES_FILE, "r", encoding="utf-8") as f: clues_data = json.load(f)
with open(MATERIALS_FILE, "r", encoding="utf-8") as f: materials_data = json.load(f)
with open(KANBAN_FILE, "r", encoding="utf-8") as f: kanban_data = json.load(f)
current_synopsis = load_text(SYNOPSIS_FILE)

if "_relationships" not in world_data: world_data["_relationships"] = []
char_keys = [k for k in world_data.keys() if k != "_relationships"]
for k in char_keys: world_data[k] = normalize_char(world_data[k])

deduplicate_relationships(world_data)
save_json(WORLD_FILE, world_data)

if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)
    st.session_state.multi_drafts = []

if st.session_state.rebuild_text:
    with st.spinner("状态同步中..."):
        try:
            p_reb = f"分析文段中出场角色的最新状态。输出纯JSON字典。\n【铁律】：绝对不要脑补！如果文段没提到某人，直接忽略他！\n【库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_text}"
            r_reb = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_reb}], response_format={"type":"json_object"})
            updated = json.loads(clean_json(r_reb.choices[0].message.content))
            for k, v in updated.items():
                if k in world_data: 
                    safe_v = normalize_char(v)
                    world_data[k].update({key: safe_v.get(key) for key in ["physical", "magic", "status"]})
            save_json(WORLD_FILE, world_data); st.session_state.rebuild_text = ""; st.rerun()
        except Exception as e: 
            handle_api_error(e)
            st.session_state.rebuild_text = ""

# ================= 5. 左侧监控与设置归集 =================
with st.sidebar:
    if nav_main in ["✍️ 码字与章节", "🧠 世界与设定"]:
        if char_keys:
            st.markdown("### 📊 实时全息监控")
            char_options = [f"{k} [{world_data[k].get('role', '未分类')}]" for k in char_keys]
            sel_str = st.selectbox(f"目标 (共 {len(char_keys)} 人)", char_options, label_visibility="collapsed")
            selected_char = sel_str.split(" [")[0]
            info = world_data[selected_char]
            
            st.markdown(f"""
            <div style="padding:12px; border-radius:10px; background: rgba(76, 175, 80, 0.05); border: 1px solid rgba(76, 175, 80, 0.2); border-left: 4px solid #4CAF50; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #4CAF50; font-weight: bold; letter-spacing: 1px;">LIFE / 生命</div>
                <div style="font-size: 14px; font-weight: 600; margin-top: 2px;">{info.get('physical', '健康')}</div>
            </div>
            <div style="padding:12px; border-radius:10px; background: rgba(33, 150, 243, 0.05); border: 1px solid rgba(33, 150, 243, 0.2); border-left: 4px solid #2196F3; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #2196F3; font-weight: bold; letter-spacing: 1px;">MANA / 能量</div>
                <div style="font-size: 14px; font-weight: 600; margin-top: 2px;">{info.get('magic', '充盈')}</div>
            </div>
            <div style="padding:12px; border-radius:10px; background: rgba(244, 67, 54, 0.05); border: 1px solid rgba(244, 67, 54, 0.2); border-left: 4px solid #F44336; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #F44336; font-weight: bold; letter-spacing: 1px;">STATUS / 处境</div>
                <div style="font-size: 14px; font-weight: 600; margin-top: 2px;">{info.get('status', '正常')}</div>
            </div>
            """, unsafe_allow_html=True)
            
    st.markdown("---")
    with st.expander("⚙️ 系统与作品配置"):
        st.session_state.theme_choice = st.radio("界面主题", ["🌌 沉浸极光 (灰调)", "🌙 极简暗夜"], horizontal=True, label_visibility="collapsed")
        st.session_state.enable_sound = st.checkbox("🔊 机械键盘打字音效", value=st.session_state.get("enable_sound", False))
        st.selectbox("全书设定风格", ["番茄爽文/快节奏", "起点/宏大叙事", "诡秘悬疑"], key="novel_style")
        st.download_button("📦 备份打包全书 (.zip)", data=create_backup_zip(cur_book), file_name=f"{cur_book}_backup.zip", use_container_width=True)
        if st.button("🧨 销毁此书", type="primary", use_container_width=True):
            if cur_book in books: books.remove(cur_book); save_json(LIBRARY_FILE, books); st.session_state.active_book = books[0] if books else None; st.rerun()

# ================= 6. 右侧：动态路由 =================
st.markdown(f"<h2>《{cur_book}》 <span style='font-size:18px; color:gray;'>/ {app_mode}</span></h2>", unsafe_allow_html=True)
st.markdown("---")

novel_style = st.session_state.get("novel_style", "番茄爽文/快节奏")

# ----------------- 路由: 作品概览与简介 (高度重构去AI味与吻合度) -----------------
if app_mode == "作品概览与简介":
    st.info("💡 管理作品的对外门面：书名重命名与简介包装。")
    c_rn1, c_rn2 = st.columns([3, 1])
    with c_rn1: new_book_name = st.text_input("重命名小说书名：", value=cur_book)
    with c_rn2:
        st.write("")
        if st.button("💾 保存新书名", use_container_width=True):
            if new_book_name != cur_book and new_book_name not in books:
                rename_book_files(cur_book, new_book_name)
                books[books.index(cur_book)] = new_book_name
                save_json(LIBRARY_FILE, books); st.session_state.active_book = new_book_name; st.success("重命名成功！"); st.rerun()

    st.markdown("### 📖 作品简介 (人性化精炼版)")
    c_syn1, c_syn2 = st.columns([3, 1])
    with c_syn1:
        syn_edit = st.text_area("编辑简介内容：", value=current_synopsis, height=220)
        if st.button("💾 保存简介内容", type="primary"):
            open(SYNOPSIS_FILE, "w", encoding="utf-8").write(syn_edit); st.success("简介已保存！"); st.rerun()
    with c_syn2:
        st.markdown("##### 🚀 智能简介抽取")
        syn_style = st.selectbox("核心叙事偏好", ["强冲突爽文", "悬疑勾子流", "硬核设定流"])
        if st.button("提取高吻合度简介", use_container_width=True):
            if not chapters_data:
                st.error("请先在写作台写几章，AI才能抓取真实剧情进行吻合匹配！")
            else:
                with st.spinner("正在解析正文核心逻辑..."):
                    try:
                        # 抽样前几章真实文本
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:3]])[:4000]
                        prompt = f"""
                        提取并生成网文简介。
                        要求：
                        1. 严格基于以下真实前文内容提取核心矛盾、主角金手指和当前生存/升级危机。绝不能凭空脑补前文没有的宏大概念。
                        2. 字数严格限制在 120-180 字之间。不废话。
                        3. 风格偏向：【{syn_style}】。
                        4. 必须通过 `/humanizer-zh` 人性化引擎过滤，严禁出现“此外/至关重要/见证/格局”等空洞词，用长短句交错的接地气人话写。
                        
                        真实前文内容：{sample_txt}
                        """
                        res = client.chat.completions.create(
                            model="deepseek-chat", 
                            messages=[
                                {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        cleaned_syn = res.choices[0].message.content.strip()
                        open(SYNOPSIS_FILE, "w", encoding="utf-8").write(cleaned_syn)
                        st.rerun()
                    except Exception as e:
                        handle_api_error(e)

# ----------------- 路由: 连载工作台 (去AI味重写核心) -----------------
elif app_mode == "连载写作台":
    cg, cl = st.columns(2)
    with cg:
        g_out = st.text_area("全书走向", value=load_text(BOOK_OUTLINE_FILE), height=100)
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out); st.toast("锁定成功")
    with cl:
        l_out = st.text_area("本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out); st.toast("锁定成功")

    buffer_val = st.text_area(f"本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=350)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        with st.expander("🔍 智能雷达引擎 (自动抓多角色)"):
            if st.button("🚀 扫描并录入新角色", use_container_width=True):
                with st.spinner("搜寻中..."):
                    try:
                        prompt = f"提取文段中的【真实新角色】。严禁把'主角'、'系统'当做姓名！忽略已存在的人：{char_keys}。输出纯JSON。\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(clean_json(res.choices[0].message.content))
                        c = 0
                        for k, v in new_chars.items():
                            if k not in world_data and len(k) > 1 and k not in ["主角", "反派", "系统"]:
                                world_data[k] = normalize_char(v); c += 1
                        save_json(WORLD_FILE, world_data); st.success(f"已录入 {c} 名角色！")
                    except Exception as e: 
                        handle_api_error(e)

        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章存目录(提时间轴)", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                try:
                    prompt = f"提炼章节核心时间点和事件。输出纯JSON字典，格式：{{\"time\":\"时间\",\"title\":\"标题\",\"desc\":\"描述\"}}。\n文段：{st.session_state.chapter_buffer[:2000]}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                    ev = json.loads(clean_json(res.choices[0].message.content))
                    if "time" in ev and "title" in ev: timeline_data.append(ev); save_json(TIMELINE_FILE, timeline_data)
                except Exception as e: 
                    handle_api_error(e)
                st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None
                st.success("入库成功！"); st.rerun()

    st.markdown("---")
    cd1, cd2, ci = st.columns([1, 1, 4])
    with cd1:
        if st.button("🎲 突发转折"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于目标【{l_out}】和前文，生成突发事件(20字内)。"}])
                st.session_state.current_prompt = f"【突降】：{res.choices[0].message.content}。往下写。"; st.session_state.current_draft = ""; st.rerun()
            except Exception as e:
                handle_api_error(e)
    with cd2:
        if st.button("🆘 卡文破局"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"卡文。前文摘要：{st.session_state.chapter_buffer[-500:]}。生成5种破局方案。"}])
                st.session_state.current_draft = f"【卡文破局】\n{res.choices[0].message.content}"; st.rerun()
            except Exception as e:
                handle_api_error(e)
    with ci:
        new_in = st.chat_input("下达生成指令（已默认注入人性化引擎）...")
        if new_in: st.session_state.current_prompt = new_in; st.session_state.current_draft = ""; st.session_state.multi_drafts = []; st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft and not st.session_state.multi_drafts:
        c_g1, c_g2 = st.columns(2)
        with c_g1:
            if st.button("🚀 闪电单推"):
                with st.chat_message("assistant"):
                    with st.spinner("构思中..."):
                        try:
                            prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n设定：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n指令：{st.session_state.current_prompt}\n要求：贴合【{novel_style}】，400字。走人性化人话路线，绝不水无意义词汇。"
                            res = client.chat.completions.create(
                                model="deepseek-chat", 
                                messages=[
                                    {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                            st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                        except Exception as e:
                            handle_api_error(e)
        with c_g2:
            if st.button("🔥 多重时间线 (3版本)"):
                with st.chat_message("assistant"):
                    with st.spinner("裂变计算中..."):
                        try:
                            prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n指令：{st.session_state.current_prompt}\n要求：返回JSON字典包含3个不同走向版本。格式：{{\"drafts\": [\"版本1\", \"版本2\", \"版本3\"]}}。每版300字。遵循人性化写作规范。"
                            res = client.chat.completions.create(
                                model="deepseek-chat", 
                                messages=[
                                    {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ],
                                response_format={"type":"json_object"}
                            )
                            st.session_state.multi_drafts = json.loads(clean_json(res.choices[0].message.content)).get("drafts", []); st.rerun()
                        except Exception as e:
                            handle_api_error(e)

    if st.session_state.current_draft:
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("➕ 接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                st.session_state.rebuild_text = draft; st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ /humanizer 强制去AI味精修", type="primary"):
                try:
                    prompt = f"将以下文本进行深度人性化提炼，清除所有机械AI感，补充具体生活细节：\n{draft}"
                    res = client.chat.completions.create(
                        model="deepseek-chat", 
                        messages=[
                            {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                            {"role": "user", "content": prompt}
                        ]
                    )
                    st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                except Exception as e:
                    handle_api_error(e)
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

    if st.session_state.multi_drafts:
        st.info("💡 挑选最满意的一条。")
        tabs = st.tabs(["时间线 A", "时间线 B", "时间线 C"])
        for i, t in enumerate(tabs):
            with t:
                if i < len(st.session_state.multi_drafts):
                    m_draft = st.text_area(f"版本 {i+1} 编辑区", value=st.session_state.multi_drafts[i], height=200, key=f"md_{i}")
                    cs, cd = st.columns([4, 1])
                    with cs:
                        if st.button(f"✨ 采用时间线 {chr(65+i)}", key=f"mb_{i}", type="primary"):
                            st.session_state.chapter_buffer += f"\n\n{m_draft}"
                            open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                            st.session_state.rebuild_text = m_draft; st.session_state.current_prompt = ""; st.session_state.multi_drafts = []; st.rerun()
                    with cd:
                        if st.button("废弃全部", key=f"mdel_{i}"): st.session_state.current_prompt = ""; st.session_state.multi_drafts = []; st.rerun()

# ----------------- 路由: 沉浸阅读与批注 -----------------
elif app_mode == "沉浸阅读与批注":
    st.info("💡 阅读模式：摘录不满意的段落，让 AI 进行专项风格强化与重塑。")
    if not chapters_data: st.warning("书籍尚无章节，请先在工作台创作。")
    else:
        c_read, c_ai = st.columns([3, 2])
        with c_read:
            read_idx = st.selectbox("选择章节", range(len(chapters_data)), format_func=lambda x: chapters_data[x]['title'])
            current_ch = chapters_data[read_idx]
            st.markdown(f"## {current_ch['title']}")
            st.markdown(f"<div style='background-color:rgba(255,255,255,0.02); padding:25px; border-radius:15px; border: 1px solid rgba(255,255,255,0.05); line-height:1.9; font-size:16px; color:#ddd; height:600px; overflow-y:auto;'>{current_ch['content'].replace(chr(10), '<br><br>')}</div>", unsafe_allow_html=True)
            
        with c_ai:
            st.markdown("### ✍️ AI 批注与重铸台")
            target_text = st.text_area("1. 粘贴要重写的原句 (完全匹配原文)", height=150)
            directive = st.text_input("2. 重写指令", placeholder="例如：用大白话改写，去掉AI味")
            
            if st.button("✨ 生成重塑版", type="primary", use_container_width=True):
                if target_text in current_ch['content']:
                    with st.spinner("AI 重铸中..."):
                        try:
                            prompt = f"根据指令重写片段。紧扣指令，彻底去除AI味。\n【原句】：{target_text}\n【指令】：{directive}"
                            res = client.chat.completions.create(
                                model="deepseek-chat", 
                                messages=[
                                    {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                                    {"role": "user", "content": prompt}
                                ]
                            )
                            st.session_state[f"rewrite_{read_idx}"] = res.choices[0].message.content
                        except Exception as e:
                            handle_api_error(e)
                else: st.error("⚠️ 未找到原文段落。")
                    
            new_text = st.session_state.get(f"rewrite_{read_idx}", "")
            if new_text:
                final_text = st.text_area("重塑结果 (可再修改)：", value=new_text, height=150)
                if st.button("🔄 一键替换回原文"):
                    chapters_data[read_idx]['content'] = current_ch['content'].replace(target_text, final_text)
                    save_json(CHAPTERS_FILE, chapters_data); st.session_state[f"rewrite_{read_idx}"] = ""; st.success("已替换！"); st.rerun()

# ----------------- 路由: 卡片大纲看板 -----------------
elif app_mode == "卡片大纲看板":
    st.info("瀑布流大纲看板。可分卷列出剧情节点。")
    c_add_lane, _ = st.columns([1, 4])
    with c_add_lane:
        new_lane = st.text_input("新增卷名", placeholder="如：第二卷 锋芒初露")
        if st.button("添加卷轴") and new_lane:
            kanban_data.append({"lane": new_lane, "events": []})
            save_json(KANBAN_FILE, kanban_data); st.rerun()
            
    st.markdown("---")
    if kanban_data:
        cols = st.columns(len(kanban_data))
        for i, lane in enumerate(kanban_data):
            with cols[i]:
                c_title, c_del_lane = st.columns([4, 1])
                with c_title:
                    new_lane_name = st.text_input(f"卷名_{i}", value=lane['lane'], key=f"kb_lane_{i}", label_visibility="collapsed")
                    if new_lane_name != lane['lane']:
                        kanban_data[i]['lane'] = new_lane_name; save_json(KANBAN_FILE, kanban_data)
                with c_del_lane:
                    if st.button("🗑️", key=f"kb_del_lane_{i}"):
                        kanban_data.pop(i); save_json(KANBAN_FILE, kanban_data); st.rerun()

                for j, ev in enumerate(lane['events']):
                    with st.container():
                        st.info(ev)
                        if st.button("移除", key=f"kb_del_{i}_{j}"):
                            lane['events'].pop(j); save_json(KANBAN_FILE, kanban_data); st.rerun()
                
                new_ev = st.text_input("新增卡片", key=f"kb_add_{i}", placeholder="简述剧情...")
                if st.button("添加", key=f"kb_btn_{i}", use_container_width=True) and new_ev:
                    lane['events'].append(new_ev); save_json(KANBAN_FILE, kanban_data); st.rerun()
    else: st.warning("大纲看板为空。")

# ----------------- 路由: 目录精修与评估 (黄金三章重构智能修改) -----------------
elif app_mode == "目录精修与评估":
    t_edit, t_clue, t_replace, t_golden = st.tabs(["📖 章节精修与伏笔标记", "📌 伏笔追踪局", "🔄 全局一键替换", "🏆 黄金三章智改与预警"])
    
    with t_edit:
        if chapters_data:
            export_text = f"《{cur_book}》\n\n"
            for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
            st.download_button("📥 导出全本小说 TXT", data=export_text, file_name=f"{cur_book}.txt", use_container_width=True)
            st.markdown("---")
            
            for idx, ch in enumerate(chapters_data):
                with st.expander(f"第 {idx+1} 章：{ch['title']} (字数: {len(ch['content'])})"):
                    new_title = st.text_input("修改标题", value=ch['title'], key=f"edit_t_{idx}")
                    new_content = st.text_area("编辑内容", value=ch['content'], height=250, key=f"edit_c_{idx}")
                    if new_title != ch['title'] or new_content != ch['content']:
                        chapters_data[idx] = {"title": new_title, "content": new_content}
                        save_json(CHAPTERS_FILE, chapters_data)
        else:
            st.warning("暂无章节数据。")

    with t_clue:
        st.info("管理全书埋下的伏笔。")
        c_clue_in = st.chat_input("记录新伏笔...")
        if c_clue_in:
            clues_data.append({"text": c_clue_in, "status": "未回收"})
            save_json(CLUES_FILE, clues_data); st.rerun()
        for idx, clue in enumerate(clues_data):
            c_c1, c_c2 = st.columns([4, 1])
            with c_c1: st.write(f"📌 {clue['text']} ({clue['status']})")
            with c_c2:
                if clue['status'] == "未回收" and st.button("收回", key=f"clue_b_{idx}"):
                    clues_data[idx]['status'] = "已回收"; save_json(CLUES_FILE, clues_data); st.rerun()

    with t_replace:
        st.info("全局人名/地名一键替换")
        r_old = st.text_input("原词")
        r_new = st.text_input("新词")
        if st.button("执行全局替换") and r_old and r_new:
            count = 0
            for idx, ch in enumerate(chapters_data):
                if r_old in ch['content']:
                    chapters_data[idx]['content'] = ch['content'].replace(r_old, r_new)
                    count += 1
            if count > 0:
                save_json(CHAPTERS_FILE, chapters_data); st.success(f"已在 {count} 个章节中完成替换！")
            else: st.warning("未找到匹配项。")

    # 【深度修复重构】：黄金三章落地页，支持智能一键重写与应用修改
    with t_golden:
        st.markdown("### 🏆 黄金三章智能修剪与落地重塑")
        if len(chapters_data) < 3:
            st.warning(f"目前只有 {len(chapters_data)} 章，黄金三章评估至少需要前 3 章内容。快去写作连载吧！")
        else:
            st.info("💡 系统将诊断前三章的钩子、节奏、人设，不仅给出建议，还将直接生成修改后的正文对比供你一键替换。")
            
            target_ch_idx = st.selectbox("选择想要AI直接帮你重改的章节", [0, 1, 2], format_func=lambda x: f"第 {x+1} 章：{chapters_data[x]['title']}")
            
            if st.button("🚀 开启黄金三章多维诊断与一键智能重写", type="primary", use_container_width=True):
                with st.spinner("正在进行多维度诊断并重写正文..."):
                    try:
                        g3_content = f"""
                        [第一章] {chapters_data[0]['title']}\n{chapters_data[0]['content'][:2000]}\n
                        [第二章] {chapters_data[1]['title']}\n{chapters_data[1]['content'][:2000]}\n
                        [第三章] {chapters_data[2]['title']}\n{chapters_data[2]['content'][:2000]}
                        """
                        
                        prompt = f"""
                        你现在是顶级网文白金总编。请对以下前三章内容进行黄金三章精修，并直接帮作者重写指定章节。
                        
                        【指定重写目标】：你要帮作者重写第 {target_ch_idx + 1} 章。
                        
                        【诊断要求】：
                        1. 钩子是否前置？前300字是否有核心悬念或金手指出现？
                        2. 节奏是否拖沓？有没有大段无意义的AI风背景介绍（世界观织锦式描写）？如果有，立刻砍掉。
                        
                        【输出格式】：
                        请严格分为两个部分输出：
                        ### 1. 核心精修诊断建议
                        （用最辛辣、最直接的行业话语指出前三章最大的问题，不要说套话）
                        
                        ### 2. 第 {target_ch_idx + 1} 章人性化重塑后正文
                        （这里直接输出重写后的整章正文。必须走 `/humanizer-zh` 人性化引擎：长短句交错、细节拉满、保留核心剧情但是把AI味、多余的解释性长句全部洗掉，变成让人一口气读完的爽快正文）
                        """
                        
                        res = client.chat.completions.create(
                            model="deepseek-chat",
                            messages=[
                                {"role": "system", "content": HUMANIZER_SYSTEM_PROMPT},
                                {"role": "user", "content": prompt}
                            ]
                        )
                        
                        raw_result = res.choices[0].message.content
                        st.session_state["golden_analysis"] = raw_result
                        
                        # 尝试利用正则切分出重塑后的正文
                        if "### 2." in raw_result:
                            rewritten_part = raw_result.split("### 2.")[1].replace(f"第 {target_ch_idx + 1} 章人性化重塑后正文", "").strip()
                            st.session_state["golden_rewritten_txt"] = rewritten_part
                            st.session_state["golden_target_idx"] = target_ch_idx
                        
                    except Exception as e:
                        handle_api_error(e)
            
            # 显示诊断与智改结果
            if "golden_analysis" in st.session_state:
                st.markdown("---")
                st.markdown(st.session_state["golden_analysis"])
                
                if "golden_rewritten_txt" in st.session_state:
                    st.markdown("---")
                    st.markdown(f"#### 🛠️ AI 智能修改预览区 (针对第 {st.session_state['golden_target_idx']+1} 章)")
                    
                    final_approved_text = st.text_area(
                        "你可以微调重写后的内容，确认无误后点击下方按钮覆盖源码：", 
                        value=st.session_state["golden_rewritten_txt"], 
                        height=350
                    )
                    
                    if st.button("🔥 智能合入：用重写后的文本覆盖原章节", type="primary", use_container_width=True):
                        t_idx = st.session_state["golden_target_idx"]
                        chapters_data[t_idx]["content"] = final_approved_text
                        save_json(CHAPTERS_FILE, chapters_data)
                        st.success(f"🎉 成功！第 {t_idx+1} 章已被AI精修版完美覆盖！")
                        # 清理缓存状态
                        del st.session_state["golden_analysis"]
                        del st.session_state["golden_rewritten_txt"]
                        st.rerun()

# ----------------- 路由: 其他安全占位 -----------------
else:
    st.write("功能模块搭建中...")
