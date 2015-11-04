#include <iostream>
#include <sstream>

#include "printable.hh"

using namespace alxs;

//------------------------------------------------------------------------------

class PrintableTest 
  : public Printable
{
public:

  PrintableTest(int x)
    : x_(x)
  {
  }

  virtual void print(std::ostream& os) const;

private:

  const int x_;

};


void PrintableTest::print(std::ostream& os) const
{
  std::cerr << "PrintableTest::print()\n";
  os << "<[" << x_ << "]>";
}


int main()
{
  const PrintableTest pt(42);
  std::ostringstream ss;
  ss << pt;
  std::cout << ss.str() << "\n";
}

