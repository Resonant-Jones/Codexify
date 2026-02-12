def test_providers_package_imports_without_google_dependency():
    """
    The providers package must be importable even if optional provider deps
    (e.g. google-cloud-texttospeech) are not installed.
    """
    import guardian.tts.providers as providers

    # It's OK if GoogleTTSProvider is None when deps are missing.
    assert hasattr(providers, "GoogleTTSProvider")
