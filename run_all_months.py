import subprocess
import time
import os
import sys
import signal

# ================= 配置 =================
YEAR = 2025                     # 年份
START_MONTH = 1                # 起始月份
END_MONTH = 12                   # 结束月份
TIMEOUT_SECONDS = 90 * 60       # 单次运行超时（秒）
GRACE_PERIOD = 30               # 优雅退出等待时间（秒）
SCRIPT_NAME = "split_monthly.py"
PYTHON_EXE = sys.executable
PERSONAL = False                # 是否使用个人账号模式（与爬虫脚本中的 --personal 对应）
# =======================================

def run_month(month):
    print(f"\n{'='*60}")
    print(f"开始处理 {YEAR}年{month}月")
    print(f"{'='*60}")

    while True:
        cmd = [PYTHON_EXE, SCRIPT_NAME, "--year", str(YEAR), "--month", str(month)]
        if PERSONAL:
            cmd.append("--personal")
        print(f"执行命令: {' '.join(cmd)}")

        proc = subprocess.Popen(cmd)
        try:
            proc.wait(timeout=TIMEOUT_SECONDS)
            # 正常结束，该月份完成
            print(f"✅ {YEAR}年{month}月正常结束。")
            break
        except subprocess.TimeoutExpired:
            print(f"⚠️ {YEAR}年{month}月运行超过 {TIMEOUT_SECONDS//60} 分钟，尝试优雅终止...")
            # 先发送 SIGINT
            if sys.platform == "win32":
                # Windows 下使用 taskkill 发送 Ctrl+C 较为复杂，此处直接尝试 terminate
                proc.terminate()
            else:
                proc.send_signal(signal.SIGINT)
            # 等待进程退出
            try:
                proc.wait(timeout=GRACE_PERIOD)
                print("子进程已优雅退出。")
            except subprocess.TimeoutExpired:
                print("优雅退出超时，强制结束进程。")
                proc.terminate()
                try:
                    proc.wait(timeout=5)
                except subprocess.TimeoutExpired:
                    proc.kill()
                    proc.wait()
            print("等待 15 秒后重启...")
            time.sleep(15)
            # 继续 while 循环，重新运行同一个月（断点续传）

def main():
    for month in range(START_MONTH, END_MONTH + 1):
        run_month(month)
    print(f"\n🎉 {YEAR}年所有月份处理完毕！")

if __name__ == "__main__":
    main()
