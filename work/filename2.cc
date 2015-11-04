#include <cassert>
#include <cstdlib>
#include <iostream>

#include "filename.hh"

using namespace alxs;

void 
summarize(
  fs::Filename const& filename, 
  std::ostream& os=std::cout)
{
  os << "filename '" << filename << "':\n"
     << "dir: " << filename.dir() << "  base: " << filename.base() << "\n"
     << "parts: ";
  for (auto part : fs::get_parts(filename))
    os << part << " ";
  os << "\n";
  os << "\n";
}


int 
main(
  int argc, 
  char const* const* argv)
{
  assert(argc == 2);

  fs::Filename const fn0(argv[1]);
  summarize(fn0);
  summarize(expand_links(fn0));
  return EXIT_SUCCESS;
}


