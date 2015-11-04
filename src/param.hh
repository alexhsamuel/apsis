#ifndef __param_hh__
#define __param_hh__

#include <map>
#include <string>
#include <vector>

//------------------------------------------------------------------------------

typedef std::string Param;

class Params
  : public std::vector<Param> 
{
};


extern std::ostream& operator<<(std::ostream&, const Params& params);

typedef std::string Arg;

class Args
  : public std::map<Param, Arg>
{
public:

  static Args from_argv(int argc, char const* const* argv);

  template<typename T> T get(std::string const& param) const;

};


//------------------------------------------------------------------------------

class MissingArgError 
  : public std::exception
{
public:

  MissingArgError(const Param& param)
    : param_(param) 
  {} 

  virtual ~MissingArgError() throw ()
  {}

  const Param& get_param() { return param_; }

private:

  const Param param_;

};


class ExtraArgError
  : public std::exception
{
public:

  ExtraArgError(const Param& param)
    : param_(param)
  {
  }

  virtual ~ExtraArgError() throw () {}

  const Param& get_param() { return param_; }

private:

  const Param param_;

};


class ParseError 
  : public std::exception
{
public:

  ParseError(const std::string message, const std::string str)
    : message_(message),
      str_(str)
  {}

  ~ParseError() throw () {}

private:

  const std::string message_;
  const std::string str_;

};


class ArgTypeError
  : std::exception
{
public:

  ArgTypeError(
    const std::string& param, const std::string& type, const std::string& arg)
    : param_(param),
      type_(type),
      arg_(arg)
  {
  }

  virtual ~ArgTypeError() throw () {}

private:

  const std::string param_;
  const std::string type_;
  const std::string arg_;

};


extern Args bind(const Params& params, const Args& args);


//------------------------------------------------------------------------------

#endif  // #ifndef __param_hh__
