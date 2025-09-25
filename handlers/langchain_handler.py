import os
import time
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
from langchain_google_genai import ChatGoogleGenerativeAI

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



class LangChainHandler:
    def __init__(self):
        load_dotenv()
        os.environ["LANGSMITH_TRACING"] = "true"    # Enable LangChain tracing
        self.set_model(self.available_providers[0]) # set the first available provider
        self.app = self.init_app_with_memory()

    @property
    def available_providers(self):
        available_providers = []
        if os.environ.get("OPENAI_API_KEY"):
            available_providers.append("OpenAI")
        if os.environ.get("GOOGLE_API_KEY"):
            available_providers.append("Google Gemini")
        if os.environ.get("GOOGLE_APPLICATION_CREDENTIALS"):
            print(os.environ.get("GOOGLE_APPLICATION_CREDENTIALS")) 
            available_providers.append("Google VertexAI")
        if os.environ.get("ANTHROPIC_API_KEY"):
            available_providers.append("Anthropic")
        if not available_providers:
            available_providers.append(None)
        return available_providers

    def list_available_models(self, provider: str):
        """
        Returns a list of common available models for the specified provider.
        
        Args:
            provider (str): The provider name (e.g., "OpenAI", "Google Gemini", "Google VertexAI", "Anthropic")
            
        Returns:
            list: A list of available model names for the provider
            
        Raises:
            ValueError: If the provider is not supported or not available
        """
        # Check if provider is available (has API key configured)
        if provider not in self.available_providers:
            raise ValueError(f"Provider '{provider}' is not available. Available providers: {self.available_providers}")
        openai_models = [
            "chatgpt-4o-latest",
            "gpt-3.5-turbo",
            "gpt-4",
            "gpt-4-turbo",
            "gpt-4.1",
            "gpt-4.1-mini",
            "gpt-4.1-nano",
            "gpt-4o",
            "gpt-4o-mini",
            "gpt-5",
            "gpt-5-chat-latest",
            "gpt-5-codex",
            "gpt-5-mini",
            "gpt-5-nano",
        ]
        gemini_models = [
            "gemini-2.5-pro",
            "gemini-2.5-flash",
            "gemini-2.5-flash-lite",
            "gemini-2.0-flash",
            "gemini-2.0-flash-lite",
        ]
        anthropic_models = [
            "claude-opus-4-1-20250805",
            "claude-opus-4-20250514",
            "claude-sonnet-4-20250514",
            "claude-3-7-sonnet-latest",
            "claude-3-5-haiku-latest",
            "claude-3-haiku-20240307",
        ]
        # Common models for each provider
        provider_models = {
            "OpenAI": openai_models,
            "Google Gemini": gemini_models,
            "Google VertexAI": gemini_models,
            "Anthropic": anthropic_models,
        }
        return provider_models.get(provider, [])
    
    def get_default_model(self, provider: str):
        if provider == "OpenAI":
            return "chatgpt-4o-latest"
        elif provider == "Google Gemini" or provider == "Google VertexAI":
            return "models/gemini-2.5-flash"
        elif provider == "Anthropic":
            return "claude-3-7-sonnet-latest"
        else:
            return None

    def set_model(self, provider: str, model: str = None):
        if not provider:
            raise ValueError("Please at least set one API keys in the .env file: [OPENAI_API_KEY, GOOGLE_API_KEY, GOOGLE_APPLICATION_CREDENTIALS, ANTHROPIC_API_KEY]")
        
        # Set default models if no specific model is provided [[memory:4396816]]
        if provider == "OpenAI":
            model_provider = "openai"
            selected_model = model if model else self.get_default_model(provider)
            self.model = init_chat_model(selected_model, model_provider=model_provider)
        elif provider == "Anthropic":
            model_provider = "anthropic"
            selected_model = model if model else self.get_default_model(provider)
            self.model = init_chat_model(selected_model, model_provider=model_provider)
        elif provider in ["Google Gemini", "Google VertexAI"]:
            selected_model = model if model else "gemini-2.5-flash"
            self.model = ChatGoogleGenerativeAI(model=selected_model)
        else:
            raise ValueError(f"Unsupported provider: {provider}")
        print(f"Using model: {selected_model} from provider: {provider}")

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
            response = self.model.invoke(prompt)    # call the model
            return {"messages": response}
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



