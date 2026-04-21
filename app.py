import streamlit as st
import json
import os
import random
import re
import pandas as pd
import altair as alt
import streamlit.components.v1 as components
from openai import OpenAI

ECHARTS_CDN = "https://cdn.jsdelivr.net/npm/echarts@5.5.0/dist/echarts.min.js"

# ================= 1. 引擎初始化 =================
with st.sidebar:
    st.header("🔑 引擎激活")
    user_api_key = st.text_input("请输入 DeepSeek API Key", type="password", value="sk-0275d85e2cd348d09b81fb01321b0147")
    if not user_api_key:
        st.warning("👈 请输入 API Key 启动引擎")
        st.stop()
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")

st.set_page_config(page_title="DBH-上帝大脑 v2.6", layout="wide")

# ================= 1.2 全局 UI 艺术化渲染 =================
st.markdown("""
<style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    div.stButton > button { border-radius: 8px; font-weight: 600; transition: all 0.3s ease; }
    div.stButton > button:hover { transform: translateY(-2px); box-shadow: 0 4px 10px rgba(0,0,0,0.1); }
    .stTextInput>div>div>input, .stTextArea>div>textarea { border-radius: 8px !important; }
</style>
""", unsafe_allow_html=True)

with st.sidebar:
    st.markdown("---")
    theme_choice = st.radio("🎨 界面主题", ["系统默认", "🌙 极夜暗黑", "🌿 抹茶护眼"], horizontal=True)
    if theme_choice == "🌙 极夜暗黑":
        st.markdown("""<style>.stApp { background-color: #121212 !important; color: #E0E0E0 !important; } .stTextInput>div>div>input, .stTextArea>div>textarea { background-color: #2D2D2D !important; color: #FFF !important; } p, h1, h2, h3, h4, h5, h6, span, label { color: #E0E0E0 !important; }</style>""", unsafe_allow_html=True)
    elif theme_choice == "🌿 抹茶护眼":
        st.markdown("""<style>.stApp { background-color: #EBF3E6 !important; color: #2D372B !important; } .stTextInput>div>div>input, .stTextArea>div>textarea { background-color: #F8FBF5 !important; color: #2D372B !important; border: 1px solid #C7EDCC !important;} p, h1, h2, h3, h4, h5, h6, span, label { color: #2D372B !important; }</style>""", unsafe_allow_html=True)

# ================= 1.5 强力数据自愈 =================
def clean_json(text):
    if not text: return "{}"
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
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

if not os.path.exists("materials"): os.makedirs("materials")

# ================= 2. 藏书馆 =================
LIBRARY_FILE = "library.json"
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
def load_text(file):
    return open(file, "r", encoding="utf-8").read() if os.path.exists(file) else ""

if not os.path.exists(LIBRARY_FILE): save_json(LIBRARY_FILE, ["我的第一部小说"])
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

if "active_book" not in st.session_state: st.session_state.active_book = books[0] if books else None
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "multi_drafts" not in st.session_state: st.session_state.multi_drafts = []
if "ai_reply" not in st.session_state: st.session_state.ai_reply = ""
if "rebuild_text" not in st.session_state: st.session_state.rebuild_text = ""

with st.sidebar:
    st.markdown("### 📚 藏书阁")
    active_idx = books.index(st.session_state.active_book) if st.session_state.active_book in books else 0
    selected_book = st.selectbox("当前操作作品", books, index=active_idx, label_visibility="collapsed")
    st.session_state.active_book = selected_book

    with st.expander("➕ 新建与导入"):
        tab_new, tab_import = st.tabs(["新建小说", "导入老书"])
        with tab_new:
            new_book = st.text_input("新书名：", key="new_book_input")
            if st.button("创建新书", use_container_width=True) and new_book:
                if new_book not in books:
                    books.append(new_book)
                    save_json(LIBRARY_FILE, books); st.session_state.active_book = new_book; st.rerun()
        with tab_import:
            uploaded_file = st.file_uploader("选择 TXT", type=["txt"], label_visibility="collapsed")
            split_method = st.radio("分章策略", ["智能正则(默认)", "自定义标志词", "不分章"])
            custom_kw = st.text_input("输入前缀 (如 '第')") if split_method == "自定义标志词" else ""

            if uploaded_file and st.button("🚀 解析并建书", type="primary", use_container_width=True):
                with st.spinner("处理中..."):
                    new_name = uploaded_file.name.replace(".txt", "")
                    base_name = new_name; counter = 1
                    while new_name in books:
                        new_name = f"{base_name}_导入版{counter}"; counter += 1
                    
                    content = uploaded_file.read().decode("utf-8", errors="ignore")
                    new_chapters = []
                    
                    if split_method == "智能正则(默认)":
                        chunks = re.split(r'\n[ \t]*?(第[零一二三四五六七八九十百千万0-9]+[章节回幕][^\n]*)\n', "\n" + content)
                        if chunks[0].strip(): new_chapters.append({"title": "引子/序言", "content": chunks[0].strip()})
                        for i in range(1, len(chunks), 2):
                            new_chapters.append({"title": chunks[i].strip(), "content": chunks[i+1].strip() if i+1 < len(chunks) else ""})
                    elif split_method == "自定义标志词" and custom_kw:
                        chunks = re.split(rf'\n[ \t]*?({custom_kw}[^\n]*)\n', "\n" + content)
                        if chunks[0].strip(): new_chapters.append({"title": "引子/序言", "content": chunks[0].strip()})
                        for i in range(1, len(chunks), 2):
                            new_chapters.append({"title": chunks[i].strip(), "content": chunks[i+1].strip() if i+1 < len(chunks) else ""})
                    else:
                        new_chapters.append({"title": "全文", "content": content})
                    
                    books.append(new_name); save_json(LIBRARY_FILE, books)
                    save_json(f"{new_name}_chapters.json", new_chapters)
                    save_json(f"{new_name}_world.json", {"_relationships": []})
                    save_json(f"{new_name}_timeline.json", [])
                    save_json(f"{new_name}_clues.json", [])
                    save_json(f"{new_name}_materials.json", [])
                    save_json(f"{new_name}_kanban.json", [{"lane": "第一卷 (初期)", "events": ["在此添加大纲节点"]}])
                    
                    st.session_state.active_book = new_name
                    st.success("导入成功！"); st.rerun()

    with st.expander("⚙️ 作品设置"):
        novel_style = st.selectbox("风格锚点", ["番茄爽文/快节奏", "起点/宏大叙事", "晋江/情感共鸣", "诡秘悬疑", "二次元吐槽"])
        if st.button("🧨 销毁当前作品", type="primary", use_container_width=True):
            if selected_book in books:
                books.remove(selected_book); save_json(LIBRARY_FILE, books)
                st.session_state.active_book = books[0] if len(books) > 0 else None
                st.rerun()

    st.markdown("---")
    
    # ================= 痛点修复：四大维度嵌套导航 =================
    st.markdown("### 🧭 上帝中枢")
    nav_main = st.selectbox("核心模块", ["✍️ 码字与章节", "🧠 世界与设定", "🛡️ 质检与数据", "✨ 灵感与工坊"])
    
    if nav_main == "✍️ 码字与章节":
        app_mode = st.radio("功能面板", ["连载写作台", "目录精修与评估", "卡片大纲看板"], label_visibility="collapsed")
    elif nav_main == "🧠 世界与设定":
        app_mode = st.radio("功能面板", ["角色图鉴与关系网", "编年史时间轴", "设定提炼引擎"], label_visibility="collapsed")
    elif nav_main == "🛡️ 质检与数据":
        app_mode = st.radio("功能面板", ["逻辑体检与防吃书", "数据分析仪表盘"], label_visibility="collapsed")
    elif nav_main == "✨ 灵感与工坊":
        app_mode = st.radio("功能面板", ["沉浸阅读与批注", "灵感与素材库", "全自动同人番外"], label_visibility="collapsed")

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

for f in [WORLD_FILE, CHAPTERS_FILE, TIMELINE_FILE, CLUES_FILE, MATERIALS_FILE]:
    if not os.path.exists(f): save_json(f, {} if f == WORLD_FILE else [])
if not os.path.exists(KANBAN_FILE): save_json(KANBAN_FILE, [{"lane": "第一卷", "events": ["主角遭遇危机"]}])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)
with open(TIMELINE_FILE, "r", encoding="utf-8") as f: timeline_data = json.load(f)
with open(CLUES_FILE, "r", encoding="utf-8") as f: clues_data = json.load(f)
with open(MATERIALS_FILE, "r", encoding="utf-8") as f: materials_data = json.load(f)
with open(KANBAN_FILE, "r", encoding="utf-8") as f: kanban_data = json.load(f)

if "_relationships" not in world_data: world_data["_relationships"] = []
char_keys = []
for k in list(world_data.keys()):
    if k != "_relationships":
        world_data[k] = normalize_char(world_data[k])
        char_keys.append(k)

deduplicate_relationships(world_data)
save_json(WORLD_FILE, world_data)

# ================= 4. 数据同步 =================
if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)
    st.session_state.ai_reply = ""
    st.session_state.multi_drafts = []

if st.session_state.rebuild_text:
    with st.spinner("状态同步中..."):
        try:
            p_reb = f"分析文段中出场角色的最新状态。输出纯JSON字典。\n【铁律】：绝对不要脑补！如果文段没提到某人，直接忽略他！physical, magic, status 的值必须是极简词语（2到8个字）。\n【库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_text}"
            r_reb = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_reb}], response_format={"type":"json_object"})
            updated = json.loads(clean_json(r_reb.choices[0].message.content))
            for k, v in updated.items():
                if k in world_data: 
                    safe_v = normalize_char(v)
                    world_data[k].update({key: safe_v.get(key) for key in ["physical", "magic", "status"]})
            save_json(WORLD_FILE, world_data); st.session_state.rebuild_text = ""; st.rerun()
        except Exception: st.session_state.rebuild_text = ""

# ================= 5. 左侧监控 =================
with st.sidebar:
    if nav_main in ["✍️ 码字与章节", "🧠 世界与设定"]:
        st.markdown("---")
        st.markdown("### 📊 实时精准监控")
        if char_keys:
            char_options = [f"{k} [{world_data[k].get('role', '未分类')}]" for k in char_keys]
            sel_str = st.selectbox(f"目标 (共 {len(char_keys)} 人)", char_options, label_visibility="collapsed")
            selected_char = sel_str.split(" [")[0]
            info = world_data[selected_char]
            
            st.markdown(f"""
            <div style="padding:10px; border-radius:8px; background: rgba(76, 175, 80, 0.1); border-left: 4px solid #4CAF50; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #4CAF50; font-weight: bold;">生命体征</div>
                <div style="font-size: 14px; font-weight: 600;">{info.get('physical', '健康')}</div>
            </div>
            <div style="padding:10px; border-radius:8px; background: rgba(33, 150, 243, 0.1); border-left: 4px solid #2196F3; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #2196F3; font-weight: bold;">能量状态</div>
                <div style="font-size: 14px; font-weight: 600;">{info.get('magic', '充盈')}</div>
            </div>
            <div style="padding:10px; border-radius:8px; background: rgba(244, 67, 54, 0.1); border-left: 4px solid #F44336; margin-bottom: 8px;">
                <div style="font-size: 11px; color: #F44336; font-weight: bold;">当前处境</div>
                <div style="font-size: 14px; font-weight: 600;">{info.get('status', '正常')}</div>
            </div>
            """, unsafe_allow_html=True)

# ================= 6. 右侧：动态路由 =================
st.title(f"《{cur_book}》- {app_mode}")
st.markdown("---")

# ----------------- 路由: 连载工作台 -----------------
if app_mode == "连载写作台":
    cg, cl = st.columns(2)
    with cg:
        g_out = st.text_area("全书走向", value=load_text(BOOK_OUTLINE_FILE), height=100)
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out); st.toast("锁定成功")
    with cl:
        l_out = st.text_area("本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out); st.toast("锁定成功")

    buffer_val = st.text_area(f"本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        with st.expander("🔍 智能雷达引擎 (自动抓多角色)"):
            if st.button("🚀 扫描并录入新角色", use_container_width=True):
                with st.spinner("搜寻全员中..."):
                    try:
                        prompt = f"提取文段中的【所有真实的新角色】。绝对禁止把'主角'、'系统'当做姓名！\n忽略已存在的人：{char_keys}。输出纯JSON。\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(clean_json(res.choices[0].message.content))
                        added_count = 0
                        for k, v in new_chars.items():
                            if k not in world_data and len(k) > 1 and k not in ["主角", "配角", "反派", "系统"]:
                                world_data[k] = normalize_char(v)
                                added_count += 1
                        save_json(WORLD_FILE, world_data); st.success(f"已录入 {added_count} 名真实角色！")
                    except Exception as e: st.error(f"提取失败: {e}")

        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章存入目录 (记录时间轴)", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                
                with st.spinner("后台提炼时间轴..."):
                    try:
                        prompt = f"提炼以下章节的核心时间点和事件名。必须只输出纯JSON字典，格式：{{\"time\":\"时间\",\"title\":\"标题\",\"desc\":\"描述\"}}。\n文段：{st.session_state.chapter_buffer[:2000]}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        ev = json.loads(clean_json(res.choices[0].message.content))
                        if "time" in ev and "title" in ev:
                            timeline_data.append(ev)
                            save_json(TIMELINE_FILE, timeline_data)
                    except Exception: pass
                
                st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None
                st.success("结章入库成功！"); st.rerun()

    st.markdown("---")
    cd1, cd2, ci = st.columns([1, 1, 4])
    with cd1:
        if st.button("🎲 突发转折"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于目标【{l_out}】和前文，生成突发事件(20字内)。"}])
                st.session_state.current_prompt = f"【突降】：{res.choices[0].message.content}。往下写。"; st.session_state.current_draft = ""; st.rerun()
            except Exception as e: st.error(f"网络异常: {e}")
    with cd2:
        if st.button("🆘 卡文破局"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"卡文。前文摘要：{st.session_state.chapter_buffer[-500:]}。生成5种破局方案。"}])
                st.session_state.current_draft = f"【卡文破局】\n{res.choices[0].message.content}"; st.rerun()
            except Exception as e: st.error(f"网络异常: {e}")
    with ci:
        new_in = st.chat_input("下达指令 (回车生成，或下方多分支)...")
        if new_in: st.session_state.current_prompt = new_in; st.session_state.current_draft = ""; st.session_state.multi_drafts = []; st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft and not st.session_state.multi_drafts:
        c_gen1, c_gen2 = st.columns(2)
        with c_gen1:
            if st.button("🚀 闪电单推 (生成1个版本)"):
                with st.chat_message("assistant"):
                    with st.spinner("构思中..."):
                        try:
                            prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n设定：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n指令：{st.session_state.current_prompt}\n要求：贴合【{novel_style}】，400字。"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                        except Exception as e: st.error(f"异常: {e}")
        with c_gen2:
            if st.button("🔥 多重时间线 (生成3个不同版本)"):
                with st.chat_message("assistant"):
                    with st.spinner("量子大脑分裂3条时间线..."):
                        try:
                            prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n指令：{st.session_state.current_prompt}\n要求：返回纯JSON字典，包含3个走向的版本。格式：{{\"drafts\": [\"版本1文本\", \"版本2文本\", \"版本3文本\"]}}。每版300字，贴合【{novel_style}】。"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                            drafts_dict = json.loads(clean_json(res.choices[0].message.content))
                            st.session_state.multi_drafts = drafts_dict.get("drafts", [])
                            st.rerun()
                        except Exception as e: st.error(f"异常: {e}")

    if st.session_state.current_draft:
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("➕ 接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                st.session_state.rebuild_text = draft 
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ 去 AI 味精修", type="primary"):
                try:
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色片段，去AI味：{draft}"}])
                    st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                except Exception as e: st.error(f"异常: {e}")
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

    if st.session_state.multi_drafts:
        st.info("💡 挑选最满意的一条。")
        tabs = st.tabs(["时间线 A", "时间线 B", "时间线 C"])
        for i, t in enumerate(tabs):
            with t:
                if i < len(st.session_state.multi_drafts):
                    m_draft = st.text_area(f"版本 {i+1} 编辑区", value=st.session_state.multi_drafts[i], height=200, key=f"md_{i}")
                    c_sel, c_del = st.columns([4, 1])
                    with c_sel:
                        if st.button(f"✨ 确认采用【时间线 {chr(65+i)}】", key=f"mb_{i}", type="primary"):
                            st.session_state.chapter_buffer += f"\n\n{m_draft}"
                            open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                            st.session_state.rebuild_text = m_draft
                            st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.session_state.multi_drafts = []; st.rerun()
                    with c_del:
                        if st.button("全部废弃", key=f"mdel_{i}"):
                            st.session_state.current_prompt = ""; st.session_state.multi_drafts = []; st.rerun()

# ----------------- 路由: 卡片大纲看板 -----------------
elif app_mode == "卡片大纲与看板":
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

                st.markdown("")
                for j, ev in enumerate(lane['events']):
                    with st.container():
                        st.info(ev)
                        if st.button("移除", key=f"kb_del_{i}_{j}"):
                            lane['events'].pop(j); save_json(KANBAN_FILE, kanban_data); st.rerun()
                
                new_ev = st.text_input("新增卡片", key=f"kb_add_{i}", placeholder="简述剧情...")
                if st.button("添加", key=f"kb_btn_{i}", use_container_width=True) and new_ev:
                    lane['events'].append(new_ev); save_json(KANBAN_FILE, kanban_data); st.rerun()
    else: st.warning("大纲看板为空，请先添加一个卷轴。")

# ----------------- 路由: 目录精修与评估 (聚合) -----------------
elif app_mode == "目录精修与评估":
    st.info("直接修改章节、向下拆分，或进行全局替换与黄金三章评估。")
    
    t_edit, t_replace, t_golden = st.tabs(["📖 章节精修与拆分", "🔄 全局一键替换", "🏆 黄金三章预警"])
    
    with t_edit:
        if chapters_data:
            export_text = f"《{cur_book}》\n\n"
            for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
            st.download_button("📥 导出全本小说 TXT", data=export_text, file_name=f"{cur_book}.txt", use_container_width=True)
            st.markdown("---")
            
            for idx, ch in enumerate(chapters_data):
                with st.expander(f"第 {idx+1} 章：{ch['title']}"):
                    new_title = st.text_input("章节名称", value=ch['title'], key=f"et_{idx}")
                    new_content = st.text_area("章节正文", value=ch['content'], height=300, key=f"ec_{idx}")
                    c_s, c_split, c_del = st.columns([1, 2, 1])
                    with c_s:
                        if st.button("保存修改", key=f"save_{idx}", type="primary"):
                            chapters_data[idx]['title'] = new_title
                            chapters_data[idx]['content'] = new_content
                            save_json(CHAPTERS_FILE, chapters_data); st.toast("保存成功"); st.rerun()
                    with c_split:
                        split_str = st.text_input("从此句向下拆分为新章", placeholder="复制正文句子", key=f"sp_{idx}")
                        if st.button("以此切割", key=f"sbtn_{idx}") and split_str:
                            if split_str in new_content:
                                parts = new_content.split(split_str, 1)
                                chapters_data[idx]['content'] = parts[0].strip()
                                chapters_data.insert(idx+1, {"title": "新拆分章节", "content": (split_str + parts[1]).strip()})
                                save_json(CHAPTERS_FILE, chapters_data); st.success("拆分成功！"); st.rerun()
                            else: st.error("未找到句子")
                    with c_del:
                        if st.button("删除本章", key=f"del_{idx}"):
                            chapters_data.pop(idx); save_json(CHAPTERS_FILE, chapters_data); st.rerun()
        else: st.warning("暂无章节。")

    with t_replace:
        st.markdown("### 全局角色/名词替换引擎")
        st.caption("将全书几十万字内的特定词语（如旧主角名）一键全部替换。")
        c_old, c_new, c_btn = st.columns([2, 2, 1])
        with c_old: old_word = st.text_input("要替换的旧词 (如: 林北)")
        with c_new: new_word = st.text_input("替换为新词 (如: 叶凡)")
        with c_btn:
            st.write("")
            if st.button("🚀 批量替换", type="primary", use_container_width=True) and old_word and new_word:
                with st.spinner("检索修改中..."):
                    count = 0
                    for ch in chapters_data:
                        count += ch['content'].count(old_word)
                        count += ch['title'].count(old_word)
                        ch['content'] = ch['content'].replace(old_word, new_word)
                        ch['title'] = ch['title'].replace(old_word, new_word)
                    save_json(CHAPTERS_FILE, chapters_data)
                    st.success(f"✅ 替换成功！全书共修改 {count} 处。"); st.rerun()

    with t_golden:
        st.markdown("### 🏆 网文主编级·黄金三章退稿预警器")
        st.info("💡 扫描前三章的节奏、毒点和金手指爽度，预估签约成功率。")
        if st.button("🚀 开始扫描前三章", type="primary", use_container_width=True):
            if len(chapters_data) < 3: st.warning("章节不足 3 章，请先多写一点！")
            else:
                with st.spinner("资深编辑正在审稿中..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:3]])[:8000]
                        prompt = f"你是一个极其严厉的网文网站主编。审视小说前三章。分别从【主角记忆点】、【金手指爽度】、【反派压迫感】、【节奏拖沓度】四个维度打分。给出百分制【签约成功率预估】，及致命的【退稿/毒点警告】。\n【前三章】：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.write(res.choices[0].message.content)
                    except Exception as e: st.error(f"审稿繁忙: {e}")

# ----------------- 路由: 角色图鉴与关系网 -----------------
elif app_mode == "角色图鉴与关系网":
    tab_wiki, tab_graph = st.tabs(["📚 图鉴档案大厅", "🕸️ 可视化关系网"])
    
    with tab_wiki:
        with st.expander("⚙️ 角色图鉴注入引擎 (创建/扫描)"):
            c_mw, c_aw = st.columns(2)
            with c_mw:
                new_char_name = st.text_input("手动新增：姓名")
                if st.button("手动创建角色", use_container_width=True) and new_char_name and new_char_name not in world_data:
                    world_data[new_char_name] = normalize_char({})
                    save_json(WORLD_FILE, world_data); st.rerun()
            with c_aw:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🤖 AI 扫描全书提取角色", type="primary", use_container_width=True):
                    with st.spinner("拉网排查中..."):
                        try:
                            sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                            prompt = f"提取所有真实出场人物。严禁提取'主角/配角/反派'等标签！输出纯JSON字典。\n文本：{sample_txt}"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                            new_c = json.loads(clean_json(res.choices[0].message.content))
                            for k, v in new_c.items():
                                if k not in world_data and k not in ["主角", "配角", "反派"]: 
                                    world_data[k] = normalize_char(v)
                            save_json(WORLD_FILE, world_data); st.success(f"提取成功，新增 {len(new_c)} 人！"); st.rerun()
                        except Exception as e: st.error(f"提取失败: {e}")

        col_list, col_edit = st.columns([1, 3])
        with col_list:
            st.subheader("角色花名册")
            char_options = [f"{k} [{world_data[k].get('role', '未分类')}]" for k in char_keys]
            sel_str = st.selectbox("选择档案", char_options, label_visibility="collapsed") if char_keys else None
            if sel_str:
                sel_wiki_char = sel_str.split(" [")[0]
                st.markdown("---")
                if st.button("🗑️ 彻底删除此角色", type="secondary"):
                    world_data.pop(sel_wiki_char); save_json(WORLD_FILE, world_data); st.rerun()
            else: sel_wiki_char = None
                
        if sel_wiki_char:
            with col_edit:
                char_info = world_data[sel_wiki_char]
                st.markdown(f"### {sel_wiki_char} 的绝密档案")
                
                t_basic, t_combat, t_bg, t_voice, t_stats = st.tabs(["基础定位", "能力与势力", "背景与动机", "语音试听", "📊 战力雷达"])
                
                with t_basic:
                    roles = ["核心主角", "重要配角", "反派BOSS", "炮灰/路人", "系统/金手指", "未分类"]
                    e_role = st.selectbox("角色定位", roles, index=roles.index(char_info.get("role", "未分类")) if char_info.get("role") in roles else 5)
                    e_tags = st.text_input("性格标签 (逗号分隔)", value=",".join(char_info.get("tags", [])))
                    e_app = st.text_input("外貌体型", value=char_info.get("appearance", ""))
                with t_combat:
                    e_faction = st.text_input("所属势力", value=char_info.get("faction", ""))
                    e_ability = st.text_area("异能体系与功法", value=char_info.get("ability", ""), height=100)
                    e_weak = st.text_input("致命弱点", value=char_info.get("weakness", ""))
                with t_bg:
                    e_bg = st.text_area("身世背景 (仅AI可见)", value=char_info.get("background", ""), height=120)
                    e_mot = st.text_area("核心动机", value=char_info.get("motivation", ""), height=100)
                with t_voice:
                    e_voice = st.text_area("声线与口癖", value=char_info.get("voice", ""), height=100)
                    if st.button("🔊 试听角色声线"):
                        speak_text = e_voice if e_voice else f"我是{sel_wiki_char}"
                        components.html(f"<script>var msg=new SpeechSynthesisUtterance('{speak_text}');msg.lang='zh-CN';window.speechSynthesis.speak(msg);</script>", height=0)
                
                with t_stats:
                    c_radar, c_sliders = st.columns([1, 1])
                    stats = char_info.get("stats", {"武力": 50, "智力": 50, "防御": 50, "敏捷": 50, "魅力": 50, "气运": 50})
                    new_stats = {}
                    with c_sliders:
                        st.markdown("##### 调节各项数值 (支持破万高战力)")
                        for stat_name in ["武力", "智力", "防御", "敏捷", "魅力", "气运"]:
                            new_stats[stat_name] = st.number_input(stat_name, 0, 9999999, int(stats.get(stat_name, 50)))
                    
                    with c_radar:
                        radar_max = max([100] + list(new_stats.values())) * 1.1 
                        radar_html = f"""
                        <!DOCTYPE html><html>
                        <head><script src="{ECHARTS_CDN}"></script></head>
                        <body style="margin:0;padding:0;background-color:transparent;">
                            <div id="radar" style="width:100%;height:300px;"></div>
                            <script>
                                var myChart = echarts.init(document.getElementById('radar'));
                                var option = {{
                                    radar: {{
                                        indicator: [
                                            {{ name: '武力', max: {radar_max} }},
                                            {{ name: '智力', max: {radar_max} }},
                                            {{ name: '防御', max: {radar_max} }},
                                            {{ name: '敏捷', max: {radar_max} }},
                                            {{ name: '魅力', max: {radar_max} }},
                                            {{ name: '气运', max: {radar_max} }}
                                        ],
                                        radius: '75%',
                                        axisName: {{color: '#888', fontSize: 13, fontWeight: 'bold'}}
                                    }},
                                    series: [{{
                                        type: 'radar',
                                        data: [{{
                                            value: [{new_stats["武力"]}, {new_stats["智力"]}, {new_stats["防御"]}, {new_stats["敏捷"]}, {new_stats["魅力"]}, {new_stats["气运"]}],
                                            name: '{sel_wiki_char}',
                                            areaStyle: {{color: 'rgba(255, 75, 75, 0.4)'}},
                                            lineStyle: {{color: '#ff4b4b'}},
                                            itemStyle: {{color: '#ff4b4b'}}
                                        }}]
                                    }}]
                                }};
                                myChart.setOption(option);
                            </script>
                        </body></html>
                        """
                        components.html(radar_html, height=320)

                if st.button(f"💾 保存全息档案", type="primary", use_container_width=True):
                    char_info.update({"role": e_role, "tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot, "stats": new_stats})
                    save_json(WORLD_FILE, world_data); st.toast("档案已归档！")

    with tab_graph:
        st.info("💡 ECharts 交互球状网：已应用完美防裁切容器！")
        c_auto, c_space = st.columns([1, 2])
        with c_auto:
            if st.button("🤖 AI 扫描重构关系网", type="primary", use_container_width=True):
                with st.spinner("AI 正在重构网络..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                        prompt = f"已知角色：{char_keys}。梳理关系。输出纯JSON字典，格式：{{\"relationships\": [{{\"source\": \"A\", \"label\": \"死敌\", \"target\": \"B\"}}]}}\n文本：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        rel_data = json.loads(clean_json(res.choices[0].message.content))
                        rels = rel_data.get("relationships", [])
                        world_data["_relationships"].extend(rels)
                        deduplicate_relationships(world_data)
                        save_json(WORLD_FILE, world_data); st.rerun()
                    except Exception as e: st.error(f"关系网解析失败: {e}")

        # 【痛点彻底修复】：加入 zoom: 0.75 强力收缩，并应用安全边距 grid。
        nodes = [{"name": k, "symbolSize": 60 if world_data[k].get("role") == "核心主角" else (45 if world_data[k].get("role") == "重要配角" else 30), "itemStyle": {"color": "#ff4b4b" if world_data[k].get("role") == "核心主角" else "#3366cc"}} for k in char_keys]
        links = [{"source": r["source"], "target": r["target"], "value": r["label"]} for r in world_data.get("_relationships", [])]
        
        if nodes:
            echarts_html = f"""
            <!DOCTYPE html><html>
            <head>
                <meta charset="utf-8">
                <script src="{ECHARTS_CDN}"></script>
                <style>html, body, #main {{width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;}}</style>
            </head>
            <body>
                <div id="main"></div>
                <script>
                    var chartDom = document.getElementById('main');
                    var myChart = echarts.init(chartDom);
                    var option = {{
                        tooltip: {{ formatter: '{{b}}' }},
                        series: [{{
                            type: 'graph', layout: 'force', roam: true, draggable: true, 
                            zoom: 0.75, /* 强力缩放防裁切 */
                            center: ['50%', '50%'],
                            label: {{show: true, position: 'right', fontSize: 14, color: 'inherit'}},
                            edgeSymbol: ['none', 'arrow'], edgeSymbolSize: [4, 10],
                            edgeLabel: {{show: true, fontSize: 12, formatter: '{{c}}'}},
                            force: {{repulsion: 300, edgeLength: 100, gravity: 0.3}}, /* 提高引力聚拢 */
                            data: {json.dumps(nodes, ensure_ascii=False)},
                            links: {json.dumps(links, ensure_ascii=False)}
                        }}]
                    }};
                    myChart.setOption(option);
                    window.onresize = function() {{ myChart.resize(); }};
                </script>
            </body></html>
            """
            st.markdown("<div style='border:1px solid #ddd; border-radius:10px; padding:20px; background:#fff; height: 600px; overflow: hidden;'>", unsafe_allow_html=True)
            components.html(echarts_html, height=580)
            st.markdown("</div>", unsafe_allow_html=True)
        else:
            st.warning("暂无角色数据，无法生成可视化网络图。请先在左侧录入角色。")

        st.markdown("---")
        with st.expander("🛠️ 手动建立新羁绊", expanded=False):
            c_rel1, c_rel2, c_rel3, c_btn = st.columns([2, 2, 2, 1])
            with c_rel1: r_source = st.selectbox("起始角色", char_keys, key="rs") if char_keys else None
            with c_rel2: r_type = st.text_input("羁绊 (如: 暗恋)")
            with c_rel3: r_target = st.selectbox("目标角色", char_keys, key="rt") if char_keys else None
            with c_btn:
                st.write("")
                if st.button("🔗 连接", use_container_width=True) and r_source and r_target and r_type:
                    world_data["_relationships"].append({"source": r_source, "label": r_type, "target": r_target})
                    deduplicate_relationships(world_data)
                    save_json(WORLD_FILE, world_data); st.rerun()

            for idx, rel in enumerate(world_data.get("_relationships", [])):
                cc1, cc3 = st.columns([9, 1])
                with cc1: st.markdown(f"**{rel.get('source')}** ⟷ `[{rel.get('label')}]` ⟷ **{rel.get('target')}**")
                with cc3:
                    if st.button("✂️ 斩断", key=f"cut_{idx}"):
                        world_data["_relationships"].pop(idx); save_json(WORLD_FILE, world_data); st.rerun()

# ----------------- 路由 9: 编年史时间轴 -----------------
elif app_mode == "编年史时间轴":
    tl_view = st.radio("切换时间轴视图", ["🌌 动态气泡时间轴 (防裁切)", "📜 详细事件流 (编辑模式)"], horizontal=True)
    
    if tl_view == "🌌 动态气泡时间轴 (防裁切)":
        st.info("💡 鼠标悬停查看详情，使用完美安全边距！")
        if not timeline_data:
            st.warning("暂无事件，请切换至【平铺可编辑】手动添加或让 AI 扫描生成。")
        else:
            # 【痛点修复：安全边距与缩放，完美展示气泡图】
            tl_nodes = []
            x_categories = []
            for i, ev in enumerate(timeline_data):
                x_categories.append(ev.get('time', f'节点{i}'))
                y_val = 1 if i % 2 == 0 else -1  
                desc = ev.get('desc', '').replace('\n', '<br>')
                tl_nodes.append({"name": ev.get('title', '未知'), "value": [i, y_val], "desc": desc, "time": ev.get('time', '')})

            tl_html = f"""
            <!DOCTYPE html><html>
            <head>
                <meta charset="utf-8">
                <script src="{ECHARTS_CDN}"></script>
                <style>html, body, #main {{width: 100%; height: 100%; margin: 0; padding: 0; overflow: hidden;}}</style>
            </head>
            <body>
                <div id="main"></div>
                <script>
                    var chartDom = document.getElementById('main');
                    var myChart = echarts.init(chartDom);
                    var option = {{
                        backgroundColor: 'transparent',
                        grid: {{ top: 50, bottom: 50, left: 40, right: 40 }}, /* 安全边距防裁切 */
                        tooltip: {{
                            trigger: 'item',
                            formatter: function (p) {{
                                return '<div style="max-width:300px;white-space:normal;"><b>[' + p.data.time + '] ' + p.data.name + '</b><br><hr style="margin:5px 0;">' + p.data.desc + '</div>';
                            }}
                        }},
                        xAxis: {{
                            type: 'category',
                            data: {json.dumps(x_categories, ensure_ascii=False)},
                            axisLine: {{ lineStyle: {{ color: '#888' }} }},
                            axisLabel: {{ rotate: 30, interval: 0 }}
                        }},
                        yAxis: {{ type: 'value', show: false, min: -3, max: 3 }}, /* 扩大上下空间 */
                        series: [{{
                            type: 'scatter',
                            symbolSize: 22,
                            itemStyle: {{ color: '#2196F3', shadowBlur: 8, shadowColor: 'rgba(33,150,243,0.5)' }},
                            data: {json.dumps(tl_nodes, ensure_ascii=False)}
                        }}, {{
                            type: 'line',
                            data: {json.dumps([[n["value"][0], 0] for n in tl_nodes])},
                            lineStyle: {{ color: '#ccc', type: 'dashed' }},
                            symbol: 'none',
                            z: -1
                        }}]
                    }};
                    myChart.setOption(option);
                    window.onresize = function() {{ myChart.resize(); }};
                </script>
            </body></html>
            """
            st.markdown("<div style='border:1px solid #ddd; border-radius:10px; padding:10px; background:#fff; height: 350px;'>", unsafe_allow_html=True)
            components.html(tl_html, height=330)
            st.markdown("</div>", unsafe_allow_html=True)
            
    else:
        c_man, c_auto = st.columns(2)
        with c_man:
            with st.expander("➕ 手动刻录大事件"):
                with st.form("add_event"):
                    e_time = st.text_input("时间节点 (例: 2025年 / 新纪元3年)")
                    e_title = st.text_input("事件名称")
                    e_desc = st.text_area("详细描述")
                    if st.form_submit_button("载入史册"):
                        timeline_data.append({"time": e_time, "title": e_title, "desc": e_desc})
                        save_json(TIMELINE_FILE, timeline_data); st.rerun()
        with c_auto:
            st.info("老书没有时间轴？让 AI 自动梳理。")
            if st.button("🤖 AI 自动阅读并生成编年史", type="primary", use_container_width=True):
                with st.spinner("跨越时间长河梳理中..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                        prompt = f"提取原著大事件。输出纯JSON字典，格式：{{\"events\": [{{\"time\":\"时间\",\"title\":\"标题\",\"desc\":\"描述\"}}]}}\n文本：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        parsed_data = json.loads(clean_json(res.choices[0].message.content))
                        ev_list = parsed_data.get("events", [])
                        if ev_list:
                            timeline_data.extend(ev_list)
                            save_json(TIMELINE_FILE, timeline_data); st.success("入库成功！"); st.rerun()
                    except Exception as e: st.error(f"提取失败: {e}")

        for idx, event in enumerate(timeline_data):
            c_line, c_card, c_del = st.columns([1, 10, 1])
            with c_line: st.markdown(f"**{event.get('time')}**<br><div style='width:2px;height:50px;background:#ff4b4b;margin-left:10px;'></div>", unsafe_allow_html=True)
            with c_card:
                with st.expander(f"{event.get('title')} (展开编辑)"):
                    et = st.text_input("时间", value=event.get('time'), key=f"t_{idx}")
                    eti = st.text_input("标题", value=event.get('title'), key=f"ti_{idx}")
                    ed = st.text_area("描述", value=event.get('desc'), key=f"d_{idx}")
                    if st.button("保存", key=f"sev_{idx}"):
                        timeline_data[idx] = {"time": et, "title": eti, "desc": ed}
                        save_json(TIMELINE_FILE, timeline_data); st.rerun()
            with c_del:
                if st.button("删除", key=f"dev_{idx}"): timeline_data.pop(idx); save_json(TIMELINE_FILE, timeline_data); st.rerun()

# ----------------- 路由 10: 设定提炼引擎 -----------------
elif app_mode == "宗师工具箱(提取)":
    sample_context = "\n\n".join([ch["content"] for ch in chapters_data[:3]])[:6000] if chapters_data else ""
    t1, t2, t3 = st.tabs(["🌍 世界观引擎", "👤 角色引擎", "🗺️ 大纲引擎"])
    
    with t1:
        if st.button("🔍 从小说提炼世界观" if sample_context else "🪄 生成新世界观", type="primary" if sample_context else "secondary"):
            with st.spinner("构架中..."):
                try:
                    prompt = f"阅读原文片段，【提炼】世界观设定。\n原文：{sample_context}" if sample_context else f"生成【{novel_style}】长篇世界观。"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.session_state.ai_reply = res.choices[0].message.content
                except Exception as e: st.error(f"网络异常: {e}")
        if st.session_state.ai_reply and "设定" in st.session_state.ai_reply:
            if st.button("📥 一键覆盖至全书大纲"):
                open(BOOK_OUTLINE_FILE, "a", encoding="utf-8").write("\n\n" + st.session_state.ai_reply)
                st.session_state.ai_reply = ""; st.toast("已追加！"); st.rerun()

    with t2:
        if st.button("🔍 提取档案并生成 (JSON)", type="primary"):
            with st.spinner("梳理中..."):
                prompt = f"提取核心角色。输出JSON字典。物理魔法状态在10字内。\n原文：{sample_context}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                st.session_state.ai_reply = res.choices[0].message.content
        if st.session_state.ai_reply and "{" in st.session_state.ai_reply:
            if st.button("📥 一键将以上角色汇入图鉴", type="primary"):
                try:
                    new_c = json.loads(clean_json(st.session_state.ai_reply))
                    for k, v in new_c.items():
                        if k not in world_data and k not in ["主角", "反派"]: world_data[k] = normalize_char(v)
                    save_json(WORLD_FILE, world_data)
                    st.session_state.ai_reply = ""; st.success("入库成功！"); st.rerun()
                except Exception as e: st.error(f"解析失败: {e}")
                
    with t3:
        if st.button("🗺️ 推演后续大纲"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于前文续写大纲：\n{sample_context}"}])
                st.session_state.ai_reply = res.choices[0].message.content
            except Exception as e: st.error(f"网络异常: {e}")
        if st.session_state.ai_reply and "大纲" in st.session_state.ai_reply:
            if st.button("📥 追加至全书大纲"):
                open(BOOK_OUTLINE_FILE, "a", encoding="utf-8").write("\n\n" + st.session_state.ai_reply)
                st.session_state.ai_reply = ""; st.toast("已追加！"); st.rerun()

    if st.session_state.ai_reply:
        st.markdown("---")
        st.text_area("智囊团结果", value=st.session_state.ai_reply, height=400)

# ----------------- 路由 11: 逻辑体检与防吃书 -----------------
elif app_mode == "逻辑体检与防吃书":
    tab_check, tab_lore, tab_clue = st.tabs(["🩺 章节逻辑体检", "🛡️ AI 防吃书检索", "📌 伏笔追踪器"])
    
    with tab_check:
        st.info("让大模型扫描最近章节，寻找前后矛盾与漏洞。")
        check_range = st.slider("检查最近多少章？", 1, max(1, len(chapters_data)), min(5, len(chapters_data)))
        if st.button("🚀 开始全面体检", type="primary"):
            with st.spinner("扫描漏洞中..."):
                try:
                    target_chs = chapters_data[-check_range:] if chapters_data else []
                    text = "\n".join([f"{ch['title']}：{ch['content'][:1500]}..." for ch in target_chs])
                    prompt = f"分析以下章节逻辑漏洞、人设OOC、节奏问题。给出修改方案。\n【章节】：\n{text}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.write(res.choices[0].message.content)
                except Exception as e: st.error(f"API 服务器繁忙: {e}")

    with tab_lore:
        st.info("向 AI 提问设定，AI 会翻阅现有设定集和前文寻找证据。")
        lore_query = st.text_input("输入查证疑问：")
        if st.button("🛡️ 发起检索"):
            with st.spinner("比对中..."):
                try:
                    sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:8000]
                    prompt = f"你是防吃书系统。解答疑问，若找不到说明“未设定”。\n【提问】：{lore_query}\n【设定库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【前文】：{sample_txt}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.success("完成："); st.write(res.choices[0].message.content)
                except Exception as e: st.error(f"失败: {e}")

    with tab_clue:
        with st.expander("➕ 手动埋设新伏笔"):
            c_title = st.text_input("伏笔名称 (如: 神秘的玉佩)")
            c_desc = st.text_area("详情与计划")
            if st.button("埋入"):
                clues_data.append({"title": c_title, "desc": c_desc, "status": "🔴 未回收"})
                save_json(CLUES_FILE, clues_data); st.rerun()
                
        for idx, clue in enumerate(clues_data):
            c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
            with c1: st.markdown(f"**{clue['title']}**<br><span style='color:gray;font-size:14px'>{clue['desc']}</span>", unsafe_allow_html=True)
            with c2: st.markdown(f"状态: **{clue['status']}**")
            with c3:
                if st.button("切状态", key=f"clue_s_{idx}"):
                    clues_data[idx]["status"] = "🟢 已回收" if clue["status"] == "🔴 未回收" else "🔴 未回收"
                    save_json(CLUES_FILE, clues_data); st.rerun()
            with c4:
                if st.button("删除", key=f"clue_d_{idx}"):
                    clues_data.pop(idx); save_json(CLUES_FILE, clues_data); st.rerun()

# ----------------- 路由 12: 数据分析仪表盘 -----------------
elif app_mode == "数据分析仪表盘":
    st.info("数据看板可以直观呈现您的创作进度与各角色活跃度。")
    if not chapters_data:
        st.warning("暂无数据。")
    else:
        c1, c2 = st.columns(2)
        with c1:
            st.markdown("#### 📈 章节字数增长趋势")
            word_counts = [len(ch['content']) for ch in chapters_data]
            # 【痛点修复：使用极简坐标防止倒转】
            chapter_labels = [f"第{i+1}章" for i in range(len(chapters_data))]
            chart_data = pd.DataFrame({"章节": chapter_labels, "字数": word_counts})
            line_chart = alt.Chart(chart_data).mark_line(point=True, color='#4CAF50').encode(
                x=alt.X('章节', sort=None, axis=alt.Axis(labelAngle=0)),
                y='字数',
                tooltip=['章节', '字数']
            ).properties(height=350)
            st.altair_chart(line_chart, use_container_width=True)
            st.caption(f"总计入库字数：{sum(word_counts)} 字")
            
        with c2:
            st.markdown("#### 🔥 核心角色出场热度")
            mentions = {k: 0 for k in char_keys}
            for ch in chapters_data:
                for k in char_keys: mentions[k] += ch['content'].count(k)
            active_mentions = {k: v for k, v in mentions.items() if v > 0}
            if active_mentions:
                bar_data = pd.DataFrame({"角色": list(active_mentions.keys()), "提及频次": list(active_mentions.values())})
                bar_chart = alt.Chart(bar_data).mark_bar(color='#2196F3').encode(
                    x=alt.X('角色', sort='-y', axis=alt.Axis(labelAngle=0)),
                    y='提及频次',
                    tooltip=['角色', '提及频次']
                ).properties(height=350)
                st.altair_chart(bar_chart, use_container_width=True)
            else:
                st.write("暂无角色出场数据。")

# ----------------- 路由 13: 灵感与素材库 -----------------
elif app_mode == "灵感与素材库":
    with st.expander("📤 上传本地多媒体"):
        uploaded_files = st.file_uploader("支持图片、音频、视频及文档", accept_multiple_files=True)
        if st.button("保存文件", type="primary"):
            if uploaded_files:
                for f in uploaded_files:
                    path = f"materials/{cur_book}_{f.name}"
                    with open(path, "wb") as file: file.write(f.getbuffer())
                    materials_data.append({"name": f.name, "type": f.type, "path": path, "url": "", "desc": ""})
                save_json(MATERIALS_FILE, materials_data); st.success("上传成功！"); st.rerun()

    with st.expander("🔗 录入网络外链"):
        col_url, col_desc = st.columns(2)
        with col_url: link_url = st.text_input("网页/视频URL")
        with col_desc: link_name = st.text_input("素材命名")
        if st.button("保存链接"):
            if link_url and link_name:
                materials_data.append({"name": link_name, "type": "url", "path": "", "url": link_url, "desc": ""})
                save_json(MATERIALS_FILE, materials_data); st.success("录入成功！"); st.rerun()

    st.markdown("### 🗂️ 我的素材库")
    if not materials_data: st.warning("素材库为空。")
    for idx, mat in enumerate(materials_data):
        with st.expander(f"{mat['name']}"):
            c_media, c_info = st.columns([2, 1])
            with c_media:
                if mat["type"].startswith("image"): st.image(mat["path"], use_container_width=True)
                elif mat["type"].startswith("audio"): st.audio(mat["path"])
                elif mat["type"].startswith("video"): st.video(mat["path"])
                elif mat["type"] == "url": st.markdown(f"**🔗 外链:** [{mat['url']}]({mat['url']})")
                elif mat["type"].startswith("text/plain"):
                    try: st.text_area("文档内容", value=open(mat["path"], "r", encoding="utf-8").read(), height=150)
                    except: pass
            with c_info:
                new_desc = st.text_area("批注:", value=mat.get("desc", ""), key=f"md_{idx}")
                if st.button("保存批注", key=f"ms_{idx}"):
                    materials_data[idx]["desc"] = new_desc
                    save_json(MATERIALS_FILE, materials_data); st.toast("已保存")
                if st.button("删除素材", key=f"mdel_{idx}"):
                    if mat["path"] and os.path.exists(mat["path"]): os.remove(mat["path"])
                    materials_data.pop(idx); save_json(MATERIALS_FILE, materials_data); st.rerun()

# ----------------- 路由 14: 沉浸阅读与批注 -----------------
elif app_mode == "沉浸阅读与批注":
    if not chapters_data: st.warning("尚无章节。")
    else:
        c_read, c_ai = st.columns([3, 2])
        with c_read:
            read_idx = st.selectbox("选择章节", range(len(chapters_data)), format_func=lambda x: chapters_data[x]['title'])
            current_ch = chapters_data[read_idx]
            st.markdown(f"## {current_ch['title']}")
            st.markdown(f"<div style='background-color:#f9f9f9; padding:20px; border-radius:10px; line-height:1.8; font-size:16px; color:#333; height:600px; overflow-y:auto;'>{current_ch['content'].replace(chr(10), '<br><br>')}</div>", unsafe_allow_html=True)
            
        with c_ai:
            st.markdown("### AI 重铸台")
            target_text = st.text_area("粘贴要重写的原句 (完全匹配原文)", height=150)
            directive = st.text_input("重写指令")
            
            if st.button("生成重塑版", type="primary", use_container_width=True):
                if target_text in current_ch['content']:
                    with st.spinner("AI 重铸中..."):
                        try:
                            prompt = f"根据指令重写片段。紧扣指令，去除AI味。\n【原句】：{target_text}\n【指令】：{directive}"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state[f"rewrite_{read_idx}"] = res.choices[0].message.content
                        except Exception as e: st.error(f"异常: {e}")
                else: st.error("未找到原文")
                    
            new_text = st.session_state.get(f"rewrite_{read_idx}", "")
            if new_text:
                final_text = st.text_area("重塑结果 (可再修改)：", value=new_text, height=150)
                if st.button("一键替换回原文"):
                    chapters_data[read_idx]['content'] = current_ch['content'].replace(target_text, final_text)
                    save_json(CHAPTERS_FILE, chapters_data)
                    st.session_state[f"rewrite_{read_idx}"] = ""; st.success("已替换！"); st.rerun()

# ----------------- 路由 15: 全自动同人番外 -----------------
elif app_mode == "全自动同人番外":
    st.info("💡 让 AI 基于设定，生成平行宇宙番外、人物前传或日常段子！")
    if not char_keys: st.warning("角色库为空，请先录入角色。")
    else:
        c1, c2 = st.columns(2)
        with c1: fanfic_chars = st.multiselect("挑选角色 (自动带入设定)", char_keys, default=char_keys[:2] if len(char_keys)>=2 else char_keys)
        with c2: fanfic_theme = st.text_input("脑洞/主题", placeholder="例如：现代校园日常 / 互换身体")
            
        if st.button("🚀 启动发电机", type="primary", use_container_width=True):
            if fanfic_chars and fanfic_theme:
                with st.spinner("AI 放飞自我中..."):
                    try:
                        char_profiles = {k: world_data[k] for k in fanfic_chars}
                        prompt = f"你是网文番外写手。基于设定写同人番外。\n【角色】：{json.dumps(char_profiles, ensure_ascii=False)}\n【主题】：{fanfic_theme}\n【要求】：不OOC，800字，越有趣越好。"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                        st.session_state.fanfic_result = res.choices[0].message.content
                    except Exception as e: st.error(f"生成失败: {e}")
            else: st.warning("请选择角色并输入主题！")
                
    if st.session_state.get("fanfic_result"):
        st.markdown("---")
        st.markdown("### 📝 番外篇")
        st.write(st.session_state.fanfic_result)
