import sys
import logging
from pathlib import Path

from src.utils.paths import is_frozen

if not is_frozen():
    project_root = Path(__file__).resolve().parent.parent
    sys.path.insert(0, str(project_root))

from PySide6.QtWidgets import QApplication

from src.utils.logging_config import setup_logging

logger = setup_logging(log_level=logging.INFO)
logger.info("=" * 60)
logger.info("S3MANAGER başlatılıyor...")
logger.info("=" * 60)

from src.ui.qt.main_window import MainWindow


def main():
    """Main application entry point - PySide6 Version"""
    try:
        app = QApplication(sys.argv)

        logger.info("QApplication oluşturuldu")
        window = MainWindow()
        logger.info("MainWindow oluşturuldu")
        window.show()
        logger.info("MainWindow gösteriliyor")

        logger.info("Uygulama çalışıyor...")
        exit_code = app.exec()
        logger.info("=" * 60)
        logger.info("S3MANAGER kapatılıyor...")
        logger.info("=" * 60)
        sys.exit(exit_code)
    except Exception as e:
        logger.critical(f"Kritik hata: {str(e)}", exc_info=True)
        raise


if __name__ == "__main__":
    main()
