#ifndef __PROC_HH__
#define __PROC_HH__

#include <string>

#include "action.hh"
#include "xsys.hh"

//------------------------------------------------------------------------------

// FIXME: Somewhere else.
class AnonymousTempFile
{
public:

  AnonymousTempFile(std::string const& prefix="AnonymousTempFile") 
    : fd_(open(prefix))
  {
  }

  ~AnonymousTempFile() 
  { 
    close(); 
  }

  void close() 
  { 
    if (! is_closed()) { 
      xclose(fd_); 
      fd_ = -1; 
    } 
  }

  bool is_closed() const 
  { 
    return fd_ == -1; 
  }

  int get_fd() const 
  { 
    assert(! is_closed()); 
    return fd_; 
  }

  void rewind() const 
  { 
    xlseek(fd_, 0, SEEK_SET); 
  }

  void dup_fd(int fd) const
  {
    xdup2(get_fd(), fd);
  }

  std::string read(size_t max_size=SIZE_MAX) const
  {
    struct stat stats;
    xfstat(fd_, &stats);
    size_t const size = std::min((size_t) stats.st_size, max_size);
    std::unique_ptr<char[]> buf(new char[size]);
    rewind();
    size_t rval = xread(fd_, buf.get(), size);
    assert(rval == size);
    return std::string(buf.get(), size);
  }

private:

  static std::string const dir_;

  static int open(std::string const& prefix)
  {
    char filename[dir_.size() + prefix.size() + 9];
    strcpy(filename, (dir_ + '/' + prefix + "-XXXXXX").c_str());
    int const fd = xmkstemp(filename);
    xunlink(filename);
    return fd;
  }

  int fd_;

};


//------------------------------------------------------------------------------

class ShellAction
  : public Action
{
public:

  ShellAction(Params const& params, std::string const& command);

  virtual Params const& get_params() const { return params_; }

  virtual Outcome* run(const Args& args) const;

private:

  const Params params_;
  const std::string command_;

  /** If true, capture stderr with stdout.  */
  bool combine_std_;

};


//------------------------------------------------------------------------------

#endif  // #ifndef __PROC_HH__

