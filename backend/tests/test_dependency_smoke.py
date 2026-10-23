"""Fast, deterministic checks for the backend's compiled/runtime dependencies."""
from io import BytesIO


def test_runtime_dependencies_and_serialization():
    """Catch broken installs before application startup or data refresh."""
    import fastapi
    import numpy as np
    import pandas as pd
    import psxdata
    import pyarrow as pa
    import pyarrow.parquet as pq
    from bs4 import BeautifulSoup
    from lxml import etree

    assert fastapi.__version__
    assert np.array([1, 2]).tolist() == [1, 2]
    assert pd.DataFrame({"value": [1, 2]}).shape == (2, 1)
    assert psxdata is not None
    assert etree.LXML_VERSION
    assert BeautifulSoup("<p>ready</p>", "lxml").get_text() == "ready"

    frame = pd.DataFrame({"symbol": ["TEST"], "price": [123.45]})
    output = BytesIO()
    table = pa.Table.from_pandas(frame, preserve_index=False)
    pq.write_table(table, output)
    output.seek(0)
    restored = pq.read_table(output).to_pandas()

    assert restored.to_dict(orient="records") == [{"symbol": "TEST", "price": 123.45}]
