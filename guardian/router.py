from guardian.contracts import get_identity_context

IDENTITY_CONTRACT_ID = "PCX-GUARDIAN-INT-001"
identity_ctx = get_identity_context(IDENTITY_CONTRACT_ID)


def validate_model(model_name: str):
    allowed_models = identity_ctx.get("model_substrate", [])
    if model_name not in allowed_models:
        raise ValueError(
            f"Model '{model_name}' is not authorized by Guardian identity contract."
        )


def route_request(user_input: str, model_name: str):
    validate_model(model_name)
    # continue with routing logic...
