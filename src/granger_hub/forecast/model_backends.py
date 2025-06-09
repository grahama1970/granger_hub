"""
Model backends for time series forecasting.
Module: model_backends.py
Description: Data models and schemas for model backends

Supports multiple backends:
- HuggingFace PatchTST models
- Ollama (for experimental LLM-based forecasting)
- Custom transformer models

Sample input: Time series data as numpy array or pandas DataFrame
Expected output: Forecast predictions with confidence intervals
"""

from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Dict, List, Tuple, Optional, Union
import numpy as np
import logging
from collections import deque

logger = logging.getLogger(__name__)


@dataclass
class ModelConfig:
    """Configuration for forecast models."""
    model_type: str = "patchtst"  # patchtst, ollama, custom
    model_name: str = "ibm-granite/granite-timeseries-patchtst"
    context_length: int = 96
    patch_length: int = 16
    stride: int = 8
    num_features: int = 1  # Univariate by default
    device: str = "cpu"


class ForecastBackend(ABC):
    """Abstract base class for forecast model backends."""
    
    @abstractmethod
    def load_model(self, config: ModelConfig):
        """Load the model with given configuration."""
        pass
    
    @abstractmethod
    def predict(self, context: np.ndarray, horizon: int) -> Dict:
        """Generate predictions from context window."""
        pass
    
    @abstractmethod
    def fine_tune(self, train_data: np.ndarray, val_data: np.ndarray):
        """Fine-tune model on custom data."""
        pass


class PatchTSTBackend(ForecastBackend):
    """HuggingFace PatchTST model backend."""
    
    def __init__(self):
        self.model = None
        self.config = None
        self.is_loaded = False
        
    def load_model(self, config: ModelConfig):
        """Load PatchTST from HuggingFace."""
        try:
            from transformers import (
                PatchTSTForPrediction, 
                PatchTSTConfig,
                PatchTSTForPretraining
            )
            
            if "granite" in config.model_name:
                # Load pre-trained Granite model
                self.config = PatchTSTConfig.from_pretrained(config.model_name)
                self.model = PatchTSTForPrediction.from_pretrained(config.model_name)
            else:
                # Create new model with custom config
                self.config = PatchTSTConfig(
                    context_length=config.context_length,
                    patch_length=config.patch_length,
                    stride=config.stride,
                    num_input_channels=config.num_features,
                    prediction_length=24,  # Default horizon
                )
                self.model = PatchTSTForPrediction(self.config)
            
            self.model.to(config.device)
            self.is_loaded = True
            logger.info(f"Loaded PatchTST model: {config.model_name}")
            
        except ImportError:
            logger.error("transformers library not installed. Run: pip install transformers")
            raise
        except Exception as e:
            logger.error(f"Failed to load PatchTST: {str(e)}")
            raise
    
    def predict(self, context: np.ndarray, horizon: int) -> Dict:
        """Generate predictions using PatchTST."""
        if not self.is_loaded:
            raise RuntimeError("Model not loaded. Call load_model first.")
        
        try:
            import torch
            
            # Prepare input tensor
            if len(context.shape) == 1:
                # Univariate: add batch and channel dimensions
                context = context.reshape(1, 1, -1)
            elif len(context.shape) == 2:
                # Add batch dimension
                context = context.reshape(1, *context.shape)
            
            # Convert to torch tensor
            inputs = torch.tensor(context, dtype=torch.float32)
            
            # Generate predictions
            with torch.no_grad():
                outputs = self.model(
                    past_values=inputs,
                    past_time_features=None,  # Can add time features if needed
                )
            
            # Extract predictions
            predictions = outputs.prediction_outputs.numpy().squeeze()
            
            # Handle horizon adjustment if needed
            if len(predictions) > horizon:
                predictions = predictions[:horizon]
            elif len(predictions) < horizon:
                # Pad or generate additional predictions
                logger.warning(f"Model generated {len(predictions)} predictions, requested {horizon}")
            
            return {
                "predictions": predictions,
                "model_type": "patchtst",
                "context_used": len(context),
            }
            
        except Exception as e:
            logger.error(f"Prediction failed: {str(e)}")
            raise
    
    def fine_tune(self, train_data: np.ndarray, val_data: np.ndarray):
        """Fine-tune PatchTST on custom data."""
        # Implementation would use HuggingFace Trainer
        # This is a placeholder for the full implementation
        logger.info("Fine-tuning PatchTST model...")
        raise NotImplementedError("Fine-tuning implementation pending")


class OllamaBackend(ForecastBackend):
    """Experimental Ollama LLM backend for forecasting."""
    
    def __init__(self):
        self.client = None
        self.model_name = None
        
    def load_model(self, config: ModelConfig):
        """Initialize Ollama connection."""
        try:
            import requests
            
            # Check if Ollama is running
            response = requests.get("http://localhost:11434/api/tags")
            if response.status_code == 200:
                available_models = [m["name"] for m in response.json()["models"]]
                logger.info(f"Available Ollama models: {available_models}")
                
                # Select best available model
                preferred = ["codellama", "mistral", "llama2"]
                for pref in preferred:
                    for model in available_models:
                        if pref in model.lower():
                            self.model_name = model
                            break
                    if self.model_name:
                        break
                
                if not self.model_name and available_models:
                    self.model_name = available_models[0]
                    
                logger.info(f"Selected Ollama model: {self.model_name}")
            else:
                raise ConnectionError("Ollama not running")
                
        except Exception as e:
            logger.error(f"Failed to connect to Ollama: {str(e)}")
            raise
    
    def predict(self, context: np.ndarray, horizon: int) -> Dict:
        """Generate predictions using Ollama."""
        # Convert context to string representation
        context_str = ", ".join([f"{x:.4f}" for x in context.flatten()[-50:]])
        
        prompt = f"""Given this time series data: [{context_str}]
        
        Predict the next {horizon} values. Consider trends, seasonality, and patterns.
        Return ONLY the numeric predictions as comma-separated values."""
        
        try:
            import requests
            
            response = requests.post(
                "http://localhost:11434/api/generate",
                json={
                    "model": self.model_name,
                    "prompt": prompt,
                    "stream": False,
                    "options": {"temperature": 0.1}
                }
            )
            
            if response.status_code == 200:
                text = response.json()["response"]
                # Extract numbers from response
                import re
                numbers = re.findall(r'-?\d+\.?\d*', text)
                predictions = np.array([float(n) for n in numbers[:horizon]])
                
                if len(predictions) < horizon:
                    # Pad with last value if not enough predictions
                    last_val = predictions[-1] if len(predictions) > 0 else context[-1]
                    predictions = np.pad(predictions, (0, horizon - len(predictions)), 
                                       constant_values=last_val)
                
                return {
                    "predictions": predictions,
                    "model_type": "ollama",
                    "model_name": self.model_name,
                }
            else:
                raise RuntimeError(f"Ollama request failed: {response.status_code}")
                
        except Exception as e:
            logger.error(f"Ollama prediction failed: {str(e)}")
            # Fallback to simple prediction
            return {
                "predictions": np.full(horizon, np.mean(context)),
                "model_type": "ollama_fallback",
                "error": str(e)
            }
    
    def fine_tune(self, train_data: np.ndarray, val_data: np.ndarray):
        """Ollama models cannot be fine-tuned directly."""
        logger.warning("Ollama models cannot be fine-tuned. Use prompting instead.")
        raise NotImplementedError("Ollama fine-tuning not supported")


class StreamingForecastWrapper:
    """Wrapper for handling streaming data with any backend."""
    
    def __init__(self, backend: ForecastBackend, context_length: int):
        self.backend = backend
        self.context_length = context_length
        self.buffer = deque(maxlen=context_length)
        self.prediction_history = []
        
    def update(self, new_value: float) -> Optional[np.ndarray]:
        """Add new value and generate prediction if buffer is full."""
        self.buffer.append(new_value)
        
        if len(self.buffer) == self.context_length:
            context = np.array(self.buffer)
            result = self.backend.predict(context, horizon=1)
            prediction = result["predictions"][0]
            
            self.prediction_history.append({
                "timestamp": len(self.prediction_history),
                "actual": new_value,
                "predicted": prediction,
                "context": context.copy()
            })
            
            return prediction
        return None
    
    def get_metrics(self) -> Dict:
        """Calculate performance metrics on historical predictions."""
        if not self.prediction_history:
            return {}
        
        actuals = [p["actual"] for p in self.prediction_history[1:]]
        predictions = [p["predicted"] for p in self.prediction_history[:-1]]
        
        if not actuals:
            return {}
        
        actuals = np.array(actuals)
        predictions = np.array(predictions)
        
        mae = np.mean(np.abs(actuals - predictions))
        mse = np.mean((actuals - predictions) ** 2)
        rmse = np.sqrt(mse)
        
        return {
            "mae": mae,
            "mse": mse,
            "rmse": rmse,
            "n_predictions": len(actuals)
        }


def create_backend(config: ModelConfig) -> ForecastBackend:
    """Factory function to create appropriate backend."""
    if config.model_type == "patchtst":
        backend = PatchTSTBackend()
    elif config.model_type == "ollama":
        backend = OllamaBackend()
    else:
        raise ValueError(f"Unknown model type: {config.model_type}")
    
    backend.load_model(config)
    return backend


# Validation
if __name__ == "__main__":
    # Test PatchTST backend
    config = ModelConfig(model_type="patchtst")
    
    try:
        backend = create_backend(config)
        
        # Generate sample data
        t = np.linspace(0, 100, 500)
        data = np.sin(0.1 * t) + 0.1 * np.random.randn(500)
        
        # Test prediction
        context = data[-96:]  # Last 96 points
        result = backend.predict(context, horizon=24)
        
        print(f"Generated {len(result['predictions'])} predictions")
        print(f"First 5 predictions: {result['predictions'][:5]}")
        
    except Exception as e:
        print(f"PatchTST test failed: {e}")
        print("Trying Ollama backend...")
        
        # Test Ollama as fallback
        config.model_type = "ollama"
        backend = create_backend(config)
        result = backend.predict(data[-96:], horizon=24)
        print(f"Ollama predictions: {result['predictions'][:5]}")