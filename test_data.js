// test_data.js —— 动态数据（模拟后端返回）
// step09：把这些应由后端返回的数据从 zhiyuan_app.html 中分离出来，
//         结构与未来后端接口返回保持一致。
// 注意：开发完后端功能后，本文件将不再需要（前端改为请求后端获取）。
// 对应字段见 PRD「数据结构约定」：autoModeTag / score / s06~s09

var planData = {
  autoModeTag: "AI智能推荐",
  score: 600,
  s06: {
    title: "冲刺院校",
    level: "red",
    items: [
      { sch: "武汉大学", major: "计算机科学与技术", risk: "冲", note: "近年录取线贴近你的分数，可冲刺" },
      { sch: "华中科技大学", major: "人工智能", risk: "冲", note: "热门专业，竞争激烈" }
    ]
  },
  s07: {
    title: "稳妥院校",
    level: "org",
    items: [
      { sch: "南京理工大学", major: "软件工程", risk: "稳", note: "分数匹配度高，录取概率较大" },
      { sch: "苏州大学", major: "数据科学", risk: "稳", note: "地域与专业均符合偏好" }
    ]
  },
  s08: {
    title: "保底院校",
    level: "grn",
    items: [
      { sch: "杭州电子科技大学", major: "计算机", risk: "保", note: "保底首选，往年分数略低于你" },
      { sch: "浙江工业大学", major: "电子信息", risk: "保", note: "稳妥保底，建议填报" }
    ]
  },
  s09: {
    title: "备选建议",
    level: "blu",
    items: [
      { sch: "宁波大学", major: "通信工程", risk: "备", note: "地域优先策略下的补充选择" }
    ]
  }
};
