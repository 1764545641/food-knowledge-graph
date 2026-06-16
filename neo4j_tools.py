import streamlit as st
from neo4j import GraphDatabase

class Neo4jTool:
    def __init__(self):
        # 从Streamlit后台Secrets读取密钥，云端无法读取本地.env
        neo4j_conf = st.secrets["NEO4J"]
        self.uri = neo4j_conf["NEO4J_URI"]
        self.user = neo4j_conf["NEO4J_USERNAME"]
        self.pwd = neo4j_conf["NEO4J_PASSWORD"]
        self.driver = GraphDatabase.driver(self.uri, auth=(self.user, self.pwd))

    def close(self):
        self.driver.close()

    def run_cypher(self, cypher, params=None):
        """执行Cypher，返回字典列表"""
        if params is None:
            params = {}
        with self.driver.session() as session:
            res = session.run(cypher, params)
            return [record.data() for record in res]

    # 1. 获取全部菜品下拉框
    def get_all_recipe(self):
        cypher = """
        MATCH (r:Recipe)
        RETURN r.name AS name
        ORDER BY r.name
        """
        data = self.run_cypher(cypher)
        return [item["name"] for item in data]

    # 2. 菜品模糊搜索
    def search_recipe(self, kw):
        cypher = """
        MATCH (r:Recipe)
        WHERE r.name CONTAINS $k
        RETURN r.name AS 菜品名, r.category AS 菜系, r.difficulty AS 难度, r.cook_time AS 烹饪时长
        """
        return self.run_cypher(cypher, {"k": kw})

    # 3. 根据食材查菜品
    def query_recipe_by_ing(self, ing_name):
        cypher = """
        MATCH (r:Recipe)-[:NEEDS]->(i:Ingredient{name:$ing})
        RETURN DISTINCT r.name AS 菜品名, r.category AS 菜系
        ORDER BY r.name
        """
        return self.run_cypher(cypher, {"ing": ing_name})

    # 4. 食材重合度推理推荐
    def recommend_by_ing(self, ing_str):
        cypher = """
        WITH $ingredients AS input_ings
        UNWIND split(input_ings, ",") AS ing_name
        WITH trim(ing_name) AS clean_ing
        MATCH (i:Ingredient{name:clean_ing})<-[:NEEDS]-(r:Recipe)
        WITH r, count(DISTINCT i) AS match_cnt
        MATCH (r)-[:NEEDS]->(all_i:Ingredient)
        WITH r, match_cnt, count(DISTINCT all_i) AS total_ing
        RETURN r.name AS 菜品名, r.category AS 菜系, r.difficulty AS 难度,
               match_cnt, total_ing, toFloat(match_cnt)/total_ing AS 食材重合度
        ORDER BY 食材重合度 DESC, r.difficulty ASC
        """
        return self.run_cypher(cypher, {"ingredients": ing_str})

    # 5. 获取单菜品完整详情（菜品基础/食材/步骤/推荐）
    def get_recipe_detail(self, recipe_name):
        # 基础信息
        base_cypher = """
        MATCH (r:Recipe{name:$name})
        RETURN r.name AS name, r.category AS category, r.difficulty AS difficulty, r.cook_time AS cook_time
        """
        base_res = self.run_cypher(base_cypher, {"name": recipe_name})
        base_info = base_res[0] if base_res else {"name":"","category":"","difficulty":"","cook_time":0}

        # 所需食材
        ing_cypher = """
        MATCH (r:Recipe{name:$name})-[n:NEEDS]->(i:Ingredient)
        RETURN i.name AS 食材名, n.quantity AS 用量, n.note AS 备注
        """
        ing_list = self.run_cypher(ing_cypher, {"name": recipe_name})

        # 制作步骤（固定别名 step_number / description）
        step_cypher = """
        MATCH (r:Recipe{name:$name})-[:HAS_STEP]->(s:Step)
        RETURN s.step_number AS step_number, s.description AS description
        ORDER BY s.step_number
        """
        step_list = self.run_cypher(step_cypher, {"name": recipe_name})

        # 推荐菜品
        rec_cypher = """
        MATCH (r1:Recipe{name:$name})-[rec:RECOMMENDS]->(r2:Recipe)
        RETURN r2.name AS 推荐菜品, rec.reason AS 推荐理由
        """
        rec_list = self.run_cypher(rec_cypher, {"name": recipe_name})

        return base_info, ing_list, step_list, rec_list

    # 6. AI问答图谱上下文（修复KeyError:name）
    def get_ai_context(self, keyword):
        cypher = """
        MATCH (r:Recipe)
        WHERE r.name CONTAINS $kw
        RETURN r.name AS name, r.category AS category, coalesce(r.description, "暂无简介") AS description
        LIMIT 1
        """
        res = self.run_cypher(cypher, {"kw": keyword})
        if not res:
            return f"图谱知识库中未检索到与「{keyword}」相关的菜品数据"
        data = res[0]
        name = data.get("name", "未知菜品")
        category = data.get("category", "未知菜系")
        desc = data.get("description", "暂无简介")
        context = f"菜品：{name}，菜系：{category}\n简介：{desc}\n"
        return context

    # 7. 统计节点、关系总数（首页顶部指标）
   
    def get_count_stat(self):
        cypher = """
        MATCH (n) RETURN labels(n) AS type, count(n) AS num
        UNION ALL
        MATCH ()-[r]->() RETURN type(r) AS type, count(r) AS num
        """
        return self.run_cypher(cypher)

  
