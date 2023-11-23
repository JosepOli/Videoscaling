from PyQt5.QtWidgets import (
    QMainWindow,
    QVBoxLayout,
    QPushButton,
    QWidget,
    QLabel,
    QFileDialog,
)
from video_processor import VideoProcessor
import os


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.video_processor = None
        self.init_ui()

    def init_ui(self):
        self.setWindowTitle("Video Upscaling App")
        self.setGeometry(100, 100, 800, 600)

        layout = QVBoxLayout()

        self.status_label = QLabel(
            "Select videos and destination to start upscaling.", self
        )
        layout.addWidget(self.status_label)

        self.upscale_button = QPushButton("Select Videos and Upscale", self)
        self.upscale_button.clicked.connect(self.select_and_upscale_video)
        layout.addWidget(self.upscale_button)

        central_widget = QWidget()
        central_widget.setLayout(layout)
        self.setCentralWidget(central_widget)

    def select_and_upscale_video(self):
        # Select Video Files
        file_dialog = QFileDialog()
        video_files, _ = file_dialog.getOpenFileNames(
            self, "Select Video Files", "", "Video Files (*.mp4 *.avi *.mkv)"
        )

        # Select Destination Folder
        destination_folder = file_dialog.getExistingDirectory(
            self, "Select Destination Folder"
        )

        if video_files and destination_folder:
            self.video_processor = VideoProcessor(destination_folder, video_files)
            self.video_processor.run()
            self.status_label.setText("Upscaling Completed.")
        else:
            self.status_label.setText("No videos selected or destination not set.")


if __name__ == "__main__":
    from PyQt5.QtWidgets import QApplication
    import sys

    app = QApplication(sys.argv)
    main_window = MainWindow()
    main_window.show()
    sys.exit(app.exec_())
