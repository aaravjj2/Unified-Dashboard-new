"""
Transformer-based Price Prediction Service
Implements #51 from ROADMAP_ULTIMATE.md

Based on Temporal Fusion Transformers and attention mechanisms
References: https://github.com/unit8co/darts, https://github.com/Nixtla/neuralforecast
"""
import numpy as np
import pandas as pd
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timedelta
from dataclasses import dataclass
import logging
import warnings
warnings.filterwarnings('ignore')

logger = logging.getLogger(__name__)

# Optional deep learning imports
try:
    import torch
    import torch.nn as nn
    import torch.nn.functional as F
    from torch.utils.data import Dataset, DataLoader
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False
    logger.warning("PyTorch not available - using simplified forecaster")

from sklearn.preprocessing import StandardScaler, MinMaxScaler
from sklearn.metrics import mean_squared_error, mean_absolute_error, r2_score


@dataclass
class ForecastConfig:
    """Configuration for transformer forecaster"""
    seq_length: int = 60  # Input sequence length
    pred_length: int = 5  # Prediction horizon
    d_model: int = 64  # Model dimension
    n_heads: int = 4  # Number of attention heads
    n_encoder_layers: int = 2
    n_decoder_layers: int = 2
    dropout: float = 0.1
    learning_rate: float = 0.001
    batch_size: int = 32
    epochs: int = 50
    patience: int = 10


if HAS_TORCH:
    class PositionalEncoding(nn.Module):
        """Positional encoding for transformer"""
        def __init__(self, d_model: int, max_len: int = 5000, dropout: float = 0.1):
            super().__init__()
            self.dropout = nn.Dropout(p=dropout)
            
            position = torch.arange(max_len).unsqueeze(1)
            div_term = torch.exp(torch.arange(0, d_model, 2) * (-np.log(10000.0) / d_model))
            
            pe = torch.zeros(max_len, 1, d_model)
            pe[:, 0, 0::2] = torch.sin(position * div_term)
            pe[:, 0, 1::2] = torch.cos(position * div_term)
            
            self.register_buffer('pe', pe)
        
        def forward(self, x):
            x = x + self.pe[:x.size(0)]
            return self.dropout(x)


    class TimeSeriesTransformer(nn.Module):
        """
        Transformer model for time series forecasting
        """
        def __init__(self, config: ForecastConfig, n_features: int = 1):
            super().__init__()
            self.config = config
            
            # Input projection
            self.input_projection = nn.Linear(n_features, config.d_model)
            
            # Positional encoding
            self.pos_encoder = PositionalEncoding(config.d_model, dropout=config.dropout)
            
            # Transformer encoder
            encoder_layer = nn.TransformerEncoderLayer(
                d_model=config.d_model,
                nhead=config.n_heads,
                dim_feedforward=config.d_model * 4,
                dropout=config.dropout,
                batch_first=True
            )
            self.transformer_encoder = nn.TransformerEncoder(
                encoder_layer, 
                num_layers=config.n_encoder_layers
            )
            
            # Temporal attention for multi-step prediction
            self.attention = nn.MultiheadAttention(
                config.d_model, 
                config.n_heads, 
                dropout=config.dropout,
                batch_first=True
            )
            
            # Output projection
            self.output_projection = nn.Sequential(
                nn.Linear(config.d_model, config.d_model // 2),
                nn.ReLU(),
                nn.Dropout(config.dropout),
                nn.Linear(config.d_model // 2, config.pred_length)
            )
            
            # Uncertainty estimation
            self.uncertainty_head = nn.Sequential(
                nn.Linear(config.d_model, config.d_model // 2),
                nn.ReLU(),
                nn.Linear(config.d_model // 2, config.pred_length),
                nn.Softplus()  # Ensure positive variance
            )
        
        def forward(self, x, return_attention: bool = False):
            # x shape: (batch, seq_len, features)
            batch_size = x.size(0)
            
            # Project input
            x = self.input_projection(x)
            
            # Add positional encoding
            x = x.transpose(0, 1)  # (seq_len, batch, d_model)
            x = self.pos_encoder(x)
            x = x.transpose(0, 1)  # (batch, seq_len, d_model)
            
            # Transformer encoder
            encoded = self.transformer_encoder(x)
            
            # Self-attention on encoded sequence
            attn_out, attn_weights = self.attention(encoded, encoded, encoded)
            
            # Use last hidden state for prediction
            last_hidden = attn_out[:, -1, :]  # (batch, d_model)
            
            # Generate predictions
            predictions = self.output_projection(last_hidden)
            
            # Generate uncertainty estimates
            uncertainty = self.uncertainty_head(last_hidden)
            
            if return_attention:
                return predictions, uncertainty, attn_weights
            return predictions, uncertainty


    class TimeSeriesDataset(Dataset):
        """Dataset for time series forecasting"""
        def __init__(self, data: np.ndarray, seq_length: int, pred_length: int):
            self.data = torch.FloatTensor(data)
            self.seq_length = seq_length
            self.pred_length = pred_length
        
        def __len__(self):
            return len(self.data) - self.seq_length - self.pred_length + 1
        
        def __getitem__(self, idx):
            x = self.data[idx:idx + self.seq_length]
            y = self.data[idx + self.seq_length:idx + self.seq_length + self.pred_length, 0]
            return x, y


class TransformerForecaster:
    """
    Transformer-based price forecasting service
    """
    
    def __init__(self, config: ForecastConfig = None):
        self.config = config or ForecastConfig()
        self.model = None
        self.scaler = StandardScaler()
        self.feature_scaler = StandardScaler()
        self.device = 'cuda' if HAS_TORCH and torch.cuda.is_available() else 'cpu'
        self.training_history = []
        
    def prepare_features(self, df: pd.DataFrame) -> pd.DataFrame:
        """Prepare features for the model"""
        features = pd.DataFrame(index=df.index)
        
        # Price features
        features['close'] = df['close']
        features['returns'] = df['close'].pct_change()
        features['log_returns'] = np.log(df['close'] / df['close'].shift(1))
        
        # Technical indicators
        features['sma_5'] = df['close'].rolling(5).mean()
        features['sma_20'] = df['close'].rolling(20).mean()
        features['sma_ratio'] = features['sma_5'] / features['sma_20']
        
        # Volatility
        features['volatility'] = features['returns'].rolling(20).std()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        features['rsi'] = 100 - (100 / (1 + rs))
        
        # MACD
        ema12 = df['close'].ewm(span=12).mean()
        ema26 = df['close'].ewm(span=26).mean()
        features['macd'] = ema12 - ema26
        features['macd_signal'] = features['macd'].ewm(span=9).mean()
        
        # Bollinger position
        bb_mid = df['close'].rolling(20).mean()
        bb_std = df['close'].rolling(20).std()
        features['bb_position'] = (df['close'] - bb_mid) / (2 * bb_std)
        
        # Volume features (if available)
        if 'volume' in df.columns:
            features['volume_ratio'] = df['volume'] / df['volume'].rolling(20).mean()
        
        # Momentum
        features['momentum_5'] = df['close'] / df['close'].shift(5) - 1
        features['momentum_10'] = df['close'] / df['close'].shift(10) - 1
        
        # Clean up
        features = features.dropna()
        
        return features
    
    def train(self, df: pd.DataFrame, target_col: str = 'close',
             validation_split: float = 0.2) -> Dict[str, Any]:
        """Train the transformer model"""
        if not HAS_TORCH:
            return self._train_fallback(df, target_col, validation_split)
        
        # Prepare features
        features_df = self.prepare_features(df)
        
        # Scale features
        feature_cols = [c for c in features_df.columns if c != target_col]
        features_scaled = self.feature_scaler.fit_transform(features_df[feature_cols])
        target_scaled = self.scaler.fit_transform(features_df[[target_col]])
        
        # Combine
        data = np.column_stack([target_scaled, features_scaled])
        
        # Split data
        split_idx = int(len(data) * (1 - validation_split))
        train_data = data[:split_idx]
        val_data = data[split_idx:]
        
        # Create datasets
        train_dataset = TimeSeriesDataset(
            train_data, 
            self.config.seq_length, 
            self.config.pred_length
        )
        val_dataset = TimeSeriesDataset(
            val_data,
            self.config.seq_length,
            self.config.pred_length
        )
        
        train_loader = DataLoader(
            train_dataset, 
            batch_size=self.config.batch_size,
            shuffle=True
        )
        val_loader = DataLoader(
            val_dataset,
            batch_size=self.config.batch_size,
            shuffle=False
        )
        
        # Initialize model
        n_features = data.shape[1]
        self.model = TimeSeriesTransformer(self.config, n_features).to(self.device)
        
        # Optimizer and loss
        optimizer = torch.optim.Adam(
            self.model.parameters(), 
            lr=self.config.learning_rate
        )
        scheduler = torch.optim.lr_scheduler.ReduceLROnPlateau(
            optimizer, mode='min', factor=0.5, patience=5
        )
        
        # Training loop
        best_val_loss = float('inf')
        patience_counter = 0
        self.training_history = []
        
        for epoch in range(self.config.epochs):
            # Train
            self.model.train()
            train_loss = 0
            for x, y in train_loader:
                x, y = x.to(self.device), y.to(self.device)
                
                optimizer.zero_grad()
                pred, uncertainty = self.model(x)
                
                # Gaussian negative log-likelihood loss
                loss = torch.mean(
                    0.5 * torch.log(uncertainty) + 
                    0.5 * ((y - pred) ** 2) / uncertainty
                )
                
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()
                
                train_loss += loss.item()
            
            train_loss /= len(train_loader)
            
            # Validate
            self.model.eval()
            val_loss = 0
            with torch.no_grad():
                for x, y in val_loader:
                    x, y = x.to(self.device), y.to(self.device)
                    pred, uncertainty = self.model(x)
                    loss = torch.mean(
                        0.5 * torch.log(uncertainty) + 
                        0.5 * ((y - pred) ** 2) / uncertainty
                    )
                    val_loss += loss.item()
            
            val_loss /= len(val_loader)
            
            self.training_history.append({
                'epoch': epoch + 1,
                'train_loss': train_loss,
                'val_loss': val_loss
            })
            
            scheduler.step(val_loss)
            
            # Early stopping
            if val_loss < best_val_loss:
                best_val_loss = val_loss
                patience_counter = 0
                # Save best model state
                best_state = {k: v.cpu().clone() for k, v in self.model.state_dict().items()}
            else:
                patience_counter += 1
                if patience_counter >= self.config.patience:
                    logger.info(f"Early stopping at epoch {epoch + 1}")
                    break
            
            if (epoch + 1) % 10 == 0:
                logger.info(f"Epoch {epoch+1}: train_loss={train_loss:.4f}, val_loss={val_loss:.4f}")
        
        # Restore best model
        self.model.load_state_dict(best_state)
        
        return {
            'epochs_trained': len(self.training_history),
            'best_val_loss': best_val_loss,
            'final_train_loss': self.training_history[-1]['train_loss'],
            'history': self.training_history
        }
    
    def _train_fallback(self, df: pd.DataFrame, target_col: str,
                       validation_split: float) -> Dict[str, Any]:
        """Fallback training without PyTorch"""
        from sklearn.linear_model import Ridge
        from sklearn.ensemble import GradientBoostingRegressor
        
        features_df = self.prepare_features(df)
        
        X = features_df.drop(columns=[target_col]).values
        y = features_df[target_col].values
        
        split_idx = int(len(X) * (1 - validation_split))
        X_train, X_val = X[:split_idx], X[split_idx:]
        y_train, y_val = y[:split_idx], y[split_idx:]
        
        self.model = GradientBoostingRegressor(
            n_estimators=100,
            max_depth=5,
            learning_rate=0.1
        )
        self.model.fit(X_train, y_train)
        
        val_pred = self.model.predict(X_val)
        val_mse = mean_squared_error(y_val, val_pred)
        
        return {
            'epochs_trained': 1,
            'best_val_loss': val_mse,
            'model_type': 'GradientBoosting'
        }
    
    def predict(self, df: pd.DataFrame, 
               return_confidence: bool = True) -> Dict[str, Any]:
        """Generate predictions"""
        if self.model is None:
            raise ValueError("Model not trained. Call train() first.")
        
        if not HAS_TORCH:
            return self._predict_fallback(df)
        
        features_df = self.prepare_features(df)
        
        # Scale
        feature_cols = [c for c in features_df.columns if c != 'close']
        features_scaled = self.feature_scaler.transform(features_df[feature_cols])
        target_scaled = self.scaler.transform(features_df[['close']])
        
        data = np.column_stack([target_scaled, features_scaled])
        
        # Get last sequence
        seq = torch.FloatTensor(data[-self.config.seq_length:]).unsqueeze(0).to(self.device)
        
        self.model.eval()
        with torch.no_grad():
            pred, uncertainty, attn_weights = self.model(seq, return_attention=True)
        
        # Inverse transform predictions
        pred_np = pred.cpu().numpy().flatten()
        uncertainty_np = uncertainty.cpu().numpy().flatten()
        
        # Scale back
        predictions = self.scaler.inverse_transform(pred_np.reshape(-1, 1)).flatten()
        
        # Calculate confidence intervals
        std_dev = np.sqrt(uncertainty_np) * self.scaler.scale_[0]
        
        current_price = df['close'].iloc[-1]
        
        result = {
            'current_price': current_price,
            'predictions': predictions.tolist(),
            'horizon_days': list(range(1, self.config.pred_length + 1)),
            'predicted_change_pct': [(p / current_price - 1) * 100 for p in predictions],
            'direction': 'bullish' if predictions[-1] > current_price else 'bearish',
            'confidence': float(1 / (1 + np.mean(uncertainty_np)))
        }
        
        if return_confidence:
            result['confidence_intervals'] = {
                'lower_68': (predictions - std_dev).tolist(),
                'upper_68': (predictions + std_dev).tolist(),
                'lower_95': (predictions - 2 * std_dev).tolist(),
                'upper_95': (predictions + 2 * std_dev).tolist()
            }
            result['attention_weights'] = attn_weights.cpu().numpy().tolist()
        
        return result
    
    def _predict_fallback(self, df: pd.DataFrame) -> Dict[str, Any]:
        """Fallback prediction without PyTorch"""
        features_df = self.prepare_features(df)
        X = features_df.drop(columns=['close']).values
        
        prediction = self.model.predict(X[-1:])
        current_price = df['close'].iloc[-1]
        
        return {
            'current_price': current_price,
            'predictions': [float(prediction[0])] * self.config.pred_length,
            'horizon_days': list(range(1, self.config.pred_length + 1)),
            'direction': 'bullish' if prediction[0] > current_price else 'bearish',
            'confidence': 0.5
        }
    
    def backtest(self, df: pd.DataFrame, 
                test_size: int = 60) -> Dict[str, Any]:
        """Backtest the model on historical data"""
        if len(df) < self.config.seq_length + test_size:
            return {'error': 'Insufficient data for backtesting'}
        
        # Train on earlier data
        train_df = df.iloc[:-test_size]
        test_df = df.iloc[-test_size - self.config.seq_length:]
        
        self.train(train_df)
        
        # Make rolling predictions
        predictions = []
        actuals = []
        
        for i in range(test_size):
            window_end = len(test_df) - test_size + i
            window_df = test_df.iloc[:window_end]
            
            pred = self.predict(window_df, return_confidence=False)
            predictions.append(pred['predictions'][0])
            actuals.append(test_df['close'].iloc[window_end])
        
        # Calculate metrics
        predictions = np.array(predictions)
        actuals = np.array(actuals)
        
        mse = mean_squared_error(actuals, predictions)
        mae = mean_absolute_error(actuals, predictions)
        rmse = np.sqrt(mse)
        
        # Direction accuracy
        actual_direction = np.sign(np.diff(actuals))
        pred_direction = np.sign(predictions[1:] - actuals[:-1])
        direction_accuracy = np.mean(actual_direction == pred_direction)
        
        return {
            'mse': mse,
            'rmse': rmse,
            'mae': mae,
            'direction_accuracy': direction_accuracy,
            'test_size': test_size,
            'predictions': predictions.tolist(),
            'actuals': actuals.tolist()
        }


# Singleton instance
_forecaster = None

def get_transformer_forecaster(config: ForecastConfig = None) -> TransformerForecaster:
    global _forecaster
    if _forecaster is None:
        _forecaster = TransformerForecaster(config)
    return _forecaster
