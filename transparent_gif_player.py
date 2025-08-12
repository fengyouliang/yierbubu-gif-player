import sys
import os
import json
from PyQt5.QtWidgets import QApplication, QLabel, QMenu, QAction, QFileDialog, QSystemTrayIcon, QStyle, QMessageBox
from PyQt5.QtCore import Qt, QSize, QTimer, QEvent
from PyQt5.QtGui import QMovie, QPainter, QIcon

# 导入编译后的资源文件
# 确保您已经运行了 'pyrcc5 resources.qrc -o resources_rc.py' 命令
import resources_rc

class TransparentGifPlayer(QLabel):
    def __init__(self, gif_folder, config_path=None):
        super().__init__()
        
        # 托盘图标设置
        self._always_on_top = True  # 先定义，后面读取配置会覆盖

        # 检查系统托盘是否可用，否则弹窗提示
        if not QSystemTrayIcon.isSystemTrayAvailable():
            QMessageBox.critical(self, "错误", "系统托盘不可用，无法显示托盘图标！")
            # 如果系统托盘不可用，可以考虑退出应用程序或提供替代方案
            sys.exit(1) 

        # 使用资源文件中的图标
        # 关键修改：图标路径现在是 ":/icons/icon/output.png"，
        # 对应 resources.qrc 中 prefix="/icons" 和 <file>icon/output.png</file> 的组合
        resource_icon_path = ":/icons/icon/output.png" 
        icon = QIcon(resource_icon_path)
        
        if icon.isNull():
            # 如果资源文件中的图标加载失败，则使用系统默认图标作为备用
            icon = self.style().standardIcon(QStyle.SP_ComputerIcon)
            QMessageBox.warning(self, "警告", f"未能加载自定义托盘图标 '{resource_icon_path}'，将使用系统默认图标。请检查 resources.qrc 文件中路径是否正确，并确保 output.png 文件存在且有效。")
            print(f"DEBUG: Failed to load custom icon from {resource_icon_path}. Using system default.")
        else:
            print(f"DEBUG: Successfully loaded custom icon from {resource_icon_path}.")
            
        # 设置全局应用图标，部分环境下托盘依赖此设置
        app = QApplication.instance()
        if app is not None:
            app.setWindowIcon(icon)
        
        # 应用程序退出时，不关闭所有窗口，而是隐藏到托盘
        QApplication.setQuitOnLastWindowClosed(False)
        
        self.tray_icon = QSystemTrayIcon(icon, self)
        self.tray_icon.setToolTip('一二布布')
        self.tray_icon.setVisible(True)
        
        # 创建托盘菜单
        tray_menu = QMenu()
        
        # 显示窗口动作
        show_action = QAction('显示窗口', self)
        def show_window():
            self.showNormal()
            self.raise_()
            self.activateWindow()
            # 恢复自动切换和计时
            if self._auto_switch and not self._timer.isActive():
                self._timer.start(self._interval)
        show_action.triggered.connect(show_window)
        tray_menu.addAction(show_action)

        # 窗口置顶动作
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

        # 退出应用程序动作
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
                if self._auto_switch and not self._timer.isActive():
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
        self._flipped = False  # 左右翻转状态
        self._single_file_mode = False  # 单文件模式标志
        
        # 读取用户配置
        self._always_on_top = True # 默认置顶
        if config_path and os.path.isfile(config_path):
            try:
                with open(config_path, 'r', encoding='utf-8') as f:
                    cfg = json.load(f)
                user_folder = cfg.get('gif_folder')
                if user_folder and os.path.isdir(user_folder):
                    self._user_gif_folder = user_folder
                
                self._always_on_top = cfg.get('always_on_top', True)
                self._auto_switch = cfg.get('auto_switch', True)
                self._interval = cfg.get('interval', 60_000)
                self._flipped = cfg.get('flipped', False)
                self._single_file_mode = cfg.get('single_file_mode', False)
            except Exception as e:
                print(f"读取配置文件失败: {e}")
                pass # 忽略错误，使用默认配置
        
        # 应用置顶配置
        self._apply_always_on_top()
        
        # --- 关键修改：初始加载GIF文件夹逻辑 ---
        initial_folder_to_load = None
        if self._user_gif_folder and os.path.isdir(self._user_gif_folder):
            initial_folder_to_load = self._user_gif_folder
            print(f"DEBUG: Using user configured GIF folder: {initial_folder_to_load}")
        else:
            default_gif_folder = os.path.join(os.path.dirname(os.path.abspath(sys.argv[0])), 'gif')
            if os.path.isdir(default_gif_folder):
                gif_files_in_default = [f for f in os.listdir(default_gif_folder) if f.lower().endswith('.gif')]
                if gif_files_in_default:
                    initial_folder_to_load = default_gif_folder
                    print(f"DEBUG: Using default GIF folder: {initial_folder_to_load}")
                else:
                    print(f"DEBUG: Default GIF folder exists but is empty: {default_gif_folder}")
            else:
                print(f"DEBUG: Default GIF folder does not exist: {default_gif_folder}")

        if initial_folder_to_load:
            self.set_gif_folder(initial_folder_to_load, save_config=False)
        else:
            # 如果没有找到任何有效的GIF文件夹（用户配置或默认），则立即弹出选择框
            print("DEBUG: No valid GIF folder found, prompting user.")
            # 使用 singleShot 确保窗口初始化后再弹出对话框，避免阻塞
            QTimer.singleShot(100, self._ask_for_gif_folder)
            
        # 启动计时器（如果自动切换开启）
        if self._auto_switch:
            self._timer.start(self._interval)

    def _save_config(self, gif_folder=None):
        """保存所有相关配置到文件"""
        config = {}
        # gif_folder 优先参数，否则用当前
        if gif_folder is not None:
            config['gif_folder'] = gif_folder
        elif self._user_gif_folder:
            config['gif_folder'] = self._user_gif_folder
        
        # 其他配置
        config['always_on_top'] = self._always_on_top # 直接使用内部状态
        config['auto_switch'] = self._auto_switch
        config['interval'] = self._interval
        config['flipped'] = self._flipped
        config['single_file_mode'] = self._single_file_mode
        
        if self._config_path:
            try:
                with open(self._config_path, 'w', encoding='utf-8') as f:
                    json.dump(config, f, ensure_ascii=False, indent=2)
            except Exception as e:
                print(f"保存配置文件失败: {e}")
                pass

    def _apply_always_on_top(self):
        """根据 _always_on_top 状态应用窗口置顶标志"""
        flags = self.windowFlags()
        # 只保留 FramelessWindowHint，避免 Qt.Tool
        base_flags = Qt.FramelessWindowHint
        if self._always_on_top:
            self.setWindowFlags(base_flags | Qt.WindowStaysOnTopHint)
        else:
            self.setWindowFlags(base_flags)
        self.show() # 重新应用窗口标志需要调用 show()
        self.raise_()
        self.activateWindow()

    def showEvent(self, event):
        """窗口显示事件，此处不再用于首次询问文件夹，但保留以防万一"""
        super().showEvent(event)
        # 移除原有的 _need_ask_for_folder 逻辑，因为已在 __init__ 中处理
        # if getattr(self, '_need_ask_for_folder', False):
        #     QTimer.singleShot(100, self._ask_for_gif_folder)
        #     self._need_ask_for_folder = False # 确保只询问一次

    def _ask_for_gif_folder(self):
        """弹出文件对话框让用户选择GIF文件夹"""
        base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
        QMessageBox.information(self, "请选择GIF文件夹", "未检测到任何有效的GIF图片文件夹。\n\n请选择一个包含GIF图片的文件夹，或直接关闭窗口退出应用。")
        folder = QFileDialog.getExistingDirectory(self, '请选择包含GIF图片的文件夹', base_dir)
        if folder:
            self.set_gif_folder(folder, save_config=True)
        else:
            self.close()  # 用户未选则直接关闭窗口

    def set_gif_folder(self, gif_folder, save_config=True):
        """设置GIF文件夹并加载GIF图片"""
        while True: # 循环直到用户选择有效文件夹或退出
            if not os.path.isdir(gif_folder):
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
                        gif_folder = folder # 更新文件夹路径，继续循环
                        continue
                    else: # 用户取消选择，退出
                        self.close()
                        return
                else: # 用户点击退出
                    self.close()
                    return
            
            # 尝试加载GIF文件
            self.gif_list = [os.path.join(gif_folder, f) for f in os.listdir(gif_folder) if f.lower().endswith('.gif')]
            self.gif_list.sort()
            self.gif_index = 0
            
            if self.gif_list:
                # 重置为文件夹模式
                self._single_file_mode = False
                self.set_gif(self.gif_list[self.gif_index])
                # 保存用户选择
                if save_config:
                    self._user_gif_folder = gif_folder
                    self._save_config(gif_folder=gif_folder)
                break # 成功加载，退出循环
            else:
                self.clear() # 清除当前显示的GIF
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
                        gif_folder = folder # 更新文件夹路径，继续循环
                        continue
                    else: # 用户取消选择，退出
                        self.close()
                        return
                else: # 用户点击退出
                    self.close()
                    return

    def set_single_gif_file(self, gif_path, save_config=True):
        """设置单个GIF文件并进入单文件模式"""
        if not os.path.isfile(gif_path) or not gif_path.lower().endswith('.gif'):
            QMessageBox.warning(self, "无效文件", "请选择一个有效的GIF文件。")
            return
        
        # 设置单文件模式
        self._single_file_mode = True
        self.gif_list = [gif_path]
        self.gif_index = 0
        self.set_gif(gif_path)
        
        # 保存配置
        if save_config:
            # 保存文件所在目录作为用户文件夹
            self._user_gif_folder = os.path.dirname(gif_path)
            self._save_config()

    def set_gif(self, gif_path):
        """设置并播放GIF"""
        if self.movie:
            self.movie.stop()
        self.movie = QMovie(gif_path)
        self.setMovie(self.movie)
        self.movie.frameChanged.connect(self.update)  # 每帧刷新
        self.movie.start()

    def paintEvent(self, event):
        """绘制事件，用于绘制缩放后的GIF"""
        if not self.movie or not self.movie.isValid():
            super().paintEvent(event)
            return
        frame = self.movie.currentPixmap()
        if frame.isNull():
            super().paintEvent(event)
            return
        
        # 如果需要左右翻转，应用水平翻转变换
        if self._flipped:
            from PyQt5.QtGui import QTransform
            transform = QTransform()
            transform.scale(-1, 1)  # 水平翻转
            frame = frame.transformed(transform)
        
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
        """窗口大小改变事件"""
        # _update_scaled_size 已弃用，paintEvent 会自动处理缩放
        super().resizeEvent(event)

    def set_player_size(self, width, height):
        """设置播放器窗口大小"""
        self.resize(width, height)

    def mousePressEvent(self, event):
        """鼠标按下事件，用于拖动和调整大小"""
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
        """鼠标移动事件，用于拖动和调整大小"""
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
        """鼠标释放事件，用于结束拖动和调整大小"""
        self._resizing = False
        self._resize_dir = None
        self._dragging = False
        self._click_pos = None
        self._moved = False
        super().mouseReleaseEvent(event)

    def mouseDoubleClickEvent(self, event):
        """鼠标双击事件，用于切换GIF"""
        if event.button() == Qt.LeftButton:
            # 无论自动切换是否开启，左键双击都切换下一个并重置计时
            self.next_gif()
            if self._auto_switch:
                self._timer.start(self._interval)
        super().mouseDoubleClickEvent(event)

    def next_gif(self):
        """切换到下一个GIF"""
        if not self.gif_list:
            return
        # 在单文件模式下，不切换文件，只是重新开始播放当前文件
        if self._single_file_mode:
            self.set_gif(self.gif_list[0])  # 重新播放当前文件
            return
        self.gif_index = (self.gif_index + 1) % len(self.gif_list)
        self.set_gif(self.gif_list[self.gif_index])

    def prev_gif(self):
        """切换到上一个GIF"""
        if not self.gif_list:
            return
        # 在单文件模式下，不切换文件，只是重新开始播放当前文件
        if self._single_file_mode:
            self.set_gif(self.gif_list[0])  # 重新播放当前文件
            return
        self.gif_index = (self.gif_index - 1 + len(self.gif_list)) % len(self.gif_list) # 确保负数也能正确循环
        self.set_gif(self.gif_list[self.gif_index])

    def contextMenuEvent(self, event):
        """右键菜单事件"""
        menu = QMenu(self)
        
        # 置顶选项
        top_action = QAction('窗口置顶', self, checkable=True)
        top_action.setChecked(self._always_on_top) # 使用内部状态
        def toggle_top():
            self._always_on_top = not self._always_on_top
            self._apply_always_on_top()
            # 取消置顶时自动前置窗口，避免被遮挡
            if not self._always_on_top:
                self.showNormal()
                self.raise_()
                self.activateWindow()
            self._save_config()
        top_action.triggered.connect(toggle_top)
        menu.addAction(top_action)

        # 最小化到系统托盘
        minimize_action = QAction('最小化到系统托盘', self)
        def minimize_to_tray():
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

        # 自动切换选项
        auto_action = QAction('自动切换', self, checkable=True)
        auto_action.setChecked(self._auto_switch)
        def toggle_auto():
            self._auto_switch = not self._auto_switch
            if self._auto_switch:
                self._timer.start(self._interval)
            else:
                self._timer.stop()
            self._save_config()
            # 重新构建菜单以更新切换间隔子菜单的可见性
            self.contextMenuEvent(event) # 重新调用自身以刷新菜单
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
                # 使用 lambda 表达式捕获 ms 值
                act.triggered.connect(lambda checked, m=ms: self._set_interval_and_save(checked, m))
                interval_menu.addAction(act)
            menu.addMenu(interval_menu)

        # 左右翻转选项
        flip_action = QAction('左右翻转', self, checkable=True)
        flip_action.setChecked(self._flipped)
        def toggle_flip():
            self._flipped = not self._flipped
            self._save_config()
            self.update()  # 触发重绘
        flip_action.triggered.connect(toggle_flip)
        menu.addAction(flip_action)

        # 新增：选择文件夹
        select_folder_action = QAction('选择GIF文件夹...', self)
        def select_folder():
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            folder = QFileDialog.getExistingDirectory(self, '选择GIF文件夹', self._user_gif_folder or base_dir)
            if folder:
                self.set_gif_folder(folder, save_config=True)
        select_folder_action.triggered.connect(select_folder)
        menu.addAction(select_folder_action)

        # 新增：选择单个GIF文件
        select_file_action = QAction('选择单个GIF文件...', self)
        def select_file():
            base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
            file_path, _ = QFileDialog.getOpenFileName(self, '选择GIF文件', self._user_gif_folder or base_dir, 'GIF Files (*.gif)')
            if file_path:
                self.set_single_gif_file(file_path, save_config=True)
        select_file_action.triggered.connect(select_file)
        menu.addAction(select_file_action)

        close_action = QAction('关闭', self)
        close_action.triggered.connect(QApplication.instance().quit)
        menu.addAction(close_action)
        
        menu.exec_(event.globalPos())

    def _set_interval_and_save(self, checked, ms):
        """设置切换间隔并保存配置"""
        if checked:
            self._interval = ms
            if self._auto_switch:
                self._timer.start(self._interval)
            self._save_config()

    def keyPressEvent(self, event):
        """键盘按下事件，用于缩放和切换GIF"""
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
                    self._timer.start(self._interval) # 重置计时器
            elif event.key() == Qt.Key_Left:
                self.prev_gif()
                if self._auto_switch:
                    self._timer.start(self._interval) # 重置计时器
            elif event.key() == Qt.Key_F:
                # Ctrl+F 切换左右翻转
                self._flipped = not self._flipped
                self._save_config()
                self.update()  # 触发重绘
        super().keyPressEvent(event)

    def scale_player(self, factor):
        """缩放播放器窗口"""
        w = max(50, int(self.width() * factor))
        h = max(50, int(self.height() * factor))
        self.resize(w, h)

    def _get_resize_dir(self, pos):
        """获取鼠标位置对应的调整大小方向"""
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
        """窗口状态改变事件（例如最小化/恢复）"""
        if event.type() == QEvent.WindowStateChange:
            # 窗口从最小化恢复时，恢复自动切换计时
            if not self.isMinimized() and self.isVisible() and self._auto_switch and not self._timer.isActive():
                self._timer.start(self._interval)
            # 如果窗口被隐藏（例如最小化到托盘），则停止计时器
            elif not self.isVisible() and self._auto_switch and self._timer.isActive():
                self._timer.stop()
        super().changeEvent(event)

if __name__ == '__main__':
    # 捕获 Ctrl+C 信号，允许正常退出
    import signal
    signal.signal(signal.SIGINT, signal.SIG_DFL)
    
    # 设置应用程序用户模型ID，解决Windows任务栏图标分组问题
    try:
        import ctypes
        ctypes.windll.shell32.SetCurrentProcessExplicitAppUserModelID('yierbubu.transparentgifplayer')
    except AttributeError:
        # 非Windows系统可能没有此属性
        pass

    app = QApplication(sys.argv)
    app.setApplicationName('一二布布')
    app.setApplicationDisplayName('一二布布')
    
    # 默认使用当前目录下的 gif 文件夹
    base_dir = os.path.dirname(os.path.abspath(sys.argv[0]))
    gif_folder = os.path.join(base_dir, 'gif') # 默认GIF文件夹
    config_path = os.path.join(base_dir, 'user_config.json') # 用户配置文件路径
    
    player = TransparentGifPlayer(gif_folder, config_path=config_path)
    player.show()
    sys.exit(app.exec_())
