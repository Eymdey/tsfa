# Phase 2 placeholder — Modal.com deployment configuration
#
# This file will contain Modal app definitions for GPU-accelerated inference:
#   - Chronos-T5-Small (Amazon Research, HuggingFace: amazon/chronos-t5-small)
#   - LSTM custom model via neuralforecast
#   - TiDE multivariate model via neuralforecast
#   - Ensemble combiner
#
# Modal provides on-demand GPU inference (A10G / T4) billed per millisecond.
# Cost is $0 when there are no requests.
#
# Example Phase 2 usage:
#
#   import modal
#
#   stub = modal.Stub("tsfa-inference")
#
#   @stub.function(gpu="A10G", image=modal.Image.debian_slim().pip_install(...))
#   def chronos_predict(series: list[float], horizon: int) -> dict:
#       from transformers import pipeline
#       ...
#
# See: https://modal.com/docs
