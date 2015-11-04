#include <cstdlib>
#include <iostream>
#include <memory>
#include <sstream>
#include <unistd.h>

#include "file.hh"
#include "json.hh"

using namespace alxs;
using namespace alxs::json;

using std::string;

int 
main()
{
  Json obj = parse(fs::load_text(STDIN_FILENO));
  obj.print(std::cout, 2);
  std::cout << std::flush;

  return EXIT_SUCCESS;
}


