"""Run the GA4 BigQuery importer CLI offline on the bundled fixture rows.

No Google API is called: a stand-in client (tests/fixtures/ga4_bigquery.py)
returns hand-built rows in GA4 export shape with made-up IDs. The output is
what the README's "Live import from GA4 BigQuery" section shows.

    python scripts/ga4_fixture_demo.py
"""

import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))

from src.importers.ga4_bigquery import main  # noqa: E402
from tests.fixtures.ga4_bigquery import FakeBigQueryClient  # noqa: E402

if __name__ == "__main__":
    argv = sys.argv[1:] or [
        "--project", "demo-project-123",
        "--dataset", "analytics_123456789",
        "--start", "20240301",
        "--end", "20240303",
        "--conversion-event", "purchase",
        "--out", "ga4_touchpoints.csv",
    ]
    sys.exit(main(argv, client=FakeBigQueryClient()))
