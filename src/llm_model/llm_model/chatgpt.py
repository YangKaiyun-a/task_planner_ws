import rclpy
from rclpy.node import Node
from std_msgs.msg import String


import json
import os
import time
import openai
from llm_config.user_config import UserConfig
from llm_model.database_manager import DatabaseManager



db_manager = DatabaseManager()

config = UserConfig()
openai.api_key = config.openai_api_key
openai.base_url = config.base_url



class ChatGPTNode(Node):
    def __init__(self):
        super().__init__("ChatGPT_node")

        self.initialization_publisher = self.create_publisher(
            String, "/llm_initialization_state", 0
        )

        self.llm_input_subscriber = self.create_subscription(
            String, "/llm_input_text", self.llm_callback, 0
        )

        self.get_logger().info("ChatGPT 节点已启动，等待输入...")


    def llm_callback(self, msg):
        self.get_logger().info(f"Input message received: {msg.data}")

        steps  = self.generate_chatgpt_response(msg.data)

        if not steps:
            return

        # 将语义任务转为结构化任务流
        final_json = db_manager.build_workflow_from_keywords(steps)
        self.get_logger().info("最终任务流程 JSON:")
        self.get_logger().info(json.dumps(final_json, indent=2, ensure_ascii=False))

        # 存储到数据库中
        db_manager.save_workflow(final_json)



    def generate_chatgpt_response(self, messages_input):
        response = openai.chat.completions.create(
            model=config.openai_model,
            messages=[
                {
                    "role": "system",
                    "content": config.system_prompt
                },
                {
                    "role": "user", 
                    "content": messages_input
                }
            ],
            temperature=config.openai_temperature
        )

        # 获取模型回复文本
        output_text = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(output_text)
            pretty_output = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pretty_output = output_text

        self.get_logger().info(f"� 原始 GPT 输出（格式化）:\n{pretty_output}\n")

        # 尝试提取 JSON
        try:
            # 有时 GPT 会带代码块 ```json ... ```
            if "```" in output_text:
                output_text = output_text.split("```")[1]
                output_text = output_text.replace("json", "").strip()
            steps = json.loads(output_text)
            return steps
        except Exception as e:
            self.get_logger().error(f"❌ 无法解析 GPT 输出为 JSON: {e}")
            return None
        


    


def main(args=None):
    rclpy.init(args=args)
    chatgpt = ChatGPTNode()
    rclpy.spin(chatgpt)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
