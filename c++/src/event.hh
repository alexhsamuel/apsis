#ifndef __EVENT_HH__
#define __EVENT_HH__

#include <deque>
#include <functional>
#include <list>
#include <map>
#include <memory>
#include <string>
#include <vector>

#include "xsys.hh"

// FIXME: Do this properly.
#ifdef __APPLE__
using sighandler_t = sig_t;
#endif

//------------------------------------------------------------------------------

namespace alxs {
namespace evt {

typedef int signum_t;

//------------------------------------------------------------------------------

// FIXME!!!!!!!!!!!!!
typedef double Time;

inline Time 
now()
{
  struct timeval tv;
  xgettimeofday(& tv);
  return tv.tv_sec + 1e-6 * tv.tv_usec;
}


//------------------------------------------------------------------------------

class SignalHandler
{
public:

  typedef std::function<void()> Callback;

  SignalHandler();
  ~SignalHandler();

  void set(signum_t signum, Callback const& callback);
  void install();
  void uninstall();

private:

  struct Signal
  {
    Signal() : callback_(nullptr) {}

    sighandler_t old_;
    Callback callback_;
  };

  static void handler(signum_t);

  static SignalHandler* instance_;

  void install(signum_t signum);
  void uninstall(signum_t signum);

  std::vector<Signal> signals_;

};


//------------------------------------------------------------------------------

// FIXME: Need a select-able fd ready event type too.

class Reactor
{
public:

  typedef std::function<void()> Callback;

  Reactor();
  ~Reactor();

  void add_timer(Time const& time, Callback callback);
  void set_signal(signum_t signum, Callback callback);
  void set_wait(pid_t pid, Callback callback);

  bool is_empty() const;
  size_t run(bool sleep=true);
  
private:

  struct Timer 
  {
    bool 
    operator<(
      Timer const& other) 
      const
    {
      if (time_ != other.time_)
        return time_ < other.time_;
      else
        return & callback_ < & other.callback_;
    }


    Time time_;
    Callback callback_;
  };

  struct Signal
  {
    Signal() : callback_(nullptr), raised_(false) {}
    Signal(Signal const&) = delete;

    Callback callback_;
    bool raised_;
  };

  size_t handle_current();
  size_t handle_signals();
  size_t handle_sigchld();

  std::deque<Timer> timers_;
  std::map<pid_t, Callback> waits_;
  std::vector<Signal> signals_;
  SignalHandler signal_handler_;

};


//------------------------------------------------------------------------------

}  // namespace evt
}  // namespace alxs

#endif  // #ifndef __EVENT_HH__

