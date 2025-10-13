#!/usr/bin/env python3
# ===============================================
# VPN 网络连通性检测脚本（Python版）
# 作者：ChatGPT
# ===============================================

import socket
import subprocess
import requests
import sys
import time
from colorama import Fore, Style, init

# 初始化颜色输出
init(autoreset=True)

def print_header(title):
    print(f"\n{'=' * 60}")
    print(f"� {title}")
    print(f"{'=' * 60}")

def resolve_domain(domain):
    try:
        ip = socket.gethostbyname(domain)
        print(f"{Fore.GREEN}✅ DNS 解析成功：{ip}{Style.RESET_ALL}")
        return ip
    except Exception as e:
        print(f"{Fore.RED}❌ DNS 解析失败: {e}{Style.RESET_ALL}")
        return None

def ping_test(ip):
    try:
        result = subprocess.run(
            ["ping", "-c", "2", "-W", "2", ip],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
        )
        if result.returncode == 0:
            print(f"{Fore.GREEN}✅ Ping 测试：通{Style.RESET_ALL}")
        else:
            print(f"{Fore.RED}❌ Ping 测试：不通{Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.RED}⚠️ Ping 测试异常: {e}{Style.RESET_ALL}")

def check_port(ip, port, timeout=3):
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(timeout)
    try:
        s.connect((ip, port))
        print(f"→ 端口 {port}: {Fore.GREEN}✔️ 可连接{Style.RESET_ALL}")
    except socket.timeout:
        print(f"→ 端口 {port}: {Fore.RED}❌ 超时（被防火墙丢弃）{Style.RESET_ALL}")
    except ConnectionRefusedError:
        print(f"→ 端口 {port}: {Fore.YELLOW}⚠️ 拒绝连接（可能服务未开或被拦截）{Style.RESET_ALL}")
    except Exception as e:
        print(f"→ 端口 {port}: {Fore.RED}❌ 异常: {e}{Style.RESET_ALL}")
    finally:
        s.close()

def check_blacklist(ip):
    print(f"\n� 检查 IP 是否在公共黑名单...")
    try:
        url = f"https://check.getipintel.net/check.php?ip={ip}&contact=test@example.com"
        response = requests.get(url, timeout=6)
        score = float(response.text.strip())
        if score > 0.95:
            print(f"{Fore.RED}❌ IP 可疑（黑名单分数: {score:.2f}){Style.RESET_ALL}")
        else:
            print(f"{Fore.GREEN}✅ IP 状态正常（分数: {score:.2f}){Style.RESET_ALL}")
    except Exception as e:
        print(f"{Fore.YELLOW}⚠️ 无法访问检测接口: {e}{Style.RESET_ALL}")

def main():
    domain = sys.argv[1] if len(sys.argv) > 1 else "no8.miaomiaowu-d.top"
    ports = [80, 443, 12221]

    print_header(f"VPN 连通性检测：{domain}")

    ip = resolve_domain(domain)
    if not ip:
        return

    ping_test(ip)

    print("\n� 端口连通性检测：")
    for port in ports:
        check_port(ip, port)
        time.sleep(0.2)

    check_blacklist(ip)
    print(f"\n✅ 检测完成。\n{'=' * 60}")

if __name__ == "__main__":
    main()
