import os
from dotenv import load_dotenv
import requests

load_dotenv()

class BailianTool:
    def __init__(self):
        self.api_key = os.getenv("DASHSCOPE_API_KEY")
        self.base_url = "https://dashscope.aliyuncs.com/api/v1/services/aigc/text-generation/generation"
        self.model = "qwen-turbo"

    # 标准chat方法，供app调用
    def chat(self, prompt: str) -> str:
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        data = {
            "model": self.model,
            "input": {"messages": [{"role": "user", "content": prompt}]},
            "parameters": {"result_format": "text"}
        }
        try:
            resp = requests.post(self.base_url, headers=headers, json=data)
            res_json = resp.json()
            if res_json.get("output") and res_json["output"].get("text"):
                return res_json["output"]["text"]
            else:
                return f"大模型调用失败：{res_json}"
        except Exception as e:
            return f"网络/接口异常：{str(e)}"

# 实例导出，给app.py导入
bailian_tool = BailianTool()