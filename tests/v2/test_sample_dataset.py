"""Public deterministic sample dataset endpoint."""


def test_sample_dataset_is_public_and_byte_for_byte_deterministic(client):
    first = client.get("/v2/sample-dataset")
    second = client.get("/v2/sample-dataset")
    assert first.status_code == second.status_code == 200
    assert first.content == second.content
    assert first.headers["content-type"].startswith("text/csv")
    assert first.headers["cache-control"] == "public, max-age=86400"
    assert int(first.headers["content-length"]) == len(first.content)
    import pandas as pd

    assert len(pd.read_csv(__import__("io").BytesIO(first.content))) == 200
