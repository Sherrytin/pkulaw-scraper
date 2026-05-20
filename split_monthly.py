import os
import re
import json
import time
import random
import shutil
import math
import argparse
import signal
import sys
from datetime import datetime
from concurrent.futures import ThreadPoolExecutor, as_completed
from DrissionPage import ChromiumPage, ChromiumOptions

# ================= 全局退出标志 =================
should_exit = False

def graceful_exit(signum, frame):
    global should_exit
    print("\n⚠️ 收到退出信号，将在完成当前 URL 后退出...")
    should_exit = True

signal.signal(signal.SIGINT, graceful_exit)
signal.signal(signal.SIGTERM, graceful_exit)

# ================= 解析命令行参数 =================
parser = argparse.ArgumentParser()
parser.add_argument('--year', type=int, required=True, help='年份，如 2025')
parser.add_argument('--month', type=int, required=True, help='要处理的月份（1-12）')
args = parser.parse_args()

YEAR = args.year
MONTH = args.month
NUM_SPLITS = 3                         # 分片数量（并行线程数，建议 2-3）
BASE_DIR = r"D:\python\data\policy\2025"    # URL 文件所在目录（可根据需要修改）

# 自动生成文件路径（使用年份和月份）
INPUT_FILE = os.path.join(BASE_DIR, f"{YEAR}_{MONTH}_urls.txt")
FINAL_OUTPUT = f"{YEAR}_{MONTH}.json"

# 安全参数（每个线程独立延时）
MIN_DELAY = 2.0                        # 最小延时（秒）
MAX_DELAY = 4.0                        # 最大延时（秒）
HEADLESS = True                        # 无头模式
BACKUP_INTERVAL = 100                  # 每成功处理 100 条备份一次（每个分片独立）

ISSUE_DATE_FIXED = str(YEAR)           # 使用年份作为 IssueDate
law_db_name = "lar"                    # 中央为chl，地方为lar
# ===========================================================

def atomic_write_json(data, filepath):
    """原子写入 JSON（先写临时文件，再替换）"""
    tmp_file = filepath + ".tmp"
    with open(tmp_file, 'w', encoding='utf-8') as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    os.replace(tmp_file, filepath)  # 原子替换

def load_all_urls(filepath):
    """读取完整的 URL 文件"""
    if not os.path.exists(filepath):
        print(f"错误: 文件不存在 {filepath}")
        return []
    with open(filepath, 'r', encoding='utf-8') as f:
        return [line.strip() for line in f if line.strip()]

def split_urls(urls, num_splits):
    """将 URL 列表平均分成 num_splits 份"""
    total = len(urls)
    part_size = math.ceil(total / num_splits)
    splits = []
    for i in range(num_splits):
        start = i * part_size
        end = min(start + part_size, total)
        splits.append(urls[start:end])
    return splits

def load_progress(progress_file):
    """加载指定分片的进度集合"""
    if os.path.exists(progress_file):
        with open(progress_file, 'r', encoding='utf-8') as f:
            return set(line.strip() for line in f)
    return set()

def save_progress(progress_file, url):
    with open(progress_file, 'a', encoding='utf-8') as f:
        f.write(url + '\n')

def load_existing_results(output_json):
    """加载已有的 JSON 结果（用于断点续传）"""
    if not os.path.exists(output_json):
        return []
    try:
        with open(output_json, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                return data
            else:
                return []
    except:
        return []

def backup_json(output_json):
    if os.path.exists(output_json):
        shutil.copy2(output_json, output_json + ".bak")

def is_verification_page(page):
    title = page.title.lower()
    html = page.html[:2000].lower()
    keywords = ["验证", "captcha", "verify", "滑动", "请完成验证"]
    for kw in keywords:
        if kw in title or kw in html:
            return True
    return False

def extract_policy(page, url):
    """提取政策信息（地方版）"""
    try:
        page.get(url)
        try:
            page.wait.ele_displayed('#divFullText', timeout=15)
        except:
            try:
                page.wait.ele_displayed('.fulltext', timeout=10)
            except:
                return None

        # 标题
        title = ""
        title_ele = page.ele('font.MTitle', timeout=2)
        if title_ele:
            title = title_ele.text.strip()
        if not title or title in ["已进入法宝V6", "法宝V6"]:
            title_ele = page.ele('h2.title', timeout=2)
            if title_ele:
                raw = title_ele.text.strip()
                if raw not in ["已进入法宝V6", "法宝V6"]:
                    title = raw
        if not title:
            title_ele = page.ele('.title', timeout=2)
            if title_ele:
                raw = title_ele.text.strip()
                if raw not in ["已进入法宝V6", "法宝V6"]:
                    title = raw
        if not title:
            content_ele = page.ele('#divFullText')
            if not content_ele:
                content_ele = page.ele('.fulltext')
            if content_ele:
                first_line = content_ele.text.strip().split('\n')[0]
                if first_line and not first_line.startswith("已进入法宝"):
                    title = first_line

        # 正文
        content_ele = page.ele('#divFullText')
        if not content_ele:
            content_ele = page.ele('.fulltext')
        detail_flag = content_ele.text.strip() if content_ele else ""

        # 元数据
        meta = {}
        fields_div = page.ele('.fields')
        if not fields_div:
            fields_div = page.ele('.doc-info')
        if fields_div:
            for li in fields_div.eles('tag:li'):
                strong = li.ele('tag:strong')
                if strong:
                    key = strong.text.replace('：', '').strip()
                    raw_value = li.text.replace(strong.text, '').strip()
                    raw_value = raw_value.replace('\n', ' ').replace('\r', '')
                    if raw_value.startswith('：'):
                        raw_value = raw_value[1:].strip()
                    meta[key] = raw_value

        pub_depart = meta.get('制定机关', '')
        pub_num = meta.get('发文字号', '')
        effectiveness = meta.get('时效性', '')
        law_type = meta.get('效力位阶', '')
        category = meta.get('法规类别', '')
        pub_date_raw = meta.get('公布日期', '')
        use_date_raw = meta.get('施行日期', '')
        pub_date = f"{pub_date_raw}公布" if pub_date_raw else ""
        use_date = f"{use_date_raw}施行" if use_date_raw else ""

        province = "其他机构"
        if pub_depart:
            if '省' in pub_depart or '市' in pub_depart:
                province = pub_depart
            elif '全国' in pub_depart or '国务院' in pub_depart or '最高' in pub_depart:
                province = "中央"

        timeliness_dic = "有效" if effectiveness == "现行有效" else (effectiveness if effectiveness else "")
        gid = page.url.split('/')[-1].replace('.html', '')

        record = {
            "law_db_name": law_db_name,
            "title": title,
            "detail_url": gid,
            "RangeOf": "",
            "ExpirationDate": "",
            "province": province,
            "EffectivenessDic": law_type,
            "TimelinessDic": timeliness_dic,
            "IssueDate": ISSUE_DATE_FIXED,
            "IssueDepartment_2": "",
            "IssueDepartment_3": "",
            "category_1": category if category else "",
            "category_2": "",
            "law_type": law_type,
            "pub_depart": pub_depart,
            "pub_num": pub_num,
            "pub_date": pub_date,
            "use_date": use_date,
            "is_time": effectiveness,
            "detail_flag": detail_flag,
            "add_time": datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        }
        return record
    except Exception as e:
        print(f"提取异常 {url}: {e}")
        return None

def handle_verification(page, url):
    print("\n⚠️ 检测到验证页面！正在打开浏览器窗口，请手动完成验证...")
    page.set_headless(False)
    page.get(url)
    input("请在弹出的浏览器中完成验证，然后按回车键继续...")
    page.set_headless(True)
    time.sleep(3)
    print("验证处理完成，继续爬取...")

def worker(split_idx, urls, output_json, progress_file, cache_dir):
    """单个分片的爬取工作函数（独立线程）"""
    global should_exit
    progress = load_progress(progress_file)
    pending = [u for u in urls if u not in progress]
    if not pending:
        print(f"[分片 {split_idx+1}] 无待处理 URL，跳过")
        return

    results = load_existing_results(output_json)
    print(f"[分片 {split_idx+1}] 待处理: {len(pending)} 条，已有结果: {len(results)}")

    # 初始化独立浏览器
    co = ChromiumOptions()
    co.set_user_data_path(cache_dir)
    co.auto_port()
    if HEADLESS:
        co.headless()
    page = ChromiumPage(addr_or_opts=co)

    total = len(pending)
    success_count = 0
    initial_count = len(results)

    for idx, url in enumerate(pending):
        if should_exit:
            print(f"[分片 {split_idx+1}] 收到退出信号，中断当前分片...")
            break

        delay = random.uniform(MIN_DELAY, MAX_DELAY)
        time.sleep(delay)
        print(f"[分片 {split_idx+1}] [{idx+1}/{total}] 处理: {url[:80]}")

        data = None
        for attempt in range(2):
            try:
                data = extract_policy(page, url)
                if data:
                    break
                if is_verification_page(page):
                    handle_verification(page, url)
                    continue
                else:
                    print(f"  提取失败，非验证原因")
                    break
            except Exception as e:
                print(f"  出错: {e}")
                if is_verification_page(page):
                    handle_verification(page, url)
                else:
                    break

        if data:
            results.append(data)
            save_progress(progress_file, url)
            success_count += 1
            atomic_write_json(results, output_json)
            if success_count % BACKUP_INTERVAL == 0:
                backup_json(output_json)
            print(f"  ✓ 成功: {data['title'][:50]}")
        else:
            print(f"  ✗ 失败: {url}")
            with open(f"failed_urls_{split_idx+1}.txt", "a", encoding='utf-8') as f:
                f.write(url + "\n")

    page.quit()
    if results:
        backup_json(output_json)
    print(f"[分片 {split_idx+1}] 完成，成功提取 {len(results)} 条（新增 {len(results)-initial_count} 条）")

def merge_results(split_outputs, final_output):
    """合并所有分片的 JSON 文件，去重后保存最终结果"""
    all_data = []
    for json_file in split_outputs:
        if os.path.exists(json_file):
            with open(json_file, 'r', encoding='utf-8') as f:
                data = json.load(f)
                if isinstance(data, list):
                    all_data.extend(data)
                    print(f"合并 {json_file}: {len(data)} 条")
    # 去重（按 detail_url）
    seen = set()
    unique = []
    for item in all_data:
        gid = item.get('detail_url')
        if gid and gid not in seen:
            seen.add(gid)
            unique.append(item)
        elif not gid:
            unique.append(item)
    atomic_write_json(unique, final_output)
    print(f"合并完成，总条数 {len(unique)}，保存至 {final_output}")
    return unique

def clean_intermediate_files(files_to_delete):
    """删除中间文件（分片 JSON、进度文件、备份文件）"""
    for f in files_to_delete:
        if os.path.exists(f):
            os.remove(f)
            print(f"已删除: {f}")

def main():
    global should_exit
    print(f"========== 开始处理 {YEAR}年{MONTH}月数据（并行分片数: {NUM_SPLITS}） ==========")
    all_urls = load_all_urls(INPUT_FILE)
    if not all_urls:
        print("未找到 URL 文件或文件为空。")
        return

    splits = split_urls(all_urls, NUM_SPLITS)
    print(f"URL 总数: {len(all_urls)}, 分为 {len(splits)} 个分片")

    split_outputs = []
    progress_files = []
    backup_files = []
    futures = []
    with ThreadPoolExecutor(max_workers=NUM_SPLITS) as executor:
        for i, urls_part in enumerate(splits):
            if not urls_part:
                continue
            output_json = f"{YEAR}_{MONTH}_part{i+1}.json"
            progress_file = f"{YEAR}_{MONTH}_progress_part{i+1}.txt"
            cache_dir = f"browser_cache_{YEAR}_{MONTH}_part{i+1}"
            split_outputs.append(output_json)
            progress_files.append(progress_file)
            backup_files.append(output_json + ".bak")
            futures.append(executor.submit(worker, i, urls_part, output_json, progress_file, cache_dir))

        for future in as_completed(futures):
            future.result()   # 等待所有分片完成

    # 如果收到了退出信号，则不进行合并和清理，直接退出（保留中间文件以便续传）
    if should_exit:
        print("\n⚠️ 因收到退出信号而中断，中间文件已保留，下次运行将自动续传。")
        sys.exit(0)

    # 合并所有分片
    final_data = merge_results(split_outputs, FINAL_OUTPUT)

    # 验证数量，若一致则删除中间文件
    if len(final_data) == len(all_urls):
        print(f"✅ 数据完整！共 {len(final_data)} 条，与 URL 总数一致。正在清理中间文件...")
        all_intermediate = split_outputs + progress_files + backup_files
        clean_intermediate_files(all_intermediate)
    else:
        print(f"⚠️ 数据不完整！爬取到 {len(final_data)} 条，URL 共 {len(all_urls)} 条。保留中间文件以便续传。")
        print(f"缺失 {len(all_urls) - len(final_data)} 条，请检查日志后重新运行脚本（会自动续传）。")

    print(f"{YEAR}年{MONTH}月处理完成！")

if __name__ == "__main__":
    main()