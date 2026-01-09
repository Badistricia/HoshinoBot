import json
from pathlib import Path
from typing import List, Dict, Optional

# Define the data path. 
# Using absolute path relative to the bot's root directory which seems to be D:\Project\Pycharm\Git\HoshinoBot
DATA_PATH = Path("data/todo_list.json")

class DataManager:
    def __init__(self):
        self.data_path = DATA_PATH
        self._ensure_data_file()

    def _ensure_data_file(self):
        if not self.data_path.exists():
            self.data_path.parent.mkdir(parents=True, exist_ok=True)
            with open(self.data_path, "w", encoding="utf-8") as f:
                json.dump({}, f)

    def _load_data(self) -> Dict:
        try:
            with open(self.data_path, "r", encoding="utf-8") as f:
                return json.load(f)
        except (json.JSONDecodeError, FileNotFoundError):
            return {}

    def _save_data(self, data: Dict):
        with open(self.data_path, "w", encoding="utf-8") as f:
            json.dump(data, f, indent=2, ensure_ascii=False)

    def _get_key(self, user_id: str, group_id: Optional[str] = None) -> str:
        # Separate data by group and user as requested
        if group_id:
            return f"group_{group_id}_user_{user_id}"
        return f"user_{user_id}"

    def _get_next_id(self, todos: List[Dict]) -> str:
        """
        Get the next smallest available ID (1, 2, 3...)
        """
        existing_ids = set()
        for t in todos:
            # Only consider numeric IDs
            try:
                existing_ids.add(int(t['id']))
            except ValueError:
                pass
        
        next_id = 1
        while next_id in existing_ids:
            next_id += 1
            
        return str(next_id)

    def add_todo(self, user_id: str, group_id: Optional[str], content: str, created_at: str, due_date: Optional[str] = None) -> Dict:
        data = self._load_data()
        key = self._get_key(user_id, group_id)
        
        if key not in data:
            data[key] = []
        
        # Recycle ID
        todo_id = self._get_next_id(data[key])
        
        new_item = {
            "id": todo_id,
            "content": content,
            "created_at": created_at,
            "due_date": due_date,
            "is_done": False
        }
        
        data[key].append(new_item)
        # Sort by ID for tidiness
        try:
            data[key].sort(key=lambda x: int(x['id']) if x['id'].isdigit() else 9999)
        except:
            pass
            
        self._save_data(data)
        return new_item

    def get_user_todos(self, user_id: str, group_id: Optional[str]) -> List[Dict]:
        data = self._load_data()
        key = self._get_key(user_id, group_id)
        return data.get(key, [])

    def get_pending_todos(self, user_id: str, group_id: Optional[str]) -> List[Dict]:
        todos = self.get_user_todos(user_id, group_id)
        return [t for t in todos if not t["is_done"]]

    def finish_todo(self, user_id: str, group_id: Optional[str], todo_id: str) -> Optional[Dict]:
        data = self._load_data()
        key = self._get_key(user_id, group_id)
        
        if key in data:
            for item in data[key]:
                if item["id"] == str(todo_id):
                    item["is_done"] = True
                    self._save_data(data)
                    return item
        return None

    def delete_todo(self, user_id: str, group_id: Optional[str], todo_id: str) -> bool:
        data = self._load_data()
        key = self._get_key(user_id, group_id)
        
        if key in data:
            original_len = len(data[key])
            data[key] = [item for item in data[key] if item["id"] != str(todo_id)]
            if len(data[key]) < original_len:
                self._save_data(data)
                return True
        return False

    def clear_todos(self, user_id: str, group_id: Optional[str]):
        data = self._load_data()
        key = self._get_key(user_id, group_id)
        if key in data:
            del data[key]
            self._save_data(data)
    
    def get_all_todos(self) -> Dict:
        """Used for startup recovery"""
        return self._load_data()
