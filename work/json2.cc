#include <cstdlib>
#include <iostream>

#include "json.hh"

using alxs::json::Json;

void
test()
{
  Json v0 = Json::OBJ;
  v0["foo"] = 42.0;
  v0["bar"] = true;
  {
    Json v1 = Json::OBJ;
    v1["Mercury"] = Json::NUL;
    v1["Venus"] = 0.000000000004;
    v1["Earth"] = Json::OBJ;
    {
      Json v2 = Json::OBJ;
      v2["Wyoming"] = "Hello, world!";
      v2["Montanan"] = "Hi.\nThis is a test.\n";
      v2["Idaho"] = Json::NUL;
      v1["Mars"] = std::move(v2);
    }
    v1["Saturn"] = Json::ARR;
    v0["baz"] = std::move(v1);
  }
  {
    Json v3 = Json::ARR;
    v3[0] = -1;
    v3[1] = 3.14159;
    v3[2] = 0;
    v3[3] = Json::NUL;
    v3[4] = Json::OBJ;
    v0["bif"] = std::move(v3);
  }

  std::cout << v0 << std::endl;
}


int 
main(
  int argc,
  char const* const* argv)   
{
  size_t const NUM = argc == 1 ? 1 : atoi(argv[1]);

  for (size_t i = 0; i < NUM; ++i)
    test();
  return EXIT_SUCCESS;
}


