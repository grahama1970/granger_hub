"""
Patch transformation for time series data.

Implements PatchTST-style patching where time series are divided into
smaller subsequences (patches) for better pattern recognition.
"""

import numpy as np
from typing import Tuple, Optional


class PatchTransformer:
    """Transform time series into patches for forecasting."""
    
    def __init__(self, patch_length: int = 16, stride: int = 8):
        """
        Initialize patch transformer.
        
        Args:
            patch_length: Length of each patch
            stride: Step size between patches (allows overlap if < patch_length)
        """
        self.patch_length = patch_length
        self.stride = stride
        
        if patch_length <= 0:
            raise ValueError("patch_length must be positive")
        if stride <= 0:
            raise ValueError("stride must be positive")
    
    def create_patches(self, time_series: np.ndarray) -> np.ndarray:
        """
        Create patches from time series.
        
        Args:
            time_series: 1D or 2D array of time series values
            
        Returns:
            Array of patches with shape (n_patches, patch_length) or
            (n_patches, patch_length, n_features) for multivariate
        """
        if len(time_series) < self.patch_length:
            raise ValueError(
                f"Time series length ({len(time_series)}) must be >= "
                f"patch_length ({self.patch_length})"
            )
        
        # Handle 1D and 2D cases
        if len(time_series.shape) == 1:
            return self._create_patches_1d(time_series)
        elif len(time_series.shape) == 2:
            return self._create_patches_2d(time_series)
        else:
            raise ValueError("Time series must be 1D or 2D array")
    
    def _create_patches_1d(self, series: np.ndarray) -> np.ndarray:
        """Create patches from 1D time series."""
        n_samples = len(series)
        n_patches = (n_samples - self.patch_length) // self.stride + 1
        
        patches = np.zeros((n_patches, self.patch_length))
        
        for i in range(n_patches):
            start_idx = i * self.stride
            end_idx = start_idx + self.patch_length
            patches[i] = series[start_idx:end_idx]
        
        return patches
    
    def _create_patches_2d(self, series: np.ndarray) -> np.ndarray:
        """Create patches from multivariate time series."""
        n_samples, n_features = series.shape
        n_patches = (n_samples - self.patch_length) // self.stride + 1
        
        patches = np.zeros((n_patches, self.patch_length, n_features))
        
        for i in range(n_patches):
            start_idx = i * self.stride
            end_idx = start_idx + self.patch_length
            patches[i] = series[start_idx:end_idx]
        
        return patches
    
    def reconstruct_from_patches(
        self, 
        patches: np.ndarray,
        original_length: Optional[int] = None
    ) -> np.ndarray:
        """
        Reconstruct time series from patches (averaging overlaps).
        
        Args:
            patches: Array of patches
            original_length: Target length for reconstruction
            
        Returns:
            Reconstructed time series
        """
        if len(patches) == 0:
            raise ValueError("No patches provided")
        
        # Determine dimensions
        if len(patches.shape) == 2:
            n_patches, patch_length = patches.shape
            is_multivariate = False
        else:
            n_patches, patch_length, n_features = patches.shape
            is_multivariate = True
        
        # Calculate output length if not provided
        if original_length is None:
            original_length = (n_patches - 1) * self.stride + patch_length
        
        # Initialize output and count arrays
        if is_multivariate:
            output = np.zeros((original_length, n_features))
            counts = np.zeros((original_length, n_features))
        else:
            output = np.zeros(original_length)
            counts = np.zeros(original_length)
        
        # Accumulate patches
        for i in range(n_patches):
            start_idx = i * self.stride
            end_idx = min(start_idx + patch_length, original_length)
            actual_length = end_idx - start_idx
            
            if is_multivariate:
                output[start_idx:end_idx] += patches[i, :actual_length]
                counts[start_idx:end_idx] += 1
            else:
                output[start_idx:end_idx] += patches[i, :actual_length]
                counts[start_idx:end_idx] += 1
        
        # Average overlapping regions
        output = np.divide(output, counts, where=counts > 0)
        
        return output
    
    def get_patch_info(self, series_length: int) -> dict:
        """
        Get information about patching for a given series length.
        
        Args:
            series_length: Length of time series
            
        Returns:
            Dictionary with patch information
        """
        if series_length < self.patch_length:
            n_patches = 0
            coverage = 0
        else:
            n_patches = (series_length - self.patch_length) // self.stride + 1
            last_patch_end = (n_patches - 1) * self.stride + self.patch_length
            coverage = min(last_patch_end / series_length, 1.0)
        
        return {
            "n_patches": n_patches,
            "patch_length": self.patch_length,
            "stride": self.stride,
            "overlap": max(0, self.patch_length - self.stride),
            "coverage": coverage,
            "series_length": series_length
        }


# Validation
if __name__ == "__main__":
    # Test with simple example
    transformer = PatchTransformer(patch_length=10, stride=5)
    
    # 1D case
    series_1d = np.sin(np.linspace(0, 4*np.pi, 100))
    patches_1d = transformer.create_patches(series_1d)
    print(f"1D Input shape: {series_1d.shape}")
    print(f"1D Patches shape: {patches_1d.shape}")
    
    # Reconstruct
    reconstructed = transformer.reconstruct_from_patches(patches_1d, len(series_1d))
    print(f"Reconstruction error: {np.mean(np.abs(series_1d - reconstructed)):.6f}")
    
    # 2D case (multivariate)
    series_2d = np.column_stack([
        np.sin(np.linspace(0, 4*np.pi, 100)),
        np.cos(np.linspace(0, 4*np.pi, 100))
    ])
    patches_2d = transformer.create_patches(series_2d)
    print(f"\n2D Input shape: {series_2d.shape}")
    print(f"2D Patches shape: {patches_2d.shape}")
    
    # Get patch info
    info = transformer.get_patch_info(100)
    print(f"\nPatch info for length 100: {info}")