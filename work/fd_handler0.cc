#include <iostream>

#include "fd_handler.hh"

int
main()
{
  alxs::run::CaptureFdHandler fh1(1);
  alxs::run::DupFdHandler fh2(2, 1);
  
  fh1.start();
  fh2.start();
  std::cout << "Hello, world!\n";
  std::cerr << "err0\n";
  std::cout << "This is a test.\n";
  std::cerr << "err1\n";
  std::cout << "The end." << std::endl;
  fh2.restore();
  std::cout << "Really, the end." << std::endl;
  std::cerr << "err2\n";
  fh1.restore();

  std::cout << "STANDARD OUTPUT:\n" << fh1.get() << std::endl;
  // std::cout << "STANDARD ERROR:\n" << fh2.get() << std::endl;

  return 0;
}
