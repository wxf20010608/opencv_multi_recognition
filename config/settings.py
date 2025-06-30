import os
from pathlib import Path

class Config:
    BASE_DIR = Path(__file__).resolve().parent.parent
    # 模型路径
    MODEL_PATHS = {
        'face_cascade': 'models/haarcascade_frontalface_default.xml',
        'paddleocr': {
            'det_model_dir': 'models/ch_ppocr_server_v2.0_det_infer',
            'rec_model_dir': 'models/ch_ppocr_server_v2.0_rec_infer',
            'cls_model_dir': 'models/ch_ppocr_mobile_v2.0_cls_infer'
        }
    }

    LOG_CONFIG = {
        'level': 'INFO',  # DEBUG/INFO/WARNING/ERROR/CRITICAL
        'format': '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        'file_path': 'logs/app.log'
    }

    @classmethod
    def create_dirs(cls):
        cls.LOG_DIR.mkdir(exist_ok=True)
        cls.MODELS_DIR.mkdir(exist_ok=True)

