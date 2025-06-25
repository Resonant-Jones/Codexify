from guardian.config import get_settings


class HybridRouter:
    # Runtime override for toggles (defaults to None; falls back to Settings)
    _cloud_only = None
    _hybrid_enabled = None

    @classmethod
    def set_cloud_only(cls, value: bool):
        cls._cloud_only = value

    @classmethod
    def set_hybrid_enabled(cls, value: bool):
        cls._hybrid_enabled = value

    @classmethod
    def get_model(cls, task_type: str = "chat"):
        """
        Returns (model_name, api_host) tuple for task_type.
        - task_type: "chat" | "research" | etc.
        """
        settings = get_settings()
        cloud_only = (
            cls._cloud_only if cls._cloud_only is not None else settings.CLOUD_ONLY
        )
        hybrid_enabled = (
            cls._hybrid_enabled
            if cls._hybrid_enabled is not None
            else settings.HYBRID_ENABLED
        )

        if cloud_only:
            return settings.CLOUD_MODEL_NAME, settings.CLOUD_API_HOST
        elif hybrid_enabled and task_type == "research":
            return settings.CLOUD_MODEL_NAME, settings.CLOUD_API_HOST
        else:
            return settings.LOCAL_MODEL_NAME, settings.LOCAL_API_HOST

    @classmethod
    def is_cloud(cls, model_name: str) -> bool:
        """
        Checks if a model name matches the current cloud model.
        """
        settings = get_settings()
        return model_name == settings.CLOUD_MODEL_NAME
