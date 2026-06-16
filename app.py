import streamlit as st
from neo4j_tools import Neo4jTool
from llm_tools import bailian_tool
from graph_view import generate_kg_html

# ===================== 页面全局配置 =====================
st.set_page_config(
    page_title="美食食谱知识图谱系统",
    page_icon="🍜",
    layout="wide"
)

# 初始化数据库工具
neo4j_tool = Neo4jTool()

# 顶部总数据统计
st.title("🍳 美食食谱知识图谱系统 | 分层架构+可视化+阿里云百炼AI")
# 统计数据
count_cypher = """
MATCH (n) RETURN labels(n) AS type, count(n) AS num
UNION ALL
MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS num
"""
count_data = neo4j_tool.run_cypher(count_cypher)
recipe_num = 0
ing_num = 0
rel_total = 0
for item in count_data:
    if isinstance(item["type"], list) and "Recipe" in item["type"]:
        recipe_num = item["num"]
    elif isinstance(item["type"], list) and "Ingredient" in item["type"]:
        ing_num = item["num"]
    elif not isinstance(item["type"], list):
        rel_total += item["num"]

# 顶部三栏指标
col1, col2, col3 = st.columns(3)
col1.metric("菜品总数", recipe_num)
col2.metric("食材种类", ing_num)
col3.metric("关系总数", rel_total)
st.divider()

# ===================== 顶部标签页切换 =====================
tab1, tab2, tab3, tab4, tab5, tab6 = st.tabs([
    "🔍菜品搜索",
    "📋菜品详情",
    "🥬食材查询",
    "✨食材推理推荐",
    "🤖阿里云百炼AI问答",
    "🌐交互式图谱可视化"
])

# ========== Tab1 菜品搜索 ==========
with tab1:
    st.subheader("菜品模糊检索")
    search_key = st.text_input("输入菜品关键词搜索")
    if st.button("搜索菜品"):
        if search_key.strip() == "":
            st.warning("请输入检索关键词")
        else:
            res = neo4j_tool.search_recipe(search_key)
            if len(res) == 0:
                st.info("未查询到相关菜品")
            else:
                st.dataframe(res, use_container_width=True)

# ========== Tab2 菜品详情（修复c1/c2/c3未定义警告） ==========
with tab2:
    st.subheader("单菜品完整信息查询（多跳关联查询）")
    all_recipes = neo4j_tool.get_all_recipe()
    select_recipe = st.selectbox("选择要查看的菜品", all_recipes)
    if select_recipe:
        base_info, ing_list, step_list, rec_list = neo4j_tool.get_recipe_detail(select_recipe)
        # 定义三列布局，消除IDE警告
        c1, c2, c3 = st.columns(3)
        st.header(f"🍳 {base_info['name']}")
        c1.metric("所属菜系", base_info["category"])
        c2.metric("制作难度", base_info["difficulty"])
        c3.metric("烹饪时长", f"{base_info['cook_time']} 分钟")

        st.divider()
        st.subheader("所需食材")
        st.dataframe(ing_list, use_container_width=True)

        st.divider()
        st.subheader("分步制作步骤")
        for step in step_list:
            num = step.get("step_number", "无序号")
            desc = step.get("description", "无步骤说明")
            st.write(f"第{num}步：{desc}")

        st.divider()
        st.subheader("推荐搭配菜品")
        st.dataframe(rec_list, use_container_width=True)

# ========== Tab3 食材反向查询 ==========
with tab3:
    st.subheader("根据食材反向查询包含该食材的所有菜品")
    ing_name = st.text_input("输入食材名称")
    if st.button("查询相关菜品"):
        if ing_name.strip() == "":
            st.warning("请输入食材名称")
        else:
            res = neo4j_tool.query_recipe_by_ing(ing_name)
            if len(res) == 0:
                st.info("暂无包含该食材的菜品")
            else:
                st.dataframe(res, use_container_width=True)

# ========== Tab4 食材推理推荐 ==========
with tab4:
    st.subheader("基于现有食材的图谱推理推荐")
    st.info("推理规则：匹配用户现有食材，计算菜品食材重合度，优先推荐易制作菜品")
    ing_input = st.text_input("输入家中现有食材（多食材使用英文逗号分隔）", value="番茄,牛肉")
    run_btn = st.button("开始智能推理推荐", type="primary")
    if run_btn:
        with st.spinner("图谱推理计算中..."):
            rec_data = neo4j_tool.recommend_by_ing(ing_input)
            if len(rec_data) == 0:
                st.warning("未匹配到包含这些食材的菜品，请检查食材名称/分隔符！")
            else:
                st.dataframe(rec_data, use_container_width=True)

# ========== Tab5 AI问答（修复KeyError: 'name'，增加容错） ==========
# ========== Tab5 AI问答（修复全套） ==========
with tab5:
    st.subheader("图谱增强AI问答 GraphRAG")
    st.info("先检索Neo4j图谱结构化数据作为上下文，再调用大模型回答，无虚构幻觉")
    kw = st.text_input("输入菜品/美食相关问题", value="宫保鸡丁怎么做")
    if st.button("发起AI问答"):
        try:
            with st.spinner("正在检索图谱知识库..."):
                # 简易关键词提取：提取菜品名（仅演示，可优化）
                clean_word = ""
                for dish in ["宫保鸡丁","麻婆豆腐","红烧肉","西红柿炒鸡蛋"]:
                    if dish in kw:
                        clean_word = dish
                        break
                # 无菜品关键词则空上下文
                if clean_word == "":
                    kg_context = "图谱内未匹配到对应菜品实体，仅根据通用美食知识回答用户问题。"
                else:
                    kg_context = neo4j_tool.get_ai_context(clean_word)

                st.info("📚 图谱检索上下文：" + kg_context)
                prompt = f"图谱参考资料：{kg_context}\n用户问题：{kw}"
                ans = bailian_tool.chat(prompt)
                st.success("🤖 AI回答：")
                st.write(ans)
        except Exception as err:
            st.error(f"执行异常，但不中断程序：{str(err)}")
            st.info("已跳过图谱检索，直接使用通用大模型回答")
            fallback_ans = bailian_tool.chat(f"用户美食问题：{kw}")
            st.write(fallback_ans)

# ========== Tab6 交互式图谱可视化 ==========
with tab6:
    st.subheader("交互式知识图谱拓扑图")
    st.info("蓝色=菜品｜红色=食材｜青绿色=制作步骤，支持拖拽、缩放、悬停查看详情")
    limit_num = st.slider("展示节点数量", min_value=20, max_value=200, value=80, step=10)
    if st.button("生成图谱拓扑图"):
        with st.spinner("正在从Neo4j读取数据、渲染可视化图谱..."):
            html_path = generate_kg_html(neo4j_tool, limit_num=limit_num)
            with open(html_path, "r", encoding="utf-8") as f:
                html_content = f.read()
            st.components.v1.html(html_content, height=780)