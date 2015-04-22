#pragma once

namespace pomagma
{

void load_signature (const std::string & filename);
void load_structure (const std::string & filename);
void dump_structure (const std::string & filename);
void load_programs (const std::string & filename);
void load_language (const std::string & filename);
void validate_consistent ();
void validate_all ();
void log_cleanup_stats ();
void log_stats ();

} // namespace pomagma

