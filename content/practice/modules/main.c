#include <stdio.h>
#include "grades.h"

int main(void) {
    const int scores[] = {85, 90, 58};
    GradeReport report = grades_summarize(scores, sizeof scores / sizeof scores[0]);
    if (report.status != GRADE_OK) {
        fprintf(stderr, "统计失败，状态=%d\n", (int)report.status);
        return 1;
    }
    printf("平均分=%.2f 最高分=%d 及格=%zu\n", report.average, report.highest, report.passed);
    return 0;
}
