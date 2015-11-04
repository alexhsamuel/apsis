#include <algorithm>
#include <cassert>
#include <iostream>

#include "file.hh"
#include "filename.hh"
#include "json.hh"
#include "program.hh"
#include "xsys.hh"

using namespace alxs::json;

using std::string;
using std::unique_ptr;

namespace alxs {
namespace run {

//------------------------------------------------------------------------------

void
Result::print(
  std::ostream& os)
  const
{
  os << "Result[";
  bool first = true;
  for (auto iter : more_) {
    if (first)
      first = false;
    else
      os << ", ";
    os << iter.first << "=" << iter.second;
  }
  os << "]";
}


class repeat
  : public Printable
{
public:

  repeat(char character, size_t num) : character_(character), num_(num) {}

  virtual void print(
    std::ostream& os)
    const
  {
    for (size_t i = 0; i < num_; ++i)
      os << character_;
  }

private:

  char character_;
  size_t num_;

};


void
Result::pretty_print(
  std::ostream& os)
  const
{
  os << "Result:\n";
  for (auto i : more_)
    if (i.second.find('\n') == string::npos)
      os << "- " << i.first << " = " << i.second << '\n';
    else
      os << "- " << i.first << ' ' << repeat('-', 77 - i.first.length()) << '\n'
         << i.second << '\n'
         << repeat('-', 80) << '\n';
}


Json
Result::to_json()
  const
{
  using namespace json;

  Json json = Json::OBJ;
  for (auto iter : more_)
    json[iter.first] = iter.second;
  return json;
}


string 
Result::get(
  string const& name) 
  const
{
  auto iter = more_.find(name);
  if (iter == more_.end())
    throw NameError(name);
  else
    return iter->second;
}


//------------------------------------------------------------------------------

EnvSpec::EnvSpec()
  : keep_all_(true)
{
}


json::Json
EnvSpec::to_json()
  const
{
  Json json = Json::OBJ;
  if (keep_all_)
    json["keep"] = true;
  else if (keep_.size() == 0)
    json["keep"] = false;
  else {
    Json keep = Json::ARR;
    for (auto var : keep_)
      keep[keep.size()] = var;
    json["keep"] = std::move(keep);
  }
  Json unset = Json::ARR;
  for (auto var : unset_)
    unset[unset.size()] = var;
  json["unset"] = std::move(unset);
  Json set = Json::OBJ;
  for (auto var : set_)
    set[var.first] = var.second;
  json["set"] = std::move(set);
  return json;
}


EnvSpec
EnvSpec::from_json(
  Json const& json)
{
  EnvSpec spec;
  if (json.has("keep")) {
    Json const& keep = json["keep"];
    if (keep.get_type() == Json::TRU || keep.get_type() == Json::FAL)
      spec.keep_all_ = keep.get_bool();
    else {
      spec.keep_all_ = false;
      for (auto const& name : keep.get_arr())
        spec.keep_.push_back(name.get_str());
    }
  }
  if (json.has("unset")) 
    for (auto const& name : json["unset"].get_arr())
      spec.unset_.push_back(name.get_str());
  if (json.has("set")) 
    for (auto const& ent : json["set"].get_obj())
      spec.set_[ent.first] = ent.second.get_str();
  return spec;
}


unique_ptr<sys::Environment>
EnvSpec::build()
  const
{
  unique_ptr<sys::Environment> envp(new sys::Environment);
  sys::Environment& env = *envp.get();

  // Possibly, keep variables from the process environment.
  if (keep_all_)
    // Keep all variables.
    env.get_proc_env();
  else if (keep_.size() > 0) {
    // Keep names variables only.
    sys::Environment proc_env;
    proc_env.get_proc_env();
    for (string const& name : keep_) {
      // Does this name exist in the process environment?
      auto find = proc_env.find(name);
      if (find != end(proc_env))
        // Yes.  Copy it over.
        env[name] = find->second;
    }
  }

  // Unset named variables.
  for (string const& name : unset_) 
    env.erase(name);

  // Explicitly set variables.
  for (auto const& ent : set_)
    env[ent.first] = ent.second;

  return envp;
}


//------------------------------------------------------------------------------

FdHandlerSpec::FdHandlerSpec(
  string const& type)
  : type_(type),
    from_fd_(1),
    filename_("/dev/null"),
    mode_(O_RDONLY)
{
}


Json
FdHandlerSpec::to_json()
  const
{
  using namespace json;

  Json json = Json::OBJ;
  json["type"] = type_;
  if (type_ == "dup")
    json["from_fd"] = from_fd_;
  else if (type_ == "file") {
    // FIXME: Stupid.
    string filename = filename_;
    json["filename"] = filename;
    json["mode"] = fs::mode_as_str(mode_);
  }
  return json;
}


unique_ptr<FdHandlerSpec>
FdHandlerSpec::from_json(
  Json const& json)
{
  unique_ptr<FdHandlerSpec> spec{new FdHandlerSpec};
  spec->type_ = 
    json.get_type() == Json::STR ? json.get_str() : json["type"].get_str();
  if (   spec->type_ == "leave"
      || spec->type_ == "close"
      || spec->type_ == "null"
      || spec->type_ == "capture")
    ;
  else if (spec->type_ == "dup")
    spec->from_fd_ = json["from_fd"].get_int();
  else if (spec->type_ == "file") {
    spec->filename_ = fs::Filename(json["filename"].get_str());
    spec->mode_ = json.has("mode") ? fs::mode_from_str(json["mode"].get_str()) : (O_RDWR | O_CREAT);
  }
  else
    throw TypeError(spec->type_);
  return spec;
}


unique_ptr<FdHandler>
FdHandlerSpec::build(
  int fd)
  const
{
  if (type_ == "leave")
    return unique_ptr<FdHandler>(new LeaveFdHandler(fd));
  else if (type_ == "close")
    return unique_ptr<FdHandler>(new CloseFdHandler(fd));
  else if (type_ == "null")
    return unique_ptr<FdHandler>(new NullFdHandler(fd));
  else if (type_ == "capture")
    return unique_ptr<FdHandler>(new CaptureFdHandler(fd));
  else if (type_ == "dup") 
    return unique_ptr<FdHandler>(new DupFdHandler(fd, from_fd_));
  else if (type_ == "file") 
    return unique_ptr<FdHandler>(new FileFdHandler(fd, filename_, mode_));
  else
    // FIXME
    assert(false);
}


//------------------------------------------------------------------------------

unique_ptr<ProgramSpec>
ProgramSpec::from_json(
  Json const& json)
{
  string const type = json["type"].get_str();
  if (type == ProcessProgramSpec::JSON_TYPE_NAME) {
    unique_ptr<ProcessProgramSpec> spec = ProcessProgramSpec::from_json(json);
    return unique_ptr<ProgramSpec>((ProgramSpec*) spec.release());
  }
  else
    // FIXME
    assert(false);
}


//------------------------------------------------------------------------------

ProcessProgram::ProcessProgram(
  Spec const& spec)
  : waited_(false),
    stdin_ (spec.stdin_ .build(STDIN_FILENO)),
    stdout_(spec.stdout_.build(STDOUT_FILENO)),
    stderr_(spec.stderr_.build(STDERR_FILENO))
{
  pid_t const child_pid = xfork();
  if (child_pid == 0) {
    // Child process.

    // Construct the argument vector.
    char const* argv[spec.args_.size() + 2];
    size_t i = 0;
    // The first argument conventionally is the executable name.
    // FIXME: Support overriding this.
    argv[i++] = spec.executable_.c_str();
    for (auto arg : spec.args_)
      argv[i++] = arg.c_str();
    // NULL-terminate it.
    argv[i++] = nullptr;

    // Construct the environment.
    unique_ptr<sys::Environment> env = spec.env_.build();
    sys::Environment::Buffer env_buffer(*env);
    char* const* const envp = const_cast<char* const*>(env_buffer.get());

    // Start file descriptor handling.
    stdin_ ->start(true);
    stdin_ ->close();
    stdout_->start(true);
    stdout_->close();
    stderr_->start(true);
    stderr_->close();

    // Invoke the executable.
    // FIXME: Handle failure.
    xexecve(spec.executable_.c_str(), const_cast<char* const*>(argv), envp);
  }
  else 
    // Parent process.
    pid_ = child_pid;
}


bool
ProcessProgram::is_done()
  const
{
  siginfo_t siginfo;
  siginfo.si_pid = 0;
  // FIXME: Check for stopped / continued?
  xwaitid(P_PID, pid_, & siginfo, WEXITED | WNOHANG | WNOWAIT);
  return siginfo.si_pid > 0;
}


unique_ptr<Result>
ProcessProgram::get_result()
{
  if (! waited_) {
    assert(is_done());
    usage_.ru_maxrss = 0;
    (void) xwait4(pid_, &status_, WNOHANG, &usage_);
    waited_ = true;
  }    

  unique_ptr<Result> result(new Result);
  result->set("status", status_);
  result->set("pid", pid_);

  // If we captured stdout or stderr, add the captured texts.
  auto stdout_capture = dynamic_cast<CaptureFdHandler*>(stdout_.get());
  if (stdout_capture != nullptr)
    result->set("stdout", stdout_capture->get());
  auto stderr_capture = dynamic_cast<CaptureFdHandler*>(stderr_.get());
  if (stderr_capture != nullptr)
    result->set("stderr", stderr_capture->get());

  // Record process usage statistics.
  result->set("user_cpu_time", to_string(usage_.ru_utime));
  result->set("system_cpu_time", to_string(usage_.ru_stime));
  // FIXME: Is this right?  Is this perhaps the pre-fork RSS?
  result->set("max_rss", to_string(usage_.ru_maxrss * 1024));

  // FIXME: Add start, end time and elapsed time.

  return result;
}


ProcessProgramSpec::ProcessProgramSpec()
  : executable_("/bin/true"),
    args_(),
    stdin_ (),
    stdout_(),
    stderr_()
{
}


unique_ptr<ProcessProgram>
ProcessProgramSpec::start()
  const
{
  return unique_ptr<ProcessProgram>(new ProcessProgram(*this));
}


Json
ProcessProgramSpec::to_json()
  const
{
  using namespace json;

  Json json = Json::OBJ;
  json["type"] = JSON_TYPE_NAME;
  json["executable"] = executable_;
  Json arr = Json::ARR;
  for (auto arg : args_)
    arr[arr.size()] = arg;
  json["args"] = std::move(arr);
  json["env"] = env_.to_json();
  json["stdin" ] = stdin_ .to_json();
  json["stdout"] = stdout_.to_json();
  json["stderr"] = stderr_.to_json();
  return json;
}


string const
ProcessProgramSpec::JSON_TYPE_NAME
  = "ProcessProgram";


unique_ptr<ProcessProgramSpec>
ProcessProgramSpec::from_json(
  Json const& json)
{
  using namespace json;

  unique_ptr<ProcessProgramSpec> spec(new ProcessProgramSpec);
  spec->executable_ = json["executable"].get_str();
  for (auto const& arg : json["args"].get_arr())
    spec->args_.emplace_back(arg.get_str());
  if (json.has("env"))
    spec->env_ = EnvSpec::from_json(json["env"]);
  if (json.has("stdin"))
    spec->stdin_  = *FdHandlerSpec::from_json(json["stdin" ]);
  if (json.has("stdout"))
    spec->stdout_ = *FdHandlerSpec::from_json(json["stdout"]);
  if (json.has("stderr"))
    spec->stderr_ = *FdHandlerSpec::from_json(json["stderr"]);
  return spec;
}


//------------------------------------------------------------------------------

void
sleep(
  double time)
{
  assert(time >= 0);

  struct timespec ts;
  ts.tv_sec = (time_t) time;
  ts.tv_nsec = ((long) (time * 1e+9)) % 1000000000;
  while (true) {
    int const rval = nanosleep(& ts, & ts);
    if (rval == 0)
      break;
    else if (rval == -1)
      if (errno == EINTR)
        continue;
      else
        throw SystemError("nanosleep");
    else
      assert(false);
  }
}


void
wait(
  Program& prog)
{
  // FIXME: This is stupid.
  double wait_time = 0.001;
  double const wait_time_max = 0.1;
  while (! prog.is_done()) 
    sleep(wait_time = std::min(wait_time_max, wait_time * 1.01));
}




}  // namespace run
}  // namespace alxs


