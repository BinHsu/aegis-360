/* One native synthetic runtime for raw isolation probes and a bounded case. */
#include <stdio.h>
#include <string.h>

/* Reuse the audited operation implementation; only dispatch differs here. */
#define main aegis_feasibility_probe_main
#include "seatbelt_feasibility_probe.c"
#undef main

int main(int argc, char **argv) {
    if (argc == 20 && strcmp(argv[1], "--aegis-isolation-probe") == 0) {
        char *translated[21];
        for (int i = 0; i < argc; ++i) translated[i] = argv[i];
        translated[1] = "--aegis-seatbelt-feasibility-probe";
        translated[argc] = NULL;
        return aegis_feasibility_probe_main(argc, translated);
    }
    if (argc == 4 && strcmp(argv[1], "--aegis-synthetic-case") == 0 &&
            strcmp(argv[2], "argv_literal") == 0 && strcmp(argv[3], "--") == 0) {
        static const char result[] = "aegis-synthetic-argv-literal-v1\n";
        return fwrite(result, 1, sizeof(result) - 1U, stdout) == sizeof(result) - 1U
            ? 0 : 74;
    }
    return 64;
}
