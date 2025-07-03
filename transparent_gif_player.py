import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QLabel, QMenu, QAction, QFileDialog, QSystemTrayIcon, QStyle, QMessageBox
from PyQt5.QtCore import Qt, QSize, QTimer
from PyQt5.QtGui import QMovie, QPainter, QIcon

class TransparentGifPlayer(QLabel):
    def __init__(self, gif_folder, config_path=None):
        super().__init__()
        # 托盘图标
        self._always_on_top = True  # 先定义，后面读取配置会覆盖
        # 托盘图标需要QApplication已初始化，且建议用QIcon
        # 优先使用内嵌资源图标
        # 检查系统托盘是否可用，否则弹窗提示
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(self, "错误", "系统托盘不可用，无法显示托盘图标！")
        # 设置自定义托盘图标（本地文件，便于调试和打包）
        icon_path = os.path.join(os.path.dirname(sys.argv[0]), 'icon', 'output.png')
        icon = QIcon(icon_path)
        if icon.isNull():
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
        # 设置全局应用图标，部分环境下托盘依赖此设置
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        QApplication.setQuitOnLastWindowClosed(False)
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip('一二布布')
        self.tray_icon.setVisible(True)
        tray_menu = QMenu()
        show_action = QAction('显示窗口', self)
        def show_window():
            self.showNormal()
            self.raise_()
            self.activateWindow()
        show_action.triggered.connect(show_window)
        tray_menu.addAction(show_action)

        top_action = QAction('窗口置顶', self, checkable=True)
        top_action.setChecked(self._always_on_top)
        def tray_toggle_top():
            self._always_on_top = not self._always_on_top
            self._apply_always_on_top()
            self._save_config()
            top_action.setChecked(self._always_on_top)
            # 取消置顶时自动前置窗口，避免被遮挡
            if not self._always_on_top:
                self.showNormal()
                self.raise_()
                self.activateWindow()
        top_action.triggered.connect(tray_toggle_top)
        tray_menu.addAction(top_action)

        quit_action = QAction('退出', self)
        quit_action.triggered.connect(QApplication.instance().quit)
        tray_menu.addAction(quit_action)

        self.tray_icon.setContextMenu(tray_menu)
        self.tray_icon.show()

        # 托盘图标单击/双击恢复窗口
        def tray_restore(reason):
            if reason in (QSystemTrayIcon.DoubleClick, QSystemTrayIcon.Trigger):
                self.showNormal()  # 恢复窗口，重新出现在任务栏和 Alt+Tab
                self.raise_()
                self.activateWindow()
                # 恢复自动切换和计时
                if self._auto_switch:
                    self._timer.start(self._interval)
        self.tray_icon.activated.connect(tray_restore)

        # 设置窗口标志：无边框、置顶、透明
        # 只用 FramelessWindowHint，避免 Qt.Tool 导致无法 Alt+Tab/任务栏找回
        self.setWindowFlags(Qt.WindowStaysOnTopHint | Qt.FramelessWindowHint)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self._default_size = QSize(200, 200)
        self.resize(self._default_size)
        self._margin = 8  # 边缘判定宽度
        self._interval = 60_000  # 默认1分钟
        self._auto_switch = True
        self._timer = QTimer(self)
        self._timer.timeout.connect(self.next_gif)
        self.setAlignment(Qt.AlignCenter)
        self._resizing = False
        self._resize_dir = None
        self._mouse_pos = None
        self._dragging = False
        self._drag_pos = None
        self._click_pos = None
        self._moved = False
        self.movie = None
        self.gif_index = 0
        self.gif_list = []
        self._config_path = config_path
        self._user_gif_folder = None
        # 读取用户配置
        self._always_on_top = True
        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                user_folder = cfg.get('gif_folder')
                if user_folder and os.path.isdir(user_folder):
                    self._user_gif_folder = user_folder
                # 新增读取配置
                self._always_on_top = cfg.get('always_on_top', True)
                self._auto_switch = cfg.get('auto_switch', True)
                self._interval = cfg.get('interval', 60_000)
            except Exception:
                pass
        # 应用置顶配置
        self._apply_always_on_top()
        # 修复：首次无gif时立即弹出选择框
        if getattr(self, '_need_ask_for_folder', False):
            self._ask_for_gif_folder()

    def _save_config(self, gif_folder=None):
        # 保存所有相关配置
        config = {}
        # gif_folder 优先参数，否则用当前
        if gif_folder is not None:
            config['gif_folder'] = gif_folder
        elif self._user_gif_folder:
            config['gif_folder'] = self._user_gif_folder
        # 其他配置
        config['always_on_top'] = bool(self.windowFlags() & Qt.WindowStaysOnTopHint)
        config['auto_switch'] = self._auto_switch
        config['interval'] = self._interval
        if self._config_path:
            try:
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception:
                pass

    def _apply_always_on_top(self):
        flags = self.windowFlags()
        # 只保留 FramelessWindowHint，避免 Qt.Tool
        base_flags = Qt.FramelessWindowHint
        if self._always_on_top:
            self.setWindowFlags(base_flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(base_flags)
        self.show()
        self.raise_()
        self.activateWindow()
        self._need_ask_for_folder = False
        if self._user_gif_folder:
            self.set_gif_folder(self._user_gif_folder)
        else:
            # 检查默认文件夹是否存在且有gif，否则首次启动弹出选择框（延后到showEvent）
            if os.path.isdir(gif_folder):
                gif_files = [f for f in os.listdir(gif_folder) if f.lower().endswith('.gif')]
            else:
                gif_files = []
            if gif_files:
                self.set_gif_folder(gif_folder)
            else:
                self._need_ask_for_folder = True
        self._timer.start(self._interval)

    def showEvent(self, event):
        super().showEvent(event)
        if getattr(self, '_need_ask_for_folder', False):
            from PyQt5.QtCore import QTimer
            QTimer.singleShot(100, self._ask_for_gif_folder)

    def _ask_for_gif_folder(self):
        from PyQt5.QtWidgets import QFileDialog, QMessageBox
        import os
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        QMessageBox.information(self, "请选择GIF文件夹", "未检测到默认gif文件夹或其中无gif图片。\n\n请选择一个包含GIF图片的文件夹，或直接关闭窗口退出应用。")
        folder = QFileDialog.getExistingDirectory(self, '请选择包含GIF图片的文件夹', base_dir)
        if folder:
            self.set_gif_folder(folder, save_config=True)
            self._need_ask_for_folder = False
        else:
            self.close()  # 用户未选则直接关闭窗口

    def set_gif_folder(self, gif_folder, save_config=True):
        from PyQt5.QtWidgets import QMessageBox
        if not os.path.isdir(gif_folder):
            self.gif_list = []
            self.clear()
            from PyQt5.QtWidgets import QMessageBox, QFileDialog
            while True:
                box = QMessageBox(self)
                box.setWindowTitle("未找到文件夹")
                box.setText(f"未找到文件夹：{gif_folder}\n\n请选择一个包含GIF图片的文件夹，或退出程序。")
                choose_btn = box.addButton("选择文件夹", QMessageBox.AcceptRole)
                exit_btn = box.addButton("退出", QMessageBox.RejectRole)
                box.setDefaultButton(choose_btn)
                box.exec_()
                if box.clickedButton() == choose_btn:
                    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                    folder = QFileDialog.getExistingDirectory(self, '请选择包含GIF图片的文件夹', base_dir)
                    if folder:
                        self.set_gif_folder(folder, save_config=True)
                        return
                    # 否则继续弹出对话框
                else:
                    self.close()
                    return
        while True:
            self.gif_list = [os.path.join(gif_folder, f) for f in os.listdir(gif_folder) if f.lower().endswith('.gif')]
            self.gif_list.sort()
            self.gif_index = 0
            if self.gif_list:
                self.set_gif(self.gif_list[self.gif_index])
                # 保存用户选择
                if save_config:
                    self._user_gif_folder = gif_folder
                    self._save_config(gif_folder=gif_folder)
                break
            else:
                self.clear()
                from PyQt5.QtWidgets import QFileDialog
                box = QMessageBox(self)
                box.setWindowTitle("没有GIF图片")
                box.setText(f"文件夹 {gif_folder} 下没有找到任何GIF图片。\n\n请选择一个包含GIF图片的文件夹，或退出程序。")
                choose_btn = box.addButton("选择文件夹", QMessageBox.AcceptRole)
                exit_btn = box.addButton("退出", QMessageBox.RejectRole)
                box.setDefaultButton(choose_btn)
                box.exec_()
                if box.clickedButton() == choose_btn:
                    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
                    folder = QFileDialog.getExistingDirectory(self, '请选择包含GIF图片的文件夹', base_dir)
                    if folder:
                        gif_folder = folder
                        continue
                    # 否则继续弹出对话框
                else:
                    self.close()
                    break

    def set_gif(self, gif_path):
        if self.movie:
            self.movie.stop()
        self.movie = QMovie(gif_path)
        self.setMovie(self.movie)
        self.movie.frameChanged.connect(self.update)  # 每帧刷新
        self.movie.start()

    def paintEvent(self, event):
        if not self.movie or not self.movie.isValid():
            super().paintEvent(event)
            return
        frame = self.movie.currentPixmap()
        if frame.isNull():
            super().paintEvent(event)
            return
        painter = QPainter(self)
        # 计算缩放比例，保持原比例，居中
        widget_w, widget_h = self.width(), self.height()
        frame_w, frame_h = frame.width(), frame.height()
        scale = min(widget_w / frame_w, widget_h / frame_h)
        new_w = int(frame_w * scale)
        new_h = int(frame_h * scale)
        x = (widget_w - new_w) // 2
        y = (widget_h - new_h) // 2
        painter.drawPixmap(x, y, new_w, new_h, frame)

    def resizeEvent(self, event):
        self._update_scaled_size()
        super().resizeEvent(event)

    def _update_scaled_size(self):
        # 已弃用，保留接口防止报错
        pass

    def set_player_size(self, width, height):
        self.resize(width, height)
        # 不再直接缩放movie，交给paintEvent处理

    def mousePressEvent(self, event):
        if event.button() == Qt.LeftButton:
            self._resize_dir = self._get_resize_dir(event.pos())
            self._moved = False
            if self._resize_dir:
                self._resizing = True
                self._mouse_pos = event.globalPos()
                self._start_geom = self.geometry()
            else:
                self._resizing = False
                self._dragging = True
                self._drag_pos = event.globalPos() - self.frameGeometry().topLeft()
                self._click_pos = event.globalPos()
        super().mousePressEvent(event)

    def mouseMoveEvent(self, event):
        if self._resizing and self._resize_dir:
            diff = event.globalPos() - self._mouse_pos
            rect = self._start_geom
            new_geom = rect
            if 'left' in self._resize_dir:
                new_geom.setLeft(rect.left() + diff.x())
            if 'right' in self._resize_dir:
                new_geom.setRight(rect.right() + diff.x())
            if 'top' in self._resize_dir:
                new_geom.setTop(rect.top() + diff.y())
            if 'bottom' in self._resize_dir:
                new_geom.setBottom(rect.bottom() + diff.y())
            minw, minh = 50, 50
            if new_geom.width() < minw:
                new_geom.setWidth(minw)
            if new_geom.height() < minh:
                new_geom.setHeight(minh)
            self.setGeometry(new_geom)
        elif self._dragging:
            self.move(event.globalPos() - self._drag_pos)
            if self._click_pos and (event.globalPos() - self._click_pos).manhattanLength() > 5:
                self._moved = True
        else:
            # 设置鼠标样式
            dir = self._get_resize_dir(event.pos())
            if dir in ('left', 'right'):
                self.setCursor(Qt.SizeHorCursor)
            elif dir in ('top', 'bottom'):
                self.setCursor(Qt.SizeVerCursor)
            elif dir in ('top_left', 'bottom_right'):
                self.setCursor(Qt.SizeFDiagCursor)
            elif dir in ('top_right', 'bottom_left'):
                self.setCursor(Qt.SizeBDiagCursor)
            else:
                self.setCursor(Qt.ArrowCursor)
        super().mouseMoveEvent(event)

    def mouseReleaseEvent(self, event):
        if self._dragging and not self._moved and not self._resize_dir:
            # 无论自动切换是否开启，左键点击都切换下一个并重置计时
            self.next_gif()
            if self._auto_switch:
                self._timer.start(60_000)
        self._resizing = False
        self._resize_dir = None
        self._dragging = False
        self._click_pos = None
        self._moved = False
        super().mouseReleaseEvent(event)

    def next_gif(self):
        if not self.gif_list:
            return
        self.gif_index = (self.gif_index + 1) % len(self.gif_list)
        self.set_gif(self.gif_list[self.gif_index])

    def prev_gif(self):
        if not self.gif_list:
            return
        self.gif_index = (self.gif_index - 1) % len(self.gif_list)
        self.set_gif(self.gif_list[self.gif_index])

    def contextMenuEvent(self, event):
        menu = QMenu(self)
        # 置顶选项
        top_action = QAction('窗口置顶', self, checkable=True)
        top_action.setChecked(self.windowFlags() & Qt.WindowStaysOnTopHint)
        def toggle_top():
            flags = self.windowFlags()
            if top_action.isChecked():
                self.setWindowFlags(flags | Qt.WindowStaysOnTopHint)
                self._always_on_top = True
            else:
                self.setWindowFlags(flags & ~Qt.WindowStaysOnTopHint)
                self._always_on_top = False
                # 取消置顶时自动前置窗口，避免被遮挡
                self.showNormal()
                self.raise_()
                self.activateWindow()
            self.show()  # 重新应用窗口标志
            self._save_config()
        top_action.triggered.connect(toggle_top)
        menu.addAction(top_action)

        # 最小化到系统托盘
        minimize_action = QAction('最小化到系统托盘', self)
        def minimize_to_tray():
            # self.showMinimized()  # 原逻辑
            self.hide()  # 隐藏窗口，彻底从任务栏和 Alt+Tab 消失
            # 最小化时暂停自动切换和计时
            if self._auto_switch:
                self._timer.stop()
            # Win11等系统托盘可能被隐藏，弹出提示
            self.tray_icon.showMessage(
                '一二布布',
                '已最小化到系统托盘，点击托盘图标可恢复窗口。',
                QSystemTrayIcon.Information,
                3000
            )
        minimize_action.triggered.connect(minimize_to_tray)
        menu.addAction(minimize_action)

        auto_action = QAction('自动切换', self, checkable=True)
        auto_action.setChecked(self._auto_switch)
        def toggle_auto():
            self._auto_switch = not self._auto_switch
            if self._auto_switch:
                self._timer.start(self._interval)
            else:
                self._timer.stop()
            self._save_config()
        auto_action.triggered.connect(toggle_auto)
        menu.addAction(auto_action)

        # 仅自动切换开启时显示切换间隔子菜单
        if self._auto_switch:
            interval_menu = QMenu('切换间隔', self)
            intervals = [
                ('1秒', 1_000),
                ('10秒', 10_000),
                ('30秒', 30_000),
                ('1分钟', 60_000),
                ('3分钟', 180_000),
                ('5分钟', 300_000),
            ]
            for label, ms in intervals:
                act = QAction(label, self, checkable=True)
                act.setChecked(self._interval == ms)
                def set_interval(checked, ms=ms):
                    if checked:
                        self._interval = ms
                        if self._auto_switch:
                            self._timer.start(self._interval)
                        self._save_config()
                act.triggered.connect(set_interval)
                interval_menu.addAction(act)
            menu.addMenu(interval_menu)

        # 新增：选择文件夹
        select_folder_action = QAction('选择GIF文件夹...', self)
        def select_folder():
            folder = QFileDialog.getExistingDirectory(self, '选择GIF文件夹', os.getcwd())
            if folder:
                self.set_gif_folder(folder, save_config=True)
        select_folder_action.triggered.connect(select_folder)
        menu.addAction(select_folder_action)

        close_action = QAction('关闭', self)
        close_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(close_action)
        menu.exec_(event.globalPos())

    def keyPressEvent(self, event):
        if event.modifiers() & Qt.ControlModifier:
            if event.key() in (Qt.Key_Plus, Qt.Key_Equal):  # 支持主键盘+和小键盘+
                self.scale_player(1.1)
            elif event.key() == Qt.Key_Minus:
                self.scale_player(0.9)
            elif event.key() == Qt.Key_0:
                self.resize(self._default_size)
            elif event.key() == Qt.Key_Right:
                self.next_gif()
                if self._auto_switch:
                    self._timer.start(self._interval)
            elif event.key() == Qt.Key_Left:
                self.prev_gif()
                if self._auto_switch:
                    self._timer.start(self._interval)
        super().keyPressEvent(event)

    def scale_player(self, factor):
        w = max(50, int(self.width() * factor))
        h = max(50, int(self.height() * factor))
        self.resize(w, h)
        # 不再直接缩放movie，交给paintEvent处理

    def _get_resize_dir(self, pos):
        x, y, w, h, m = pos.x(), pos.y(), self.width(), self.height(), self._margin
        left = x < m
        right = x > w - m
        top = y < m
        bottom = y > h - m
        if left and top:
            return 'top_left'
        if right and top:
            return 'top_right'
        if left and bottom:
            return 'bottom_left'
        if right and bottom:
            return 'bottom_right'
        if left:
            return 'left'
        if right:
            return 'right'
        if top:
            return 'top'
        if bottom:
            return 'bottom'
        return None

    def changeEvent(self, event):
        # 窗口从最小化恢复时，恢复自动切换计时
        from PyQt5.QtCore import QEvent
        if event.type() == QEvent.WindowStateChange:
            if not self.isMinimized() and self._auto_switch:
                self._timer.start(self._interval)
        super().changeEvent(event)

if __name__ == '__main__':
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    import ctypes
    ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('yierbubu')
    app = QApplication(sys.argv)
    app.setApplicationName('一二布布')
    app.setApplicationDisplayName('一二布布')
    # 默认使用当前目录下的 gif 文件夹
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    gif_folder = os.path.join(base_dir, 'gif')
    config_path = os.path.join(base_dir, 'user_config.json')
    player = TransparentGifPlayer(gif_folder, config_path=config_path)
    player.show()
    sys.exit(app.exec_())
