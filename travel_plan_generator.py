"""
智能旅游规划助手 - 真正有用的版本
功能：收集用户输入 → 拼接Skill模板 → 调用大模型 → 解析JSON → 格式化输出
"""

import json
import os
import re
from datetime import datetime
from typing import Dict, List, Optional
import requests


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
        """
        构建标准化的Skill提示词
        
        这个模板定义了"规范"，让大模型知道必须输出什么
        """
        
        # 构建目的地描述
        if len(destinations) == 1:
            dest_desc = destinations[0]
            route_type = "单目的地"
        else:
            dest_desc = " → ".join(destinations)
            route_type = "多目的地中转"
        
        # 构建预算描述
        budget_desc = f"预算约¥{budget}" if budget else "预算未指定"
        
        # 构建日期描述
        date_desc = f"出发日期：{start_date}" if start_date else "日期未指定（假设近期）"
        
        # 构建偏好描述
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

## 你必须提供以下信息（JSON格式）

```json
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
      "temp_min": 最低温度,
      "temp_max": 最高温度,
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
          "price": 价格,
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
          "price_per_night": 每晚价格,
          "rating": 评分,
          "reason": "推荐理由"
        }}
      ]
    }}
  ],
  "itinerary": [
    {{
      "day": 第几天,
      "date": "日期",
      "city": "所在城市",
      "activities": [
        {{
          "time": "上午/下午/晚上",
          "name": "活动/景点名称",
          "type": "景点/美食/交通",
          "score": 评分1-10,
          "price": 价格,
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
          "price": 人均价格,
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
```

## 要求

1. **天气必须准确**：根据季节和目的地给出合理温度范围
2. **交通必须实用**：提供真实存在的车次/航班，价格符合市场行情
3. **酒店必须具体**：给出真实存在的酒店名称，不要编造
4. **行程必须合理**：每天2-3个主要景点，考虑交通时间
5. **预算必须详细**：各项费用明确，总计符合用户预算
6. **中途游玩必须支持**：如果是多目的地，每个城市都要有独立行程

## 输出格式

请直接输出JSON，不要有任何其他文字。确保JSON格式正确，可以被解析。
"""
        return prompt


class LLMClient:
    """大模型调用客户端"""
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        # 支持多种模型接口
        self.base_url = os.getenv("LLM_BASE_URL", "https://api.openai.com/v1")
        self.model = os.getenv("LLM_MODEL", "gpt-4")
    
    def call(self, prompt: str, temperature: float = 0.7) -> str:
        """
        调用大模型
        
        支持：OpenAI、Azure、Claude、文心一言、通义千问等
        通过环境变量配置
        """
        try:
            headers = {
                "Authorization": f"Bearer {self.api_key}",
                "Content-Type": "application/json"
            }
            
            data = {
                "model": self.model,
                "messages": [
                    {"role": "system", "content": "你是一个专业的旅游规划助手。"},
                    {"role": "user", "content": prompt}
                ],
                "temperature": temperature,
                "max_tokens": 4000
            }
            
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=data,
                timeout=120
            )
            
            result = response.json()
            return result["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"调用大模型失败: {e}")
            print("请检查：")
            print("1. 是否设置了 OPENAI_API_KEY 环境变量")
            print("2. 是否正确配置了 LLM_BASE_URL 和 LLM_MODEL")
            raise


class TravelPlanParser:
    """旅游计划解析器"""
    
    @staticmethod
    def parse_json(text: str) -> Dict:
        """从模型返回的文本中提取JSON"""
        # 尝试直接解析
        try:
            return json.loads(text)
        except json.JSONDecodeError:
            pass
        
        # 尝试从代码块中提取
        json_match = re.search(r'```(?:json)?\s*(\{.*?\})\s*```', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        # 尝试从文本中提取最像JSON的部分
        json_match = re.search(r'(\{.*\})', text, re.DOTALL)
        if json_match:
            try:
                return json.loads(json_match.group(1))
            except json.JSONDecodeError:
                pass
        
        raise ValueError("无法从模型返回中提取有效的JSON")


class TravelPlanFormatter:
    """旅游计划格式化器"""
    
    @staticmethod
    def format_console(plan: Dict) -> str:
        """格式化为控制台输出"""
        lines = []
        
        # 标题
        lines.append("=" * 70)
        lines.append(f"  {plan.get('title', '旅游规划方案')}")
        lines.append("=" * 70)
        
        # 行程概览
        lines.append("\n【行程概览】")
        overview = plan.get("overview", {})
        for key, value in overview.items():
            lines.append(f"  {key}：{value}")
        
        # 天气
        if plan.get("weather"):
            lines.append("\n【天气与穿衣建议】")
            for w in plan["weather"]:
                lines.append(f"\n  {w.get('city', '')} - {w.get('date', '')}")
                lines.append(f"    温度：{w.get('temp_min')}°C ~ {w.get('temp_max')}°C")
                lines.append(f"    天气：{w.get('condition', '')}")
                lines.append(f"    穿衣：{w.get('clothing_advice', '')}")
        
        # 交通
        if plan.get("transport"):
            lines.append("\n【交通方案】")
            for t in plan["transport"]:
                lines.append(f"\n  {t.get('segment', '')}：{t.get('from', '')} → {t.get('to', '')}")
                for opt in t.get("options", []):
                    lines.append(f"    {opt.get('type', '')} {opt.get('name', '')}")
                    lines.append(f"      时间：{opt.get('depart', '')} - {opt.get('arrive', '')}")
                    lines.append(f"      时长：{opt.get('duration', '')}")
                    lines.append(f"      价格：¥{opt.get('price', 0)}")
                    lines.append(f"      推荐：{opt.get('recommendation', '')}")
        
        # 酒店
        if plan.get("hotels"):
            lines.append("\n【酒店推荐】")
            for h in plan["hotels"]:
                lines.append(f"\n  {h.get('city', '')}")
                for r in h.get("recommendations", []):
                    lines.append(f"    {r.get('name', '')}")
                    lines.append(f"      位置：{r.get('location', '')}")
                    lines.append(f"      价格：¥{r.get('price_per_night', 0)}/晚")
                    lines.append(f"      评分：{r.get('rating', 0)}分")
                    lines.append(f"      理由：{r.get('reason', '')}")
        
        # 行程
        if plan.get("itinerary"):
            lines.append("\n【详细行程】")
            for day in plan["itinerary"]:
                lines.append(f"\n  第{day.get('day', '')}天 - {day.get('date', '')} - {day.get('city', '')}")
                for act in day.get("activities", []):
                    lines.append(f"    {act.get('time', '')}：{act.get('name', '')}")
                    if act.get("score"):
                        lines.append(f"      评分：{act['score']}分")
                    if act.get("price"):
                        lines.append(f"      价格：¥{act['price']}")
                    if act.get("duration"):
                        lines.append(f"      时长：{act['duration']}")
                    if act.get("tips"):
                        lines.append(f"      提示：{act['tips']}")
        
        # 美食
        if plan.get("food"):
            lines.append("\n【美食推荐】")
            for f in plan["food"]:
                lines.append(f"\n  {f.get('city', '')}")
                for r in f.get("recommendations", []):
                    lines.append(f"    {r.get('name', '')} - {r.get('shop', '')}")
                    lines.append(f"      人均：¥{r.get('price', 0)}")
                    lines.append(f"      理由：{r.get('reason', '')}")
        
        # 预算
        if plan.get("budget_detail"):
            lines.append("\n【费用预算】")
            budget = plan["budget_detail"]
            for key, value in budget.items():
                if key != "total":
                    lines.append(f"  {key}：¥{value}")
            lines.append(f"  总计：¥{budget.get('total', 0)}")
        
        # 提示
        if plan.get("tips"):
            lines.append("\n【温馨提示】")
            for tip in plan["tips"]:
                lines.append(f"  • {tip}")
        
        # 信息来源
        if plan.get("sources"):
            lines.append("\n【信息来源】")
            for source in plan["sources"]:
                lines.append(f"  • {source}")
        
        lines.append("\n" + "=" * 70)
        
        return "\n".join(lines)
    
    @staticmethod
    def save_to_file(plan: Dict, output_dir: str = None) -> str:
        """保存为文件"""
        if output_dir is None:
            output_dir = os.path.join(os.path.expanduser("~"), "Desktop", "旅游方案")
        
        os.makedirs(output_dir, exist_ok=True)
        
        # 生成文件名
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        from_city = plan.get("overview", {}).get("出发地", "未知")
        dest = plan.get("overview", {}).get("目的地", "未知").replace(" → ", "_")
        filename = f"旅游方案_{from_city}_{dest}_{timestamp}.json"
        filepath = os.path.join(output_dir, filename)
        
        # 保存JSON
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(plan, f, ensure_ascii=False, indent=2)
        
        # 同时保存文本版本
        txt_filename = filename.replace(".json", ".txt")
        txt_filepath = os.path.join(output_dir, txt_filename)
        with open(txt_filepath, "w", encoding="utf-8") as f:
            f.write(TravelPlanFormatter.format_console(plan))
        
        return filepath, txt_filepath


class TravelAgent:
    """旅游规划智能体 - 主入口"""
    
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
    ) -> Dict:
        """
        生成旅游方案
        
        完整流程：
        1. 收集用户输入
        2. 拼接Skill模板
        3. 调用大模型
        4. 解析JSON
        5. 格式化输出
        6. 保存文件
        """
        
        print("=" * 70)
        print("智能旅游规划助手")
        print("=" * 70)
        
        # 1. 构建提示词
        print("\n[1/4] 正在构建规划模板...")
        prompt = self.template.build_prompt(
            from_city=from_city,
            destinations=destinations,
            days=days,
            budget=budget,
            people=people,
            preferences=preferences,
            start_date=start_date,
        )
        
        # 2. 调用大模型
        print("[2/4] 正在调用AI生成方案（约需30-60秒）...")
        try:
            response = self.llm.call(prompt)
        except Exception as e:
            print(f"\n错误：{e}")
            return None
        
        # 3. 解析结果
        print("[3/4] 正在解析方案...")
        try:
            plan = self.parser.parse_json(response)
        except ValueError as e:
            print(f"\n解析失败：{e}")
            print("\n模型原始返回：")
            print(response[:500] + "..." if len(response) > 500 else response)
            return None
        
        # 4. 格式化输出
        print("[4/4] 正在格式化输出...")
        formatted = self.formatter.format_console(plan)
        print(formatted)
        
        # 5. 保存文件
        if save:
            json_path, txt_path = self.formatter.save_to_file(plan)
            print(f"\n方案已保存：")
            print(f"  JSON：{json_path}")
            print(f"  文本：{txt_path}")
        
        return plan


def interactive_mode():
    """交互模式"""
    print("\n" + "=" * 70)
    print("欢迎使用智能旅游规划助手！")
    print("=" * 70)
    
    # 收集用户输入
    print("\n请回答以下问题（直接回车使用默认值）：\n")
    
    from_city = input("1. 出发城市？ ").strip()
    if not from_city:
        print("出发城市不能为空！")
        return
    
    dest_input = input("2. 目的地（多个用逗号分隔，如：北京,大连）？ ").strip()
    destinations = [d.strip() for d in dest_input.split(",") if d.strip()]
    if not destinations:
        print("目的地不能为空！")
        return
    
    days_str = input("3. 出行天数？ ").strip()
    try:
        days = int(days_str) if days_str else 3
    except ValueError:
        days = 3
    
    budget_str = input("4. 预算（元，可选）？ ").strip()
    budget = float(budget_str) if budget_str else None
    
    people_str = input("5. 出行人数（默认1人）？ ").strip()
    try:
        people = int(people_str) if people_str else 1
    except ValueError:
        people = 1
    
    preferences = input("6. 特定需求（如：环球影城、看海、美食等，可选）？ ").strip() or None
    
    start_date = input("7. 出发日期（如：2025-06-01，可选）？ ").strip() or None
    
    # 确认
    print("\n" + "-" * 70)
    print("请确认行程信息：")
    print(f"  出发地：{from_city}")
    print(f"  目的地：{' → '.join(destinations)}")
    print(f"  天数：{days}天")
    print(f"  人数：{people}人")
    print(f"  预算：¥{budget}" if budget else "  预算：未指定")
    print(f"  需求：{preferences}" if preferences else "  需求：无")
    print(f"  日期：{start_date}" if start_date else "  日期：近期")
    print("-" * 70)
    
    confirm = input("\n确认生成方案？(y/n) ").strip().lower()
    if confirm != "y":
        print("已取消")
        return
    
    # 生成方案
    agent = TravelAgent()
    agent.plan(
        from_city=from_city,
        destinations=destinations,
        days=days,
        budget=budget,
        people=people,
        preferences=preferences,
        start_date=start_date,
    )


def quick_mode(
    from_city: str,
    destinations: str,
    days: int,
    budget: Optional[float] = None,
    people: int = 1,
    preferences: Optional[str] = None,
):
    """快速模式 - 命令行参数"""
    dest_list = [d.strip() for d in destinations.split(",")]
    
    agent = TravelAgent()
    agent.plan(
        from_city=from_city,
        destinations=dest_list,
        days=days,
        budget=budget,
        people=people,
        preferences=preferences,
    )


if __name__ == "__main__":
    import sys
    
    # 检查是否有命令行参数
    if len(sys.argv) > 1:
        # 快速模式
        # 用法：python travel_agent.py 天津 北京,大连 3 6000 1 环球影城
        from_city = sys.argv[1]
        destinations = sys.argv[2]
        days = int(sys.argv[3])
        budget = float(sys.argv[4]) if len(sys.argv) > 4 else None
        people = int(sys.argv[5]) if len(sys.argv) > 5 else 1
        preferences = sys.argv[6] if len(sys.argv) > 6 else None
        
        quick_mode(from_city, destinations, days, budget, people, preferences)
    else:
        # 交互模式
        interactive_mode()
