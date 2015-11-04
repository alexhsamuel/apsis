#include <cstdlib>
#include <iostream>

#include "tzfile.hh"

using namespace alxs;

int
main(
  int argc,
  char const* const* argv)
{
  if (argc != 2) {
    std::cerr << "Usage: " << argv[0] << " FILENAME\n";
    return EXIT_FAILURE;
  }

  cron::TzFile tz_file;
  try {
    tz_file = cron::TzFile::load(fs::Filename(argv[1]));
  }
  catch (FormatError err) {
    std::cerr << err.what() << "\n";
    return EXIT_FAILURE;
  }

  std::cout << tz_file << std::endl;
  return EXIT_SUCCESS;
}


