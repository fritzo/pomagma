#include "aggregator.hpp"
#include "carrier.hpp"
#include <unordered_map>

namespace pomagma
{

class PartialIsomorphism
{
    Structure & m_dom;
    Structure & m_cod;

    typedef std::unordered_map<Ob, Ob> Map;
    Map m_fwd;
    Map m_bwd;

public:

    PartialIsomorphism (
            Structure & dom,    // smaller
            Structure & cod)    // larger
        : m_dom(dom),
          m_cod(cod)
    {
    }

    bool empty () const { return m_fwd.empty(); }
    void clear () { m_fwd.clear(); m_bwd.clear(); }

    void unify ()
    {
        TODO("find a maximal map dom -> cod, possibly merging pairs in both");
    }

    bool try_complete ()
    {
        TODO("for each x in dom, create a f(x) in cod unless cod is full");
    }

    bool try_complete_naive ();

private:

    void insert (Ob cod_ob, Ob dom_ob)
    {
        m_fwd.insert(Map::value_type(dom_ob, cod_ob));
        m_bwd.insert(Map::value_type(cod_ob, dom_ob));
    }

    void dom_merge_callback (Ob dom_dep, Ob dom_rep)
    {
        auto dep_i = m_fwd.find(dom_dep);
        if (dep_i == m_fwd.end()) { return; }
        Ob cod_dep = dep_i->second;
        m_fwd.erase(dep_i);
        m_bwd.erase(cod_dep);

        auto rep_i = m_fwd.find(dom_rep);
        if (rep_i == m_fwd.end()) {
            insert(dom_rep, cod_dep);
        } else {
            Ob cod_rep = rep_i->second;
            if (cod_rep != cod_dep) {
                TODO("m_cod.merge(cod_dep, cod_rep);");
            }
        }
    }

    void cod_merge_callback (
            Ob cod_dep __attribute__((unused)),
            Ob dom_dep __attribute__((unused)))
    {
        TODO("copy from dom_merge_callback");
    }
};

bool PartialIsomorphism::try_complete_naive ()
{
    size_t cod_required_item_dim
        = m_cod.carrier().item_count()
        + m_dom.carrier().item_count()
        - m_fwd.size();
    if (cod_required_item_dim > m_cod.carrier().item_dim()) {
        return false;
    }

    for (auto i = m_dom.carrier().iter(); i.ok(); i.next()) {
        if (m_fwd.find(*i) == m_fwd.end()) {
            insert(*i, m_cod.carrier().unsafe_insert());
        }
    }
    POMAGMA_ASSERT_EQ(cod_required_item_dim, m_cod.carrier().item_dim());

    TODO("register merge functions");
    TODO("enforce all equations in dom");
    TODO("enforce all equations in cod");
}

void aggregate (
        Structure & destin,
        Structure & src)
{
    POMAGMA_ASSERT(& destin != & src, "cannot merge structure into self");

    PartialIsomorphism iso(src, destin);
    iso.unify();
    while (not iso.try_complete()) {
        TODO("resize destin");
    }
}

} // namespace pomagma
