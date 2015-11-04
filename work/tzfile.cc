#include <iostream>
#include <memory>

#include "exc.hh"
#include "filename.hh"

using std::string;
using std::unique_ptr;

namespace alxs {
namespace chron {

//------------------------------------------------------------------------------

class FormatError
  : public alxs::FormatError
{
public:

  FormatError(string const& name) : Error(string("timezone file: ") + name) {}
  virtual ~FormatError() throw () {}

};


//------------------------------------------------------------------------------

namespace {

class TimezoneFile
{
public:

  static unique_ptr<TimezoneFile> load(Filename const& filename);

  TimezoneFile(string const& data);
  ~TimezoneFile();

  uint32_t get_isgmt_cnt() const;
  uint32_t get_isstd_cnt() const;
  uint32_t get_leap_cnt() const;
  uint32_t get_time_cnt() const;
  uint32_t get_type_cnt() const;
  uint32_t get_abbr_len() const;

private:

  static size_t const UINT32 = sizeof(uint32_t);

  uint32_t get_uint32(size_t offset) const { return ntohl(*reinterpret_cast<uint32_t>(data_.c_str() + offset)); }

  string data_;

};


inline uint32_t
TimezoneFile::get_isgmt_cnt()
  const
{
  return get_uint32(0 * UINT32);
}


inline uint32_t
TimezoneFile::get_isstd_cnt()
  const
{
  return get_uint32(1 * UINT32);
}


inline uint32_t
TimezoneFile::get_leap_cnt()
  const
{
  return get_uint32(2 * UINT32);
}


inline uint32_t
TimezoneFile::get_time_cnt()
  const
{
  return get_uint32(3 * UINT32);
}


inline uint32_t
TimezoneFile::get_time_cnt()
  const
{
  return get_uint32(4 * UINT32);
}


inline uint32_t
TimezoneFile::get_isgmt_cnt()
  const
{
  return get_uint32(5 * UINT32);
}






unique_ptr<TimezoneFile>
parse(
  char const* const text)
{
  char const* p = text;
  unique_ptr<TimezoneFile> t = new TimezoneFile;

  // Format header.
  if (*p++ != 'T' || *p++ != 'Z' || *p++ != 'i' || *p++ != 'f')
    throw FormatError("not a timezone file");
  char const version = *p++;
  if (version != '\0' && version != '2')
    throw FormatError(string("unknown version: ") + version);
  for (size_t i = 0; i < 15; ++i)
    if (*p++ != 0)
      throw FormatError("nonzero reserved bytes");

  // File header, containing item counts.
  t->tzh_ttisgmtcnt = get_long(p);
  t->tzh_ttisstdcnt = get_long(p);
  t->tzh_leapcnt    = get_long(p);
  t->tzh_timecnt    = get_long(p);
  t->tzh_typecnt    = get_long(p);
  t->tzh_charcnt    = get_long(p);
}


void
load(
  fs::Filename const& filename)
{
  string text = load_text(filename);
  return text.c_str();
}


//------------------------------------------------------------------------------

}  // namespace chron
}  // namespace alxs

