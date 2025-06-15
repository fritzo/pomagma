import os
import warnings

import torch

from pomagma.util import BLOB_DIR, BUILD

POMAGMA_TORCH_SO = os.path.join(BUILD, "pomagma", "torch", "pomagma_torch.so")
if os.path.exists(POMAGMA_TORCH_SO):
    torch.ops.load_library(POMAGMA_TORCH_SO)
    torch.ops.pomagma.init_extension(BLOB_DIR)
else:
    warnings.warn(f"PyTorch extension not found: {POMAGMA_TORCH_SO}")
