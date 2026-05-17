from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Database
    DATABASE_URL: str

    # Auth
    JWT_SECRET_KEY: str
    JWT_ALGORITHM: str = "HS256"
    JWT_EXPIRE_MINUTES: int = 60

    # gRPC
    INTERNAL_GRPC_SECRET: str

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str
    KAFKA_TASKS_TOPIC: str = "hermes.tasks"
    KAFKA_DLQ_TOPIC: str = "hermes.tasks.dlq"
    KAFKA_RESULTS_TOPIC: str = "hermes.results"

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"

    # Circuit breaker
    CIRCUIT_FAILURE_THRESHOLD: int = 3
    CIRCUIT_FAILURE_WINDOW_SECONDS: int = 60
    CIRCUIT_OPEN_TIMEOUT_SECONDS: int = 30
    CIRCUIT_MAX_OPEN_TIMEOUT_SECONDS: int = 300

    class Config:
        env_file = ".env"

settings = Settings()