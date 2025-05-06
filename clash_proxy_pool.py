# -*- coding: utf-8 -*-
"""
Created on 2025-05-06 13:17
---------
@summary:
---------
@author: q
---------
@e-mail:2182782869@qq.com
"""

import requests
import random
import time


class ClashProxyPool:
    def __init__(self, clash_api="http://172.16.3.6:9097", secret=None, proxy_port=7897, max_fail=3,
                 proxy_server="172.16.3.6"):
        self.clash_api = clash_api.rstrip('/')
        self.secret = secret
        self.headers = {"Authorization": f"Bearer {secret}"} if secret else {}
        self.proxy_port = proxy_port
        self.max_fail = max_fail
        self.proxy_group = "GLOBAL"  # 强制使用 GLOBAL 策略组
        self.nodes = self._get_global_nodes()
        self.node_failures = {node: 0 for node in self.nodes}
        self.current_node = self.get_current_node()
        self.proxy_server = proxy_server

    def _get_global_nodes(self):
        try:
            url = f"{self.clash_api}/proxies"
            res = requests.get(url, headers=self.headers, timeout=5).json()
            group_info = res["proxies"].get(self.proxy_group)
            if not group_info or "all" not in group_info:
                raise Exception("❌ GLOBAL 组中未找到节点")

            all_nodes = group_info["all"]
            valid_nodes = [node for node in all_nodes if node.upper() not in ("DIRECT", "REJECT")]
            print(f"✅ GLOBAL 模式，发现 {len(valid_nodes)} 个可用节点")
            return valid_nodes
        except Exception as e:
            raise RuntimeError(f"❌ 获取 GLOBAL 节点失败: {e}")

    def _auto_detect_proxy_group(self):
        try:
            url = f"{self.clash_api}/proxies"
            res = requests.get(url, headers=self.headers, timeout=5).json()
            for group, info in res["proxies"].items():
                if "all" in info:
                    print(f"✅ 自动识别到 proxy group: {group}")
                    return group, info["all"]
            raise Exception("❌ 未找到包含节点的策略组（Proxy Group）")
        except Exception as e:
            raise RuntimeError(f"❌ 获取 proxy group 失败: {e}")

    def get_current_node(self):
        try:
            url = f"{self.clash_api}/proxies/{self.proxy_group}"
            res = requests.get(url, headers=self.headers, timeout=5).json()
            now_node = res.get("now")
            if now_node and now_node.upper() not in ("DIRECT", "REJECT"):
                return now_node
            return None
        except Exception as e:
            print("❌ 获取当前 GLOBAL 节点失败:", e)
            return None

    def list_nodes(self):
        print(f"📦 当前策略组：{self.proxy_group}")
        print("📋 可用节点：")
        for i, node in enumerate(self.nodes, 1):
            mark = "✅" if node == self.current_node else "  "
            print(f"{mark} {i}. {node}")

    def manual_switch(self, node_name):
        if node_name not in self.nodes:
            print(f"❌ 节点 {node_name} 不存在于策略组 {self.proxy_group}")
            return

        url = f"{self.clash_api}/proxies/{self.proxy_group}"
        try:
            res = requests.put(url, json={"name": node_name}, headers=self.headers, timeout=5)
            if res.status_code == 204:
                self.current_node = node_name
                print(f"✅ 已手动切换至节点：{node_name}")
                print("当前出口 IP：", self.get_public_ip())
            else:
                print("❌ 切换失败:", res.text)
        except Exception as e:
            print("❌ 切换节点异常:", e)

    def switch_node(self):
        healthy_nodes = [node for node, fail in self.node_failures.items() if fail < self.max_fail]
        if not healthy_nodes:
            raise RuntimeError("❌ 无可用代理节点，全部节点都被标记为失败")

        node = random.choice(healthy_nodes)
        url = f"{self.clash_api}/proxies/{self.proxy_group}"
        try:
            res = requests.put(url, json={"name": node}, headers=self.headers, timeout=5)
            if res.status_code == 204:
                self.current_node = node
                print(f"✅ 自动切换至节点：{node}")
                print("当前出口 IP：", self.get_public_ip())
            else:
                print("❌ 切换节点失败:", res.text)
        except Exception as e:
            print("❌ 切换节点异常:", e)

    def get_public_ip(self):
        proxies = {
            'http': f'http://{self.proxy_server}:{self.proxy_port}',
            'https': f'http://{self.proxy_server}:{self.proxy_port}'
        }
        try:
            res = requests.get('https://httpbin.org/ip', proxies=proxies, timeout=5)
            return res.json()['origin']
        except Exception as e:
            return f"获取失败: {e}"

    def request(self, method, url, retries=3, **kwargs):
        proxies = {
            'http': f'http://{self.proxy_server}:{self.proxy_port}',
            'https': f'http://{self.proxy_server}:{self.proxy_port}'
        }
        kwargs['proxies'] = proxies

        for attempt in range(retries):
            if not self.current_node or self.node_failures[self.current_node] >= self.max_fail:
                self.switch_node()

            try:
                response = requests.request(method, url, timeout=10, **kwargs)
                response.raise_for_status()
                self.node_failures[self.current_node] = 0  # 成功则重置失败计数
                return response
            except Exception as e:
                print(f"⚠️ 节点 {self.current_node} 第 {attempt + 1} 次请求失败：{e}")
                self.node_failures[self.current_node] += 1
                time.sleep(1)
                self.current_node = None  # 尝试下一个节点

        return None


if __name__ == '__main__':
    pool = ClashProxyPool(clash_api="http://172.16.3.6:9097", secret=None, proxy_port=7897, max_fail=3,
                          proxy_server="172.16.3.6")

    print("🎯 当前出口 IP：", pool.get_public_ip())

    print("\n📋 当前节点列表：")
    pool.list_nodes()

    # # 手动切换示例
    # node_name = input("\n请输入你想切换的节点名：")
    # pool.manual_switch(node_name)

    # 发起一个测试请求
    print("\n📡 发送请求到 httpbin.org/ip")
    resp = pool.request("GET", "https://httpbin.org/ip")
    if resp:
        print("响应内容：", resp.json())
