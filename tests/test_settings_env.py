import pytest
pytestmark = pytest.mark.settings
from guardian.config.core import get_settings_no_env, Settings, warn_if_missing_keys

def test_dev_gemini_no_keys_warns_not_fails(capfd):
    s = get_settings_no_env(ENV="development", AI_BACKEND="gemini",
                            GENAI_API_KEY=None, GOOGLE_API_KEY=None)
    assert isinstance(s, Settings)
    warn_if_missing_keys(s)
    out, err = capfd.readouterr()
    assert "Missing Gemini API key" in out

def test_prod_groq_missing_key_fails():
    with pytest.raises(ValueError):
        get_settings_no_env(ENV="production", AI_BACKEND="groq", GROQ_API_KEY=None)

def test_prod_gemini_accepts_either_key():
    s = get_settings_no_env(ENV="production", AI_BACKEND="gemini", GENAI_API_KEY="x")
    assert s.GENAI_API_KEY == "x"
    s2 = get_settings_no_env(ENV="production", AI_BACKEND="gemini",
                             GENAI_API_KEY=None, GOOGLE_API_KEY="y")
    assert s2.GOOGLE_API_KEY == "y"
