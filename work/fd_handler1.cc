#include <iostream>

#include "program.hh"
#include "fd_handler.hh"

using namespace alxs;

using std::unique_ptr;

int
main()
{
  run::FdHandlerSpec fhs1("capture");
  run::FdHandlerSpec fhs2("dup");
  fhs2.from_fd_ = 1;
  std::cout << fhs1.to_json() << "\n"
            << fhs2.to_json() << "\n";

  unique_ptr<run::FdHandler> fh1 = fhs1.build(1);
  unique_ptr<run::FdHandler> fh2 = fhs2.build(2);
  
  fh1->start();
  fh2->start();
  std::cout << "Hello, world!\n";
  std::cerr << "err0\n";
  std::cout << "This is a test.\n";
  std::cerr << "err1\n";
  std::cout << "The end." << std::endl;
  fh2->restore();
  std::cout << "Really, the end." << std::endl;
  std::cerr << "err2\n";
  fh1->restore();

  run::CaptureFdHandler* p = dynamic_cast<run::CaptureFdHandler*>(fh1.get());
  std::cout << "STANDARD OUTPUT:\n" << p->get() << std::endl;
  // std::cout << "STANDARD ERROR:\n" << fh2->get() << std::endl;

  return 0;
}
