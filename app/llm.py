from openai import AsyncOpenAI

from app.config import Settings
from app.models import (
    EntityCandidate,
    ExtractedEntity,
    ExtractionResult,
    ResolutionDecision,
)


EXTRACTION_SYSTEM_PROMPT = """
You convert durable natural-language knowledge into a small evidence-backed graph.

Extract entities that can be referred to again and claims connecting them. Entity
kinds and claim predicates are open-ended; do not restrict them to an ontology.
Normalize predicates to concise UPPER_SNAKE_CASE verbs such as USES, REPLACED,
DEPENDS_ON, TARGETS, or MOTIVATED_BY.

Rules:
- Preserve the meaning and scope of the input. Do not infer unsupported facts.
- Give every entity a unique temp_id and use those IDs in claims.
- Include useful aliases explicitly supported by the text or common unambiguous
  variants, but do not collapse ambiguous entities.
- evidence_quote must be an exact substring of the input.
- Use object_literal only for values that are not durable entities.
- Set supersedes_existing only when replacement, migration, cancellation, or a
  correction is explicit in the input.
- If there is no durable knowledge, return empty lists.
""".strip()


class KnowledgeLLM:
    def __init__(self, settings: Settings) -> None:
        kwargs: dict[str, str] = {"api_key": settings.openai_api_key}
        if settings.openai_base_url:
            kwargs["base_url"] = settings.openai_base_url
        self._client = AsyncOpenAI(**kwargs)
        self._model = settings.openai_model
        self._embedding_model = settings.openai_embedding_model
        self._embedding_dimensions = settings.embedding_dimensions

    async def extract(self, text: str) -> ExtractionResult:
        completion = await self._client.chat.completions.parse(
            model=self._model,
            temperature=0,
            messages=[
                {"role": "system", "content": EXTRACTION_SYSTEM_PROMPT},
                {"role": "user", "content": text},
            ],
            response_format=ExtractionResult,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            raise ValueError("The extraction model did not return structured output")
        return result

    async def resolve(
        self,
        mention: ExtractedEntity,
        candidates: list[EntityCandidate],
        source_text: str,
    ) -> ResolutionDecision:
        candidate_lines = "\n".join(
            f"- id={candidate.id}; name={candidate.name}; kind={candidate.kind}; "
            f"summary={candidate.summary}; aliases={candidate.aliases}"
            for candidate in candidates
        )
        prompt = f"""
Decide whether the extracted mention refers to one existing entity.

Source text:
{source_text}

Mention:
name={mention.name}
kind={mention.kind}
summary={mention.summary}
aliases={mention.aliases}

Existing candidates:
{candidate_lines}

Return LINK only when the identity is clear from context. Return NEW when the
mention is clearly a different entity. Return UNRESOLVED when evidence is
ambiguous. If LINK, candidate_id must exactly match one listed ID.
""".strip()
        completion = await self._client.chat.completions.parse(
            model=self._model,
            temperature=0,
            messages=[{"role": "user", "content": prompt}],
            response_format=ResolutionDecision,
        )
        result = completion.choices[0].message.parsed
        if result is None:
            raise ValueError("The resolution model did not return structured output")
        valid_ids = {candidate.id for candidate in candidates}
        if result.action == "LINK" and result.candidate_id not in valid_ids:
            return ResolutionDecision(
                action="UNRESOLVED",
                confidence=0,
                reason="Resolver returned an unknown candidate ID",
            )
        return result

    async def embed(self, text: str) -> list[float]:
        response = await self._client.embeddings.create(
            model=self._embedding_model,
            input=text,
            dimensions=self._embedding_dimensions,
        )
        return response.data[0].embedding
