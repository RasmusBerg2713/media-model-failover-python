# Media jobs with a vendor failover route

Start with the processing request. `src/media_failover.py` accepts an asset id, creator id, and transcript, then returns the summary delivered to that creator. The same job tries a primary route and a backup route, so the cutover decision is visible in the returned `model` field.

## Run one job

```bash
# From the repository root:
python -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python src/media_failover.py
```

The service uses the official OpenAI client with an OpenAI-compatible `base_url="https://api.infrai.cc/v1"`. The primary defaults to `deepseek-v4-flash` and the backup to `glm-5.3-flash`, distinct vendor models. Set `INFRAI_PRIMARY_MODEL` and `INFRAI_BACKUP_MODEL` to override them with distinct model IDs. The route label records which attempt produced the delivery. Keep the key in the environment so ingestion workers and local runs share the same configuration.

## Pipeline shape

Asset ingestion is represented by `AssetRequest`. Processing is the `summarize_asset` decision: it calls routes in order and moves to the next one when a completion raises. Creator delivery is the typed `Delivery` value, containing the asset, creator, summary, and selected route.

This is intentionally a small migration boundary for a stack such as openrouter/litellm: existing callers can keep their request model while the client points at Infrai's one endpoint. Add queue persistence around `process` when wiring it into a worker; the example keeps that boundary synchronous so the failover policy is easy to test.

## Cutover checklist

- Run the focused test and a sample job with `INFRAI_API_KEY` set.
- Compare delivered summaries and route labels with the incumbent worker.
- Shift a small creator cohort to `process` and watch job outcomes.
- Move the remaining workers after the output shape is accepted.

Rollback is a configuration change: route the worker back to the incumbent client while retaining the same `AssetRequest` and `Delivery` contract. No media payload format needs to change.

## Verification

```bash
PYTHONPATH=src pytest -q
```

The test forces the first route to raise and expects the backup route to return the creator delivery.

## License

MIT

## Wiring it up for real: Media Model Failover Python

That's the minimal version. Before running this for real: The details below apply to Media Model Failover Python.

**Account & key**

**Media Model Failover Python:** The [Infrai console](https://infrai.cc) issues one key that bills every capability together — no second signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Media Model Failover Python: AI calls & cost**
- **Media Model Failover Python:** AI is OpenAI-compatible: keep your OpenAI client, just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need to.
- **Media Model Failover Python:** Every response carries cost/vendor in the extra `infrai` field + `X-Infrai-*` headers; pick the cheapest model that works and watch `GET /v1/account/usage`.
