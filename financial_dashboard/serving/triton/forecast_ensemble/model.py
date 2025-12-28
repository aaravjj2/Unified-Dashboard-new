"""
Minimal PyTorch model to convert a historical price sequence into a short
forecast horizon. This is a tiny model intended purely as an example and
TorchScript export target for Triton.

It takes a 1D sequence of floats (length `seq_length`) and outputs a vector
of length `horizon`.
"""
import argparse
import torch
import torch.nn as nn


class SimpleForecastNet(nn.Module):
    def __init__(self, seq_length: int, horizon: int, hidden: int = 64):
        super().__init__()
        self.seq_length = seq_length
        self.horizon = horizon
        self.net = nn.Sequential(
            nn.Linear(seq_length, hidden),
            nn.ReLU(),
            nn.Linear(hidden, hidden//2),
            nn.ReLU(),
            nn.Linear(hidden//2, horizon)
        )

    def forward(self, x):
        # x shape: [batch, seq_length]
        return self.net(x)


def save_model(output_path: str, seq_length: int, horizon: int):
    model = SimpleForecastNet(seq_length, horizon)
    model.eval()
    example = torch.zeros(1, seq_length, dtype=torch.float32)
    traced = torch.jit.trace(model, example)
    traced.save(output_path)
    print(f"Saved TorchScript model to {output_path}")


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--output', '-o', default='model.pt')
    parser.add_argument('--seq-length', type=int, default=60)
    parser.add_argument('--horizon', type=int, default=7)
    args = parser.parse_args()
    save_model(args.output, args.seq_length, args.horizon)
