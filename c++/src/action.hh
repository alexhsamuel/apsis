#pragma once

#include "param.hh"
#include "printable.hh"

//------------------------------------------------------------------------------

class Outcome
  : public alxs::Printable
{
public:

  class State {
  public:

    enum Code {
      UNKNOWN_START,  // Unknown problem; job did not start.
      ABORT_START,    // Job was aborted before start.
      TIMEOUT_START,  // Job timed out before start.
      ERROR_START,    // Error starting job.
      UNKNOWN,        // Unknown problem after start.
      ABORT,          // Job was aborted after start.
      TIMEOUT,        // Job timed out after start.
      COMPLETE,       // Job completed.
      _LAST
    };

    static char const* get_name(Code code);

    State(Code state)
      : code_(state)
    {
    }

    char const* get_name() const
    {
      return get_name(code_);
    }

    bool isStarted() const 
    {
      return ! (
           code_ == UNKNOWN_START
        || code_ == ABORT_START 
        || code_ == TIMEOUT_START
        || code_ == ERROR_START);
    }

    bool isTimeout() const 
    {
      return code_ == TIMEOUT_START || code_ == TIMEOUT;
    }

    bool isAbort() const 
    {
      return code_ == ABORT_START || code_ == ABORT;
    }

    bool isComplete() const 
    {
      return code_ == COMPLETE;
    }

  private:

    static char const* const CODE_NAMES[];
    Code code_;

  };

  Outcome(State state)
    : state_(state)
  {
  }

  Outcome(State::Code code)
    : state_(State(code))
  {
  }

  void print(std::ostream& os) const
  {
    os << "Outcome(" << state_.get_name() << ")";
  }

private:

  State state_;

};


//------------------------------------------------------------------------------

class Action 
{
public:

  virtual const Params& get_params() const = 0;
  virtual Outcome* run(const Args& args) const = 0;

};


//------------------------------------------------------------------------------

class RandomAction
  : public Action
{
public:

  virtual const Params& get_params() const { return PARAMS; }

  virtual Outcome* run(const Args& args) const;

private:

  static const Params PARAMS;

};


//------------------------------------------------------------------------------



