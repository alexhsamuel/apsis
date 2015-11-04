#include <cstdint>
#include <cstdio>
#include <cstdlib>
#include <cstring>
#include <string>

#include "env.hh"
#include "exc.hh"
#include "proc.hh"
#include "xsys.hh"

//------------------------------------------------------------------------------

void set_null_stdin()
{
  int const null_fd = xopen("/dev/null", O_RDONLY);
  xdup2(null_fd, 0);
  xclose(null_fd);
}


// FIXME
std::string const AnonymousTempFile::dir_ = "/tmp";

//------------------------------------------------------------------------------

ShellAction::ShellAction(Params const& params, std::string const& command)
  : params_(params),
    command_(command),
    combine_std_(false)
{
}


Outcome* ShellAction::run(const Args& args) const
{
  Args const bound = bind(params_, args);

  std::unique_ptr<AnonymousTempFile> stdout_file(
    new AnonymousTempFile("stdout"));
  std::unique_ptr<AnonymousTempFile> stderr_file(
    combine_std_ ? NULL : new AnonymousTempFile("stderr"));

  const pid_t child_pid = fork();
  
  if (child_pid == -1) {
    // FIXME: Generate an outcome.
    perror("fork");
    abort();
  }

  else if (child_pid == 0) {
    // Child process.
    char const* const executable = "/bin/bash";  // FIXME

    // Build the process argument list.
    char const* const argv[] = {
      executable,
      "-c",
      command_.c_str(),
      NULL
    };

    // Build the process environment.
    alxs::sys::Environment env;
    env.get_proc_env();
    // Set arguments as environment variables.
    env.insert(bound.begin(), bound.end());
    // Build an environment structure suitable for exec.
    alxs::sys::Environment::Buffer env_buffer(env);
    char* const* const envp = const_cast<char* const*>(env_buffer.get());

    // No stdin available.  FIXME: Specify stdin in action?
    set_null_stdin();
    // Capture stdout.
    stdout_file->dup_fd(1);
    if (combine_std_)
      // Capture stderr to the stdout file.
      stdout_file->dup_fd(2);
    else {
      // Capture stderr to a separate file.
      stderr_file->dup_fd(2);
      // No need for the original stderr file fd.
      stderr_file->close();
    }
    // No need for the original stdout file fd.
    stdout_file->close();

    // FIXME: Close other fds.

    // FIXME: Handle failure.
    xexecve(executable, (char* const*) argv, envp);
  }

  else {
    // Wait for the child process to complete.
    int status;
    rusage usage;
    pid_t const done_pid = wait4(child_pid, &status, 0, &usage);
    if (done_pid == -1) {
      // FIXME: Generate an outcome.
      perror("wait4");
      abort();
    }
    else {
      assert(done_pid == child_pid);

      // FIXME: For testing only.
      std::string stdout = stdout_file->read();
      std::cerr << "--- stdout ---\n";
      std::cerr << stdout;
      if (! combine_std_) {
        std::string stderr = stderr_file->read();
        std::cerr << "--- stderr ---\n";
        std::cerr << stderr;
      }
      std::cerr << "--------------\n";

      // FIXME
      Outcome::State state(Outcome::State::UNKNOWN);
      if (WIFEXITED(status))
        state = Outcome::State(Outcome::State::COMPLETE);
      else 
        state = Outcome::State(Outcome::State::ABORT);
      return new Outcome(state);
    }
  }
}


