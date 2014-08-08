#include "hdf5.hpp"
#include <mutex>

namespace pomagma
{
namespace hdf5
{

// Calling H5garbage_collect is not sufficient to make H5 free resources,
// so we manually lock the library and fully H5close & H5open between locks.
std::mutex g_mutex;

GlobalLock::GlobalLock ()
{
    g_mutex.lock();
    H5open();

    // permanently turn off error reporting to stderr
    // http://www.hdfgroup.org/HDF5/doc/UG/UG_frame13ErrorHandling.html
    H5Eset_auto(H5P_DEFAULT, nullptr, nullptr);
}

GlobalLock::~GlobalLock ()
{
    // In moving from 1.8.4 to 1.8.11,
    // HDF5 starts to break when H5close is called multiple times.
    //H5close();
    H5garbage_collect();

    g_mutex.unlock();
}

} // namespace hdf5
} // namespace pomagma
