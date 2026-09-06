#define _DARWIN_C_SOURCE

#include <CommonCrypto/CommonDigest.h>
#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <signal.h>
#include <stdint.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/resource.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <unistd.h>

#define POLICY_MAX 65536U
#define ARGC_MAX 256
#define ARG_BYTES_MAX 131072U
#define FD_SCAN_MAX 1048576U

extern char **environ;

static void fail(const char *stage) {
    (void)write(STDERR_FILENO, stage, strlen(stage));
    (void)write(STDERR_FILENO, "\n", 1);
    _exit(70);
}

static int prefix(const char *value, const char *name, const char **result) {
    size_t length = strlen(name);
    if (strncmp(value, name, length) != 0) return 0;
    *result = value + length;
    return 1;
}

static uint64_t decimal(const char *value) {
    uint64_t result = 0;
    if (*value == '\0' || (*value == '0' && value[1] != '\0')) fail("launcher:argv");
    for (const unsigned char *p = (const unsigned char *)value; *p; ++p) {
        if (*p < '0' || *p > '9') fail("launcher:argv");
        if (result > (UINT64_MAX - (uint64_t)(*p - '0')) / 10U) fail("launcher:argv");
        result = result * 10U + (uint64_t)(*p - '0');
    }
    return result;
}

static int canonical_absolute(const char *value) {
    size_t n = strlen(value);
    if (n < 2 || n > 4096 || value[0] != '/' || value[n - 1] == '/') return 0;
    if (strstr(value, "//") != NULL || strstr(value, "/./") != NULL ||
            strstr(value, "/../") != NULL || strcmp(value + n - 2, "/.") == 0 ||
            (n >= 3 && strcmp(value + n - 3, "/..") == 0)) return 0;
    for (size_t i = 0; i < n; ++i)
        if ((unsigned char)value[i] < 32 || (unsigned char)value[i] == 127) return 0;
    return 1;
}

static void exact_environment(const char *home, const char *tmpdir, char **fresh) {
    const char *names[] = {"LANG=C", "LC_ALL=C", "TZ=UTC", "NO_COLOR=1"};
    int seen[6] = {0};
    size_t home_length = strlen(home), tmp_length = strlen(tmpdir);
    for (char **entry = environ; *entry != NULL; ++entry) {
        int match = -1;
        for (int i = 0; i < 4; ++i) if (strcmp(*entry, names[i]) == 0) match = i;
        if (strncmp(*entry, "HOME=", 5) == 0 && strlen(*entry + 5) == home_length &&
                strcmp(*entry + 5, home) == 0) match = 4;
        if (strncmp(*entry, "TMPDIR=", 7) == 0 && strlen(*entry + 7) == tmp_length &&
                strcmp(*entry + 7, tmpdir) == 0) match = 5;
        if (match < 0 || seen[match]) fail("launcher:env");
        seen[match] = 1;
    }
    for (int i = 0; i < 6; ++i) if (!seen[i]) fail("launcher:env");
    fresh[0] = "LANG=C"; fresh[1] = "LC_ALL=C"; fresh[2] = "TZ=UTC";
    fresh[3] = "NO_COLOR=1";
    size_t hn = home_length + 6, tn = tmp_length + 8;
    fresh[4] = malloc(hn); fresh[5] = malloc(tn); fresh[6] = NULL;
    if (fresh[4] == NULL || fresh[5] == NULL) fail("launcher:memory");
    if (snprintf(fresh[4], hn, "HOME=%s", home) < 0 ||
            snprintf(fresh[5], tn, "TMPDIR=%s", tmpdir) < 0) fail("launcher:env");
}

static void verify_sha(const unsigned char *bytes, size_t length, const char *expected) {
    if (strlen(expected) != 64) fail("launcher:policy-hash");
    unsigned char digest[CC_SHA256_DIGEST_LENGTH];
    if (CC_SHA256(bytes, (CC_LONG)length, digest) == NULL) fail("launcher:policy-hash");
    static const char hex[] = "0123456789abcdef";
    unsigned char mismatch = 0;
    for (size_t i = 0; i < sizeof(digest); ++i) {
        mismatch |= (unsigned char)(expected[i * 2] ^ hex[digest[i] >> 4]);
        mismatch |= (unsigned char)(expected[i * 2 + 1] ^ hex[digest[i] & 15]);
    }
    if (mismatch != 0) fail("launcher:policy-hash");
}

static void verify_runtime(const char *path, uint64_t device, uint64_t inode,
                           uint64_t size, uid_t uid) {
    struct stat named, opened;
    if (lstat(path, &named) != 0 || !S_ISREG(named.st_mode) || named.st_nlink != 1 ||
            named.st_uid != uid || (named.st_mode & 07777) != 0555 ||
            (uint64_t)named.st_dev != device || (uint64_t)named.st_ino != inode ||
            (uint64_t)named.st_size != size) fail("launcher:runtime");
    int fd = open(path, O_RDONLY | O_NOFOLLOW | O_CLOEXEC);
    if (fd < 0 || fstat(fd, &opened) != 0 || !S_ISREG(opened.st_mode) ||
            opened.st_nlink != 1 || opened.st_uid != uid ||
            (opened.st_mode & 07777) != 0555 || (uint64_t)opened.st_dev != device ||
            (uint64_t)opened.st_ino != inode || (uint64_t)opened.st_size != size ||
            opened.st_dev != named.st_dev || opened.st_ino != named.st_ino ||
            close(fd) != 0) fail("launcher:runtime");
}

int main(int argc, char **argv) {
    if (argc < 14 || argc > ARGC_MAX) fail("launcher:argv");
    size_t argv_bytes = 0;
    for (int i = 0; i < argc; ++i) {
        size_t n = strlen(argv[i]);
        if (n > 4096 || argv_bytes > ARG_BYTES_MAX - n - 1) fail("launcher:argv");
        argv_bytes += n + 1;
    }
    const char *v[12];
    const char *keys[] = {"--policy-fd=", "--policy-size=", "--policy-sha256=",
        "--cwd-fd=", "--cwd-dev=", "--cwd-ino=", "--uid=", "--gid=",
        "--home=", "--tmpdir=", "--runtime-dev=", "--runtime-ino="};
    for (int i = 0; i < 12; ++i) if (!prefix(argv[i + 1], keys[i], &v[i])) fail("launcher:argv");
    const char *runtime_size_text;
    if (!prefix(argv[13], "--runtime-size=", &runtime_size_text) || argc < 16 ||
            strcmp(argv[14], "--") != 0) fail("launcher:argv");
    const char *runtime = argv[15];
    if (!canonical_absolute(v[8]) || !canonical_absolute(v[9]) ||
            !canonical_absolute(runtime)) fail("launcher:path");

    uint64_t policy_fd64 = decimal(v[0]), policy_size64 = decimal(v[1]);
    uint64_t cwd_fd64 = decimal(v[3]), cwd_dev = decimal(v[4]), cwd_ino = decimal(v[5]);
    uint64_t uid64 = decimal(v[6]), gid64 = decimal(v[7]);
    uint64_t runtime_dev = decimal(v[10]), runtime_ino = decimal(v[11]);
    uint64_t runtime_size = decimal(runtime_size_text);
    if (policy_fd64 <= 2 || cwd_fd64 <= 2 || policy_fd64 == cwd_fd64 ||
            policy_fd64 > INT_MAX || cwd_fd64 > INT_MAX || policy_size64 < 1 ||
            policy_size64 > POLICY_MAX || uid64 > UINT_MAX || gid64 > UINT_MAX)
        fail("launcher:argv");
    uid_t uid = (uid_t)uid64; gid_t gid = (gid_t)gid64;
    if (getuid() != uid || geteuid() != uid || getgid() != gid || getegid() != gid || uid == 0)
        fail("launcher:identity");
    char *fresh_env[7]; exact_environment(v[8], v[9], fresh_env);

    int policy_fd = (int)policy_fd64, cwd_fd = (int)cwd_fd64;
    int policy_flags = fcntl(policy_fd, F_GETFD), cwd_flags = fcntl(cwd_fd, F_GETFD);
    if (policy_flags < 0 || cwd_flags < 0 ||
            fcntl(policy_fd, F_SETFD, policy_flags | FD_CLOEXEC) != 0 ||
            fcntl(cwd_fd, F_SETFD, cwd_flags | FD_CLOEXEC) != 0) fail("launcher:fd");
    struct stat cwd_before, cwd_after;
    if (fstat(cwd_fd, &cwd_before) != 0 || !S_ISDIR(cwd_before.st_mode) ||
            cwd_before.st_uid != uid || (cwd_before.st_mode & 07777) != 0555 ||
            (uint64_t)cwd_before.st_dev != cwd_dev || (uint64_t)cwd_before.st_ino != cwd_ino ||
            fchdir(cwd_fd) != 0 || fstat(cwd_fd, &cwd_after) != 0 ||
            !S_ISDIR(cwd_after.st_mode) || cwd_after.st_uid != uid ||
            (cwd_after.st_mode & 07777) != 0555 ||
            (uint64_t)cwd_after.st_dev != cwd_dev ||
            (uint64_t)cwd_after.st_ino != cwd_ino ||
            cwd_after.st_dev != cwd_before.st_dev || cwd_after.st_ino != cwd_before.st_ino)
        fail("launcher:cwd");

    if (setsid() != getpid() || getpgrp() != getpid()) fail("launcher:session");
    (void)umask(077);
    struct rlimit core = {0, 0};
    if (setrlimit(RLIMIT_CORE, &core) != 0) fail("launcher:rlimit");
    sigset_t empty;
    if (sigemptyset(&empty) != 0 || sigprocmask(SIG_SETMASK, &empty, NULL) != 0)
        fail("launcher:signal");
    for (int sig = 1; sig < NSIG; ++sig)
        if (sig != SIGKILL && sig != SIGSTOP && signal(sig, SIG_DFL) == SIG_ERR && errno != EINVAL)
            fail("launcher:signal");

    size_t policy_size = (size_t)policy_size64;
    unsigned char prefix_bytes[8];
    size_t prefix_offset = 0;
    while (prefix_offset < sizeof(prefix_bytes)) {
        ssize_t count = read(policy_fd, prefix_bytes + prefix_offset,
                             sizeof(prefix_bytes) - prefix_offset);
        if (count <= 0) fail("launcher:policy-prefix");
        prefix_offset += (size_t)count;
    }
    uint64_t prefixed_size = 0;
    for (size_t i = 0; i < sizeof(prefix_bytes); ++i)
        prefixed_size = (prefixed_size << 8) | prefix_bytes[i];
    if (prefixed_size != policy_size64) fail("launcher:policy-prefix");
    unsigned char *policy = malloc(policy_size + 1);
    if (policy == NULL) fail("launcher:memory");
    size_t offset = 0;
    while (offset < policy_size) {
        ssize_t count = read(policy_fd, policy + offset, policy_size - offset);
        if (count <= 0) fail("launcher:policy-read");
        offset += (size_t)count;
    }
    unsigned char extra;
    if (read(policy_fd, &extra, 1) != 0) fail("launcher:policy-length");
    for (size_t i = 0; i < policy_size; ++i)
        if (policy[i] == 0 || policy[i] > 127) fail("launcher:policy-bytes");
    if (policy[policy_size - 1] != '\n') fail("launcher:policy-bytes");
    policy[policy_size] = '\0';
    verify_sha(policy, policy_size, v[2]);

    long arg_max = sysconf(_SC_ARG_MAX);
    if (arg_max < 262144) fail("launcher:arg-max");
    size_t exec_bytes = policy_size + 1 + sizeof("/usr/bin/sandbox-exec") +
        sizeof("-p") + sizeof("--") + (size_t)(argc - 15) * sizeof(char *) +
        7U * sizeof(char *) + 32768U;
    for (int i = 15; i < argc; ++i) exec_bytes += strlen(argv[i]) + 1;
    for (int i = 0; i < 6; ++i) exec_bytes += strlen(fresh_env[i]) + 1;
    if (exec_bytes > (size_t)arg_max) fail("launcher:arg-max");

    size_t child_count = (size_t)(argc - 15) + 5;
    char **child = calloc(child_count, sizeof(char *));
    if (child == NULL) fail("launcher:memory");
    child[0] = "/usr/bin/sandbox-exec"; child[1] = "-p"; child[2] = (char *)policy;
    child[3] = "--";
    for (int i = 15; i < argc; ++i) child[(size_t)i - 11] = argv[i];
    child[child_count - 1] = NULL;

    if (close(policy_fd) != 0 || close(cwd_fd) != 0) fail("launcher:fd");
    struct rlimit nofile;
    if (getrlimit(RLIMIT_NOFILE, &nofile) != 0 || nofile.rlim_cur == RLIM_INFINITY ||
            nofile.rlim_cur > FD_SCAN_MAX) fail("launcher:fd-bound");
    for (int fd = 3; fd < (int)nofile.rlim_cur; ++fd) (void)close(fd);
    for (int fd = 0; fd < 3; ++fd) if (fcntl(fd, F_GETFD) < 0) fail("launcher:stdio");

    verify_runtime(runtime, runtime_dev, runtime_ino, runtime_size, uid);
    execve(child[0], child, fresh_env);
    fail("launcher:exec");
}
