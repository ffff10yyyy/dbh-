import streamlit as st
import json
import os
import random
from openai import OpenAI

# ================= 1. 引擎初始化 =================
with st.sidebar:
    st.header("🔑 引擎激活")
    user_api_key = st.text_input("请输入 DeepSeek API Key", type="password", value="sk-0275d85e2cd348d09b81fb01321b0147")
    if not user_api_key:
        st.warning("👈 请输入 API Key 启动引擎")
        st.stop()
client = OpenAI(api_key=user_api_key, base_url="https://api.deepseek.com")

st.set_page_config(page_title="上帝大脑 | 工业化 SOP 版", layout="wide")

# ================= 2. 藏书馆系统 =================
LIBRARY_FILE = "library.json"
if not os.path.exists(LIBRARY_FILE):
    with open(LIBRARY_FILE, "w", encoding="utf-8") as f: json.dump(["我的第一部小说"], f, ensure_ascii=False, indent=4)
with open(LIBRARY_FILE, "r", encoding="utf-8") as f: books = json.load(f)

with st.sidebar:
    st.header("📚 我的书架")
    selected_book = st.selectbox("切换当前作品", books)
    
    # 【新增】：全书风格锚点
    novel_style = st.selectbox("🎯 奠定全书风格", ["番茄爽文/快节奏升级", "起点升级流/宏大叙事", "晋江细腻向/情感共鸣", "诡秘悬疑风/不可名状", "二次元轻小说/吐槽搞笑"])
    
    with st.expander("🗑️ 管理当前书籍"):
        if st.button("🧨 彻底删除") and st.checkbox("确定永久销毁《" + selected_book + "》吗？"):
            books.remove(selected_book)
            with open(LIBRARY_FILE, "w", encoding="utf-8") as f: json.dump(books, f, ensure_ascii=False, indent=4)
            st.rerun()
    with st.expander("➕ 创建新小说"):
        new_book = st.text_input("新书名：")
        if st.button("立即创建") and new_book not in books:
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
def load_text(file):
    return open(file, "r", encoding="utf-8").read() if os.path.exists(file) else ""

if not os.path.exists(WORLD_FILE): save_json(WORLD_FILE, {})
if not os.path.exists(CHAPTERS_FILE): save_json(CHAPTERS_FILE, [])

with open(WORLD_FILE, "r", encoding="utf-8") as f: world_data = json.load(f)
with open(CHAPTERS_FILE, "r", encoding="utf-8") as f: chapters_data = json.load(f)

# ================= 4. 状态与暂存记忆 =================
if "current_prompt" not in st.session_state: st.session_state.current_prompt = ""
if "current_draft" not in st.session_state: st.session_state.current_draft = ""
if "ai_assistant_reply" not in st.session_state: st.session_state.ai_assistant_reply = ""
if "rebuild_world_text" not in st.session_state: st.session_state.rebuild_world_text = ""

if st.session_state.get("last_book") != selected_book:
    st.session_state.last_book = selected_book
    st.session_state.chapter_buffer = load_text(BUFFER_FILE)

# ================= 5. 左侧：精简状态与目录 =================
with st.sidebar:
    tab_status, tab_dir = st.tabs(["📊 动态监控", "📖 目录回溯"])
    with tab_status:
        char_list = list(world_data.keys())
        if char_list:
            selected_char = st.selectbox("当前监控", char_list)
            info = world_data[selected_char]
            c_p, c_m = st.columns(2)
            with c_p: st.success(f"💪 身体: {info.get('physical', '健康')}")
            with c_m: st.info(f"✨ 灵力: {info.get('magic', '充盈')}")
            st.write(f"🎒 物品: {', '.join(info.get('inventory', [])) if info.get('inventory') else '无'}")
            st.error(f"🏷️ 处境: {info.get('status', '正常')}")

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

# 回溯保护
if st.session_state.rebuild_world_text:
    with st.spinner("🕵️‍♂️ 解析动态数据中..."):
        p_rebuild = f"根据文段更新角色physical, magic, status, inventory。严禁修改静态设定！输出JSON。\n【库】：{json.dumps(world_data, ensure_ascii=False)}\n【文】：{st.session_state.rebuild_world_text}"
        r_rebuild = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_rebuild}], response_format={"type":"json_object"})
        world_data = json.loads(r_rebuild.choices[0].message.content)
        save_json(WORLD_FILE, world_data)
        st.session_state.rebuild_world_text = ""
        st.rerun()

# ================= 6. 右侧：主控大厅 =================
st.title(f"✍️ 《{selected_book}》")

tab_workspace, tab_wiki, tab_timeline, tab_toolbox = st.tabs(["🖋️ 工作台", "👥 设定集", "⏳ 时间线", "🧰 宗师工具箱"])

# ----------------- Tab 4: 宗师工具箱 (SOP 模板 1, 2, 3, 6) -----------------
with tab_toolbox:
    st.subheader("🛠️ 智能 SOP 构建系统")
    st.caption(f"当前执行风格锚点：【{novel_style}】")
    
    t1, t2, t3, t4 = st.tabs(["🌍 构架世界", "👤 塑造角色", "🗺️ 推演大纲", "🩺 逻辑体检"])
    
    with t1:
        st.info("基于模板一：生成结构清晰、逻辑自洽的世界观。")
        genre = st.text_input("输入核心题材 (如：赛博修仙、都市异能)", "赛博修仙")
        if st.button("🪄 一键生成世界观设定"):
            with st.spinner("正在构建世界底层法则..."):
                prompt = f"请生成【{genre}】题材的长篇小说世界观，贴合【{novel_style}】风格。要求包含：地理设定、社会阶层/体系、核心规则(3-5条不可冲突)、力量/科技体系、核心冲突、禁忌设定(3-4条)。内容详实，不空洞模板化。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content
                
    with t2:
        st.info("基于模板二：生成8人核心档案，人设鲜明，带动机和弱点。")
        if st.button("🪄 一键生成核心人物库"):
            with st.spinner("正在注入灵魂..."):
                prompt = f"基于以下世界观，创作8个核心人物档案(3主+5配含1反派)，风格【{novel_style}】。每个档案必须包含：姓名、年龄、外貌(2处标志)、身份(表层+隐藏)、性格(核心+缺点+细节)、核心动机(短+长)、弱点(真实致命)、标志性特征(口头禅+动作)。反派需明确动机。\n当前大纲/世界观参考：\n{load_text(BOOK_OUTLINE_FILE)[:1000]}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content

    with t3:
        st.info("基于模板三：生成3卷20章的详尽大纲，带钩子和爽点。")
        if st.button("🪄 一键推演全书大纲"):
            with st.spinner("正在排布爽点与伏笔..."):
                prompt = f"基于设定，按【{novel_style}】风格创作全书大纲(3卷，每卷20章)。必须包含：全书核心主题、结局方向、伏笔总清单(5-8个)。每卷需有核心目标和卷末反转。每章需列出：核心事件+爽点/情绪点+结尾钩子。每3-5章一个小爽点。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content

    with t4:
        st.info("基于模板六(逻辑检查)：防崩盘神器。")
        if st.button("🩺 对已写章节进行全面体检"):
            with st.spinner("扫描逻辑漏洞与 OOC 中..."):
                chapters_text = "\n".join([f"第{i+1}章：{ch['content']}" for i, ch in enumerate(chapters_data[-5:])]) # 检查最近5章
                prompt = f"基于世界观和全书大纲，分析以下最近章节内容。重点检查4点：1. 逻辑漏洞(与前文或规则冲突的地方)。2. 人设OOC(人物言行不符设定)。3. 伏笔问题(未铺垫或未回收)。4. 节奏与冲突(太慢或太突兀)。给出具体问题和直接修改方案。\n【待查章节】：\n{chapters_text}"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.ai_assistant_reply = res.choices[0].message.content

    if st.session_state.ai_assistant_reply:
        st.markdown("---")
        st.text_area("🤖 智囊团生成结果 (请复制所需内容到对应的大纲或百科中)", value=st.session_state.ai_assistant_reply, height=400)

# ----------------- Tab 2: 角色设定库 (Wiki) -----------------
with tab_wiki:
    col_list, col_edit = st.columns([1, 3])
    with col_list:
        wiki_chars = list(world_data.keys())
        sel_wiki_char = st.radio("编辑角色", wiki_chars) if wiki_chars else None
        with st.expander("➕ 创造新角色"):
            new_char_name = st.text_input("新角色姓名")
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
                e_bg = st.text_area("身世背景", value=char_info.get("background", ""), height=60)
                e_mot = st.text_area("核心动机", value=char_info.get("motivation", ""), height=60)
            if st.button(f"💾 保存 {sel_wiki_char}", use_container_width=True):
                char_info.update({"tags": [t.strip() for t in e_tags.split(",") if t.strip()], "appearance": e_app, "voice": e_voice, "ability": e_ability, "weakness": e_weak, "background": e_bg, "motivation": e_mot})
                save_json(WORLD_FILE, world_data); st.success("同步成功！")

# ----------------- Tab 3: 时间线 -----------------
with tab_timeline:
    if not chapters_data: st.info("尚无事件。")
    for idx, chapter in enumerate(chapters_data):
        with st.container():
            cl, cc = st.columns([1, 15])
            with cl: st.markdown('<div style="display:flex;flex-direction:column;align-items:center;height:100%;"><div style="width:15px;height:15px;background:#ff4b4b;border-radius:50%;margin-top:5px;"></div><div style="width:2px;height:100%;background:#ff4b4b;opacity:0.3;flex-grow:1;"></div></div>', unsafe_allow_html=True)
            with cc:
                with st.expander(f"📍 第 {idx+1} 幕：{chapter['title']}", expanded=(idx == len(chapters_data)-1)):
                    st.write(chapter['content'])
                    if st.button("📂 回溯修改", key=f"tl_load_{idx}"):
                        st.session_state.chapter_buffer = chapter['content']
                        with open(BUFFER_FILE, "w", encoding="utf-8") as f: f.write(chapter['content'])
                        st.session_state.rebuild_world_text = chapter['content']
                        st.rerun()

# ----------------- Tab 1: 连载工作台 (SOP 模板 4, 5, 6) -----------------
with tab_workspace:
    cg, cl = st.columns(2)
    with cg:
        g_out = st.text_area("🌍 全书走向", value=load_text(BOOK_OUTLINE_FILE), height=100)
        if st.button("锁定全书", key="bg1"): open(BOOK_OUTLINE_FILE, "w", encoding="utf-8").write(g_out)
    with cl:
        l_out = st.text_area("🚩 本章目标", value=load_text(CHAPTER_OUTLINE_FILE), height=100)
        if st.button("锁定本章", key="bl1"): open(CHAPTER_OUTLINE_FILE, "w", encoding="utf-8").write(l_out)

    st.markdown("---")
    buffer_val = st.text_area(f"📝 本章暂存箱 (字数: {len(st.session_state.chapter_buffer)})", value=st.session_state.chapter_buffer, height=350)
    if buffer_val != st.session_state.chapter_buffer:
        st.session_state.chapter_buffer = buffer_val
        open(BUFFER_FILE, "w", encoding="utf-8").write(buffer_val)

    if st.session_state.chapter_buffer:
        ct1, ct2 = st.columns([3, 1])
        with ct1: title = st.text_input("本章标题", key="ti1")
        with ct2: 
            if st.button("✅ 结章存入时间线"):
                chapters_data.append({"title": title if title else "未命名", "content": st.session_state.chapter_buffer})
                save_json(CHAPTERS_FILE, chapters_data)
                st.session_state.chapter_buffer = ""; os.remove(BUFFER_FILE) if os.path.exists(BUFFER_FILE) else None
                st.rerun()

    st.markdown("---")
    
    # 救场与指令区
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
            with st.spinner("智囊团生成破局方案中..."):
                prompt = f"当前卡文。前文摘要：{st.session_state.chapter_buffer[-500:] if st.session_state.chapter_buffer else '刚开局'}。基于人物库和目标，生成5种合理的破局方案。涵盖自身破局、外力破局、反转破局，并标注星级和优缺点。"
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = f"【卡文破局锦囊】\n\n{res.choices[0].message.content}\n\n（请挑选一个方案，改写为您自己的指令输入到底部输入框）"
                st.rerun()
                
    with ci:
        new_in = st.chat_input("输入剧情指令...")
        if new_in:
            st.session_state.current_prompt = new_in
            st.session_state.current_draft = ""
            st.rerun()

    # ================= 核心：基于“模板四”的单章生成引擎 =================
    if st.session_state.current_prompt and not st.session_state.current_draft:
        with st.chat_message("assistant"):
            with st.spinner(f"正在以【{novel_style}】风格，执行核心单章生成协议..."):
                context = st.session_state.chapter_buffer[-1000:] if st.session_state.chapter_buffer else "起笔开篇"
                prompt = f"""
                【严格执行模板四：防跑偏保质量单章生成协议】
                回顾前文：{context}
                基于世界观、人物档案：{json.dumps(world_data, ensure_ascii=False)}
                全书大纲与本章目标：{l_out}
                
                指令：创作本段正文，严格贴合【{novel_style}】风格。必须满足以下所有要求：
                1. 核心情节：执行导演指令：{st.session_state.current_prompt}。
                2. 细节要求：加入至少3处五感描写、1段关键心理描写、符合人物设定的标志性台词和口头禅。
                3. 节奏与情绪：必须有情绪波动，设置一个小爽点或情绪共鸣点。
                4. 结尾钩子：结尾设置1个悬念钩子，吸引继续阅读。
                5. 字数与风格：控制在400-600字左右。语言流畅，短句为主，禁止使用“只见他眼神一冷”等AI模板化套话，绝对不可出现生命值等游戏数值。人设绝对不可OOC。
                """
                res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":prompt}])
                st.session_state.current_draft = res.choices[0].message.content
                st.rerun()

    # 审核与润色区
    if st.session_state.current_draft:
        st.info("💡 建议内容：")
        draft = st.text_area("编辑区", value=st.session_state.current_draft, height=250)
        b1, b2, b3, b4 = st.columns([2, 2, 1, 1])
        with b1:
            if st.button("➕ 确认接续并更新数据"):
                st.session_state.chapter_buffer += f"\n\n{draft}"
                open(BUFFER_FILE, "w", encoding="utf-8").write(st.session_state.chapter_buffer)
                with st.spinner("结算数据..."):
                    p_up = f"仅更新出场角色的 physical, magic, status, inventory。严禁覆盖 tags 等静态设定！\n【库】：{json.dumps(world_data, ensure_ascii=False)}\n【文】：{draft}"
                    r_up = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":p_up}], response_format={"type":"json_object"})
                    save_json(WORLD_FILE, json.loads(r_up.choices[0].message.content))
                st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
        with b2:
            # ================= 核心：基于“模板五”的深度润色 =================
            if st.button("✨ 深度润色去 AI 味", type="primary"):
                with st.spinner("正在执行高阶文笔重塑..."):
                    polish_prompt = f"""
                    【执行模板五：润色/去AI味协议】
                    请润色以下小说片段，核心目标是【去AI味、增强文笔、贴合{novel_style}风格】：
                    1. 删除所有AI模板化套话（如“强大的气息”、“倒吸一口凉气”），替换为生动细节。
                    2. 优化节奏：短句为主，长短句结合，增强画面感和情绪张力。
                    3. 补充细节：新增五感描写/方言/人物特有的小动作。对话严格符合人设字典。
                    4. 绝对不可改变核心事件和伏笔。
                    
                    待润色文本：
                    {draft}
                    """
                    res = client.chat.completions.create(model="deepseek-chat", messages=[{"role":"user","content":polish_prompt}])
                    st.session_state.current_draft = res.choices[0].message.content
                    st.rerun()
        with b3:
            if st.button("🔄 废弃"): st.session_state.current_draft = ""; st.rerun()
        with b4:
            if st.button("🗑️ 取消"): st.session_state.current_prompt = ""; st.session_state.current_draft = ""; st.rerun()
