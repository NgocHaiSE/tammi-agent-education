import json
import os
from typing import List, Dict


class SymptomMemory:
    """Singleton class quản lý lịch sử hội thoại và lưu cache ra file JSON.
    
    Tự động reset cache khi session_id thay đổi.
    """

    _instance = None  # Singleton instance
    
    # Đường dẫn file cache này ở cùng cấp với script hiện tại 
    SYMPTOM_MEMORY_CACHE_DIR = os.path.join(
        os.path.dirname(__file__), "symptom_memory_cache.json" 
    )

    def __new__(cls, *args, **kwargs):
        """Đảm bảo chỉ tạo duy nhất một instance (Singleton)."""
        if cls._instance is None:
            cls._instance = super(SymptomMemory, cls).__new__(cls)
            cls._instance._initialized = False
        return cls._instance

    def __init__(self, session_id: str = None):
        """Khởi tạo SymptomMemory, load dữ liệu từ file cache nếu có.
        
        Args:
            session_id (str, optional): Session ID hiện tại. Nếu khác với session_id 
                                       đã lưu, cache sẽ được reset.
        """
        if self._initialized:
            # Nếu đã init, check session_id
            if session_id and session_id != self.session_id:
                # Session mới -> reset cache
                self._reset_for_new_session(session_id)
            return
            
        # First time initialization
        self.history: List[Dict[str, str]] = []
        self.session_id: str = session_id or "default"
        self.load_from_file()
        self._initialized = True
    
    def _reset_for_new_session(self, new_session_id: str):
        """Reset cache khi chuyển sang session mới.
        
        Args:
            new_session_id (str): Session ID mới.
        """
        self.history = []
        self.session_id = new_session_id
        self.save_to_file()

    def add_message(self, role: str, content: str):
        """Thêm một tin nhắn vào lịch sử hội thoại.

        Args:
            role (str): Vai trò của tin nhắn, chỉ nhận giá trị "human" hoặc "ai".
            content (str): Nội dung tin nhắn.

        Raises:
            ValueError: Nếu role không phải "human" hoặc "ai".
        """
        if role not in ["human", "ai"]:
            raise ValueError("role phải là 'human' hoặc 'ai'")
        self.history.append({"role": role, "content": content})

    def edit_message(self, index: int, new_content: str):
        """Sửa nội dung của một tin nhắn trong lịch sử.

        Args:
            index (int): Vị trí của tin nhắn trong lịch sử.
            new_content (str): Nội dung mới để thay thế.

        Raises:
            IndexError: Nếu index không hợp lệ.
        """
        if 0 <= index < len(self.history):
            self.history[index]["content"] = new_content
        else:
            raise IndexError("Index không tồn tại trong lịch sử chat")

    def delete_message(self, index: int):
        """Xoá một tin nhắn khỏi lịch sử.

        Args:
            index (int): Vị trí của tin nhắn cần xoá.

        Raises:
            IndexError: Nếu index không hợp lệ.
        """
        if 0 <= index < len(self.history):
            self.history.pop(index)
        else:
            raise IndexError("Index không tồn tại trong lịch sử chat")

    def clear_history(self):
        """Xoá toàn bộ lịch sử hội thoại và file cache."""
        self.history = []
        if os.path.exists(self.SYMPTOM_MEMORY_CACHE_DIR):
            os.remove(self.SYMPTOM_MEMORY_CACHE_DIR)

    def get_history(self) -> List[Dict[str, str]]:
        """Lấy toàn bộ lịch sử hội thoại hiện tại.

        Returns:
            List[Dict[str, str]]: Danh sách tin nhắn, mỗi tin nhắn có dạng:
                {
                    "role": "human" | "ai",
                    "content": "Nội dung tin nhắn"
                }
        """
        return self.history

    def save_to_file(self):
        """Lưu lịch sử hội thoại và session_id hiện tại ra file JSON."""
        data = {
            "session_id": self.session_id,
            "history": self.history
        }
        with open(self.SYMPTOM_MEMORY_CACHE_DIR, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)

    def load_from_file(self) -> List[Dict[str, str]]:
        """Tải lịch sử hội thoại và session_id từ file JSON nếu tồn tại.

        Nếu file không tồn tại hoặc session_id không khớp, history sẽ được reset.

        Returns:
            List[Dict[str, str]]: Danh sách tin nhắn đã load, mỗi tin nhắn có dạng:
                {
                    "role": "human" | "ai",
                    "content": "Nội dung tin nhắn"
                }
        """
        try:
            if os.path.exists(self.SYMPTOM_MEMORY_CACHE_DIR):
                with open(self.SYMPTOM_MEMORY_CACHE_DIR, "r", encoding="utf-8") as f:
                    content = f.read().strip()
                    if content:  # nếu file không rỗng
                        data = json.loads(content)
                        
                        # Kiểm tra format mới (có session_id)
                        if isinstance(data, dict) and "session_id" in data:
                            saved_session_id = data.get("session_id")
                            
                            # Nếu session_id khớp, load history
                            if saved_session_id == self.session_id:
                                self.history = data.get("history", [])
                            else:
                                # Session khác -> reset
                                self.history = []
                        # Backward compatibility: format cũ (chỉ có list history)
                        elif isinstance(data, list):
                            # Không có session_id trong file cũ -> reset để bắt đầu mới
                            self.history = []
                        else:
                            self.history = []
                    else:
                        self.history = []
            else:
                self.history = []
        except (FileNotFoundError, json.JSONDecodeError):
            self.history = []
        return self.history

    def get_parsed_history(self) -> str:
        """Lấy toàn bộ nội dung tin nhắn từ lịch sử (chỉ trường 'content').

        Returns:
            str: Chuỗi gồm tất cả nội dung tin nhắn, mỗi tin nhắn trên một dòng.
        """
        return "\n".join(msg["content"] for msg in self.history)

    def reset_cache_on_new_session(self):
        """Reset symptom cache khi bắt đầu session mới."""
        self.clear_history()
        self.save_to_file()