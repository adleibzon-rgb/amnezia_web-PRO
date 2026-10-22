#!/usr/bin/env python3
"""Ищем склеенные строки в конфигах awg на всех серверах панели.

Имена переменных в пробе латиницей: sh внутри контейнеров кириллицу не берёт.
"""
import json, sys
sys.path.insert(0, "/app")
from managers.ssh_manager import SSHManager

ПРОБА = (
    "for c in amnezia-awg2 amnezia-awg amnezia-awg31 amnezia-awg3 amnezia-awg-legacy; do "
    "  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx $c || continue; "
    "  for f in awg0.conf wg0.conf; do "
    "    p=/opt/amnezia/awg/$f; "
    "    docker exec $c test -f $p 2>/dev/null || continue; "
    "    glue=$(docker exec $c grep -c '/32\\[Peer\\]' $p 2>/dev/null || echo 0); "
    "    endnl=$(docker exec $c sh -c \"tail -c 1 $p | od -An -c | tr -d ' '\" 2>/dev/null); "
    "    peers=$(docker exec $c grep -c '^\\[Peer\\]' $p 2>/dev/null || echo 0); "
    "    echo \"$c/$f peers=$peers glue=$glue end=$endnl\"; "
    "  done; done"
)

d = json.load(open("/app/data/data.json"))
for s in d["servers"]:
    try:
        with SSHManager(s["host"], s.get("ssh_port", 22), s["username"],
                        password=s.get("password") or None,
                        private_key=s.get("private_key") or None,
                        connect_timeout=8) as ssh:
            out, err, _ = ssh.run_command(ПРОБА, timeout=40)
        for строка in (out or err).splitlines():
            строка = строка.strip()
            if not строка:
                continue
            плохо = ("glue=0" not in строка) or ("end=\\n" not in строка)
            print("%s %-26s %s" % ("  !!" if плохо else "   ", s["name"][:26], строка))
    except Exception as e:
        print("    %-26s СБОЙ: %s" % (s["name"][:26], str(e)[:50]))
