#include <iostream>
#include <memory>
#include <vector>

#include "file.hh"
#include "filename.hh"
#include "json.hh"
#include "program.hh"
#include "xsys.hh"

using namespace alxs;

using std::string;
using std::unique_ptr;

int 
main(
  int argc,
  char const* const* argv)
{
  if (argc != 2) {
    std::cerr << "usage: " << argv[0] << " JSON-PROGRAM\n";
    exit(1);
  }
  fs::Filename const filename(argv[1]);

  json::Json obj = json::parse(fs::load_text(filename));
  unique_ptr<run::ProgramSpec> spec = run::ProgramSpec::from_json(obj);
  if (false) {
    spec->to_json().print(std::cout, 2);
    std::cout << "\n" << std::endl;
  }

  unique_ptr<run::Program> prog = spec->start();
  // FIXME: Don't spin.
  while (! prog->is_done())
    ;

  unique_ptr<run::Result> result = prog->get_result();
  result->to_json().print(std::cout, 2);
  std::cout << std::endl;

  return 0;
}


