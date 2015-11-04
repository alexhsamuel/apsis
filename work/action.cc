#include <cassert>
#include <cstdlib>
#include <iostream>
#include <memory>
#include <sys/time.h>

#include "action.hh"
#include "proc.hh"

//------------------------------------------------------------------------------

/**
 * Seeds the C library PRNG rand() from high-resolution time of day.
 */
void seed_rand()
{
  struct timeval tv;
  const int ret = gettimeofday(&tv, NULL);
  assert(ret == 0);
  srand(tv.tv_sec + tv.tv_usec);
}


int main(int argc, char** argv)
{
  seed_rand();

  {
    const RandomAction action;
    const Params params = action.get_params();
    const Args args = Args::from_argv(argc, argv);
    std::unique_ptr<Outcome> outcome(action.run(args));
    std::cout << "outcome: " << *outcome << std::endl;
  }

  return EXIT_SUCCESS;
}


