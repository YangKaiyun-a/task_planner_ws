import rclpy
from rclpy.node import Node
from std_msgs.msg import String


import json
import os
import subprocess
import tempfile
from openai import OpenAI
from llm_config.user_config import UserConfig
from llm_model.database_manager import DatabaseManager
from llm_model.audio_asr import XFYunASRClient
from rclpy.qos import QoSProfile, ReliabilityPolicy, DurabilityPolicy, HistoryPolicy


db_manager = DatabaseManager()
config = UserConfig()
client = OpenAI(api_key=config.openai_api_key, base_url=config.base_url)


class ChatGPTNode(Node):
    def __init__(self):
        super().__init__("ChatGPT_node")


        #====================== 通用配置 ======================#

        init_qos = QoSProfile(
            history=HistoryPolicy.KEEP_LAST,
            depth=1,
            reliability=ReliabilityPolicy.RELIABLE,
            durability=DurabilityPolicy.TRANSIENT_LOCAL
        )

        self.asr_client = XFYunASRClient(
            app_id=config.xfyun_app_id,
            api_key=config.xfyun_api_key,
            api_secret=config.xfyun_api_secret
        )




        #====================== Topic ======================#


        # 状态发布
        self.initialization_publisher = self.create_publisher(
            String, "/llm_initialization_state", init_qos
        )

        # 文本输入
        self.llm_input_subscriber = self.create_subscription(
            String, "/llm_input_text", self.llm_callback, 10
        )

        # 语音文件输入
        self.audio_file_subscriber = self.create_subscription(
            String, "/llm_input_audio_file", self.audio_file_callback, 10
        )

        # 实时语音输入
        self.audio_input_subscriber = self.create_subscription(
            String, "/llm_input_audio", self.audio_callback, 10
        )


        self.get_logger().info("ChatGPT 节点已启动，等待文本或语音输入...")
        init_msg = String()
        init_msg.data = "ready"
        self.initialization_publisher.publish(init_msg)


    def publish_state(self, state: str):
        msg = String()
        msg.data = state
        self.initialization_publisher.publish(msg)
        self.get_logger().info(f"状态切换: {state}")


    def process_input_text(self, input_text: str):
        if not input_text or not input_text.strip():
            self.get_logger().warning("输入文本为空")
            return

        steps = self.generate_chatgpt_response(input_text)
        if not steps:
            self.get_logger().error("未能生成 steps")
            return

        # 将语义任务转为结构化任务流
        final_json = db_manager.build_workflow_from_keywords(steps)
        self.get_logger().info("最终任务流程 JSON:")
        self.get_logger().info(json.dumps(final_json, indent=2, ensure_ascii=False))

        # 存储到数据库中
        db_manager.save_workflow(final_json)


    def generate_chatgpt_response(self, messages_input):
        response = client.chat.completions.create(
            model = config.openai_model,
            messages = [
                {
                    "role": "system",
                    "content": config.system_prompt
                },
                {
                    "role": "user", 
                    "content": messages_input
                }
            ],
            temperature = config.openai_temperature
        )

        # 获取模型回复文本
        output_text = response.choices[0].message.content.strip()
        try:
            parsed = json.loads(output_text)
            pretty_output = json.dumps(parsed, indent=2, ensure_ascii=False)
        except json.JSONDecodeError:
            pretty_output = output_text

        self.get_logger().info(f" 原始 GPT 输出（格式化）:\n{pretty_output}\n")

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
        
    
    def convert_audio_to_pcm(self, input_path: str) -> str | None:
        """
        将 m4a/wav/mp3 等音频转为 16k/mono/s16le 的 pcm
        """
        try:
            fd, output_path = tempfile.mkstemp(suffix=".pcm", prefix="llm_audio_")
            os.close(fd)

            cmd = [
                "ffmpeg",
                "-y",
                "-i", input_path,
                "-ac", "1",
                "-ar", "16000",
                "-f", "s16le",
                output_path
            ]

            result = subprocess.run(
                cmd,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True
            )

            if result.returncode != 0:
                self.get_logger().error(f"ffmpeg 转码失败: {result.stderr}")
                if os.path.exists(output_path):
                    os.remove(output_path)
                return None

            self.get_logger().info(f"音频已转为 PCM: {output_path}")
            return output_path

        except Exception as e:
            self.get_logger().error(f"音频转 PCM 异常: {e}")
            return None





    #====================== 回调函数 ======================#

    def llm_callback(self, msg):
        self.get_logger().info(f"Input message received: {msg.data}")
        self.process_input_text(msg.data)


    def audio_file_callback(self, msg):
        audio_file_path = msg.data.strip()
        self.get_logger().info(f"Input audio file received: {audio_file_path}")

        if not os.path.exists(audio_file_path):
            self.get_logger().error(f"音频文件不存在: {audio_file_path}")
            return

        pcm_file = None

        try:
            ext = os.path.splitext(audio_file_path)[1].lower()

            if ext == ".pcm":
                pcm_file = audio_file_path
            else:
                pcm_file = self.convert_audio_to_pcm(audio_file_path)

            if not pcm_file or not os.path.exists(pcm_file):
                self.get_logger().error("音频转 PCM 失败")
                self.publish_state("error")
                return

            text = self.asr_client.transcribe_pcm(pcm_file, timeout=30.0)
            if not text:
                err = self.asr_client.get_last_error()
                self.get_logger().error(f"语音转文本失败: {err}")
                self.publish_state("error")
                return

            self.get_logger().info(f"语音识别结果: {text}")

            self.publish_state("thinking")
            self.process_input_text(text)
            self.publish_state("ready")

        except Exception as e:
            self.get_logger().error(f"处理音频失败: {e}") 
            self.publish_state("error")
        finally:
            # 只删除临时生成的 pcm，不删除原始 pcm
            if pcm_file and pcm_file != audio_file_path and os.path.exists(pcm_file):
                try:
                    os.remove(pcm_file)
                except Exception:
                    pass

    def audio_callback(self, msg):
        pass

    


    



def main(args=None):
    rclpy.init(args=args)
    chatgpt = ChatGPTNode()
    rclpy.spin(chatgpt)
    rclpy.shutdown()


if __name__ == "__main__":
    main()
