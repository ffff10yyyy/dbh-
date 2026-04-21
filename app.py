import streamlit as st
import json
import os
import random
import re
import base64
import streamlit.components.v1 as components
from openai import OpenAI

# ================= 1. 引擎初始化 =================
with st.sidebar:
    st.header("🔑 引擎激活")
    user_api_key = st.text_input("请输入 DeepSeek API Key", type="password", value="sk-0275d85e2cd348d09b81fb01321b0147")
    if not user_api_key:
        st.warning("👈 请输入 API Key 启动引擎")
        st.stop()
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")

st.set_page_config(page_title="DBH-上帝大脑 v1.3", layout="wide")

# ================= 1.2 界面主题引擎 (新增) =================
with st.sidebar:
    st.markdown("---")
    theme_choice = st.radio("🎨 界面主题", ["跟随系统", "🌙 暗黑模式", "🌿 护眼模式"], horizontal=True)
    if theme_choice == "🌙 暗黑模式":
        st.markdown("""<style>
            .stApp { background-color: #121212 !important; color: #E0E0E0 !important; }
            .stTextInput>div>div>input, .stTextArea>div>textarea { background-color: #2D2D2D !important; color: #FFF !important; }
            p, h1, h2, h3, h4, h5, h6, span, label { color: #E0E0E0 !important; }
        </style>""", unsafe_allow_html=True)
    elif theme_choice == "🌿 护眼模式":
        st.markdown("""<style>
            .stApp { background-color: #C7EDCC !important; color: #2D372B !important; }
            .stTextInput>div>div>input, .stTextArea>div>textarea { background-color: #E3EDCD !important; color: #2D372B !important; }
            p, h1, h2, h3, h4, h5, h6, span, label { color: #2D372B !important; }
        </style>""", unsafe_allow_html=True)

# ================= 1.5 强力数据自愈清洗器 =================
def clean_json(text):
    if not text: return "{}"
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

def normalize_char(data):
    if not isinstance(data, dict):
        data = {"physical":"健康", "magic":"充盈", "status":str(data)[:10], "inventory":[], "tags":[], "appearance":"", "voice":"", "faction":"", "ability":"", "weakness":"", "background":str(data), "motivation":"", "role":"未分类"}
    for key in ["tags", "inventory"]:
        val = data.get(key, [])
        if isinstance(val, str): data[key] = [val]
        elif not isinstance(val, list): data[key] = []
    for key in ["physical", "magic", "status", "appearance", "voice", "faction", "ability", "weakness", "background", "motivation", "role"]:
        if key not in data or not isinstance(data[key], str): data[key] = str(data.get(key, ""))
    if not data.get("role"): data["role"] = "未分类"
    return data

if not os.path.exists("materials"): os.makedirs("materials")

# ================= 2. 藏书馆与全局管理 =================
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
if "ai_reply" not in st.session_state: st.session_state.ai_reply = ""
if "rebuild_text" not in st.session_state: st.session_state.rebuild_text = ""

with st.sidebar:
    st.header("📚 藏书阁")
    active_idx = books.index(st.session_state.active_book) if st.session_state.active_book in books else 0
    selected_book = st.selectbox("当前操作作品", books, index=active_idx)
    st.session_state.active_book = selected_book

    with st.expander("➕ 新建与导入老书"):
        tab_new, tab_import = st.tabs(["新建空小说", "导入 TXT 老书"])
        with tab_new:
            new_book = st.text_input("新书名：", key="new_book_input")
            if st.button("创建新书", use_container_width=True) and new_book:
                if new_book not in books:
                    books.append(new_book)
                    save_json(LIBRARY_FILE, books); st.session_state.active_book = new_book; st.rerun()
        with tab_import:
            st.caption("自动解析章节并创建独立新书")
            uploaded_file = st.file_uploader("选择 TXT", type=["txt"], label_visibility="collapsed")
            split_method = st.radio("分章策略", ["智能正则(默认)", "自定义标志词", "不分章(全文导入)"])
            custom_kw = st.text_input("输入章节前缀 (如 '第' 或 'Chapter')") if split_method == "自定义标志词" else ""

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
                    save_json(f"{new_name}_kanban.json", [{"lane": "第一卷", "events": ["在此添加大纲节点"]}])
                    
                    st.session_state.active_book = new_name
                    st.success(f"导入成功！生成新书《{new_name}》")
                    st.rerun()

    with st.expander("⚙️ 当前作品设置"):
        novel_style = st.selectbox("全书风格锚点", ["番茄爽文/快节奏升级", "起点升级流/宏大叙事", "晋江细腻向/情感共鸣", "诡秘悬疑风/不可名状", "二次元轻小说/吐槽搞笑"])
        if st.button("🧨 一键销毁当前作品 (危险)", type="primary", use_container_width=True):
            if selected_book in books:
                books.remove(selected_book); save_json(LIBRARY_FILE, books)
                st.session_state.active_book = books[0] if len(books) > 0 else None
                st.rerun()

    st.markdown("---")
    st.markdown("### DBH v1.3 导航")
    # 【新增灵感X路由】：大纲卡片与看板
    app_mode = st.radio("🧭 核心控制台", ["🖋️ 连载写作台", "📋 卡片大纲与看板", "📖 目录精修与拆分", "📖 沉浸阅读与批注", "⏳ 编年史时间轴", "👥 角色图鉴与关系网", "🩺 逻辑体检与防吃书", "💡 灵感与素材库", "🧰 宗师工具箱"], label_visibility="collapsed")

# ================= 3. 数据加载与隔离 =================
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
if not os.path.exists(KANBAN_FILE): save_json(KANBAN_FILE, [{"lane": "第一卷 (初期)", "events": ["主角遭遇危机", "金手指觉醒"]}])

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
save_json(WORLD_FILE, world_data)

# ================= 4. 数据更新与回溯保护 =================
if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)
    st.session_state.ai_reply = ""

if st.session_state.rebuild_text:
    with st.spinner("🕵️‍♂️ 数据同步中(安全模式)..."):
        try:
            p_reb = f"分析文段中出场角色的状态。输出纯JSON字典。\n【要求】：绝对不要脑补！必须是客观事实！physical, magic, status 的值控制在 4-10 字。\n【库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_text}"
            r_reb = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_reb}], response_format={"type":"json_object"})
            updated = json.loads(clean_json(r_reb.choices[0].message.content))
            for k, v in updated.items():
                if k in world_data: 
                    safe_v = normalize_char(v)
                    world_data[k].update({key: safe_v.get(key) for key in ["physical", "magic", "status", "inventory"]})
            save_json(WORLD_FILE, world_data); st.session_state.rebuild_text = ""; st.rerun()
        except Exception as e:
            st.error(f"同步失败: {e}"); st.session_state.rebuild_text = ""

# ================= 5. 左侧监控 =================
with st.sidebar:
    if app_mode in ["🖋️ 连载写作台", "👥 角色图鉴与关系网", "🩺 逻辑体检与防吃书", "📖 沉浸阅读与批注"]:
        st.markdown("---")
        st.subheader("📊 实时精准监控")
        if char_keys:
            char_options = [f"{k} [{world_data[k].get('role', '未分类')}]" for k in char_keys]
            sel_str = st.selectbox(f"监控角色 (共 {len(char_keys)} 人)", char_options, label_visibility="collapsed")
            selected_char = sel_str.split(" [")[0]
            
            info = world_data[selected_char]
            c_p, c_m = st.columns(2)
            with c_p: st.success(f"💪 {info.get('physical', '健康')}")
            with c_m: st.info(f"✨ {info.get('magic', '充盈')}")
            st.error(f"🏷️ 处境: {info.get('status', '正常')}")

# ================= 6. 右侧：动态路由大厅 =================
st.title(f"《{cur_book}》- {app_mode.split(' ')[1]}")
st.markdown("---")

# ----------------- 路由 1: 连载工作台 -----------------
if app_mode == "🖋️ 连载写作台":
    cg, cl = st.columns(2)
    with cg:
        g_out = st.text_area("🌍 全书走向", value=load_text(BOOK_OUTLINE_FILE), height=100)
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out); st.toast("锁定成功")
    with cl:
        l_out = st.text_area("🚩 本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out); st.toast("锁定成功")

    buffer_val = st.text_area(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        with st.expander("🔍 智能雷达引擎 (自动抓多角色)"):
            if st.button("🚀 全面扫描并录入新角色", use_container_width=True):
                with st.spinner("雷达全开，搜寻全员中..."):
                    try:
                        prompt = f"提取文段中的【所有真实的新角色】。必须是具体的人名！绝对禁止把'主角'、'配角'、'反派'、'系统'当做姓名提取！\n忽略已存在的人：{char_keys}。输出纯JSON字典。\n要求：physical, magic, status 的内容在 4 到 10 个字以内！\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(clean_json(res.choices[0].message.content))
                        added_count = 0
                        for k, v in new_chars.items():
                            if k not in world_data and len(k) > 1 and k not in ["主角", "配角", "反派", "系统", "核心主角", "重要配角"]:
                                world_data[k] = normalize_char(v)
                                added_count += 1
                        save_json(WORLD_FILE, world_data); st.success(f"已安全录入 {added_count} 名真实角色设定！")
                    except Exception as e: st.error(f"提取失败，请检查网络: {e}")

        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章存入目录 (并记录时间轴)", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                
                with st.spinner("后台全自动提炼时间轴..."):
                    try:
                        prompt = f"提炼以下章节的一个核心时间点和事件名。若无具体时间填'当前剧情'。必须只输出纯JSON字典，格式：{{\"time\":\"时间\",\"title\":\"标题\",\"desc\":\"描述\"}}。\n文段：{st.session_state.chapter_buffer[:2000]}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        ev = json.loads(clean_json(res.choices[0].message.content))
                        if "time" in ev and "title" in ev:
                            timeline_data.append(ev)
                            save_json(TIMELINE_FILE, timeline_data)
                    except Exception: st.warning(f"时间轴提炼超时，但章节已入库。")
                
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
        new_in = st.chat_input("下达指令...")
        if new_in: st.session_state.current_prompt = new_in; st.session_state.current_draft = ""; st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner("构思中..."):
                try:
                    prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n设定：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n指令：{st.session_state.current_prompt}\n要求：贴合【{novel_style}】，400字。"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                except Exception as e: st.error(f"AI服务器异常: {e}")

    if st.session_state.current_draft:
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("➕ 接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                st.session_state.rebuild_text = draft # 触发安全数据更新
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ 去 AI 味精修", type="primary"):
                try:
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色片段，去AI味：{draft}"}])
                    st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                except Exception as e: st.error(f"网络异常: {e}")
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

# ----------------- 路由 2: 卡片大纲与看板 (实装灵感X) -----------------
elif app_mode == "📋 卡片大纲与看板":
    st.info("💡 瀑布流大纲看板。你可以分卷列出剧情节点，辅助长线创作规划。")
    
    c_add_lane, _ = st.columns([1, 4])
    with c_add_lane:
        new_lane = st.text_input("新增卷名/阶段", placeholder="如：第二卷 锋芒初露")
        if st.button("➕ 添加卷轴") and new_lane:
            kanban_data.append({"lane": new_lane, "events": []})
            save_json(KANBAN_FILE, kanban_data); st.rerun()
            
    st.markdown("---")
    
    # 动态渲染看板列
    if kanban_data:
        cols = st.columns(len(kanban_data))
        for i, lane in enumerate(kanban_data):
            with cols[i]:
                st.markdown(f"#### 📌 {lane['lane']}")
                for j, ev in enumerate(lane['events']):
                    # 使用 container 模拟卡片效果
                    with st.container():
                        st.info(ev)
                        if st.button("🗑️ 移除", key=f"kb_del_{i}_{j}", help="删除此剧情节点"):
                            lane['events'].pop(j); save_json(KANBAN_FILE, kanban_data); st.rerun()
                
                st.markdown("<br>", unsafe_allow_html=True)
                new_ev = st.text_input("新增剧情卡片", key=f"kb_add_{i}", placeholder="简述剧情...")
                c_kb1, c_kb2 = st.columns(2)
                with c_kb1:
                    if st.button("➕ 添加", key=f"kb_btn_{i}") and new_ev:
                        lane['events'].append(new_ev); save_json(KANBAN_FILE, kanban_data); st.rerun()
                with c_kb2:
                    if st.button("🗑️ 删卷", key=f"kb_del_lane_{i}"):
                        kanban_data.pop(i); save_json(KANBAN_FILE, kanban_data); st.rerun()
    else:
        st.warning("大纲看板为空，请先添加一个卷轴。")

# ----------------- 路由 3: 目录精修与拆分 -----------------
elif app_mode == "📖 目录精修与拆分":
    st.info("💡 直接修改章节，或输入切分词进行向下拆分。")
    if chapters_data:
        export_text = f"《{cur_book}》\n\n"
        for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
        st.download_button("📥 一键导出全本小说 TXT", data=export_text, file_name=f"{cur_book}.txt")
        st.markdown("---")
        
        for idx, ch in enumerate(chapters_data):
            with st.expander(f"📖 第 {idx+1} 章：{ch['title']}"):
                new_title = st.text_input("章节名称", value=ch['title'], key=f"et_{idx}")
                new_content = st.text_area("章节正文", value=ch['content'], height=300, key=f"ec_{idx}")
                
                c_s, c_split, c_del = st.columns([1, 2, 1])
                with c_s:
                    if st.button("💾 保存修改", key=f"save_{idx}", type="primary"):
                        chapters_data[idx]['title'] = new_title
                        chapters_data[idx]['content'] = new_content
                        save_json(CHAPTERS_FILE, chapters_data); st.toast("保存成功"); st.rerun()
                with c_split:
                    split_str = st.text_input("✂️ 从此句向下拆分为新章", placeholder="复制正文句子", key=f"sp_{idx}")
                    if st.button("切割", key=f"sbtn_{idx}") and split_str:
                        if split_str in new_content:
                            parts = new_content.split(split_str, 1)
                            chapters_data[idx]['content'] = parts[0].strip()
                            chapters_data.insert(idx+1, {"title": "新拆分章节", "content": (split_str + parts[1]).strip()})
                            save_json(CHAPTERS_FILE, chapters_data); st.success("拆分成功！"); st.rerun()
                        else: st.error("未找到句子")
                with c_del:
                    if st.button("🗑️ 删除本章", key=f"del_{idx}"):
                        chapters_data.pop(idx); save_json(CHAPTERS_FILE, chapters_data); st.rerun()

# ----------------- 路由 4: 沉浸阅读与批注 -----------------
elif app_mode == "📖 沉浸阅读与批注":
    st.info("💡 阅读模式：摘录不满意的段落，让 AI 进行专项风格强化与重塑。")
    if not chapters_data:
        st.warning("书籍尚无章节，请先在工作台创作。")
    else:
        c_read, c_ai = st.columns([3, 2])
        
        with c_read:
            read_idx = st.selectbox("选择章节", range(len(chapters_data)), format_func=lambda x: chapters_data[x]['title'])
            current_ch = chapters_data[read_idx]
            st.markdown(f"## {current_ch['title']}")
            st.markdown(f"<div style='background-color:#f9f9f9; padding:20px; border-radius:10px; line-height:1.8; font-size:16px; color:#333; height:600px; overflow-y:auto;'>{current_ch['content'].replace(chr(10), '<br><br>')}</div>", unsafe_allow_html=True)
            
        with c_ai:
            st.markdown("### ✍️ AI 批注与重铸台")
            target_text = st.text_area("1. 粘贴要重写的原句/段落 (必须完全匹配原文)", height=150)
            directive = st.text_input("2. 重写指令", placeholder="例如：改写得更血腥一点 / 加入更多视觉感官描写 / 换成嘲讽的语气")
            
            if st.button("✨ 生成重塑版", type="primary", use_container_width=True):
                if target_text and target_text in current_ch['content']:
                    with st.spinner("AI 重铸中..."):
                        try:
                            prompt = f"请根据指令，重写以下小说片段。必须紧扣指令要求，去除AI味，贴合网文质感。\n【原句】：{target_text}\n【指令】：{directive}"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                            st.session_state[f"rewrite_{read_idx}"] = res.choices[0].message.content
                        except Exception as e: st.error(f"异常: {e}")
                else:
                    st.error("⚠️ 未在当前章节找到该段落，请确保原封不动地复制原文。")
                    
            new_text = st.session_state.get(f"rewrite_{read_idx}", "")
            if new_text:
                st.info("💡 重塑结果：")
                final_text = st.text_area("你可以再次修改此结果：", value=new_text, height=150)
                if st.button("🔄 一键替换回原文"):
                    chapters_data[read_idx]['content'] = current_ch['content'].replace(target_text, final_text)
                    save_json(CHAPTERS_FILE, chapters_data)
                    st.session_state[f"rewrite_{read_idx}"] = ""
                    st.success("已替换！"); st.rerun()

# ----------------- 路由 5: 编年史时间轴 -----------------
elif app_mode == "⏳ 编年史时间轴":
    c_man, c_auto = st.columns(2)
    with c_man:
        with st.expander("➕ 手动刻录大事件"):
            with st.form("add_event"):
                e_time = st.text_input("时间节点")
                e_title = st.text_input("事件名称")
                e_desc = st.text_area("详细描述")
                if st.form_submit_button("载入史册"):
                    timeline_data.append({"time": e_time, "title": e_title, "desc": e_desc})
                    save_json(TIMELINE_FILE, timeline_data); st.rerun()
    with c_auto:
        st.info("💡 老书没有时间轴？让 AI 自动梳理。")
        if st.button("🤖 AI 自动阅读并生成编年史", type="primary", use_container_width=True):
            with st.spinner("AI 正在跨越时间长河梳理历史..."):
                try:
                    sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                    prompt = f"提取原著大事件。输出纯JSON字典，格式：{{\"events\": [{{\"time\":\"时间\",\"title\":\"事件标题\",\"desc\":\"详细描述\"}}]}}\n文本：{sample_txt}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                    parsed_data = json.loads(clean_json(res.choices[0].message.content))
                    ev_list = parsed_data.get("events", [])
                    if ev_list:
                        timeline_data.extend(ev_list)
                        save_json(TIMELINE_FILE, timeline_data); st.success("入库成功！"); st.rerun()
                    else: st.warning("未提取到明显大事件。")
                except Exception as e:
                    st.error(f"提取失败: {e}")

    for idx, event in enumerate(timeline_data):
        c_line, c_card, c_del = st.columns([1, 10, 1])
        with c_line: st.markdown(f"**{event.get('time')}**<br><div style='width:2px;height:50px;background:#ff4b4b;margin-left:10px;'></div>", unsafe_allow_html=True)
        with c_card:
            with st.expander(f"🚩 {event.get('title')} (展开编辑)"):
                et = st.text_input("时间", value=event.get('time'), key=f"t_{idx}")
                eti = st.text_input("标题", value=event.get('title'), key=f"ti_{idx}")
                ed = st.text_area("描述", value=event.get('desc'), key=f"d_{idx}")
                if st.button("💾 保存", key=f"sev_{idx}"):
                    timeline_data[idx] = {"time": et, "title": eti, "desc": ed}
                    save_json(TIMELINE_FILE, timeline_data); st.rerun()
        with c_del:
            if st.button("🗑️", key=f"dev_{idx}"): timeline_data.pop(idx); save_json(TIMELINE_FILE, timeline_data); st.rerun()

# ----------------- 路由 6: 角色图鉴与关系网 -----------------
elif app_mode == "👥 角色图鉴与关系网":
    tab_wiki, tab_graph = st.tabs(["📚 图鉴档案大厅", "🕸️ 树状与可视化关系网"])
    
    with tab_wiki:
        with st.expander("⚙️ 角色图鉴注入引擎 (创建/扫描)"):
            c_mw, c_aw = st.columns(2)
            with c_mw:
                new_char_name = st.text_input("手动新增：姓名")
                if st.button("➕ 手动创建角色", use_container_width=True) and new_char_name and new_char_name not in world_data:
                    world_data[new_char_name] = normalize_char({})
                    save_json(WORLD_FILE, world_data); st.rerun()
            with c_aw:
                st.markdown("<br>", unsafe_allow_html=True)
                if st.button("🤖 AI 扫描全书提取角色 (不漏一人)", type="primary", use_container_width=True):
                    with st.spinner("AI 正在拉网式排查全员档案..."):
                        try:
                            sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                            prompt = f"提取所有真实出场人物。必须是具体人名，严禁提取'主角/配角/反派'等标签！输出纯JSON字典。\n要求：physical, magic, status 的属性值必须限制在 4 到 10 个字以内。\n文本：{sample_txt}"
                            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                            new_c = json.loads(clean_json(res.choices[0].message.content))
                            for k, v in new_c.items():
                                if k not in world_data and k not in ["主角", "配角", "反派"]: 
                                    world_data[k] = normalize_char(v)
                            save_json(WORLD_FILE, world_data); st.success(f"图鉴提取成功，共新增 {len(new_c)} 人！"); st.rerun()
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
            else:
                sel_wiki_char = None
                
        if sel_wiki_char:
            with col_edit:
                char_info = world_data[sel_wiki_char]
                st.markdown(f"### 📝 {sel_wiki_char} 的绝密档案")
                t_basic, t_combat, t_bg, t_voice = st.tabs(["📝 基础定位", "⚔️ 能力与势力", "📖 背景与动机", "🔊 语音与特殊"])
                
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
                    e_voice = st.text_area("声线与标志口癖", value=char_info.get("voice", ""), height=100)
                    if st.button("🔊 试听角色声线 (AI Web-TTS)"):
                        speak_text = e_voice if e_voice else f"我是{sel_wiki_char}"
                        components.html(f"<script>var msg=new SpeechSynthesisUtterance('{speak_text}');msg.lang='zh-CN';window.speechSynthesis.speak(msg);</script>", height=0)

                if st.button(f"💾 一键保存全息档案", type="primary", use_container_width=True):
                    char_info.update({"role": e_role, "tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                    save_json(WORLD_FILE, world_data); st.success("档案已归档！")

    with tab_graph:
        # 【痛点一修复：Echarts 留白缩减与双模式关系网】
        st.info("💡 关系网双模式：上方为精简的树状思维导图模式，下方为全景交互网络球图。")
        c_auto, c_space = st.columns([1, 2])
        with c_auto:
            if st.button("🤖 AI 扫描重构关系网", type="primary", use_container_width=True):
                with st.spinner("AI 阅读原著重构网络中..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                        prompt = f"已知角色：{char_keys}。梳理关系。输出纯JSON字典，格式：{{\"relationships\": [{{\"source\": \"A\", \"label\": \"死敌\", \"target\": \"B\"}}]}}\n文本：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        rel_data = json.loads(clean_json(res.choices[0].message.content))
                        rels = rel_data.get("relationships", [])
                        world_data["_relationships"].extend(rels)
                        save_json(WORLD_FILE, world_data); st.rerun()
                    except Exception as e: st.error(f"关系网解析失败: {e}")

        # --- 模式 A：树状分类清单（类思维导图） ---
        st.markdown("### 🌲 树状人物连线图 (思维导图式)")
        grouped_rels = {}
        for idx, r in enumerate(world_data.get("_relationships", [])):
            if r["source"] not in grouped_rels: grouped_rels[r["source"]] = []
            grouped_rels[r["source"]].append((idx, r))
            
        if not grouped_rels: st.warning("暂无人物关系数据，请手动建立或让 AI 扫描。")
        for src, rels in grouped_rels.items():
            with st.expander(f"👤 【{src}】 的羁绊网络", expanded=False):
                for idx, r in rels:
                    c1, c2 = st.columns([8, 2])
                    with c1: st.markdown(f" └─ ⟷ `[{r['label']}]` ⟷ **{r['target']}**")
                    with c2:
                        if st.button("✂️ 斩断", key=f"cut_tree_{idx}"):
                            world_data["_relationships"].pop(idx); save_json(WORLD_FILE, world_data); st.rerun()

        st.markdown("---")
        # --- 模式 B：ECharts 缩紧版 ---
        st.markdown("### 🕸️ 动态拖拽交互网络")
        nodes = [{"name": k, "symbolSize": 55 if world_data[k].get("role") == "核心主角" else 35, "itemStyle": {"color": "#ff4b4b" if world_data[k].get("role") == "核心主角" else "#3366cc"}} for k in char_keys]
        links = [{"source": r["source"], "target": r["target"], "label": {"show": True, "formatter": r["label"]}} for r in world_data.get("_relationships", [])]
        
        if nodes:
            # 调整了 repulsion (排斥力) 和 edgeLength，减少空白区域
            echarts_html = f"""
            <!DOCTYPE html><html>
            <head><script src="[https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js](https://registry.npmmirror.com/echarts/5.4.3/files/dist/echarts.min.js)"></script></head>
            <body style="margin:0;padding:0;background-color:transparent;">
                <div id="main" style="width:100%;height:450px;"></div>
                <script>
                    var myChart = echarts.init(document.getElementById('main'));
                    var option = {{
                        tooltip: {{ formatter: '{{b}}' }},
                        series: [{{
                            type: 'graph', layout: 'force', roam: true, draggable: true, zoom: 1.2,
                            label: {{show: true, position: 'right', fontSize: 14}},
                            edgeSymbol: ['none', 'arrow'], edgeSymbolSize: [4, 10],
                            edgeLabel: {{fontSize: 12}},
                            force: {{repulsion: 150, edgeLength: 80, gravity: 0.1}},
                            data: {json.dumps(nodes)}, links: {json.dumps(links)}
                        }}]
                    }};
                    myChart.setOption(option);
                </script>
            </body></html>
            """
            components.html(echarts_html, height=470)
            
        st.markdown("---")
        with st.expander("🛠️ 手动建立新羁绊", expanded=False):
            c_rel1, c_rel2, c_rel3, c_btn = st.columns([2, 2, 2, 1])
            with c_rel1: r_source = st.selectbox("起始角色", char_keys, key="rs") if char_keys else None
            with c_rel2: r_type = st.text_input("羁绊 (如: 暗恋)")
            with c_rel3: r_target = st.selectbox("目标角色", char_keys, key="rt") if char_keys else None
            with c_btn:
                st.write("")
                if st.button("🔗 缔结羁绊", use_container_width=True) and r_source and r_target and r_type:
                    world_data["_relationships"].append({"source": r_source, "label": r_type, "target": r_target})
                    save_json(WORLD_FILE, world_data); st.rerun()

# ----------------- 路由 7: 逻辑体检与防吃书 -----------------
elif app_mode == "🩺 逻辑体检与防吃书":
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
                except Exception as e:
                    st.error(f"API 服务器繁忙: {e}")

    with tab_lore:
        st.info("向 AI 提问设定（例如：“主角的异能是什么？”），AI 会翻阅你现有的设定集和前文，为你提供确切证明。")
        lore_query = st.text_input("输入你要查证的设定疑问：")
        if st.button("🛡️ 发起全库检索"):
            with st.spinner("量子大脑全库检索比对中..."):
                try:
                    sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:8000]
                    prompt = f"你是防吃书系统。解答疑问，若找不到明确说明“未设定”。\n【提问】：{lore_query}\n【设定库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【前文】：{sample_txt}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.success("检索完成："); st.write(res.choices[0].message.content)
                except Exception as e: st.error(f"检索失败: {e}")

    with tab_clue:
        with st.expander("➕ 手动埋设新伏笔"):
            c_title = st.text_input("伏笔名称 (如: 神秘的玉佩)")
            c_desc = st.text_area("伏笔详情与回收计划")
            if st.button("📥 埋入土中"):
                clues_data.append({"title": c_title, "desc": c_desc, "status": "🔴 未回收"})
                save_json(CLUES_FILE, clues_data); st.rerun()
                
        st.markdown("### 📂 伏笔档案库")
        for idx, clue in enumerate(clues_data):
            c1, c2, c3, c4 = st.columns([5, 2, 1, 1])
            with c1: st.markdown(f"**{clue['title']}**<br><span style='color:gray;font-size:14px'>{clue['desc']}</span>", unsafe_allow_html=True)
            with c2: st.markdown(f"状态: **{clue['status']}**")
            with c3:
                if st.button("🔄 切状态", key=f"clue_s_{idx}"):
                    clues_data[idx]["status"] = "🟢 已回收" if clue["status"] == "🔴 未回收" else "🔴 未回收"
                    save_json(CLUES_FILE, clues_data); st.rerun()
            with c4:
                if st.button("🗑️", key=f"clue_d_{idx}"):
                    clues_data.pop(idx); save_json(CLUES_FILE, clues_data); st.rerun()

# ----------------- 路由 8: 灵感与素材库 -----------------
elif app_mode == "💡 灵感与素材库":
    st.info("在这里上传图片、视频、音频文件，或粘贴网页 URL，作为小说的设定参考与故事灵感。")
    
    with st.expander("📤 上传本地多媒体素材"):
        uploaded_files = st.file_uploader("支持图片、音频、视频及文档", accept_multiple_files=True)
        if st.button("保存选中文件", type="primary"):
            if uploaded_files:
                for f in uploaded_files:
                    path = f"materials/{cur_book}_{f.name}"
                    with open(path, "wb") as file: file.write(f.getbuffer())
                    materials_data.append({"name": f.name, "type": f.type, "path": path, "url": "", "desc": ""})
                save_json(MATERIALS_FILE, materials_data); st.success("上传成功！"); st.rerun()

    with st.expander("🔗 录入网络外链素材"):
        col_url, col_desc = st.columns(2)
        with col_url: link_url = st.text_input("网页/视频URL (例如 B站/微博 链接)")
        with col_desc: link_name = st.text_input("素材命名 (如: 赛博朋克参考视频)")
        if st.button("保存链接素材"):
            if link_url and link_name:
                materials_data.append({"name": link_name, "type": "url", "path": "", "url": link_url, "desc": ""})
                save_json(MATERIALS_FILE, materials_data); st.success("录入成功！"); st.rerun()

    st.markdown("### 🗂️ 我的素材库")
    if not materials_data: st.warning("素材库为空。")
    for idx, mat in enumerate(materials_data):
        with st.expander(f"📁 {mat['name']}"):
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
                new_desc = st.text_area("灵感批注:", value=mat.get("desc", ""), key=f"mat_desc_{idx}")
                if st.button("💾 保存批注", key=f"mat_save_{idx}"):
                    materials_data[idx]["desc"] = new_desc
                    save_json(MATERIALS_FILE, materials_data); st.toast("保存成功")
                if st.button("🗑️ 删除素材", key=f"mat_del_{idx}"):
                    if mat["path"] and os.path.exists(mat["path"]): os.remove(mat["path"])
                    materials_data.pop(idx); save_json(MATERIALS_FILE, materials_data); st.rerun()

# ----------------- 路由 9: 宗师工具箱 -----------------
elif app_mode == "🧰 宗师工具箱":
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
        st.text_area("🤖 智囊团结果", value=st.session_state.ai_reply, height=400)
