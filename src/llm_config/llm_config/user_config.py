import os

gpt_4_1106_preview = "gpt-4-1106-preview"       # 0.072/千tokens，0.216/千tokens
gpt_4o = "gpt-4o"                               # 0.018/千tokens，0.072/千tokens，速度快，准确
ZHIZENGZENG_KEY = "sk-zk271d37b11c7d1a6584fa6a8eb4de3d9fd68e8b89bf2655";
ZHIZENGZENG_URL = "https://api.zhizengzeng.com/v1/"



deepseek_r1_250528 = "deepseek-r1-250528"       # 0.004/千tokens，0.016/千tokens，速度稍慢，准确
deepseek_v3_2_exp = "deepseek-v3.2-exp"         # 0.002/千tokens，0.003/千tokens，速度快，准确
HUAWEI_KEY = "51xbnNKKk4sBf6uEpFKMNr-zPC1FeJlPxIjpSyLjQkKaJeQrh4TnFkG48SvlGvzwfQAx3IDB-ptJjscA5LRCYA"
HUAWEI_URL = "https://api.modelarts-maas.com/v1"


API_SECRET_KEY = HUAWEI_KEY
BASE_URL = HUAWEI_URL
OPENAI_MODEL = deepseek_v3_2_exp
SYSTEM_PROMPT = (
    "你是一个机器人任务规划助手。"
    "请将用户的自然语言任务拆分为多个步骤，"
    "每个步骤用一个简洁的 JSON 对象表示，包含关键词 action 和 target，"
    "只输出 JSON 数组，不要其他解释。"
    "例如：“去厨房拿毛巾放到沙发上” 应输出："
    "[{\"action\": \"move\", \"target\": \"厨房\"}, {\"action\": \"grab\", \"target\": \"毛巾\"}, {\"action\": \"move\", \"target\": \"沙发\"}, {\"action\": \"release\", \"target\": \"沙发\"}]，"
    "例如：“移动到桌子旁，然后等待 10s，再移动到窗户” 应输出："
    "[{\"action\": \"move\", \"target\": \"桌子\"}, {\"action\": \"wait\", \"target\": \"10\"}, {\"action\": \"move\", \"target\": \"窗户\"}]"
)





class UserConfig:
    def __init__(self):
        self.openai_api_key = os.getenv("OPENAI_API_KEY", API_SECRET_KEY)
        self.base_url = os.getenv("BASE_URL", BASE_URL)
        self.openai_model = OPENAI_MODEL
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
        self.system_prompt = SYSTEM_PROMPT
        self.chat_history = [{"role": "system", "content": self.system_prompt}]


        

