#include <algorithm>
#include <cassert>
#include <iostream>
#include <list>
#include <memory>
#include <signal.h>
#include <time.h>
#include <vector>

#include "event.hh"
#include "exc.hh"

namespace alxs {
namespace evt {

//------------------------------------------------------------------------------

int const SIG_MAX =
#if __linux__
  SIGRTMIN
#else
  NSIG
#endif
;


SignalHandler::SignalHandler()
  : signals_(SIG_MAX)
{
}


SignalHandler::~SignalHandler()
{
  if (instance_ == this)
    uninstall();
}


void
SignalHandler::set(
  signum_t signum,
  Callback const &callback)
{
  assert(0 < signum && signum < SIG_MAX);
  assert(callback != nullptr);

  Signal& signal = signals_[signum];
  if (signal.callback_ != nullptr)
    throw Error("signal already set");
  signal.callback_ = callback;

  if (instance_ == this)
    install(signum);
}


void
SignalHandler::install()
{
  assert(instance_ == nullptr);
  instance_ = this;

  for (signum_t signum = 1; signum < SIG_MAX; ++signum)
    if (signals_[signum].callback_ != nullptr)
      install(signum);
}


void
SignalHandler::uninstall()
{
  assert(instance_ == this);

  for (signum_t signum = 1; signum < SIG_MAX; ++signum)
    if (signals_[signum].callback_ != nullptr) 
      uninstall(signum);

  instance_ = nullptr;
}


void
SignalHandler::handler(
  signum_t signum)
{
  assert(0 < signum && signum < SIG_MAX);
  assert(instance_ != nullptr);

  Signal& signal = instance_->signals_[signum];
  assert(signal.callback_ != nullptr);
  signal.callback_();
}


void
SignalHandler::install(
  signum_t signum)
{
  assert(0 < signum && signum < SIG_MAX);
  Signal& signal = signals_[signum];
  assert(signal.callback_ != nullptr);

  // Install our signal handler.
  signal.old_ = ::signal(signum, handler);
  // Our handler shouldn't already be installed!
  assert(signal.old_ != handler);
  // FIXME: Warn if other than SIG_IGN or SIG_DFL was installed?
}


void
SignalHandler::uninstall(
  signum_t signum)
{
  assert(0 < signum && signum < SIG_MAX);
  Signal& signal = signals_[signum];
  assert(signal.callback_ != nullptr);

  // Restore the old signal disposition.
  auto old = ::signal(signum, signal.old_);
  assert(old == handler);
}


SignalHandler*
SignalHandler::instance_
  = nullptr;


//------------------------------------------------------------------------------

Reactor::Reactor()
  : signals_(SIG_MAX)
{
  // Set up to wait for children to complete.  Set a SIGCHLD hander that flags
  // this signal.
  bool& raised = signals_[SIGCHLD].raised_;
  raised = false;
  signal_handler_.set(SIGCHLD, [&raised] () { raised = true; });

  // FIXME
  signal_handler_.install();
}


Reactor::~Reactor()
{
}


void
Reactor::add_timer(
  Time const& time,
  Callback callback)
{
  Timer timer = { time, callback };
  auto position = std::lower_bound(begin(timers_), end(timers_), timer);
  timers_.insert(position, timer);
}


void
Reactor::set_signal(
  signum_t signum,
  Callback callback)
{
  assert(signum > 0 && signum < SIG_MAX);
  assert(signum != SIGCHLD);

  Signal& signal = signals_[signum];
  if (signal.callback_ == nullptr) {
    signal.callback_ = callback;
    signal.raised_ = false;
    signal_handler_.set(signum, [&signal] () { signal.raised_ = true; });
  }
  else
    throw Error("callback for signal already set");
}


void
Reactor::set_wait(
  pid_t pid,
  Callback callback)
{
  auto find = waits_.find(pid);
  if (find == end(waits_))
    // Map this pid to its callback.
    waits_[pid] = callback;
  else
    throw Error("callback for pid already set");
}


inline bool
Reactor::is_empty()
  const
{
  // Count the number of active signal handlers.
  size_t const num_signals = std::count_if(
    begin(signals_), end(signals_),
    [] (Signal const& s) { return s.callback_ != nullptr; });

  return timers_.size() == 0 && waits_.size() == 0 && num_signals == 0;
}


size_t
Reactor::run(bool sleep)
{
  assert(! is_empty());

  size_t num_done = handle_current();
  while (sleep && num_done == 0) {
    struct timespec ts;
    if (timers_.empty()) {
      ts.tv_sec = 86400;  // FIXME
      ts.tv_nsec = 0;
    }
    else {
      Time const wait = timers_.front().time_ - now();
      ts.tv_sec = (long) wait;
      ts.tv_nsec = (wait - ts.tv_sec) * 1e+9;
    }
    int const rval = nanosleep(& ts, nullptr);
    if (rval == -1)
      if (errno == EINTR)
        // Sleep interrupted.  Loop again.
        ;
      else
        throw SystemError("nanosleep");
    else 
      assert(rval == 0);
    num_done += handle_current();
  }

  return num_done;
}


size_t
Reactor::handle_current()
{
  size_t num_done = 0;

  num_done += handle_signals();

  Time now = evt::now();
  auto iter = begin(timers_);
  for (; iter != end(timers_); ++iter)
    if (iter->time_ < now) {
      // This timer is overdue.  Invoke its callback.
      ++num_done;
      iter->callback_();
    }
    else {
      // Remove all the entries we've aready handled.
      break;
    }
  timers_.erase(begin(timers_), iter);

  return num_done;
}


size_t
Reactor::handle_signals()
{
  size_t num_done = 0;
  for (signum_t signum = 1; signum < SIG_MAX; ++signum) {
    Signal& signal = signals_[signum];
    if (signal.raised_) {
      // Received a signal.  
      signal.raised_ = false;
      if (signum == SIGCHLD) 
        num_done += handle_sigchld();
      else {
        signal.callback_();
        ++num_done;
      }
    }
  }
  return num_done;
}


size_t
Reactor::handle_sigchld()
{
  size_t num_done = 0;

  // For each child we're waiting, test completion with a non-blocking wait().
  for (auto iter = begin(waits_); iter != end(waits_); ) {
    pid_t const pid = iter->first;
    Callback const& callback = iter->second;
    siginfo_t siginfo;
    siginfo.si_pid = 0;
    xwaitid(P_PID, pid, & siginfo, WEXITED | WNOHANG | WNOWAIT);
    if (siginfo.si_pid > 0) {
      // Child process is done.
      callback();
      ++num_done;
      iter = waits_.erase(iter);
    }
    else 
      // This child is not done.  On to the next.
      ++iter;
  }
  
  return num_done;
}


}  // namespace evt
}  // namespace alxs

