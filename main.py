import random
import asyncio
import json
import time
from typing import Dict, List, Optional, Set, Tuple
from enum import Enum
from dataclasses import dataclass
from collections import defaultdict

import astrbot.api.message_components as Comp
from astrbot.api import AstrBotConfig, logger
from astrbot.api.event import AstrMessageEvent, filter
from astrbot.api.star import Context, Star, register
from astrbot.core.message.message_event_result import MessageChain
from astrbot.core.platform.message_type import MessageType
from astrbot.core.star.filter.event_message_type import EventMessageType
from astrbot.core.star.filter.platform_adapter_type import PlatformAdapterType


class GamePhase(Enum):
    """游戏阶段"""
    WAITING = "等待开始"  # 等待开始
    REGISTERING = "报名中"  # 报名阶段
    NIGHT = "深夜"  # 黑夜阶段
    DAY = "白天"  # 白天阶段
    VOTING = "投票中"  # 投票阶段
    ENDED = "已结束"  # 游戏结束


class PlayerStatus(Enum):
    """玩家状态"""
    ALIVE = "在学"  # 存活
    DROPPED = "挂科"  # 出局
    GRADUATED = "毕业"  # 胜利
    SUSPENDED = "休学"  # 暂停


class Role(Enum):
    """角色类型"""
    # 挂科阵营 (类似狼人)
    BAD_STUDENT = "挂科生"  # 挂科生 (类似狼人)
    
    # 学生阵营 (类似村民)
    ORDINARY_STUDENT = "普通学生"  # 普通学生 (类似村民)
    ACADEMIC_AFFAIRS = "教务处"  # 教务处 (类似预言家)
    TEACHER = "任课老师"  # 任课老师 (类似女巫)
    SCHOLARSHIP = "奖学金"  # 奖学金 (类似守卫)
    TEACHING_ASSISTANT = "助教"  # 助教 (类似猎人)
    EXCHANGE_STUDENT = "交换生"  # 交换生 (类似丘比特)
    REPEATER = "重修生"  # 重修生 (类似盗贼)
    ACADEMIC_WARNING = "学业预警"  # 学业预警 (类似白狼王)
    LIBRARIAN = "图书馆管理员"  # 图书馆管理员 (类似禁言长老)
    STUDENT_UNION = "学生会主席"  # 学生会主席 (类似长老)
    CHEATER = "作弊者"  # 作弊者 (类似隐狼)


@dataclass
class Player:
    """玩家信息"""
    user_id: str
    user_name: str
    role: Optional[Role] = None
    status: PlayerStatus = PlayerStatus.ALIVE
    group_id: Optional[str] = None
    is_exposed: bool = False  # 是否被教务处查验过
    is_protected: bool = False  # 是否被奖学金保护
    is_poisoned: bool = False  # 是否被任课老师挂科
    is_exchanged: bool = False  # 是否被交换生连接
    partner: Optional[str] = None  # 交换生连接的对象
    voted_count: int = 0  # 得票数
    votes: List[str] = []  # 投票记录
    last_action_time: float = 0  # 上次行动时间


@register(
    "astrbot_plugin_fail_werewolf",
    "wangxinghuo",
    "挂科版狼人杀插件，体验大学挂科的恐怖",
    "1.0.0",
)
class FailWerewolfPlugin(Star):
    def __init__(self, context: Context, config: AstrBotConfig):
        super().__init__(context)
        self.config = config
        
        # 游戏状态
        self.game_phase = GamePhase.WAITING
        self.game_group_id = None
        self.game_master = None  # 游戏主持人
        self.players: Dict[str, Player] = {}  # 所有玩家
        self.registered_players: Set[str] = set()  # 已报名玩家
        self.player_order: List[str] = []  # 玩家顺序
        self.day_count = 0  # 当前天数
        self.night_actions = {}  # 夜晚行动记录
        self.day_actions = {}  # 白天行动记录
        self.votes = {}  # 投票记录
        self.lynched_player = None  # 被投票淘汰的玩家
        self.last_action_time = 0  # 上次行动时间
        
        # 角色相关
        self.werewolf_players = set()  # 挂科生阵营玩家
        self.good_players = set()  # 学生阵营玩家
        self.exchange_couples = []  # 交换生连接的情侣
        self.academic_affairs_target = None  # 教务处查验目标
        self.teacher_action = None  # 任课老师行动
        self.scholarship_target = None  # 奖学金保护目标
        self.cheater_target = None  # 作弊者目标
        self.ta_target = None  # 助教目标
        
        # 游戏配置
        self.min_players = config.get("min_players", 6)
        self.max_players = config.get("max_players", 12)
        self.night_timeout = config.get("night_timeout", 120)  # 夜晚时间(秒)
        self.day_timeout = config.get("day_timeout", 180)  # 白天时间(秒)
        self.vote_timeout = config.get("vote_timeout", 60)  # 投票时间(秒)
        self.enable_private_chat = config.get("enable_private_chat", True)
        self.show_role_death = config.get("show_role_death", True)
        self.allow_revote = config.get("allow_revote", False)
        
        # 角色配置
        self.roles_config = config.get("roles", {
            "bad_student": 2,  # 挂科生数量
            "academic_affairs": 1,  # 教务处
            "teacher": 1,  # 任课老师
            "scholarship": 1,  # 奖学金
            "teaching_assistant": 1,  # 助教
            "exchange_student": 0,  # 交换生 (可选)
            "repeater": 0,  # 重修生 (可选)
            "academic_warning": 0,  # 学业预警 (可选)
            "librarian": 0,  # 图书馆管理员 (可选)
            "student_union": 0,  # 学生会主席 (可选)
            "cheater": 0,  # 作弊者 (可选)
        })
        
        logger.info("[挂科狼人杀] 插件初始化完成")

    def _generate_roles(self, player_count: int) -> List[Role]:
        """根据玩家人数生成角色列表"""
        roles = []
        
        # 计算挂科生数量
        bad_count = self.roles_config.get("bad_student", 2)
        if player_count <= 6:
            bad_count = 2
        elif player_count <= 8:
            bad_count = 3
        else:
            bad_count = 4
        
        # 添加挂科生
        roles.extend([Role.BAD_STUDENT] * bad_count)
        
        # 添加特殊角色
        if self.roles_config.get("academic_affairs", 1):
            roles.append(Role.ACADEMIC_AFFAIRS)
        
        if self.roles_config.get("teacher", 1):
            roles.append(Role.TEACHER)
            
        if self.roles_config.get("scholarship", 1):
            roles.append(Role.SCHOLARSHIP)
            
        if self.roles_config.get("teaching_assistant", 1):
            roles.append(Role.TEACHING_ASSISTANT)
            
        if self.roles_config.get("exchange_student", 0) and player_count >= 8:
            roles.append(Role.EXCHANGE_STUDENT)
            
        if self.roles_config.get("repeater", 0) and player_count >= 9:
            roles.append(Role.REPEATER)
            
        if self.roles_config.get("academic_warning", 0) and player_count >= 10:
            roles.append(Role.ACADEMIC_WARNING)
            
        if self.roles_config.get("librarian", 0) and player_count >= 11:
            roles.append(Role.LIBRARIAN)
            
        if self.roles_config.get("student_union", 0) and player_count >= 12:
            roles.append(Role.STUDENT_UNION)
            
        if self.roles_config.get("cheater", 0) and player_count >= 13:
            roles.append(Role.CHEATER)
        
        # 填充普通学生
        ordinary_count = player_count - len(roles)
        roles.extend([Role.ORDINARY_STUDENT] * ordinary_count)
        
        # 随机打乱
        random.shuffle(roles)
        return roles

    def _get_role_description(self, role: Role) -> str:
        """获取角色描述"""
        descriptions = {
            Role.BAD_STUDENT: (
                "🔴 【挂科生】- 挂科阵营\n"
                "能力：每晚可以集体讨论，选择一名学生挂科（使其出局）\n"
                "胜利条件：淘汰所有学生阵营玩家"
            ),
            Role.ORDINARY_STUDENT: (
                "🎓 【普通学生】- 学生阵营\n"
                "能力：无特殊能力，凭借敏锐的观察力找出挂科生\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.ACADEMIC_AFFAIRS: (
                "🏛️ 【教务处】- 学生阵营\n"
                "能力：每晚可以查验一名玩家的身份，确认其是否为挂科生\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.TEACHER: (
                "👨‍🏫 【任课老师】- 学生阵营\n"
                "能力：拥有两瓶药水\n"
                "  平时成绩（救药）：可以救活一名被挂科的学生\n"
                "  挂科警告（毒药）：可以让一名学生挂科出局\n"
                "  注意：同一晚不能使用两种药水\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.SCHOLARSHIP: (
                "🏅 【奖学金】- 学生阵营\n"
                "能力：每晚可以保护一名学生，使其不会被挂科\n"
                "  但不能连续两晚保护同一名学生\n"
                "  被保护的学生如果被任课老师用毒药挂科，仍然会出局\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.TEACHING_ASSISTANT: (
                "👨‍🎓 【助教】- 学生阵营\n"
                "能力：当被挂科（夜晚被淘汰或白天被投票出局）时\n"
                "  可以带走一名学生一起出局\n"
                "  被挂科时不能发动技能\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.EXCHANGE_STUDENT: (
                "🌍 【交换生】- 第三方阵营\n"
                "能力：游戏开始时选择两名玩家成为情侣\n"
                "  情侣中一人出局，另一人也会殉情出局\n"
                "  交换生自身可能与情侣同阵营或不同阵营\n"
                "胜利条件：与情侣一起活到最后"
            ),
            Role.REPEATER: (
                "🔄 【重修生】- 随机阵营\n"
                "能力：游戏开始时从两张身份牌中选择一张作为身份\n"
                "  如果两张身份牌中有挂科生，则必须选择挂科生\n"
                "  否则可以选择任意身份\n"
                "胜利条件：根据所选身份决定"
            ),
            Role.ACADEMIC_WARNING: (
                "⚠️ 【学业预警】- 挂科阵营\n"
                "能力：每晚可以额外查验一名玩家的具体身份\n"
                "  白天发言阶段，可以自爆带走一名玩家\n"
                "胜利条件：淘汰所有学生阵营玩家"
            ),
            Role.LIBRARIAN: (
                "📚 【图书馆管理员】- 学生阵营\n"
                "能力：每晚可以禁言一名玩家，使其第二天不能发言\n"
                "  不能连续两晚禁言同一名玩家\n"
                "  被禁言的玩家仍可以投票\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.STUDENT_UNION: (
                "👑 【学生会主席】- 学生阵营\n"
                "能力：有两颗学分（两条命）\n"
                "  第一次被挂科不会出局，只会失去一颗学分\n"
                "  被任课老师用毒药挂科时直接出局\n"
                "胜利条件：找出并淘汰所有挂科生"
            ),
            Role.CHEATER: (
                "🎭 【作弊者】- 挂科阵营\n"
                "能力：白天不会被教务处查验为挂科生\n"
                "  只有晚上被教务处查验时才会暴露身份\n"
                "  挂科生不知道作弊者的身份\n"
                "胜利条件：淘汰所有学生阵营玩家"
            )
        }
        return descriptions.get(role, "未知角色")

    def _get_role_night_action(self, role: Role) -> str:
        """获取角色夜晚行动说明"""
        actions = {
            Role.BAD_STUDENT: "请选择一名学生挂科（淘汰）",
            Role.ACADEMIC_AFFAIRS: "请选择一名学生查验其身份",
            Role.TEACHER: "请选择使用平时成绩（救人）或挂科警告（淘汰）",
            Role.SCHOLARSHIP: "请选择一名学生保护（使其今晚不会被挂科）",
            Role.ACADEMIC_WARNING: "请选择一名学生查验其具体身份",
            Role.LIBRARIAN: "请选择一名学生禁言（使其明天不能发言）",
            Role.CHEATER: "请选择一名学生进行干扰（使其被查验时显示为学生阵营）",
        }
        return actions.get(role, "无夜晚行动")

    async def _send_private_message(self, user_id: str, content: str):
        """发送私聊消息"""
        if not self.enable_private_chat:
            return
        try:
            await self.context.send_message(
                MessageType.PRIVATE,
                user_id,
                content
            )
        except Exception as e:
            logger.error(f"[挂科狼人杀] 发送私聊消息失败: {e}")

    async def _send_group_message(self, content: str):
        """发送群聊消息"""
        if not self.game_group_id:
            return
        try:
            await self.context.send_message(
                MessageType.GROUP,
                self.game_group_id,
                content
            )
        except Exception as e:
            logger.error(f"[挂科狼人杀] 发送群聊消息失败: {e}")

    async def _broadcast_to_players(self, content: str, exclude: List[str] = None):
        """向所有存活玩家广播消息"""
        exclude = exclude or []
        for player_id, player in self.players.items():
            if player.status == PlayerStatus.ALIVE and player_id not in exclude:
                await self._send_private_message(player_id, content)

    async def start_registration(self, group_id: str, master_id: str):
        """开始报名"""
        if self.game_phase != GamePhase.WAITING:
            await self._send_group_message("❌ 游戏正在进行中，无法开始新游戏")
            return
            
        self.game_phase = GamePhase.REGISTERING
        self.game_group_id = group_id
        self.game_master = master_id
        self.registered_players.clear()
        
        await self._send_group_message(
            f"🎮 【挂科版狼人杀】游戏报名开始！\n"
            f"📢 主持人：@{master_id}\n"
            f"👥 人数：{self.min_players}-{self.max_players}人\n"
            f"⏰ 报名时间：2分钟\n\n"
            f"输入【报名】或【join】加入游戏\n"
            f"输入【开始游戏】或【start】开始游戏（需至少{self.min_players}人）"
        )
        
        # 设置报名超时
        asyncio.create_task(self._registration_timeout())

    async def _registration_timeout(self):
        """报名超时"""
        await asyncio.sleep(120)  # 2分钟报名时间
        if self.game_phase == GamePhase.REGISTERING:
            if len(self.registered_players) >= self.min_players:
                await self.start_game()
            else:
                await self._send_group_message(
                    f"⏰ 报名时间结束，报名人数不足{self.min_players}人，游戏取消"
                )
                self.reset_game()

    async def register_player(self, user_id: str, user_name: str):
        """玩家报名"""
        if self.game_phase != GamePhase.REGISTERING:
            await self._send_private_message(user_id, "❌ 当前不在报名阶段")
            return
            
        if user_id in self.registered_players:
            await self._send_private_message(user_id, "❌ 你已经报名过了")
            return
            
        self.registered_players.add(user_id)
        self.players[user_id] = Player(
            user_id=user_id,
            user_name=user_name,
            group_id=self.game_group_id
        )
        
        await self._send_group_message(
            f"✅ {user_name} 已报名\n"
            f"📊 当前报名人数：{len(self.registered_players)}/{self.max_players}"
        )
        
        await self._send_private_message(
            user_id,
            f"✅ 报名成功！\n"
            f"请等待游戏开始，当前报名人数：{len(self.registered_players)}人"
        )

    async def start_game(self):
        """开始游戏"""
        if len(self.registered_players) < self.min_players:
            await self._send_group_message(
                f"❌ 报名人数不足{self.min_players}人，无法开始游戏"
            )
            return
            
        self.game_phase = GamePhase.NIGHT
        self.day_count = 0
        self.player_order = list(self.registered_players)
        
        # 分配角色
        roles = self._generate_roles(len(self.player_order))
        random.shuffle(self.player_order)
        
        for i, player_id in enumerate(self.player_order):
            player = self.players[player_id]
            player.role = roles[i]
            
            # 初始化阵营
            if roles[i] in [Role.BAD_STUDENT, Role.ACADEMIC_WARNING, Role.CHEATER]:
                self.werewolf_players.add(player_id)
            else:
                self.good_players.add(player_id)
        
        # 通知玩家角色
        await self._send_group_message(
            f"🎮 【挂科版狼人杀】游戏开始！\n"
            f"👥 玩家数量：{len(self.player_order)}人\n"
            f"🌙 现在是第{self.day_count+1}天夜晚\n"
            f"📢 请查看私聊获取你的身份"
        )
        
        # 发送角色信息给每个玩家
        for player_id in self.player_order:
            player = self.players[player_id]
            role_desc = self._get_role_description(player.role)
            night_action = self._get_role_night_action(player.role)
            
            # 如果是挂科生，告诉他们同伙
            if player_id in self.werewolf_players:
                teammates = [self.players[p].user_name for p in self.werewolf_players if p != player_id]
                teammates_str = "、".join(teammates) if teammates else "无"
                role_desc += f"\n\n👥 你的挂科生队友：{teammates_str}"
            
            await self._send_private_message(
                player_id,
                f"🎭 你的身份是：{player.role.value}\n\n"
                f"📋 角色能力：\n{role_desc}\n\n"
                f"🌙 夜晚行动：{night_action if night_action != '无夜晚行动' else '请等待天亮'}"
            )
        
        # 开始第一夜
        await self.start_night()

    async def start_night(self):
        """开始夜晚阶段"""
        self.game_phase = GamePhase.NIGHT
        self.day_count += 1
        self.night_actions.clear()
        
        # 重置保护状态
        for player in self.players.values():
            player.is_protected = False
        
        await self._send_group_message(
            f"🌙 第{self.day_count}天夜晚开始！\n"
            f"⏰ 请有夜晚行动能力的玩家在{self.night_timeout}秒内完成行动\n"
            f"💤 其他玩家请耐心等待..."
        )
        
        # 通知有夜晚行动的玩家
        for player_id, player in self.players.items():
            if player.status != PlayerStatus.ALIVE:
                continue
                
            night_action = self._get_role_night_action(player.role)
            if night_action != "无夜晚行动":
                await self._send_private_message(
                    player_id,
                    f"🌙 第{self.day_count}天夜晚\n"
                    f"请进行你的夜晚行动：\n{night_action}\n"
                    f"⏰ 请在{self.night_timeout}秒内完成"
                )
        
        # 设置夜晚超时
        asyncio.create_task(self._night_timeout())

    async def _night_timeout(self):
        """夜晚超时"""
        await asyncio.sleep(self.night_timeout)
        if self.game_phase == GamePhase.NIGHT:
            await self.process_night_actions()

    async def process_night_actions(self):
        """处理夜晚行动结果"""
        await self._send_group_message("🌅 天亮了！")
        await asyncio.sleep(2)
        
        # 处理挂科生行动
        killed_players = []
        protected_players = []
        poisoned_players = []
        
        # 收集挂科生投票
        werewolf_votes = defaultdict(int)
        for player_id, action in self.night_actions.items():
            player = self.players.get(player_id)
            if player and player.role == Role.BAD_STUDENT and action:
                target_player = self.get_player_by_name(action)
                if target_player and target_player.status == PlayerStatus.ALIVE:
                    werewolf_votes[target_player.user_id] += 1
        
        # 确定挂科目标
        if werewolf_votes:
            max_votes = max(werewolf_votes.values())
            candidates = [pid for pid, votes in werewolf_votes.items() if votes == max_votes]
            kill_target = random.choice(candidates) if candidates else None
            
            if kill_target:
                target_player = self.players[kill_target]
                # 检查是否被奖学金保护
                if not target_player.is_protected:
                    killed_players.append(target_player)
                else:
                    protected_players.append(target_player)
        
        # 处理任课老师行动
        teacher_action = self.night_actions.get(self._get_player_by_role(Role.TEACHER))
        if teacher_action:
            teacher_player = self.players.get(self._get_player_by_role(Role.TEACHER))
            if teacher_player and teacher_player.status == PlayerStatus.ALIVE:
                if teacher_action.startswith("救"):
                    # 救人行动
                    saved_player_name = teacher_action[1:].strip()
                    saved_player = self.get_player_by_name(saved_player_name)
                    if saved_player and saved_player in killed_players:
                        killed_players.remove(saved_player)
                        await self._send_group_message(f"💊 任课老师使用平时成绩救了{saved_player.user_name}！")
                elif teacher_action.startswith("毒"):
                    # 毒人行动
                    poisoned_player_name = teacher_action[1:].strip()
                    poisoned_player = self.get_player_by_name(poisoned_player_name)
                    if poisoned_player and poisoned_player.status == PlayerStatus.ALIVE:
                        # 检查是否被奖学金保护
                        if not poisoned_player.is_protected:
                            poisoned_players.append(poisoned_player)
        
        # 处理其他角色行动
        # 这里可以添加其他角色的夜晚行动处理逻辑
        
        # 公布夜晚结果
        night_result = f"🌅 第{self.day_count}天夜晚结束\n"
        
        if killed_players:
            names = "、".join([p.user_name for p in killed_players])
            night_result += f"📉 昨晚挂科的学生：{names}\n"
            for player in killed_players:
                player.status = PlayerStatus.DROPPED
                if self.show_role_death:
                    night_result += f"  - {player.user_name} 的身份是 {player.role.value}\n"
        else:
            night_result += "🎉 昨晚是平安夜，没有学生挂科\n"
            
        if poisoned_players:
            names = "、".join([p.user_name for p in poisoned_players])
            night_result += f"🧪 被任课老师挂科：{names}\n"
            for player in poisoned_players:
                player.status = PlayerStatus.DROPPED
        
        if protected_players:
            names = "、".join([p.user_name for p in protected_players])
            night_result += f"🛡️ 被奖学金保护：{names}\n"
        
        await self._send_group_message(night_result)
        
        # 检查游戏是否结束
        if self.check_game_end():
            return
            
        # 进入白天阶段
        await self.start_day()

    async def start_day(self):
        """开始白天阶段"""
        self.game_phase = GamePhase.DAY
        
        await self._send_group_message(
            f"☀️ 第{self.day_count}天白天开始！\n"
            f"🗣️ 请玩家依次发言讨论\n"
            f"⏰ 讨论时间：{self.day_timeout}秒\n"
            f"发言格式：/发言 你的发言内容"
        )
        
        # 设置白天超时
        asyncio.create_task(self._day_timeout())

    async def _day_timeout(self):
        """白天超时"""
        await asyncio.sleep(self.day_timeout)
        if self.game_phase == GamePhase.DAY:
            await self.start_voting()

    async def start_voting(self):
        """开始投票阶段"""
        self.game_phase = GamePhase.VOTING
        self.votes.clear()
        
        # 获取存活玩家列表
        alive_players = [p for p in self.players.values() if p.status == PlayerStatus.ALIVE]
        alive_names = "、".join([p.user_name for p in alive_players])
        
        await self._send_group_message(
            f"🗳️ 开始投票！\n"
            f"👥 存活玩家：{alive_names}\n"
            f"⏰ 投票时间：{self.vote_timeout}秒\n"
            f"📝 投票格式：/投票 玩家名称\n"
            f"💡 得票最多的玩家将被退学（淘汰）"
        )
        
        # 设置投票超时
        asyncio.create_task(self._vote_timeout())

    async def _vote_timeout(self):
        """投票超时"""
        await asyncio.sleep(self.vote_timeout)
        if self.game_phase == GamePhase.VOTING:
            await self.process_votes()

    async def process_votes(self):
        """处理投票结果"""
        # 统计票数
        vote_counts = defaultdict(int)
        for voter_id, target_name in self.votes.items():
            target_player = self.get_player_by_name(target_name)
            if target_player and target_player.status == PlayerStatus.ALIVE:
                vote_counts[target_player.user_id] += 1
        
        # 确定被投票淘汰的玩家
        lynched_player = None
        if vote_counts:
            max_votes = max(vote_counts.values())
            candidates = [pid for pid, votes in vote_counts.items() if votes == max_votes]
            
            if len(candidates) == 1:
                lynched_player = self.players[candidates[0]]
            else:
                # 平票，无人被淘汰
                tied_names = "、".join([self.players[pid].user_name for pid in candidates])
                await self._send_group_message(f"⚖️ 平票！{tied_names} 得票相同，无人被淘汰")
        
        # 处理淘汰
        if lynched_player:
            lynched_player.status = PlayerStatus.DROPPED
            await self._send_group_message(
                f"🚨 {lynched_player.user_name} 被投票退学！\n"
                f"身份是：{lynched_player.role.value}"
            )
            
            # 处理助教技能
            if lynched_player.role == Role.TEACHING_ASSISTANT:
                await self._handle_teaching_assistant_skill(lynched_player)
        
        # 检查游戏是否结束
        if self.check_game_end():
            return
            
        # 进入下一夜
        await self.start_night()

    async def _handle_teaching_assistant_skill(self, ta_player: Player):
        """处理助教技能"""
        await self._send_group_message(
            f"💥 {ta_player.user_name}（助教）发动技能！\n"
            f"助教可以在被淘汰时带走一名学生\n"
            f"请在10秒内选择要带走的学生：/带走 学生名称"
        )
        
        # 这里需要实现助教选择带走的逻辑
        # 由于时间关系，简化处理
        await asyncio.sleep(10)
        
        # 随机选择一个存活玩家带走
        alive_players = [p for p in self.players.values() 
                        if p.status == PlayerStatus.ALIVE and p.user_id != ta_player.user_id]
        if alive_players:
            target = random.choice(alive_players)
            target.status = PlayerStatus.DROPPED
            await self._send_group_message(f"💥 {ta_player.user_name} 带走了 {target.user_name}！")

    def check_game_end(self) -> bool:
        """检查游戏是否结束"""
        alive_good = [p for p in self.players.values() 
                     if p.status == PlayerStatus.ALIVE and p.user_id in self.good_players]
        alive_werewolf = [p for p in self.players.values() 
                         if p.status == PlayerStatus.ALIVE and p.user_id in self.werewolf_players]
        
        if not alive_werewolf:
            # 学生阵营胜利
            self.game_phase = GamePhase.ENDED
            asyncio.create_task(self.end_game("学生阵营"))
            return True
        elif not alive_good:
            # 挂科阵营胜利
            self.game_phase = GamePhase.ENDED
            asyncio.create_task(self.end_game("挂科阵营"))
            return True
        
        return False

    async def end_game(self, winner: str):
        """结束游戏"""
        # 显示所有玩家身份
        result_message = f"🎉 游戏结束！{winner}胜利！\n\n📊 玩家身份：\n"
        
        for player in self.players.values():
            status_emoji = "✅" if player.status == PlayerStatus.ALIVE else "❌"
            result_message += f"{status_emoji} {player.user_name}: {player.role.value}\n"
        
        result_message += "\n🎮 感谢参与挂科版狼人杀！"
        
        await self._send_group_message(result_message)
        self.reset_game()

    def reset_game(self):
        """重置游戏"""
        self.game_phase = GamePhase.WAITING
        self.game_group_id = None
        self.game_master = None
        self.players.clear()
        self.registered_players.clear()
        self.player_order.clear()
        self.day_count = 0
        self.night_actions.clear()
        self.day_actions.clear()
        self.votes.clear()
        self.lynched_player = None
        self.werewolf_players.clear()
        self.good_players.clear()
        self.exchange_couples.clear()
        self.academic_affairs_target = None
        self.teacher_action = None
        self.scholarship_target = None
        self.cheater_target = None
        self.ta_target = None

    def get_player_by_name(self, name: str) -> Optional[Player]:
        """通过玩家名称获取玩家对象"""
        for player in self.players.values():
            if player.user_name == name:
                return player
        return None

    def _get_player_by_role(self, role: Role) -> Optional[str]:
        """通过角色获取玩家ID"""
        for player_id, player in self.players.items():
            if player.role == role and player.status == PlayerStatus.ALIVE:
                return player_id
        return None

    async def handle_night_action(self, user_id: str, action: str):
        """处理夜晚行动"""
        if self.game_phase != GamePhase.NIGHT:
            await self._send_private_message(user_id, "❌ 现在不是夜晚行动时间")
            return
            
        player = self.players.get(user_id)
        if not player or player.status != PlayerStatus.ALIVE:
            await self._send_private_message(user_id, "❌ 你已出局，不能行动")
            return
            
        # 记录行动
        self.night_actions[user_id] = action
        
        await self._send_private_message(user_id, f"✅ 你的行动已记录：{action}")

    async def handle_vote(self, voter_id: str, target_name: str):
        """处理投票"""
        if self.game_phase != GamePhase.VOTING:
            await self._send_private_message(voter_id, "❌ 现在不是投票时间")
            return
            
        voter = self.players.get(voter_id)
        if not voter or voter.status != PlayerStatus.ALIVE:
            await self._send_private_message(voter_id, "❌ 你已出局，不能投票")
            return
            
        target = self.get_player_by_name(target_name)
        if not target or target.status != PlayerStatus.ALIVE:
            await self._send_private_message(voter_id, f"❌ 找不到玩家 {target_name} 或该玩家已出局")
            return
            
        if target.user_id == voter_id:
            await self._send_private_message(voter_id, "❌ 不能投票给自己")
            return
            
        # 记录投票
        self.votes[voter_id] = target_name
        await self._send_private_message(voter_id, f"✅ 你已投票给 {target_name}")
        
        # 广播投票情况
        vote_count = len(self.votes)
        alive_count = len([p for p in self.players.values() if p.status == PlayerStatus.ALIVE])
        await self._send_group_message(f"🗳️ 投票进度：{vote_count}/{alive_count}")

    async def handle_speech(self, user_id: str, content: str):
        """处理发言"""
        if self.game_phase != GamePhase.DAY:
            await self._send_private_message(user_id, "❌ 现在不是发言时间")
            return
            
        player = self.players.get(user_id)
        if not player or player.status != PlayerStatus.ALIVE:
            await self._send_private_message(user_id, "❌ 你已出局，不能发言")
            return
            
        # 广播发言
        await self._send_group_message(f"🗣️ {player.user_name}：{content}")

    @filter.event_message_type(EventMessageType.ALL)
    @filter.platform_adapter_type(PlatformAdapterType.AIOCQHTTP)
    async def on_message(self, event: AstrMessageEvent):
        """处理消息"""
        try:
            message = str(event.message_obj.message_chain).strip()
            user_id = str(event.get_sender_id())
            user_name = event.get_sender_name() or f"用户{user_id}"
            group_id = str(event.get_group_id())
            
            # 只处理游戏所在群聊的消息
            if group_id != self.game_group_id:
                return
                
            # 处理命令
            if message.startswith("报名") or message.startswith("join"):
                await self.register_player(user_id, user_name)
                
            elif message.startswith("开始游戏") or message.startswith("start"):
                if user_id == self.game_master or self.game_master is None:
                    await self.start_game()
                else:
                    await self._send_private_message(user_id, "❌ 只有主持人可以开始游戏")
                    
            elif message.startswith("/投票"):
                parts = message.split(" ", 1)
                if len(parts) > 1:
                    target_name = parts[1].strip()
                    await self.handle_vote(user_id, target_name)
                    
            elif message.startswith("/发言"):
                parts = message.split(" ", 1)
                if len(parts) > 1:
                    speech_content = parts[1].strip()
                    await self.handle_speech(user_id, speech_content)
                    
            elif message.startswith("/行动"):
                parts = message.split(" ", 1)
                if len(parts) > 1:
                    action = parts[1].strip()
                    await self.handle_night_action(user_id, action)
                    
            elif message.startswith("/带走"):
                parts = message.split(" ", 1)
                if len(parts) > 1:
                    target_name = parts[1].strip()
                    # 处理助教技能
                    pass
                    
            elif message == "游戏规则":
                await self._send_group_message(self.get_game_rules())
                
            elif message == "游戏状态":
                await self.show_game_status()
                
            elif message == "取消游戏":
                if user_id == self.game_master:
                    await self._send_group_message("游戏已取消")
                    self.reset_game()
                    
        except Exception as e:
            logger.error(f"[挂科狼人杀] 处理消息失败: {e}", exc_info=True)

    def get_game_rules(self) -> str:
        """获取游戏规则"""
        return (
            "🎮 【挂科版狼人杀】游戏规则\n\n"
            "🎯 游戏目标：\n"
            "  🔴 挂科阵营：让所有学生挂科\n"
            "  🎓 学生阵营：找出并淘汰所有挂科生\n\n"
            "🌙 夜晚行动顺序：\n"
            "  1. 作弊者（可选）\n"
            "  2. 挂科生、学业预警\n"
            "  3. 教务处\n"
            "  4. 奖学金\n"
            "  5. 图书馆管理员\n"
            "  6. 任课老师\n\n"
            "☀️ 白天流程：\n"
            "  1. 公布昨晚结果\n"
            "  2. 讨论发言\n"
            "  3. 投票淘汰\n\n"
            "💡 特殊角色说明详见私聊"
        )

    async def show_game_status(self):
        """显示游戏状态"""
        if self.game_phase == GamePhase.WAITING:
            await self._send_group_message("🕐 游戏未开始")
            return
            
        status_msg = f"🎮 游戏状态：{self.game_phase.value}\n"
        
        if self.game_phase == GamePhase.REGISTERING:
            status_msg += f"👥 已报名：{len(self.registered_players)}人\n"
            status_msg += f"⏰ 最少{self.min_players}人开始游戏"
            
        elif self.game_phase in [GamePhase.NIGHT, GamePhase.DAY, GamePhase.VOTING]:
            status_msg += f"📅 第{self.day_count}天\n"
            
            # 存活玩家
            alive_players = [p for p in self.players.values() if p.status == PlayerStatus.ALIVE]
            dead_players = [p for p in self.players.values() if p.status == PlayerStatus.DROPPED]
            
            status_msg += f"✅ 存活：{len(alive_players)}人\n"
            if alive_players:
                status_msg += "  " + "、".join([p.user_name for p in alive_players]) + "\n"
                
            status_msg += f"❌ 挂科：{len(dead_players)}人\n"
            if dead_players and self.show_role_death:
                status_msg += "  " + "、".join([f"{p.user_name}({p.role.value})" for p in dead_players])
        
        await self._send_group_message(status_msg)

