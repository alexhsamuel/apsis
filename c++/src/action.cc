#include <cassert>
#include <cstdlib>
#include <iostream>

#include "action.hh"
#include "param.hh"

//------------------------------------------------------------------------------

char const* const Outcome::State::CODE_NAMES[] = {
  "UNKNOWN_START",
  "ABORT_START",
  "TIMEOUT_START",
  "ERROR_START",
  "UNKNOWN",
  "ABORT",
  "TIMEOUT",
  "COMPLETE",
};


char const* Outcome::State::get_name(Code code)
{
  // FIXME: Make static_assert.
  assert(sizeof(CODE_NAMES) / sizeof(char const* const) == _LAST);
  return CODE_NAMES[code];
}


//------------------------------------------------------------------------------

Outcome* RandomAction::run(const Args& args)
  const
{
  Args const bound = bind(PARAMS, args);
  // FIXME: Check error / types, or use typed accessor.
  assert(bound.size() == 3);
  const double abort_weight     = bound.get<double>("abort_weight");
  const double timeout_weight   = bound.get<double>("timeout_weight");
  const double complete_weight  = bound.get<double>("complete_weight");
  // FIXME: Check non-negative.

  const double total_weight = abort_weight + timeout_weight + complete_weight;
  double random = rand() / ((double) RAND_MAX + 1) * total_weight;
  Outcome::State::Code state;
  if ((random -= abort_weight) <= 0)
    state = Outcome::State::ABORT;
  else if ((random -= timeout_weight) <= 0)
    state = Outcome::State::TIMEOUT;
  else if ((random -= complete_weight) <= 0)
    state = Outcome::State::COMPLETE;
  else {
    assert(false);  // Unreachable.
    state = Outcome::State::UNKNOWN;
  }
  return new Outcome(state);
}


namespace {

Params build_params()
{
  Params params;
  params.push_back("abort_weight");
  params.push_back("timeout_weight");
  params.push_back("complete_weight");
  return params;
}

}  // anonymous namespace

const Params RandomAction::PARAMS = build_params();

