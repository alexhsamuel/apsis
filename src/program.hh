#pragma once

#include <cassert>
#include <map>
#include <memory>
#include <sstream>
#include <string>
#include <vector>

#include "env.hh"
#include "fd_handler.hh"
#include "json.hh"
#include "printable.hh"
#include "string.hh"
#include "xsys.hh"

//------------------------------------------------------------------------------

namespace alxs {
namespace run {

class Result
  : public Printable,
    public json::Serializable
{
public:

  virtual ~Result() {}
  virtual void print(std::ostream& os) const;
  virtual void pretty_print(std::ostream& os) const;
  virtual json::Json to_json() const;

  std::string get(std::string const& name) const;
  template<typename T> void set(std::string const& name, T const& val);

private:

  std::map<std::string, std::string> more_;

};


template<typename T> inline void
Result::set(
  std::string const& name, 
  T const& val) 
{ 
  set(name, to_string(val));
}


template<> inline void
Result::set<std::string>(
  std::string const& name, 
  std::string const& val) 
{ 
  more_[name] = val;
}


//------------------------------------------------------------------------------

struct EnvSpec
  : public json::Serializable
{
  EnvSpec();

  virtual json::Json to_json() const;
  static EnvSpec from_json(json::Json const& json);

  std::unique_ptr<sys::Environment> build() const;

  bool keep_all_;
  std::vector<std::string> keep_;
  std::vector<std::string> unset_;
  std::map<std::string, std::string> set_;

};


//------------------------------------------------------------------------------

struct FdHandlerSpec
  : public json::Serializable
{
  FdHandlerSpec(std::string const& type_="leave");

  virtual json::Json to_json() const;
  static std::unique_ptr<FdHandlerSpec> from_json(json::Json const& json);

  std::unique_ptr<FdHandler> build(int fd) const;

  std::string type_;
  int from_fd_;
  fs::Filename filename_;
  mode_t mode_;

  // FIXME: Support better (mode general) mode specification for "file" type.

};


//------------------------------------------------------------------------------

class Program
{
public:

  virtual ~Program() {}

  virtual bool is_done() const = 0;
  virtual std::unique_ptr<Result> get_result() = 0;  

};


//------------------------------------------------------------------------------

class ProgramSpec
  : public json::Serializable
{
public:

  static std::unique_ptr<ProgramSpec> from_json(json::Json const& json);

  virtual ~ProgramSpec() {}

  // Base json::Serializable.
  virtual json::Json to_json() const = 0;

  virtual std::unique_ptr<Program> start() const = 0;

};


//------------------------------------------------------------------------------

class ProcessProgramSpec;


class ProcessProgram
  : public Program
{
public:

  typedef ProcessProgramSpec Spec;

  ProcessProgram(Spec const& spec);
  virtual ~ProcessProgram() {}

  // Base Program.
  virtual bool is_done() const;
  virtual std::unique_ptr<Result> get_result(); 

  pid_t get_pid() const { return pid_; }

private:

  pid_t pid_;
  bool waited_;

  std::unique_ptr<FdHandler> stdin_;
  std::unique_ptr<FdHandler> stdout_;
  std::unique_ptr<FdHandler> stderr_;

  int status_;
  rusage usage_;

};


class ProcessProgramSpec
  : public json::Serializable
{
public:

  typedef std::vector<std::string> Argv;

  static std::string const JSON_TYPE_NAME;
  static std::unique_ptr<ProcessProgramSpec> from_json(json::Json const& json);

  ProcessProgramSpec();
  virtual ~ProcessProgramSpec() {};

  virtual json::Json to_json() const;
  virtual std::unique_ptr<ProcessProgram> start() const;

  std::string executable_;
  Argv args_;
  EnvSpec env_;
  FdHandlerSpec stdin_;
  FdHandlerSpec stdout_;
  FdHandlerSpec stderr_;
  
};


//------------------------------------------------------------------------------

extern void wait(Program& prog);

//------------------------------------------------------------------------------

}  // namespace run
}  // namespace alxs

