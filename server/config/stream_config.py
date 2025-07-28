STREAM_CONFIG = {
    'tcp_retry_attempts': 10,
    'tcp_timeout': 30,  # Augmenté à 30 secondes
    'frame_buffer_size': 4,  # Augmenté pour plus de stabilité
    'target_fps': 15,  # Reduced from 30 for better performance
    'quality_preset': 'ultrafast',  # FFmpeg preset for faster encoding
    'max_queue_size': 4,
    'jpeg_quality': 60,  # Reduced from 80 for faster transmission
    'keepalive_interval': 5,
    'reconnect_delay': 2
}

TCP_CONFIG = {
    'host': '192.168.100.220',
    'port': 8080,
    'reconnect_delay': 1.0
}
