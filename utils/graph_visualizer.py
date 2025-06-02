
import networkx as nx
import matplotlib.pyplot as plt
import streamlit as st

def build_graph(results, max_nodes=50):
    G = nx.Graph()

    for r in results[:max_nodes]:
        uid = r.get("username", "") + "_" + r.get("platform", "")
        content = r.get("content", "")
        topic = r.get("topic", "Uncategorized")
        entities = r.get("entities", [])

        G.add_node(uid, label="user", color="skyblue")
        G.add_node(topic, label="topic", color="lightgreen")
        G.add_edge(uid, topic)

        for ent in entities:
            G.add_node(ent, label="entity", color="orange")
            G.add_edge(uid, ent)

    return G

def draw_graph(G):
    st.subheader("🕸 OSINT Graph: Users ↔ Entities ↔ Topics")
    pos = nx.spring_layout(G, k=0.4)
    colors = [G.nodes[n].get("color", "grey") for n in G.nodes]

    plt.figure(figsize=(12, 8))
    nx.draw_networkx(G, pos, node_color=colors, with_labels=True, font_size=9, edge_color="gray")
    st.pyplot(plt)
