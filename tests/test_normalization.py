import pytest
from app.services.normalization import URLNormalizer


class TestURLNormalizer:
    """Test URL normalization logic"""
    
    def test_basic_normalization(self):
        """Test basic URL normalization"""
        url = "HTTPS://EXAMPLE.COM/Path/"
        normalized = URLNormalizer.normalize_url(url)
        assert normalized == "https://example.com/path"
    
    def test_remove_tracking_params(self):
        """Test removal of tracking parameters"""
        url = "https://example.com/page?utm_source=google&utm_medium=cpc&important=keep&fbclid=123"
        normalized = URLNormalizer.normalize_url(url)
        assert "utm_source" not in normalized
        assert "utm_medium" not in normalized
        assert "fbclid" not in normalized
        assert "important=keep" in normalized
    
    def test_remove_fragment(self):
        """Test removal of URL fragments"""
        url = "https://example.com/page#section1"
        normalized = URLNormalizer.normalize_url(url)
        assert "#section1" not in normalized
        assert normalized == "https://example.com/page"
    
    def test_sort_query_params(self):
        """Test sorting of query parameters"""
        url = "https://example.com/page?z=1&a=2&m=3"
        normalized = URLNormalizer.normalize_url(url)
        expected = "https://example.com/page?a=2&m=3&z=1"
        assert normalized == expected
    
    def test_trailing_slash_removal(self):
        """Test trailing slash removal (except root)"""
        # Regular path
        url1 = "https://example.com/page/"
        assert URLNormalizer.normalize_url(url1) == "https://example.com/page"
        
        # Root path should keep slash
        url2 = "https://example.com/"
        assert URLNormalizer.normalize_url(url2) == "https://example.com/"
    
    def test_add_protocol(self):
        """Test adding https protocol if missing"""
        url = "example.com/page"
        normalized = URLNormalizer.normalize_url(url)
        assert normalized.startswith("https://")
        assert "example.com/page" in normalized
    
    def test_complex_normalization(self):
        """Test complex URL with multiple normalization rules"""
        url = "HTTPS://EXAMPLE.COM/Page/?utm_source=google&important=keep&z=1&a=2#fragment"
        normalized = URLNormalizer.normalize_url(url)
        expected = "https://example.com/page?a=2&important=keep&z=1"
        assert normalized == expected
    
    def test_empty_and_invalid_urls(self):
        """Test handling of empty and invalid URLs"""
        assert URLNormalizer.normalize_url("") == ""
        assert URLNormalizer.normalize_url("   ") == ""
        assert URLNormalizer.normalize_url(None) == ""
    
    def test_url_hash_computation(self):
        """Test URL hash computation"""
        url = "https://example.com/page"
        hash1 = URLNormalizer.compute_url_hash(url)
        hash2 = URLNormalizer.compute_url_hash(url)
        
        # Should be consistent
        assert hash1 == hash2
        assert len(hash1) == 64  # SHA256 hex length
        assert hash1.lower() == hash1  # Should be lowercase
    
    def test_file_hash_validation(self):
        """Test file hash validation and normalization"""
        # Valid SHA256
        valid_hash = "a" * 64
        assert URLNormalizer.compute_file_hash(valid_hash) == valid_hash
        
        # Valid with uppercase
        upper_hash = "A" * 64
        assert URLNormalizer.compute_file_hash(upper_hash) == valid_hash
        
        # Valid with whitespace
        spaced_hash = "  " + valid_hash + "  "
        assert URLNormalizer.compute_file_hash(spaced_hash) == valid_hash
        
        # Invalid - too short
        assert URLNormalizer.compute_file_hash("abc123") == ""
        
        # Invalid - wrong characters
        assert URLNormalizer.compute_file_hash("g" * 64) == ""
        
        # Empty
        assert URLNormalizer.compute_file_hash("") == ""
        assert URLNormalizer.compute_file_hash(None) == ""
    
    def test_process_submission_url_only(self):
        """Test processing submission with URL only"""
        result = URLNormalizer.process_submission(url="https://example.com/page")
        
        assert result['url'] == "https://example.com/page"
        assert result['url_normalized'] == "https://example.com/page"
        assert len(result['url_hash']) == 64
        assert result['file_hash'] == ""
        assert result['has_content'] is True
    
    def test_process_submission_file_hash_only(self):
        """Test processing submission with file hash only"""
        file_hash = "a" * 64
        result = URLNormalizer.process_submission(file_hash=file_hash)
        
        assert result['url'] == ""
        assert result['url_normalized'] == ""
        assert result['url_hash'] == ""
        assert result['file_hash'] == file_hash
        assert result['has_content'] is True
    
    def test_process_submission_both(self):
        """Test processing submission with both URL and file hash"""
        file_hash = "b" * 64
        result = URLNormalizer.process_submission(
            url="https://example.com/page",
            file_hash=file_hash
        )
        
        assert result['url'] == "https://example.com/page"
        assert result['url_normalized'] == "https://example.com/page"
        assert len(result['url_hash']) == 64
        assert result['file_hash'] == file_hash
        assert result['has_content'] is True
    
    def test_process_submission_empty(self):
        """Test processing submission with no content"""
        result = URLNormalizer.process_submission()
        
        assert result['url'] == ""
        assert result['url_normalized'] == ""
        assert result['url_hash'] == ""
        assert result['file_hash'] == ""
        assert result['has_content'] is False
    
    def test_process_submission_invalid_file_hash(self):
        """Test processing submission with invalid file hash"""
        result = URLNormalizer.process_submission(
            url="https://example.com/page",
            file_hash="invalid"
        )
        
        assert result['file_hash'] == ""  # Invalid hash should be empty
        assert result['has_content'] is True  # But URL is still valid
    
    def test_deduplication_same_urls(self):
        """Test that same URLs produce same hashes"""
        urls = [
            "https://example.com/page?a=1&b=2",
            "HTTPS://EXAMPLE.COM/page/?b=2&a=1&utm_source=test#fragment",
            "example.com/page?utm_medium=cpc&a=1&b=2"
        ]
        
        hashes = []
        for url in urls:
            normalized = URLNormalizer.normalize_url(url)
            hash_val = URLNormalizer.compute_url_hash(normalized)
            hashes.append(hash_val)
        
        # All should produce the same hash
        assert len(set(hashes)) == 1
        assert hashes[0] == hashes[1] == hashes[2]
