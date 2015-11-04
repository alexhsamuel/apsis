#include <cstdlib>
#include <cstring>
#include <memory>

#include "env.hh"

extern "C" char** environ;
  
namespace alxs {
namespace sys {

//------------------------------------------------------------------------------

void Environment::get_proc_env()
{
  for (char const* const* ptr = environ; *ptr != NULL; ++ptr) {
    char const* const eq = strchr(*ptr, '=');
    if (eq == NULL) 
      // Wonky environment variable.
      std::cerr << "unconventional environ entry '" << ptr << "'\n";
    else {
      std::string const name(*ptr, eq - *ptr);
      std::string const val(eq + 1);
      (*this)[name] = val;
      // at(name) = val;
    }
  }
}


Environment::Buffer::Buffer(Environment const& env)
  : buf_(build(env))
{
}


std::unique_ptr<char[]> Environment::Buffer::build(Environment const& env)
{
  // We construct the environ in a single allocation.  The main NULL-terminated
  // array of variable pointers is at the beginning, followed by "NAME=VAL\0"
  // entries for the individual entries following.

  // Calculate the total allocation length.
  size_t alloc = (env.size() + 1) * sizeof(char*);
  for (auto i : env)
    // Room for the variable name, value, =, and NUL.
    alloc += i.first.length() + 1 + i.second.length() + 1;

  std::unique_ptr<char[]> buf(new char[alloc]);
  // The location of the next variable pointer.
  char** vars = (char**) buf.get();
  // The location of the next variable entry.  
  char* var = (char*) (vars + env.size() + 1);

  for (auto i : env) {
    std::string const& name = i.first;
    std::string const& val = i.second;
    // Construct the "NAME=VAL\0" string.
    strncpy(var, name.c_str(), name.length());
    var[name.length()] = '=';
    strcpy(var + name.length() + 1, val.c_str());
    // Add the pointer to this entry.
    *vars++ = var;
    // Advance.
    var += name.length() + 1 + val.length() + 1;
  }
  assert(var == (char*) buf.get() + alloc);
  // NULL-terminate the array of variables.
  *vars = NULL;

  return buf;
}


Environment::Buffer::~Buffer()
{
}


std::ostream& operator<<(std::ostream& os, Environment const& env)
{
  for (auto var : env)
    os << var.first << '=' << var.second << '\n';
  return os;
}


//------------------------------------------------------------------------------

}  // namespace sys
}  // namespace alxs

