"""Live local listeners for a bounded isolation probe; no capability authority."""

from __future__ import annotations

import errno
import os
import socket
import stat
import tempfile
from pathlib import Path


class _ProbeListeners:
    def __init__(self, root: Path):
        if (not isinstance(root, Path) or not root.is_absolute()
                or root.resolve(strict=True) != root):
            raise ValueError("listener root is not canonical")
        root_stat = os.lstat(root)
        if (not stat.S_ISDIR(root_stat.st_mode)
                or stat.S_IMODE(root_stat.st_mode) != 0o700
                or root_stat.st_uid != os.getuid()):
            raise ValueError("listener root is not private")
        self.root = root
        self.root_identity = (root_stat.st_dev, root_stat.st_ino)
        self.unix_path = root / "listener.sock"
        self.sockets = []
        self.unix_identity = None
        self.closed = False
        try:
            for family, address in ((socket.AF_INET, ("127.0.0.1", 0)),
                                    (socket.AF_INET6, ("::1", 0)),
                                    (socket.AF_UNIX, str(self.unix_path))):
                listener = socket.socket(family, socket.SOCK_STREAM)
                self.sockets.append(listener)
                listener.bind(address)
                if family == socket.AF_UNIX:
                    unix_stat = os.lstat(self.unix_path)
                    self.unix_identity = (unix_stat.st_dev, unix_stat.st_ino)
                listener.listen(1)
                listener.setblocking(False)
            unix_stat = os.lstat(self.unix_path)
            if not stat.S_ISSOCK(unix_stat.st_mode):
                raise ValueError("local listener path is not a socket")
            self.unix_identity = (unix_stat.st_dev, unix_stat.st_ino)
            self.revalidate()
        except BaseException:
            self.close()
            raise

    @property
    def ipv4_port(self): return self.sockets[0].getsockname()[1]

    @property
    def ipv6_port(self): return self.sockets[1].getsockname()[1]

    def revalidate(self):
        if self.closed: raise ValueError("probe listeners are closed")
        current_root = os.lstat(self.root)
        current_unix = os.lstat(self.unix_path)
        if ((current_root.st_dev, current_root.st_ino) != self.root_identity
                or (current_unix.st_dev, current_unix.st_ino) != self.unix_identity
                or not stat.S_ISSOCK(current_unix.st_mode)):
            raise ValueError("probe listener path identity changed")
        for listener, family in zip(self.sockets,
                (socket.AF_INET, socket.AF_INET6, socket.AF_UNIX)):
            if listener.fileno() < 0 or listener.family != family:
                raise ValueError("probe listener is not live")
            address = listener.getsockname()
            if (family == socket.AF_INET and address[0] != "127.0.0.1"
                    or family == socket.AF_INET6 and address[0] != "::1"
                    or family == socket.AF_UNIX and address != str(self.unix_path)):
                raise ValueError("probe listener address changed")
            try:
                accepted, _ = listener.accept()
            except BlockingIOError:
                continue
            except OSError as error:
                if error.errno in (errno.EAGAIN, errno.EWOULDBLOCK): continue
                raise ValueError("probe listener accept failed") from error
            else:
                accepted.close()
                raise ValueError("probe listener accepted a forbidden connection")

    def close(self):
        if self.closed: return
        self.closed = True
        for listener in self.sockets: listener.close()
        if self.unix_identity is not None:
            try: current = os.lstat(self.unix_path)
            except FileNotFoundError: return
            if (current.st_dev, current.st_ino) != self.unix_identity:
                raise ValueError("replaced local socket path was preserved")
            os.unlink(self.unix_path)

    def __enter__(self): return self

    def __exit__(self, *_): self.close()


class _OwnedProbeListeners:
    """Own the listener directory and remove it only after child reap."""

    def __init__(self, parent: Path):
        if (not isinstance(parent, Path) or not parent.is_absolute()
                or parent.resolve(strict=True) != parent):
            raise ValueError("listener parent is not canonical")
        self.root = Path(tempfile.mkdtemp(prefix="l", dir=parent)).resolve()
        named = os.lstat(self.root)
        self.identity = (named.st_dev, named.st_ino)
        self.listeners = None
        self.closed = False
        try:
            self.listeners = _ProbeListeners(self.root)
            self.revalidate()
        except BaseException:
            if self.listeners is not None: self.listeners.close()
            try:
                named = os.lstat(self.root)
                if (named.st_dev, named.st_ino) == self.identity:
                    self.root.rmdir()
            except OSError:
                pass
            raise

    def revalidate(self):
        if self.closed: raise ValueError("owned probe listeners are closed")
        named = os.lstat(self.root)
        if ((named.st_dev, named.st_ino) != self.identity
                or not stat.S_ISDIR(named.st_mode)
                or stat.S_IMODE(named.st_mode) != 0o700
                or named.st_uid != os.getuid()
                or set(os.listdir(self.root)) != {"listener.sock"}):
            raise ValueError("owned listener tree changed")
        self.listeners.revalidate()

    def finish_after_reap(self, returncode: int | None):
        if type(returncode) is not int:
            self.abandon()
            raise ValueError("listeners cannot be cleaned before reap")
        try:
            self.revalidate()
            self.listeners.close()
            named = os.lstat(self.root)
            if (named.st_dev, named.st_ino) != self.identity:
                raise ValueError("listener root changed during cleanup")
            self.root.rmdir()
            self.closed = True
        except BaseException:
            self.abandon()
            raise

    def abandon(self):
        if self.closed: return
        self.closed = True
        if self.listeners is not None:
            self.listeners.closed = True
            for listener in self.listeners.sockets: listener.close()
