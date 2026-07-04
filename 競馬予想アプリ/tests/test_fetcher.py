from pathlib import Path
from keiba import fetcher


class FakeResp:
    def __init__(self, content: bytes, status=200):
        self.content = content
        self.status_code = status

    def raise_for_status(self):
        if self.status_code >= 400:
            raise RuntimeError(f"status {self.status_code}")


class FakeSession:
    def __init__(self, responses):
        self._responses = list(responses)
        self.calls = 0

    def get(self, url, headers=None, timeout=None):
        self.calls += 1
        return self._responses.pop(0)


def test_fetch_writes_cache_and_decodes(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "テスト".encode("euc-jp")
    sess = FakeSession([FakeResp(body)])
    sleeps = []
    out = fetcher.fetch("https://example.com/a", session=sess,
                        sleeper=lambda: sleeps.append(1))
    assert "テスト" in out
    assert sess.calls == 1
    assert len(sleeps) == 1                      # 取得時にスリープした
    assert fetcher.cache_path("https://example.com/a").exists()


def test_fetch_uses_cache_second_time(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "あ".encode("euc-jp")
    sess = FakeSession([FakeResp(body)])
    sleeps = []
    fetcher.fetch("https://example.com/b", session=sess, sleeper=lambda: sleeps.append(1))
    out2 = fetcher.fetch("https://example.com/b", session=sess, sleeper=lambda: sleeps.append(1))
    assert out2 == "あ"
    assert sess.calls == 1                        # 2回目はHTTPを呼ばない
    assert len(sleeps) == 1                        # 2回目はスリープしない


def test_fetch_retries_on_5xx(tmp_path, monkeypatch):
    monkeypatch.setattr(fetcher.config, "CACHE_DIR", tmp_path)
    body = "x".encode("euc-jp")
    sess = FakeSession([FakeResp(b"", 503), FakeResp(body, 200)])
    out = fetcher.fetch("https://example.com/c", session=sess,
                        sleeper=lambda: None, max_retries=3)
    assert out == "x"
    assert sess.calls == 2
