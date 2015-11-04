#include <cstdlib>
#include <sstream>
#include <string>

#include "printable.hh"

using namespace alxs;

using std::cout;
using std::string;

//------------------------------------------------------------------------------

template<typename T> inline void 
show(
  string const& name,
  T const& val)
{
  cout << "'" << name << "' = '" << to_string(val) << "'\n";
}


template<> inline void
show<string>(
  string const& name,
  string const& val)
{
  cout << "'" << name << "' = '" << val << "' (string)\n";
}


int 
main()
{
  cout << to_string("hello") << "\n";
  char const* const strp = "Hello, world.";
  cout << to_string(string("This is a string.")) << "\n";
  cout << to_string(strp) << "\n";
  cout << to_string(42) << "\n";
  cout << to_string(3.1415) << "\n";
  cout << to_string(true) << "\n";
  cout << to_string(& std::cout) << "\n";
  cout << "\n";

  string const name = "name";
  string const value = "value";
  show(name, 0);
  show(name, 0.5);
  show(name, true);
  show(name, "Hello.");
  show(name, value);
  show("name (literal)", 0);
  show("name (literal)", 0.5);
  show("name (literal)", true);
  show("name (literal)", "Hello.");
  show("name (literal)", value);

  return EXIT_SUCCESS;
}

