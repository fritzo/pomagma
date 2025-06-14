import os

import torch

from pomagma.util import BLOB_DIR, BUILD

torch.ops.load_library(os.path.join(BUILD, "src", "torch", "pomagma_torch.so"))
torch.ops.pomagma.init_extension(BLOB_DIR)
