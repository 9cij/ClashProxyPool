# ClashProxyPool
在python中使用clash节点作为代理池，自动切换

用法:
```python
from clash_proxy_pool import ClashProxyPool
pool = ClashProxyPool()
response=pool.request("GET", "https://www.baidu.com", headers={"user-agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/136.0.0.0 Safari/537.36 Edg/136.0.0.0"})
print(response)
```
