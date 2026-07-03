from __future__ import annotations

from pulumi_truenas.secrets import resolve_api_key


def test_config_value_wins(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUENAS_API_KEY", "from-env")
    dotenv = tmp_path / ".env"
    dotenv.write_text("TRUENAS_API_KEY=from-dotenv\n")
    key = resolve_api_key(config_value="from-config", dotenv_path=dotenv)
    assert key == "from-config"


def test_env_beats_dotenv(monkeypatch, tmp_path):
    monkeypatch.setenv("TRUENAS_API_KEY", "from-env")
    dotenv = tmp_path / ".env"
    dotenv.write_text("TRUENAS_API_KEY=from-dotenv\n")
    assert resolve_api_key(dotenv_path=dotenv) == "from-env"


def test_dotenv_fallback(monkeypatch, tmp_path):
    monkeypatch.delenv("TRUENAS_API_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text('TRUENAS_API_KEY="quoted-value"\n')
    assert resolve_api_key(dotenv_path=dotenv) == "quoted-value"


def test_dotenv_ignores_comments_and_other_keys(monkeypatch, tmp_path):
    monkeypatch.delenv("TRUENAS_API_KEY", raising=False)
    dotenv = tmp_path / ".env"
    dotenv.write_text("# comment\nOTHER=x\nTRUENAS_API_KEY=real\n")
    assert resolve_api_key(dotenv_path=dotenv) == "real"


def test_none_when_nothing_set(monkeypatch, tmp_path):
    monkeypatch.delenv("TRUENAS_API_KEY", raising=False)
    assert resolve_api_key(dotenv_path=tmp_path / "missing.env") is None


def test_custom_env_var_name(monkeypatch, tmp_path):
    monkeypatch.setenv("MY_KEY", "custom")
    assert resolve_api_key(env_var="MY_KEY", dotenv_path=tmp_path / "x.env") == "custom"
