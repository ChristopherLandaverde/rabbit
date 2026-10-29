# Dataset playground

Start with a deterministic 200-row CSV. This endpoint is public and does not
need an API key:

```bash
curl -o sample_campaigns.csv http://localhost:8000/v2/sample-dataset
```

The response is `text/csv` and cacheable for one day. Create a test key with
`POST /v2/keys/signup`, then upload the downloaded file:

```bash
curl -X POST http://localhost:8000/v2/datasets \
  -H "Authorization: Bearer $RABBIT_API_KEY" \
  -F "file=@sample_campaigns.csv"
```

Use the returned `id` with `GET /v2/datasets/{id}` to poll validation. A `ready`
response includes row counts and a schema fingerprint; an `invalid` response
means validation found problems and includes machine-readable error codes. See
[the quickstart recipe](../../examples/quickstart.md) for the complete local flow.
