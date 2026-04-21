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

st.set_page_config(page_title="上帝大脑 | 终极架构版", layout="wide")

# ================= 2. 藏书馆与全局管理 (移至侧边栏顶部) =================
LIBRARY_FILE = "library.json"
def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)
def load_text(file):
    return open(file, "r", encoding="utf-8").read() if os.path.exists(file) else ""

if not os.path.exists(LIBRARY_FILE): save_json(LIBRARY_FILE, ["我的第一部小说"])
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

# 确保有活动书籍状态
if "active_book" not in st.session_state:
    st.session_state.active_book = books[0] if books else None

with st.sidebar:
    st.header("📚 藏书阁")
    
    # 当前书籍选择器 (受状态控制，导入新书时可自动跳转)
    active_idx = books.index(st.session_state.active_book) if st.session_state.active_book in books else 0
    selected_book = st.selectbox("当前操作作品", books, index=active_idx)
    st.session_state.active_book = selected_book

    # 【核心升级 1 & 3】：新建与老书导入独立成全局功能，自动生成新书
    with st.expander("➕ 新建与导入老书"):
        tab_new, tab_import = st.tabs(["新建空小说", "导入 TXT 老书"])
        with tab_new:
            new_book = st.text_input("新书名：", key="new_book_input")
            if st.button("创建新书", use_container_width=True) and new_book:
                if new_book not in books:
                    books.append(new_book)
                    save_json(LIBRARY_FILE, books)
                    st.session_state.active_book = new_book
                    st.rerun()
        with tab_import:
            st.caption("自动解析章节并创建一本新书")
            uploaded_file = st.file_uploader("选择 TXT", type=["txt"], label_visibility="collapsed")
            if uploaded_file and st.button("🚀 解析并建书", type="primary", use_container_width=True):
                with st.spinner("切割章节中..."):
                    # 自动提取文件名作为新书名 (去掉.txt)
                    new_import_name = uploaded_file.name.replace(".txt", "")
                    # 防止重名
                    base_name = new_import_name
                    counter = 1
                    while new_import_name in books:
                        new_import_name = f"{base_name}_导入版{counter}"
                        counter += 1
                    
                    content = uploaded_file.read().decode("utf-8", errors="ignore")
                    chunks = re.split(r'\n(第[零一二三四五六七八九十百千万0-9]+[章节回幕].*?)\n', "\n" + content)
                    new_chapters = []
                    if chunks[0].strip(): new_chapters.append({"title": "序言/引子", "content": chunks[0].strip()})
                    for i in range(1, len(chunks), 2):
                        new_chapters.append({"title": chunks[i].strip(), "content": chunks[i+1].strip() if i+1 < len(chunks) else ""})
                    
                    # 存入新书数据
                    books.append(new_import_name)
                    save_json(LIBRARY_FILE, books)
                    save_json(f"{new_import_name}_chapters.json", new_chapters)
                    save_json(f"{new_import_name}_world.json", {}) # 初始化空设定集
                    
                    st.session_state.active_book = new_import_name # 强制跳转到新书
                    st.success(f"导入成功！已生成新书《{new_import_name}》")
                    st.rerun()

    with st.expander("⚙️ 当前作品设置"):
        novel_style = st.selectbox("全书风格锚点", ["番茄爽文/快节奏升级", "起点升级流/宏大叙事", "晋江细腻向/情感共鸣", "诡秘悬疑风/不可名状", "二次元轻小说/吐槽搞笑"])
        if st.button("🧨 销毁当前作品", use_container_width=True) and st.checkbox("确认永久删除"):
            books.remove(selected_book)
            save_json(LIBRARY_FILE, books)
            st.session_state.active_book = books[0] if books else None
            st.rerun()

    st.markdown("---")

    # 【核心升级 2】：抛弃嵌套 Tab，改用全局左侧导航栏
    app_mode = st.radio("🧭 工作台导航", ["🖋️ 连载写作台", "👥 角色设定集 (Wiki)", "⏳ 剧情时间线", "🧰 宗师工具箱"])

# ================= 3. 数据加载与隔离 =================
if not st.session_state.active_book:
    st.warning("书架空空如也，请先在左侧创建或导入小说！")
    st.stop()

cur_book = st.session_state.active_book
WORLD_FILE = f"{cur_book}_world.json"
CHAPTERS_FILE = f"{cur_book}_chapters.json"
BUFFER_FILE = f"{cur_book}_buffer.txt"
BOOK_OUTLINE_FILE = f"{cur_book}_global_outline.txt"
CHAPTER_OUTLINE_FILE = f"{cur_book}_local_outline.txt"

if not os.path.exists(WORLD_FILE): save_json(WORLD_FILE, {})
if not os.path.exists(CHAPTERS_FILE): save_json(CHAPTERS_FILE, [])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)

# 初始化百科结构（防丢失）
for char, data in world_data.items():
    if "hp" in data: data["physical"] = "健康"; del data["hp"]
    if "mp" in data: data["magic"] = "充盈"; del data["mp"]
    for key in ["physical", "magic", "status", "appearance", "voice", "faction", "ability", "weakness", "background", "motivation"]:
        data.setdefault(key, "正常" if key == "status" else "")
    data.setdefault("inventory", [])
    data.setdefault("tags", [])
save_json(WORLD_FILE, world_data)

# ================= 4. 状态记忆与回溯数据保护 =================
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "ai_assistant_reply" not in st.session_state: st.session_state.ai_assistant_reply = ""
if "rebuild_world_text" not in st.session_state: st.session_state.rebuild_world_text = ""

if st.session_state.get("last_book_check") != cur_book:
    st.session_state.last_book_check = cur_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)

if st.session_state.rebuild_world_text:
    with st.spinner("🕵️‍♂️ 解析动态数据中(安全模式)..."):
        p_rebuild = f"仅更新出场角色的 physical, magic, status, inventory。严禁修改 tags 等静态设定！输出纯JSON。\n【库】：{json.dumps(world_data, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_world_text}"
        r_rebuild = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_rebuild}], response_format={"type":"json_object"})
        world_data = json.loads(r_rebuild.choices[0].message.content)
        save_json(WORLD_FILE, world_data)
        st.session_state.rebuild_world_text = ""
        st.toast("✅ 回溯完成！设定集已同步！")
        st.rerun()

# ================= 5. 左侧：动态监控 =================
with st.sidebar:
    if app_mode in ["🖋️ 连载写作台", "👥 角色设定集 (Wiki)"]:
        st.markdown("---")
        st.subheader("📊 实时监控")
        char_list = list(world_data.keys())
        if char_list:
            selected_char = st.selectbox("监控角色", char_list, label_visibility="collapsed")
            info = world_data[selected_char]
            c_p, c_m = st.columns(2)
            with c_p: st.success(f"💪 {info.get('physical', '健康')}")
            with c_m: st.info(f"✨ {info.get('magic', '充盈')}")
            st.write(f"🎒 物品: {', '.join(info.get('inventory', [])) if info.get('inventory') else '无'}")
            st.error(f"🏷️ 处境: {info.get('status', '正常')}")
        else:
            st.caption("暂无角色记录")

# ================= 6. 右侧：主控大厅 (动态路由) =================
st.title(f"《{cur_book}》- {app_mode.split(' ')[1]}")
st.markdown("---")

# ----------------- 路由 1: 连载工作台 -----------------
if app_mode == "🖋️ 连载写作台":
    cg, cl = st.columns(2)
    with cg:
        g_out = st.text_area("🌍 全书走向", value=load_text(BOOK_OUTLINE_FILE), height=100)
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out); st.toast("全书大纲已锁定")
    with cl:
        l_out = st.text_area("🚩 本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out); st.toast("本章目标已锁定")

    st.markdown("---")
    buffer_val = st.text_area(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    # 渐进式雷达扫描
    if st.session_state.chapter_buffer:
        with st.expander("🔍 渐进式雷达：扫描本章提取新角色 (旧书导入后极度推荐)"):
            if st.button("🚀 启动扫描", use_container_width=True):
                with st.spinner("雷达全开，抓取新出场角色中..."):
                    known_chars = list(world_data.keys())
                    radar_prompt = f"提取文段中的新角色。忽略这些人：{known_chars}。严格输出JSON，键为姓名，值为字典：physical(健康), magic(充盈), status(现状), inventory([]), tags([]), appearance(\"\"), voice(\"\"), faction(\"\"), ability(\"\"), weakness(\"\"), background(\"\"), motivation(\"\")。无新角色输出{{}}。\n【文段】：{st.session_state.chapter_buffer}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":radar_prompt}], response_format={"type":"json_object"})
                    new_chars = json.loads(res.choices[0].message.content)
                    if new_chars:
                        for k, v in new_chars.items():
                            if k not in world_data: world_data[k] = v
                        save_json(WORLD_FILE, world_data)
                        st.success(f"🎉 成功捕获 {len(new_chars)} 名新角色！已录入【设定集】。")
                    else: st.info("💡 本章未发现新角色。")

    if st.session_state.chapter_buffer:
        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1", placeholder="输入标题完成本章...")
        with ct2: 
            if st.button("✅ 结章并归档", type="primary", use_container_width=True):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None
                st.success("已结章入库！请前往【时间线】查看。")
                st.rerun()

    st.markdown("---")
    cd1, cd2, ci = st.columns([1, 1, 4])
    with cd1:
        if st.button("🎲 剧情突发转折"):
            with st.spinner("推演中..."):
                prompt = f"基于本章目标【{l_out}】和前文，生成一个突发事件(20字内)。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_prompt = f"【灵感突降】：{res.choices[0].message.content}。以此往下写。"
                st.session_state.current_draft = ""
                st.rerun()
    with cd2:
        if st.button("🆘 卡文破局"):
            with st.spinner("生成破局锦囊中..."):
                prompt = f"当前卡文。前文：{st.session_state.chapter_buffer[-500:] if st.session_state.chapter_buffer else '刚开局'}。生成5种破局方案。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = f"【卡文破局锦囊】\n\n{res.choices[0].message.content}\n\n（请挑选一个，改写为指令输入到底部输入框）"
                st.rerun()
                
    with ci:
        new_in = st.chat_input("下达下一段动作指令...")
        if new_in:
            st.session_state.current_prompt = new_in
            st.session_state.current_draft = ""
            st.rerun()

    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner(f"正在执行单章生成协议..."):
                context = st.session_state.chapter_buffer[-1000:] if st.session_state.chapter_buffer else "起笔开篇"
                prompt = f"""
                回顾前文：{context}
                基于设定：{json.dumps(world_data, ensure_ascii=False)}
                目标：{l_out}
                指令：创作本段正文，贴合【{novel_style}】风格。执行导演指令：{st.session_state.current_prompt}。
                要求：加入五感描写、关键心理描写、标志性台词。有情绪波动和小爽点。结尾设悬念钩子。400-600字。禁止AI套话和数值，人设绝对不可OOC。
                """
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = res.choices[0].message.content
                st.rerun()

    if st.session_state.current_draft:
        st.info("💡 草稿审查：")
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3, b4 = st.columns([2, 2, 1, 1])
        with b1:
            if st.button("➕ 确认接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                with st.spinner("自动结算状态..."):
                    p_up = f"仅更新出场角色动态状态。严禁覆盖静态设定！\n【库】：{json.dumps(world_data, ensure_ascii=False)}\n【文】：{draft}"
                    r_up = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_up}], response_format={"type":"json_object"})
                    save_json(WORLD_FILE, json.loads(r_up.choices[0].message.content))
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("✨ 深度润色去 AI 味", type="primary"):
                with st.spinner("执行文笔重塑..."):
                    polish_prompt = f"润色片段，【去AI味、贴合{novel_style}风格】：删除套话，加入五感/小动作，优化节奏。待润色：{draft}"
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":polish_prompt}])
                    st.session_state.current_draft = res.choices[0].message.content
                    st.rerun()
        with b3:
            if st.button("🔄 废弃"): st.session_state.current_draft = ""; st.rerun()
        with b4:
            if st.button("🗑️ 取消"): st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()

# ----------------- 路由 2: 角色设定集 (Wiki) -----------------
elif app_mode == "👥 角色设定集 (Wiki)":
    col_list, col_edit = st.columns([1, 3])
    with col_list:
        wiki_chars = list(world_data.keys())
        sel_wiki_char = st.radio("选择档案", wiki_chars) if wiki_chars else None
        with st.expander("➕ 手动创建新角色"):
            new_char_name = st.text_input("姓名")
            if st.button("录入图鉴", use_container_width=True) and new_char_name and new_char_name not in world_data:
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
                e_bg = st.text_area("身世背景 (仅AI可见)", value=char_info.get("background", ""), height=68)
                e_mot = st.text_area("核心动机", value=char_info.get("motivation", ""), height=68)
            if st.button(f"💾 保存【{sel_wiki_char}】的设定档案", type="primary", use_container_width=True):
                char_info.update({"tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "faction": e_faction, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                save_json(WORLD_FILE, world_data); st.success("同步成功！")

# ----------------- 路由 3: 剧情时间线与导出 -----------------
elif app_mode == "⏳ 剧情时间线":
    col_tl, col_export = st.columns([3, 1])
    with col_export:
        st.subheader("📦 整本导出")
        if chapters_data:
            export_text = f"《{cur_book}》\n\n"
            for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
            st.download_button("📥 导出全本 TXT", data=export_text, file_name=f"{cur_book}.txt", use_container_width=True)
        else:
            st.info("暂无章节可导出")
            
    with col_tl:
        st.subheader("📍 全局剧本轴")
        if not chapters_data: st.info("时间线尚无事件，快去工作台写下第一章吧！")
        for idx, chapter in enumerate(chapters_data):
            with st.container():
                cl, cc = st.columns([1, 15])
                with cl: st.markdown('<div style="display:flex;flex-direction:column;align-items:center;height:100%;"><div style="width:15px;height:15px;background:#ff4b4b;border-radius:50%;margin-top:5px;"></div><div style="width:2px;height:100%;background:#ff4b4b;opacity:0.3;flex-grow:1;"></div></div>', unsafe_allow_html=True)
                with cc:
                    with st.expander(f"第 {idx+1} 幕：{chapter['title']}", expanded=(idx == len(chapters_data)-1)):
                        st.write(chapter['content'])
                        c_btn1, c_btn2 = st.columns(2)
                        with c_btn1:
                            if st.button("📂 回溯修改此章", key=f"tl_load_{idx}", use_container_width=True):
                                st.session_state.chapter_buffer = chapter['content']
                                open(BUFFER_FILE, "w", encoding="utf-8").write(chapter['content'])
                                st.session_state.rebuild_world_text = chapter['content']
                                st.success("已加载回工作台暂存箱！请在左侧切换回【🖋️ 连载写作台】。")
                        with c_btn2:
                            if st.button("🗑️ 彻底删除此章", key=f"tl_del_{idx}", use_container_width=True):
                                chapters_data.pop(idx)
                                save_json(CHAPTERS_FILE, chapters_data)
                                st.rerun()

# ----------------- 路由 4: 宗师工具箱 -----------------
elif app_mode == "🧰 宗师工具箱":
    st.info(f"💡 当前所有工具生成将自动匹配你在左侧设置的【{novel_style}】风格。")
    t1, t2, t3, t4 = st.tabs(["🌍 构架世界", "👤 塑造角色", "🗺️ 推演大纲", "🩺 逻辑体检"])
    
    with t1:
        genre = st.text_input("输入核心题材", "赛博修仙")
        if st.button("🪄 一键生成世界观设定", use_container_width=True):
            with st.spinner("正在构建世界底层法则..."):
                prompt = f"请生成【{genre}】题材的长篇世界观，贴合【{novel_style}】风格。要求包含：地理设定、社会体系、核心规则、力量体系、核心冲突、禁忌。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
    with t2:
        if st.button("🪄 一键生成核心人物库", use_container_width=True):
            with st.spinner("正在注入灵魂..."):
                prompt = f"基于以下世界观，创作8个核心人物档案(3主+5配含1反派)，风格【{novel_style}】。包含：姓名、年龄、外貌、身份、性格、动机、弱点、口头禅。\n大纲参考：\n{load_text(BOOK_OUTLINE_FILE)[:1000]}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
    with t3:
        if st.button("🪄 一键推演全书大纲", use_container_width=True):
            with st.spinner("正在排布爽点与伏笔..."):
                prompt = f"基于设定，按【{novel_style}】风格创作全书大纲(3卷，每卷20章)。包含：全书主题、结局方向、伏笔清单。每卷需有反转。每章有事件+爽点+钩子。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
    with t4:
        if st.button("🩺 对最近章节进行逻辑体检", use_container_width=True):
            with st.spinner("扫描逻辑漏洞与 OOC 中..."):
                chapters_text = "\n".join([f"第{i+1}章：{ch['content']}" for i, ch in enumerate(chapters_data[-5:])])
                prompt = f"分析以下最近章节。检查：1.逻辑漏洞 2.人设OOC 3.伏笔问题 4.节奏与冲突。给出修改方案。\n【章节】：\n{chapters_text}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content

    if st.session_state.ai_assistant_reply:
        st.markdown("---")
        st.text_area("🤖 智囊团生成结果 (可直接复制使用)", value=st.session_state.ai_assistant_reply, height=500)
