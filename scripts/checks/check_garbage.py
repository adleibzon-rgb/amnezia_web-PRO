"""Не осталось ли от проверок тестовых клиентов в clientsTable и в data.json."""
import json, sys
sys.path.insert(0, "/app")
from managers.ssh_manager import SSHManager

МЕТКА = "__проверка_связи"
d = json.load(open("/app/data/data.json"))

в_панели = [c for c in json.dumps(d, ensure_ascii=False).split('"') if МЕТКА in c]
print("следов в data.json панели:", len(в_панели))

ПРОБА = (
    "for c in $(docker ps --format '{{.Names}}' 2>/dev/null | grep -E 'amnezia-(awg|wireguard|xray)'); do "
    "  n=$(docker exec $c sh -c \"grep -o '%s[^\\\"]*' /opt/amnezia/awg/clientsTable /opt/amnezia/xray/clientsTable 2>/dev/null | wc -l\"); "
    "  [ \"$n\" != \"0\" ] && echo \"$c: $n\"; done; echo готово" % МЕТКА
)
всего = 0
for s in d["servers"]:
    try:
        with SSHManager(s["host"], s.get("ssh_port", 22), s["username"],
                        password=s.get("password") or None,
                        private_key=s.get("private_key") or None, connect_timeout=8) as ssh:
            o, _, _ = ssh.run_command(ПРОБА, timeout=40)
        строки = [x for x in (o or "").splitlines() if x.strip() and "готово" not in x]
        if строки:
            всего += len(строки)
            print("  !!", s["name"], строки)
    except Exception as e:
        print("  ?", s["name"][:26], str(e)[:40])
print("серверов с остатками:", всего)
