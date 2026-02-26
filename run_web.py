"""
启动 Web 应用的便捷脚本
"""

import sys
import os
from pathlib import Path

# 添加项目根目录到路径
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root / 'src'))
sys.path.insert(0, str(project_root / 'src' / 'web'))

# 导入并运行 Flask 应用
from web.app import app, config, logger

if __name__ == '__main__':
    host = config.get('app.host', '127.0.0.1')
    port = config.get('app.port', 5000)
    debug = config.get('app.debug', False)

    logger.info("=" * 50)
    logger.info("播客分析工具 Web 应用")
    logger.info("=" * 50)
    logger.info(f"访问地址: http://{host}:{port}")
    logger.info("按 Ctrl+C 停止服务器")
    logger.info("=" * 50)

    app.run(host=host, port=port, debug=debug)
