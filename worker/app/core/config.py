from pydantic_settings import BaseSettings

class Settings(BaseSettings):
    # Worker identity
    WORKER_ID: str = "worker-a"
    WORKER_FAILURE_RATE: float = 0.0
    WORKER_TASK_DURATION: float = 0.3

    # Kafka
    KAFKA_BOOTSTRAP_SERVERS: str = "kafka:29092"
    KAFKA_TASKS_TOPIC: str = "hermes.tasks"
    KAFKA_RESULTS_TOPIC: str = "hermes.results"

    # Coordinator gRPC address
    COORDINATOR_GRPC_ADDRESS: str = "coordinator:50051"

    # OpenTelemetry
    OTEL_EXPORTER_OTLP_ENDPOINT: str = "http://otel-collector:4317"

    # Debug endpoints
    ENABLE_DEBUG_ENDPOINTS: bool = True

    class Config:
        env_file = ".env"


settings = Settings()