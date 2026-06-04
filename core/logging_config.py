"""日志配置模块 — 按日期分割，保留30天"""
import os
import logging
from logging.handlers import TimedRotatingFileHandler


def setup_logging(level: int = logging.INFO) -> None:
    """配置全局日志：同时输出到控制台和文件

    - 文件按天分割，保留最近 30 天
    - 日志目录: logs/ (自动创建)
    - 格式: 时间 - 模块名 - 级别 - 消息
    """
    log_dir = os.path.join(os.path.dirname(os.path.dirname(__file__)), 'logs')
    os.makedirs(log_dir, exist_ok=True)

    fmt = logging.Formatter(
        '%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        datefmt='%Y-%m-%d %H:%M:%S'
    )

    # 控制台 Handler
    console = logging.StreamHandler()
    console.setLevel(level)
    console.setFormatter(fmt)

    # 文件 Handler — 每天午夜分割，保留 30 天
    file_handler = TimedRotatingFileHandler(
        filename=os.path.join(log_dir, 'trader.log'),
        when='midnight',
        interval=1,
        backupCount=30,
        encoding='utf-8'
    )
    file_handler.setLevel(level)
    file_handler.setFormatter(fmt)
    # 分割后的文件名格式: trader.log.2026-06-04
    file_handler.suffix = '%Y-%m-%d'

    # 应用到 root logger
    root = logging.getLogger()
    root.setLevel(level)
    # 移除已有的 handler（避免重复），再添加新的
    root.handlers.clear()
    root.addHandler(console)
    root.addHandler(file_handler)

    # 降级噪音模块：httpx 和 telegram 的每次 HTTP 请求日志会刷屏
    logging.getLogger('httpx').setLevel(logging.WARNING)
    logging.getLogger('telegram').setLevel(logging.WARNING)
