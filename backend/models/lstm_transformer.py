"""
zero_carbon_park_agent LSTM-Transformer 混合时序预测模型

- LSTM 捕获局部时序依赖
- Transformer Encoder 利用多头自注意力捕获长程依赖
- 多输出: 同时预测 COD、氨氮、硝氮三个指标
- 使用 PyTorch 实现，支持 CPU 训练（不需要 GPU）
"""
import torch
import torch.nn as nn
import numpy as np
from pathlib import Path
import sys
import json

sys.path.insert(0, str(Path(__file__).parent.parent))
from config import HIDDEN_DIM, NUM_HEADS, NUM_LAYERS, DROPOUT, MODEL_DIR


class PositionalEncoding(nn.Module):
    """位置编码"""
    def __init__(self, d_model: int, max_len: int = 500, dropout: float = 0.1):
        super().__init__()
        self.dropout = nn.Dropout(p=dropout)
        pe = torch.zeros(max_len, d_model)
        position = torch.arange(0, max_len).unsqueeze(1).float()
        div_term = torch.exp(torch.arange(0, d_model, 2).float()
                             * (-np.log(10000.0) / d_model))
        pe[:, 0::2] = torch.sin(position * div_term)
        pe[:, 1::2] = torch.cos(position * div_term)
        self.register_buffer("pe", pe.unsqueeze(0))

    def forward(self, x):
        return self.dropout(x + self.pe[:, :x.size(1), :])


class LSTMTransformer(nn.Module):
    """LSTM-Transformer 混合预测模型

    LSTM → Transformer Encoder → 多输出头 → 三个指标预测值
    """

    def __init__(self, input_dim: int, hidden_dim: int = HIDDEN_DIM,
                 num_heads: int = NUM_HEADS, num_layers: int = NUM_LAYERS,
                 dropout: float = DROPOUT, pred_len: int = 24, output_dim: int = 3):
        super().__init__()

        self.input_dim = input_dim
        self.hidden_dim = hidden_dim
        self.pred_len = pred_len

        # LSTM 层
        self.lstm = nn.LSTM(
            input_size=input_dim,
            hidden_size=hidden_dim,
            num_layers=2,
            batch_first=True,
            dropout=dropout if num_layers > 1 else 0,
            bidirectional=True,
        )
        lstm_output_dim = hidden_dim * 2  # 双向

        # 投影到 Transformer 维度
        self.input_proj = nn.Linear(lstm_output_dim, hidden_dim)

        # 位置编码
        self.pos_encoder = PositionalEncoding(hidden_dim, dropout=dropout)

        # Transformer Encoder
        encoder_layer = nn.TransformerEncoderLayer(
            d_model=hidden_dim,
            nhead=num_heads,
            dim_feedforward=hidden_dim * 4,
            dropout=dropout,
            batch_first=True,
            activation="gelu",
        )
        self.transformer = nn.TransformerEncoder(encoder_layer, num_layers=num_layers)

        # 预测头（多输出）
        self.pred_head = nn.Sequential(
            nn.Linear(hidden_dim, hidden_dim),
            nn.GELU(),
            nn.Dropout(dropout),
            nn.Linear(hidden_dim, output_dim * pred_len),
        )

        self.output_dim = output_dim
        self._init_weights()

    def _init_weights(self):
        for p in self.parameters():
            if p.dim() > 1:
                nn.init.xavier_uniform_(p)

    def forward(self, x: torch.Tensor) -> torch.Tensor:
        """
        Args:
            x: (batch, seq_len, input_dim)
        Returns:
            (batch, pred_len, output_dim) - 预测的 COD, 氨氮, 硝氮
        """
        batch_size = x.size(0)

        # LSTM 编码
        lstm_out, _ = self.lstm(x)  # (batch, seq_len, hidden_dim*2)

        # 投影
        encoded = self.input_proj(lstm_out)  # (batch, seq_len, hidden_dim)

        # 位置编码 + Transformer
        encoded = self.pos_encoder(encoded)
        transformer_out = self.transformer(encoded)  # (batch, seq_len, hidden_dim)

        # 取最后一个时间步的输出作为序列表示
        seq_repr = transformer_out[:, -1, :]  # (batch, hidden_dim)

        # 预测
        preds = self.pred_head(seq_repr)  # (batch, output_dim * pred_len)
        preds = preds.view(batch_size, self.pred_len, self.output_dim)

        return preds


class WaterPredictionModel:
    """水质预测模型封装

    提供训练、保存、加载、推理接口
    """

    METRIC_NAMES = ["cod", "ammonia_nitrogen", "nitrate_nitrogen"]

    def __init__(self, input_dim: int, pred_len: int = 24):
        self.input_dim = input_dim
        self.pred_len = pred_len
        self.model = LSTMTransformer(input_dim=input_dim, pred_len=pred_len)
        self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        self.model.to(self.device)
        self.is_trained = False

    def train(self, X: np.ndarray, y: np.ndarray, epochs: int = 30,
              batch_size: int = 32, lr: float = 0.001) -> dict:
        """训练模型"""
        self.model.train()
        X_tensor = torch.FloatTensor(X).to(self.device)
        y_tensor = torch.FloatTensor(y).to(self.device)

        dataset = torch.utils.data.TensorDataset(X_tensor, y_tensor)
        dataloader = torch.utils.data.DataLoader(dataset, batch_size=batch_size, shuffle=True)

        optimizer = torch.optim.AdamW(self.model.parameters(), lr=lr, weight_decay=1e-5)
        scheduler = torch.optim.lr_scheduler.CosineAnnealingLR(optimizer, T_max=epochs)
        criterion = nn.HuberLoss()  # 对异常值鲁棒

        history = {"loss": [], "mape": []}

        for epoch in range(epochs):
            epoch_loss = 0.0
            epoch_mape = 0.0
            n_batches = 0

            for batch_X, batch_y in dataloader:
                optimizer.zero_grad()
                preds = self.model(batch_X)
                loss = criterion(preds, batch_y)
                loss.backward()
                torch.nn.utils.clip_grad_norm_(self.model.parameters(), 1.0)
                optimizer.step()

                epoch_loss += loss.item()
                # MAPE
                mape = (torch.abs(batch_y - preds) / (batch_y.abs() + 1e-8)).mean().item()
                epoch_mape += mape
                n_batches += 1

            scheduler.step()
            avg_loss = epoch_loss / n_batches
            avg_mape = epoch_mape / n_batches
            history["loss"].append(avg_loss)
            history["mape"].append(avg_mape)

            if (epoch + 1) % 10 == 0:
                print(f"  Epoch {epoch+1}/{epochs} - Loss: {avg_loss:.4f}, MAPE: {avg_mape:.4f}")

        self.is_trained = True
        return history

    def predict(self, X: np.ndarray) -> np.ndarray:
        """批量预测

        Args:
            X: (N, seq_len, input_dim)
        Returns:
            (N, pred_len, 3) - COD, 氨氮, 硝氮
        """
        self.model.eval()
        X_tensor = torch.FloatTensor(X).to(self.device)
        with torch.no_grad():
            preds = self.model(X_tensor)
        return preds.cpu().numpy()

    def predict_single(self, X: np.ndarray) -> dict:
        """单次预测（用于 API 调用）

        Args:
            X: (1, seq_len, input_dim)
        Returns:
            {"cod": [...], "ammonia_nitrogen": [...], "nitrate_nitrogen": [...]}
        """
        preds = self.predict(X)[0]  # (pred_len, 3)
        return {
            "cod": preds[:, 0].tolist(),
            "ammonia_nitrogen": preds[:, 1].tolist(),
            "nitrate_nitrogen": preds[:, 2].tolist(),
        }

    def save(self, path: Path = None):
        """保存模型"""
        if path is None:
            path = MODEL_DIR / "lstm_transformer_model.pt"
        torch.save({
            "model_state_dict": self.model.state_dict(),
            "input_dim": self.input_dim,
            "pred_len": self.pred_len,
            "is_trained": self.is_trained,
        }, path)
        print(f"模型已保存: {path}")

    def load(self, path: Path = None):
        """加载模型"""
        if path is None:
            path = MODEL_DIR / "lstm_transformer_model.pt"
        if not path.exists():
            print(f"模型文件不存在: {path}")
            return False

        checkpoint = torch.load(path, map_location=self.device, weights_only=False)
        self.input_dim = checkpoint["input_dim"]
        self.pred_len = checkpoint["pred_len"]
        self.model = LSTMTransformer(input_dim=self.input_dim, pred_len=self.pred_len)
        self.model.load_state_dict(checkpoint["model_state_dict"])
        self.model.to(self.device)
        self.is_trained = checkpoint.get("is_trained", True)
        print(f"模型已加载: {path}")
        return True


# 全局模型实例
_model_instance: WaterPredictionModel = None


def get_prediction_model() -> WaterPredictionModel:
    """获取预测模型单例"""
    global _model_instance
    if _model_instance is None:
        _model_instance = WaterPredictionModel(input_dim=0)  # 先创建空模型
        _model_instance.load()
    return _model_instance


if __name__ == "__main__":
    print("模型结构:")
    model = LSTMTransformer(input_dim=50, pred_len=24)
    x = torch.randn(2, 72, 50)
    y = model(x)
    print(f"  输入: {x.shape} → 输出: {y.shape}")
    total_params = sum(p.numel() for p in model.parameters())
    print(f"  参数量: {total_params:,}")