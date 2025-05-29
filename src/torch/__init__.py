import os

import torch

from pomagma.util import BUILD

torch.ops.load_library(os.path.join(BUILD, "src", "torch", "pomagma_torch.so"))
