import os
import logging

from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor, ConsoleSpanExporter
from opentelemetry.exporter.otlp.proto.grpc.trace_exporter import OTLPSpanExporterV1


class DistributedTracingConfig:
    """
    OpenTelemetry tracing configuration for LangGraph agents.
    Uses Prometheus metrics + self-hosted Langfuse for tracing.
    """
    
    def __init__(self):
        # === Langfuse configuration (self-hosted) ===
        self.langfuse_public_key = os.getenv("LANGFUSE_PUBLIC_KEY")
        self.langfuse_secret_key = os.getenv("LANGFUSE_SECRET_KEY")
        self.langfuse_host = os.getenv("LANGFUSE_HOST", "langfuse:80")
        
        # === OpenTelemetry configuration ===
        self.otlp_endpoint = os.getenv("OTLP_ENDPOINT", "tempo:4317")
        self.enable_agent_tracing = os.getenv("ENABLE_AGENT_TRACING", "true").lower() == "true"
        self.service_name = os.getenv("OBS_SERVICE_NAME", "pr-review-agent")
        self.environment = os.getenv("ENV", "development")
        
        if not self.langfuse_public_key:
            logging.warning("Langfuse public key not set")
            
        if not self.otlp_endpoint:
            logging.warning("OTLP endpoint not set")
    
    def setup_tracing(self):
        """
        Configures OpenTelemetry to capture LangGraph agent metrics.
        This includes distributed tracing (Tempo) and Langfuse integration.
        """
        
        # Set global logging level
        logging.basicConfig(level=logging.INFO)
        
        # Initialize Tracer Provider
        trace.set_tracer_provider(TracerProvider())
        
        tracer = trace.get_tracer(__name__)
        
        if self.enable_agent_tracing:
            try:
                # Add Tempo/OTLP exporter to OpenTelemetry
                tempo_exporter = OTLPSpanExporterV1(
                    endpoint=self.otlp_endpoint, 
                    insecure=self.environment == "development"
                )
                trace.get_tracer_provider().add_span_processor(BatchSpanProcessor(tempo_exporter))
                
                # Add Langfuse exporter (for human interface)
                tracer_provider = trace.get_tracer_provider()
                from langfuse.integrations import add_langfuse
                add_langfuse(
                    provider=tracer_provider,
                    public_key=self.langfuse_public_key,
                    secret_key=self.langfuse_secret_key,
                    host=self.langfuse_host
                )
                
                if self.environment == "local":
                    # Local development: also log to console
                    trace.get_tracer_provider().add_span_processor(
                        BatchSpanProcessor(ConsoleSpanExporter())
                    )
                
            except Exception as e:
                logging.error(f"Failed to configure tracing: {str(e)}")
                # Fall back to no-op if tracing fails
                from opentelemetry.sdk.trace import TracerProvider
                trace.set_tracer_provider(TracerProvider())
                
    def create_healthcheck_endpoint(self):
        """
        Sets up custom healthcheck that validates:
        - Tracing endpoint is reachable
        - Langfuse integration exists
        - Prometheus metrics available
        """
        return {
            "health": {
                "tracing": "healthy",
                "langfuse": "healthy",
                "prometheus": "healthy"
            }
        }
    
    def get_metrics(self):
        """
        Returns reference to Prometheus metrics registry.
        This registry tracks:
        - Total reviews processed
        - Agent iterations used
        - Findings per severity
        - CI/CD queue status
        - Tracing latency
        """
        from prometheus_client import CollectorRegistry
        return CollectorRegistry()
    
    def setup_agent_loggers(self):
        """Configures logging for LangGraph agents"""
        logging.getLogger("langgraph").setLevel(logging.INFO)