import streamlit as st
import json
import os
import random
from openai import OpenAI

# ================= 1. 引擎初始化 (安全部署版) =================
with st.sidebar:
    st.header("🔑 引擎激活")
    # type="password" 可以隐藏输入的字符，防止别人偷看
    user_api_key = st.text_input("请输入 DeepSeek API Key", type="password")
    
    if not user_api_key:
        st.info("💡 请在下方输入 DeepSeek 的 API Key 以启动小说引擎。")
        st.caption("你可以从 deepseek 官网申请 Key。")
        st.stop() # 强制停止后续代码运行，保护安全

# 只有输入了 Key，才会运行到这里
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")
# ================= 2. 藏书馆系统 =================
LIBRARY_FILE = "library.json"
if not os.path.exists(LIBRARY_FILE):
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f: json.dump(["我的第一部小说"], f, ensure_ascii=False, indent=4)
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

with st.sidebar:
    st.header("📚 我的书架")
    selected_book = st.selectbox("切换当前作品", books)
    
    with st.expander("🗑️ 管理当前书籍"):
        if st.button("🧨 彻底删除") and st.checkbox("确定永久销毁《" + selected_book + "》吗？"):
            books.remove(selected_book)
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f: json.dump(books, f, ensure_ascii=False, indent=4)
            st.rerun()

    with st.expander("➕ 创建新小说"):
        new_book = st.text_input("新书名：")
        if st.button("立即创建"):
            if new_book and new_book not in books:
                books.append(new_book)
                with open(LIBRARY_FILE, "w", encoding="utf-8") as f: json.dump(books, f, ensure_ascii=False, indent=4)
                st.rerun()

# ================= 3. 数据加载与隔离 =================
WORLD_FILE = f"{selected_book}_world.json"
CHAPTERS_FILE = f"{selected_book}_chapters.json"
BUFFER_FILE = f"{selected_book}_buffer.txt"
BOOK_OUTLINE_FILE = f"{selected_book}_global_outline.txt"
CHAPTER_OUTLINE_FILE = f"{selected_book}_local_outline.txt"

def save_json(file, data):
    with open(file, "w", encoding="utf-8") as f: json.dump(data, f, ensure_ascii=False, indent=4)

if not os.path.exists(WORLD_FILE): save_json(WORLD_FILE, {})
if not os.path.exists(CHAPTERS_FILE): save_json(CHAPTERS_FILE, [])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)

# 初始化百科结构（防丢失）
for char, data in world_data.items():
    if "hp" in data: data["physical"] = "健康"; del data["hp"]
    if "mp" in data: data["magic"] = "充盈"; del data["mp"]
    data.setdefault("physical", "健康")
    data.setdefault("magic", "充盈")
    data.setdefault("status", "未登场")
    data.setdefault("inventory", [])
    data.setdefault("tags", [])
    data.setdefault("appearance", "")
    data.setdefault("voice", "")
    data.setdefault("faction", "")
    data.setdefault("ability", "")
    data.setdefault("weakness", "")
    data.setdefault("background", "")
    data.setdefault("motivation", "")
save_json(WORLD_FILE, world_data)

with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)

# ================= 4. 状态与暂存记忆 =================
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "need_inspiration" not in st.session_state: st.session_state.need_inspiration = False
if "rebuild_world_text" not in st.session_state: st.session_state.rebuild_world_text = ""

if st.session_state.get("last_book") != selected_book:
    st.session_state.last_book = selected_book
    st.session_state.chapter_buffer = open(BUFFER_FILE, "r", encoding="utf-8").read() if os.path.exists(BUFFER_FILE) else ""

# ================= 5. 左侧：精简状态与目录 =================
with st.sidebar:
    tab_status, tab_dir = st.tabs(["📊 动态监控", "📖 目录回溯"])
    
    with tab_status:
        st.caption("详细设定请在右侧【设定库】修改")
        char_list = list(world_data.keys())
        if char_list:
            selected_char = st.selectbox("当前监控", char_list)
            info = world_data[selected_char]
            c_p, c_m = st.columns(2)
            with c_p: st.success(f"💪 身体: {info.get('physical')}")
            with c_m: st.info(f"✨ 灵力: {info.get('magic')}")
            st.write(f"🎒 物品: {', '.join(info.get('inventory', [])) if info.get('inventory') else '空空如也'}")
            st.error(f"🏷️ 处境: {info['status']}")

    with tab_dir:
        if chapters_data:
            export_text = f"《{selected_book}》\n\n"
            for idx, ch in enumerate(chapters_data): export_text += f"第{idx+1}章 {ch['title']}\n\n{ch['content']}\n\n"
            st.download_button("📥 导出全本 TXT", data=export_text, file_name=f"{selected_book}.txt")
            st.markdown("---")
        
        for idx, ch in enumerate(chapters_data):
            c_view, c_act = st.columns([3, 1])
            with c_view:
                with st.expander(f"第{idx+1}章: {ch['title']}"): st.write(ch['content'])
            with c_act:
                if st.button("🗑️", key=f"del_{idx}"):
                    chapters_data.pop(idx)
                    save_json(CHAPTERS_FILE, chapters_data)
                    st.rerun()

# ================= 核心：回溯时的数据安全重建 =================
if st.session_state.rebuild_world_text:
    with st.spinner("🕵️‍♂️ 正在解析回溯章节的动态数据(安全模式)..."):
        p_rebuild = f"""
        阅读文段，更新角色的动态数据。
        【当前百科库】：{json.dumps(world_data, ensure_ascii=False)}
        【回溯章节】：{st.session_state.rebuild_world_text}
        要求：
        1. 仅更新文段中出现角色的 physical, magic, status(10字内), inventory。
        2. 出现新角色则添加完整属性结构。
        3. 【绝对禁止】覆盖或删除库中角色的 tags, appearance, voice, background, motivation 等静态设定！
        只输出纯 JSON 数据。
        """
        r_rebuild = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_rebuild}], response_format={"type":"json_object"})
        world_data = json.loads(r_rebuild.choices[0].message.content)
        save_json(WORLD_FILE, world_data)
        st.session_state.rebuild_world_text = ""
        st.toast("✅ 回溯完成！设定集已保护！")
        st.rerun()

# ================= 6. 右侧：主控大厅 =================
st.title(f"✍️ 《{selected_book}》")

# 使用 Tab 切分核心功能
tab_workspace, tab_wiki, tab_timeline = st.tabs(["🖋️ 连载工作台", "👥 角色设定库 (Wiki)", "⏳ 剧情时间线"])

# ----------------- Tab 2: 角色设定库 -----------------
with tab_wiki:
    st.subheader("📚 本书专属设定集")
    st.caption("AI 将在每次生成时读取这些机密档案，让配角也能拥有灵魂。")
    
    col_list, col_edit = st.columns([1, 3])
    with col_list:
        wiki_chars = list(world_data.keys())
        sel_wiki_char = st.radio("选择要编辑的角色", wiki_chars) if wiki_chars else None
        
        st.markdown("---")
        with st.expander("➕ 创造新角色"):
            new_char_name = st.text_input("新角色姓名")
            if st.button("录入图鉴") and new_char_name:
                if new_char_name not in world_data:
                    world_data[new_char_name] = {"physical": "健康", "magic": "充盈", "status": "未登场", "inventory": [], "tags": [], "appearance": "", "voice": "", "faction": "", "ability": "", "weakness": "", "background": "", "motivation": ""}
                    save_json(WORLD_FILE, world_data)
                    st.rerun()

    if sel_wiki_char:
        with col_edit:
            st.markdown(f"### ⚙️ 编辑档案：{sel_wiki_char}")
            char_info = world_data[sel_wiki_char]
            
            e1, e2 = st.columns(2)
            with e1:
                e_tags = st.text_input("性格标签 (如: 傲娇, 毒舌)", value=",".join(char_info.get("tags", [])))
                e_app = st.text_input("外貌与体型", value=char_info.get("appearance", ""))
                e_voice = st.text_input("声线与口癖", value=char_info.get("voice", ""))
                e_faction = st.text_input("所属势力", value=char_info.get("faction", ""))
            with e2:
                e_ability = st.text_input("异能/武功体系", value=char_info.get("ability", ""))
                e_weak = st.text_input("致命弱点", value=char_info.get("weakness", ""))
                e_bg = st.text_area("身世背景 (仅AI可见)", value=char_info.get("background", ""), height=80)
                e_mot = st.text_area("核心动机/终极目标", value=char_info.get("motivation", ""), height=80)

            if st.button(f"💾 保存 {sel_wiki_char} 的人设", use_container_width=True):
                char_info.update({
                    "tags": [t.strip() for t in e_tags.split(",") if t.strip()],
                    "appearance": e_app, "voice": e_voice, "faction": e_faction,
                    "ability": e_ability, "weakness": e_weak, 
                    "background": e_bg, "motivation": e_mot
                })
                save_json(WORLD_FILE, world_data)
                st.success(f"{sel_wiki_char} 设定已同步！")

# ----------------- Tab 3: 时间线 -----------------
with tab_timeline:
    st.subheader("⏳ 全局剧情时间线")
    if not chapters_data:
        st.info("时间线尚无事件，快去写下第一章吧！")
    else:
        for idx, chapter in enumerate(chapters_data):
            with st.container():
                col_line, col_content = st.columns([1, 15])
                with col_line:
                    st.markdown(f"""
                    <div style="display: flex; flex-direction: column; align-items: center; height: 100%;">
                        <div style="width: 15px; height: 15px; background-color: #ff4b4b; border-radius: 50%; margin-top: 5px;"></div>
                        <div style="width: 2px; height: 100%; background-color: #ff4b4b; opacity: 0.3; flex-grow: 1;"></div>
                    </div>
                    """, unsafe_allow_html=True)
                with col_content:
                    with st.expander(f"📍 第 {idx+1} 幕：{chapter['title']}", expanded=(idx == len(chapters_data)-1)):
                        st.write(chapter['content'])
                        
                        # 把回溯按钮集成在时间线里
                        if st.button("📂 将此幕加载回工作台 (回溯修改)", key=f"tl_load_{idx}"):
                            st.session_state.chapter_buffer = chapter['content']
                            with open(BUFFER_FILE, "w", encoding="utf-8") as f: f.write(chapter['content'])
                            st.session_state.rebuild_world_text = chapter['content'] 
                            st.rerun()

# ----------------- Tab 1: 工作台 (原封不动继承) -----------------
with tab_workspace:
    # 双层大纲
    col_g, col_l = st.columns(2)
    with col_g:
        g_out = st.text_area("🌍 全书走向", value=(open(BOOK_OUTLINE_FILE, "r", encoding="utf-8").read() if os.path.exists(BOOK_OUTLINE_FILE) else ""), height=100)
        if st.button("锁定全书设定"): 
            with open(BOOK_OUTLINE_FILE, "w", encoding="utf-8") as f: f.write(g_out)
            st.toast("设定已保存")
    with col_l:
        l_out = st.text_area("🚩 本章目标", value=(open(CHAPTER_OUTLINE_FILE, "r", encoding="utf-8").read() if os.path.exists(CHAPTER_OUTLINE_FILE) else ""), height=100)
        if st.button("锁定本章目标"): 
            with open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8") as f: f.write(l_out)
            st.toast("目标已锁定")

    st.markdown("---")

    # 暂存箱
    st.subheader(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})")
    buffer_val = st.text_area("在此修改或查看全文...", value=st.session_state.chapter_buffer, height=400)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        with open(BUFFER_FILE, "w", encoding="utf-8") as f: f.write(buffer_val)

    if st.session_state.chapter_buffer:
        c1, c2 = st.columns([3, 1])
        with c1: title = st.text_input("本章标题", key="title_input")
        with c2: 
            if st.button("🪄 标题灵感"):
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":f"取标题：\n{st.session_state.chapter_buffer[:500]}"}])
                st.toast(f"建议：{res.choices[0].message.content}")
        
        if st.button("✅ 结章存档，更新至时间线"):
            chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
            save_json(CHAPTERS_FILE, chapters_data)
            st.session_state.chapter_buffer = ""
            if os.path.exists(BUFFER_FILE): os.remove(BUFFER_FILE)
            st.rerun()

    st.markdown("---")

    # 智能骰子与指令
    col_dice, col_input = st.columns([1, 4])
    with col_dice:
        if st.button("🎲 智能灵感骰子"):
            st.session_state.need_inspiration = True
            st.rerun()
    with col_input:
        new_in = st.chat_input("下达指令...")
        if new_in:
            st.session_state.current_prompt = new_in
            st.session_state.current_draft = ""
            st.rerun()

    if st.session_state.need_inspiration:
        with st.chat_message("assistant"):
            with st.spinner("🎲 推演突发转折..."):
                insp_prompt = f"【本章目标】：{l_out if l_out else '自由发展'}\n【前文】：{st.session_state.chapter_buffer[-400:] if st.session_state.chapter_buffer else '开篇'}\n生成一个贴合大纲的突发事件(20字内)。"
                insp_res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":insp_prompt}])
                st.session_state.current_prompt = f"【突发】：{insp_res.choices[0].message.content}。往下写。"
                st.session_state.need_inspiration = False
                st.rerun()

    # AI 生成
    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner("融合百科设定与大纲构思中..."):
                context = st.session_state.chapter_buffer[-800:] if st.session_state.chapter_buffer else ""
                prompt = f"""你是一位网文作家。
                【全书大纲】：{g_out}
                【本章目标】：{l_out}
                【百科设定字典 (遵守性格和声线)】：{json.dumps(world_data, ensure_ascii=False)}
                【前文】：{context}
                【指令】：{st.session_state.current_prompt}
                要求：严格遵循百科设定。重点描写 physical/magic 感受，约400字。
                """
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = res.choices[0].message.content
                st.rerun()

    # 审核
    if st.session_state.current_draft:
        st.info("💡 建议段落：")
        draft = st.text_area("编辑段落", value=st.session_state.current_draft, height=200)
        b1, b2, b3 = st.columns([2, 1, 1])
        with b1:
            if st.button("➕ 确认接续并结算动态数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                with open(BUFFER_FILE, "w", encoding="utf-8") as f: f.write(st.session_state.chapter_buffer)
                
                with st.spinner("结算数据(保护百科设定)..."):
                    p_up = f"""
                    【百科库】：{json.dumps(world_data, ensure_ascii=False)}
                    【文段】：{draft}
                    要求：
                    1. 仅更新文段中出现角色的 physical, magic, status, inventory。
                    2. 若出现新角色则添加。
                    3. 【核心警告】：绝对禁止修改/删除已有角色的 tags, appearance, voice, faction, ability, weakness, background, motivation！必须原样保留！
                    只输出纯 JSON。
                    """
                    r_up = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_up}], response_format={"type":"json_object"})
                    world_data = json.loads(r_up.choices[0].message.content)
                    save_json(WORLD_FILE, world_data)
                    
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            if st.button("🔄 重写"): st.session_state.current_draft = ""; st.rerun()
        with b3:
            if st.button("🗑️ 取消"): st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
