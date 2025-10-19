import hashlib
import pyautogui
from PIL import Image
import io
from typing import Optional, Tuple, Dict
import time
import logging

class MissclickHandler:

    def __init__(self, delay_between_checks: float = 0.5):
        """    
        Args:
            delay_between_checks: Delay in seconds between verification checks
        """
        self.delay_between_checks = delay_between_checks
        self.stored_hashes: Dict[str, str] = {}
        self.logger = logging.getLogger(__name__)
        
    def capture_region_hash(self, region: Tuple[int, int, int, int]) -> str:
        """
        Capture a screen region and return its MD5 hash.
        
        Args:
            region: Tuple of (left, top, width, height) defining the screen region
            
        Returns:
            MD5 hash string of the captured region
        """
        try:
            screenshot = pyautogui.screenshot(region=region)
            
            # Convert to bytes for hashing
            img_byte_arr = io.BytesIO()
            screenshot.save(img_byte_arr, format='PNG')
            img_bytes = img_byte_arr.getvalue()
            
            # Generate MD5 hash
            md5_hash = hashlib.md5(img_bytes).hexdigest()
            
            self.logger.debug(f"Captured hash for region {region}: {md5_hash}")
            return md5_hash
            
        except Exception as e:
            self.logger.error(f"Error capturing region hash: {e}")
            raise
    
    def store_baseline(self, region: Tuple[int, int, int, int], region_name: str = "default") -> str:
        """
        Capture and store a baseline hash for a region (before performing an action).
        
        Args:
            region: Tuple of (left, top, width, height) defining the screen region
            region_name: Identifier for this region
            
        Returns:
            The captured baseline hash
        """
        baseline_hash = self.capture_region_hash(region)
        self.stored_hashes[region_name] = baseline_hash
        self.logger.info(f"Stored baseline hash for region '{region_name}'")
        return baseline_hash
    
    def verify_action(self, region: Tuple[int, int, int, int], 
                     region_name: str = "default", 
                     expect_change: bool = True) -> bool:
        """
        Verify if an action was successful by comparing current hash with stored baseline.
        
        Args:
            region: Tuple of (left, top, width, height) defining the screen region
            region_name: Identifier for this region
            expect_change: If True, expects the hash to be different (action changed something)
                          If False, expects the hash to be the same (action didn't change anything)
            
        Returns:
            True if action was successful according to expectation, False otherwise
        """
        if region_name not in self.stored_hashes:
            self.logger.warning(f"No baseline hash found for region '{region_name}'. Storing current as baseline.")
            self.store_baseline(region, region_name)
            return True  # First capture, assume success
        
        current_hash = self.capture_region_hash(region)
        baseline_hash = self.stored_hashes[region_name]
        
        if expect_change:
            # Action should have changed the screen
            success = current_hash != baseline_hash
            self.logger.info(f"Action verification for '{region_name}': {'SUCCESS' if success else 'FAILED'} "
                           f"(Expected change, got {'change' if success else 'no change'})")
        else:
            # Action should NOT have changed the screen
            success = current_hash == baseline_hash
            self.logger.info(f"Action verification for '{region_name}': {'SUCCESS' if success else 'FAILED'} "
                           f"(Expected no change, got {'no change' if success else 'change'})")
        
        return success
    
    def compare_regions(self, region1: Tuple[int, int, int, int], 
                       region2: Tuple[int, int, int, int]) -> bool:
        """
        Compare two different screen regions to see if they're identical.
        
        Args:
            region1: First region to compare
            region2: Second region to compare
            
        Returns:
            True if regions are identical, False otherwise
        """
        hash1 = self.capture_region_hash(region1)
        hash2 = self.capture_region_hash(region2)
        
        are_identical = hash1 == hash2
        self.logger.info(f"Region comparison: {region1} vs {region2} = {'IDENTICAL' if are_identical else 'DIFFERENT'}")
        
        return are_identical
    
    def get_stored_hash(self, region_name: str) -> Optional[str]:
        """
        Get the stored hash for a region.
        
        Args:
            region_name: Name of the region
            
        Returns:
            The stored hash or None if not found
        """
        return self.stored_hashes.get(region_name)
    
    def clear_stored_hash(self, region_name: str) -> bool:
        """
        Clear the stored hash for a region.
        
        Args:
            region_name: Name of the region
            
        Returns:
            True if hash was cleared, False if it didn't exist
        """
        if region_name in self.stored_hashes:
            del self.stored_hashes[region_name]
            self.logger.info(f"Cleared stored hash for region '{region_name}'")
            return True
        return False
    
    def clear_all_hashes(self):
        """Clear all stored hashes."""
        self.stored_hashes.clear()
        self.logger.info("Cleared all stored hashes")


# Standalone utility functions for quick usage
def quick_verify_change(region: Tuple[int, int, int, int], 
                       baseline_hash: str, 
                       expect_change: bool = True) -> bool:
    """
    Quick verification function that compares current region hash with a provided baseline.
    
    Args:
        region: Screen region to capture and verify
        baseline_hash: Previously captured hash to compare against
        expect_change: Whether to expect a change from baseline
        
    Returns:
        True if verification matches expectation, False otherwise
    """
    handler = MissclickHandler()
    current_hash = handler.capture_region_hash(region)
    
    if expect_change:
        return current_hash != baseline_hash
    else:
        return current_hash == baseline_hash


def capture_and_compare(region: Tuple[int, int, int, int], 
                       previous_hash: Optional[str] = None) -> Tuple[str, bool]:
    """
    Capture current region hash and optionally compare with previous hash.
    
    Args:
        region: Screen region to capture
        previous_hash: Optional previous hash to compare against
        
    Returns:
        Tuple of (current_hash, changed) where changed is True if different from previous_hash
    """
    handler = MissclickHandler()
    current_hash = handler.capture_region_hash(region)
    
    if previous_hash is None:
        return current_hash, False
    
    changed = current_hash != previous_hash
    return current_hash, changed


def verify_action_with_delay(region: Tuple[int, int, int, int],
                           baseline_hash: str,
                           expect_change: bool = True,
                           delay: float = 0.5) -> bool:
    """
    Verify action after a delay to allow UI updates.
    
    Args:
        region: Screen region to verify
        baseline_hash: Hash to compare against
        expect_change: Whether to expect change
        delay: Seconds to wait before verification
        
    Returns:
        True if verification succeeds, False otherwise
    """
    time.sleep(delay)
    return quick_verify_change(region, baseline_hash, expect_change)