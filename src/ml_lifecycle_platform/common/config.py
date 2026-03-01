import os


def env(name: str, default: str | None = None) -> str:
    v = os.getenv(name, default)
    if v is None:
        raise RuntimeError(f"Missing required env var: {name}")
    return v


def get_tracking_uri() -> str:
    return env("MLFLOW_TRACKING_URI", "http://localhost:5050")


def get_registry_uri() -> str:
    return env("MLFLOW_REGISTRY_URI", get_tracking_uri())


def get_experiment_name() -> str:
    return env("EXPERIMENT_NAME", "breast-cancer-platform")


def get_model_name() -> str:
    return env("MODEL_NAME", "breast_cancer_clf")
