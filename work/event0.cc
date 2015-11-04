#include <cstdlib>
#include <iostream>
#include <memory>

#include "event.hh"
#include "program.hh"

using namespace alxs;

using std::unique_ptr;

//------------------------------------------------------------------------------

static double const RAND_MUL = 1. / RAND_MAX;

int
main()
{
  srandom(time(nullptr));

  evt::Reactor reactor;
 
  auto now = evt::now();
  for (int i = 0; i < 12; ++i) {
    double const r = int(random() * RAND_MUL * 100) * 0.02;
    reactor.add_timer(
      now + r, 
      [=] () { std::cout << evt::now() - now << " timer " << i << " @ " << r << std::endl; });
  }

  run::ProcessProgramSpec spec;
  spec.executable_ = "/bin/sleep";
  spec.args_.push_back("1");
  auto program = spec.start();

  reactor.set_wait(
    program->get_pid(), 
    [&program] () {
      assert(program->is_done());
      auto result = program->get_result();
      std::cout << "result: " << *result << std::endl;
    });

  reactor.set_signal(SIGUSR1, [] () { std::cerr << "SIGUSR1\n"; });

  while (! reactor.is_empty())
    reactor.run();

  return 0;
}


