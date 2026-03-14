import threading
import logging

logger = logging.getLogger(__name__)

class SessionPool:
    """管理网络设备会话池"""
    
    def __init__(self, max_size=10):
        self.max_size = max_size
        self.sessions = {}
        self._lock = threading.Lock()

    def get(self, name):
        """获取指定设备的会话"""
        with self._lock:
            return self.sessions.get(name)

    def add(self, name, session):
        """添加会话到池中"""
        with self._lock:
            if len(self.sessions) >= self.max_size:
                logger.warning("Session pool full")
                return False
            self.sessions[name] = session
            return True

    def remove(self, name):
        """从池中移除会话"""
        with self._lock:
            if name in self.sessions:
                del self.sessions[name]
                return True
            return False

    def close_all(self):
        """关闭所有会话并清空池"""
        with self._lock:
            for name, session in self.sessions.items():
                try:
                    session.disconnect()
                except Exception as e:
                    logger.error(f"Error closing session for {name}: {e}")
            self.sessions.clear()
