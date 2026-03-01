"""
graph.py — Grafo LangGraph del asistente financiero.
"""

from datetime import date

from langchain_core.messages import SystemMessage
from langchain_google_genai import ChatGoogleGenerativeAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import StateGraph, END
from langgraph.prebuilt import ToolNode

from .state import AgentState
from .tools import ALL_TOOLS

memory = MemorySaver()

def _build_system_prompt() -> str:
    hoy = date.today()
    fecha_str = f"{hoy.day} de {hoy.strftime('%B')} de {hoy.year}"  
    dia_semana = ["lunes", "martes", "miércoles", "jueves", "viernes", "sábado", "domingo"][hoy.weekday()]
    return (
        f"Eres un asistente financiero personal. "
        f"Hoy es {dia_semana}, {fecha_str}. "
        f"Cuando el usuario pregunte por la fecha actual, el día, el mes o el año, responde directamente con este dato sin usar ninguna herramienta. "
        f"Para consultar datos financieros usa siempre las herramientas disponibles; nunca inventes cifras. "
        f"Responde siempre en español, de forma concisa y empática."
    )

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

    system_prompt = SystemMessage(content=_build_system_prompt())

    def llm_node(state: AgentState) -> dict:
        response = llm.invoke([system_prompt] + state["messages"])
        return {"messages": [response]}

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

    graph_builder.add_edge(NODE_TOOLS, NODE_LLM)

    return graph_builder.compile(checkpointer=memory)

# para probar que funciona el agente en terminal
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
        "¿Cuánto he gastado este trimestre por categoría?",                      
        "¿Cómo ha evolucionado mi gasto en Supermercado los últimos 6 meses?",   
        "Dame el balance de ingresos y gastos del último semestre.",             
        "¿Cómo voy con mi objetivo de Vacaciones de verano?",                    
        "¿Cuáles han sido mis 5 gastos más altos este año?",                     
    ]

    for pregunta in preguntas:
        print(f"👤 Usuario: {pregunta}")
        result = graph.invoke({"messages": [HumanMessage(content=pregunta)]})
        print(f"🤖 Agente:  {result['messages'][-1].content}")