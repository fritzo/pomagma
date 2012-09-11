#include "dense_set.hpp"

using namespace pomagma;

double test_iterator (size_t exponent, float density, size_t iters = 10000)
{
    size_t item_count = (1 << exponent) - 1;
    DenseSet set(item_count);
    for (size_t i = 1; i <= item_count; ++i) {
        if (random_bool(density)) {
            set.insert(i);
        }
    }

    size_t count = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        for (auto iter = set.iter(); iter.ok(); iter.next()) {
            ++count;
        }
    }
    return timer.elapsed();
}

int main ()
{
    Log::title("DenseSet profile");

    size_t min_exponent = 10;
    size_t max_exponent = 16;
    POMAGMA_INFO(std::setw(12) << "exponent" << std::setw(12) << "time (sec)");
    for (size_t exponent = min_exponent; exponent < max_exponent; ++exponent) {
        float density = 1.f / (1 << (exponent - min_exponent));
        float time = test_iterator(exponent, density);
        POMAGMA_INFO(std::setw(12) << exponent << std::setw(12) << time);
    }

    return 0;
}
