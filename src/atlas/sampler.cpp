#include "sampler.hpp"
#include "nullary_function.hpp"
#include "injective_function.hpp"
#include "binary_function.hpp"
#include "symmetric_function.hpp"
#include <pomagma/util/sampler_impl.hpp>

namespace pomagma
{

inline Ob Sampler::Policy::sample (Ob val)
{
    if (val) {
        bool_ref contained = m_set(val);
        if (likely(contained.load())) {
            return val;
        } else {
            POMAGMA_ASSERT_LT(m_size, m_capacity);
            contained.one();
            m_size += 1;
            throw ObInsertedException(val);
        }
    } else {
        throw ObRejectedException();
    }
}

inline Ob Sampler::Policy::sample (
		const NullaryFunction & fun)
{
    return sample(fun.find());
}

inline Ob Sampler::Policy::sample (
		const InjectiveFunction & fun,
        Ob key)
{
    return sample(fun.find(key));
}

inline Ob Sampler::Policy::sample (
		const BinaryFunction & fun,
        Ob lhs,
        Ob rhs)
{
    return sample(fun.find(lhs, rhs));
}

inline Ob Sampler::Policy::sample (
		const SymmetricFunction & fun,
        Ob lhs,
        Ob rhs)
{
    return sample(fun.find(lhs, rhs));
}

} // namespace pomagma
