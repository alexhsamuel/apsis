#include <iostream>

#include "date.hh"

using namespace alxs;

std::ostream&
operator<<(
  std::ostream& os,
  cron::Date const& date)
{
  auto parts = date.get_parts();
  os
    << parts.year 
    << "-" << 1 + parts.month 
    << "-" << 1 + parts.day 
    << " ord=" << 1 + parts.ordinal
    << " offset=" << date.get_offset()
    ;
  return os;
}

std::ostream&
operator<<(
  std::ostream& os,
  cron::SmallDate const& date)
{
  auto parts = date.get_parts();
  os
    << parts.year 
    << "-" << 1 + parts.month 
    << "-" << 1 + parts.day 
    << " ord=" << 1 + parts.ordinal
    << " offset=" << date.get_offset()
    ;
  return os;
}


int
main()
{
  std::cout << cron::Date::from_offset(281177) << "\n";
  std::cout << cron::Date::from_ymd(1970,  crn::JANUARY,  1 - 1) << "\n";

  std::cout << cron::Date::from_offset(282609) << "\n";
  std::cout << cron::Date::from_ymd(1973, crn::DECEMBER,  3 - 1) << "\n";
  std::cout << "MIN: " << cron::Date::MIN << "\n";
  std::cout << "MAX: " << cron::Date::MAX - 1 << "\n";
  std::cout << "range: " << cron::Date::MAX - crn::Date::MIN << "\n";

  cron::Date date = crn::Date::from_ymd(1973, crn::DECEMBER, 3 - 1);
  std::cout << format("%Y%m%d", date) << "\n";
  std::cout << format("%a %B %e, %Y", date) << "\n";
  std::cout << format("%Y-W%V-%u (%A)", date) << "\n";

  std::cout << "\nSmallDate:\n";
  std::cout << cron::SmallDate::from_offset(0) << "\n";
  std::cout << cron::SmallDate::from_ymd(1973, crn::DECEMBER,  3 - 1) << "\n";
  std::cout << "MIN: " << cron::SmallDate::MIN << "\n";
  std::cout << "MAX: " << cron::SmallDate::MAX - 1 << "\n";
  std::cout << "range: " << cron::SmallDate::MAX - crn::SmallDate::MIN << "\n";

  return 0;
}


