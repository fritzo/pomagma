#pragma once

namespace pomagma
{

class Signature;

namespace hdf5
{
class InFile;
};

void check_structure (hdf5::InFile & file, const Signature & signature);

} // namespace pomagma
