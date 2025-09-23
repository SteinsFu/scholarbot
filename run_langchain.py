import os
from dotenv import load_dotenv
from langchain.chat_models import init_chat_model
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, MessagesState, StateGraph
from langchain_core.messages import HumanMessage, AIMessage, SystemMessage
from langchain_core.prompts import ChatPromptTemplate, MessagesPlaceholder

from typing import Sequence
from langchain_core.messages import BaseMessage
from langgraph.graph.message import add_messages
from typing_extensions import Annotated, TypedDict

from pdf_utils import pdf_url_to_text



SUMMARY_PROMPT = f"""
You are an expert research paper analyst. Your task is to analyze academic papers and provide comprehensive summaries.

Here is the extracted content of the paper: 
<paper>
{{context}}
</paper>

When analyzing a research paper, provide:

1. **Title and Authors** (if available)
2. **Abstract Summary** (2-3 sentences)
3. **Key Research Questions/Objectives**
4. **Methodology** (brief description of approach)
5. **Main Findings/Results** (3-5 key points)
6. **Significance/Impact** (why this research matters)
7. **Limitations** (if mentioned)
8. **Key Terms/Concepts** (important terminology)

Format your response clearly with headers and bullet points for easy reading.
Be concise but comprehensive. Focus on the most important aspects that would help someone understand the paper's contribution to the field.

Please output in the user-specified language: {{language}}.
"""



class State(TypedDict):
    messages: Annotated[Sequence[BaseMessage], add_messages]
    context: str
    language: str


class LangChainCaller:
    def __init__(self):
        load_dotenv()
        os.environ["LANGCHAIN_TRACING"] = "true"    # Enable LangChain tracing
        self.model = init_chat_model("chatgpt-4o-latest", model_provider="openai")
        self.app = self.init_app_with_memory()

    def init_app_with_memory(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", SUMMARY_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # create a function to call the model
        def call_model(state: State):
            prompt = prompt_template.invoke(state)  # create the prompt
            response = self.model.invoke(prompt)    # call the model
            return {"messages": response}
        # create a workflow
        workflow = StateGraph(state_schema=State)
        workflow.add_node("model", call_model)          # create a node
        workflow.add_edge(START, "model")               # add an edge from START to model
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        return app

    def call(self, prompt: str, context: str = "", language: str = "English"):
        config = {"configurable": {"thread_id": "abc123"}}    # conversation thread id
        input_messages = [HumanMessage(content=prompt)]
        output = self.app.invoke({
            "messages": input_messages,
            "context": context,
            "language": language,
        }, config)
        return output["messages"][-1].content




if __name__ == "__main__":
    prompt = "summarize this paper: "
    pdf_url = "https://arxiv.org/abs/2505.11128"
    
    # Extract and optimize PDF text
    pdf_url = pdf_url.replace("arxiv.org/abs", "arxiv.org/pdf") # replace abs with pdf for arxiv urls
    pdf_result = pdf_url_to_text(pdf_url, optimize=True, strategy="smart", max_tokens=4000)
    context = pdf_result["text"]
    
    # Display optimization info
    print("\n" + "="*50)
    print("Optimized Text:")
    print("="*50)
    print(context)
    print("="*50 + "\n")
    opt_info = pdf_result["optimization_info"]
    print(f"Optimization applied: {opt_info.get('strategy', 'none')}")
    if opt_info.get('optimized', False):
        print(f"Token reduction: {opt_info.get('token_reduction', 0)} tokens ({opt_info.get('reduction_percentage', 0):.1f}%)")
        print(f"Cost savings: ${opt_info.get('cost_savings', 0):.4f}")
        print(f"Used AI: {opt_info.get('used_ai', False)}")
    
    # caller = LangChainCaller()
    # print("\n" + "="*50)
    # print("PAPER SUMMARY:")
    # print("="*50)
    # print(caller.call(prompt, context, "English"))