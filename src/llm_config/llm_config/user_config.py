import os

API_SECRET_KEY = "sk-zk271d37b11c7d1a6584fa6a8eb4de3d9fd68e8b89bf2655";
BASE_URL = "https://api.zhizengzeng.com/v1/"

system_prompt = (
    "你是一个机器人任务规划助手。"
    "请将用户的自然语言任务拆分为多个步骤，"
    "每个步骤用一个简洁的 JSON 对象表示，包含关键词 action 和 target"
    "只输出 JSON 数组，不要其他解释。"
    "例如：“去厨房拿毛巾放到沙发上” 应输出："
    "[{\"action\": \"move\", \"target\": \"厨房\"}, {\"action\": \"grab\", \"target\": \"毛巾\"}, {\"action\": \"move\", \"target\": \"沙发\"}, {\"action\": \"release\", \"target\": \"沙发\"}]，"
    "例如：“移动到桌子旁，然后等待 10s，再移动到窗户” 应输出："
    "[{\"action\": \"move\", \"target\": \"桌子\"}, {\"action\": \"wait\", \"target\": \"10\"}, {\"action\": \"move\", \"target\": \"窗户\"}]"
)

gpt_4_1106_preview = "gpt-4-1106-preview"
gpt_4o = "gpt-4o" 


class UserConfig:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", API_SECRET_KEY)
        self.base_url = os.getenv("BASE_URL", BASE_URL)
        self.openai_model = gpt_4o
        self.openai_organization = "Auromix"
        self.openai_temperature = 0.2
        self.openai_top_p = 1
        self.openai_n = 1
        self.openai_stream = False
        self.openai_stop = "NULL"
        self.openai_max_tokens = 4000
        self.openai_frequency_penalty = 0
        self.openai_presence_penalty = 0
        self.user_prompt = ""
        self.assistant_response = ""
        self.chat_history_path = os.path.expanduser("~")
        self.chat_history_max_length = 4000
        self.system_prompt = system_prompt
        self.chat_history = [{"role": "system", "content": self.system_prompt}]


        

