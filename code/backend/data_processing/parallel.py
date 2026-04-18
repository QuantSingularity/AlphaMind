"""
Parallel processing utilities for financial data.

This module provides classes and functions for parallel processing
of financial data, including task management, worker pools, and
distributed computing capabilities.
"""

import concurrent.futures
import logging
import multiprocessing as mp
import queue
import threading
import time
import uuid
from concurrent.futures import ProcessPoolExecutor, ThreadPoolExecutor, as_completed
from functools import partial
from typing import Any, Callable, Dict, List, Optional, Tuple, Union

import dask
import dask.dataframe as dd
import pandas as pd

logger = logging.getLogger("alphamind.parallel")


class ParallelProcessor:
    """
    Base class for parallel processing of financial data.

    This class provides methods for executing tasks in parallel
    using various parallelization strategies (threads or processes).

    Parameters
    ----------
    n_workers : int, optional
        Number of worker processes or threads.
        If None, uses the number of CPU cores.
    use_threads : bool, default=False
        Whether to use threads instead of processes.
        Threads are generally better for I/O-bound tasks (e.g., waiting for data),
        processes for CPU-bound tasks (e.g., complex calculations) due to the GIL.
    """

    def __init__(
        self, n_workers: Optional[int] = None, use_threads: bool = False
    ) -> None:
        self.n_workers = n_workers or mp.cpu_count()
        self.use_threads = use_threads
        self.executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
        self.logger = logger.getChild(self.__class__.__name__)
        self.logger.info(
            f"Initialized with {self.n_workers} workers using {('Threads' if use_threads else 'Processes')}"
        )

    def map(self, func: Callable, items: List[Any], *args, **kwargs) -> List[Any]:
        """
        Apply a function to each item in parallel.

        Parameters
        ----------
        func : callable
            Function to apply to each item. The first argument of `func` should be an item from `items`.
        items : list
            List of items to process.
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        results : list
            List of results, maintaining the order of the input `items`.
        """
        if not items:
            return []
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        with self.executor_class(max_workers=self.n_workers) as executor:
            results = list(executor.map(func, items))
        return results

    def apply(self, funcs: List[Callable], *args, **kwargs) -> List[Any]:
        """
        Apply multiple functions in parallel.

        Parameters
        ----------
        funcs : list
            List of callable functions to execute.
        *args : tuple
            Additional positional arguments to pass to each function.
        **kwargs : dict
            Additional keyword arguments to pass to each function.

        Returns
        -------
        results : list
            List of results, ordered by completion time.
        """
        if not funcs:
            return []
        if args or kwargs:
            funcs = [partial(func, *args, **kwargs) for func in funcs]
        with self.executor_class(max_workers=self.n_workers) as executor:
            futures = [executor.submit(func) for func in funcs]
            results = [future.result() for future in as_completed(futures)]
        return results

    def process_dataframe(
        self,
        df: pd.DataFrame,
        func: Callable,
        by: Optional[Union[str, List[str]]] = None,
        *args,
        **kwargs,
    ) -> pd.DataFrame:
        """
        Process a DataFrame in parallel by splitting it into partitions or groups.

        Parameters
        ----------
        df : DataFrame
            DataFrame to process.
        func : callable
            Function to apply to each group (if `by` is not None) or partition (if `by` is None).
        by : str or list, optional
            Column(s) to group by. If None, splits the DataFrame into partitions by row count.
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        result_df : DataFrame
            Processed DataFrame, concatenated from the results of the parallel executions.
        """
        if hasattr(df, "empty") and df.empty:
            return df
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        if by is not None:
            groups = df.groupby(by)
            group_names = list(groups.groups.keys())
            items_to_process = [groups.get_group(name) for name in group_names]
            self.logger.info(f"Processing {len(group_names)} groups in parallel...")
            with self.executor_class(max_workers=self.n_workers) as executor:
                futures = {
                    executor.submit(func, item): group_names[i]
                    for i, item in enumerate(items_to_process)
                }
                results_map: Dict[str, Any] = {}
                for future in as_completed(futures):
                    name = futures[future]
                    try:
                        results_map[name] = future.result()
                    except Exception as e:
                        self.logger.error(f"Error processing group {name}: {e}")
                        results_map[name] = None
            valid_results = [
                result for result in results_map.values() if result is not None
            ]
            if not valid_results:
                return pd.DataFrame()
            return pd.concat(valid_results)
        else:
            n_rows = len(df)
            chunk_size = max(1, n_rows // self.n_workers)
            chunks = [df.iloc[i : i + chunk_size] for i in range(0, n_rows, chunk_size)]
            self.logger.info(f"Processing {len(chunks)} partitions in parallel...")
            results = self.map(func, chunks)
            valid_results = [result for result in results if result is not None]
            if not valid_results:
                return pd.DataFrame()
            return pd.concat(valid_results)

    def process_dask_dataframe(
        self, df: pd.DataFrame, func: Callable, *args, **kwargs
    ) -> pd.DataFrame:
        """
        Process a DataFrame using Dask for streamlined, optimized parallelization.
        This uses Dask's internal schedulers (threads/processes) which are generally
        more efficient than the concurrent.futures executors for DataFrame tasks.

        Parameters
        ----------
        df : DataFrame
            DataFrame to process.
        func : callable
            Function to apply to each partition. Must return a Pandas object.
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        result_df : DataFrame
            Processed DataFrame.
        """
        if hasattr(df, "empty") and df.empty:
            return df
        dask_df = dd.from_pandas(df, npartitions=self.n_workers)
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        result_df = dask_df.map_partitions(func).compute()
        return result_df

    def parallel_apply(
        self, df: pd.DataFrame, func: Callable, axis: int = 0, *args, **kwargs
    ) -> pd.Series:
        """
        Apply a function along an axis of a DataFrame (row or column) in parallel.
        This is essentially a parallel version of `df.apply(func, axis=axis)`.

        Parameters
        ----------
        df : DataFrame
            DataFrame to process.
        func : callable
            Function to apply to each row (axis=0) or column (axis=1).
        axis : int, default=0
            Axis along which to apply the function (0 for rows, 1 for columns).
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        result : Series
            Series with the results.
        """
        if hasattr(df, "empty") and df.empty:
            return pd.Series()
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        if axis == 0:
            items = [df.iloc[i] for i in range(len(df))]
            index = df.index
            self.logger.info(f"Applying function to {len(items)} rows in parallel...")
        else:
            items = [df[col] for col in df.columns]
            index = df.columns
            self.logger.info(
                f"Applying function to {len(items)} columns in parallel..."
            )
        with self.executor_class(max_workers=self.n_workers) as executor:
            results = list(executor.map(func, items))
        return pd.Series(results, index=index)


class TaskManager:
    """
    Manager for parallel task execution with dependencies.

    This class provides methods for defining and executing tasks
    in parallel, respecting a defined dependency graph.

    Parameters
    ----------
    n_workers : int, optional
        Number of worker processes or threads.
        If None, uses the number of CPU cores.
    use_threads : bool, default=False
        Whether to use threads instead of processes.
    """

    def __init__(
        self, n_workers: Optional[int] = None, use_threads: bool = False
    ) -> None:
        self.n_workers = n_workers or mp.cpu_count()
        self.use_threads = use_threads
        self.executor_class = ThreadPoolExecutor if use_threads else ProcessPoolExecutor
        self.tasks: Dict[str, Callable] = {}
        self.dependencies: Dict[str, List[str]] = {}
        self.results: Dict[str, Any] = {}
        self.logger = logger.getChild(self.__class__.__name__)

    def add_task(
        self,
        task_id: str,
        func: Callable,
        dependencies: Optional[List[str]] = None,
        *args,
        **kwargs,
    ) -> None:
        """
        Add a task to the manager.

        Parameters
        ----------
        task_id : str
            Unique identifier for the task.
        func : callable
            Function to execute.
        dependencies : list, optional
            List of task IDs that this task depends on (must be executed first).
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.
        """
        if task_id in self.tasks:
            raise ValueError(f"Task with ID '{task_id}' already exists")
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        self.tasks[task_id] = func
        self.dependencies[task_id] = dependencies or []

    def execute(self) -> Dict[str, Any]:
        """
        Execute all tasks in parallel, respecting dependencies.

        Returns
        -------
        results : dict
            Dictionary mapping task IDs to results. Returns None for failed tasks.
        """
        self.results = {}
        self.logger.info(
            f"Starting execution of {len(self.tasks)} tasks with dependencies."
        )
        ready_tasks = [
            task_id for task_id, deps in self.dependencies.items() if not deps
        ]
        pending_tasks = {
            task_id for task_id in self.tasks if task_id not in ready_tasks
        }
        with self.executor_class(max_workers=self.n_workers) as executor:
            futures: Dict[concurrent.futures.Future, str] = {}
            total_tasks = len(self.tasks)
            completed_count = 0
            while ready_tasks or futures:
                for task_id in ready_tasks:
                    self.logger.debug(f"Submitting task: {task_id}")
                    func = self.tasks[task_id]
                    futures[executor.submit(func)] = task_id
                if futures:
                    done, _ = concurrent.futures.wait(
                        futures.keys(), return_when=concurrent.futures.FIRST_COMPLETED
                    )
                    for future in done:
                        task_id = futures.pop(future)
                        completed_count += 1
                        try:
                            self.results[task_id] = future.result()
                            self.logger.info(
                                f"Completed task: {task_id} ({completed_count}/{total_tasks})"
                            )
                        except Exception as e:
                            self.logger.error(
                                f"Error executing task {task_id}: {e}", exc_info=True
                            )
                            self.results[task_id] = None
                        for pending_id in list(pending_tasks):
                            if all(
                                (
                                    dep in self.results
                                    for dep in self.dependencies[pending_id]
                                )
                            ):
                                ready_tasks.append(pending_id)
                                pending_tasks.remove(pending_id)
                elif pending_tasks:
                    self.logger.error(
                        f"Deadlock detected or remaining pending tasks: {pending_tasks}"
                    )
                    break
        self.logger.info(
            f"Execution finished. Total tasks: {total_tasks}, Completed: {completed_count}"
        )
        return self.results

    def get_result(self, task_id: str) -> Any:
        """
        Get the result of a task.

        Parameters
        ----------
        task_id : str
            ID of the task.

        Returns
        -------
        result : any
            Result of the task.

        Raises
        ------
        ValueError: If no result is found for the task.
        """
        if task_id not in self.results:
            raise ValueError(
                f"No result found for task '{task_id}'. Task may not have run or failed."
            )
        return self.results[task_id]

    def clear(self) -> None:
        """Clear all tasks, dependencies, and results."""
        self.tasks = {}
        self.dependencies = {}
        self.results = {}
        self.logger.info("Task Manager cleared.")


class WorkerPool:
    """
    Pool of workers for parallel task execution using queues.

    This class provides methods for managing a pool of persistent workers
    (threads or processes) that pull tasks from a queue.

    Parameters
    ----------
    n_workers : int, optional
        Number of worker processes or threads.
        If None, uses the number of CPU cores.
    use_threads : bool, default=False
        Whether to use threads instead of processes.
    """

    def __init__(
        self, n_workers: Optional[int] = None, use_threads: bool = False
    ) -> None:
        self.n_workers = n_workers or mp.cpu_count()
        self.use_threads = use_threads
        QueueClass = queue.Queue if use_threads else mp.Queue
        self.task_queue = QueueClass()
        self.result_queue = QueueClass()
        self.workers: List[Union[threading.Thread, mp.Process]] = []
        self.running = False
        self.logger = logger.getChild(self.__class__.__name__)

    def start(self) -> None:
        """Start the worker pool."""
        if self.running:
            return
        self.running = True
        WorkerClass = threading.Thread if self.use_threads else mp.Process
        for i in range(self.n_workers):
            worker = WorkerClass(target=self._worker_loop, name=f"Worker-{i}")
            worker.daemon = True
            worker.start()
            self.workers.append(worker)
        self.logger.info(
            f"Started worker pool with {self.n_workers} {('threads' if self.use_threads else 'processes')}."
        )

    def stop(self) -> None:
        """Stop the worker pool."""
        if not self.running:
            return
        self.running = False
        for _ in range(self.n_workers):
            self.task_queue.put(None)
        for worker in self.workers:
            worker.join(timeout=5)
        self.workers = []
        self.logger.info("Worker pool stopped.")

    def _worker_loop(self) -> None:
        """Worker loop for processing tasks from the queue."""
        while self.running:
            try:
                task = self.task_queue.get(timeout=0.1)
                if task is None:
                    break
                task_id, func, args, kwargs = task
                try:
                    result = func(*args, **kwargs)
                    self.result_queue.put((task_id, result, None))
                except Exception as e:
                    self.logger.error(f"Task {task_id} failed: {e}", exc_info=True)
                    self.result_queue.put((task_id, None, str(e)))
                finally:
                    self.task_queue.task_done()
            except queue.Empty:
                continue
            except Exception as e:
                self.logger.critical(
                    f"Critical error in worker loop: {e}", exc_info=True
                )
                break

    def submit(self, func: Callable, *args, **kwargs) -> str:
        """
        Submit a task to the worker pool. Starts the pool if it's not running.

        Parameters
        ----------
        func : callable
            Function to execute.
        *args : tuple
            Positional arguments to pass to the function.
        **kwargs : dict
            Keyword arguments to pass to the function.

        Returns
        -------
        task_id : str
            Unique identifier for the task.
        """
        if not self.running:
            self.start()
        task_id = str(uuid.uuid4())
        self.task_queue.put((task_id, func, args, kwargs))
        self.logger.debug(f"Submitted task {task_id}")
        return task_id

    def get_result(
        self, task_id: Optional[str] = None, timeout: Optional[float] = None
    ) -> Tuple[str, Any, Optional[str]]:
        """
        Get a result from the worker pool.

        Parameters
        ----------
        task_id : str, optional
            ID of the task to get the result for.
            If None, returns the next available result.
        timeout : float, optional
            Maximum time to wait for a result.

        Returns
        -------
        result : tuple
            Tuple containing (task_id, result, error string).

        Raises
        ------
        RuntimeError: If the worker pool is not running.
        TimeoutError: If the wait times out.
        """
        if not self.running:
            raise RuntimeError("Worker pool is not running")
        if task_id is None:
            try:
                return self.result_queue.get(timeout=timeout)
            except queue.Empty:
                raise TimeoutError("Timed out waiting for a result")
        else:
            start_time = time.time()
            other_results: List[Any] = []
            while timeout is None or time.time() - start_time < timeout:
                try:
                    result = self.result_queue.get(timeout=1)
                    if result[0] == task_id:
                        for other_res in other_results:
                            self.result_queue.put(other_res)
                        return result
                    other_results.append(result)
                except queue.Empty:
                    continue
            for other_res in other_results:
                self.result_queue.put(other_res)
            raise TimeoutError(f"Timed out waiting for task {task_id}")

    def wait_all(
        self, timeout: Optional[float] = None
    ) -> Dict[str, Tuple[Any, Optional[str]]]:
        """
        Wait for all submitted tasks to complete.

        Note: This is non-blocking with respect to *future* submissions,
        but blocks until the current tasks are done or the timeout is reached.

        Parameters
        ----------
        timeout : float, optional
            Maximum time to wait for all currently submitted tasks to complete.

        Returns
        -------
        results : dict
            Dictionary mapping task IDs to (result, error) tuples.
        """
        if not self.running:
            raise RuntimeError("Worker pool is not running")
        results: Dict[str, Any] = {}
        start_time = time.time()
        initial_tasks = self.task_queue.qsize() + len(results)
        while len(results) < initial_tasks:
            if timeout is not None and time.time() - start_time > timeout:
                self.logger.warning(f"wait_all timed out after {timeout} seconds.")
                break
            try:
                remaining_timeout = (
                    timeout - (time.time() - start_time) if timeout is not None else 1
                )
                task_id, result, error = self.result_queue.get(
                    timeout=remaining_timeout
                )
                results[task_id] = (result, error)
            except queue.Empty:
                if self.task_queue.qsize() == 0:
                    if len(results) == initial_tasks:
                        break
                    else:
                        continue
                continue
            except TimeoutError:
                continue
        return results


class DistributedComputing:
    """
    Distributed computing for financial data processing using Dask.

    This class provides methods for distributed computing
    using Dask, leveraging a cluster for scaling beyond a single machine.
    Requires the `dask.distributed` package.

    Parameters
    ----------
    scheduler : str, optional
        Dask scheduler address (e.g., 'tcp://<ip>:<port>').
        If None, a local Dask cluster is created.
    n_workers : int, optional
        Number of worker processes for the local cluster.
        If None, uses the number of CPU cores.
    """

    def __init__(
        self, scheduler: Optional[str] = None, n_workers: Optional[int] = None
    ) -> None:
        self.scheduler = scheduler
        self.n_workers = n_workers or mp.cpu_count()
        self.client = None
        self.cluster = None
        self.logger = logger.getChild(self.__class__.__name__)
        self._initialize_client()

    def _initialize_client(self) -> None:
        """Initialize Dask client."""
        try:
            from dask.distributed import Client, LocalCluster

            if self.scheduler:
                self.client = Client(self.scheduler)
                self.logger.info(f"Connected to Dask scheduler: {self.scheduler}")
            else:
                self.cluster = LocalCluster(n_workers=self.n_workers)
                self.client = Client(self.cluster)
                self.logger.info(
                    f"Created local Dask cluster with {self.n_workers} workers."
                )
            self.logger.info(f"Initialized Dask client: {self.client}")
        except ImportError:
            self.logger.warning(
                "Dask distributed not available. DistributedComputing will not function."
            )
        except Exception as e:
            self.logger.error(f"Error initializing Dask client: {e}", exc_info=True)

    def process_dataframe(
        self, df: pd.DataFrame, func: Callable, *args, **kwargs
    ) -> pd.DataFrame:
        """
        Process a DataFrame using Dask for distributed computing.

        Parameters
        ----------
        df : DataFrame
            DataFrame to process.
        func : callable
            Function to apply to each partition.
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        result_df : DataFrame
            Processed DataFrame.
        """
        if hasattr(df, "empty") and df.empty:
            return df
        if not self.client:
            self.logger.warning(
                "Dask client not available. Falling back to local pandas execution."
            )
            return func(df, *args, **kwargs)
        npartitions = self.n_workers
        dask_df = dd.from_pandas(df, npartitions=npartitions)
        if args or kwargs:
            func = partial(func, *args, **kwargs)
        result_df = dask_df.map_partitions(func).compute()
        return result_df

    def submit(self, func: Callable, *args, **kwargs) -> Any:
        """
        Submit a function for distributed execution.

        Parameters
        ----------
        func : callable
            Function to execute.
        *args : tuple
            Positional arguments to pass to the function.
        **kwargs : dict
            Keyword arguments to pass to the function.

        Returns
        -------
        future : dask.distributed.Future or dask.delayed
            Future object representing the computation. Use `.result()` or `.compute()` to retrieve the result.
        """
        if self.client:
            return self.client.submit(func, *args, **kwargs)
        else:
            return dask.delayed(func)(*args, **kwargs)

    def map(self, func: Callable, items: List[Any], *args, **kwargs) -> List[Any]:
        """
        Apply a function to each item in parallel using the Dask cluster.

        Parameters
        ----------
        func : callable
            Function to apply to each item.
        items : list
            List of items to process.
        *args : tuple
            Additional positional arguments to pass to the function.
        **kwargs : dict
            Additional keyword arguments to pass to the function.

        Returns
        -------
        results : list
            List of results.
        """
        if not items:
            return []
        if self.client:
            futures = self.client.map(func, items, *args, **kwargs)
            return self.client.gather(futures)
        else:
            return [func(item, *args, **kwargs) for item in items]

    def close(self) -> None:
        """Close the Dask client and cluster (if locally managed)."""
        if self.client:
            self.client.close()
            self.client = None
        if self.cluster:
            self.cluster.close()
            self.cluster = None
        self.logger.info("Dask client and cluster closed.")
