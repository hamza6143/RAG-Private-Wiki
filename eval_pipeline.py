import sys
import types
import os
import asyncio
import time


# =====================================================================
# RAGAS RUNTIME SHIMS
# ragas.llms.base hard-imports two langchain_community symbols that no
# longer ship with the package. Stub them before any ragas import.
# =====================================================================
def _stub(mod_path: str, **attrs):
    if mod_path not in sys.modules:
        m = types.ModuleType(mod_path)
        for k, v in attrs.items():
            setattr(m, k, v)
        sys.modules[mod_path] = m

_stub("langchain_community.chat_models.vertexai",
      ChatVertexAI=type("ChatVertexAI", (object,), {}))
_stub("langchain_community.llms.vertexai",
      VertexAI=type("VertexAI", (object,), {}))

try:
    import langchain_community.llms as _lc_llms
    if not hasattr(_lc_llms, "VertexAI"):
        _lc_llms.VertexAI = type("VertexAI", (object,), {})
except Exception:
    pass
# =====================================================================

import json
import pandas as pd
from dotenv import load_dotenv

from google import genai as google_genai
import instructor

# collections metrics have their own base class (BaseMetric) that is
# completely separate from ragas.metrics.base.Metric.  They DO NOT work
# with ragas.evaluate() — that function's isinstance(m, Metric) guard
# rejects them.  Instead call abatch_score() directly on each metric.
from ragas.metrics.collections import (
    Faithfulness,
    AnswerRelevancy,
    ContextPrecision,
    ContextRecall,
)
from ragas.llms.adapters.instructor import InstructorLLM
from ragas.embeddings.google_provider import GoogleEmbeddings
from llama_index.embeddings.google_genai import GoogleGenAIEmbedding
from ragas.embeddings.base import BaseRagasEmbedding


# ---------------------------------------------------------------------------
# Rate-limit throttle
#
# The free Gemini tier allows 5 RPM.  We serialise every metric call and
# insert a 13-second sleep between them so we stay well under the cap.
# Four metrics × N test-cases means N × 4 calls, each 13 s apart.
# ---------------------------------------------------------------------------
_RATE_LIMIT_SLEEP = 13  # seconds between LLM calls


def _build_llm(api_key: str):
    """
    Create an async-capable InstructorLLM for google.genai.Client.

    The key difference from llm_factory():
    - We pass use_async=True to instructor.from_genai() to get AsyncInstructor
    - We wrap it directly in InstructorLLM with provider='google'
    - This enables agenerate() which the collections metrics require
    """
    client = google_genai.Client(api_key=api_key)
    
    # Get an async-capable instructor-wrapped client
    # use_async=True returns AsyncInstructor which supports async chat.create()
    async_instructor_client = instructor.from_genai(client, use_async=True)
    
    # Wrap in ragas' InstructorLLM for collections metrics
    return InstructorLLM(
        client=async_instructor_client,
        model="gemini-2.5-flash",
        provider="google",
    )

# 1. Create an adapter that forces Ragas to use LlamaIndex's embedding model
class LlamaIndexRagasEmbeddingAdapter(BaseRagasEmbedding):
    def __init__(self, embed_model):
        super().__init__()
        self.embed_model = embed_model

    def embed_text(self, text: str) -> list[float]:
        return self.embed_model.get_text_embedding(text)

    async def aembed_text(self, text: str) -> list[float]:
        return await self.embed_model.aget_text_embedding(text)

    def embed_texts(self, texts: list[str]) -> list[list[float]]:
        return self.embed_model.get_text_embedding_batch(texts)

    async def aembed_texts(self, texts: list[str]) -> list[list[float]]:
        return await self.embed_model.aget_text_embedding_batch(texts)


def _build_embeddings(api_key: str):
    llama_embed_model = GoogleGenAIEmbedding(
        model_name="gemini-embedding-2-preview",
        api_key=api_key
    )
    return LlamaIndexRagasEmbeddingAdapter(llama_embed_model)


async def _score_case(metrics, case_inputs: dict) -> dict:
    """
    Run all four metrics on a single test case, one at a time with
    rate-limit sleeps between each call.

    Required keys per metric:
      Faithfulness      : user_input, response, retrieved_contexts
      AnswerRelevancy   : user_input, response
      ContextPrecision  : user_input, reference, retrieved_contexts
      ContextRecall     : user_input, retrieved_contexts, reference
    """
    scores = {}
    metric_inputs = {
        "Faithfulness": {
            "user_input":        case_inputs["user_input"],
            "response":          case_inputs["response"],
            "retrieved_contexts": case_inputs["retrieved_contexts"],
        },
        "AnswerRelevancy": {
            "user_input": case_inputs["user_input"],
            "response":   case_inputs["response"],
        },
        "ContextPrecision": {
            "user_input":        case_inputs["user_input"],
            "reference":         case_inputs["reference"],
            "retrieved_contexts": case_inputs["retrieved_contexts"],
        },
        "ContextRecall": {
            "user_input":        case_inputs["user_input"],
            "retrieved_contexts": case_inputs["retrieved_contexts"],
            "reference":         case_inputs["reference"],
        },
    }

    for metric in metrics:
        name = type(metric).__name__
        result = await metric.ascore(**metric_inputs[name])
        scores[name] = result.value
        await asyncio.sleep(_RATE_LIMIT_SLEEP)

    return scores


def run_uploaded_evaluation_workflow(
    org_namespace: str,
    user_role: str,
    json_bytes: bytes,
    query_pipeline_func,
) -> pd.DataFrame:
    load_dotenv()

    api_key = os.environ["GEMINI_API_KEY"]

    llm = _build_llm(api_key)
    embeddings = _build_embeddings(api_key)

    metrics = [
        Faithfulness(llm=llm),
        AnswerRelevancy(llm=llm, embeddings=embeddings),
        ContextPrecision(llm=llm),
        ContextRecall(llm=llm),
    ]

    test_cases = json.loads(json_bytes.decode("utf-8"))

    rows = []
    for case in test_cases:
        q_text  = case.get("question")
        gt_text = case.get("ground_truth")
        if not q_text or not gt_text:
            continue

        response_payload = query_pipeline_func(
            org_namespace=org_namespace, user_role=user_role, query=q_text
        )
        contexts = [node.node.get_content() for node in response_payload.source_nodes]

        case_inputs = {
            "user_input":         q_text,
            "reference":          gt_text,
            "response":           response_payload.response,
            "retrieved_contexts": contexts,
        }

        # asyncio.run() is safe here because query_pipeline_func is synchronous.
        # If you ever move to an async app entrypoint, switch to `await _score_case(...)`.
        scores = asyncio.run(_score_case(metrics, case_inputs))

        rows.append({
            "question":          q_text,
            "ground_truth":      gt_text,
            "answer":            response_payload.response,
            "contexts":          contexts,
            "faithfulness":      scores["Faithfulness"],
            "answer_relevancy":  scores["AnswerRelevancy"],
            "context_precision": scores["ContextPrecision"],
            "context_recall":    scores["ContextRecall"],
        })

    return pd.DataFrame(rows)