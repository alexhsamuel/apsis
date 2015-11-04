#ifndef __FD_HANDLER__
#define __FD_HANDLER__

#include <string>
#include <memory>

#include "filename.hh"
#include "proc.hh"

namespace alxs {
namespace run {

//------------------------------------------------------------------------------

class FdHandler
{
public:

  FdHandler(int fd);
  virtual ~FdHandler() {}

  virtual void start(bool final=false);
  virtual void restore();
  virtual void close() {}

  int get_fd() const { return fd_; }

protected:

  int const fd_;
  int old_fd_;

};


class LeaveFdHandler
  : public FdHandler
{
public:

  LeaveFdHandler(int fd) : FdHandler(fd) {}
  virtual ~LeaveFdHandler() {}
  virtual void start(bool /*final*/=false) {}
  virtual void restore() {}

};


class CloseFdHandler
  : public FdHandler
{
public:

  CloseFdHandler(int fd) : FdHandler(fd) {}
  virtual ~CloseFdHandler() {}
  virtual void start(bool final=false);

};


class NullFdHandler
  : public FdHandler
{
public:

  NullFdHandler(int fd) : FdHandler(fd) {}
  virtual ~NullFdHandler() {}
  virtual void start(bool final=false);

};


class CaptureFdHandler
  : public FdHandler
{
public:

  CaptureFdHandler(int fd);
  virtual ~CaptureFdHandler() {};
  virtual void start(bool final=false);
  virtual void close();

  std::string get() const;

private:

  std::unique_ptr<AnonymousTempFile> tmp_file_;

};


class DupFdHandler
  : public FdHandler
{
public:

  DupFdHandler(int fd, int from_fd) : FdHandler(fd), from_fd_(from_fd) {}
  virtual ~DupFdHandler() {}
  virtual void start(bool final=false);

private:

  int from_fd_;

};


class FileFdHandler
  : public FdHandler
{
public:

  // FIXME: Suppose specification of new file permissions.  

  FileFdHandler(int fd, fs::Filename const& filename, mode_t mode);
  virtual ~FileFdHandler() {}
  virtual void start(bool final=false);

private:

  fs::Filename filename_;
  mode_t mode_;

};


inline 
FileFdHandler::FileFdHandler(
  int fd,
  fs::Filename const& filename,
  mode_t mode)
  : FdHandler(fd),
    filename_(filename),
    mode_(mode)
{
}


//------------------------------------------------------------------------------

}  // namespace run
}  // namespace alxs


#endif  // #ifndef __FD_HANDLER__

