import tempfile
from pyvis.network import Network

def generate_kg_html(neo4j_tool, limit_num=80):
    net = Network(
        height="750px",
        width="100%",
        bgcolor="#1a1a1a",
        font_color="white",
        notebook=False
    )

    # 简化配置：关闭连线文字，物理布局正常散开
    net.set_options("""
    {
      "physics": {
        "barnesHut": {
          "gravity": -8000,
          "centralGravity": 0.3,
          "springLength": 120,
          "springConstant": 0.04,
          "damping": 0.09,
          "avoidOverlap": 0.1
        },
        "enabled": true
      },
      "edges": {
        "font": {"size": 0},
        "labelHighlightBold": false,
        "color": {"inherit": false},
        "smooth": {"type": "continuous"}
      },
      "nodes": {
        "font": {"size": 12, "face": "微软雅黑"},
        "size": 25,
        "borderWidth": 2
      }
    }
    """)

    # 实体配色
    color_map = {
        "Recipe": "#639df0",
        "Ingredient": "#f26c6c",
        "Step": "#6cd9b9"
    }
    # 关系线条区分颜色，不加文字更清爽
    edge_style = {
        "HAS_STEP": {"color": "#4cd964", "dashes": False},
        "NEEDS": {"color": "#ff9500", "dashes": False},
        "RECOMMENDS": {"color": "#ffcc00", "dashes": True}
    }

    added_nodes = set()

    cypher = f"""
    MATCH (n)
    WHERE labels(n) <> []
    OPTIONAL MATCH (n)-[r]-(m)
    WHERE labels(m) <> []
    WITH DISTINCT n, r, m
    LIMIT {limit_num * 2}
    RETURN
        labels(n) AS n_label,
        trim(replace(replace(coalesce(n.name, n.description, "未知节点"),"\\n","")," ","")) AS n_name,
        labels(m) AS m_label,
        trim(replace(replace(coalesce(m.name, m.description, "未知节点"),"\\n","")," ","")) AS m_name,
        type(r) AS rel_type
    """
    res = neo4j_tool.run_cypher(cypher)

    for record in res:
        # 渲染主节点
        n_label_list = record["n_label"]
        n_raw_name = record["n_name"]
        n_label = n_label_list[0] if n_label_list else "Unknown"
        n_node_name = n_raw_name if n_raw_name else f"{n_label}_无名节点"
        n_color = color_map.get(n_label, "#aaaaaa")

        if n_node_name not in added_nodes:
            net.add_node(
                n_node_name,
                label=n_node_name,
                color=n_color,
                title=f"实体：{n_label}"
            )
            added_nodes.add(n_node_name)

        # 渲染关联节点与连线
        m_label_list = record["m_label"]
        m_raw_name = record["m_name"]
        rel_type = record["rel_type"]
        if m_label_list and m_raw_name and rel_type:
            m_label = m_label_list[0]
            m_node_name = m_raw_name if m_raw_name else f"{m_label}_无名节点"
            m_color = color_map.get(m_label, "#aaaaaa")
            if m_node_name not in added_nodes:
                net.add_node(
                    m_node_name,
                    label=m_node_name,
                    color=m_color,
                    title=f"实体：{m_label}"
                )
                added_nodes.add(m_node_name)

            style = edge_style.get(rel_type, {"color": "#aaaaaa", "dashes": False})
            # 移除 label=rel_type，连线上无文字，仅鼠标悬浮看关系
            net.add_edge(
                n_node_name,
                m_node_name,
                title=f"关系：{rel_type}",
                color=style["color"],
                dashes=style["dashes"]
            )

    tmp_file = tempfile.NamedTemporaryFile(mode="w", suffix=".html", delete=False, encoding="utf-8")
    net.write_html(tmp_file.name)
    tmp_file.close()
    return tmp_file.name