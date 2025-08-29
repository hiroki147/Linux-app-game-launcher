import sys
import os
import json
import subprocess
from PyQt5.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QMessageBox,
    QFileDialog, QHBoxLayout, QScrollArea, QFrame, QTabWidget
)
from PyQt5.QtGui import QIcon, QPixmap, QFont
from PyQt5.QtCore import Qt

CONFIG_PATH = "launcher_config.json"

def load_config():
    if not os.path.exists(CONFIG_PATH):
        return {"items": []}
    with open(CONFIG_PATH, "r") as f:
        return json.load(f)

def save_config(config):
    with open(CONFIG_PATH, "w") as f:
        json.dump(config, f, indent=2)

def parse_desktop_file(path):
    info = {
        "name": os.path.basename(path),
        "exec": "",
        "icon": "",
        "path": path,
        "type": "app"  # default type
    }
    try:
        with open(path, "r") as f:
            in_desktop_entry = False
            for line in f:
                line = line.strip()
                if line.startswith("[Desktop Entry]"):
                    in_desktop_entry = True
                    continue
                elif line.startswith("[") and not line.startswith("[Desktop Entry]"):
                    in_desktop_entry = False
                if in_desktop_entry:
                    if line.startswith("Name="):
                        info["name"] = line.split("=", 1)[1]
                    elif line.startswith("Exec="):
                        info["exec"] = line.split("=", 1)[1].split()[0]
                    elif line.startswith("Icon="):
                        info["icon"] = line.split("=", 1)[1]
    except Exception as e:
        print(f"Error reading {path}: {e}")
    return info

def find_icon_path(icon_name):
    if os.path.isabs(icon_name) and os.path.exists(icon_name):
        return icon_name
    possible_dirs = [
        "/usr/share/icons/hicolor/48x48/apps/",
        "/usr/share/pixmaps/"
    ]
    for d in possible_dirs:
        for ext in [".png", ".svg", ".xpm"]:
            candidate = os.path.join(d, icon_name + ext)
            if os.path.exists(candidate):
                return candidate
    return None

class LauncherWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Linux アプリ＆ゲーム ランチャー")
        self.setGeometry(300, 300, 540, 420)
        self.config = load_config()
        self.desktop_infos = []
        self.refresh_desktop_infos()

        main_layout = QVBoxLayout()

        # タイトルを大きく
        title_label = QLabel("Linux アプリ＆ゲーム ランチャー")
        title_font = QFont()
        title_font.setPointSize(20)
        title_font.setBold(True)
        title_label.setFont(title_font)
        title_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(title_label)

        # app/game タブ
        self.tab_widget = QTabWidget()
        self.app_frame = self.create_apps_frame("app")
        self.game_frame = self.create_apps_frame("game")
        self.tab_widget.addTab(self.app_frame, "App")
        self.tab_widget.addTab(self.game_frame, "Game")
        main_layout.addWidget(self.tab_widget)

        # 追加・削除ボタン（下部）
        btn_layout = QHBoxLayout()
        add_btn = QPushButton("追加 (.desktop)")
        add_btn.clicked.connect(self.add_desktop_file)
        btn_layout.addWidget(add_btn)
        del_btn = QPushButton("選択削除")
        del_btn.clicked.connect(self.delete_selected_item)
        btn_layout.addWidget(del_btn)
        main_layout.addLayout(btn_layout)

        self.setLayout(main_layout)
        self.selected_item = None  # 削除用

    def refresh_desktop_infos(self):
        self.desktop_infos = []
        for item in self.config.get("items", []):
            info = parse_desktop_file(item["path"])
            info["type"] = item.get("type", "app")
            self.desktop_infos.append(info)

    def create_apps_frame(self, target_type):
        frame = QFrame()
        layout = QVBoxLayout()
        for info in self.desktop_infos:
            if info["type"] != target_type:
                continue
            row = QHBoxLayout()
            icon_path = find_icon_path(info["icon"])
            if icon_path:
                pixmap = QPixmap(icon_path).scaled(32, 32)
                icon_label = QLabel()
                icon_label.setPixmap(pixmap)
            else:
                icon_label = QLabel("🗂")
            row.addWidget(icon_label)

            btn = QPushButton(info["name"])
            btn.setStyleSheet("font-size: 16px; padding: 8px;")
            btn.clicked.connect(lambda checked, cmd=info["exec"]: self.launch_app(cmd))
            row.addWidget(btn)

            # 選択用（削除時）
            select_btn = QPushButton("選択")
            select_btn.setMaximumWidth(60)
            select_btn.clicked.connect(lambda checked, path=info["path"]: self.select_item(path))
            row.addWidget(select_btn)

            # タイプ表示
            type_label = QLabel(info["type"])
            type_label.setMaximumWidth(50)
            row.addWidget(type_label)

            layout.addLayout(row)
        frame.setLayout(layout)
        return frame

    def refresh_tabs(self):
        # タブの内容を更新
        self.tab_widget.removeTab(1)
        self.tab_widget.removeTab(0)
        self.app_frame = self.create_apps_frame("app")
        self.game_frame = self.create_apps_frame("game")
        self.tab_widget.addTab(self.app_frame, "App")
        self.tab_widget.addTab(self.game_frame, "Game")

    def add_desktop_file(self):
        fname, _ = QFileDialog.getOpenFileName(self, "Select .desktop file", "/usr/share/applications/", "Desktop Files (*.desktop)")
        if fname:
            info = parse_desktop_file(fname)
            # タイプ選択ダイアログ
            type_btn = QMessageBox()
            type_btn.setWindowTitle("タイプ選択")
            type_btn.setText("game ですか？ app ですか？")
            game_btn = type_btn.addButton("Game", QMessageBox.YesRole)
            app_btn = type_btn.addButton("App", QMessageBox.NoRole)
            type_btn.exec_()
            if type_btn.clickedButton() == game_btn:
                item_type = "game"
            else:
                item_type = "app"
            # 重複チェック
            if any([item["path"] == fname for item in self.config.get("items", [])]):
                QMessageBox.warning(self, "既に登録済み", "この.desktopファイルは既に登録されています。")
                return
            self.config.setdefault("items", []).append({
                "path": fname,
                "type": item_type
            })
            save_config(self.config)
            self.refresh_desktop_infos()
            self.refresh_tabs()
            QMessageBox.information(self, "追加", ".desktopファイルを追加しました。")

    def select_item(self, path):
        self.selected_item = path
        QMessageBox.information(self, "選択", f"削除対象に選択: {os.path.basename(path)}")

    def delete_selected_item(self):
        if self.selected_item:
            self.config["items"] = [item for item in self.config["items"] if item["path"] != self.selected_item]
            save_config(self.config)
            self.refresh_desktop_infos()
            self.refresh_tabs()
            QMessageBox.information(self, "削除", "削除しました。")
            self.selected_item = None
        else:
            QMessageBox.warning(self, "未選択", "削除対象を選択してください。")

    def launch_app(self, command):
        try:
            subprocess.Popen(command.split())
        except Exception as e:
            QMessageBox.critical(self, "起動エラー", f"{command} の起動に失敗しました。\n{e}")

if __name__ == "__main__":
    app = QApplication(sys.argv)
    window = LauncherWindow()
    window.show()
    sys.exit(app.exec_())
