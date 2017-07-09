#ifndef __ENV_HH__
#define __ENV_HH__

#include <cassert>
#include <iostream>
#include <map>
#include <memory>
#include <string>

namespace alxs {
namespace sys {

//------------------------------------------------------------------------------

class Environment
  : public std::map<std::string, std::string>
{
public:

  typedef char const* const* ptr_t;

  class Buffer
  {
  public:

    Buffer(Environment const& env);
    ~Buffer();

    char const* const* get() const { return (char const* const*) buf_.get(); }

  private:

    static std::unique_ptr<char[]> build(Environment const& env);

    std::unique_ptr<char[]> const buf_;

  };

  /** 
   * Loads the process environment into this.
   */
  void get_proc_env();
  
  /**
   * Returns an 'envion'-style environment pointer.  The pointer is owned by
   * this and should be freed with 'free_ptr' before this is modified or
   * destroyed.
   */
  std::unique_ptr<Buffer> get_buffer() const { return std::unique_ptr<Buffer>(new Buffer(*this)); }

};


std::ostream& operator<<(std::ostream& os, Environment const& env);


//------------------------------------------------------------------------------

}  // namespace sys
}  // namespace alxs

#endif  // #ifndef __ENV_CC__

