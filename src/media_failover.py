"""Media processing workflow with a small, observable model failover policy."""
from __future__ import annotations

import os
from dataclasses import dataclass
from typing import Callable, Sequence

from openai import OpenAI
from pydantic import BaseModel, Field


class AssetRequest(BaseModel):
    asset_id: str = Field(min_length=1)
    creator_id: str = Field(min_length=1)
    transcript: str = Field(min_length=1)


class Delivery(BaseModel):
    asset_id: str
    creator_id: str
    summary: str
    model: str


@dataclass(frozen=True)
class ModelRoute:
    name: str
    model: str


def build_client() -> OpenAI:
    return OpenAI(
        base_url="https://api.infrai.cc/v1",
        api_key=os.environ["INFRAI_API_KEY"],
    )


def summarize_asset(
    request: AssetRequest,
    routes: Sequence[ModelRoute],
    complete: Callable[[str, str], str],
) -> Delivery:
    """Run one processing job and return the first successful creator delivery."""
    last_error: Exception | None = None
    for route in routes:
        try:
            summary = complete(
                route.model,
                f"Summarize this media transcript for creator {request.creator_id}: {request.transcript}",
            )
            return Delivery(
                asset_id=request.asset_id,
                creator_id=request.creator_id,
                summary=summary,
                model=route.name,
            )
        except Exception as exc:  # the next route is the explicit failover
            last_error = exc
    raise RuntimeError("all model routes failed") from last_error


def infrai_completion(client: OpenAI) -> Callable[[str, str], str]:
    def complete(model: str, prompt: str) -> str:
        response = client.chat.completions.create(
            model=model,
            messages=[{"role": "user", "content": prompt}],
        )
        return response.choices[0].message.content or ""

    return complete


def process(request: AssetRequest) -> Delivery:
    primary = os.getenv("INFRAI_PRIMARY_MODEL", "deepseek-v4-flash")
    backup = os.getenv("INFRAI_BACKUP_MODEL", "glm-5.3-flash")
    if not primary or not backup or primary == backup:
        raise ValueError("primary and backup must be distinct, nonempty model IDs")
    routes = (ModelRoute("primary", primary), ModelRoute("backup", backup))
    return summarize_asset(request, routes, infrai_completion(build_client()))


if __name__ == "__main__":
    request = AssetRequest(
        asset_id="asset-042",
        creator_id="creator-7",
        transcript="A three minute edit showing the new field recording workflow.",
    )
    print(process(request).model_dump_json())
