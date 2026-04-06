from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", env_file_encoding="utf-8", extra="ignore")

    # Neo4j
    neo4j_uri: str = "bolt://localhost:7687"
    neo4j_user: str = "neo4j"
    neo4j_password: str = "resumegraph_dev"

    # Azure OpenAI
    azure_openai_endpoint: str = ""
    azure_openai_api_key: str = ""
    azure_openai_deployment_name: str = "gpt-4o"
    azure_openai_api_version: str = "2024-10-21"

    # Azure OpenAI Embeddings
    azure_openai_embedding_deployment: str = "text-embedding-ada-002"

    # API
    api_host: str = "0.0.0.0"
    api_port: int = 3100


settings = Settings()
