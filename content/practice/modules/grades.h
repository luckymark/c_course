#ifndef C_COURSE_GRADES_H
#define C_COURSE_GRADES_H

#include <stddef.h>

#define GRADE_CAPACITY 100

typedef enum {
    GRADE_OK,
    GRADE_EMPTY,
    GRADE_INVALID,
    GRADE_TOO_MANY
} GradeStatus;

typedef struct {
    GradeStatus status;
    double average;
    int highest;
    size_t passed;
} GradeReport;

/* The caller supplies count readable elements; input is never modified.
 * NULL with a positive count is invalid; count 0 is empty.
 * More than GRADE_CAPACITY elements is too many; scores must be 0..100.
 * On error the numeric fields are zero. */
GradeReport grades_summarize(const int scores[], size_t count);

#endif
