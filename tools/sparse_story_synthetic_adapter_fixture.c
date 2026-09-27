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

static int emit_pipe_pressure(void) {
    if (emit_padded_case(60000U) != 0) return 74;
    if (fflush(stdout) != 0) return 74;
    char buffer[256];
    size_t received = 0;
    while (received < 60000U) {
        size_t chunk = 60000U - received;
        if (chunk > sizeof(buffer)) chunk = sizeof(buffer);
        size_t count = fread(buffer, 1, chunk, stdin);
        if (count == 0) return 65;
        for (size_t i = 0; i < count; ++i) if (buffer[i] != 'x') return 65;
        received += count;
    }
    return fgetc(stdin) == EOF && !ferror(stdin) ? 0 : 65;
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

static int read_case(const char *path, const char *expected, int denied) {
    errno = 0;
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (denied) {
        if (fd >= 0) { close(fd); return 65; }
        return errno == EACCES || errno == EPERM
            ? emit_case_bytes(abstain, sizeof(abstain) - 1U) : 65;
    }
    if (fd < 0) return 65;
    char bytes[129];
    ssize_t count = read(fd, bytes, sizeof(bytes));
    int close_result = close(fd);
    size_t length = strlen(expected);
    if (close_result != 0 || count < 0 || (size_t)count != length ||
            memcmp(bytes, expected, length) != 0) return 65;
    return emit_case_bytes(abstain, sizeof(abstain) - 1U);
}

static int create_case(const char *path, int denied) {
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (denied) {
        if (fd >= 0) { close(fd); return 65; }
        return errno == EACCES || errno == EPERM
            ? emit_case_bytes(abstain, sizeof(abstain) - 1U) : 65;
    }
    if (fd < 0) return 65;
    static const char marker[] = "synthetic-scratch-write-v1";
    ssize_t count = write(fd, marker, sizeof(marker) - 1U);
    int close_result = close(fd);
    if (count != (ssize_t)(sizeof(marker) - 1U) || close_result != 0) return 65;
    return emit_case_bytes(abstain, sizeof(abstain) - 1U);
}

static int network_case(int family, const char *target) {
    errno = 0;
    int fd = socket(family, SOCK_STREAM, 0);
    if (fd < 0) return errno == EACCES || errno == EPERM
        ? emit_case_bytes(abstain, sizeof(abstain) - 1U) : 65;
    int result;
    if (family == AF_UNIX) {
        struct sockaddr_un address = {.sun_family = AF_UNIX};
        if (strlen(target) >= sizeof(address.sun_path)) { close(fd); return 64; }
        strcpy(address.sun_path, target);
        result = connect(fd, (struct sockaddr *)&address, sizeof(address));
    } else {
        char *end = NULL;
        errno = 0;
        long port = strtol(target, &end, 10);
        if (errno != 0 || end == target || *end != '\0' || port < 1 || port > 65535) {
            close(fd); return 64;
        }
        if (family == AF_INET) {
            struct sockaddr_in address = {.sin_family = AF_INET,
                .sin_port = htons((unsigned short)port)};
            address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
            result = connect(fd, (struct sockaddr *)&address, sizeof(address));
        } else {
            struct sockaddr_in6 address = {.sin6_family = AF_INET6,
                .sin6_port = htons((unsigned short)port), .sin6_addr = IN6ADDR_LOOPBACK_INIT};
            result = connect(fd, (struct sockaddr *)&address, sizeof(address));
        }
    }
    int error = result < 0 ? errno : 0;
    close(fd);
    return result < 0 && (error == EACCES || error == EPERM)
        ? emit_case_bytes(abstain, sizeof(abstain) - 1U) : 65;
}

static int grandchild_case(const char *marker) {
    errno = 0;
    pid_t child = fork();
    if (child < 0) return errno == EACCES || errno == EPERM
        ? emit_case_bytes(abstain, sizeof(abstain) - 1U) : 65;
    if (child == 0) {
        int fd = open(marker, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
        if (fd >= 0) {
            static const char value[] = "grandchild-created-v1";
            (void)write(fd, value, sizeof(value) - 1U);
            close(fd);
        }
        _exit(0);
    }
    int status = 0;
    if (waitpid(child, &status, 0) != child) return 65;
    return 65;
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
        if (argc == 6 && (strcmp(case_id, "bundle_read_allowed") == 0 ||
                strcmp(case_id, "model_read_allowed") == 0 ||
                strcmp(case_id, "prompt_read_allowed") == 0))
            return read_case(argv[4], argv[5], 0);
        if (argc == 5 && (strcmp(case_id, "repository_read_denied") == 0 ||
                strcmp(case_id, "protocol_read_denied") == 0 ||
                strcmp(case_id, "neighbor_packet_read_denied") == 0 ||
                strcmp(case_id, "result_read_denied") == 0))
            return read_case(argv[4], "", 1);
        if (argc == 5 && strcmp(case_id, "scratch_write_allowed") == 0)
            return create_case(argv[4], 0);
        if (argc == 5 && strcmp(case_id, "outside_write_denied") == 0)
            return create_case(argv[4], 1);
        if (argc == 5 && strcmp(case_id, "network_ipv4_denied") == 0)
            return network_case(AF_INET, argv[4]);
        if (argc == 5 && strcmp(case_id, "network_ipv6_denied") == 0)
            return network_case(AF_INET6, argv[4]);
        if (argc == 5 && strcmp(case_id, "unix_socket_denied") == 0)
            return network_case(AF_UNIX, argv[4]);
        if (argc == 5 && strcmp(case_id, "grandchild_containment") == 0)
            return grandchild_case(argv[4]);
        if (argc != 4) return 64;
        if (strcmp(case_id, "fd_hygiene") == 0) {
            if (fd_hygiene() != 0) return 65;
            return emit_case_bytes(abstain, sizeof(abstain) - 1U);
        }
        if (strcmp(case_id, "stdout_empty") == 0) return 0;
        if (strcmp(case_id, "stdout_limit_minus_one") == 0) return emit_padded_case(65535U);
        if (strcmp(case_id, "stdout_limit_exact") == 0) return emit_padded_case(65536U);
        if (strcmp(case_id, "stdout_limit_plus_one") == 0) return emit_padded_case(65537U);
        if (strcmp(case_id, "concurrent_pipe_pressure") == 0) return emit_pipe_pressure();
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
        if (strcmp(case_id, "term_ignore_kill") == 0) {
            if (signal(SIGTERM, SIG_IGN) == SIG_ERR) return 75;
            static const char ready[] = "ready\n";
            if (emit_case_bytes(ready, sizeof(ready) - 1U) != 0 ||
                    fflush(stdout) != 0) return 74;
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
