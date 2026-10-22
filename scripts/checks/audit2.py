#!/usr/bin/env python3
"""Сверяем ПОДНЯТЫЕ интерфейсы с их собственными конфигами.

Первый заход сравнивал wg0.conf с интерфейсом wg0, а в контейнере amnezia-awg
поднят awg0 — отсюда ложные «расхождения».
"""
import json, sys
sys.path.insert(0, "/app")
from managers.ssh_manager import SSHManager

PROBE = r"""
for c in $(docker ps --format '{{.Names}}' 2>/dev/null | grep '^amnezia-' | grep -vE 'nginx|frontend|backend|landing|xray|socks|ipsec|openvpn'); do
  for bin in awg wg; do
    docker exec $c sh -c "command -v $bin >/dev/null" 2>/dev/null || continue
    for i in $(docker exec $c sh -c "$bin show interfaces 2>/dev/null"); do
      live=$(docker exec $c sh -c "$bin show $i peers 2>/dev/null | grep -c ." | tr -d '\n')
      conf=""
      for f in /opt/amnezia/awg/$i.conf /opt/amnezia/awg/awg0.conf /opt/amnezia/awg/wg0.conf; do
        docker exec $c test -f $f 2>/dev/null && { conf=$f; break; }
      done
      [ -n "$conf" ] || { echo "$c $i live=$live конфиг=НЕ НАЙДЕН"; continue; }
      infile=$(docker exec $c grep -c '^\[Peer\]' $conf 2>/dev/null | tr -d '\n')
      echo "$c $i live=$live файл=$infile ($conf)"
    done
  done
done
"""

d = json.load(open("/app/data/data.json"))
плохо = 0
for s in d["servers"]:
    try:
        with SSHManager(s["host"], s.get("ssh_port", 22), s["username"],
                        password=s.get("password") or None,
                        private_key=s.get("private_key") or None,
                        connect_timeout=8) as ssh:
            out, err, _ = ssh.run_command(PROBE, timeout=60)
        строки = [x.strip() for x in (out or "").splitlines() if x.strip()]
        if not строки:
            print("   ?  %-26s нет поднятых интерфейсов" % s["name"][:26])
            continue
        for стр in строки:
            беда = False
            if "live=" in стр and "файл=" in стр:
                l = int(стр.split("live=")[1].split()[0])
                f = int(стр.split("файл=")[1].split()[0])
                беда = (l != f)
            плохо += 1 if беда else 0
            print("  %s %-26s %s" % ("!!" if беда else "ok", s["name"][:26], стр))
    except Exception as e:
        плохо += 1
        print("  !! %-26s НЕ ДОСТУЧАЛСЯ: %s" % (s["name"][:26], str(e)[:60]))
print("\nрасхождений:", плохо)
