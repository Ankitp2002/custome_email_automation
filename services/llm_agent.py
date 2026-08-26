from typing import Union

from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_groq import ChatGroq
from langchain_huggingface import HuggingFaceEmbeddings
from langchain_core.prompts import ChatPromptTemplate
from langchain_core.output_parsers import StrOutputParser


class LLMManager:
    __slot__ = ["available_client"]

    def __init__(self):
        self.available_client: dict[str, Union[ChatGroq, ChatGoogleGenerativeAI]] = {}

    def initialize(self):
        # =====================================================================
        # GROK Models
        # =====================================================================
        self.available_client["llm_gpt_oss_120"] = ChatGroq(
            model="openai/gpt-oss-120b", temperature=0
        )
        self.available_client["llm_vision_llama_17b"] = ChatGroq(
            model="meta-llama/llama-4-scout-17b-16e-instruct", temperature=0.3
        )
        # =====================================================================

        # =====================================================================
        # Gemini Models
        # =====================================================================
        self.available_client["llm_gemini_2_5_flash"] = ChatGoogleGenerativeAI(
            model="gemini-2.5-flash", temperature=0
        )
        # =====================================================================

    def get_client(self, model_name: str) -> Union[ChatGroq, ChatGoogleGenerativeAI]:
        if model_name not in self.available_client:
            raise ValueError(
                f"Model {model_name} is not available. Please check the model name."
            )
        return self.available_client[model_name]

    def invoke_llm(self, client, user_context: str, llm_context: str) -> str:
        """Invokes the LLM using a dynamic task instruction (llm_context)
        and the provided input data/query (user_context).
        """
        prompt_template = ChatPromptTemplate.from_messages(
            [
                (
                    "system",
                    "{instruction}",
                ),
                (
                    "human",
                    "{input_data}",
                ),
            ]
        )
        chain = prompt_template | client | StrOutputParser()
        answer = chain.invoke(
            {
                "instruction": llm_context,
                "input_data": user_context,
            }
        )
        return answer
