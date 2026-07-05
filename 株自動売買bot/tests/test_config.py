import os
import pytest
import config

def test_strategy_params_defaults():
    p = config.StrategyParams()
    assert p.ema_fast == 9 and p.ema_slow == 21
    assert p.stop_loss_pct == 0.02 and p.take_profit_pct == 0.04

def test_risk_params_defaults():
    r = config.RiskParams()
    assert r.max_positions == 5 and r.position_pct == 0.10
    assert r.daily_max_loss_pct == 0.05

def test_symbols_nonempty():
    assert len(config.SYMBOLS) >= 5

def test_load_credentials_reads_env(monkeypatch):
    monkeypatch.setenv("ALPACA_API_KEY", "k")
    monkeypatch.setenv("ALPACA_SECRET_KEY", "s")
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "u")
    c = config.load_credentials()
    assert c.alpaca_key == "k" and c.alpaca_secret == "s" and c.slack_webhook == "u"

def test_load_credentials_missing_raises(monkeypatch):
    monkeypatch.delenv("ALPACA_API_KEY", raising=False)
    with pytest.raises(RuntimeError):
        config.load_credentials()
