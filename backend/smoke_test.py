"""Small dependency check for a clean Python 3.13 backend install."""

def main() -> None:
    import fastapi
    import numpy
    import pandas
    import pyarrow as pa
    import pyarrow.parquet as pq
    import psxdata
    from bs4 import BeautifulSoup
    from lxml import etree
    from io import BytesIO

    assert BeautifulSoup("<p>ok</p>", "lxml").get_text() == "ok"
    table = pa.table({"value": [1, 2]})
    output = BytesIO()
    pq.write_table(table, output)
    output.seek(0)
    assert pq.read_table(output).to_pydict() == {"value": [1, 2]}
    print("Backend dependency smoke test passed")
    print(f"fastapi={fastapi.__version__} numpy={numpy.__version__} pandas={pandas.__version__}")
    print(f"pyarrow={pa.__version__} psxdata={getattr(psxdata, '__version__', 'installed')} lxml={etree.LXML_VERSION}")


if __name__ == "__main__":
    main()
