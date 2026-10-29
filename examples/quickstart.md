# Dataset upload quickstart

Download the deterministic sample and create a test key:

```bash
curl -o sample_campaigns.csv http://localhost:8000/v2/sample-dataset
```

Use the key returned by `POST /v2/keys/signup` to upload the CSV:

```bash
curl -X POST http://localhost:8000/v2/datasets \
  -H "Authorization: Bearer $RABBIT_API_KEY" \
  -F "file=@sample_campaigns.csv"
```

The response includes a `dataset_id` in `id` and starts with `status=validating`.
Poll its status and read the validation report:

```bash
curl http://localhost:8000/v2/datasets/$DATASET_ID \
  -H "Authorization: Bearer $RABBIT_API_KEY"
```

Wait until `status` is `ready`; an `invalid` dataset includes stable issue codes
under `validation.errors`. The sample contains 200 touchpoints and conversions.
