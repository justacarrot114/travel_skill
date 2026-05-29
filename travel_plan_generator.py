"""
智能旅游规划助手 - 真正有用的版本
功能：收集用户输入 → 拼接Skill模板 → 调用大模型 → 解析JSON → 格式化输出

使用前请设置环境变量：
  set OPENAI_API_KEY=你的密钥
  set LLM_BASE_URL=https://api.deepseek.com/v1    （可选，默认OpenAI）
  set LLM_MODEL=deepseek-chat                      （可选，默认gpt-4）

推荐使用 DeepSeek（便宜好用）：
  1. 注册 https://platform.deepseek.com
  2. 创建API Key
  3. set OPENAI_API_KEY=sk-你的密钥
  4. set LLM_BASE_URL=https://api.deepseek.com/v1
  5. set LLM_MODEL=deepseek-chat
"""

import json
import os
import re
import sys
from datetime import datetime
from typing import Dict, List, Optional

import requests


# ============================================================
# 配置区 - 在这里填写你的API信息，或者用环境变量
# ============================================================

# 方式1：直接填在这里（简单但不安全，不要把代码分享给别人）
# API_KEY = "sk-你的密钥"
# BASE_URL = "https://api.deepseek.com/v1"
# MODEL = "deepseek-chat"

# 方式2：用环境变量（推荐）
API_KEY = os.getenv("OPENAI_API_KEY", "")
BASE_URL = os.getenv("LLM_BASE_URL", "https://api.deepseek.com/v1")
MODEL = os.getenv("LLM_MODEL", "deepseek-chat")


# ============================================================
# Skill模板 - 定义大模型必须输出什么
# ============================================================

class TravelSkillTemplate:
    """旅游规划Skill模板"""

    @staticmethod
    def build_prompt(
        from_city: str,
        destinations: List[str],
        days: int,
        budget: Optional[float] = None,
        people: int = 1,
        preferences: Optional[str] = None,
        start_date: Optional[str] = None,
    ) -> str:
        if len(destinations) == 1:
            dest_desc = destinations[0]
            route_type = "单目的地"
        else:
            dest_desc = " → ".join(destinations)
            route_type = "多目的地中转"

        budget_desc = f"预算约{budget}元" if budget else "预算未指定"
        date_desc = f"出发日期：{start_date}" if start_date else "日期未指定（假设近期）"
        pref_desc = f"特定需求：{preferences}" if preferences else "无特定需求"

        prompt = f"""你是一个专业的旅游规划助手。请为以下行程生成完整的旅游方案。

## 行程需求
- 出发地：{from_city}
- 目的地：{dest_desc}
- 行程类型：{route_type}
- 出行天数：{days}天
- 出行人数：{people}人
- {budget_desc}
- {date_desc}
- {pref_desc}

## 你必须提供以下信息（严格JSON格式）

{{
  "title": "行程标题",
  "overview": {{
    "出发地": "",
    "目的地": "",
    "行程路线": "",
    "总天数": "",
    "出行人数": "",
    "预算": "",
    "特定需求": ""
  }},
  "weather": [
    {{
      "city": "城市名",
      "date": "日期",
      "temp_min": 最低温度数字,
      "temp_max": 最高温度数字,
      "condition": "天气状况",
      "clothing_advice": "穿衣建议"
    }}
  ],
  "transport": [
    {{
      "segment": "第几段",
      "from": "出发城市",
      "to": "到达城市",
      "options": [
        {{
          "type": "高铁/飞机/大巴",
          "name": "车次/航班号",
          "depart": "出发时间",
          "arrive": "到达时间",
          "duration": "时长",
          "price": 价格数字,
          "recommendation": "推荐理由"
        }}
      ]
    }}
  ],
  "hotels": [
    {{
      "city": "城市",
      "recommendations": [
        {{
          "name": "酒店名称",
          "location": "位置",
          "price_per_night": 每晚价格数字,
          "rating": 评分数字,
          "reason": "推荐理由"
        }}
      ]
    }}
  ],
  "itinerary": [
    {{
      "day": 第几天数字,
      "date": "日期",
      "city": "所在城市",
      "activities": [
        {{
          "time": "上午/下午/晚上",
          "name": "活动/景点名称",
          "type": "景点/美食/交通",
          "score": 评分数字1到10,
          "price": 价格数字,
          "duration": "建议时长",
          "tips": "注意事项"
        }}
      ]
    }}
  ],
  "food": [
    {{
      "city": "城市",
      "recommendations": [
        {{
          "name": "美食名称",
          "shop": "推荐店铺",
          "price": 人均价格数字,
          "reason": "推荐理由"
        }}
      ]
    }}
  ],
  "budget_detail": {{
    "交通": 0,
    "住宿": 0,
    "门票": 0,
    "餐饮": 0,
    "其他": 0,
    "total": 0
  }},
  "tips": [
    "提示1",
    "提示2"
  ],
  "sources": [
    "信息来源1",
    "信息来源2"
  ]
}}

## 要求

1. 天气必须准确：根据季节和目的地给出合理温度范围
2. 交通必须实用：提供真实存在的车次/航班，价格符合市场行情
3. 酒店必须具体：给出真实存在的酒店名称，不要编造
4. 行程必须合理：每天2-3个主要景点，考虑交通时间
5. 预算必须详细：各项费用明确，总计符合用户预算
6. 中途游玩必须支持：如果是多目的地，每个城市都要有独立行程

## 输出格式

请直接输出JSON，不要有任何其他文字，不要用markdown代码块包裹。确保JSON格式正确。
"""
        return prompt


# ============================================================
# 大模型调用
# ============================================================

class LLMClient:
    """大模型调用客户端"""

    def __init__(self, api_key: str = None, base_url: str = None, model: str = None):
        self.api_key = api_key or API_KEY
        self.base_url = base_url or BASE_URL
        self.model = model or MODEL

    def call(self, prompt: str, temperature: float = 0.7) -> str:
        if not self.api_key:
            raise ValueError(
                "没有设置API Key！\n\n"
                "请选择以下方式之一：\n"
                "1. 在代码顶部 API_KEY = \"sk-你的密钥\"\n"
                "2. 在cmd中运行：set OPENAI_API_KEY=sk-你的密钥\n"
                "3. 在cmd中运行：set LLM_BASE_URL=https://api.deepseek.com/v1\n"
                "4. 在cmd中运行：set LLM_MODEL=deepseek-chat\n\n"
                "推荐使用DeepSeek（便宜好用）：\n"
                "  注册：https://platform.deepseek.com\n"
                "  新用户送500万token，够用很久"
            )

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }

        data = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": "你是一个专业的旅游规划助手，只输出JSON。"},
                {"role": "user", "content": prompt}
            ],
            "temperature": temperature,
            "max_tokens": 4000
        }

        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            response.raise_for_status()
            result = response.json()
            return result["choices"][0]["message"]["content"]
        except requests.exceptions.HTTPError as e:
            status = e.response.status_code
            if status == 401:
                raise ValueError("API Key无效，请检查你的密钥是否正确")
            elif status == 429:
                raise ValueError("请求过于频繁或余额不足，请稍后再试")
            elif status == 404:
                raise ValueError(
                    f"模型不存在或API地址错误\n"
                    f"当前配置：BASE_URL={self.base_url}，MODEL={self.model}\n"
                    f"请检查环境变量设置是否正确"
                )
            else:
                raise ValueError(f"API请求失败（HTTP {status}）：{e}")
        except requests.exceptions.ConnectionError:
            raise ValueError(
                f"无法连接到 {self.base_url}\n"
                f"请检查网络连接，或确认API地址是否正确"
            )


# ============================================================
# 解析器
# ============================================================

class TravelPlanParser:
    """旅游计划解析器"""

    @staticmethod
    def parse_json(text: str) -> Dict:
        # 去掉可能的markdown代码块标记
        text = text.strip()
        text = re.sub(r'^```(?:json)?\s*', '', text)
        text = re.sub(r'\s*```$', '', text)

        # 直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass

        # 从文本中提取JSON
        json_match = re.search(r'\{.*\}', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(0))
            except json.JSONDecodeError:
                pass

        raise ValueError("无法从模型返回中提取有效的JSON，请重试")


# ============================================================
# 格式化输出
# ============================================================

class TravelPlanFormatter:
    """旅游计划格式化器"""

    @staticmethod
    def format_console(plan: Dict) -> str:
        lines = []

        lines.append("=" * 70)
        lines.append(f"  {plan.get('title', '旅游规划方案')}")
        lines.append("=" * 70)

        # 行程概览
        lines.append("\n【行程概览】")
        for key, value in plan.get("overview", {}).items():
            lines.append(f"  {key}：{value}")

        # 天气
        for w in plan.get("weather", []):
            lines.append(f"\n【天气 - {w.get('city', '')}】")
            lines.append(f"  温度：{w.get('temp_min')}°C ~ {w.get('temp_max')}°C")
            lines.append(f"  天气：{w.get('condition', '')}")
            lines.append(f"  穿衣：{w.get('clothing_advice', '')}")

        # 交通
        lines.append("\n【交通方案】")
        for t in plan.get("transport", []):
            lines.append(f"\n  {t.get('segment', '')}：{t.get('from', '')} -> {t.get('to', '')}")
            for opt in t.get("options", []):
                lines.append(f"    {opt.get('type', '')} {opt.get('name', '')}")
                lines.append(f"      {opt.get('depart', '')} - {opt.get('arrive', '')}（{opt.get('duration', '')}）")
                lines.append(f"      价格：{opt.get('price', 0)}元  {opt.get('recommendation', '')}")

        # 酒店
        lines.append("\n【酒店推荐】")
        for h in plan.get("hotels", []):
            lines.append(f"\n  {h.get('city', '')}")
            for r in h.get("recommendations", []):
                lines.append(f"    {r.get('name', '')}（{r.get('rating', 0)}分）")
                lines.append(f"      位置：{r.get('location', '')}  价格：{r.get('price_per_night', 0)}元/晚")
                lines.append(f"      {r.get('reason', '')}")

        # 行程
        lines.append("\n【详细行程】")
        for day in plan.get("itinerary", []):
            lines.append(f"\n  第{day.get('day', '')}天 - {day.get('city', '')}")
            for act in day.get("activities", []):
                score_str = f"（{act.get('score', 0)}分" if act.get('score') else "（"
                price_str = f"，{act.get('price', 0)}元" if act.get('price') else ""
                tips_str = f"，{act.get('tips', '')}" if act.get('tips') else ""
                lines.append(f"    {act.get('time', '')}：{act.get('name', '')}{score_str}{price_str}{tips_str}）")

        # 美食
        lines.append("\n【美食推荐】")
        for f in plan.get("food", []):
            lines.append(f"\n  {f.get('city', '')}")
            for r in f.get("recommendations", []):
                lines.append(f"    {r.get('name', '')} - {r.get('shop', '')}（人均{r.get('price', 0)}元）")
                lines.append(f"      {r.get('reason', '')}")

        # 预算
        lines.append("\n【费用预算】")
        budget = plan.get("budget_detail", {})
        for key, value in budget.items():
            if key != "total":
                lines.append(f"  {key}：{value}元")
        lines.append(f"  总计：{budget.get('total', 0)}元")

        # 提示
        if plan.get("tips"):
            lines.append("\n【温馨提示】")
            for tip in plan["tips"]:
                lines.append(f"  - {tip}")

        # 来源
        if plan.get("sources"):
            lines.append("\n【信息来源】")
            for source in plan["sources"]:
                lines.append(f"  - {source}")

        lines.append("\n" + "=" * 70)
        return "\n".join(lines)

    @staticmethod
    def save_to_file(plan: Dict, output_dir: str = None):
        if output_dir is None:
            output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "旅游方案")

        os.makedirs(output_dir, exist_ok=True)

        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from_city = plan.get("overview", {}).get("出发地", "未知")
        dest = plan.get("overview", {}).get("目的地", "未知").replace(" -> ", "_").replace(" → ", "_")
        base_name = f"旅游方案_{from_city}_{dest}_{timestamp}"

        # JSON
        json_path = os.path.join(output_dir, base_name + ".json")
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)

        # 文本
        txt_path = os.path.join(output_dir, base_name + ".txt")
        with open(txt_path, "w", encoding="utf-8") as f:
            f.write(TravelPlanFormatter.format_console(plan))

        return json_path, txt_path


# ============================================================
# 主入口
# ============================================================

class TravelAgent:
    """旅游规划智能体"""

    def __init__(self):
        self.template = TravelSkillTemplate()
        self.llm = LLMClient()
        self.parser = TravelPlanParser()
        self.formatter = TravelPlanFormatter()

    def plan(
        self,
        from_city: str,
        destinations: List[str],
        days: int,
        budget: Optional[float] = None,
        people: int = 1,
        preferences: Optional[str] = None,
        start_date: Optional[str] = None,
        save: bool = True,
    ) -> Optional[Dict]:
        print("=" * 70)
        print("  智能旅游规划助手")
        print("=" * 70)

        print("\n[1/4] 构建规划模板...")
        prompt = self.template.build_prompt(
            from_city=from_city,
            destinations=destinations,
            days=days,
            budget=budget,
            people=people,
            preferences=preferences,
            start_date=start_date,
        )

        print("[2/4] 调用AI生成方案（约需30-60秒）...")
        try:
            response = self.llm.call(prompt)
        except ValueError as e:
            print(f"\n  错误：{e}")
            return None

        print("[3/4] 解析方案...")
        try:
            plan = self.parser.parse_json(response)
        except ValueError as e:
            print(f"\n  解析失败：{e}")
            print("\n  模型原始返回（前500字）：")
            print("  " + response[:500])
            return None

        print("[4/4] 格式化输出...\n")
        formatted = self.formatter.format_console(plan)
        print(formatted)

        if save:
            json_path, txt_path = self.formatter.save_to_file(plan)
            print(f"\n  方案已保存：")
            print(f"  JSON：{json_path}")
            print(f"  文本：{txt_path}")

        return plan


def interactive_mode():
    """交互模式"""
    print("\n" + "=" * 70)
    print("  欢迎使用智能旅游规划助手！")
    print("=" * 70)
    print("\n请回答以下问题（直接回车使用默认值）：\n")

    from_city = input("1. 出发城市？ ").strip()
    if not from_city:
        print("  出发城市不能为空！")
        return

    dest_input = input("2. 目的地（多个用逗号分隔，如：北京,大连）？ ").strip()
    destinations = [d.strip() for d in dest_input.split(",") if d.strip()]
    if not destinations:
        print("  目的地不能为空！")
        return

    days_str = input("3. 出行天数（默认3）？ ").strip()
    try:
        days = int(days_str) if days_str else 3
    except ValueError:
        days = 3

    budget_str = input("4. 预算/元（可选）？ ").strip()
    budget = float(budget_str) if budget_str else None

    people_str = input("5. 出行人数（默认1）？ ").strip()
    try:
        people = int(people_str) if people_str else 1
    except ValueError:
        people = 1

    preferences = input("6. 特定需求（如：环球影城、看海，可选）？ ").strip() or None
    start_date = input("7. 出发日期（如：2025-06-01，可选）？ ").strip() or None

    print("\n" + "-" * 70)
    print("  请确认：")
    print(f"  {from_city} -> {' -> '.join(destinations)}，{days}天，{people}人")
    if budget:
        print(f"  预算：{budget}元")
    if preferences:
        print(f"  需求：{preferences}")
    print("-" * 70)

    if input("\n  确认生成？(y/n) ").strip().lower() != "y":
        print("  已取消")
        return

    TravelAgent().plan(
        from_city=from_city,
        destinations=destinations,
        days=days,
        budget=budget,
        people=people,
        preferences=preferences,
        start_date=start_date,
    )


def quick_mode(from_city, destinations, days, budget=None, people=1, preferences=None):
    """快速模式"""
    dest_list = [d.strip() for d in destinations.split(",")]
    TravelAgent().plan(
        from_city=from_city,
        destinations=dest_list,
        days=days,
        budget=budget,
        people=people,
        preferences=preferences,
    )


# ============================================================
# 入口
# ============================================================

if __name__ == "__main__":
    try:
        if len(sys.argv) > 1:
            # 快速模式：python travel_agent.py 天津 北京,大连 3 6000 1 环球影城
            quick_mode(
                from_city=sys.argv[1],
                destinations=sys.argv[2],
                days=int(sys.argv[3]),
                budget=float(sys.argv[4]) if len(sys.argv) > 4 else None,
                people=int(sys.argv[5]) if len(sys.argv) > 5 else 1,
                preferences=sys.argv[6] if len(sys.argv) > 6 else None,
            )
        else:
            interactive_mode()
    except Exception as e:
        print(f"\n  出错了：{e}")
    finally:
        input("\n按回车键退出...")
