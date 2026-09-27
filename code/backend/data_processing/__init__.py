"""
AlphaMind Data Processing Framework.

Optimised data processing capabilities for financial applications:

1. pipeline   - Sequential ETL transformation stages
2. parallel   - Multi-threading, multi-processing, and distributed execution
3. streaming  - Real-time data ingestion and processing
4. caching    - MemoryCache, DiskCache, RedisCache backends
5. monitoring - Performance tracking and alert generation
"""

from data_processing.caching import (
    CacheManager,
    CachePolicy,
    DiskCache,
    MemoryCache,
    RedisCache,
)
from data_processing.monitoring import (
    AlertManager,
    MetricsCollector,
    PerformanceTracker,
    PipelineMonitor,
)
from data_processing.parallel import (
    DistributedComputing,
    ParallelProcessor,
    TaskManager,
    WorkerPool,
)
from data_processing.pipeline import (
    DataExporter,
    DataLoader,
    DataPipeline,
    DataTransformer,
    PipelineStage,
    PipelineStatus,
)
from data_processing.streaming import (
    DataStreamProcessor,
    KafkaStreamProcessor,
    StreamAggregator,
    WebSocketStreamProcessor,
)

__all__ = [
    # caching
    "CachePolicy",
    "MemoryCache",
    "DiskCache",
    "RedisCache",
    "CacheManager",
    # monitoring
    "MetricsCollector",
    "PerformanceTracker",
    "AlertManager",
    "PipelineMonitor",
    # parallel
    "ParallelProcessor",
    "WorkerPool",
    "TaskManager",
    "DistributedComputing",
    # pipeline
    "PipelineStatus",
    "PipelineStage",
    "DataPipeline",
    "DataLoader",
    "DataTransformer",
    "DataExporter",
    # streaming
    "DataStreamProcessor",
    "KafkaStreamProcessor",
    "WebSocketStreamProcessor",
    "StreamAggregator",
]
