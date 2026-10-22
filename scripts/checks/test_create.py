#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""Боевая проверка: на каждом сервере и каждом протоколе создаём тестового
клиента и тут же удаляем. Именно так работает кнопка «Добавить подключение».

Считаем пиров до и после: если после удаления число не вернулось — значит
за нами остался мусор, и это надо видеть.
"""
import json, sys, time
sys.path.insert(0, "/app")
from managers.ssh_manager import SSHManager
from managers.awg_manager import AWGManager

ИМЯ = "__проверка_связи_" + time.strftime("%d%m_%H%M")
ПРОТОКОЛЫ = ("awg", "awg2", "awg3", "awg31", "wireguard")

d = json.load(open("/app/data/data.json"))
итог = {"ok": 0, "сбой": 0, "мусор": 0}

for s in d["servers"]:
    протоколы = [p for p in ПРОТОКОЛЫ
                 if (s.get("protocols", {}).get(p) or {}).get("installed")]
    if not протоколы:
        print("  –  %-26s протоколов AWG не заведено" % s["name"][:26])
        continue
    for proto in протоколы:
        метка = "%s / %s" % (s["name"][:22], proto)
        try:
            ssh = SSHManager(s["host"], s.get("ssh_port", 22), s["username"],
                             password=s.get("password") or None,
                             private_key=s.get("private_key") or None,
                             connect_timeout=10, connect_retries=1)
            ssh.connect()
            try:
                m = AWGManager(ssh)
                было = len(m._get_used_ips(proto))
                порт = (s["protocols"][proto] or {}).get("port", "55424")
                r = m.add_client(proto, ИМЯ, s["host"], порт)
                cid = r.get("client_id") or r.get("clientId")
                есть_конфиг = bool(r.get("config"))
                стало = len(m._get_used_ips(proto))
                m.remove_client(proto, cid)
                после = len(m._get_used_ips(proto))
            finally:
                ssh.disconnect()

            если_чисто = (после == было)
            итог["ok" if (есть_конфиг and стало == было + 1) else "сбой"] += 1
            if not если_чисто:
                итог["мусор"] += 1
            print("  %s %-30s пиров %d → %d → %d  конфиг=%s" % (
                "ok" if (есть_конфиг and стало == было + 1 and если_чисто) else "!!",
                метка, было, стало, после, "есть" if есть_конфиг else "НЕТ"))
        except Exception as e:
            итог["сбой"] += 1
            print("  !! %-30s %s" % (метка, str(e)[:70]))

print("\nсоздалось и убралось начисто: %d, сбоев: %d, осталось мусора: %d"
      % (итог["ok"], итог["сбой"], итог["мусор"]))
