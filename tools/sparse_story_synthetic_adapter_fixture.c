/* One native synthetic runtime for raw isolation probes and bounded cases. */
#include <stdio.h>
#include <string.h>
#include <limits.h>
#include <signal.h>

/* Reuse the audited operation implementation; only dispatch differs here. */
#define main aegis_feasibility_probe_main
#include "seatbelt_feasibility_probe.c"
#undef main

static const char abstain[] =
    "{\"activity_relation\":\"unclear\",\"anonymous_participant_configuration\":\"unclear\","
    "\"capture_or_projection_artifact\":\"unclear\",\"early_state_coherence\":\"unclear\","
    "\"exposure_or_palette_change\":\"unclear\",\"foreground_rearrangement\":\"unclear\","
    "\"late_state_coherence\":\"unclear\",\"setting_relation\":\"unclear\","
    "\"status\":\"abstain\",\"transition_support\":\"insufficient\","
    "\"viewpoint_change\":\"unclear\"}";

static int emit_case_bytes(const char *bytes, size_t length) {
    return fwrite(bytes, 1, length, stdout) == length ? 0 : 74;
}

static int emit_padded_case(size_t total) {
    char spaces[256];
    memset(spaces, ' ', sizeof(spaces));
    size_t written = sizeof(abstain) - 1U;
    if (total < written || emit_case_bytes(abstain, written) != 0) return 74;
    while (written < total) {
        size_t chunk = total - written;
        if (chunk > sizeof(spaces)) chunk = sizeof(spaces);
        if (emit_case_bytes(spaces, chunk) != 0) return 74;
        written += chunk;
    }
    return 0;
}

extern char **environ;

static int environment_exact(const char *home, const char *tmpdir) {
    static const char *names[] = {"LANG", "LC_ALL", "TZ", "NO_COLOR", "HOME", "TMPDIR"};
    const char *values[] = {"C", "C", "UTC", "1", home, tmpdir};
    size_t count = 0;
    unsigned int seen = 0;
    for (char **entry = environ; *entry != NULL; ++entry) {
        const char *equal = strchr(*entry, '=');
        if (equal == NULL) return 65;
        int recognized = 0;
        for (size_t i = 0; i < sizeof(names) / sizeof(names[0]); ++i) {
            if ((size_t)(equal - *entry) == strlen(names[i]) &&
                    strncmp(*entry, names[i], strlen(names[i])) == 0 &&
                    strcmp(equal + 1, values[i]) == 0 && (seen & (1U << i)) == 0) {
                seen |= 1U << i;
                recognized = 1;
                break;
            }
        }
        if (!recognized) return 65;
        ++count;
    }
    return count == sizeof(names) / sizeof(names[0]) ? 0 : 65;
}

static int fd_hygiene(void) {
    int limit = getdtablesize();
    if (limit < 3) return 65;
    for (int fd = 3; fd < limit; ++fd) {
        errno = 0;
        if (fcntl(fd, F_GETFD) != -1 || errno != EBADF) return 65;
    }
    return 0;
}

int main(int argc, char **argv) {
    if (argc == 20 && strcmp(argv[1], "--aegis-isolation-probe") == 0) {
        char *translated[21];
        for (int i = 0; i < argc; ++i) translated[i] = argv[i];
        translated[1] = "--aegis-seatbelt-feasibility-probe";
        translated[argc] = NULL;
        return aegis_feasibility_probe_main(argc, translated);
    }
    if (argc >= 4 && strcmp(argv[1], "--aegis-synthetic-case") == 0 &&
            strcmp(argv[3], "--") == 0) {
        const char *case_id = argv[2];
        if (strcmp(case_id, "argv_literal") == 0 && argc == 6 &&
                strcmp(argv[4], ";$(touch should-not-run)") == 0 &&
                strcmp(argv[5], "* ' \" \\") == 0)
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        if (strcmp(case_id, "environment_exact") == 0 && argc == 6) {
            if (environment_exact(argv[4], argv[5]) != 0) return 65;
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        }
        if (strcmp(case_id, "cwd_identity") == 0 && argc == 5) {
            char cwd[PATH_MAX];
            if (getcwd(cwd, sizeof(cwd)) == NULL || strcmp(cwd, argv[4]) != 0) return 65;
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        }
        if (argc != 4) return 64;
        if (strcmp(case_id, "fd_hygiene") == 0) {
            if (fd_hygiene() != 0) return 65;
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        }
        if (strcmp(case_id, "stdout_empty") == 0) return 0;
        if (strcmp(case_id, "stdout_limit_minus_one") == 0) return emit_padded_case(65535U);
        if (strcmp(case_id, "stdout_limit_exact") == 0) return emit_padded_case(65536U);
        if (strcmp(case_id, "stdout_limit_plus_one") == 0) return emit_padded_case(65537U);
        if (strcmp(case_id, "stderr_nonempty") == 0) {
            static const char warning[] = "synthetic-stderr-v1\n";
            if (fwrite(warning, 1, sizeof(warning) - 1U, stderr) != sizeof(warning) - 1U)
                return 74;
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        }
        if (strcmp(case_id, "nonzero_exit") == 0) {
            if (emit_case_bytes(abstain, sizeof(abstain) - 1U) != 0) return 74;
            return 23;
        }
        if (strcmp(case_id, "signal_exit") == 0) {
            raise(SIGTERM);
            return 75;
        }
        if (strcmp(case_id, "wall_timeout") == 0) {
            pause();
            return 75;
        }
        if (strcmp(case_id, "stdout_invalid_utf8") == 0) {
            static const char invalid[] = "\xff";
            return emit_case_bytes(invalid, sizeof(invalid) - 1U);
        }
        if (strcmp(case_id, "stdout_duplicate_key") == 0) {
            static const char duplicate[] = "{\"status\":\"abstain\",\"status\":\"abstain\"}";
            return emit_case_bytes(duplicate, sizeof(duplicate) - 1U);
        }
        if (strcmp(case_id, "stdout_nan") == 0) {
            static const char nan_value[] = "{\"status\":NaN}";
            return emit_case_bytes(nan_value, sizeof(nan_value) - 1U);
        }
        if (strcmp(case_id, "stdout_trailing_bytes") == 0) {
            static const char trailing[] = "{}{}";
            return emit_case_bytes(trailing, sizeof(trailing) - 1U);
        }
        if (strcmp(case_id, "stdout_forbidden_field") == 0) {
            static const char forbidden[] = "{\"source_time\":0}";
            return emit_case_bytes(forbidden, sizeof(forbidden) - 1U);
        }
        if (strcmp(case_id, "stdout_extra_field") == 0) {
            static const char extra[] = "{\"unexpected\":true}";
            return emit_case_bytes(extra, sizeof(extra) - 1U);
        }
    }
    return 64;
}
