#include <iostream>
#include <memory>
#include <vector>

#include "json.hh"
#include "program.hh"

using namespace alxs;

using std::string;
using std::unique_ptr;

int main()
{
  run::ProcessProgramSpec spec;
  spec.executable_ = "/bin/ls";
  spec.args_ = std::vector<string>{"/home/samuel"};

  json::Json json0 = spec.to_json();
  std::cout << json0 << "\n" << std::endl;

  unique_ptr<run::ProcessProgram> prog = spec.start();
  // FIXME: Don't spin.
  while (! prog->is_done())
    ;

  unique_ptr<run::Result> result = prog->get_result();
  std::cout << *result << "\n" << std::endl;
  json::Json json1 = result->to_json();
  std::cout << json1 << "\n" << std::endl;

  return 0;
}


