import json
import re
import os

# ================= 配置 =================
URLS_FILE = r"D:\python\data\policy\2025\中央_urls.txt"           # 输入：包含所有 URL 的文件（每行一个）
JSON_FILE = r"D:\python\pycharm\project\pkulaw_scraper\learning\2025中央.json"           # 已爬取结果的 JSON 文件
OUTPUT_FILE = "2025_13_urls.txt"      # 输出：未爬取的 URL
# =======================================

def extract_gid_from_url(url):
    """从 URL 中提取 GID（例如 https://www.pkulaw.com/chl/xxx.html -> xxx）"""
    # 匹配 /chl/ 后面到 .html 的部分
    match = re.search(r'/chl/([a-f0-9]+)\.html', url)
    if match:
        return match.group(1)
    return None

def main():
    # 1. 读取 JSON 中已爬取的 GID 集合
    if not os.path.exists(JSON_FILE):
        print(f"错误: JSON 文件 {JSON_FILE} 不存在")
        return
    with open(JSON_FILE, 'r', encoding='utf-8') as f:
        data = json.load(f)
    crawled_gids = {item.get('detail_url') for item in data if item.get('detail_url')}
    print(f"已爬取 GID 数量: {len(crawled_gids)}")

    # 2. 读取 URL 文件中的所有 URL
    if not os.path.exists(URLS_FILE):
        print(f"错误: URL 文件 {URLS_FILE} 不存在")
        return
    with open(URLS_FILE, 'r', encoding='utf-8') as f:
        urls = [line.strip() for line in f if line.strip()]
    print(f"总 URL 数量: {len(urls)}")

    # 3. 找出未爬取的 URL
    remaining = []
    for url in urls:
        gid = extract_gid_from_url(url)
        if gid is None:
            print(f"警告: 无法从 URL 提取 GID: {url}")
            continue
        if gid not in crawled_gids:
            remaining.append(url)

    print(f"未爬取 URL 数量: {len(remaining)}")

    # 4. 写入输出文件
    with open(OUTPUT_FILE, 'w', encoding='utf-8') as f:
        f.write('\n'.join(remaining))
    print(f"已保存至 {OUTPUT_FILE}")

if __name__ == "__main__":
    main()