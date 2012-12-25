
class hid_t;

namespace pomagma
{

class Structure
{
public:

    Structure (Carrier & carrier);

    void declare (const std::string & name, BinaryRelation & rel);
    void declare (const std::string & name, NullaryFunction & fun);
    void declare (const std::string & name, InjectiveFunction & fun);
    void declare (const std::string & name, BinaryFunction & fun);
    void declare (const std::string & name, SymmetricFunction & fun);

    void load (const std::string & filename);
    void dump (const std::string & filename);

private:

    void dump_binary_functions (const hid_t & file_id);

    // ...data structures...
};

} // namespace pomagma
