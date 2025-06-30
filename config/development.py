# 服务器地址和端口
SERVER_CONFIG = {
    'face_detection': {
        'host': '0.0.0.0',
        'port': 8002,
        'api_endpoint': '/detect_faces'
    },
    'gesture_detection': {
        'host': '0.0.0.0',
        'port': 8003,
        'websocket_endpoint': '/ws/gesture-detection'
    },
    'plate_detection': {
        'host': '0.0.0.0',
        'port': 8001,
        'api_endpoint': '/recognize_plate'
    }
}