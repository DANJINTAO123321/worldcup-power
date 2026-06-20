// 2026世界杯数据备份
const WORLD_CUP_DATA = {
  // 今晚4场预测
  predictions: [
    {
      time: "6/21 01:00",
      team1: { name: "荷兰", flag: "🇳🇱", power: 89 },
      team2: { name: "瑞典", flag: "🇸🇪", power: 83 },
      scores: ["2-0", "1-0", "1-1"],
      advice: "荷兰不能再次丢分，防守稳健小胜过关"
    },
    {
      time: "6/21 04:00", 
      team1: { name: "德国", flag: "🇩🇪", power: 92 },
      team2: { name: "科特迪瓦", flag: "🇨🇮", power: 78 },
      scores: ["2-1", "3-1", "1-0"],
      advice: "德国进攻最强，但科特迪瓦会进球（搏双方进球）"
    },
    {
      time: "6/21 08:00",
      team1: { name: "厄瓜多尔", flag: "🇪🇨", power: 82 },
      team2: { name: "库拉索", flag: "🇨🇼", power: 65 },
      scores: ["2-0", "3-0", "4-0"],
      advice: "厄瓜多尔实力碾压，必胜之战"
    },
    {
      time: "6/21 12:00",
      team1: { name: "突尼斯", flag: "🇹🇳", power: 74 },
      team2: { name: "日本", flag: "🇯🇵", power: 84 },
      scores: ["0-2", "0-3", "1-3"],
      advice: "日本状态稳定，突尼斯军心大乱"
    }
  ],

  // 48队战力榜 (三家AI平均值)
  powerRanking: [
    { rank: 1, name: "阿根廷", flag: "🇦🇷", power: 96, note: "FIFA 5 · 卫冕冠军" },
    { rank: 2, name: "法国", flag: "🇫🇷", power: 96, note: "FIFA 2 · 姆巴佩巅峰" },
    { rank: 3, name: "英格兰", flag: "🏴󠁧󠁢󠁥󠁮󠁧󠁿", power: 93, note: "FIFA 4 · 青春风暴" },
    { rank: 4, name: "巴西", flag: "🇧🇷", power: 92, note: "FIFA 3 · 5星豪门" },
    { rank: 5, name: "西班牙", flag: "🇪🇸", power: 92, note: "FIFA 1 · 欧洲冠军" },
    { rank: 6, name: "德国", flag: "🇩🇪", power: 90, note: "FIFA 16 · 进攻最强" },
    { rank: 7, name: "葡萄牙", flag: "🇵🇹", power: 89, note: "FIFA 7 · C罗最后一届" },
    { rank: 8, name: "荷兰", flag: "🇳🇱", power: 87, note: "FIFA 8 · 范戴克领衔" },
    { rank: 9, name: "乌拉圭", flag: "🇺🇾", power: 86, note: "FIFA 13 · 南美劲旅" },
    { rank: 10, name: "摩洛哥", flag: "🇲🇦", power: 85, note: "FIFA 10 · 2022四强" },
    { rank: 11, name: "比利时", flag: "🇧🇪", power: 84, note: "FIFA 9 · 黄金一代" },
    { rank: 12, name: "哥伦比亚", flag: "🇨🇴", power: 84, note: "FIFA 17 · 南美黑马" },
    { rank: 13, name: "克罗地亚", flag: "🇭🇷", power: 84, note: "FIFA 11 · 上届四强" },
    { rank: 14, name: "瑞士", flag: "🇨🇭", power: 81, note: "FIFA 15 · 虐菜稳定" },
    { rank: 15, name: "墨西哥", flag: "🇲🇽", power: 80, note: "FIFA 12 · 东道主" },
    { rank: 16, name: "日本", flag: "🇯🇵", power: 79, note: "FIFA 18 · 亚洲最强" },
    { rank: 17, name: "美国", flag: "🇺🇸", power: 79, note: "FIFA 14 · 东道主" },
    { rank: 18, name: "厄瓜多尔", flag: "🇪🇨", power: 78, note: "FIFA 31 · 高原主场" },
    { rank: 19, name: "韩国", flag: "🇰🇷", power: 78, note: "FIFA 19 · 孙兴慜" },
    { rank: 20, name: "塞内加尔", flag: "🇸🇳", power: 77, note: "FIFA 16 · 非洲冠军" },
    { rank: 21, name: "奥地利", flag: "🇦🇹", power: 76, note: "FIFA 23 · 高位压迫" },
    { rank: 22, name: "阿尔及利亚", flag: "🇩🇿", power: 75, note: "FIFA 45 · 非洲劲旅" },
    { rank: 23, name: "瑞典", flag: "🇸🇪", power: 74, note: "FIFA 26 · 伊萨克" },
    { rank: 24, name: "挪威", flag: "🇳🇴", power: 74, note: "FIFA 24 · 哈兰德" },
    { rank: 25, name: "科特迪瓦", flag: "🇨🇮", power: 74, note: "FIFA 43 · 非洲杯冠军" },
    { rank: 26, name: "土耳其", flag: "🇹🇷", power: 73, note: "FIFA 46 · 状态起伏" },
    { rank: 27, name: "澳大利亚", flag: "🇦🇺", power: 73, note: "FIFA 22 · 身体对抗" },
    { rank: 28, name: "加纳", flag: "🇬🇭", power: 73, note: "FIFA 60 · 库杜斯" },
    { rank: 29, name: "埃及", flag: "🇪🇬", power: 72, note: "FIFA 39 · 萨拉赫" },
    { rank: 30, name: "波兰", flag: "🇵🇱", power: 72, note: "FIFA 21 · 莱万" },
    { rank: 31, name: "捷克", flag: "🇨🇿", power: 69, note: "FIFA 28 · 欧洲中游" },
    { rank: 32, name: "沙特阿拉伯", flag: "🇸🇦", power: 66, note: "FIFA 56 · 亚洲劲旅" },
    { rank: 33, name: "突尼斯", flag: "🇹🇳", power: 66, note: "FIFA 41 · 换帅混乱" },
    { rank: 34, name: "加拿大", flag: "🇨🇦", power: 67, note: "FIFA 25 · 阿方索" },
    { rank: 35, name: "波黑", flag: "🇧🇦", power: 67, note: "FIFA 50 · 哲科" },
    { rank: 36, name: "巴拉圭", flag: "🇵🇾", power: 67, note: "FIFA 58 · 美洲劲旅" },
    { rank: 37, name: "伊朗", flag: "🇮🇷", power: 64, note: "FIFA 21 · 亚洲强队" },
    { rank: 38, name: "巴拿马", flag: "🇵🇦", power: 63, note: "FIFA 95 · 中北美" },
    { rank: 39, name: "卡塔尔", flag: "🇶🇦", power: 62, note: "FIFA 57 · 东道主" },
    { rank: 40, name: "苏格兰", flag: "🏴󠁧󠁢󠁳󠁣󠁴󠁿", power: 60, note: "FIFA 42 · 欧洲中游" },
    { rank: 41, name: "乌兹别克斯坦", flag: "🇺🇿", power: 59, note: "FIFA 61 · 首次正赛" },
    { rank: 42, name: "海地", flag: "🇭🇹", power: 58, note: "FIFA 87 · 陪跑" },
    { rank: 43, name: "伊拉克", flag: "🇮🇶", power: 58, note: "FIFA 63 · 亚洲" },
    { rank: 44, name: "刚果(金)", flag: "🇨🇩", power: 58, note: "FIFA 62 · 非洲" },
    { rank: 45, name: "南非", flag: "🇿🇦", power: 56, note: "FIFA 57 · 非洲" },
    { rank: 46, name: "新西兰", flag: "🇳🇿", power: 56, note: "FIFA 26 · 大洋洲" },
    { rank: 47, name: "库拉索", flag: "🇨🇼", power: 56, note: "FIFA 141 · 业余防线" },
    { rank: 48, name: "佛得角", flag: "🇨🇻", power: 53, note: "FIFA 88 · 陪跑" }
  ],

  // 分组赛况
  groups: {
    A: { teams: ["墨西哥", "韩国", "南非", "捷克"], results: ["1-0", "0-0"], points: [3, 3, 1, 0] },
    B: { teams: ["瑞士", "加拿大", "波黑", "卡塔尔"], results: ["1-0", "0-1"], points: [3, 3, 0, 0] },
    C: { teams: ["巴西", "摩洛哥", "苏格兰", "海地"], results: ["3-0", "0-1"], points: [3, 3, 0, 0] },
    D: { teams: ["美国", "墨西哥", "土耳其", "巴拉圭"], results: ["1-0", "0-1"], points: [3, 3, 0, 0] },
    E: { teams: ["德国", "科特迪瓦", "厄瓜多尔", "库拉索"], results: ["7-1", "0-1"], points: [3, 3, 0, 0] },
    F: { teams: ["瑞典", "荷兰", "日本", "突尼斯"], results: ["5-1", "2-2"], points: [3, 1, 1, 0] }
  }
};
