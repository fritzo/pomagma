
#include "util.hpp"
#include "dense_sym_fun.hpp"
#include <vector>

using pomagma::Log;
using pomagma::dense_sym_fun;

//eg: f(x,y) = gcd(x,y)
unsigned gcd (unsigned n,unsigned m) { return m==0 ? n : gcd(m,n%m); }

void test_dense_sym_fun (unsigned N)
{
    POMAGMA_INFO("Defining function");
    dense_sym_fun fun(N);
    for (unsigned i=1; i<=N; ++i) {
    for (unsigned j=i; j<=N; ++j) {
        unsigned k = gcd(i,j);
        if (k <= 1) continue;
        fun.insert(i,j,k);
    } }

    POMAGMA_INFO("Checking function values");
    std::vector<unsigned> line_size(N+1);
    for (unsigned i=1; i<=N; ++i) { line_size[i] = 0;
    for (unsigned j=1; j<=N; ++j) {
        int k = gcd(i,j);
        if (k <= 1) {
            POMAGMA_ASSERT(0, not fun.contains(i,j),
                    "function contains bad pair " << i << ',' << j);
        } else {
            POMAGMA_ASSERT(0, fun.contains(i,j),
                    "function does not contain good pair " << i << ',' << j);
            POMAGMA_ASSERT(0, fun.get_value(i,j) == k,
                    "function contains wrong value for " << i << ',' << j);
            ++line_size[i];
        }
    } }

    POMAGMA_INFO("Checking line iterators");
    dense_sym_fun::Iterator iter(&fun);
    for (unsigned i=1; i<=N; ++i) {
        unsigned line_size_i = 0;
        for (iter.begin(i); iter; iter.next()) {
            unsigned j = iter.moving();
            unsigned k = iter.value();
            POMAGMA_ASSERT(0, gcd(i,j) == k and k >= 1,
                    "iterator gave wrong function value for " << i << ',' << j);
            ++line_size_i;
        }
        POMAGMA_ASSERT(0, line_size[i] == line_size_i,
                "line sizes disagree: "
                << line_size[i] << " != " << line_size_i);
    }

    POMAGMA_INFO("Validating");
    fun.validate();
}

int main ()
{
    Log::title("Running Dense Symmetric Function Test");

    test_dense_sym_fun(3 + (1<<9));

    return 0;
}

