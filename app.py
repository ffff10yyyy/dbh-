import streamlit as st
import json
import os
import random
import re
from openai import OpenAI

# ================= 1. 引擎初始化 =================
with st.sidebar:
    st.header("🔑 引擎激活")
    user_api_key = st.text_input("请输入 DeepSeek API Key", type="password", value="sk-0275d85e2cd348d09b81fb01321b0147")
    if not user_api_key:
        st.warning("👈 请输入 API Key 启动引擎")
        st.stop()
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")

st.set_page_config(page_title="上帝大脑 | 终极网络版", layout="wide")

# ================= 2. 藏书馆与全局管理 =================
LIBRARY_FILE = "library.json"
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
def load_text(file):
    return open(file, "r", encoding="utf-8").read() if os.path.exists(file) else ""

if not os.path.exists(LIBRARY_FILE): save_json(LIBRARY_FILE, ["我的第一部小说"])
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

if "active_book" not in st.session_state:
    st.session_state.active_book = books[0] if books else None

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
            st.caption("自动解析章节并创建一本独立新书")
            uploaded_file = st.file_uploader("选择 TXT", type=["txt"], label_visibility="collapsed")
            
            # 【优化 4】：新增手动分章与自定义分章
            split_method = st.radio("分章策略", ["智能正则(默认)", "自定义标志词", "不分章(全文导入)"])
            custom_kw = ""
            if split_method == "自定义标志词":
                custom_kw = st.text_input("输入章节前缀 (如 '第' 或 'Chapter')")

            if uploaded_file and st.button("🚀 解析并建书", type="primary", use_container_width=True):
                with st.spinner("处理中..."):
                    new_name = uploaded_file.name.replace(".txt", "")
                    base_name = new_name
                    counter = 1
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
                    
                    books.append(new_name)
                    save_json(LIBRARY_FILE, books)
                    save_json(f"{new_name}_chapters.json", new_chapters)
                    save_json(f"{new_name}_world.json", {"_relationships": []})
                    save_json(f"{new_name}_timeline.json", [])
                    save_json(f"{new_name}_clues.json", [])
                    
                    st.session_state.active_book = new_name
                    st.success(f"导入成功！生成新书《{new_name}》")
                    st.rerun()

    with st.expander("⚙️ 当前作品设置"):
        novel_style = st.selectbox("全书风格锚点", ["番茄爽文/快节奏升级", "起点升级流/宏大叙事", "晋江细腻向/情感共鸣", "诡秘悬疑风/不可名状", "二次元轻小说/吐槽搞笑"])
        # 【优化 1】：修复幽灵删除 Bug
        if st.button("🧨 销毁当前作品", use_container_width=True) and st.checkbox("确认永久删除"):
            if selected_book in books:
                books.remove(selected_book)
                save_json(LIBRARY_FILE, books)
                st.session_state.active_book = books[0] if len(books) > 0 else None
                st.rerun()

    st.markdown("---")
    # 【优化 3】：独立逻辑体检与伏笔大厅
    app_mode = st.radio("🧭 核心控制台", ["🖋️ 连载写作台", "📖 目录与精修", "⏳ 编年史时间轴", "👥 角色设定与关系网", "🩺 逻辑体检与伏笔", "🧰 宗师工具箱"])

# ================= 3. 数据加载与隔离 =================
if not st.session_state.active_book: st.stop()
cur_book = st.session_state.active_book

WORLD_FILE = f"{cur_book}_world.json"
CHAPTERS_FILE = f"{cur_book}_chapters.json"
BUFFER_FILE = f"{cur_book}_buffer.txt"
TIMELINE_FILE = f"{cur_book}_timeline.json"
CLUES_FILE = f"{cur_book}_clues.json"
BOOK_OUTLINE_FILE = f"{cur_book}_global_outline.txt"
CHAPTER_OUTLINE_FILE = f"{cur_book}_local_outline.txt"

for f in [WORLD_FILE, CHAPTERS_FILE, TIMELINE_FILE, CLUES_FILE]:
    if not os.path.exists(f): save_json(f, {} if f == WORLD_FILE else [])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)
with open(TIMELINE_FILE, "r", encoding="utf-8") as f: timeline_data = json.load(f)
with open(CLUES_FILE, "r", encoding="utf-8") as f: clues_data = json.load(f)

if "_relationships" not in world_data: world_data["_relationships"] = []

# 过滤出真实角色数据
char_keys = [k for k in world_data.keys() if k != "_relationships"]

# ================= 4. 状态记忆 =================
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "ai_reply" not in st.session_state: st.session_state.ai_reply = ""
if "rebuild_text" not in st.session_state: st.session_state.rebuild_text = ""

if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)

if st.session_state.rebuild_text:
    with st.spinner("🕵️‍♂️ 数据同步中(安全模式)..."):
        p_reb = f"仅更新出场角色状态。输出JSON。\n【库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_text}"
        r_reb = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_reb}], response_format={"type":"json_object"})
        updated = json.loads(r_reb.choices[0].message.content)
        for k, v in updated.items():
            if k in world_data: world_data[k].update({key: v.get(key) for key in ["physical", "magic", "status", "inventory"]})
        save_json(WORLD_FILE, world_data); st.session_state.rebuild_text = ""; st.rerun()

# ================= 5. 左侧监控 =================
with st.sidebar:
    if app_mode in ["🖋️ 连载写作台", "👥 角色设定与关系网", "🩺 逻辑体检与伏笔"]:
        st.markdown("---")
        st.subheader("📊 实时监控")
        if char_keys:
            selected_char = st.selectbox("监控角色", char_keys, label_visibility="collapsed")
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
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out)
    with cl:
        l_out = st.text_area("🚩 本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out)

    buffer_val = st.text_area(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        with st.expander("🔍 智能雷达引擎 (抓角色 / 提事件)"):
            c_radar, c_event = st.columns(2)
            with c_radar:
                if st.button("🚀 扫描并录入新角色", use_container_width=True):
                    with st.spinner("抓取中..."):
                        prompt = f"提取新角色，忽略：{char_keys}。输出纯JSON。\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(res.choices[0].message.content)
                        for k, v in new_chars.items():
                            if k not in world_data: world_data[k] = v
                        save_json(WORLD_FILE, world_data); st.success("已录入设定集！")
            with c_event:
                if st.button("⚡ 提炼大事件入时间轴", use_container_width=True):
                    with st.spinner("提炼中..."):
                        prompt = f"提炼时间点和事件。输出JSON：{{'time':'时间','title':'标题','desc':'描述'}}。\n文段：{st.session_state.chapter_buffer[:2000]}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        timeline_data.append(json.loads(res.choices[0].message.content)); save_json(TIMELINE_FILE, timeline_data); st.success("已录入编年史")

        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章存入目录", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data); st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None; st.rerun()

    st.markdown("---")
    cd1, cd2, ci = st.columns([1, 1, 4])
    with cd1:
        if st.button("🎲 突发转折"):
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于目标【{l_out}】和前文，生成突发事件(20字内)。"}])
            st.session_state.current_prompt = f"【突降】：{res.choices[0].message.content}。往下写。"; st.session_state.current_draft = ""; st.rerun()
    with cd2:
        if st.button("🆘 卡文破局"):
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"卡文。前文摘要：{st.session_state.chapter_buffer[-500:]}。生成5种破局方案。"}])
            st.session_state.current_draft = f"【卡文破局】\n{res.choices[0].message.content}"; st.rerun()
    with ci:
        new_in = st.chat_input("下达指令...")
        if new_in: st.session_state.current_prompt = new_in; st.session_state.current_draft = ""; st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner("构思中..."):
                prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n设定：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n指令：{st.session_state.current_prompt}\n要求：贴合【{novel_style}】，400字。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = res.choices[0].message.content; st.rerun()

    if st.session_state.current_draft:
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("➕ 接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ 去 AI 味精修", type="primary"):
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色片段，去AI味：{draft}"}])
                st.session_state.current_draft = res.choices[0].message.content; st.rerun()
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

# ----------------- 路由 2: 目录与精修 -----------------
elif app_mode == "📖 目录与精修":
    if chapters_data:
        export_text = f"《{cur_book}》\n\n"
        for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
        st.download_button("📥 一键导出全本小说 TXT", data=export_text, file_name=f"{cur_book}.txt")
        for idx, ch in enumerate(chapters_data):
            c_view, c_act1, c_act2 = st.columns([6, 1, 1])
            with c_view:
                with st.expander(f"第 {idx+1} 章：{ch['title']}"): st.write(ch['content'])
            with c_act1:
                if st.button("📂 回溯", key=f"load_{idx}"):
                    st.session_state.chapter_buffer = ch['content']
                    open(BUFFER_FILE, "w", encoding="utf-8").write(ch['content'])
                    st.session_state.rebuild_text = ch['content']
            with c_act2:
                if st.button("🗑️ 删除", key=f"del_{idx}"): chapters_data.pop(idx); save_json(CHAPTERS_FILE, chapters_data); st.rerun()

# ----------------- 路由 3: 编年史时间轴 -----------------
elif app_mode == "⏳ 编年史时间轴":
    with st.expander("➕ 手动刻录大事件"):
        with st.form("add_event"):
            e_time = st.text_input("时间节点")
            e_title = st.text_input("事件名称")
            e_desc = st.text_area("详细描述")
            if st.form_submit_button("载入史册"):
                timeline_data.append({"time": e_time, "title": e_title, "desc": e_desc})
                save_json(TIMELINE_FILE, timeline_data); st.rerun()

    for idx, event in enumerate(timeline_data):
        c_line, c_card, c_del = st.columns([1, 10, 1])
        with c_line: st.markdown(f"**{event.get('time')}**<br><div style='width:2px;height:50px;background:#ff4b4b;margin-left:10px;'></div>", unsafe_allow_html=True)
        with c_card:
            st.markdown(f"### 🚩 {event.get('title')}")
            st.write(event.get('desc'))
        with c_del:
            if st.button("🗑️", key=f"dev_{idx}"): timeline_data.pop(idx); save_json(TIMELINE_FILE, timeline_data); st.rerun()

# ----------------- 路由 4: 角色设定与关系网 (优化 6) -----------------
elif app_mode == "👥 角色设定与关系网":
    tab_wiki, tab_graph = st.tabs(["📚 图鉴档案", "🕸️ 关系网拓扑"])
    
    with tab_wiki:
        col_list, col_edit = st.columns([1, 3])
        with col_list:
            sel_wiki_char = st.radio("选择档案", char_keys) if char_keys else None
            with st.expander("➕ 创建新角色"):
                new_char_name = st.text_input("姓名")
                if st.button("录入图鉴") and new_char_name and new_char_name not in world_data:
                    world_data[new_char_name] = {"physical":"健康", "magic":"充盈", "status":"未登场", "inventory":[], "tags":[], "appearance":"", "voice":"", "faction":"", "ability":"", "weakness":"", "background":"", "motivation":""}
                    save_json(WORLD_FILE, world_data); st.rerun()
        if sel_wiki_char:
            with col_edit:
                char_info = world_data[sel_wiki_char]
                e1, e2 = st.columns(2)
                with e1:
                    e_tags = st.text_input("性格标签", value=",".join(char_info.get("tags", [])))
                    e_app = st.text_input("外貌体型", value=char_info.get("appearance", ""))
                    e_voice = st.text_input("声线口癖", value=char_info.get("voice", ""))
                    e_weak = st.text_input("致命弱点", value=char_info.get("weakness", ""))
                with e2:
                    e_ability = st.text_input("异能武功", value=char_info.get("ability", ""))
                    e_faction = st.text_input("所属势力", value=char_info.get("faction", ""))
                    e_bg = st.text_area("身世背景", value=char_info.get("background", ""), height=68)
                    e_mot = st.text_area("核心动机", value=char_info.get("motivation", ""), height=68)
                if st.button(f"💾 保存【{sel_wiki_char}】", type="primary"):
                    char_info.update({"tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                    save_json(WORLD_FILE, world_data); st.success("已同步！")

    with tab_graph:
        st.info("构建角色之间的羁绊与仇恨。AI 会在创作时参考此关系网。")
        c_rel1, c_rel2, c_rel3, c_btn = st.columns([2, 2, 2, 1])
        with c_rel1: r_source = st.selectbox("核心角色", char_keys, key="rs") if char_keys else None
        with c_rel2: r_type = st.text_input("是什么关系 (如: 死敌/恩人/暗恋)")
        with c_rel3: r_target = st.selectbox("目标角色", char_keys, key="rt") if char_keys else None
        with c_btn:
            st.write("")
            if st.button("🔗 建立羁绊") and r_source and r_target and r_type:
                world_data["_relationships"].append({"source": r_source, "label": r_type, "target": r_target})
                save_json(WORLD_FILE, world_data); st.rerun()
                
        st.markdown("### 🕸️ 人际网络图")
        for idx, rel in enumerate(world_data["_relationships"]):
            cc1, cc2, cc3 = st.columns([8, 1, 1])
            with cc1: st.markdown(f"**{rel['source']}** ⟷ `[{rel['label']}]` ⟷ **{rel['target']}**")
            with cc3:
                if st.button("✂️", key=f"cut_{idx}"):
                    world_data["_relationships"].pop(idx); save_json(WORLD_FILE, world_data); st.rerun()

# ----------------- 路由 5: 逻辑体检与伏笔 (优化 3 & 5) -----------------
elif app_mode == "🩺 逻辑体检与伏笔":
    tab_check, tab_clue = st.tabs(["🩺 章节逻辑体检", "📌 伏笔追踪器"])
    
    with tab_check:
        st.info("让大模型扫描你最近的章节，找出前后矛盾、人设崩塌和节奏问题。")
        check_range = st.slider("检查最近多少章？", 1, max(1, len(chapters_data)), min(5, len(chapters_data)))
        if st.button("🚀 开始全面体检", type="primary"):
            with st.spinner("扫描漏洞中..."):
                target_chs = chapters_data[-check_range:] if chapters_data else []
                text = "\n".join([f"{ch['title']}：{ch['content'][:1500]}..." for ch in target_chs])
                prompt = f"分析以下章节逻辑漏洞、人设OOC、节奏问题。给出修改方案。\n【章节】：\n{text}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.write(res.choices[0].message.content)

    with tab_clue:
        st.info("埋坑不填，天理难容。在这里记录所有的草蛇灰线。")
        with st.expander("➕ 手动埋设新伏笔"):
            c_title = st.text_input("伏笔名称 (如: 神秘的玉佩)")
            c_desc = st.text_area("伏笔详情与原定回收计划")
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

# ----------------- 路由 6: 宗师工具箱 (优化 2 一键导入) -----------------
elif app_mode == "🧰 宗师工具箱":
    sample_context = "\n\n".join([ch["content"] for ch in chapters_data[:3]])[:8000] if chapters_data else ""
    t1, t2, t3 = st.tabs(["🌍 世界观引擎", "👤 角色引擎", "🗺️ 大纲引擎"])
    
    with t1:
        if st.button("🔍 从导入小说提炼世界观" if sample_context else "🪄 生成新世界观", type="primary" if sample_context else "secondary"):
            with st.spinner("构架中..."):
                prompt = f"阅读原文片段，【提炼】世界观设定。\n原文：{sample_context}" if sample_context else f"生成【{novel_style}】长篇世界观。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_reply = res.choices[0].message.content
        if st.session_state.ai_reply and "设定" in st.session_state.ai_reply:
            if st.button("📥 一键覆盖至全书大纲"):
                open(BOOK_OUTLINE_FILE, "a", encoding="utf-8").write("\n\n" + st.session_state.ai_reply); st.toast("已追加至全书大纲！")

    with t2:
        if st.button("🔍 提取全员档案并入库 (JSON格式)", type="primary"):
            with st.spinner("梳理中..."):
                prompt = f"提取核心角色。严格输出JSON字典，键为姓名，值为属性字典(含physical,magic,tags等)。\n原文：{sample_context}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                st.session_state.ai_reply = res.choices[0].message.content
        if st.session_state.ai_reply and "{" in st.session_state.ai_reply:
            if st.button("📥 一键将以上角色汇入图鉴"):
                new_c = json.loads(st.session_state.ai_reply)
                for k, v in new_c.items():
                    if k not in world_data: world_data[k] = v
                save_json(WORLD_FILE, world_data); st.toast("全部入库成功！")
                
    with t3:
        if st.button("🗺️ 推演后续大纲"):
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于前文续写大纲：\n{sample_context}"}])
            st.session_state.ai_reply = res.choices[0].message.content
        if st.session_state.ai_reply and "大纲" in st.session_state.ai_reply:
            if st.button("📥 追加至全书大纲"):
                open(BOOK_OUTLINE_FILE, "a", encoding="utf-8").write("\n\n" + st.session_state.ai_reply); st.toast("已追加！")

    if st.session_state.ai_reply:
        st.markdown("---")
        st.text_area("🤖 智囊团结果", value=st.session_state.ai_reply, height=400)
