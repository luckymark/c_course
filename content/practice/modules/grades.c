#include "grades.h"

/* Internal linkage: this helper belongs only to this translation unit. */
static int score_is_valid(int score) {
    return score >= 0 && score <= 100;
}

GradeReport grades_summarize(const int scores[], size_t count) {
    GradeReport result = {GRADE_EMPTY, 0.0, 0, 0};
    if (count == 0) { return result; }
    if (count > GRADE_CAPACITY) {
        result.status = GRADE_TOO_MANY;
        return result;
    }
    if (scores == NULL) {
        result.status = GRADE_INVALID;
        return result;
    }
    int total = 0, highest = 0;
    size_t passed = 0;
    for (size_t i = 0; i < count; ++i) {
        if (!score_is_valid(scores[i])) {
            result.status = GRADE_INVALID;
            return result;
        }
        total += scores[i];
        if (scores[i] > highest) { highest = scores[i]; }
        if (scores[i] >= 60) { ++passed; }
    }
    result.status = GRADE_OK;
    result.average = (double)total / count;
    result.highest = highest;
    result.passed = passed;
    return result;
}
