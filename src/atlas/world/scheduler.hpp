#pragma once

#include "util.hpp"

namespace pomagma
{

class Signature;

void schedule_merge (Ob dep);
void process_mergers (Signature & signature);

} // namespace pomagma
