"""
graph.py — Grafo LangGraph del asistente financiero.
Arquitectura:
    [usuario] → [nodo LLM] → ¿tool? → SÍ → [ejecutar tool] → [nodo LLM] → [respuesta]
                                     → NO → [respuesta]
La API Key se recibe como parámetro en cada invocación,
NUNCA se hardcodea ni se guarda en el servidor.
"""

from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .tools import ALL_TOOLS

# Nombres de nodos para claridad
NODE_LLM = "llm"
NODE_TOOLS = "tools"


def build_graph(api_key: str) -> "CompiledGraph":
    """
    Construye y compila el grafo LangGraph.

    Parámetros:
        api_key: API Key de Google AI (Gemini) proporcionada por el usuario en cada petición.

    Devuelve el grafo compilado listo para invocar.
    """
    llm = ChatGoogleGenerativeAI(
        model="gemini-2.0-flash",
        temperature=0.3,
        google_api_key=api_key,
    ).bind_tools(ALL_TOOLS)

    def llm_node(state: AgentState) -> dict:
        response = llm.invoke(state["messages"])
        return {"messages": [response]}

    # edge condicional: ¿el LLM quiere ejecutar una tool?
    def should_use_tool(state: AgentState) -> str:
        last_message = state["messages"][-1]
        if hasattr(last_message, "tool_calls") and last_message.tool_calls:
            return NODE_TOOLS
        return END
    
    graph_builder = StateGraph(AgentState)

    graph_builder.add_node(NODE_LLM, llm_node)
    graph_builder.add_node(NODE_TOOLS, ToolNode(ALL_TOOLS))

    graph_builder.set_entry_point(NODE_LLM)

    graph_builder.add_conditional_edges(
        NODE_LLM,
        should_use_tool,
        {NODE_TOOLS: NODE_TOOLS, END: END},
    )

    # después de ejecutar tools, volvemos al LLM para que redacte la respuesta final
    graph_builder.add_edge(NODE_TOOLS, NODE_LLM)

    return graph_builder.compile()

# para probar que funciona el agente
if __name__ == "__main__":
    import os
    import sys
    from pathlib import Path
    from langchain_core.messages import HumanMessage

    api_key = os.environ.get("GOOGLE_API_KEY")
    if not api_key:
        raise ValueError("Exporta GOOGLE_API_KEY antes de ejecutar este script.")

    graph = build_graph(api_key)

    preguntas = [
        "¿Cuánto he gastado este trimestre por categoría?",                      # get_gastos_periodo
        "¿Cómo ha evolucionado mi gasto en Supermercado los últimos 6 meses?",   # get_evolucion_categoria
        "Dame el balance de ingresos y gastos del último semestre.",             # get_resumen_ingresos_vs_gastos
        "¿Cómo voy con mi objetivo de Vacaciones de verano?",                    # get_progreso_objetivo
        "¿Cuáles han sido mis 5 gastos más altos este año?",                     # get_top_gastos
    ]

    for pregunta in preguntas:
        print(f"👤 Usuario: {pregunta}")
        result = graph.invoke({"messages": [HumanMessage(content=pregunta)]})
        print(f"🤖 Agente:  {result['messages'][-1].content}")