"""Pagination and chunking utilities for handling large datasets."""

from typing import List, Dict, Any, Iterator, Optional, Tuple, Callable
import math
from dataclasses import dataclass


@dataclass
class PaginationConfig:
    """Configuration for pagination."""
    page_size: int = 1000
    max_pages: Optional[int] = None
    total_limit: Optional[int] = None
    offset: int = 0


@dataclass
class PageResult:
    """Result of a paginated operation."""
    data: List[Dict[str, Any]]
    page_number: int
    page_size: int
    total_items: Optional[int] = None
    total_pages: Optional[int] = None
    has_next: bool = False
    has_previous: bool = False


class PaginationEngine:
    """Engine for handling pagination and chunking operations."""
    
    def __init__(self, default_page_size: int = 1000):
        """Initialize pagination engine."""
        self.default_page_size = default_page_size
    
    def paginate_data(self, data: List[Dict[str, Any]], 
                     config: PaginationConfig) -> Iterator[PageResult]:
        """Paginate a list of data."""
        total_items = len(data)
        page_size = config.page_size or self.default_page_size
        total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        
        # Apply total limit if specified
        if config.total_limit:
            data = data[:config.total_limit]
            total_items = min(total_items, config.total_limit)
            total_pages = math.ceil(total_items / page_size) if total_items > 0 else 0
        
        # Apply max pages limit
        if config.max_pages:
            total_pages = min(total_pages, config.max_pages)
        
        start_page = config.offset // page_size + 1
        
        for page_num in range(start_page, total_pages + 1):
            start_idx = (page_num - 1) * page_size
            end_idx = min(start_idx + page_size, total_items)
            
            if start_idx >= total_items:
                break
            
            page_data = data[start_idx:end_idx]
            
            yield PageResult(
                data=page_data,
                page_number=page_num,
                page_size=page_size,
                total_items=total_items,
                total_pages=total_pages,
                has_next=page_num < total_pages,
                has_previous=page_num > 1
            )
    
    def chunk_data(self, data: List[Dict[str, Any]], 
                   chunk_size: int) -> Iterator[List[Dict[str, Any]]]:
        """Split data into chunks of specified size."""
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    def batch_process(self, data: List[Dict[str, Any]], 
                     processor: Callable[[List[Dict[str, Any]]], Any],
                     batch_size: int = 1000,
                     max_batches: Optional[int] = None) -> List[Any]:
        """Process data in batches using the provided processor function."""
        results = []
        batch_count = 0
        
        for batch in self.chunk_data(data, batch_size):
            if max_batches and batch_count >= max_batches:
                break
            
            try:
                result = processor(batch)
                results.append(result)
                batch_count += 1
            except Exception as e:
                # Log error but continue processing
                results.append({'error': str(e), 'batch_number': batch_count})
                batch_count += 1
        
        return results
    
    def parallel_chunk_process(self, data: List[Dict[str, Any]],
                              processor: Callable[[List[Dict[str, Any]]], Any],
                              chunk_size: int = 1000,
                              max_workers: int = 4) -> List[Any]:
        """Process data chunks in parallel."""
        import concurrent.futures
        import threading
        
        chunks = list(self.chunk_data(data, chunk_size))
        results = [None] * len(chunks)
        
        def process_chunk(chunk_index: int, chunk_data: List[Dict[str, Any]]):
            """Process a single chunk."""
            try:
                result = processor(chunk_data)
                results[chunk_index] = result
            except Exception as e:
                results[chunk_index] = {'error': str(e), 'chunk_index': chunk_index}
        
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = []
            
            for i, chunk in enumerate(chunks):
                future = executor.submit(process_chunk, i, chunk)
                futures.append(future)
            
            # Wait for all futures to complete
            concurrent.futures.wait(futures)
        
        return results
    
    def stream_process(self, data_generator: Iterator[Dict[str, Any]],
                      processor: Callable[[Dict[str, Any]], Any],
                      buffer_size: int = 1000) -> Iterator[Any]:
        """Process streaming data with buffering."""
        buffer = []
        
        for item in data_generator:
            buffer.append(item)
            
            if len(buffer) >= buffer_size:
                # Process buffer
                for buffered_item in buffer:
                    try:
                        yield processor(buffered_item)
                    except Exception as e:
                        yield {'error': str(e), 'item': buffered_item}
                
                buffer.clear()
        
        # Process remaining items in buffer
        for buffered_item in buffer:
            try:
                yield processor(buffered_item)
            except Exception as e:
                yield {'error': str(e), 'item': buffered_item}


class AdvancedPaginationEngine(PaginationEngine):
    """Advanced pagination engine with additional features."""
    
    def __init__(self, default_page_size: int = 1000):
        """Initialize advanced pagination engine."""
        super().__init__(default_page_size)
    
    def cursor_paginate(self, data: List[Dict[str, Any]], 
                       cursor_field: str,
                       cursor_value: Optional[Any] = None,
                       page_size: int = None,
                       direction: str = 'forward') -> PageResult:
        """Implement cursor-based pagination."""
        page_size = page_size or self.default_page_size
        
        if cursor_value is None:
            # First page
            if direction == 'forward':
                page_data = data[:page_size]
                has_next = len(data) > page_size
                has_previous = False
            else:
                page_data = data[-page_size:] if len(data) > page_size else data
                has_next = False
                has_previous = len(data) > page_size
        else:
            # Find cursor position
            cursor_index = self._find_cursor_index(data, cursor_field, cursor_value)
            
            if direction == 'forward':
                start_idx = cursor_index + 1
                end_idx = start_idx + page_size
                page_data = data[start_idx:end_idx]
                has_next = end_idx < len(data)
                has_previous = start_idx > 0
            else:  # backward
                end_idx = cursor_index
                start_idx = max(0, end_idx - page_size)
                page_data = data[start_idx:end_idx]
                has_next = end_idx < len(data)
                has_previous = start_idx > 0
        
        return PageResult(
            data=page_data,
            page_number=0,  # Not applicable for cursor pagination
            page_size=page_size,
            total_items=len(data),
            has_next=has_next,
            has_previous=has_previous
        )
    
    def _find_cursor_index(self, data: List[Dict[str, Any]], 
                          cursor_field: str, cursor_value: Any) -> int:
        """Find the index of the cursor value."""
        for i, item in enumerate(data):
            if self._get_nested_value(item, cursor_field) == cursor_value:
                return i
        return -1
    
    def _get_nested_value(self, item: Dict[str, Any], field: str) -> Any:
        """Get value from nested dictionary using dot notation."""
        keys = field.split('.')
        value = item
        
        for key in keys:
            if isinstance(value, dict):
                value = value.get(key)
            else:
                return None
        
        return value
    
    def adaptive_pagination(self, data: List[Dict[str, Any]],
                          performance_target: float = 1.0,
                          initial_page_size: int = 1000) -> Iterator[PageResult]:
        """Implement adaptive pagination that adjusts page size based on performance."""
        import time
        
        current_page_size = initial_page_size
        page_number = 1
        start_idx = 0
        
        while start_idx < len(data):
            start_time = time.time()
            
            end_idx = min(start_idx + current_page_size, len(data))
            page_data = data[start_idx:end_idx]
            
            processing_time = time.time() - start_time
            
            # Adjust page size based on performance
            if processing_time > performance_target:
                # Too slow, reduce page size
                current_page_size = max(100, int(current_page_size * 0.8))
            elif processing_time < performance_target * 0.5:
                # Too fast, increase page size
                current_page_size = min(10000, int(current_page_size * 1.2))
            
            yield PageResult(
                data=page_data,
                page_number=page_number,
                page_size=current_page_size,
                total_items=len(data),
                total_pages=math.ceil(len(data) / current_page_size),
                has_next=end_idx < len(data),
                has_previous=page_number > 1
            )
            
            start_idx = end_idx
            page_number += 1
    
    def memory_efficient_pagination(self, data_source: Callable[[int, int], List[Dict[str, Any]]],
                                  total_count: int,
                                  page_size: int = 1000) -> Iterator[PageResult]:
        """Memory-efficient pagination that loads data on demand."""
        total_pages = math.ceil(total_count / page_size)
        
        for page_num in range(1, total_pages + 1):
            offset = (page_num - 1) * page_size
            
            try:
                page_data = data_source(offset, page_size)
                
                yield PageResult(
                    data=page_data,
                    page_number=page_num,
                    page_size=page_size,
                    total_items=total_count,
                    total_pages=total_pages,
                    has_next=page_num < total_pages,
                    has_previous=page_num > 1
                )
            except Exception as e:
                # Yield error result
                yield PageResult(
                    data=[],
                    page_number=page_num,
                    page_size=page_size,
                    total_items=total_count,
                    total_pages=total_pages,
                    has_next=page_num < total_pages,
                    has_previous=page_num > 1
                )


class DataChunker:
    """Utility class for intelligent data chunking."""
    
    def __init__(self, max_memory_mb: int = 100):
        """Initialize data chunker with memory constraints."""
        self.max_memory_mb = max_memory_mb
    
    def smart_chunk(self, data: List[Dict[str, Any]], 
                   target_chunk_size: Optional[int] = None) -> Iterator[List[Dict[str, Any]]]:
        """Intelligently chunk data based on memory usage."""
        import sys
        
        if not data:
            return
        
        # Estimate memory usage per item
        sample_item = data[0]
        item_size_bytes = sys.getsizeof(str(sample_item))
        max_items_per_chunk = (self.max_memory_mb * 1024 * 1024) // item_size_bytes
        
        # Use target chunk size if provided and reasonable
        if target_chunk_size:
            chunk_size = min(target_chunk_size, max_items_per_chunk)
        else:
            chunk_size = max_items_per_chunk
        
        chunk_size = max(1, chunk_size)  # Ensure at least 1 item per chunk
        
        for i in range(0, len(data), chunk_size):
            yield data[i:i + chunk_size]
    
    def balanced_chunk(self, data: List[Dict[str, Any]], 
                      num_chunks: int) -> List[List[Dict[str, Any]]]:
        """Create balanced chunks with approximately equal sizes."""
        if num_chunks <= 0 or not data:
            return [data] if data else []
        
        chunk_size = len(data) // num_chunks
        remainder = len(data) % num_chunks
        
        chunks = []
        start_idx = 0
        
        for i in range(num_chunks):
            # Add one extra item to first 'remainder' chunks
            current_chunk_size = chunk_size + (1 if i < remainder else 0)
            end_idx = start_idx + current_chunk_size
            
            if start_idx < len(data):
                chunks.append(data[start_idx:end_idx])
            
            start_idx = end_idx
        
        return [chunk for chunk in chunks if chunk]  # Filter out empty chunks