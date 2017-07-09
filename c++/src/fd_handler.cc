#include <cassert>
#include <iostream>

#include "fd_handler.hh"
#include "xsys.hh"

using std::string;

namespace alxs {
namespace run {

//------------------------------------------------------------------------------
// FdHandler

FdHandler::FdHandler(
  int fd)
  : fd_(fd),
    old_fd_(-1)
{
}


void
FdHandler::start(
  bool final)
{
  if (! final)
    // Copy the file descriptor, so we can restore it later.
    old_fd_ = xdup(fd_);
}


void
FdHandler::restore()
{
  // Restore the previous file descriptor.
  assert(old_fd_ >= 0);
  xdup2(old_fd_, fd_);
  xclose(old_fd_);
  old_fd_ = -1;
}


//------------------------------------------------------------------------------
// CloseFdHandler

void
CloseFdHandler::start(
  bool final)
{
  FdHandler::start(final);
  xclose(fd_);
}


//------------------------------------------------------------------------------
// NullFdHandler

void
NullFdHandler::start(
  bool final)
{
  FdHandler::start(final);
  int const null_fd = xopen("/dev/null", O_RDONLY);
  try {
    xdup2(null_fd, fd_);
  }
  catch (...) {
    xclose(null_fd);
    throw;
  }
}


//------------------------------------------------------------------------------
// CaptureFdHandler

CaptureFdHandler::CaptureFdHandler(
  int fd)
  : FdHandler(fd),
    tmp_file_(new AnonymousTempFile)
{
}


void
CaptureFdHandler::start(
  bool final)
{
  FdHandler::start(final);
  tmp_file_->dup_fd(fd_);
}
  

void
CaptureFdHandler::close()
{
  tmp_file_.reset(NULL);
}


string
CaptureFdHandler::get()
  const
{
  assert(tmp_file_ != NULL);
  return tmp_file_->read();
}


//------------------------------------------------------------------------------
// DupFdHandler

void 
DupFdHandler::start(
  bool final)
{
  FdHandler::start(final);
  xdup2(from_fd_, fd_);
}


//------------------------------------------------------------------------------
// FileFdHandler

void
FileFdHandler::start(
  bool /*final*/)
{
  // FIXME: Handle errors here?
  std::cerr << "start: " << filename_ << " " << mode_ << "\n";
  int const file_fd = xopen(filename_, mode_);
  std::cerr << "opened\n";
  xdup2(file_fd, fd_);
  xclose(file_fd);
}


//------------------------------------------------------------------------------

}  // namespace run
}  // namespace alxs

