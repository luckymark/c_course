#include <stdio.h>
#include "grades.h"
#include "grades.h" /* Deliberately repeated: verify the include guard. */

int main(void) {
    const int normal[] = {85, 90, 58};
    const int single[] = {60};
    const int boundaries[] = {0, 100};
    const int negative[] = {85, -1};
    const int too_high[] = {101};
    struct Case {
        const char *name;
        const int *scores;
        size_t count;
        GradeReport expected;
    };
    const struct Case cases[] = {
        {"normal", normal, 3, {GRADE_OK, 233.0 / 3, 90, 2}},
        {"single", single, 1, {GRADE_OK, 60.0, 60, 1}},
        {"boundaries", boundaries, 2, {GRADE_OK, 50.0, 100, 1}},
        {"empty", NULL, 0, {GRADE_EMPTY, 0.0, 0, 0}},
        {"negative", negative, 2, {GRADE_INVALID, 0.0, 0, 0}},
        {"too_high", too_high, 1, {GRADE_INVALID, 0.0, 0, 0}},
        {"null", NULL, 1, {GRADE_INVALID, 0.0, 0, 0}},
        {"too_many", normal, 101, {GRADE_TOO_MANY, 0.0, 0, 0}}
    };
    const size_t case_count = sizeof cases / sizeof cases[0];
    size_t passed = 0;
    for (size_t i = 0; i < case_count; ++i) {
        GradeReport actual = grades_summarize(cases[i].scores, cases[i].count);
        GradeReport expected = cases[i].expected;
        double difference = actual.average - expected.average;
        int ok = actual.status == expected.status && actual.highest == expected.highest
            && actual.passed == expected.passed && difference > -0.000001 && difference < 0.000001;
        if (ok) { ++passed; }
        printf("%s %s\n", ok ? "PASS" : "FAIL", cases[i].name);
    }
    printf("%zu/%zu PASS\n", passed, case_count);
    return passed == case_count ? 0 : 1;
}
