import uuid
from datetime import datetime
from typing import Dict, Any, List

class TaskManager:
    def __init__(self):
        self.tasks: Dict[str, Dict[str, Any]] = {}

    def create_task(self, task_type: str, metadata: Dict[str, Any] = None) -> str:
        task_id = str(uuid.uuid4())
        self.tasks[task_id] = {
            "id": task_id,
            "type": task_type,
            "status": "pending",
            "progress": 0,
            "created_at": datetime.now().isoformat(),
            "updated_at": datetime.now().isoformat(),
            "metadata": metadata or {},
            "result": None,
            "error": None
        }
        return task_id

    def update_task(self, task_id: str, status: str = None, progress: int = None, result: Any = None, error: str = None):
        if task_id in self.tasks:
            task = self.tasks[task_id]
            if status:
                task["status"] = status
            if progress is not None:
                task["progress"] = progress
            if result is not None:
                task["result"] = result
            if error:
                task["error"] = error
            task["updated_at"] = datetime.now().isoformat()

    def get_task(self, task_id: str) -> Dict[str, Any]:
        return self.tasks.get(task_id)

    def list_tasks(self) -> List[Dict[str, Any]]:
        return list(self.tasks.values())

# Global task manager instance
task_manager = TaskManager()
