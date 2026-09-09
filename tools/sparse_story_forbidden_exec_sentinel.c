#include <errno.h>
#include <fcntl.h>
#include <limits.h>
#include <stddef.h>
#include <stdio.h>
#include <string.h>
#include <sys/stat.h>
#include <unistd.h>

/* A dedicated native executable control; it is neither launcher nor adapter. */
static const char marker_bytes[] = "aegis-forbidden-exec-marker-v1\n";

static int same_owned_marker(const struct stat *left, const struct stat *right) {
    return S_ISREG(left->st_mode) && S_ISREG(right->st_mode) &&
        left->st_dev == right->st_dev && left->st_ino == right->st_ino &&
        left->st_nlink == 1 && right->st_nlink == 1;
}

static int fail_after_marker(int fd, const char *marker, const struct stat *owned) {
    if (fd >= 0)
        (void)close(fd);
    struct stat named;
    if (lstat(marker, &named) == 0 && same_owned_marker(owned, &named))
        (void)unlink(marker);
    return 75;
}

int main(int argc, char **argv) {
    if (argc != 3 || strcmp(argv[1], "--aegis-forbidden-exec-sentinel-v1") != 0 ||
            argv[2][0] != '/')
        return 64;
    int fd = open(argv[2], O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC, 0600);
    if (fd < 0)
        return errno == EEXIST ? 73 : 74;
    struct stat owned = {0};
    if (fstat(fd, &owned) != 0 || !S_ISREG(owned.st_mode) || owned.st_nlink != 1)
        return fail_after_marker(fd, argv[2], &owned);
#ifdef AEGIS_SENTINEL_TEST_WRITE_FAILURE
    errno = EIO;
    return fail_after_marker(fd, argv[2], &owned);
#endif
    size_t offset = 0;
    while (offset < sizeof(marker_bytes) - 1U) {
        ssize_t written = write(fd, marker_bytes + offset,
                                sizeof(marker_bytes) - 1U - offset);
        if (written <= 0)
            return fail_after_marker(fd, argv[2], &owned);
        offset += (size_t)written;
    }
#ifdef AEGIS_SENTINEL_TEST_FSYNC_FAILURE
    errno = EIO;
    return fail_after_marker(fd, argv[2], &owned);
#endif
    if (fsync(fd) != 0)
        return fail_after_marker(fd, argv[2], &owned);
#ifdef AEGIS_SENTINEL_TEST_RACE_REPLACEMENT
    char moved[PATH_MAX];
    int moved_length = snprintf(moved, sizeof(moved), "%s.retained", argv[2]);
    if (moved_length < 0 || (size_t)moved_length >= sizeof(moved) ||
            rename(argv[2], moved) != 0)
        return fail_after_marker(fd, argv[2], &owned);
    int replacement = open(argv[2], O_WRONLY | O_CREAT | O_EXCL | O_NOFOLLOW | O_CLOEXEC,
                           0600);
    if (replacement >= 0) {
        static const char replacement_bytes[] = "replacement";
        (void)write(replacement, replacement_bytes, sizeof(replacement_bytes) - 1U);
        (void)close(replacement);
    }
    return fail_after_marker(fd, argv[2], &owned);
#endif
#ifdef AEGIS_SENTINEL_TEST_CLOSE_FAILURE
    return fail_after_marker(fd, argv[2], &owned);
#endif
    if (close(fd) != 0) {
        struct stat named;
        if (lstat(argv[2], &named) == 0 && same_owned_marker(&owned, &named))
            (void)unlink(argv[2]);
        return 75;
    }
    return 0;
}
