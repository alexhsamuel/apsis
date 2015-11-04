//------------------------------------------------------------------------------
// TO DO:
// - Use better data structure for arr.
// - Use better data structure for obj.
// - Use wchar_t instead of char* to support Unicode strings.
//------------------------------------------------------------------------------

#include <cassert>
#include <cstdlib>
#include <cstring>
#include <new>
#include <string>

#include "json.hh"

using std::string;

//------------------------------------------------------------------------------

namespace alxs {
namespace json {

int const FORMAT_MIN = -2;
int const FORMAT_ONE_LINE = -1;

namespace {

inline void sep(std::ostream& os, int indent, size_t level)
{
  if (indent == FORMAT_MIN)
    ;
  else if (indent == FORMAT_ONE_LINE) 
    os << ' ';
  else {
    os << '\n';
    for (size_t i = 0; i < indent * level; ++i)
      os << ' ';
  }
}


}  // anonymous namespace


void 
Json::print(
  std::ostream& os, 
  int indent, 
  size_t level) const
{
  switch (type_) {
  case NUL:
    os << "null";
    break;

  case FAL:
    os << "false";
    break;

  case TRU:
    os << "true";
    break;

  case NUM:
    os << get_num();  // FIXME: Right format?  No scientific notation...
    break;

  case STR:
    os << '"';
    for (char const c : get_str())
      switch (c) {
      case '"':  os << '\\' << '"'; break;
      case '\\': os << '\\' << '\\'; break;
      case '\b': os << '\\' << 'b'; break;
      case '\f': os << '\\' << 'f'; break;
      case '\n': os << '\\' << 'n'; break;
      case '\r': os << '\\' << 'r'; break;
      case '\t': os << '\\' << 't'; break;

      default:
        assert(isprint(c));
        os << c;
        break;
      }
    os << '"';
    break;

  case ARR: {
    os << '[';
    bool first = true;
    for (auto const& ent : get_arr()) {
      if (first)
        first = false;
      else
        os << ',';
      sep(os, indent, level + 1);
      ent.print(os, indent, level + 1);
    }
    sep(os, indent, level);
    os << ']';
    } break;

  case OBJ: {
    os << '{';
    bool first = true;
    for (auto const& ent : get_obj()) {
      if (first)
        first = false;
      else
        os << ',';
      sep(os, indent, level + 1);
      // Use the STR type's print method for the name.
      Json(ent.first).print(os);
      os << ':';
      if (indent != FORMAT_MIN)
        os << ' ';
      ent.second.print(os, indent, level + 1);
    }    
    sep(os, indent, level);
    os << '}';
    } break;
  }
}


//------------------------------------------------------------------------------

namespace {

// Forward declaration.
Json _parse_val(char const** json);

inline bool _eat(char const** json, char c)
{
  if (**json == c) {
    ++*json;
    return true;
  }
  else
    return false;
}


inline void _skip_space(char const** json)
{
  while (isspace(**json))
    ++*json;
}


string _parse_str(char const** json)
{
  // Start with a double quote.
  if (! _eat(json, '"'))
    throw ParseError();

  // Count the length of the string.
  size_t length = 0;
  for (const char* c = *json; *c != '"'; ++c) {
    if (*c == '\0') 
      // Hit the end of string inside a quoted string.  
      throw ParseError();
    // Don't count an escape character.
    _eat(&c, '\\');
    ++length;
  }

  // Now go back and build the string.
  char str[length];
  char* d = str;
  while (true) {
    if (_eat(json, '"'))
      break;
    // Skip over the escape character, but treat the next character specially.
    else if (_eat(json, '\\')) 
      switch (**json) {
      case '"':
      case '\\':
      case '/':
        *d = **json;
        break;

      case 'b':
        *d = '\b';
        break;
        
      case 'f':
        *d = '\f';
        break;

      case 'n':
        *d = '\n';
        break;

      case 'r':
        *d = '\r';
        break;

      case 't':
        *d = '\t';
        break;

      default:
        // Unknown escape sequence.
        throw ParseError();
      }
    else 
      // Normal character; copy it.
      *d = **json;
    ++*json;
    ++d;
  }
  assert(d - str == (int) length);
  return string(str, length);
}


Json 
_parse_obj(
  char const** json)
{
  // Start with a left curly.
  if (! _eat(json, '{'))
    throw ParseError();
  _skip_space(json);
  Json obj = Json::OBJ;

  if (_eat(json, '}'))
    return obj;
  
  while (true) {
    // Parse the next '"name": value' element.
    _skip_space(json);
    string const name = _parse_str(json);
    _skip_space(json);
    if (! _eat(json, ':')) 
      throw ParseError();
    _skip_space(json);
    // FIXME: Detect duplicates.
    obj[name] = _parse_val(json);

    _skip_space(json);
    if (_eat(json, ','))
      // Comma means on to the next element.
      continue;
    else if (_eat(json, '}'))
      // Closing brace means done.
      break;
    else 
      throw ParseError();
  }

  return obj;
}


Json _parse_arr(char const** json)
{
  // Start with a left bracket;
  if (! _eat(json, '['))
    throw ParseError();

  Json arr = Json::ARR;

  _skip_space(json);
  if (_eat(json, ']'))
    // Empty array.
    return arr;
  
  while (true) {
    // Parse the next element.
    _skip_space(json);
    arr[arr.size()] = _parse_val(json);

    _skip_space(json);
    if (_eat(json, ','))
      // Comma means on to the next element.
      continue;
    else if (_eat(json, ']'))
      // Closing bracket means done.
      break;
    else 
      throw ParseError();
  }

  return arr;
}


Json _parse_num(char const** json)
{
  double num;
  int chars;
  if (sscanf(*json, "%lg%n", &num, &chars) == 1) {
    *json += chars;
    return Json(num);
  }
  else
    throw ParseError();
}


Json _parse_val(char const** json)
{
  _skip_space(json);
  if (**json == '"') 
    return Json(_parse_str(json));
  else if (**json == '{')
    return _parse_obj(json);
  else if (**json == '[')
    return _parse_arr(json);
  else if (**json == '-' || isdigit(**json))
    return _parse_num(json);
  else if (strncmp(*json, "true", 4) == 0) {
    *json += 4;
    return Json::TRU;
  }
  else if (strncmp(*json, "false", 5) == 0) {
    *json += 5;
    return Json::FAL;
  }
  else if (strncmp(*json, "null", 4) == 0) {
    *json += 4;
    return Json::NUL;
  }
  else 
    throw ParseError();
}


}  // anonymous namespace

Json 
parse(
  string const& json, 
  string::size_type& end)
{
  char const* j = json.c_str();
  Json val = _parse_val(&j);
  end = j - json.c_str();
  return val;
}


Json parse(string const& json)
{
  char const* j = json.c_str();
  return _parse_val(&j);
}


//------------------------------------------------------------------------------

}  // namespace json
}  // namespace alxs


