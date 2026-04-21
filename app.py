import streamlit as st
import json
import os
import random
import re
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

st.set_page_config(page_title="上帝大脑 | 第九世代防爆版", layout="wide")

# ================= 1.5 安全 JSON 清洗器 =================
def clean_json(text):
    if not text: return "{}"
    text = text.strip()
    text = re.sub(r'^```json\s*', '', text)
    text = re.sub(r'^```\s*', '', text)
    text = re.sub(r'\s*```$', '', text)
    return text.strip()

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
    app_mode = st.radio("🧭 核心控制台", ["🖋️ 连载写作台", "📖 目录与精修 (修改/分章)", "⏳ 编年史时间轴", "👥 角色图鉴与关系网", "🩺 逻辑体检与伏笔", "🧰 宗师工具箱"])

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
char_keys = [k for k in world_data.keys() if k != "_relationships"]

# ================= 4. 数据更新与回溯保护 =================
if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)
    st.session_state.ai_reply = ""

if st.session_state.rebuild_text:
    with st.spinner("🕵️‍♂️ 数据同步中(安全模式)..."):
        try:
            p_reb = f"仅更新出场角色状态。输出纯JSON字典。\n【库】：{json.dumps({k: world_data[k] for k in char_keys}, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_text}"
            r_reb = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_reb}], response_format={"type":"json_object"})
            updated = json.loads(clean_json(r_reb.choices[0].message.content))
            for k, v in updated.items():
                if k in world_data: world_data[k].update({key: v.get(key) for key in ["physical", "magic", "status", "inventory"]})
            save_json(WORLD_FILE, world_data); st.session_state.rebuild_text = ""; st.rerun()
        except Exception as e:
            st.error(f"同步失败 (网络超时或格式错误): {e}")
            st.session_state.rebuild_text = ""

# ================= 5. 左侧监控 =================
with st.sidebar:
    if app_mode in ["🖋️ 连载写作台", "👥 角色图鉴与关系网", "🩺 逻辑体检与伏笔"]:
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
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out); st.toast("锁定成功")
    with cl:
        l_out = st.text_area("🚩 本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out); st.toast("锁定成功")

    buffer_val = st.text_area(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        with st.expander("🔍 智能雷达引擎 (自动抓角色)"):
            if st.button("🚀 扫描并录入新角色", use_container_width=True):
                with st.spinner("抓取中..."):
                    try:
                        prompt = f"提取新角色，忽略已存在的人：{char_keys}。输出纯JSON字典。\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(clean_json(res.choices[0].message.content))
                        for k, v in new_chars.items():
                            if k not in world_data: world_data[k] = v
                        save_json(WORLD_FILE, world_data); st.success("已录入设定集！")
                    except Exception as e:
                        st.error(f"提取失败，请检查网络: {e}")

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
                    except Exception as e:
                        st.warning(f"由于网络波动，时间轴提炼失败，但章节已成功入库。")
                
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
                except Exception as e: st.error(f"AI服务器异常，请重试: {e}")

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
                try:
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"润色片段，去AI味：{draft}"}])
                    st.session_state.current_draft = res.choices[0].message.content; st.rerun()
                except Exception as e: st.error(f"网络异常: {e}")
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

# ----------------- 路由 2: 目录与精修 -----------------
elif app_mode == "📖 目录与精修 (修改/分章)":
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

# ----------------- 路由 3: 编年史时间轴 (修复痛点四：一键全本梳理) -----------------
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
        # 新增痛点修复：给老书直接补全时间轴的按钮
        st.info("💡 老书没有时间轴？让 AI 自动梳理。")
        if st.button("🤖 AI 自动阅读并生成编年史", type="primary", use_container_width=True):
            with st.spinner("AI 正在跨越时间长河梳理历史..."):
                try:
                    # 截取适量字符防止超时
                    sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                    prompt = f"提取原著中的大事件。必须输出纯JSON字典，格式：{{\"events\": [{{\"time\":\"时间\",\"title\":\"事件标题\",\"desc\":\"详细描述\"}}]}}\n文本：{sample_txt}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                    parsed_data = json.loads(clean_json(res.choices[0].message.content))
                    ev_list = parsed_data.get("events", [])
                    if ev_list:
                        timeline_data.extend(ev_list)
                        save_json(TIMELINE_FILE, timeline_data)
                        st.success("编年史全自动梳理入库成功！")
                        st.rerun()
                    else: st.warning("未提取到明显大事件。")
                except Exception as e:
                    st.error(f"提取失败，API超时或格式错误: {e}")

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

# ----------------- 路由 4: 角色图鉴与关系网 (修复痛点二：一键全自动图鉴) -----------------
elif app_mode == "👥 角色图鉴与关系网":
    tab_wiki, tab_graph = st.tabs(["📚 图鉴档案", "🕸️ 可视化关系网"])
    
    with tab_wiki:
        c_mw, c_aw = st.columns(2)
        with c_mw:
            with st.expander("➕ 手动创建角色"):
                new_char_name = st.text_input("姓名")
                if st.button("录入图鉴") and new_char_name and new_char_name not in world_data:
                    world_data[new_char_name] = {"physical":"健康", "magic":"充盈", "status":"未登场", "inventory":[], "tags":[], "appearance":"", "voice":"", "faction":"", "ability":"", "weakness":"", "background":"", "motivation":""}
                    save_json(WORLD_FILE, world_data); st.rerun()
        with c_aw:
            # 独立在图鉴页的 AI 一键自动获取按钮
            if st.button("🤖 AI 自动扫描全书提取角色", type="primary", use_container_width=True):
                with st.spinner("AI 正在扫描原著建立全员档案..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                        prompt = f"提取核心角色。输出JSON字典，键为姓名，值为字典(含physical,magic,status,inventory,tags,appearance,voice,faction,ability,weakness,background,motivation)。\n文本：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_c = json.loads(clean_json(res.choices[0].message.content))
                        for k, v in new_c.items():
                            if k not in world_data: world_data[k] = v
                        save_json(WORLD_FILE, world_data)
                        st.success("角色图鉴批量入库成功！")
                        st.rerun()
                    except Exception as e:
                        st.error(f"提取失败，API超时或格式异常: {e}")

        col_list, col_edit = st.columns([1, 3])
        with col_list:
            sel_wiki_char = st.radio("选择档案", char_keys) if char_keys else None
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
                if st.button(f"💾 保存【{sel_wiki_char}】", type="primary", use_container_width=True):
                    char_info.update({"tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                    save_json(WORLD_FILE, world_data); st.success("已同步！")

    with tab_graph:
        st.info("可视化关系拓扑。可让AI自动梳理，或鼠标拖拽查看羁绊。")
        c_auto, c_space = st.columns([1, 2])
        with c_auto:
            if st.button("🤖 AI 扫描重构关系网", type="primary", use_container_width=True):
                with st.spinner("AI 阅读原著重构网络中..."):
                    try:
                        sample_txt = "\n".join([ch["content"] for ch in chapters_data[:10]])[:6000]
                        prompt = f"已知角色：{char_keys}。梳理他们的关系。必须输出纯JSON字典，格式：{{\"relationships\": [{{\"source\": \"人物A\", \"label\": \"死敌\", \"target\": \"人物B\"}}]}}\n文本：{sample_txt}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        rel_data = json.loads(clean_json(res.choices[0].message.content))
                        rels = rel_data.get("relationships", [])
                        world_data["_relationships"].extend(rels)
                        save_json(WORLD_FILE, world_data); st.rerun()
                    except Exception as e:
                        st.error(f"关系网解析失败 (网络超时或格式错误): {e}")

        # 【核心黑科技】：ECharts 可视化交互图表
        nodes = [{"name": k, "symbolSize": 50 if k == sel_wiki_char else 35, "itemStyle": {"color": "#ff4b4b" if k == sel_wiki_char else "#3366cc"}} for k in char_keys]
        links = [{"source": r["source"], "target": r["target"], "label": {"show": True, "formatter": r["label"]}} for r in world_data.get("_relationships", [])]
        
        if nodes:
            echarts_html = f"""
            <!DOCTYPE html>
            <html>
            <head><script src="[https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js](https://cdn.jsdelivr.net/npm/echarts@5.4.3/dist/echarts.min.js)"></script></head>
            <body style="margin:0;padding:0;background-color:transparent;">
                <div id="main" style="width:100%;height:500px;"></div>
                <script>
                    var myChart = echarts.init(document.getElementById('main'));
                    var option = {{
                        tooltip: {{ formatter: '{{b}}' }},
                        series: [{{
                            type: 'graph', layout: 'force', roam: true, draggable: true,
                            label: {{show: true, position: 'right', fontSize: 14}},
                            edgeSymbol: ['none', 'arrow'], edgeSymbolSize: [4, 10],
                            edgeLabel: {{fontSize: 12}},
                            force: {{repulsion: 400, edgeLength: 150}},
                            data: {json.dumps(nodes)}, links: {json.dumps(links)}
                        }}]
                    }};
                    myChart.setOption(option);
                </script>
            </body>
            </html>
            """
            components.html(echarts_html, height=520)
        else:
            st.warning("暂无角色数据，无法生成网络图。")

        st.markdown("### 🕸️ 手动连线与删改")
        c_rel1, c_rel2, c_rel3, c_btn = st.columns([2, 2, 2, 1])
        with c_rel1: r_source = st.selectbox("核心角色", char_keys, key="rs") if char_keys else None
        with c_rel2: r_type = st.text_input("关系 (如: 暗恋)")
        with c_rel3: r_target = st.selectbox("目标角色", char_keys, key="rt") if char_keys else None
        with c_btn:
            st.write("")
            if st.button("🔗 连接") and r_source and r_target and r_type:
                world_data["_relationships"].append({"source": r_source, "label": r_type, "target": r_target})
                save_json(WORLD_FILE, world_data); st.rerun()

        for idx, rel in enumerate(world_data.get("_relationships", [])):
            cc1, cc3 = st.columns([9, 1])
            with cc1: st.markdown(f"**{rel.get('source')}** ⟷ `[{rel.get('label')}]` ⟷ **{rel.get('target')}**")
            with cc3:
                if st.button("✂️ 斩断", key=f"cut_{idx}"):
                    world_data["_relationships"].pop(idx); save_json(WORLD_FILE, world_data); st.rerun()

# ----------------- 路由 5: 逻辑体检与伏笔 -----------------
elif app_mode == "🩺 逻辑体检与伏笔":
    tab_check, tab_clue = st.tabs(["🩺 章节逻辑体检", "📌 伏笔追踪器"])
    
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
                    st.error(f"API 服务器繁忙，请稍后重试: {e}")

    with tab_clue:
        st.info("埋坑不填，天理难容。记录所有草蛇灰线。")
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
                if st.button("🗑️ 删除", key=f"clue_d_{idx}"):
                    clues_data.pop(idx); save_json(CLUES_FILE, clues_data); st.rerun()

# ----------------- 路由 6: 宗师工具箱 -----------------
elif app_mode == "🧰 宗师工具箱":
    sample_context = "\n\n".join([ch["content"] for ch in chapters_data[:3]])[:6000] if chapters_data else ""
    t1, t3 = st.tabs(["🌍 世界观引擎", "🗺️ 大纲引擎"])
    
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
                st.session_state.ai_reply = ""
                st.toast("已追加至全书大纲！"); st.rerun()
                
    with t3:
        if st.button("🗺️ 推演后续大纲"):
            try:
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于前文续写大纲：\n{sample_context}"}])
                st.session_state.ai_reply = res.choices[0].message.content
            except Exception as e: st.error(f"网络异常: {e}")
        if st.session_state.ai_reply and "大纲" in st.session_state.ai_reply:
            if st.button("📥 追加至全书大纲"):
                open(BOOK_OUTLINE_FILE, "a", encoding="utf-8").write("\n\n" + st.session_state.ai_reply)
                st.session_state.ai_reply = ""
                st.toast("已追加！"); st.rerun()

    if st.session_state.ai_reply:
        st.markdown("---")
        st.text_area("🤖 智囊团结果", value=st.session_state.ai_reply, height=400)
