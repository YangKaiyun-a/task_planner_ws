#       
# DatabaseManager 
# 用于统一管理 PostgreSQL 连接、查询与任务流程相关的数据库操作。
#


import json
import psycopg2
from datetime import datetime
import uuid
import re


class DatabaseManager:
    def __init__(self, database="postgres", user="postgres", password="12345678", host="127.0.0.1", port="5432"):
        self.conn = psycopg2.connect(
            database=database,
            user=user,
            password=password,
            host=host,
            port=port
        )
        self.cursor = self.conn.cursor()
        self.action_to_node = {
            "move": "chassis_move",
            "grab": "arm_grab",
            "release": "arm_release",
            "wait": "wait"
        }

    # ✅ 规范化位置名
    def normalize_target_position(self, raw_name):
        """
        将自然语言位置描述（如“窗户上”、“桌子旁”）规范化为数据库 position 表中的 position_name。
        若匹配失败，则返回 "error"。
        """
        if not raw_name:
            return "error"

        self.cursor.execute("SELECT position_name FROM position;")
        positions = [row[0] for row in self.cursor.fetchall() if row[0]]

        for pos in positions:
            if pos in raw_name:
                return pos

        return "error"

    # ✅ 加载节点模板
    def get_node_params(self, node_name):
        """从 workflow_node 表中加载节点模板"""
        self.cursor.execute("SELECT params FROM workflow_node WHERE node_name = %s", (node_name,))
        result = self.cursor.fetchone()

        if not result:
            print(f"⚠️ 数据库中未找到节点: {node_name}")
            return None

        params_json = result[0]
        return params_json if isinstance(params_json, dict) else json.loads(params_json)

    # ✅ 核心函数：构建流程 JSON
    def build_workflow_from_keywords(self, keywords):
        """
        将 GPT 输出的关键词任务流转为结构化 JSON。
        keywords 示例：
        [
          {"action": "move", "target": "窗户上"},
          {"action": "grab", "target": "毛巾"},
          {"action": "move", "target": "客厅旁"},
          {"action": "release", "target": "沙发上"}
        ]
        """
        conn = self.conn
        cursor = self.cursor

        config = []

        for step in keywords:
            action = step["action"]
            node_name = self.action_to_node.get(action)

            if not node_name:
                print(f"⚠️ 未识别的动作类型: {action}")
                continue

            # 查询节点模板
            cursor.execute("SELECT params FROM workflow_node WHERE node_name = %s", (node_name,))
            result = cursor.fetchone()

            if not result:
                print(f"⚠️ 数据库中未找到节点: {node_name}")
                continue

            params_json = result[0]
            base_params = params_json if isinstance(params_json, dict) else json.loads(params_json)

            # ✅ 针对不同类型节点的参数规范化
            if node_name == "chassis_move":
                original_value = step.get("target", "")
                normalized_value = self.normalize_target_position(original_value)
                base_params["target_position"] = normalized_value

                if normalized_value == "error":
                    print(f"[警告] {node_name}: 无法规范化目标 '{original_value}'，已标记为 error。")
                else:
                    print(f"[规范化] {node_name}: {original_value} → {normalized_value}")

            elif node_name == "wait":
                # ✅ 提取等待时间中的数字（例如 "10s" → 10）
                raw_value = step.get("target", "")
                match = re.search(r"(\d+)\s*(s|秒|seconds|min|分钟)?", raw_value)
                if match:
                    wait_seconds = int(match.group())
                    base_params["wait_seconds"] = wait_seconds
                    print(f"[规范化] wait: {raw_value} → {wait_seconds} 秒")
                else:
                    base_params["wait_seconds"] = 0  # 默认等待 0 秒
                    print(f"[警告] wait: 无法识别等待时间 '{raw_value}'，默认 0 秒。")

            config.append(base_params)

        return {"config": config}

    # ✅ 保存流程结果到数据库
    def save_workflow(self, workflow_json):
        """
          - create_time: 当前时间
          - create_by: 固定为 1
          - status: 固定为 0
          - robot_id: 固定为 1
        """
        try:
            create_time = datetime.now()
            random_suffix = uuid.uuid4().hex[:5].upper()  # 取UUID前5位，例如 'ABF93'
            workflow_name = f"语音创建-{random_suffix}"

            insert_sql = """
                INSERT INTO workflow_config (
                    workflow_name,
                    create_time,
                    create_by,
                    status,
                    robot_id,
                    workflow_config
                )
                VALUES (%s, %s, %s, %s, %s, %s);
            """

            self.cursor.execute(
                insert_sql,
                (
                    workflow_name,                      # 外部提供
                    create_time,                        # 当前时间
                    1,                                   # create_by 固定为 1
                    0,                                   # status 固定为 0
                    1,                                   # robot_id 固定为 1
                    json.dumps(workflow_json, ensure_ascii=False)  # JSON 转字符串
                )
            )
            self.conn.commit()
            print(f"✅ 工作流程《{workflow_name}》已保存至数据库。")

        except Exception as e:
            print(f"❌ 保存工作流程失败: {e}")
            self.conn.rollback()

    def close(self):
        self.conn.close()
