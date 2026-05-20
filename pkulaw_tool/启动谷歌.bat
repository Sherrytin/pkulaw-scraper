@echo off
echo 正在启动Chrome浏览器，请稍候...
start "" "C:\Program Files\Google\Chrome\Application\chrome.exe" --remote-debugging-port=9333 --user-data-dir="D:\chrome_temp"
echo Chrome浏览器已启动，远程调试端口为9333
echo 请不要关闭此窗口，直接最小化即可
echo 关闭此窗口将导致爬虫无法连接到浏览器
pause