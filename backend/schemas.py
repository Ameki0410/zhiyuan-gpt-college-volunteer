# schemas.py —— 请求/响应数据模型（与前端结构一致）
# step11：先定义 /api/data 的入参与出参；第15步补充注册/登录模型

from typing import List, Optional
from pydantic import BaseModel, Field


class PlanRequest(BaseModel):
    """前端点击「生成方案」后上报的考生信息 + 偏好"""
    province: str = Field(..., description="省份")
    subjects: List[str] = Field(..., description="选科组合，1-3 门")
    score: int = Field(..., ge=0, le=750, description="高考成绩")
    school: str = Field("不限", description="目标院校偏好")
    region: str = Field("不限", description="地域偏好")
    major: str = Field("不限", description="专业偏好")
    strategy: str = Field("分数优先", description="优先策略")
    gradPlan: str = Field("直接就业", description="毕业规划")
    career: str = Field("不限", description="职业倾向")
    tuition: str = Field("不限", description="学费倾向")


class PlanItem(BaseModel):
    sch: str
    major: str
    risk: str
    note: str


class PlanGroup(BaseModel):
    title: str
    level: str
    items: List[PlanItem]


class PlanResponse(BaseModel):
    """后端下发的方案数据（与 test_data.js 结构一致）"""
    autoModeTag: str
    score: int
    s06: PlanGroup
    s07: PlanGroup
    s08: PlanGroup
    s09: PlanGroup
