#include <stdio.h>
#include <string.h>

struct ParsedScore {
    int valid;
    int value;
};

/* One text line contains one score; whitespace and a leading + are allowed.
 * Width 4 bounds the integer conversion; a second conversion rejects suffixes.
 * This interface handles text, not binary data containing embedded NUL bytes. */
static struct ParsedScore parse_score(const char *line) {
    int score = 0;
    char extra;
    int assigned = sscanf(line, "%4d %c", &score, &extra);
    struct ParsedScore result = {assigned == 1 && score >= 0 && score <= 100, score};
    return result;
}

int main(int argc, char *argv[]) {
    if (argc != 3) {
        fprintf(stderr, "用法: file_report 输入文件 输出文件\n");
        return 1;
    }
    FILE *input = fopen(argv[1], "r");
    if (input == NULL) {
        fprintf(stderr, "无法打开输入文件: %s\n", argv[1]);
        return 1;
    }

    /* At most 32 bytes per line, excluding newline. Room for newline and NUL. */
    char line[34];
    size_t count = 0, passed = 0, line_number = 0;
    int total = 0, highest = 0, failed = 0;
    while (fgets(line, sizeof line, input) != NULL) {
        ++line_number;
        size_t length = strlen(line);
        if (length > 0 && line[length - 1] == '\n') { --length; }
        if (length > 32) {
            fprintf(stderr, "第%zu行超过32字节\n", line_number);
            failed = 1;
            break;
        }
        struct ParsedScore parsed = parse_score(line);
        if (!parsed.valid) {
            fprintf(stderr, "第%zu行不是0..100的整数\n", line_number);
            failed = 1;
            break;
        }
        if (count == 100) {
            fprintf(stderr, "人数超过100\n");
            failed = 1;
            break;
        }
        ++count;
        total += parsed.value;
        if (parsed.value > highest) { highest = parsed.value; }
        if (parsed.value >= 60) { ++passed; }
    }
    if (ferror(input)) {
        fprintf(stderr, "读取失败: %s\n", argv[1]);
        failed = 1;
    }
    if (fclose(input) != 0) {
        fprintf(stderr, "关闭输入文件失败: %s\n", argv[1]);
        failed = 1;
    }
    if (failed) { return 1; }
    if (count == 0) {
        fprintf(stderr, "输入文件没有成绩: %s\n", argv[1]);
        return 1;
    }

    /* C17's x modifier refuses to replace an existing file. */
    FILE *output = fopen(argv[2], "wx");
    if (output == NULL) {
        fprintf(stderr, "无法打开输出文件: %s\n", argv[2]);
        return 1;
    }
    if (fprintf(output, "人数=%zu\n平均分=%.2f\n最高分=%d\n及格=%zu\n",
                count, (double)total / count, highest, passed) < 0) {
        fprintf(stderr, "写入失败: %s\n", argv[2]);
        failed = 1;
    }
    if (fclose(output) != 0) {
        fprintf(stderr, "关闭输出文件失败: %s\n", argv[2]);
        failed = 1;
    }
    if (failed) { return 1; }
    printf("已生成报告\n");
    return 0;
}
