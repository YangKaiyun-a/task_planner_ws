from openai import OpenAI

base_url = "https://api.modelarts-maas.com/v1" 
api_key = "51xbnNKKk4sBf6uEpFKMNr-zPC1FeJlPxIjpSyLjQkKaJeQrh4TnFkG48SvlGvzwfQAx3IDB-ptJjscA5LRCYA"


client = OpenAI(api_key=api_key, base_url=base_url)


response = client.chat.completions.create(
    model = "deepseek-r1-250528", # model参数
    messages = [
        {"role": "system", "content": "You are a helpful assistant"},
        {"role": "user", "content": "你好"}
    ],
    temperature = 0.2
)

print(response.choices[0].message.content)
