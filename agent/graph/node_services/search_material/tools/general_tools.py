import logging

from typing import Dict, Any, Annotated, Literal
from pydantic import BaseModel, Field

from langchain_core.tools import tool as langchain_tool
from langgraph.prebuilt import InjectedState

from agent.graph.node_services.health_advice.health_advice import HealthAdviceNode 
from agent.graph.node_services.health_advice.subgraph.state import SubgraphHealthAdviceState

logger = logging.getLogger(__name__)

#======================================================================
# TOOL: Tìm thêm triệu chứng  
#======================================================================

class SymptomCollectorToolInput(BaseModel):
    state: Annotated[SubgraphHealthAdviceState, InjectedState]
    question: str = Field(..., description="Câu hỏi để thu thập thêm triệu chứng.")

@HealthAdviceNode.tool_register()
@langchain_tool(
    description="""Thu thập thêm triệu chứng
    
    Nếu cảm thấy cần thu thập thêm thông tin triệu chứng thì truyền vào symptom_collector_tool chuỗi (str) câu hỏi để thu thập thêm triệu chứng. 
    Mẫu: 
    - "Bạn hãy mô tả thêm về {triệu chứng}. Có phải bạn cảm thấy {tính chất/mức độ} hoặc xảy ra ở {vị trí/thời điểm} không?"
    - "Ngoài {triệu chứng chính}, bạn có gặp thêm tình trạng như {triệu chứng phụ} hoặc {biểu hiện khác} không?"
    """,
    args_schema=SymptomCollectorToolInput
)
async def symptom_collector_tool(
    state: Annotated[SubgraphHealthAdviceState, InjectedState],
    question: str
) -> str:
    """Thu thập thêm triệu chứng.

    Args:
        state (Annotated[SubgraphHealthAdviceState, InjectedState]): The current subgraph execution state.
        question (str): Câu hỏi để thu thập thêm triệu chứng

    Returns:
        str: Câu hỏi để thu thập thêm triệu chứng
    """
    
    return question

#======================================================================
# TOOL: Chẩn đoán
#======================================================================

class DiagnosisEngineToolInput(BaseModel):
    state: Annotated[SubgraphHealthAdviceState, InjectedState]
    diagnosis: str = Field(..., description="Báo cáo chẩn đoán.")
    
@HealthAdviceNode.tool_register()
@langchain_tool(
    description="""Báo cáo chẩn đoán

    Nếu dưới 3 bệnh lý đã có thể được khoanh vùng (nghi ngờ >90%), thì truyền vào diagnosis_engine_tool chuỗi (str) báo cáo chẩn đoán bệnh lý một cách rõ ràng.
    """,
    args_schema=DiagnosisEngineToolInput
)
async def diagnosis_engine_tool(
    state: Annotated[SubgraphHealthAdviceState, InjectedState],
    diagnosis: str
) -> str:
    """Báo cáo chẩn đoán.

    Args:
        state (Annotated[SubgraphHealthAdviceState, InjectedState]): The current subgraph execution state.
        diagnosis (str): Báo cáo chẩn đoán.

    Returns:
        str: Báo cáo chẩn đoán.
    """

    return diagnosis