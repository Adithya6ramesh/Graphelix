import hashlib
import re
from urllib.parse import urlparse, parse_qs, urlencode, urlunparse
from typing import Optional, Set


class URLNormalizer:
    """URL normalization for consistent deduplication"""
    
    # Common tracking parameters to remove
    TRACKING_PARAMS: Set[str] = {
        # Google Analytics and Ads
        'utm_source', 'utm_medium', 'utm_campaign', 'utm_term', 'utm_content',
        'gclid', 'gclsrc', 'dclid', 'wbraid', 'gbraid',
        # Facebook
        'fbclid', 'fbadid',
        # Microsoft
        'msclkid',
        # General tracking
        'ref', 'referrer', 'source',
        # Session/random IDs
        'sessionid', 'sid', '_t', 'timestamp', 'ts',
        # Cache busters
        'v', 'version', 'cache', 'nocache',
    }
    
    @classmethod
    def normalize_url(cls, url: str) -> str:
        """
        Normalize URL for consistent deduplication:
        - Convert to lowercase
        - Remove tracking parameters
        - Remove fragments (#)
        - Strip trailing slashes
        - Sort query parameters
        """
        if not url or not url.strip():
            return ""
        
        url = url.strip()
        
        # Handle URLs without protocol
        if not url.lower().startswith(('http://', 'https://')):
            url = 'https://' + url
        
        try:
            # Convert to lowercase before parsing
            url = url.lower()
            parsed = urlparse(url)
            
            # Remove tracking parameters
            if parsed.query:
                query_params = parse_qs(parsed.query, keep_blank_values=False)
                filtered_params = {
                    k: v for k, v in query_params.items() 
                    if k.lower() not in cls.TRACKING_PARAMS
                }
                # Sort parameters for consistency
                sorted_query = urlencode(sorted(filtered_params.items()), doseq=True)
            else:
                sorted_query = ""
            
            # Remove trailing slash from path (except for root)
            path = parsed.path.rstrip('/') if parsed.path != '/' else '/'
            
            # Reconstruct URL without fragment
            normalized = urlunparse((
                parsed.scheme,
                parsed.netloc,
                path,
                parsed.params,
                sorted_query,
                ''  # Remove fragment
            ))
            
            return normalized
            
        except Exception:
            # If URL parsing fails, return cleaned version
            return url.lower().strip()
    
    @classmethod
    def compute_url_hash(cls, normalized_url: str) -> str:
        """Compute SHA256 hash of normalized URL"""
        if not normalized_url:
            return ""
        return hashlib.sha256(normalized_url.encode('utf-8')).hexdigest()
    
    @classmethod
    def compute_file_hash(cls, file_hash: str) -> str:
        """Validate and normalize file hash (should be SHA256)"""
        if not file_hash:
            return ""
        
        # Remove any whitespace and convert to lowercase
        cleaned = file_hash.strip().lower()
        
        # Validate it's a proper SHA256 (64 hex characters)
        if re.match(r'^[a-f0-9]{64}$', cleaned):
            return cleaned
        
        # If not valid SHA256, return empty (could raise exception instead)
        return ""
    
    @classmethod
    def process_submission(cls, url: Optional[str] = None, file_hash: Optional[str] = None) -> dict:
        """
        Process a case submission and return normalized data for deduplication
        
        Returns:
            dict with keys: url, url_normalized, url_hash, file_hash, has_content
        """
        result = {
            'url': url or '',
            'url_normalized': '',
            'url_hash': '',
            'file_hash': '',
            'has_content': False
        }
        
        # Process URL if provided
        if url and url.strip():
            result['url'] = url.strip()
            result['url_normalized'] = cls.normalize_url(url)
            result['url_hash'] = cls.compute_url_hash(result['url_normalized'])
            result['has_content'] = True
        
        # Process file hash if provided
        if file_hash and file_hash.strip():
            result['file_hash'] = cls.compute_file_hash(file_hash)
            if result['file_hash']:  # Only count if valid
                result['has_content'] = True
        
        return result
