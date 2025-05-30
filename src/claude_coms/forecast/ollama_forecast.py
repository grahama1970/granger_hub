"""
Ollama-based forecasting backend.

Uses Ollama LLMs for time series prediction through clever prompting.
"""

import numpy as np
import requests
import json
import logging
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class OllamaForecaster:
    """Forecaster that uses Ollama for predictions."""
    
    def __init__(self, model_name: str = "auto", host: str = "localhost", port: int = 11434):
        self.model_name = model_name
        self.host = host
        self.port = port
        self.base_url = f"http://{host}:{port}"
        self.selected_model = None
        
        if model_name == "auto":
            self._auto_select_model()
    
    def _auto_select_model(self):
        """Auto-select best available Ollama model."""
        try:
            response = requests.get(f"{self.base_url}/api/tags")
            if response.status_code == 200:
                models = response.json().get("models", [])
                model_names = [m["name"] for m in models]
                
                # Preferred models for forecasting
                preferred = ["codellama", "mistral", "llama2", "qwen2.5", "phi3"]
                
                for pref in preferred:
                    for model in model_names:
                        if pref in model.lower():
                            self.selected_model = model
                            logger.info(f"Auto-selected Ollama model: {model}")
                            return
                
                # Fallback to first available
                if model_names:
                    self.selected_model = model_names[0]
                    logger.info(f"Using fallback model: {self.selected_model}")
        except Exception as e:
            logger.warning(f"Failed to auto-select model: {e}")
            self.selected_model = "codellama"  # Default fallback
    
    def get_model_info(self) -> str:
        """Get information about the selected model."""
        return self.selected_model or self.model_name
    
    def forecast(self, patches: np.ndarray, horizon: int, context: str = "") -> Dict[str, Any]:
        """
        Generate forecast using Ollama.
        
        Args:
            patches: Array of patches from time series
            horizon: Number of steps to forecast
            context: Additional context about the data
            
        Returns:
            Dictionary with predictions and metadata
        """
        model = self.selected_model or self.model_name
        
        # Convert patches to a reasonable representation
        # Take last few patches for context
        recent_patches = patches[-5:] if len(patches) > 5 else patches
        
        # Flatten and get recent values
        recent_values = []
        for patch in recent_patches:
            if isinstance(patch, np.ndarray):
                recent_values.extend(patch.flatten().tolist())
            else:
                recent_values.append(float(patch))
        
        # Limit to last 50 values
        recent_values = recent_values[-50:]
        
        # Create prompt
        prompt = self._create_forecast_prompt(recent_values, horizon, context)
        
        try:
            # Call Ollama
            response = requests.post(
                f"{self.base_url}/api/generate",
                json={
                    "model": model,
                    "prompt": prompt,
                    "stream": False,
                    "options": {
                        "temperature": 0.3,  # Lower temperature for more consistent predictions
                        "num_predict": 500
                    }
                }
            )
            
            if response.status_code == 200:
                result = response.json()
                predictions = self._parse_predictions(result["response"], horizon)
                
                return {
                    "predictions": predictions,
                    "uncertainty": 0.1,  # Simple fixed uncertainty
                    "model": model,
                    "raw_response": result["response"]
                }
            else:
                logger.error(f"Ollama request failed: {response.status_code}")
                return self._fallback_forecast(recent_values, horizon)
                
        except Exception as e:
            logger.error(f"Ollama forecast failed: {e}")
            return self._fallback_forecast(recent_values, horizon)
    
    def _create_forecast_prompt(self, values: List[float], horizon: int, context: str) -> str:
        """Create an effective prompt for time series forecasting."""
        # Format values nicely
        values_str = ", ".join([f"{v:.2f}" for v in values[-20:]])  # Last 20 values
        
        # Calculate simple statistics
        mean = np.mean(values)
        std = np.std(values)
        trend = "increasing" if values[-1] > values[0] else "decreasing"
        
        prompt = f"""You are analyzing time series data. Here are the recent values:
[{values_str}]

Statistics:
- Mean: {mean:.2f}
- Std Dev: {std:.2f}
- Trend: {trend}
{f'- Context: {context}' if context else ''}

Based on this pattern, predict the next {horizon} values.
Consider any trends, seasonality, or patterns you observe.

Return ONLY {horizon} numeric predictions as comma-separated values, nothing else.
Example format: 23.4, 24.1, 23.8, 24.5"""
        
        return prompt
    
    def _parse_predictions(self, response: str, horizon: int) -> np.ndarray:
        """Parse predictions from Ollama response."""
        import re
        
        # Try to extract numbers from response
        # Look for comma-separated numbers
        number_pattern = r'-?\d+\.?\d*'
        numbers = re.findall(number_pattern, response)
        
        # Convert to floats
        predictions = []
        for num in numbers:
            try:
                predictions.append(float(num))
                if len(predictions) >= horizon:
                    break
            except ValueError:
                continue
        
        # If we got enough predictions, use them
        if len(predictions) >= horizon:
            return np.array(predictions[:horizon])
        
        # If not enough, pad with last value or mean
        if predictions:
            last_val = predictions[-1]
            while len(predictions) < horizon:
                predictions.append(last_val)
            return np.array(predictions)
        
        # Complete fallback
        logger.warning("Could not parse predictions from Ollama")
        return np.full(horizon, 0.0)
    
    def _fallback_forecast(self, values: List[float], horizon: int) -> Dict[str, Any]:
        """Simple fallback forecast when Ollama fails."""
        # Use last value as naive forecast
        last_value = values[-1] if values else 0.0
        
        # Add small random walk
        predictions = []
        current = last_value
        for _ in range(horizon):
            current += np.random.normal(0, 0.01 * abs(current))
            predictions.append(current)
        
        return {
            "predictions": np.array(predictions),
            "uncertainty": 0.2,
            "model": "fallback",
            "error": "Ollama unavailable, using fallback"
        }


# Validation
if __name__ == "__main__":
    # Test Ollama forecaster
    forecaster = OllamaForecaster()
    print(f"Selected model: {forecaster.get_model_info()}")
    
    # Test with sample data
    test_values = np.sin(np.linspace(0, 4*np.pi, 100)) + np.random.normal(0, 0.1, 100)
    test_patches = test_values.reshape(-1, 10)  # 10 patches of 10
    
    result = forecaster.forecast(
        test_patches,
        horizon=10,
        context="Sine wave with noise"
    )
    
    print(f"Predictions: {result['predictions']}")
    print(f"Model used: {result['model']}")