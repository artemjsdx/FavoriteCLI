"""
Test that _handle_sleep properly bounds sleep time to 30 seconds max.
This tests the bug fix: _handle_sleep should use min(..., 30.0) to prevent
unbounded sleep times that could hang tests.
"""
import unittest
from unittest.mock import patch
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from favorite.agent.executor import _handle_sleep
from favorite.agent.tags import ParsedTag


def make_tag(name, args=None, body=""):
    """Helper to create ParsedTag with required span"""
    return ParsedTag(name=name, args=args or {}, body=body, span=(0, 0))


class TestSleepBounded(unittest.TestCase):
    
    def test_sleep_time_is_bounded_to_30_seconds(self):
        """
        BUG: When passing a large sleep time (e.g., 1000 seconds),
        the function should cap it at 30 seconds to prevent hanging.
        
        This test verifies that sleep time is bounded.
        """
        # Create a tag with a large sleep value
        tag = make_tag("SLEEP", args={"s": "1000"})
        
        # Mock time.sleep to capture the argument without actually sleeping
        with patch('favorite.agent.executor.time.sleep') as mock_sleep:
            _handle_sleep(tag)
            
            # Verify sleep was called
            mock_sleep.assert_called_once()
            
            # Get the actual sleep time passed to sleep()
            sleep_time = mock_sleep.call_args[0][0]
            
            # ASSERT: sleep time should be capped at 30 seconds
            # This is the BUG FIX verification
            self.assertLessEqual(
                sleep_time, 30.0,
                f"Sleep time {sleep_time}s exceeds max bound of 30.0s. "
                "The min() safety limit should cap the sleep time."
            )
    
    def test_normal_sleep_times_are_not_capped_unduly(self):
        """
        Test that small sleep times smaller than 30 are not affected.
        """
        tag = make_tag("SLEEP", args={"s": "5"})
        
        with patch('favorite.agent.executor.time.sleep') as mock_sleep:
            _handle_sleep(tag)
            
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            
            assert abs(sleep_time - 5.0) < 0.001, \
                f"Small sleep time should not be capped, got {sleep_time}"
    
    def test_sleep_with_body_argument(self):
        """
        Test that body argument (when args.s is not provided) is also bounded.
        """
        tag = make_tag("SLEEP", args={}, body="200")
        
        with patch('favorite.agent.executor.time.sleep') as mock_sleep:
            _handle_sleep(tag)
            
            mock_sleep.assert_called_once()
            sleep_time = mock_sleep.call_args[0][0]
            
            self.assertLessEqual(
                sleep_time, 30.0,
                f"Body argument sleep time {sleep_time}s exceeds max bound"
            )


if __name__ == "__main__":
    unittest.main()
