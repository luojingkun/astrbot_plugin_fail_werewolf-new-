挂科版狼人杀 - AstrBot插件


📚 项目简介

《挂科版狼人杀》是一款基于"AstrBot" (https://github.com/Soulter/AstrBot)框架开发的创意狼人杀游戏插件，将传统的狼人杀游戏与大学校园生活相结合，带来全新的游戏体验。

✨ 核心特色

🎭 校园主题角色 - 将传统角色替换为教务处、任课老师、奖学金等校园元素

📚 教育场景设定 - 以挂科、重修、奖学金等大学生活为主题

🤖 智能游戏管理 - 自动化的游戏流程和裁判系统

🎮 多角色策略 - 支持多种特殊角色，游戏策略丰富多样

📱 简单易用 - 通过简单的聊天命令即可开始游戏

🚀 快速开始

环境要求

- Python 3.8+
- AstrBot 框架
- OneBot协议适配器（如go-cqhttp、NoneBot等）

安装步骤

1. 克隆或下载插件
git clone https://github.com/LingshuoMoe/astrbot_plugin_fail_werewolf.git
2. 放置插件文件将 
"astrbot_plugin_fail_werewolf.py" 文件复制到AstrBot的插件目录：
AstrBot/
├── plugins/
│   └── astrbot_plugin_fail_werewolf.py
└── ...
3. 配置插件在AstrBot的配置文件中添加以下配置：
{
  "astrbot_plugin_fail_werewolf": {
    "enabled": true,
    "min_players": 6,
    "max_players": 12,
    "night_timeout": 120,
    "day_timeout": 180,
    "vote_timeout": 60,
    "enable_private_chat": true,
    "show_role_death": true,
    "allow_revote": false,
    "roles": {
      "bad_student": 2,
      "academic_affairs": 1,
      "teacher": 1,
「奖学金」:1，
「助教」:1，
“交换_学生”:0，
      "repeater": 0,
      "academic_warning": 0,
      "librarian": 0,
      "student_union": 0,
      "cheater": 0
    }
  }
}
4. 重启AstrBot重启AstrBot以加载插件。

🎮 游戏命令

游戏管理命令

命令 说明 权限

"挂科狼人杀" 或 
"failwerewolf" 开始报名 所有人

"开始游戏" 或 
"start" 开始游戏 主持人

"取消游戏" 取消当前游戏 主持人

"游戏状态" 查看游戏当前状态 所有人

"游戏规则" 查看游戏详细规则 所有人

游戏内命令

命令 说明 使用时机

"/发言 内容" 在白天发言讨论 白天阶段

"/投票 玩家名" 投票淘汰玩家 投票阶段

"/行动 目标" 执行夜晚行动 夜晚阶段

"/带走 玩家名" 助教技能：带走一人 被淘汰时

🎭 角色系统

阵营介绍

🎓 学生阵营（好人阵营）

目标：找出并淘汰所有挂科生

1. 普通学生 🎓
   - 无特殊能力，凭借观察力找出挂科生
   - 胜利条件：淘汰所有挂科生
2. 教务处 🏛️
   - 每晚可以查验一名玩家身份
   - 类似传统狼人杀的预言家
3. 任课老师 👨‍🏫
   - 拥有两瓶药水：
      - 平时成绩（救药）：救活被挂科的学生
      - 挂科警告（毒药）：让学生挂科出局
   - 同一晚不能使用两种药水
4. 奖学金 🏅
   - 每晚可以保护一名学生不被挂科
   - 不能连续两晚保护同一人
5. 助教 👨‍🎓
   - 被淘汰时可以带走一名学生
   - 类似传统狼人杀的猎人

🔴 挂科阵营（狼人阵营）

目标：淘汰所有学生阵营玩家

1. 挂科生 🔴
   - 每晚集体讨论，选择一名学生挂科
   - 类似传统狼人杀的狼人
2. 学业预警 ⚠️
   - 每晚可以额外查验一名玩家的具体身份
   - 白天可以自爆带走一名玩家
   - 类似白狼王
3. 作弊者 🎭
   - 白天不会被教务处查验为挂科生
   - 只有晚上被查验才会暴露
   - 挂科生不知道作弊者的身份

🌍 第三方阵营

1. 交换生 🌍
   - 游戏开始时选择两名玩家成为情侣
   - 情侣中一人出局，另一人殉情
   - 胜利条件：与情侣一起活到最后
   - 类似丘比特
2. 重修生 🔄
   - 游戏开始时从两张身份牌中选择一张
   - 如果牌中有挂科生，必须选择挂科生
   - 胜利条件根据所选身份决定
   - 类似盗贼

🛡️ 特殊角色

1. 图书馆管理员 📚
   - 每晚可以禁言一名玩家
   - 被禁言的玩家第二天不能发言
   - 不能连续两晚禁言同一人
2. 学生会主席 👑
   - 有两颗学分（两条命）
   - 第一次被挂科不会出局
   - 被毒药挂科时直接出局

📖 游戏流程

1. 报名阶段

- 主持人发送 
"挂科狼人杀" 开始报名
- 玩家发送 
"报名" 或 
"join" 加入游戏
- 达到最少人数后，主持人可以开始游戏

2. 角色分配

- 系统根据人数自动分配角色
- 玩家通过私聊接收自己的身份信息
- 挂科生会被告知队友信息

3. 游戏循环

夜晚阶段 🌙

1. 作弊者行动（可选）
2. 挂科生、学业预警行动
3. 教务处查验身份
4. 奖学金保护玩家
5. 图书馆管理员禁言
6. 任课老师使用药水

白天阶段 ☀️

1. 公布夜晚结果
2. 玩家依次发言讨论
3. 投票淘汰玩家
4. 处理被淘汰玩家的技能

4. 游戏结束

游戏在以下情况结束：

- ✅ 学生阵营淘汰所有挂科生
- ✅ 挂科生阵营淘汰所有学生
- ✅ 交换生与情侣一起存活到最后

⚙️ 详细配置

基本配置

{
  "astrbot_plugin_fail_werewolf": {
    "enabled": true,                    // 是否启用插件
    "min_players": 6,                   // 最少玩家数
    "max_players": 12,                  // 最多玩家数
    "night_timeout": 120,               // 夜晚行动时间（秒）
    "day_timeout": 180,                 // 白天讨论时间（秒）
    "vote_timeout": 60,                 // 投票时间（秒）
    "enable_private_chat": true,        // 是否启用私聊
    "show_role_death": true,            // 出局时是否显示身份
    "allow_revote": false               // 是否允许重新投票
  }
}

角色配置

"roles": {
  "bad_student": 2,           // 挂科生数量
  "academic_affairs": 1,      // 教务处数量
  "teacher": 1,               // 任课老师数量
  "scholarship": 1,           // 奖学金数量
  "teaching_assistant": 1,    // 助教数量
  "exchange_student": 0,      // 交换生数量（可选）
  "repeater": 0,              // 重修生数量（可选）
  "academic_warning": 0,      // 学业预警数量（可选）
  "librarian": 0,             // 图书馆管理员数量（可选）
  "student_union": 0,         // 学生会主席数量（可选）
  "cheater": 0                // 作弊者数量（可选）
}

🎯 游戏策略与技巧

对学生阵营的建议

1. 教务处应尽早验证可疑玩家身份
2. 任课老师要谨慎使用毒药，避免误伤队友
3. 奖学金保护关键角色，如教务处或任课老师
4. 普通学生要仔细分析发言，找出逻辑漏洞

对挂科阵营的建议

1. 假装自己是普通学生，避免暴露
2. 优先淘汰关键角色（教务处、任课老师）
3. 利用学业预警的自爆技能打乱好人节奏
4. 作弊者要隐藏好身份，关键时刻发挥作用

第三方阵营策略

1. 交换生要选择合适的玩家建立情侣关系
2. 重修生根据局势选择有利的身份

🔧 开发与贡献

项目结构

astrbot_plugin_fail_werewolf/
├── astrbot_plugin_fail_werewolf.py  # 主插件文件
是 - config.json #Profile Beispiele
├── README.md                        # 说明文档
├── CHANGELOG.md                     # 更新日志
├── LICENSE                          # 开源协议
└── assets/                          # 资源文件
    ├── images/                      # 图片资源
    └── docs/                        # 详细文档

开发环境设置

1. 克隆仓库：
git clone https://github.com/LingshuoMoe/astrbot_plugin_fail_werewolf.git
cd astrbot_plugin_fail_werewolf
2. 安装依赖：
pip install -r requirements.txt
3. 运行测试：
python -m pytest tests/

贡献指南

欢迎提交Issue和Pull Request！在提交前请确保：

1. 代码符合PEP 8规范
2. 添加适当的测试用例
3. 更新相关文档
4. 通过所有现有测试

📊 性能与限制

性能特点

- ✅ 支持最多20名玩家同时游戏
- ✅ 低内存占用，高效的消息处理
- ✅ 异步处理，不阻塞主线程
- ✅ 完善的错误处理和日志记录

当前限制

- ⚠️ 仅支持OneBot协议
- ⚠️ 需要AstrBot框架支持
- ⚠️ 暂不支持Web界面
- ⚠️ 部分高级功能仍在开发中

📞 支持与反馈

问题报告

如果遇到问题，请通过以下方式反馈：

1. 查看 "常见问题解答" (FAQ.md)
2. 搜索 "已有Issue" (issues)
3.创建"新问题”(问题/新)

联系方式

- 作者: 灵烁 (Lingshuo)
-GitHub:“@ lingshuo moe”(https://GitHub . com/lingshuo moe)
-邮箱:lingshuo070330@163.com
- QQ群: 暂时还没有 (#) (以后可能有)

📄 许可证

本项目采用 MIT 许可证 - 查看 "LICENSE" (LICENSE) 文件了解详情。

🙏 致谢

感谢以下项目对本插件的支持：

-"阿斯特博特“(https://github . com/soul ter/astr bot)优秀的机器人框架
-“OneBot”(https://OneBot . dev/)统一的聊天机器人协议
- 所有参与测试和改进的社区成员

🎉 特别说明

本插件以娱乐为目的，结合了校园生活和传统狼人杀元素。游戏中的"挂科"概念仅为游戏设定，请勿与现实学习生活混淆。祝大家游戏愉快，学业顺利！

<差异排列=“居中”>

如果喜欢这个项目,请点个⭐明星报支持一下！

"[图片]https://api.star-history.com/svg?repos = lingshuo moe/astrbot _ plugin _ fail _ Wolfe & type = Date "(https://star-history . com/# lingshuo moe/astrbot _ plugin _ fail _ Wolfe & Date)

</DIV>astrbot_plugin_fail狼人-
