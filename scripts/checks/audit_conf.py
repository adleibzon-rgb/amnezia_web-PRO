#!/usr/bin/env python3
"""Целостность конфигов awg по всему парку: склейки, финальный перевод строки,
проходит ли awg-quick strip и совпадает ли число пиров с живым интерфейсом."""
import json, sys
sys.path.insert(0, "/app")
from managers.ssh_manager import SSHManager

PROBE = r"""
for c in amnezia-awg2 amnezia-awg amnezia-awg31 amnezia-awg3 amnezia-awg-legacy; do
  docker ps --format '{{.Names}}' 2>/dev/null | grep -qx $c || continue
  for f in awg0.conf wg0.conf; do
    p=/opt/amnezia/awg/$f
    docker exec $c test -f $p 2>/dev/null || continue
    glue=$(docker exec $c grep -c '/32\[Peer\]' $p 2>/dev/null | tr -d '\n')
    end=$(docker exec $c sh -c "tail -c 1 $p | od -An -c | tr -d ' \n'")
    peers=$(docker exec $c grep -c '^\[Peer\]' $p 2>/dev/null | tr -d '\n')
    mode=$(docker exec $c stat -c %a $p 2>/dev/null | tr -d '\n')
    bin=wg; iface=wg0
    case $f in awg0.conf) bin=awg; iface=awg0;; esac
    if docker exec $c sh -c "$bin-quick strip $p > /dev/null 2>&1"; then strip=ok; else strip=СБОЙ; fi
    live=$(docker exec $c sh -c "$bin show $iface peers 2>/dev/null | grep -c ." | tr -d '\n')
    echo "$c/$f peers=$peers live=$live glue=$glue end=$end mode=$mode strip=$strip"
  done
done
"""

d = json.load(open("/app/data/data.json"))
беда = 0
for s in d["servers"]:
    try:
        with SSHManager(s["host"], s.get("ssh_port", 22), s["username"],
                        password=s.get("password") or None,
                        private_key=s.get("private_key") or None,
                        connect_timeout=8) as ssh:
            out, err, _ = ssh.run_command(PROBE, timeout=60)
        строки = [x.strip() for x in (out or "").splitlines() if x.strip()]
        if not строки:
            print("  ?  %-26s нет контейнеров awg (%s)" % (s["name"][:26], (err or "")[:40]))
            continue
        for стр in строки:
            плохо = ("glue=0" not in стр) or ("strip=ok" not in стр) or ("end=\\n" not in стр)
            if "peers=" in стр and "live=" in стр:
                try:
                    p = int(стр.split("peers=")[1].split()[0])
                    l = int(стр.split("live=")[1].split()[0])
                    if p != l:
                        плохо = True
                        стр += "  ← файл и интерфейс расходятся"
                except Exception:
                    pass
            беда += 1 if плохо else 0
            print("  %s %-26s %s" % ("!!" if плохо else "ok", s["name"][:26], стр))
    except Exception as e:
        беда += 1
        print("  !! %-26s НЕ ДОСТУЧАЛСЯ: %s" % (s["name"][:26], str(e)[:60]))
print("\nпроблемных строк:", беда)
