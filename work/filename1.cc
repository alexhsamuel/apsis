#include <cassert>
#include <cstdlib>
#include <iostream>

#include "filename.hh"

using namespace alxs;

std::string const NORM_TEST[] = {
  "",
  "foo",
  "foo/bar",
  "foo/bar/baz",
  "foo//bar/baz",
  "foo/bar///baz",
  "foo/bar/baz//////",
  "/",
  "/foo",
  "/foo/bar",
  "/foo/bar/baz",
  "/foo/bar/baz/",
  "//foo/bar/baz",
  "/foo//bar/baz",
  "/foo/bar/baz//",
  "/foo////bar/baz////",
  "////foo///bar//baz/bif/bum",
  ".",
  "/.",
  "/./",
  "/.//",
  "/foo/.",
  "/foo/./",
  "/foo/./bar",
  "/foo/./././bar/./baz/.",
  "..",
  "../..",
  "../../foo/bar",
  "../../foo/../bar/baz",
  "/..",
  "//..",
  "/../",
  "/..//",
  "/../..//..//../././/../../.././..////..//./",
  "/foo/..",
  "/foo//..",
  "/foo/../",
  "/foo/../bar",
  "/foo/bar/..",
  "/foo/bar/../",
  "/foo/bar/../..",
  "/foo/bar/../../..",
  "/foo/bar/baz/../../bif/../bim",
  "/foo/bar/baz/../bif/bim/../../boo/",
  "/foo/bar/baz/../bif/bim/../../boo/..//../bux",
};
  

int main(int argc, char const* const* argv)
{
  for (auto test : NORM_TEST)
    std::cout << test << " -> " << fs::Filename::normalize(test) << "\n";

  return EXIT_SUCCESS;
}

