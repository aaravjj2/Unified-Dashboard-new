Forecast Ensemble Triton Model

This folder contains a minimal scaffold to produce a TorchScript model suitable
for deployment to Triton. It's intentionally lightweight and intended as a
starter example for converting the ensemble logic into a single model that
accepts a fixed-length historical price sequence and outputs a forecast
(time series of length `horizon`).

Files:
- `model.py` - PyTorch module and a save helper to produce `model.pt`.

How to create a TorchScript model (example):

```bash
python model.py --output model.pt --seq-length 60 --horizon 7
```

After producing `model.pt`, place it under a Triton model repository layout:

models/forecast_ensemble/1/model.pt

Then configure Triton with an appropriate `config.pbtxt` describing the
input tensor shape `[1, seq_length]` and output `[1, horizon]`.
