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

st.set_page_config(page_title="上帝大脑 | 双轨编年史版", layout="wide")

# ================= 2. 藏书馆系统 =================
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
            if uploaded_file and st.button("🚀 解析并建书", type="primary", use_container_width=True):
                with st.spinner("切割章节中..."):
                    new_import_name = uploaded_file.name.replace(".txt", "")
                    base_name = new_import_name
                    counter = 1
                    while new_import_name in books:
                        new_import_name = f"{base_name}_导入版{counter}"; counter += 1
                    
                    content = uploaded_file.read().decode("utf-8", errors="ignore")
                    chunks = re.split(r'\n(第[零一二三四五六七八九十百千万0-9]+[章节回幕].*?)\n', "\n" + content)
                    new_chapters = []
                    if chunks[0].strip(): new_chapters.append({"title": "序言/引子", "content": chunks[0].strip()})
                    for i in range(1, len(chunks), 2):
                        new_chapters.append({"title": chunks[i].strip(), "content": chunks[i+1].strip() if i+1 < len(chunks) else ""})
                    
                    books.append(new_import_name)
                    save_json(LIBRARY_FILE, books)
                    save_json(f"{new_import_name}_chapters.json", new_chapters)
                    save_json(f"{new_import_name}_world.json", {})
                    save_json(f"{new_import_name}_timeline.json", []) # 新增时间轴文件
                    
                    st.session_state.active_book = new_import_name
                    st.success(f"导入成功！已生成新书《{new_import_name}》")
                    st.rerun()

    with st.expander("⚙️ 当前作品设置"):
        novel_style = st.selectbox("全书风格锚点", ["番茄爽文/快节奏升级", "起点升级流/宏大叙事", "晋江细腻向/情感共鸣", "诡秘悬疑风/不可名状", "二次元轻小说/吐槽搞笑"])
        if st.button("🧨 销毁当前作品", use_container_width=True) and st.checkbox("确认永久删除"):
            books.remove(selected_book); save_json(LIBRARY_FILE, books)
            st.session_state.active_book = books[0] if books else None; st.rerun()

    st.markdown("---")
    # 【核心升级 1】：导航栏重构，分离“目录”与“时间线”
    app_mode = st.radio("🧭 核心控制台", ["🖋️ 连载写作台", "📖 目录与精修", "⏳ 编年史时间轴", "👥 角色设定集", "🧰 宗师工具箱"])

# ================= 3. 数据加载与隔离 =================
if not st.session_state.active_book: st.stop()
cur_book = st.session_state.active_book

WORLD_FILE = f"{cur_book}_world.json"
CHAPTERS_FILE = f"{cur_book}_chapters.json"
BUFFER_FILE = f"{cur_book}_buffer.txt"
TIMELINE_FILE = f"{cur_book}_timeline.json" # 新增
BOOK_OUTLINE_FILE = f"{cur_book}_global_outline.txt"
CHAPTER_OUTLINE_FILE = f"{cur_book}_local_outline.txt"

if not os.path.exists(WORLD_FILE): save_json(WORLD_FILE, {})
if not os.path.exists(CHAPTERS_FILE): save_json(CHAPTERS_FILE, [])
if not os.path.exists(TIMELINE_FILE): save_json(TIMELINE_FILE, [])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)
with open(TIMELINE_FILE, "r", encoding="utf-8") as f: timeline_data = json.load(f)

for char, data in world_data.items():
    if "hp" in data: data["physical"] = "健康"; del data["hp"]
    if "mp" in data: data["magic"] = "充盈"; del data["mp"]
    for key in ["physical", "magic", "status", "appearance", "voice", "faction", "ability", "weakness", "background", "motivation"]:
        data.setdefault(key, "正常" if key == "status" else "")
    data.setdefault("inventory", [])
    data.setdefault("tags", [])
save_json(WORLD_FILE, world_data)

# ================= 4. 状态记忆 =================
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "rebuild_world_text" not in st.session_state: st.session_state.rebuild_world_text = ""

if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)

# ================= 5. 左侧监控 =================
with st.sidebar:
    if app_mode in ["🖋️ 连载写作台", "👥 角色设定集"]:
        st.markdown("---")
        st.subheader("📊 实时监控")
        char_list = list(world_data.keys())
        if char_list:
            selected_char = st.selectbox("监控角色", char_list, label_visibility="collapsed")
            info = world_data[selected_char]
            c_p, c_m = st.columns(2)
            with c_p: st.success(f"💪 {info.get('physical', '健康')}")
            with c_m: st.info(f"✨ {info.get('magic', '充盈')}")
            st.error(f"🏷️ 处境: {info.get('status', '正常')}")

# ================= 6. 右侧：动态路由 =================
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
        with st.expander("🔍 雷达与大事件记录"):
            c_radar, c_event = st.columns(2)
            with c_radar:
                if st.button("🚀 扫描本章新角色", use_container_width=True):
                    with st.spinner("抓取中..."):
                        known = list(world_data.keys())
                        prompt = f"提取新角色，忽略：{known}。输出纯JSON，格式：{{'姓名':{{'physical':'健康','magic':'充盈','status':'现状','inventory':[],'tags':[],'appearance':'','voice':'','faction':'','ability':'','weakness':'','background':'','motivation':''}}}}。\n文段：{st.session_state.chapter_buffer}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        new_chars = json.loads(res.choices[0].message.content)
                        for k, v in new_chars.items():
                            if k not in world_data: world_data[k] = v
                        save_json(WORLD_FILE, world_data); st.success("已录入设定集！")
            with c_event:
                if st.button("⚡ 提炼本章为大事件存入时间轴", use_container_width=True):
                    with st.spinner("提炼中..."):
                        prompt = f"根据以下章节，提炼一个极其简短的时间点和事件名（如：'新历102年，李四觉醒'）。输出JSON：{{'time':'时间','title':'标题','desc':'一句话描述'}}。\n文段：{st.session_state.chapter_buffer[:2000]}"
                        res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}], response_format={"type":"json_object"})
                        ev = json.loads(res.choices[0].message.content)
                        timeline_data.append(ev); save_json(TIMELINE_FILE, timeline_data)
                        st.success(f"已录入编年史：{ev.get('title')}")

        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章存入目录", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None
                st.success("已结章入库！"); st.rerun()

    st.markdown("---")
    cd1, cd2, ci = st.columns([1, 1, 4])
    with cd1:
        if st.button("🎲 突发转折"):
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于目标【{l_out}】和前文，生成突发事件(20字内)。"}])
            st.session_state.current_prompt = f"【突降】：{res.choices[0].message.content}。往下写。"; st.session_state.current_draft = ""; st.rerun()
    with cd2:
        if st.button("🆘 卡文破局"):
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"卡文。前文：{st.session_state.chapter_buffer[-500:]}。生成5种破局方案。"}])
            st.session_state.current_draft = f"【卡文破局】\n{res.choices[0].message.content}"; st.rerun()
    with ci:
        new_in = st.chat_input("下达指令...")
        if new_in:
            st.session_state.current_prompt = new_in; st.session_state.current_draft = ""; st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner("构思中..."):
                prompt = f"前文：{st.session_state.chapter_buffer[-1000:]}\n设定：{json.dumps(world_data, ensure_ascii=False)}\n指令：{st.session_state.current_prompt}\n要求：贴合【{novel_style}】，加五感，禁套话，400字。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = res.choices[0].message.content; st.rerun()

    if st.session_state.current_draft:
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3 = st.columns([2, 2, 1])
        with b1:
            if st.button("➕ 接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                p_up = f"更新出场角色状态。严禁覆盖静态设定！输出JSON。\n【库】：{json.dumps(world_data, ensure_ascii=False)}\n【文】：{draft}"
                r_up = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_up}], response_format={"type":"json_object"})
                save_json(WORLD_FILE, json.loads(r_up.choices[0].message.content))
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ 去 AI 味精修", type="primary"):
                polish = f"润色片段，去AI味，加细节：{draft}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":polish}])
                st.session_state.current_draft = res.choices[0].message.content; st.rerun()
        with b3:
            if st.button("🗑️ 废弃"): st.session_state.current_draft = ""; st.rerun()

# ----------------- 路由 2: 目录与精修 -----------------
elif app_mode == "📖 目录与精修":
    st.info("这里是你的实体书目录，你可以在此回顾、回溯和管理章节。")
    if chapters_data:
        export_text = f"《{cur_book}》\n\n"
        for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
        st.download_button("📥 一键导出全本小说 TXT", data=export_text, file_name=f"{cur_book}.txt")
        st.markdown("---")
        
        for idx, ch in enumerate(chapters_data):
            c_view, c_act1, c_act2 = st.columns([6, 1, 1])
            with c_view:
                with st.expander(f"第 {idx+1} 章：{ch['title']}"): st.write(ch['content'])
            with c_act1:
                if st.button("📂 回溯", key=f"load_ch_{idx}", help="加载至工作台修改"):
                    st.session_state.chapter_buffer = ch['content']
                    open(BUFFER_FILE, "w", encoding="utf-8").write(ch['content'])
                    st.success("已加载至暂存箱，请切回【连载写作台】"); st.rerun()
            with c_act2:
                if st.button("🗑️ 删除", key=f"del_ch_{idx}"):
                    chapters_data.pop(idx); save_json(CHAPTERS_FILE, chapters_data); st.rerun()
    else:
        st.warning("暂无章节。")

# ----------------- 路由 3: 编年史时间轴 -----------------
elif app_mode == "⏳ 编年史时间轴":
    st.info("这里记录了整个世界的重大历史事件，你可以手动添加或在写作台让 AI 自动提炼。独立于章节目录之外。")
    
    with st.expander("➕ 手动刻录大事件"):
        with st.form("add_event"):
            e_time = st.text_input("时间节点 (如: 神历100年 / 灾变后第3天)")
            e_title = st.text_input("大事件名称 (如: 诸神黄昏)")
            e_desc = st.text_area("详细描述")
            if st.form_submit_button("载入史册"):
                timeline_data.append({"time": e_time, "title": e_title, "desc": e_desc})
                save_json(TIMELINE_FILE, timeline_data); st.success("记录成功！"); st.rerun()

    st.markdown("---")
    if not timeline_data: st.write("尚无大事件记录。")
    
    for idx, event in enumerate(timeline_data):
        c_line, c_card, c_del = st.columns([1, 10, 1])
        with c_line:
            st.markdown(f"**{event.get('time', '未知时间')}**<br><div style='width:2px;height:50px;background:#ff4b4b;margin-left:10px;'></div>", unsafe_allow_html=True)
        with c_card:
            st.markdown(f"### 🚩 {event.get('title')}")
            st.write(event.get('desc'))
        with c_del:
            if st.button("🗑️", key=f"del_ev_{idx}"):
                timeline_data.pop(idx); save_json(TIMELINE_FILE, timeline_data); st.rerun()

# ----------------- 路由 4: 角色设定集 -----------------
elif app_mode == "👥 角色设定集":
    col_list, col_edit = st.columns([1, 3])
    with col_list:
        wiki_chars = list(world_data.keys())
        sel_wiki_char = st.radio("选择档案", wiki_chars) if wiki_chars else None
        with st.expander("➕ 手动创建新角色"):
            new_char_name = st.text_input("姓名")
            if st.button("录入图鉴") and new_char_name and new_char_name not in world_data:
                world_data[new_char_name] = {"physical":"健康", "magic":"充盈", "status":"未登场", "inventory":[], "tags":[], "appearance":"", "voice":"", "faction":"", "ability":"", "weakness":"", "background":"", "motivation":""}
                save_json(WORLD_FILE, world_data); st.rerun()
    if sel_wiki_char:
        with col_edit:
            char_info = world_data[sel_wiki_char]
            e1, e2 = st.columns(2)
            with e1:
                e_tags = st.text_input("性格标签 (逗号分隔)", value=",".join(char_info.get("tags", [])))
                e_app = st.text_input("外貌体型", value=char_info.get("appearance", ""))
                e_voice = st.text_input("声线口癖", value=char_info.get("voice", ""))
                e_weak = st.text_input("致命弱点", value=char_info.get("weakness", ""))
            with e2:
                e_ability = st.text_input("异能武功", value=char_info.get("ability", ""))
                e_faction = st.text_input("所属势力", value=char_info.get("faction", ""))
                e_bg = st.text_area("身世背景", value=char_info.get("background", ""), height=68)
                e_mot = st.text_area("核心动机", value=char_info.get("motivation", ""), height=68)
            if st.button(f"💾 保存【{sel_wiki_char}】的设定", type="primary", use_container_width=True):
                char_info.update({"tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                save_json(WORLD_FILE, world_data); st.success("同步成功！")

# ----------------- 路由 5: 宗师工具箱 (原著提炼级) -----------------
elif app_mode == "🧰 宗师工具箱":
    st.info("💡 系统已检测到当前作品状态。如果是导入的老书，AI 将【忠于原著提取】；如果是新书，则【辅助生成】。")
    
    # 提取前 8000 字作为 RAG 参考上下文（如果有章节的话）
    sample_context = ""
    if chapters_data:
        sample_context = "\n\n".join([ch["content"] for ch in chapters_data[:3]])[:8000]
        st.success("✅ 已挂载原著小说上下文，开启【深度原著提炼模式】！AI 不会再乱编设定了。")
    
    t1, t2, t3, t4 = st.tabs(["🌍 提炼/构架世界", "👤 塑造角色", "🗺️ 推演大纲", "🩺 逻辑体检"])
    
    with t1:
        if sample_context:
            if st.button("🔍 从导入小说提炼世界观", use_container_width=True, type="primary"):
                with st.spinner("深度阅读原著中..."):
                    prompt = f"这是我小说的原文片段。请你仔细阅读，【提炼】（绝不要自己乱编！）出本书已有的世界观设定，包括地理环境、力量体系、社会势力等。\n原文：\n{sample_context}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.session_state.ai_assistant_reply = res.choices[0].message.content
        else:
            genre = st.text_input("输入题材", "赛博修仙")
            if st.button("🪄 生成新世界观"):
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"请生成【{genre}】题材的长篇世界观，风格【{novel_style}】。包含：地理设定、核心规则、力量体系、禁忌。"}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
    
    with t2:
        if sample_context:
            if st.button("🔍 从导入小说提取全部核心人物", use_container_width=True, type="primary"):
                with st.spinner("梳理人物关系网..."):
                    prompt = f"阅读以下小说原文片段，【提炼】出出现的所有核心角色及其性格、动机、武功体系，不要脑补不存在的人。\n原文：\n{sample_context}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                    st.session_state.ai_assistant_reply = res.choices[0].message.content
        else:
            if st.button("🪄 生成新人物库"):
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"基于当前大纲，生成8个档案，风格【{novel_style}】。"}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
                
    with t3:
        if st.button("🗺️ 推演/续写全书大纲", use_container_width=True):
            with st.spinner("排布中..."):
                prompt = f"基于以下前文剧情/设定，【续写或完善】后续的大纲走向，包含核心反转和最终结局方向。\n参考内容：\n{sample_context if sample_context else load_text(BOOK_OUTLINE_FILE)}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content

    with t4:
        if st.button("🩺 对最近章节进行逻辑体检"):
            chapters_text = "\n".join([f"第{i+1}章：{ch['content']}" for i, ch in enumerate(chapters_data[-5:])])
            prompt = f"分析以下章节的逻辑漏洞、人设OOC、伏笔问题。\n【章节】：\n{chapters_text}"
            res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
            st.session_state.ai_assistant_reply = res.choices[0].message.content

    if st.session_state.ai_assistant_reply:
        st.markdown("---")
        st.text_area("🤖 智囊团提炼结果 (可复制入设定集或大纲)", value=st.session_state.ai_assistant_reply, height=400)
