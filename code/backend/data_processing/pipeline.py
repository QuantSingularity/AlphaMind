"""
Data pipeline module for AlphaMind.

Provides ETL (Extract, Transform, Load) pipeline capabilities.
"""

import logging
import time
from abc import ABC, abstractmethod
from enum import Enum
from typing import Any, Callable, Dict, List, Optional

logger = logging.getLogger(__name__)


class PipelineStatus(Enum):
    """Status of pipeline execution."""

    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELLED = "cancelled"


class PipelineStage(ABC):
    """Base class for pipeline stages."""

    def __init__(self, name: str) -> None:
        """
        Initialize pipeline stage.

        Args:
            name: Name of the stage
        """
        self.name = name
        self.logger = logging.getLogger(f"Pipeline.{name}")

    @abstractmethod
    def execute(self, data: Any) -> Any:
        """
        Execute the pipeline stage.

        Args:
            data: Input data

        Returns:
            Transformed data
        """

    def validate_input(self, data: Any) -> bool:
        """
        Validate input data.

        Args:
            data: Input data to validate

        Returns:
            True if valid, False otherwise
        """
        return data is not None

    def validate_output(self, data: Any) -> bool:
        """
        Validate output data.

        Args:
            data: Output data to validate

        Returns:
            True if valid, False otherwise
        """
        return data is not None


class DataExtractionStage(PipelineStage):
    """Stage for extracting data from sources."""

    def __init__(self, name: str, extractor: Callable) -> None:
        """
        Initialize data extraction stage.

        Args:
            name: Name of the stage
            extractor: Function to extract data
        """
        super().__init__(name)
        self.extractor = extractor

    def execute(self, data: Any) -> Any:
        """Execute data extraction."""
        self.logger.info(f"Extracting data in stage: {self.name}")
        try:
            result = self.extractor(data)
            self.logger.info(f"Successfully extracted data in stage: {self.name}")
            return result
        except Exception as e:
            self.logger.error(f"Error extracting data in stage {self.name}: {e}")
            raise


class DataTransformationStage(PipelineStage):
    """Stage for transforming data."""

    def __init__(self, name: str, transformer: Callable) -> None:
        """
        Initialize data transformation stage.

        Args:
            name: Name of the stage
            transformer: Function to transform data
        """
        super().__init__(name)
        self.transformer = transformer

    def execute(self, data: Any) -> Any:
        """Execute data transformation."""
        self.logger.info(f"Transforming data in stage: {self.name}")
        try:
            result = self.transformer(data)
            self.logger.info(f"Successfully transformed data in stage: {self.name}")
            return result
        except Exception as e:
            self.logger.error(f"Error transforming data in stage {self.name}: {e}")
            raise


class DataLoadStage(PipelineStage):
    """Stage for loading data to destination."""

    def __init__(self, name: str, loader: Callable) -> None:
        """
        Initialize data load stage.

        Args:
            name: Name of the stage
            loader: Function to load data
        """
        super().__init__(name)
        self.loader = loader

    def execute(self, data: Any) -> Any:
        """Execute data loading."""
        self.logger.info(f"Loading data in stage: {self.name}")
        try:
            result = self.loader(data)
            self.logger.info(f"Successfully loaded data in stage: {self.name}")
            return result
        except Exception as e:
            self.logger.error(f"Error loading data in stage {self.name}: {e}")
            raise


class DataPipeline:
    """Manages sequential execution of pipeline stages."""

    def __init__(self, name: str, stages: Optional[List[PipelineStage]] = None) -> None:
        """
        Initialize data pipeline.

        Args:
            name: Name of the pipeline
            stages: List of pipeline stages
        """
        self.name = name
        self.stages = stages or []
        self.status = PipelineStatus.PENDING
        self.execution_history: List[Dict[str, Any]] = []
        self.logger = logging.getLogger(f"Pipeline.{name}")

    def add_stage(self, stage: PipelineStage) -> "DataPipeline":
        """
        Add a stage to the pipeline.

        Args:
            stage: Pipeline stage to add

        Returns:
            Self for method chaining
        """
        self.stages.append(stage)
        self.logger.info(f"Added stage '{stage.name}' to pipeline '{self.name}'")
        return self

    def execute(self, initial_data: Any) -> Any:
        """
        Execute the pipeline.

        Args:
            initial_data: Initial input data

        Returns:
            Final output data after all stages

        Raises:
            Exception: If any stage fails
        """
        self.logger.info(f"Starting pipeline execution: {self.name}")
        self.status = PipelineStatus.RUNNING
        start_time = time.time()

        data = initial_data
        stage_results: List[Any] = []
        try:
            for i, stage in enumerate(self.stages):
                stage_start = time.time()
                self.logger.info(
                    f"Executing stage {i + 1}/{len(self.stages)}: {stage.name}"
                )

                # Validate input
                if not stage.validate_input(data):
                    raise ValueError(f"Invalid input for stage: {stage.name}")

                # Execute stage
                data = stage.execute(data)

                # Validate output
                if not stage.validate_output(data):
                    raise ValueError(f"Invalid output from stage: {stage.name}")

                stage_duration = time.time() - stage_start
                stage_results.append(
                    {
                        "stage": stage.name,
                        "duration": stage_duration,
                        "status": "completed",
                    }
                )
                self.logger.info(
                    f"Stage '{stage.name}' completed in {stage_duration:.2f}s"
                )

            # Pipeline completed successfully
            total_duration = time.time() - start_time
            self.status = PipelineStatus.COMPLETED
            self.logger.info(
                f"Pipeline '{self.name}' completed successfully in {total_duration:.2f}s"
            )

            # Record execution history
            self.execution_history.append(
                {
                    "timestamp": time.time(),
                    "status": "completed",
                    "duration": total_duration,
                    "stages": stage_results,
                }
            )

            return data

        except Exception as e:
            # Pipeline failed
            total_duration = time.time() - start_time
            self.status = PipelineStatus.FAILED
            self.logger.error(
                f"Pipeline '{self.name}' failed after {total_duration:.2f}s: {e}"
            )

            # Record execution history
            self.execution_history.append(
                {
                    "timestamp": time.time(),
                    "status": "failed",
                    "duration": total_duration,
                    "stages": stage_results,
                    "error": str(e),
                }
            )

            raise

    def get_stats(self) -> Dict[str, Any]:
        """Get pipeline statistics."""
        return {
            "name": self.name,
            "status": self.status.value,
            "stages_count": len(self.stages),
            "executions": len(self.execution_history),
            "last_execution": (
                self.execution_history[-1] if self.execution_history else None
            ),
        }


class PipelineBuilder:
    """Builder for creating data pipelines."""

    def __init__(self, name: str) -> None:
        """Initialize pipeline builder."""
        self.pipeline = DataPipeline(name)

    def extract(self, name: str, extractor: Callable) -> "PipelineBuilder":
        """Add extraction stage."""
        self.pipeline.add_stage(DataExtractionStage(name, extractor))
        return self

    def transform(self, name: str, transformer: Callable) -> "PipelineBuilder":
        """Add transformation stage."""
        self.pipeline.add_stage(DataTransformationStage(name, transformer))
        return self

    def load(self, name: str, loader: Callable) -> "PipelineBuilder":
        """Add load stage."""
        self.pipeline.add_stage(DataLoadStage(name, loader))
        return self

    def build(self) -> DataPipeline:
        """Build and return the pipeline."""
        return self.pipeline


# ---------------------------------------------------------------------------
# Public aliases required by data_processing/__init__.py
# ---------------------------------------------------------------------------

#: Alias for DataExtractionStage (extract/load data from a source).
DataLoader = DataExtractionStage

#: Alias for DataTransformationStage (apply transformations to data).
DataTransformer = DataTransformationStage

#: Alias for DataLoadStage (write/export data to a destination).
DataExporter = DataLoadStage
