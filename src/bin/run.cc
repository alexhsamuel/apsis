#include <algorithm>
#include <cassert>
#include <cstdlib>
#include <fstream>
#include <getopt.h>
#include <iostream>
#include <memory>
#include <string>
#include <unistd.h>

#include "file.hh"
#include "filename.hh"
#include "program.hh"

using namespace alxs;

using std::string;
using std::unique_ptr;

//------------------------------------------------------------------------------
// Helper functions.

namespace {

// FIXME: Move elsewhere.

/**
 * Removes from 'vec' all elements that compare equal to 'val'.
 */
template<typename T>
inline void
remove_all_of(
  std::vector<T>& vec,
  T const& val)
{
  vec.erase(
    std::remove_if(
      begin(vec), 
      end(vec), 
      [=](string const& s) { return s == val; }),
    end(vec));
}
  

}  // anonymous namespace

//------------------------------------------------------------------------------

string
program_name
  = "run";


char const*
option_help =
R"(Options:
     --clear-env        Clear the environment.
  -h --help             Print usage and exit.
     --keep-env VAR     Keep VAR in the environment.
     --no-print         Don't print the result.
     --no-run           Don't run the program.
  -o --output FILE      Write result to FILE.  Implies --no-print.
     --print            Print the result [default].
  -r --read FILE        Read program spec from FILE.
     --run              Run the program [default].
  -e --set-env VAR=VAL  Set VAR to VAL in the environment.
  -E --stderr SPEC      Handle stderr by SPEC [default: leave].
  -I --stdin SPEC       Handle stdin by SPEC [default: leave].
  -O --stdout SPEC      Handle stdout by SPEC [default: leave].
  -u --unset-env VAR    Unset VAR in the environment.
  -w --write FILE       Write program spec to FILE.  Implies --no-run.
)";

void
print_usage(
  std::ostream& os)
{
  os << "Usage:\n  " 
     << program_name << " [ OPTIONS ] [ EXECUTABLE [ ARG ... ] ]\n\n"
     << option_help
     << std::endl;
}


void
usage_error(
  string const& message="")
{
  if (message.length() > 0)
    std::cerr << message << "\n";
  std::cerr << "\n";
  print_usage(std::cerr);
  exit(EXIT_FAILURE);
}


run::FdHandlerSpec
parse_fd_handler(
  string const& arg)
{
  run::FdHandlerSpec spec;
  if (arg == "leave")
    spec.type_ = "leave";
  else if (arg == "null")
    spec.type_ = "null";
  else if (arg == "close")
    spec.type_ = "close";
  else if (arg == "capture")
    spec.type_ = "capture";
  else if (arg.substr(0, 4) == "dup") {
    spec.type_ = "dup";
    try {
      spec.from_fd_ = std::stoi(arg.substr(4));
    }
    catch (std::exception) {
      usage_error(string("Invalid file descriptor: ") + arg);
    }
  }
  else if (arg == "stdout") {
    spec.type_ = "dup";
    spec.from_fd_ = STDOUT_FILENO;
  }
  else if (arg == "stderr") {
    spec.type_ = "dup";
    spec.from_fd_ = STDERR_FILENO;
  }

  return spec;
}


unique_ptr<run::ProcessProgramSpec>
read_spec_file(
  string const& arg)
{
  // FIXME: Handle errors.
  string text = fs::load_text_for_arg(arg);
  json::Json obj = json::parse(text);
  return run::ProcessProgramSpec::from_json(obj);
}


void
write_json_file(
  json::Serializable const& obj,
  string const& arg)
{
  // FIXME: Abstract.
  std::ofstream ofs;
  if (arg != "-")
    ofs.open(arg);
  std::ostream& os = arg == "-" ? std::cout : ofs;
  obj.to_json().print(os, 2);
  os << std::endl;
}


struct CmdLine
{
  unique_ptr<run::ProcessProgramSpec> spec_;
  string write_;
  bool run_;
  bool print_;
  string output_;
};


CmdLine
parse_cmd_line(
  int argc,
  char const* const* argv)
{
  enum {
    CMD_CLEAR_ENV = 1000,
    CMD_KEEP_ENV,
    CMD_NO_PRINT,
    CMD_NO_RUN,
    CMD_PRINT,
    CMD_RUN,
  };
  static struct option long_options[] = {
    {"clear-env",   no_argument,        nullptr, CMD_CLEAR_ENV},
    {"help",        no_argument,        nullptr, 'h'},
    {"keep-env",    required_argument,  nullptr, CMD_KEEP_ENV},
    {"no-print",    no_argument,        nullptr, CMD_NO_PRINT},
    {"no-run",      no_argument,        nullptr, CMD_NO_RUN},
    {"output",      required_argument,  nullptr, 'o'},
    {"print",       no_argument,        nullptr, CMD_PRINT},
    {"read",        required_argument,  nullptr, 'r'},
    {"run",         no_argument,        nullptr, CMD_RUN},
    {"set-env",     required_argument,  nullptr, 'e'},
    {"stderr",      required_argument,  nullptr, 'E'},
    {"stdin",       required_argument,  nullptr, 'I'},
    {"stdout",      required_argument,  nullptr, 'O'},
    {"unset-env",   required_argument,  nullptr, 'u'},
    {"write",       required_argument,  nullptr, 'w'},
    {nullptr,       0,                  nullptr, 0  },
  };
  static char const* const short_options = "e:E:hI:o:O:r:u:w:";

  CmdLine cmd_line;
  cmd_line.spec_.reset(new run::ProcessProgramSpec);
  cmd_line.run_ = true;
  cmd_line.print_ = true;

  while (true) {
    int c = getopt_long(argc, const_cast<char* const*>(argv), short_options, long_options, nullptr);
    if (c == -1)
      break;

    string const arg = optarg == nullptr ? "" : optarg;
    switch (c) {
    case 'e': {
      // Split the argument as VAR=VAL.
      string::size_type eq = arg.find('=');
      if (eq == string::npos)
        usage_error(string("bad --env option: ") + arg);
      string const var = arg.substr(0, eq);
      remove_all_of(cmd_line.spec_->env_.keep_, var);
      remove_all_of(cmd_line.spec_->env_.unset_, var);
      cmd_line.spec_->env_.set_[var] = arg.substr(eq + 1);
    } break;

    case 'E':
      cmd_line.spec_->stderr_ = parse_fd_handler(arg);
      break;

    case 'h':
      print_usage(std::cout);
      exit(EXIT_SUCCESS);
      break;

    case 'I':
      cmd_line.spec_->stdin_  = parse_fd_handler(arg);
      break;

    case 'o':
      cmd_line.output_ = arg;
      cmd_line.print_ = false;
      break;

    case 'O':
      cmd_line.spec_->stdout_ = parse_fd_handler(arg);
      break;

    case 'r': 
      cmd_line.spec_ = read_spec_file(arg);
      break;

    case 'u':
      remove_all_of(cmd_line.spec_->env_.keep_, arg);
      cmd_line.spec_->env_.set_.erase(arg);
      cmd_line.spec_->env_.unset_.push_back(arg);
      break;

    case 'w':
      cmd_line.write_ = arg;
      cmd_line.run_ = false;
      break;

    case CMD_CLEAR_ENV:
      cmd_line.spec_->env_.keep_all_ = false;
      cmd_line.spec_->env_.keep_.clear();
      // FIXME: Clear set_ and unset_ too?
      break;

    case CMD_KEEP_ENV:
      remove_all_of(cmd_line.spec_->env_.keep_, arg);
      cmd_line.spec_->env_.keep_.push_back(arg);
      cmd_line.spec_->env_.set_.erase(arg);
      remove_all_of(cmd_line.spec_->env_.unset_, arg);
      break;

    case CMD_NO_PRINT:
      cmd_line.print_ = false;
      break;

    case CMD_NO_RUN:
      cmd_line.run_ = false;
      break;

    case CMD_PRINT:
      cmd_line.print_ = true;
      break;

    case CMD_RUN:
      cmd_line.run_ = true;
      break;

    case '?':
      usage_error();
      break;

    default:
      assert(false);
    }
  }

  if (optind < argc) {
    // An exececutable was given.  Replace the executable and args from
    // non-option command line arguments.
    cmd_line.spec_->executable_ = argv[optind++];
    cmd_line.spec_->args_.clear();
    while (optind < argc)
      cmd_line.spec_->args_.push_back(argv[optind++]);
  }

  return cmd_line;
}


int
main(
  int argc,
  char const* const* argv)
{
  assert(argc > 0);
  program_name = fs::Filename(argv[0]).base();

  // Parse the command line, assembling the program spec.
  CmdLine cmd_line = parse_cmd_line(argc, argv);

  if (! cmd_line.write_.empty())
    // Write out the spec file.
    write_json_file(* cmd_line.spec_, cmd_line.write_);

  if (cmd_line.run_) {
    // Run the program, wait for it to complete, and grab the result.
    unique_ptr<run::ProcessProgram> prog = cmd_line.spec_->start();
    run::wait(*prog);
    unique_ptr<run::Result> result = prog->get_result();

    if (! cmd_line.output_.empty())
      // Write the result as JSON.
      write_json_file(*result, cmd_line.output_);
    if (cmd_line.print_)
      // Print the result.
      std::cout << result->pretty() << std::endl;
  }

  return EXIT_SUCCESS;
}


