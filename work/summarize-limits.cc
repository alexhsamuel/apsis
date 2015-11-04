#include <iostream>
#include <string>

#include "cron.hh"

using namespace std;
using namespace alxs::cron;

template<class D>
void
summarize_date(
  string const& name,
  ostream& os=cout)
{
  os 
    << name << "\n"
    << "  size: " << sizeof(D) << "\n"
    << "  min : " << D::MIN << "\n"
    << "  last: " << D::LAST << "\n"
    << "\n";
}


template<class T>
void
summarize_time(
  string const& name,
  ostream& os=cout)
{
  os 
    << name << "\n"
    << "  size: " << sizeof(T) << "\n"
    << "  min : " << T::MIN << "\n"
    << "  last: " << T::LAST << "\n"
    << "  base: " << Date::from_datenum(T::BASE) << "\n"
    << "  den : " << T::DENOMINATOR << "\n"
    << "  res : " << T::RESOLUTION << "\n"
    << "\n";
}


int
main()
{
  set_display_time_zone(UTC);
  summarize_date<Date>("Date");
  summarize_date<SmallDate>("SmallDate");
  summarize_time<Time>("Time"); 
  summarize_time<SmallTime>("SmallTime");
  summarize_time<NsecTime>("NsecTime");
  summarize_time<Unix32Time>("Unix32Time");
  summarize_time<Unix64Time>("Unix64Time");
  return 0;
}
