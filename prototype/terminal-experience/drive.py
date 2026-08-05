"""Drive the wizard through a real PTY and capture the frames it draws.

questionary needs an actual terminal; a pipe raises EOFError (#4, measured). So we
fork a PTY, send keystrokes, and keep every frame so the selection can be seen
mid-flight, not just its result.
"""

import os
import pty
import re
import select
import sys
import time

variant = sys.argv[1]
keys = sys.argv[2] if len(sys.argv) > 2 else "\r\x1b[B\r\r"

proto = "/tmp/claude-1000/-home-paninit-workspaces-panlabs-tech-overpower/edcf444e-9f27-4fe9-aa05-db4c7ec60cd5/scratchpad/proto"
env = dict(os.environ, COLUMNS="80", LINES="40", TERM="xterm-256color")

pid, fd = pty.fork()
if pid == 0:
    os.chdir(proto)
    os.execvpe("uv", ["uv", "run", "op.py", "-V", variant, "install"], env)

buf = b""
sent = 0
deadline = time.time() + 25
while time.time() < deadline:
    r, _, _ = select.select([fd], [], [], 0.4)
    if r:
        try:
            chunk = os.read(fd, 65536)
        except OSError:
            break
        if not chunk:
            break
        buf += chunk
    else:
        if sent < len(keys):
            time.sleep(0.5)
            os.write(fd, keys[sent].encode())
            # arrow keys are 3 bytes; send them whole
            if keys[sent] == "\x1b":
                os.write(fd, keys[sent + 1 : sent + 3].encode())
                sent += 2
            sent += 1
        elif buf:
            time.sleep(0.6)
            r2, _, _ = select.select([fd], [], [], 0.4)
            if not r2:
                break

os.close(fd)
os.waitpid(pid, 0)

text = buf.decode("utf-8", "replace")
# Split on erase-display / cursor-home so each questionary redraw is one frame.
raw_frames = re.split(r"\x1b\[\d*J", text)
clean = []
for f in raw_frames:
    f = re.sub(r"\x1b\[[0-9;?]*[a-zA-Z]", "", f)
    f = f.replace("\r\n", "\n").replace("\r", "\n")
    f = "\n".join(l.rstrip() for l in f.split("\n"))
    f = re.sub(r"\n{3,}", "\n\n", f).strip("\n")
    if f:
        clean.append(f)

for i, f in enumerate(clean):
    print(f"----- frame {i} -----")
    print(f)
