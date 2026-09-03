# mock_plan.py —— 模拟方案数据（镜像前端 test_data.js 的 planData）
# step11：后端先把这份 mock 数据回给前端，让前端展示出来。
# step13 起改为真实调用大模型，本文件退为兜底数据。

# 注意：与 zhiyuan_app.html 原内联数据 / test_data.js 保持结构一致
MOCK_PLAN = {
    "autoModeTag": "AI智能推荐",
    "score": 600,
    "s06": {
        "title": "冲刺院校",
        "level": "red",
        "items": [
            {"sch": "武汉大学", "major": "计算机科学与技术", "risk": "冲", "note": "近年录取线贴近你的分数，可冲刺"},
            {"sch": "华中科技大学", "major": "人工智能", "risk": "冲", "note": "热门专业，竞争激烈"},
        ],
    },
    "s07": {
        "title": "稳妥院校",
        "level": "org",
        "items": [
            {"sch": "南京理工大学", "major": "软件工程", "risk": "稳", "note": "分数匹配度高，录取概率较大"},
            {"sch": "苏州大学", "major": "数据科学", "risk": "稳", "note": "地域与专业均符合偏好"},
        ],
    },
    "s08": {
        "title": "保底院校",
        "level": "grn",
        "items": [
            {"sch": "杭州电子科技大学", "major": "计算机", "risk": "保", "note": "保底首选，往年分数略低于你"},
            {"sch": "浙江工业大学", "major": "电子信息", "risk": "保", "note": "稳妥保底，建议填报"},
        ],
    },
    "s09": {
        "title": "备选建议",
        "level": "blu",
        "items": [
            {"sch": "宁波大学", "major": "通信工程", "risk": "备", "note": "地域优先策略下的补充选择"},
        ],
    },
}


def build_mock_plan(score: int) -> dict:
    """根据考生分数回显，返回 mock 方案（step11）"""
    plan = {
        "autoModeTag": MOCK_PLAN["autoModeTag"],
        "score": score,
        "s06": MOCK_PLAN["s06"],
        "s07": MOCK_PLAN["s07"],
        "s08": MOCK_PLAN["s08"],
        "s09": MOCK_PLAN["s09"],
    }
    return plan
