from dataclasses import dataclass

from os import getenv


@dataclass
class DemoConfig:
    gmaps_client_key: str

    raven_endpoint: str
    hf_token: str

    summary_model_endpoint: str

    @classmethod
    def load_from_env(cls) -> "DemoConfig":
        return DemoConfig(
            gmaps_client_key=getenv("GMAPS_CLIENT_KEY"),
            raven_endpoint=getenv("RAVEN_ENDPOINT"),
            hf_token=getenv("HF_TOKEN"),
            summary_model_endpoint=getenv("SUMMARY_MODEL_ENDPOINT"),
        )
