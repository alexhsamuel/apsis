#define _POSIX_SOURCE 1

#include <arpa/inet.h>
#include <assert.h>
#include <errno.h>
#include <fcntl.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <time.h>
#include <unistd.h>


struct tzfile
{
  uint32_t tzh_ttisgmtcnt;
  uint32_t tzh_ttisstdcnt;
  uint32_t tzh_leapcnt;
  uint32_t tzh_timecnt;
  uint32_t tzh_typecnt;
  uint32_t tzh_charcnt;
}
__attribute__((packed));


struct ttinfo 
{
  int32_t tt_gmtoff;
  int8_t tt_isdst;
  uint8_t tt_abbrind;
}
__attribute__((packed));


struct tleap
{
  time_t tl_time;
  uint32_t tl_secs;
}
__attribute__((packed));


inline int32_t*
tzh_time(
  struct tzfile* tz)
{
  return (int32_t*) (tz + 1);
}


inline uint8_t*
tzh_time_type(
  struct tzfile* tz)
{
  return (uint8_t*) (tzh_time(tz) + tz->tzh_timecnt);
}


inline struct ttinfo*
tzh_type(
  struct tzfile* tz)
{
  return (struct ttinfo*) (tzh_time_type(tz) + tz->tzh_timecnt);
}


inline struct tleap*
tzh_leap(
  struct tzfile* tz)
{
  return (struct tleap*) (tzh_type(tz) + tz->tzh_typecnt);
}


inline uint8_t*
tzh_isstd(
  struct tzfile* tz)
{
  return (uint8_t*) (tzh_leap(tz) + tz->tzh_leapcnt);
}


inline uint8_t*
tzh_isgmt(
  struct tzfile* tz)
{
  return (uint8_t*) (tzh_isstd(tz) + tz->tzh_ttisstdcnt);
}


inline char*
tzh_abbr(
  struct tzfile* tz)
{
  return (char*) (tzh_isgmt(tz) + tz->tzh_ttisgmtcnt);
}


static inline void
swap(
  void* ptr)
{
  uint32_t* uptr = (uint32_t*) ptr;
  *uptr = ntohl(*uptr);
}


extern inline int32_t* tzh_time(struct tzfile* tz);
extern inline uint8_t* tzh_time_type(struct tzfile* tz);
extern inline struct ttinfo* tzh_type(struct tzfile* tz);
extern inline struct tleap* tzh_leap(struct tzfile* tz);
extern inline uint8_t* tzh_isstd(struct tzfile* tz);
extern inline uint8_t* tzh_isgmt(struct tzfile* tz);
extern inline char* tzh_abbr(struct tzfile* tz);


struct tzfile*
tzfile_load(
  char const* filename)
{
  int fd = open(filename, O_RDONLY);
  if (fd == -1)
    return NULL;

  struct stat info;
  if (fstat(fd, &info) != 0)
    return NULL;
  
  // Read in the file header.
  if (info.st_size < 20) {
    errno = EPROTO;
    return NULL;
  }
  char hdr[20];
  int rval = read(fd, hdr, sizeof(hdr));
  if (rval == -1)
    return NULL;
  else 
    assert(rval == sizeof(hdr));
  
  // Check the header.
  if (!(   hdr[0] == 'T' 
        && hdr[1] == 'Z' 
        && hdr[2] == 'i' 
        && hdr[3] == 'f'
        && (hdr[4] == '\0' || hdr[4] == '2'))) {
    errno = EPROTO;
    return NULL;
  }
  for (size_t i = 5; i < sizeof(hdr); ++i)
    if (hdr[i] != 0) {
      errno = EPROTO;
      return NULL;
    }

  // Load in the data.
  size_t const len = info.st_size - sizeof(hdr);
  char* buf = (char*) malloc(len);
  if (buf == NULL)
    return NULL;
  rval = read(fd, buf, len);
  if (rval == -1) {
    free(buf);
    return NULL;
  }
  else
    assert(rval == len);
  struct tzfile* tz = (struct tzfile*) buf;
  
  // Byte-swap the count fields.
  swap(&tz->tzh_ttisgmtcnt);
  swap(&tz->tzh_ttisstdcnt);
  swap(&tz->tzh_leapcnt);
  swap(&tz->tzh_timecnt);
  swap(&tz->tzh_typecnt);
  swap(&tz->tzh_charcnt);
  // Byte-swap the times.
  for (size_t i = 0; i < tz->tzh_timecnt; ++i)
    swap(tzh_time(tz) + i);
  // Byte-swap the ttinfo structures.
  for (size_t i = 0; i < tz->tzh_typecnt; ++i)
    swap(&(tzh_type(tz) + i)->tt_gmtoff);
  // Byte-swap the tleap structures.
  for (size_t i = 0; i < tz->tzh_leapcnt; ++i) {
    struct tleap* const tl = tzh_leap(tz) + i;
    swap(&tl->tl_time);
    swap(&tl->tl_secs);
  }

  return tz;
}


void
tzfile_free(
  struct tzfile* tz)
{
  free(tz);
}


void
tzfile_print(
  struct tzfile* tz,
  FILE* fp)
{
  fprintf(fp, "Time zone file:\n");
  fprintf(fp, "  counts=%u %u %u %u %u %u\n", tz->tzh_ttisgmtcnt, tz->tzh_ttisstdcnt, tz->tzh_leapcnt, tz->tzh_timecnt, tz->tzh_typecnt, tz->tzh_charcnt);
  fprintf(fp, "  local time types:\n");
  for (uint32_t i = 0; i < tz->tzh_typecnt; ++i) {
    struct ttinfo const* const tt = tzh_type(tz) + i;
    char* const abbr = tzh_abbr(tz) + tt->tt_abbrind;
    fprintf(
      fp, "    %2u: offset=%d sec, DST=%c, abbr=%hhu '%s'\n", 
      i, tt->tt_gmtoff, tt->tt_isdst ? 'T' : 'F', tt->tt_abbrind, abbr);
  }
  fprintf(fp, "  local time transitions:\n");
  for (uint32_t i = 0; i < tz->tzh_timecnt; ++i) {
    time_t time = tzh_time(tz)[i];
    struct tm tm;
    gmtime_r(&time, &tm);
    char transition[26];
    asctime_r(&tm, transition);
    transition[24] = '\0';
    fprintf(
      fp, "    %3u: time=%s type=%hhu\n", i, transition, *(tzh_time_type(tz) + i));
  }
  fprintf(fp, "  leap seconds:\n");
  for (uint32_t i = 0; i < tz->tzh_leapcnt; ++i) {
    struct tleap const* const tl = tzh_leap(tz) + i;
    fprintf(
      fp, "    %2u. time=%u leap=%u secs\n", i, tl->tl_time, tl->tl_secs);
  }
  fprintf(fp, "  chars:");
  for (size_t i = 0; i < tz->tzh_charcnt; ++i)
    fprintf(fp, " %2x", tzh_abbr(tz)[i]);
  fprintf(fp, "\n");
  // FIXME: Print isgmt, isstd flags.
}


void
tzfile_find(
  struct tzfile* tz,
  time_t time)
{
  assert(INT32_MIN <= time && time <= INT32_MAX);
}


//------------------------------------------------------------------------------

int
main(
  int argc,
  char const* const* argv)
{
  if (argc != 2) {
    fprintf(stderr, "usage: %s FILENAME\n", argv[0]);
    return EXIT_FAILURE;
  }
  char const* const filename = argv[1];

  struct tzfile* tz = tzfile_load(filename);
  if (tz == NULL) {
    perror("tzfile_load");
    return EXIT_FAILURE;
  }

  tzfile_print(tz, stdout);
  tzfile_free(tz);

  return EXIT_SUCCESS;
}


