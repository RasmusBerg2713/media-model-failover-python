import pytest

from media_failover import AssetRequest, ModelRoute, process, summarize_asset


def test_backup_route_delivers_when_primary_rejects():
    request = AssetRequest(asset_id="a1", creator_id="c1", transcript="field notes")
    seen: list[str] = []

    def complete(model: str, prompt: str) -> str:
        seen.append(model)
        if len(seen) == 1:
            raise RuntimeError("primary unavailable")
        return "A concise edit summary."

    delivery = summarize_asset(
        request,
        (ModelRoute("primary", "deepseek-v4-flash"), ModelRoute("backup", "glm-5.3-flash")),
        complete,
    )

    assert delivery.model == "backup"
    assert delivery.summary == "A concise edit summary."
    assert seen == ["deepseek-v4-flash", "glm-5.3-flash"]


def test_process_rejects_identical_models(monkeypatch):
    monkeypatch.setenv("INFRAI_PRIMARY_MODEL", "same")
    monkeypatch.setenv("INFRAI_BACKUP_MODEL", "same")
    with pytest.raises(ValueError, match="distinct"):
        process(AssetRequest(asset_id="a1", creator_id="c1", transcript="field notes"))
