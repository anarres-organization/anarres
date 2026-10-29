/*
 * Synthetic benchmark code for defensive evaluation. Authored by cc opus 5.5 xhigh, 2026-10-29.
 *
 * main.c - reads a command script from stdin, one command per line.
 */
#include <stdio.h>
#include <string.h>
#include "sesscache.h"

#define LINE_MAX_LEN 256

int main(void)
{
    static Cache cache;
    char line[LINE_MAX_LEN];

    cache_init(&cache);
    while (fgets(line, sizeof line, stdin)) {
        size_t n = strlen(line);

        if (n == sizeof line - 1 && line[n - 1] != '\n') {
            /* over-long line: discard the rest of it */
            int ch;
            while ((ch = getchar()) != EOF && ch != '\n')
                ;
            cache_tick(&cache);
            printf("error: line too long\n");
            cache.st.errors++;
            continue;
        }
        cmd_run_line(&cache, line);
    }
    cache_destroy(&cache);
    fflush(stdout);
    return 0;
}
