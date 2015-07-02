#pragma once

#include <pomagma/atlas/world/structure.hpp>

namespace pomagma
{

size_t infer_pos (Structure & structure);
size_t infer_neg (Structure & structure);

inline size_t infer_lazy (Structure & structure)
{
    size_t theorem_count = 0;
    if (not theorem_count) { theorem_count = infer_pos(structure); }
    if (not theorem_count) { theorem_count = infer_neg(structure); }
    return theorem_count;
}

inline size_t infer_eager (Structure & structure)
{
    size_t theorem_count = 0;
    theorem_count += infer_pos(structure);
    theorem_count += infer_neg(structure);
    return theorem_count;
}

} // namespace pomagma
