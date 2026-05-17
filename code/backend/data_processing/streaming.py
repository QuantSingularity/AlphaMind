"""
Streaming data processing utilities for financial applications.

This module provides classes and functions for processing streaming
financial data, including real-time data handling, event processing,
and integration with various streaming platforms.
"""

import asyncio
import json
import logging
import threading
import time
import uuid
from abc import ABC, abstractmethod
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import pandas as pd
import websockets


class StreamEvent:
    """
    Class representing a streaming data event.

    This class provides a common structure for events in the
    streaming data processing framework.

    Parameters
    ----------
    event_type : str
        Type of the event.
    data : any
        Event data.
    timestamp : float, optional
        Event timestamp. If None, uses current time.
    source : str, optional
        Source of the event.
    metadata : dict, optional
        Additional metadata for the event.
    """

    def __init__(
        self,
        event_type: str,
        data: Any,
        timestamp: Optional[float] = None,
        source: Optional[str] = None,
        metadata: Optional[Dict] = None,
    ) -> None:
        self.id = str(uuid.uuid4())
        self.event_type = event_type
        self.data = data
        self.timestamp = timestamp or time.time()
        self.source = source
        self.metadata = metadata or {}

    def to_dict(self) -> Dict:
        """
        Convert event to dictionary.

        Returns
        -------
        event_dict : dict
            Dictionary representation of the event.
        """
        return {
            "id": self.id,
            "event_type": self.event_type,
            "data": self.data,
            "timestamp": self.timestamp,
            "source": self.source,
            "metadata": self.metadata,
        }

    @classmethod
    def from_dict(cls: Any, data: Dict) -> "StreamEvent":
        """
        Create event from dictionary.

        Parameters
        ----------
        data : dict
            Dictionary representation of the event.

        Returns
        -------
        event : StreamEvent
            Event created from the dictionary.
        """
        event = cls(
            event_type=data["event_type"],
            data=data["data"],
            timestamp=data["timestamp"],
            source=data["source"],
            metadata=data["metadata"],
        )
        event.id = data["id"]
        return event

    def __str__(self) -> str:
        """String representation of the event."""
        return f"StreamEvent(id={self.id}, type={self.event_type}, source={self.source}, timestamp={self.timestamp})"


class DataStream(ABC):
    """
    Abstract base class for data streams.

    This class provides a common interface for all data streams
    in the streaming data processing framework.
    """

    def __init__(self) -> None:
        self.listeners = []
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)

    @abstractmethod
    def start(self) -> None:
        """Start the data stream."""
        self.running = True

    @abstractmethod
    def stop(self) -> None:
        """Stop the data stream."""
        self.running = False

    def add_listener(self, listener: Callable[[StreamEvent], None]) -> None:
        """
        Add a listener to the data stream.

        Parameters
        ----------
        listener : callable
            Function to call when an event is received.
        """
        self.listeners.append(listener)

    def remove_listener(self, listener: Callable[[StreamEvent], None]) -> None:
        """
        Remove a listener from the data stream.

        Parameters
        ----------
        listener : callable
            Listener to remove.
        """
        if listener in self.listeners:
            self.listeners.remove(listener)

    def notify_listeners(self, event: StreamEvent) -> None:
        """
        Notify all listeners of an event.

        Parameters
        ----------
        event : StreamEvent
            Event to notify listeners of.
        """
        for listener in self.listeners:
            try:
                listener(event)
            except Exception as e:
                self.logger.error(f"Error in listener: {e}")


class FileStream(DataStream):
    """
    Data stream from a file.

    This class provides methods for streaming data from a file,
    with support for various file formats and streaming modes.

    Parameters
    ----------
    filepath : str
        Path to the file to stream from.
    event_type : str, default="file_data"
        Type of events to generate.
    chunk_size : int, default=1000
        Number of lines to read at a time.
    delay : float, default=0.1
        Delay between chunks in seconds.
    repeat : bool, default=False
        Whether to repeat the file when finished.
    """

    def __init__(
        self,
        filepath: str,
        event_type: str = "file_data",
        chunk_size: int = 1000,
        delay: float = 0.1,
        repeat: bool = False,
    ) -> None:
        super().__init__()
        self.filepath = filepath
        self.event_type = event_type
        self.chunk_size = chunk_size
        self.delay = delay
        self.repeat = repeat
        self.thread = None

    def start(self) -> None:
        """Start streaming data from the file."""
        super().start()
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._stream_file)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop streaming data from the file."""
        super().stop()
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def _stream_file(self) -> None:
        """Stream data from the file."""
        while self.running:
            try:
                with open(self.filepath, "r") as f:
                    chunk: List[Any] = []
                    for line in f:
                        if not self.running:
                            break
                        chunk.append(line.strip())
                        if len(chunk) >= self.chunk_size:
                            event = StreamEvent(
                                event_type=self.event_type,
                                data=chunk,
                                source=self.filepath,
                            )
                            self.notify_listeners(event)
                            chunk: List[Any] = []
                            time.sleep(self.delay)
                    if chunk and self.running:
                        event = StreamEvent(
                            event_type=self.event_type, data=chunk, source=self.filepath
                        )
                        self.notify_listeners(event)
                if not self.repeat or not self.running:
                    break
            except Exception as e:
                self.logger.error(f"Error streaming file: {e}")
                break


class CSVStream(DataStream):
    """
    Data stream from a CSV file.

    This class provides methods for streaming data from a CSV file,
    with support for various streaming modes and data transformations.

    Parameters
    ----------
    filepath : str
        Path to the CSV file to stream from.
    event_type : str, default="csv_data"
        Type of events to generate.
    chunk_size : int, default=100
        Number of rows to read at a time.
    delay : float, default=0.1
        Delay between chunks in seconds.
    repeat : bool, default=False
        Whether to repeat the file when finished.
    """

    def __init__(
        self,
        filepath: str,
        event_type: str = "csv_data",
        chunk_size: int = 100,
        delay: float = 0.1,
        repeat: bool = False,
    ) -> None:
        super().__init__()
        self.filepath = filepath
        self.event_type = event_type
        self.chunk_size = chunk_size
        self.delay = delay
        self.repeat = repeat
        self.thread = None

    def start(self) -> None:
        """Start streaming data from the CSV file."""
        super().start()
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._stream_csv)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop streaming data from the CSV file."""
        super().stop()
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def _stream_csv(self) -> None:
        """Stream data from the CSV file."""
        while self.running:
            try:
                for chunk in pd.read_csv(self.filepath, chunksize=self.chunk_size):
                    if not self.running:
                        break
                    event = StreamEvent(
                        event_type=self.event_type, data=chunk, source=self.filepath
                    )
                    self.notify_listeners(event)
                    time.sleep(self.delay)
                if not self.repeat or not self.running:
                    break
            except Exception as e:
                self.logger.error(f"Error streaming CSV: {e}")
                break


class WebSocketStream(DataStream):
    """
    Data stream from a WebSocket connection.

    This class provides methods for streaming data from a WebSocket connection,
    with support for various data formats and connection options.

    Parameters
    ----------
    url : str
        URL of the WebSocket server.
    event_type : str, default="websocket_data"
        Type of events to generate.
    headers : dict, optional
        Headers to include in the WebSocket connection.
    auth : tuple, optional
        Authentication credentials (username, password).
    reconnect : bool, default=True
        Whether to automatically reconnect on disconnection.
    reconnect_delay : float, default=5.0
        Delay before reconnecting in seconds.
    """

    def __init__(
        self,
        url: str,
        event_type: str = "websocket_data",
        headers: Optional[Dict] = None,
        auth: Optional[Tuple[str, str]] = None,
        reconnect: bool = True,
        reconnect_delay: float = 5.0,
    ) -> None:
        super().__init__()
        self.url = url
        self.event_type = event_type
        self.headers = headers or {}
        self.auth = auth
        self.reconnect = reconnect
        self.reconnect_delay = reconnect_delay
        self.thread = None
        self.websocket = None

    def start(self) -> None:
        """Start streaming data from the WebSocket connection."""
        super().start()
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_websocket)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop streaming data from the WebSocket connection."""
        super().stop()
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def _run_websocket(self) -> None:
        """Run the WebSocket connection."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            loop.run_until_complete(self._connect_websocket())
        except Exception as e:
            self.logger.error(f"Error in WebSocket connection: {e}")
        finally:
            loop.close()

    async def _connect_websocket(self) -> None:
        """Connect to the WebSocket server."""
        while self.running:
            try:
                async with websockets.connect(
                    self.url, extra_headers=self.headers
                ) as websocket:
                    self.websocket = websocket
                    self.logger.info(f"Connected to WebSocket: {self.url}")
                    async for message in websocket:
                        if not self.running:
                            break
                        try:
                            if isinstance(message, str):
                                try:
                                    data = json.loads(message)
                                except Exception:
                                    data = message
                            else:
                                data = message
                            event = StreamEvent(
                                event_type=self.event_type, data=data, source=self.url
                            )
                            self.notify_listeners(event)
                        except Exception as e:
                            self.logger.error(
                                f"Error processing WebSocket message: {e}"
                            )
                    self.websocket = None
                    if not self.reconnect or not self.running:
                        break
                    self.logger.info(
                        f"Reconnecting to WebSocket in {self.reconnect_delay} seconds..."
                    )
                    await asyncio.sleep(self.reconnect_delay)
            except Exception as e:
                self.logger.error(f"WebSocket connection error: {e}")
                if not self.reconnect or not self.running:
                    break
                self.logger.info(
                    f"Reconnecting to WebSocket in {self.reconnect_delay} seconds..."
                )
                await asyncio.sleep(self.reconnect_delay)

    async def send(self, message: Union[str, Dict]) -> None:
        """
        Send a message to the WebSocket server.

        Parameters
        ----------
        message : str or dict
            Message to send. If a dictionary, it will be converted to JSON.
        """
        if not self.websocket:
            raise RuntimeError("WebSocket is not connected")
        if isinstance(message, dict):
            message = json.dumps(message)
        await self.websocket.send(message)


class KafkaStreamAdapter(DataStream):
    """
    Data stream adapter for Kafka.

    This class provides methods for streaming data from a Kafka topic,
    with support for various Kafka configurations and data formats.

    Parameters
    ----------
    bootstrap_servers : str
        Comma-separated list of Kafka broker addresses.
    topic : str
        Kafka topic to consume from.
    event_type : str, default="kafka_data"
        Type of events to generate.
    group_id : str, optional
        Consumer group ID. If None, generates a random ID.
    auto_offset_reset : str, default="latest"
        Offset reset strategy. Options: "earliest", "latest".
    """

    def __init__(
        self,
        bootstrap_servers: str,
        topic: str,
        event_type: str = "kafka_data",
        group_id: Optional[str] = None,
        auto_offset_reset: str = "latest",
    ) -> None:
        super().__init__()
        self.bootstrap_servers = bootstrap_servers
        self.topic = topic
        self.event_type = event_type
        self.group_id = group_id or f"consumer-{uuid.uuid4()}"
        self.auto_offset_reset = auto_offset_reset
        self.thread = None
        self.consumer = None

    def start(self) -> None:
        """Start streaming data from the Kafka topic."""
        super().start()
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._consume_kafka)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop streaming data from the Kafka topic."""
        super().stop()
        if self.consumer:
            self.consumer.close()
            self.consumer = None
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def _consume_kafka(self) -> None:
        """Consume data from the Kafka topic."""
        try:
            from kafka import KafkaConsumer

            self.consumer = KafkaConsumer(
                self.topic,
                bootstrap_servers=self.bootstrap_servers,
                group_id=self.group_id,
                auto_offset_reset=self.auto_offset_reset,
                value_deserializer=lambda x: self._deserialize_message(x),
            )
            for message in self.consumer:
                if not self.running:
                    break
                event = StreamEvent(
                    event_type=self.event_type,
                    data=message.value,
                    timestamp=message.timestamp / 1000.0,
                    source=f"{self.topic}:{message.partition}:{message.offset}",
                    metadata={
                        "topic": message.topic,
                        "partition": message.partition,
                        "offset": message.offset,
                        "key": message.key,
                    },
                )
                self.notify_listeners(event)
        except ImportError:
            self.logger.error(
                "Kafka library not available. Install with: pip install kafka-python"
            )
        except Exception as e:
            self.logger.error(f"Error consuming Kafka messages: {e}")

    def _deserialize_message(self, message: bytes) -> Any:
        """
        Deserialize a Kafka message.

        Parameters
        ----------
        message : bytes
            Message to deserialize.

        Returns
        -------
        data : any
            Deserialized message.
        """
        try:
            return json.loads(message.decode("utf-8"))
        except Exception:
            return message


class WebSocketStreamAdapter(DataStream):
    """
    Data stream adapter for WebSocket server.

    This class provides methods for streaming data from a WebSocket server,
    with support for various WebSocket configurations and data formats.

    Parameters
    ----------
    host : str, default="0.0.0.0"
        Host to bind the WebSocket server to.
    port : int, default=8765
        Port to bind the WebSocket server to.
    event_type : str, default="websocket_data"
        Type of events to generate.
    """

    def __init__(
        self,
        host: str = "0.0.0.0",
        port: int = 8765,
        event_type: str = "websocket_data",
    ) -> None:
        super().__init__()
        self.host = host
        self.port = port
        self.event_type = event_type
        self.thread = None
        self.server = None
        self.clients = set()

    def start(self) -> None:
        """Start the WebSocket server."""
        super().start()
        if self.thread and self.thread.is_alive():
            return
        self.thread = threading.Thread(target=self._run_server)
        self.thread.daemon = True
        self.thread.start()

    def stop(self) -> None:
        """Stop the WebSocket server."""
        super().stop()
        if self.server:
            self.server.close()
            self.server = None
        if self.thread:
            self.thread.join(timeout=1)
            self.thread = None

    def _run_server(self) -> None:
        """Run the WebSocket server."""
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        try:
            start_server = websockets.serve(self._handle_client, self.host, self.port)
            self.server = loop.run_until_complete(start_server)
            self.logger.info(
                f"WebSocket server started on ws://{self.host}:{self.port}"
            )
            loop.run_forever()
        except Exception as e:
            self.logger.error(f"Error in WebSocket server: {e}")
        finally:
            loop.close()

    async def _handle_client(self, websocket, path) -> None:
        """
        Handle a WebSocket client connection.

        Parameters
        ----------
        websocket : WebSocketServerProtocol
            WebSocket connection.
        path : str
            Connection path.
        """
        self.clients.add(websocket)
        try:
            async for message in websocket:
                if not self.running:
                    break
                try:
                    if isinstance(message, str):
                        try:
                            data = json.loads(message)
                        except Exception:
                            data = message
                    else:
                        data = message
                    event = StreamEvent(
                        event_type=self.event_type,
                        data=data,
                        source=f"{websocket.remote_address[0]}:{websocket.remote_address[1]}",
                    )
                    self.notify_listeners(event)
                except Exception as e:
                    self.logger.error(f"Error processing WebSocket message: {e}")
        except websockets.exceptions.ConnectionClosed:
            pass
        finally:
            self.clients.remove(websocket)

    async def broadcast(self, message: Union[str, Dict]) -> None:
        """
        Broadcast a message to all connected clients.

        Parameters
        ----------
        message : str or dict
            Message to broadcast. If a dictionary, it will be converted to JSON.
        """
        if isinstance(message, dict):
            message = json.dumps(message)
        if not self.clients:
            return
        await asyncio.gather(*[client.send(message) for client in self.clients])


class StreamProcessor:
    """
    Processor for streaming data.

    This class provides methods for processing streaming data,
    including filtering, transformation, and aggregation.

    Parameters
    ----------
    name : str, optional
        Name of the processor.
        If None, generates a random name.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or f"processor-{uuid.uuid4()}"
        self.streams = []
        self.processors = []
        self.filters = []
        self.transformers = []
        self.handlers = []
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_stream(self, stream: DataStream) -> None:
        """
        Add a data stream to the processor.

        Parameters
        ----------
        stream : DataStream
            Data stream to add.
        """
        self.streams.append(stream)
        stream.add_listener(self._process_event)

    def remove_stream(self, stream: DataStream) -> None:
        """
        Remove a data stream from the processor.

        Parameters
        ----------
        stream : DataStream
            Data stream to remove.
        """
        if stream in self.streams:
            stream.remove_listener(self._process_event)
            self.streams.remove(stream)

    def add_processor(self, processor: "StreamProcessor") -> None:
        """
        Add a downstream processor.

        Parameters
        ----------
        processor : StreamProcessor
            Processor to add.
        """
        self.processors.append(processor)

    def remove_processor(self, processor: "StreamProcessor") -> None:
        """
        Remove a downstream processor.

        Parameters
        ----------
        processor : StreamProcessor
            Processor to remove.
        """
        if processor in self.processors:
            self.processors.remove(processor)

    def add_filter(self, filter_func: Callable[[StreamEvent], bool]) -> None:
        """
        Add a filter function.

        Parameters
        ----------
        filter_func : callable
            Function that takes an event and returns a boolean.
            If True, the event is processed; if False, it is discarded.
        """
        self.filters.append(filter_func)

    def add_transformer(
        self,
        transformer_func: Callable[
            [StreamEvent], Union[StreamEvent, List[StreamEvent]]
        ],
    ) -> None:
        """
        Add a transformer function.

        Parameters
        ----------
        transformer_func : callable
            Function that takes an event and returns a new event or list of events.
        """
        self.transformers.append(transformer_func)

    def add_handler(self, handler_func: Callable[[StreamEvent], None]) -> None:
        """
        Add a handler function.

        Parameters
        ----------
        handler_func : callable
            Function that takes an event and performs an action.
        """
        self.handlers.append(handler_func)

    def start(self) -> None:
        """Start all data streams."""
        for stream in self.streams:
            stream.start()

    def stop(self) -> None:
        """Stop all data streams."""
        for stream in self.streams:
            stream.stop()

    def _process_event(self, event: StreamEvent) -> None:
        """
        Process an event.

        Parameters
        ----------
        event : StreamEvent
            Event to process.
        """
        for filter_func in self.filters:
            try:
                if not filter_func(event):
                    return
            except Exception as e:
                self.logger.error(f"Error in filter: {e}")
        events = [event]
        for transformer_func in self.transformers:
            try:
                new_events: List[Any] = []
                for event in events:
                    result = transformer_func(event)
                    if result is None:
                        continue
                    elif isinstance(result, list):
                        new_events.extend(result)
                    else:
                        new_events.append(result)
                events = new_events
            except Exception as e:
                self.logger.error(f"Error in transformer: {e}")
        for event in events:
            for handler_func in self.handlers:
                try:
                    handler_func(event)
                except Exception as e:
                    self.logger.error(f"Error in handler: {e}")
            for processor in self.processors:
                processor._process_event(event)


class StreamingPipeline:
    """
    Pipeline for streaming data processing.

    This class provides methods for building and executing
    streaming data processing pipelines.

    Parameters
    ----------
    name : str, optional
        Name of the pipeline.
        If None, generates a random name.
    """

    def __init__(self, name: Optional[str] = None) -> None:
        self.name = name or f"pipeline-{uuid.uuid4()}"
        self.stages = []
        self.running = False
        self.logger = logging.getLogger(self.__class__.__name__)

    def add_stage(self, processor: StreamProcessor, name: Optional[str] = None) -> None:
        """
        Add a stage to the pipeline.

        Parameters
        ----------
        processor : StreamProcessor
            Processor to add as a stage.
        name : str, optional
            Name of the stage. If None, uses the processor's name.
        """
        stage_name = name or processor.name
        self.stages.append((stage_name, processor))
        if len(self.stages) > 1:
            prev_processor = self.stages[-2][1]
            prev_processor.add_processor(processor)

    def start(self) -> None:
        """Start the pipeline."""
        if self.running:
            return
        self.running = True
        for name, processor in self.stages:
            self.logger.info(f"Starting pipeline stage: {name}")
            processor.start()

    def stop(self) -> None:
        """Stop the pipeline."""
        if not self.running:
            return
        self.running = False
        for name, processor in reversed(self.stages):
            self.logger.info(f"Stopping pipeline stage: {name}")
            processor.stop()

    def get_stage(self, name: str) -> Optional[StreamProcessor]:
        """
        Get a stage by name.

        Parameters
        ----------
        name : str
            Name of the stage.

        Returns
        -------
        processor : StreamProcessor or None
            Processor for the stage, or None if not found.
        """
        for stage_name, processor in self.stages:
            if stage_name == name:
                return processor
        return None


# ---------------------------------------------------------------------------
# Public aliases required by data_processing/__init__.py
# ---------------------------------------------------------------------------

#: Alias — DataStreamProcessor is the public name for StreamProcessor.
DataStreamProcessor = StreamProcessor

#: Alias — KafkaStreamProcessor is the public name for KafkaStreamAdapter.
KafkaStreamProcessor = KafkaStreamAdapter

#: Alias — WebSocketStreamProcessor is the public name for WebSocketStreamAdapter.
WebSocketStreamProcessor = WebSocketStreamAdapter


class StreamAggregator:
    """
    Aggregates multiple :class:`StreamProcessor` outputs into a single stream.

    Parameters
    ----------
    processors : list of StreamProcessor
        Source processors whose outputs are merged.
    """

    def __init__(self, processors=None) -> None:
        self.processors = processors or []

    def add_processor(self, processor: StreamProcessor) -> "StreamAggregator":
        """Register a processor as a source."""
        self.processors.append(processor)
        return self

    def aggregate(self, events):
        """
        Collect and merge events from all registered processors.

        Parameters
        ----------
        events : iterable
            Raw events passed to each processor in sequence.

        Returns
        -------
        list
            Concatenated processed results from all processors.
        """
        results = []
        for proc in self.processors:
            for event in events:
                result = proc.process(event)
                if result is not None:
                    results.append(result)
        return results
