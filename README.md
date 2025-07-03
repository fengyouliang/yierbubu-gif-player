# GIF透明播放器打包与使用说明

## 一、环境准备

1. 安装 Python 3.7+（推荐 64 位，打包后目标电脑无需安装 Python）
2. 安装依赖库：
   ```bash
   pip install pyinstaller PyQt5
   ```

## 二、打包命令





在 `transparent_gif_player.py` 所在目录下打开命令行，**每次打包前建议加 --clean 参数，避免旧的 .spec 文件或缓存导致路径错误**：

```powershell
pyinstaller --clean --noconsole --onefile --name "一二布布" --distpath dist_build --workpath dist_build/build --specpath dist_build --exclude-module test --exclude-module tkinter transparent_gif_player.py
```

### GitHub Actions 自动发布 Release

如需用 GitHub Actions 自动打包并发布 release，需在推送 tag 时触发 workflow。操作如下：

1. 修改/确认 `.github/workflows/release.yml` 的 `on` 部分如下：
   ```yaml
   on:
     push:
       tags:
         - 'v*'  # 只有推送 tag 时才触发
   ```
2. 打 tag 并推送（如 v1.0.1）：
   ```powershell
   git tag v1.0.1
   git push origin v1.0.1
   ```
3. Actions 会自动打包并上传 exe 到 Release 页面。

- `--noconsole`：不弹出命令行窗口（适合 GUI 程序）
- `--onefile`：生成单一 exe 文件，便于分发

打包完成后，`dist_build` 目录下会生成 `一二布布.exe`，可直接运行。

**注意事项：**
- 如果你更换了打包参数或遇到“Unable to find ... gif”报错，请务必加上 `--clean` 参数，或手动删除 `dist_build/一二布布.spec` 后再打包。


## 三、使用说明

1. 将 `一二布布.exe` 分发到目标电脑。
2. 双击运行 `一二布布.exe`，首次启动时请选择包含 gif 动图的文件夹。
3. 右键点击播放器窗口，可选择：
   - "选择GIF文件夹..." 切换播放其他文件夹
   - "自动切换"、"切换间隔"、"窗口置顶"等功能
   - "关闭" 退出程序

## 四、常见问题

- 若目标电脑缺少 VC++ 运行库，需安装 [Microsoft Visual C++ Redistributable](https://aka.ms/vs/17/release/vc_redist.x64.exe)
- 若选择的文件夹为空或无 gif 文件，会提示重新选择

### 其他说明与常见易混点

- 最小化到系统托盘后，窗口会彻底从任务栏和 Alt+Tab 消失，点击托盘图标可恢复窗口。
- 最小化到托盘时自动暂停 GIF 切换，恢复窗口时自动恢复切换。
- “窗口置顶”“自动切换”“切换间隔”等选项会自动保存到 user_config.json，重启后自动恢复。
- 若托盘图标不显示，请先用标准图标测试，确认是图片问题还是系统环境问题。
- Windows 11 下托盘图标可能被收纳到隐藏区，可在任务栏设置中调整显示。

## 五、自定义托盘图标（内嵌到exe，无需外部文件）



1. 用 `icon_util.py` 处理你的 PNG 图标，生成 32x32（或 16x16）不带透明通道的 PNG：
   ```bash
   python icon_util.py
   ```
   生成的 `output.png` 会在 `icon/output.png` 路径下。

2. 主程序自动读取本地图片，无需资源编译：
   ```python
   icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icon', 'output.png')
   icon = QIcon(icon_path)
   if icon.isNull():
       icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
   ```

3. 打包时需加参数确保图片被包含：
   ```powershell
   --add-data "icon/output.png;icon"
   ```

4. 运行主程序，系统托盘即显示你的自定义图标。

5. 运行主程序，系统托盘即显示你的自定义图标。

> 如托盘仍显示默认图标，务必检查图片尺寸、色深、透明度，建议用 32x32 PNG 且有不透明像素。每次更换图片都要重新 pyrcc5 编译资源。

## 六、开发/调试

- 可直接运行 `python transparent_gif_player.py` 进行调试
- 默认会提示选择 gif 文件夹

---

如有问题可联系开发者。
