"""
Pagination and chunking utilities for handling large datasets.
"""
from typing import Any, Dict, List, Generator, Optional
from math import ceil


class Pagination:
    """Utilities for chunking and paginating data."""
    
    def __init__(self, page_size: int = 100):
        """
        Initialize pagination.
        
        Args:
            page_size: Default page size for chunking
        """
        self.page_size = page_size
    
    def chunk(
        self, 
        data: List[Any], 
        chunk_size: Optional[int] = None
    ) -> Generator[List[Any], None, None]:
        """
        Split data into chunks.
        
        Args:
            data: List to chunk
            chunk_size: Size of each chunk (defaults to page_size)
            
        Yields:
            Chunks of data
        """
        size = chunk_size or self.page_size
        for i in range(0, len(data), size):
            yield data[i:i + size]
    
    def paginate(
        self,
        data: List[Any],
        page: int = 1,
        page_size: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Paginate data and return page with metadata.
        
        Args:
            data: List to paginate
            page: Page number (1-indexed)
            page_size: Items per page (defaults to self.page_size)
            
        Returns:
            Dictionary with 'data', 'page', 'page_size', 'total_items', 'total_pages'
        """
        size = page_size or self.page_size
        total_items = len(data)
        total_pages = ceil(total_items / size) if size > 0 else 0
        
        # Validate page number
        if page < 1:
            page = 1
        if page > total_pages and total_pages > 0:
            page = total_pages
        
        # Calculate slice indices
        start_idx = (page - 1) * size
        end_idx = start_idx + size
        
        return {
            'data': data[start_idx:end_idx],
            'page': page,
            'page_size': size,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1
        }
    
    def paginate_with_offset(
        self,
        data: List[Any],
        offset: int = 0,
        limit: Optional[int] = None
    ) -> Dict[str, Any]:
        """
        Paginate data using offset and limit.
        
        Args:
            data: List to paginate
            offset: Starting index (0-indexed)
            limit: Maximum items to return
            
        Returns:
            Dictionary with 'data', 'offset', 'limit', 'total_items'
        """
        limit = limit or self.page_size
        total_items = len(data)
        
        # Validate offset
        if offset < 0:
            offset = 0
        if offset >= total_items:
            offset = max(0, total_items - 1)
        
        # Calculate slice
        end_idx = min(offset + limit, total_items)
        
        return {
            'data': data[offset:end_idx],
            'offset': offset,
            'limit': limit,
            'total_items': total_items,
            'returned_items': end_idx - offset,
            'has_more': end_idx < total_items
        }
    
    def batch_process(
        self,
        items: List[Any],
        batch_size: Optional[int] = None
    ) -> List[List[Any]]:
        """
        Convert data into batches for batch processing.
        
        Args:
            items: List of items to batch
            batch_size: Size of each batch
            
        Returns:
            List of batches
        """
        size = batch_size or self.page_size
        return [list(chunk) for chunk in self.chunk(items, size)]
    
    def create_page_metadata(
        self,
        total_items: int,
        page: int,
        page_size: int
    ) -> Dict[str, Any]:
        """
        Create pagination metadata without data.
        
        Args:
            total_items: Total number of items
            page: Current page number
            page_size: Items per page
            
        Returns:
            Pagination metadata
        """
        total_pages = ceil(total_items / page_size) if page_size > 0 else 0
        
        return {
            'page': page,
            'page_size': page_size,
            'total_items': total_items,
            'total_pages': total_pages,
            'has_next': page < total_pages,
            'has_prev': page > 1,
            'start_index': (page - 1) * page_size,
            'end_index': min(page * page_size, total_items)
        }


class StreamingPagination:
    """Utilities for streaming and processing large datasets."""
    
    @staticmethod
    def stream_chunks(
        data_generator: Generator[Any, None, None],
        chunk_size: int = 100
    ) -> Generator[List[Any], None, None]:
        """
        Stream data in chunks from a generator.
        
        Args:
            data_generator: Generator yielding individual items
            chunk_size: Size of each chunk
            
        Yields:
            Chunks of data
        """
        chunk = []
        for item in data_generator:
            chunk.append(item)
            if len(chunk) >= chunk_size:
                yield chunk
                chunk = []
        
        # Yield remaining items
        if chunk:
            yield chunk
    
    @staticmethod
    def sliding_window(
        data: List[Any],
        window_size: int,
        step: int = 1
    ) -> Generator[List[Any], None, None]:
        """
        Create sliding window over data.
        
        Args:
            data: List to window over
            window_size: Size of each window
            step: Step size between windows
            
        Yields:
            Windows of data
        """
        for i in range(0, len(data) - window_size + 1, step):
            yield data[i:i + window_size]
