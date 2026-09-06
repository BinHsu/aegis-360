#include <arpa/inet.h>
#include <errno.h>
#include <fcntl.h>
#include <netinet/in.h>
#include <stdio.h>
#include <stdlib.h>
#include <string.h>
#include <sys/socket.h>
#include <sys/stat.h>
#include <sys/types.h>
#include <sys/un.h>
#include <sys/wait.h>
#include <unistd.h>

static void emit(const char *name, long value, int error, const unsigned char *data,
                 size_t length) {
    printf("%s\t%ld\t%d\t", name, value, error);
    for (size_t i = 0; i < length; i++) printf("%02x", data[i]);
    putchar('\n');
    fflush(stdout);
}

static void read_probe(const char *name, const char *path) {
    unsigned char bytes[128];
    errno = 0;
    int fd = open(path, O_RDONLY | O_CLOEXEC | O_NOFOLLOW);
    if (fd < 0) { emit(name, -1, errno, NULL, 0); return; }
    ssize_t count = read(fd, bytes, sizeof(bytes));
    int error = count < 0 ? errno : 0;
    close(fd);
    emit(name, count, error, bytes, count > 0 ? (size_t)count : 0);
}

static void write_probe(const char *name, const char *path) {
    static const unsigned char value[] = "scratch-write-sentinel-v1";
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd < 0) { emit(name, -1, errno, NULL, 0); return; }
    ssize_t count = write(fd, value, sizeof(value) - 1);
    int error = count < 0 ? errno : 0;
    close(fd);
    emit(name, count, error, NULL, 0);
}

static void create_probe(const char *path) {
    errno = 0;
    int fd = open(path, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    int error = fd < 0 ? errno : 0;
    if (fd >= 0) close(fd);
    emit("outside_create", fd < 0 ? -1 : 0, error, NULL, 0);
}

static void overwrite_probe(const char *path) {
    static const unsigned char value[] = "overwrite-attempt-v1";
    errno = 0;
    int fd = open(path, O_WRONLY | O_CLOEXEC);
    if (fd < 0) { emit("outside_overwrite", -1, errno, (const unsigned char *)"open", 4); return; }
    errno = 0;
    ssize_t count = pwrite(fd, value, sizeof(value) - 1, 0);
    int error = count < 0 ? errno : 0;
    close(fd);
    emit("outside_overwrite", count, error, (const unsigned char *)"pwrite", 6);
}

static void truncate_probe(const char *path) {
    errno = 0;
    int fd = open(path, O_WRONLY | O_TRUNC | O_CLOEXEC);
    int error = fd < 0 ? errno : 0;
    if (fd >= 0) close(fd);
    emit("outside_truncate", fd < 0 ? -1 : 0, error, NULL, 0);
}

static void rename_probe(const char *source, const char *destination) {
    errno = 0;
    int value = rename(source, destination);
    emit("outside_rename", value, value < 0 ? errno : 0, NULL, 0);
}

static void unlink_probe(const char *path) {
    errno = 0;
    int value = unlink(path);
    emit("outside_unlink", value, value < 0 ? errno : 0, NULL, 0);
}

static void connect_ipv4(const char *port_text) {
    errno = 0;
    int fd = socket(AF_INET, SOCK_STREAM, 0);
    int socket_error = fd < 0 ? errno : 0;
    emit("ipv4_socket", fd, socket_error, NULL, 0);
    if (fd < 0) return;
    struct sockaddr_in address;
    memset(&address, 0, sizeof(address));
    address.sin_family = AF_INET;
    address.sin_port = htons((unsigned short)strtoul(port_text, NULL, 10));
    address.sin_addr.s_addr = htonl(INADDR_LOOPBACK);
    errno = 0;
    int value = connect(fd, (struct sockaddr *)&address, sizeof(address));
    int error = value < 0 ? errno : 0;
    close(fd);
    emit("ipv4_connect", value, error, NULL, 0);
}

static void connect_ipv6(const char *port_text) {
    errno = 0;
    int fd = socket(AF_INET6, SOCK_STREAM, 0);
    int socket_error = fd < 0 ? errno : 0;
    emit("ipv6_socket", fd, socket_error, NULL, 0);
    if (fd < 0) return;
    struct sockaddr_in6 address;
    memset(&address, 0, sizeof(address));
    address.sin6_family = AF_INET6;
    address.sin6_port = htons((unsigned short)strtoul(port_text, NULL, 10));
    address.sin6_addr = in6addr_loopback;
    errno = 0;
    int value = connect(fd, (struct sockaddr *)&address, sizeof(address));
    int error = value < 0 ? errno : 0;
    close(fd);
    emit("ipv6_connect", value, error, NULL, 0);
}

static void connect_unix(const char *path) {
    errno = 0;
    int fd = socket(AF_UNIX, SOCK_STREAM, 0);
    int socket_error = fd < 0 ? errno : 0;
    emit("unix_socket", fd, socket_error, NULL, 0);
    if (fd < 0) return;
    struct sockaddr_un address;
    memset(&address, 0, sizeof(address));
    address.sun_family = AF_UNIX;
    if (strlen(path) >= sizeof(address.sun_path)) {
        close(fd); emit("unix_connect", -1, ENAMETOOLONG, NULL, 0); return;
    }
    strcpy(address.sun_path, path);
    errno = 0;
    int value = connect(fd, (struct sockaddr *)&address, sizeof(address));
    int error = value < 0 ? errno : 0;
    close(fd);
    emit("unix_connect", value, error, NULL, 0);
}

static void fork_probe(const char *marker) {
    errno = 0;
    pid_t child = fork();
    if (child < 0) {
        static const unsigned char denied[] = "-1,-1,0";
        emit("process_fork", -1, errno, denied, sizeof(denied) - 1);
        return;
    }
    if (child == 0) {
        int fd = open(marker, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
        if (fd < 0) _exit(errno > 125 ? 125 : errno);
        ssize_t count = write(fd, "forked", 6);
        int error = count == 6 ? 0 : (errno > 125 ? 125 : errno);
        close(fd);
        _exit(error);
    }
    int status = -1;
    errno = 0;
    pid_t waited = waitpid(child, &status, 0);
    int wait_error = waited < 0 ? errno : 0;
    unsigned char evidence[96];
    int length = snprintf((char *)evidence, sizeof(evidence), "%ld,%d,%d",
                          (long)waited, status, wait_error);
    emit("process_fork", child, 0, evidence, length > 0 ? (size_t)length : 0);
}

static int forbidden_exec_mode(const char *marker) {
    int fd = open(marker, O_WRONLY | O_CREAT | O_EXCL | O_CLOEXEC, 0600);
    if (fd >= 0) { write(fd, "executed", 8); close(fd); }
    return 91;
}

int main(int argc, char **argv) {
    if (argc == 3 && strcmp(argv[1], "--forbidden-exec-sentinel") == 0)
        return forbidden_exec_mode(argv[2]);
    if (argc != 20 || strcmp(argv[1], "--aegis-seatbelt-feasibility-probe") != 0)
        return 64;
    read_probe("bundle_read", argv[2]);
    read_probe("model_read", argv[3]);
    read_probe("prompt_read", argv[4]);
    write_probe("scratch_write", argv[5]);
    read_probe("repository_read", argv[6]);
    read_probe("protocol_read", argv[7]);
    read_probe("neighbor_read", argv[8]);
    read_probe("result_read", argv[9]);
    create_probe(argv[10]);
    overwrite_probe(argv[11]);
    truncate_probe(argv[11]);
    rename_probe(argv[12], argv[13]);
    unlink_probe(argv[11]);
    fork_probe(argv[14]);
    connect_ipv4(argv[15]);
    connect_ipv6(argv[16]);
    connect_unix(argv[17]);
    errno = 0;
    char *const exec_argv[] = {argv[18], "--forbidden-exec-sentinel", argv[19], NULL};
    char *const exec_env[] = {NULL};
    execve(argv[18], exec_argv, exec_env);
    emit("forbidden_exec", -1, errno, NULL, 0);
    return 0;
}
