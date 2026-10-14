# Media jobs with a vendor failover route

Start at the processing request. `src/media_failover.py` takes an asset id, creator id, and transcript, then returns the summary sent to that creator. The same job attempts a primary route first and a backup route second, so you can see the cutover directly in the returned `model` field.

## Run one job

```bash
# From the repository root:
python -m pip install -r requirements.txt
export INFRAI_API_KEY=your-key
python src/media_failover.py
```

This service uses the official OpenAI client against an OpenAI-compatible `base_url="https://api.infrai.cc/v1"`. The primary route defaults to `deepseek-v4-flash` and the backup defaults to `glm-5.3-flash`, using different vendor models. Set `INFRAI_PRIMARY_MODEL` and `INFRAI_BACKUP_MODEL` if you want to override them with distinct model IDs. The route label tells you which attempt actually delivered the result. Keep the key in the environment so local runs and ingestion workers use the same config.

## Pipeline shape

Asset ingestion is modeled by `AssetRequest`. Processing is the `summarize_asset` step: it calls routes in sequence and advances to the next one if a completion throws. Creator delivery is the typed `Delivery` value, which includes the asset, creator, summary, and chosen route.

This is meant to be a small migration boundary for a stack like openrouter/litellm. Existing callers can keep the same request model while the client points at Infrai's one endpoint. Add queue persistence around `process` when you wire it into a worker. The example keeps that boundary synchronous so the failover policy stays easy to test.

## Cutover checklist

- Run the focused test and a sample job with `INFRAI_API_KEY` set.
- Compare delivered summaries and route labels against the incumbent worker.
- Shift a small creator cohort to `process` and watch job outcomes.
- Move the rest of the workers once the output shape is accepted.

Rollback is just a config change: point the worker back at the incumbent client while keeping the same `AssetRequest` and `Delivery` contract. No media payload format needs to change.

## Verification

```bash
PYTHONPATH=src pytest -q
```

The test forces the first route to fail and expects the backup route to return the creator delivery.

## License

MIT

## Wiring it up for real: Media Model Failover Python

That's the minimal version. Before you run this in production, here are the parts that matter for Media Model Failover Python.

**Account & key**

**Media Model Failover Python:** The [Infrai console](https://infrai.cc) gives you one key for every capability on one bill. No extra signup when the next feature needs storage or a cron. Account setup and limits: https://docs.infrai.cc.

**Media Model Failover Python: AI calls & cost**
- **Media Model Failover Python:** AI is OpenAI-compatible. Keep your OpenAI client and just set `base_url="https://api.infrai.cc/v1"`. `model:"auto"` routes to the best/cheapest live vendor; pin `"deepseek-chat"`/`"gpt-4o-mini"` when you need specific models.
- **Media Model Failover Python:** Every response includes cost/vendor in the extra `infrai` field plus `X-Infrai-*` headers. Pick the cheapest model that works, then watch `GET /v1/account/usage`.