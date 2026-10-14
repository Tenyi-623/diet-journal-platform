"""Show this Spark's physical network IPv4 addresses without scanning other devices."""

import ipaddress
import json
from pathlib import Path
import subprocess


def lan_addresses():
    result = subprocess.run(
        ["ip", "-j", "-4", "address", "show", "up"],
        capture_output=True, text=True, check=True, timeout=5,
    )
    addresses = []
    for interface in json.loads(result.stdout):
        name = interface["ifname"]
        # Physical Ethernet/Wi-Fi devices, excluding loopback, Docker and VPNs.
        if not (Path("/sys/class/net") / name / "device").exists():
            continue
        for info in interface.get("addr_info", []):
            if info.get("scope") != "global":
                continue
            address = ipaddress.IPv4Interface(f"{info['local']}/{info['prefixlen']}")
            addresses.append({
                "interface": name,
                "ip": str(address.ip),
                "network": str(address.network),
            })
    return addresses


def show_addresses():
    print("Spark 本机：http://127.0.0.1:8000/chat")
    try:
        addresses = lan_addresses()
    except (OSError, subprocess.SubprocessError, ValueError, KeyError) as exc:
        print(f"无法自动读取局域网地址（{type(exc).__name__}），请运行 ip -brief -4 address。")
        return
    if not addresses:
        print("未找到已连接的有线/Wi-Fi IPv4 地址。请连接网络后重试。")
    for address in addresses:
        print(f"网卡：{address['interface']}  IP：{address['ip']}  子网：{address['network']}")
        print(f"同一局域网的设备打开：http://{address['ip']}:8000/chat")
    print("以上为本机网卡地址；跨设备连通性还取决于防火墙和网络是否允许设备互访。")


if __name__ == "__main__":
    show_addresses()
