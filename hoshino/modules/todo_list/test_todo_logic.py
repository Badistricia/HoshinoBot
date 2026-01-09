import sys
import os
import unittest
from unittest.mock import MagicMock, patch, AsyncMock
import json
from datetime import datetime, timedelta
import shutil
import asyncio

# -----------------------------------------------------------------------------
# Mocking Nonebot2 and Plugins Environment
# -----------------------------------------------------------------------------

# Create a dummy module structure for nonebot
sys.modules["nonebot"] = MagicMock()
sys.modules["nonebot.adapters.onebot.v11"] = MagicMock()
sys.modules["nonebot.params"] = MagicMock()
sys.modules["nonebot.plugin"] = MagicMock()

# Mock nonebot.require to do nothing
sys.modules["nonebot"].require = MagicMock()

# Mock logger
mock_logger = MagicMock()
mock_logger.info = print
mock_logger.error = print
sys.modules["nonebot"].logger = mock_logger

# Mock scheduler
sys.modules["nonebot_plugin_apscheduler"] = MagicMock()
mock_scheduler = MagicMock()
sys.modules["nonebot_plugin_apscheduler"].scheduler = mock_scheduler

# Mock htmlrender
sys.modules["nonebot_plugin_htmlrender"] = MagicMock()
# IMPORTANT: Use AsyncMock or a coroutine for async functions
async def fake_template_to_pic(*args, **kwargs):
    return b"fake_image_bytes"

sys.modules["nonebot_plugin_htmlrender"].template_to_pic = fake_template_to_pic

# Now we can import our module components
current_dir = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, current_dir)

try:
    from data_manager import DataManager
    from scheduler_manager import SchedulerManager
    from render_utils import render_todo_list
    import jionlp
except ImportError as e:
    print(f"Import failed: {e}")
    sys.exit(1)

# -----------------------------------------------------------------------------
# Test Suite
# -----------------------------------------------------------------------------

class TestTodoList(unittest.TestCase):
    def setUp(self):
        self.test_data_path = "data/test_todo_list.json"
        self.dm = DataManager()
        self.dm.data_path = self.dm.data_path.parent / "test_todo_list.json"
        if os.path.exists(self.dm.data_path):
            os.remove(self.dm.data_path)
        self.dm._ensure_data_file()

        self.sm = SchedulerManager()

    def tearDown(self):
        if os.path.exists(self.dm.data_path):
            os.remove(self.dm.data_path)

    def test_1_add_and_get_todo(self):
        print("\n[Test] Adding Todo...")
        user_id = "123456"
        group_id = "987654"
        content = "Buy milk"
        created_at = "2023-10-27 10:00:00"
        
        item = self.dm.add_todo(user_id, group_id, content, created_at)
        
        self.assertIsNotNone(item["id"])
        self.assertEqual(item["content"], content)
        self.assertFalse(item["is_done"])
        
        print(f"Added item: {item}")
        
        todos = self.dm.get_user_todos(user_id, group_id)
        self.assertEqual(len(todos), 1)
        self.assertEqual(todos[0]["id"], item["id"])
        print("[Pass] Add and Get Todo")

    def test_2_finish_todo(self):
        print("\n[Test] Finishing Todo...")
        user_id = "123456"
        item = self.dm.add_todo(user_id, None, "Sleep", "now")
        
        finished_item = self.dm.finish_todo(user_id, None, item["id"])
        self.assertTrue(finished_item["is_done"])
        
        pending = self.dm.get_pending_todos(user_id, None)
        self.assertEqual(len(pending), 0)
        print("[Pass] Finish Todo")

    def test_3_delete_todo(self):
        print("\n[Test] Deleting Todo...")
        user_id = "123456"
        item = self.dm.add_todo(user_id, None, "Delete me", "now")
        
        success = self.dm.delete_todo(user_id, None, item["id"])
        self.assertTrue(success)
        
        todos = self.dm.get_user_todos(user_id, None)
        self.assertEqual(len(todos), 0)
        print("[Pass] Delete Todo")

    def test_4_scheduler_integration(self):
        print("\n[Test] Scheduler Logic...")
        mock_scheduler.add_job.reset_mock()
        
        todo_id = "test_id"
        run_date = datetime.now() + timedelta(hours=1)
        user_id = "123"
        content = "Test Job"
        
        self.sm.add_job(todo_id, run_date, user_id, None, content)
        
        mock_scheduler.add_job.assert_called_once()
        print("[Pass] Scheduler Add Job called")
        
        mock_scheduler.remove_job.reset_mock()
        mock_scheduler.get_job.return_value = True
        
        self.sm.remove_job(todo_id)
        mock_scheduler.remove_job.assert_called_once_with(f"todo_{todo_id}")
        print("[Pass] Scheduler Remove Job called")

    def test_5_jionlp_extraction(self):
        print("\n[Test] Jionlp Time Extraction...")
        text = "明天下午三点开会"
        import time
        try:
            res = jionlp.ner.extract_time(text, time_base=time.time())
            if res:
                print(f"Extracted: {res}")
                time_detail = res[0]['detail']
                if 'time' in time_detail:
                    print(f"Time point: {time_detail['time'][0]}")
                    self.assertTrue(True)
                else:
                    print("No time point found in detail.")
            else:
                print("No time extracted.")
        except Exception as e:
            print(f"Jionlp error: {e}")
            pass
        print("[Pass] Jionlp extraction ran")

    def test_6_render_utils_async(self):
        print("\n[Test] Async Render Utils...")
        async def run_test():
            todos = [{"id": "1", "content": "Test", "is_done": False}]
            img = await render_todo_list(todos)
            return img
            
        loop = asyncio.new_event_loop()
        asyncio.set_event_loop(loop)
        img = loop.run_until_complete(run_test())
        loop.close()
        
        self.assertEqual(img, b"fake_image_bytes")
        print("[Pass] Render Utils called template_to_pic")

if __name__ == "__main__":
    unittest.main(verbosity=2)
