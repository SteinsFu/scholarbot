import os
import time
import vertexai
import google.generativeai as genai
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

from utils.text_optimizer import TextOptimizer
from handlers.jina_handler import JinaHandler


ROLE_PROMPT = "You are an expert research paper analyst. Your task is to analyze academic papers and answer the user's question."


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

Please output in the user-specified language: {{language}}

Here is the user's question: {{query}}
"""


RELATED_PAPERS_PROMPT = f"""
# Task

You are given:  
1. **Target Paper Metadata** (in <paper> tag) – information about the main paper of interest.  
2. **Related Papers Metadata** (in <related_papers> tag) – a list of papers that may be related to the target paper.  
3. **Context Memory** – you have already summarized the target paper in a previous step/conversation.  

Your task is to analyze the relationships between the target paper and the related papers.  
Use **both** the provided metadata **and** your prior summary (memory) of the target paper to guide your reasoning.  
Then, rank the related papers according to their similarity and importance to the target paper.  

---

## Ranking Guidelines

Rank the related papers in descending order of relevance to the target paper using the following criteria (and any additional reasonable factors you infer):  

1. **Direct Dependency (Highest Priority):**  
   - If the target paper directly builds upon or extends another (e.g., uses it as a backbone, framework, or foundational method), that paper should rank highest.  

2. **Conceptual or Methodological Closeness:**  
   - Papers that share highly similar methodologies, frameworks, or application domains should rank above tangentially related works.  

3. **Baseline or Benchmark Role:**  
   - If the target paper primarily uses another paper as a baseline for comparison (not as a backbone), rank it lower than direct dependencies but higher than peripheral references.  

4. **Peripheral/Background References (Lowest Priority):**  
   - Papers only tangentially related or providing background context rank lowest.  

---

## Output Format

Return a ranked list of the related papers. For each paper, include:  

- **Title** (linked to the paper's URL) 
- **Explanation:** A concise description of why it is relevant and how it relates to the target paper.  
- **Justification for Ranking:** Why it was placed in this position according to the ranking criteria.  

At the end, output a **Final Ranking Summary** like the following:
**Final Ranking Summary**
1. ✅ Paper 1 – brief reason why it is relevant
2. ✅ Paper 2 - brief reason why it is relevant
3. ✅ Paper 3 - brief reason why it is relevant
4. 🔁 Paper 4 - brief reason why it is less relevant
5. 🔁 Paper 5 - brief reason why it is less relevant
6. ❌ Paper 6 - brief reason why it is not relevant
7. ❌ Paper 7 - brief reason why it is not relevant
...

## Inputs:
Paper content:  
<paper>  
{{main_paper}}
</paper>  

Related papers:  
<related_papers>
{{related_papers}}  
</related_papers>  

Please output in the user-specified language: {{language}}.
"""



# class State(TypedDict):
#     messages: Annotated[Sequence[BaseMessage], add_messages]
#     context: str
#     language: str


class LangChainHandler:
    def __init__(self):
        load_dotenv()
        os.environ["LANGCHAIN_TRACING"] = "true"    # Enable LangChain tracing
        os.environ['GOOGLE_APPLICATION_CREDENTIALS'] = "/Users/momoka_furuhashi/work/2025_inui/tu-vertex-ai-prod-2fd3bb917540.json" ## Your creadit path
        # self.model = init_chat_model("chatgpt-4o-latest", model_provider="openai")
        ### geminiに対応
        gemini_model = genai.GenerativeModel("models/gemini-2.5-flash")
        self.model = gemini_model
        
        self.app = self.init_app_with_memory()

    def init_app_with_memory(self):
        prompt_template = ChatPromptTemplate.from_messages(
            [
                ("system", ROLE_PROMPT),
                MessagesPlaceholder(variable_name="messages"),
            ]
        )
        # create a function to call the model
        def call_model(state: MessagesState):
            prompt = prompt_template.invoke(state)  # create the prompt
            # response = self.model.invoke(prompt)    # call the model
            # return {"messages": response}
            response = self.model.generate_content(prompt) # geminiに対応
            return {"messages": [AIMessage(content=response.text)]}  # geminiに対応
        
        # create a workflow
        workflow = StateGraph(state_schema=MessagesState)
        workflow.add_node("model", call_model)          # create a node
        workflow.add_edge(START, "model")               # add an edge from START to model
        memory = MemorySaver()
        app = workflow.compile(checkpointer=memory)
        return app

    def summarize_paper(self, prompt: str, thread_id: str, context: str = "", language: str = "English"):
        config = {"configurable": {"thread_id": thread_id}}    # conversation thread id
        prompt = SUMMARY_PROMPT.format(query=prompt, context=context, language=language)
        input_messages = [HumanMessage(content=prompt)]
        output = self.app.invoke({
            "messages": input_messages,
        }, config)
        return output["messages"][-1].content

    def rank_related_papers(self, thread_id: str, main_paper: str, related_papers: str, language: str = "English"):
        config = {"configurable": {"thread_id": thread_id}}    # conversation thread id
        prompt = RELATED_PAPERS_PROMPT.format(main_paper=main_paper, related_papers=related_papers, language=language)
        input_messages = [HumanMessage(content=prompt)]
        output = self.app.invoke({
            "messages": input_messages,
        }, config)
        return output["messages"][-1].content

    def call(self, prompt: str, thread_id: str):
        config = {"configurable": {"thread_id": thread_id}}    # conversation thread id
        input_messages = [HumanMessage(content=prompt)]
        output = self.app.invoke({
            "messages": input_messages,
        }, config)
        return output["messages"][-1].content



