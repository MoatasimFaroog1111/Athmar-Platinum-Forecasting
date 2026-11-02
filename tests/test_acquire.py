import pytest
from platinum.acquire import fetch_one

class DummyResponse:
    def raise_for_status(self):
        pass
    def iter_content(self, chunk_size):
        yield b"<html>blocked</html>"

class DummyClient:
    def get(self, *args, **kwargs):
        return DummyResponse()

def test_html_is_not_accepted_as_source_data(tmp_path):
    with pytest.raises(ValueError, match="Expected"):
        fetch_one("sample", "https://example.org/data.zip", tmp_path, DummyClient())
