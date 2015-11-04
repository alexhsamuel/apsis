#include <algorithm>
#include <cassert>
#include <iostream>
#include <map>
#include <string>
#include <vector>

#include "param.hh"

//------------------------------------------------------------------------------

static const char ARG_SEP = '=';

//------------------------------------------------------------------------------

std::ostream& operator<<(std::ostream& os, const Params& params)
{
  os << '(';
  bool first = true;
  for (Params::const_iterator i = params.begin(); i != params.end(); ++i) {
    if (first) 
      first = false;
    else
      os << ", ";
    os << *i;
  }
  os << ')';
  return os;
}


std::pair<Param, Arg> parse_arg(const std::string& str)
{
  size_t eq = str.find(ARG_SEP);
  if (eq == std::string::npos)
    throw ParseError("missing separator", str);
  else {
    const Param param = str.substr(0, eq);
    const Arg arg = str.substr(eq + 1, std::string::npos);
    return std::pair<Param, Arg>(param, arg);
  }
}


Args bind(const Params& params, const Args& args)
{
  Args bound;

  // Scan through params, matching an arg to each.
  for (Params::const_iterator iter = params.begin();
       iter != params.end();
       ++iter) {
    Args::const_iterator match = args.find(*iter);
    if (match == args.end())
      // No matching argument.
      throw MissingArgError(*iter);
    else 
      // Matching arg.
      bound[*iter] = match->second;
  }

  if (args.size() != params.size()) {
    // Length mismatch; there must be extra arguments.  Look for the first arg
    // that doesn't match a param.
    for (Args::const_iterator iter = args.begin(); 
         iter != args.end(); 
         ++iter) 
      if (std::find(params.begin(), params.end(), iter->first) 
          == params.end()) 
        throw ExtraArgError(iter->first);
    assert(false);  // Unreachable.
  }

  return bound;
}


//------------------------------------------------------------------------------

Args Args::from_argv(int argc, char const* const* argv)
{
  Args args;
  for (int i = 1; i < argc; ++i) {
    std::pair<Param, Arg> pair = parse_arg(argv[i]);
    args[pair.first] = pair.second;
  }
  return args;
}


template<>
std::string Args::get<std::string>(std::string const& param) const
{
  auto i = find(param);
  if (i == end())
    throw MissingArgError(param);
  else
    return i->second;
}


template<>
long Args::get<long>(std::string const& param) const
{
  std::string const arg = get<std::string>(param);

  // FIXME: Not thread-safe.
  errno = 0;
  char* end;
  long const val = strtol(arg.c_str(), &end, 10);
  if (errno == 0 && *end == '\0') 
    return val;
  else
    throw ArgTypeError(param, "long", arg);
}


template<>
double Args::get<double>(std::string const& param) const
{
  std::string const arg = get<std::string>(param);

  // FIXME: Not thread-safe.
  errno = 0;
  char* end;
  double const val = strtod(arg.c_str(), &end);
  if (errno == 0 && *end == '\0')
    return val;
  else
    throw ArgTypeError(param, "double", arg);
}


