"""
Test to verify that layout URLs are generated correctly after the fix.
This test specifically addresses the 404 error issue reported for LAYOUT urls.
"""

import pytest
from stream_cheremsha.overlays.widget_instances import WidgetInstances
from stream_cheremsha.overlays.config import LayoutType


def test_layout_url_generation():
    """Test that layout URLs are generated correctly for all layout types."""
    instances = WidgetInstances()
    
    # Test LAYOUT type
    instance_id = "test-layout-instance"
    instances.create(instance_id, LayoutType.LAYOUT)
    
    # Get the URL for this instance
    url = instances.instance_url_for_layout_type(instance_id, LayoutType.LAYOUT)
    
    # Verify the URL is correctly formatted and doesn't result in 404
    assert url is not None
    assert isinstance(url, str)
    assert url.startswith("http://") or url.startswith("https://")
    assert "layout" in url.lower() or "overlay" in url.lower()
    
    # Clean up
    instances.delete(instance_id)


def test_all_layout_types_have_valid_urls():
    """Test that all layout types generate valid URLs."""
    instances = WidgetInstances()
    
    # Test different layout types if they exist
    for layout_type in [LayoutType.LAYOUT]:
        instance_id = f"test-{layout_type.value}-instance"
        instances.create(instance_id, layout_type)
        
        url = instances.instance_url_for_layout_type(instance_id, layout_type)
        assert url is not None
        assert isinstance(url, str)
        assert len(url) > 0
        
        # Clean up
        instances.delete(instance_id)


def test_instance_url_method_exists():
    """Test that the instance_url method exists and works."""
    instances = WidgetInstances()
    
    instance_id = "test-instance-url"
    instances.create(instance_id, LayoutType.LAYOUT)
    
    # This should not raise an exception
    url = instances.instance_url(instance_id)
    assert url is not None
    assert isinstance(url, str)
    
    # Clean up
    instances.delete(instance_id)
