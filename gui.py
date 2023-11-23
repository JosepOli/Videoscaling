from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QFileDialog,
    QProgressBar,
    QApplication,
    QListWidget,
)
from PyQt5.QtCore import Qt
from video_processor import VideoProcessor
import sys


class FileListWidget(QListWidget):
    def __init__(self, parent=None):
        super(FileListWidget, self).__init__(parent)
        self.setAcceptDrops(True)
        self.setDragDropMode(QListWidget.InternalMove)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dragMoveEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            event.setDropAction(Qt.CopyAction)
            event.accept()
            links = []
            for url in event.mimeData().urls():
                if url.isLocalFile():
                    links.append(str(url.toLocalFile()))
            self.addItems(links)
        else:
            event.ignore()


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_processor = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Upscaling App")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.file_list = FileListWidget()
        layout.addWidget(self.file_list)

        self.progress_bar = QProgressBar(self)
        layout.addWidget(self.progress_bar)

        self.upscale_button = QPushButton("Upscale Videos", self)
        self.upscale_button.clicked.connect(self.select_and_upscale_video)
        layout.addWidget(self.upscale_button)

        self.status_label = QLabel("Ready", self)
        layout.addWidget(self.status_label)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def select_and_upscale_video(self):
        if not self.file_list.count():
            self.select_files()

        destination_folder = QFileDialog.getExistingDirectory(
            self, "Select Destination Folder"
        )
        if self.file_list.count() and destination_folder:
            video_files = [
                self.file_list.item(i).text() for i in range(self.file_list.count())
            ]
            for video_file in video_files:
                processor = VideoProcessor(destination_folder, [video_file])
                processor.progress_updated.connect(self.update_progress)
                processor.start()
                processor.wait()  # Wait for the thread to finish
            self.status_label.setText("Upscaling Completed.")
        else:
            self.status_label.setText("No videos selected or destination not set.")

    def update_progress(self, progress):
        self.progress_bar.setValue(progress)

    def select_files(self):
        file_dialog = QFileDialog()
        video_files, _ = file_dialog.getOpenFileNames(
            self, "Select Video Files", "", "Video Files (*.mp4 *.avi *.mkv)"
        )
        for file in video_files:
            self.file_list.addItem(file)


if __name__ == "__main__":
    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
