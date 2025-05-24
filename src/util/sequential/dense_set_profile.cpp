#include <pomagma/util/sequential/dense_set.hpp>

using namespace pomagma;
using namespace sequential;

rng_t rng;

double test_iterator(size_t exponent, float density, size_t iters = 10000) {
    size_t item_count = (1 << exponent) - 1;
    DenseSet set(item_count);
    std::bernoulli_distribution randomly_insert(density);
    for (size_t i = 1; i <= item_count; ++i) {
        if (randomly_insert(rng)) {
            set.insert(i);
        }
    }

    size_t count __attribute__((unused)) = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        for (auto iter = set.iter(); iter.ok(); iter.next()) {
            ++count;
        }
    }
    return iters / timer.elapsed();
}

double test_iterator2(size_t exponent, float density, size_t iters = 10000) {
    size_t item_count = (1 << exponent) - 1;
    DenseSet set1(item_count);
    DenseSet set2(item_count);
    std::bernoulli_distribution randomly_insert(density);
    for (size_t i = 1; i <= item_count; ++i) {
        if (randomly_insert(rng)) set1.insert(i);
        if (randomly_insert(rng)) set2.insert(i);
    }

    size_t count __attribute__((unused)) = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        for (auto iter = set2.iter_insn(set2); iter.ok(); iter.next()) {
            ++count;
        }
    }
    return iters / timer.elapsed();
}

double test_equal(size_t exponent, float density, size_t iters = 10000) {
    size_t item_count = (1 << exponent) - 1;
    DenseSet set(item_count);
    std::bernoulli_distribution randomly_insert(density);
    for (size_t i = 1; i <= item_count; ++i) {
        if (randomly_insert(rng)) set.insert(i);
    }

    size_t count __attribute__((unused)) = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        // operator== is usually called with actually equal sets
        count += (set == set);
    }
    return iters / timer.elapsed();
}

double test_likely_disjoint(size_t exponent, float density,
                            size_t iters = 10000) {
    size_t item_count = (1 << exponent) - 1;
    DenseSet set1(item_count);
    DenseSet set2(item_count);
    std::bernoulli_distribution randomly_insert(density);
    for (size_t i = 1; i <= item_count; ++i) {
        if (randomly_insert(rng)) set1.insert(i);
        if (randomly_insert(rng)) set2.insert(i);
    }

    // likely_disjoint is usually called with actually disjoint sets
    set2 -= set1;

    size_t count __attribute__((unused)) = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        count += set1.likely_disjoint(set2);
    }
    return iters / timer.elapsed();
}

double test_unlikely_disjoint(size_t exponent, float density,
                              size_t iters = 10000) {
    size_t item_count = (1 << exponent) - 1;
    DenseSet set1(item_count);
    DenseSet set2(item_count);
    std::bernoulli_distribution randomly_insert(density);
    for (size_t i = 1; i <= item_count; ++i) {
        if (randomly_insert(rng)) set1.insert(i);
        if (randomly_insert(rng)) set2.insert(i);
    }

    size_t count __attribute__((unused)) = 0;
    Timer timer;
    for (size_t i = 0; i < iters; ++i) {
        count += set1.unlikely_disjoint(set2);
    }
    return iters / timer.elapsed();
}

int main() {
    Log::Context log_context("sequential DenseSet profile");

    size_t min_exponent = 10;
    size_t max_exponent = 16;
    POMAGMA_INFO(std::setw(10)
                 << "log2(size)" << std::setw(10) << "iter(kHz)"
                 << std::setw(15) << "iter_insn(kHz)" << std::setw(15)
                 << "equal(kHz)" << std::setw(20) << "likely_disjoint(kHz)"
                 << std::setw(20) << "unlikely_disj(kHz)");
    for (size_t exponent = min_exponent; exponent < max_exponent; ++exponent) {
        float density = 1.f / (1 << (exponent - min_exponent));
        float freq1 = test_iterator(exponent, density) / 1000;
        float freq2 = test_iterator2(exponent, density) / 1000;
        float freq3 = test_equal(exponent, density) / 1000;
        float freq4 = test_likely_disjoint(exponent, 0.5) / 1000;
        float freq5 = test_unlikely_disjoint(exponent, 0.5) / 1000;
        POMAGMA_INFO(std::setw(15)
                     << exponent << std::setw(15) << freq1 << std::setw(15)
                     << freq2 << std::setw(15) << freq3 << std::setw(15)
                     << freq4 << std::setw(15) << freq5);
    }

    return 0;
}
