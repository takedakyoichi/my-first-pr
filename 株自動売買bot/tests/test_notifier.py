from unittest.mock import MagicMock
from notifier import send_slack

def test_send_slack_posts_payload():
    sess = MagicMock()
    sess.post.return_value = MagicMock(status_code=200)
    ok = send_slack("http://hook", "hello", session=sess)
    assert ok is True
    sess.post.assert_called_once()
    args, kwargs = sess.post.call_args
    assert kwargs["json"] == {"text": "hello"}

def test_send_slack_returns_false_on_exception():
    sess = MagicMock()
    sess.post.side_effect = RuntimeError("network down")
    ok = send_slack("http://hook", "hi", session=sess)
    assert ok is False
