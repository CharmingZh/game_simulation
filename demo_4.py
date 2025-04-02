import os
import random
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体显示中文
plt.rcParams["axes.unicode_minus"] = False    # 正常显示负号

# ========== 全局参数 ==========
RELIEVE_PROB = 0.7       # 回复短信后，触发缓解的概率
RELIEVE_RATIO = 0.2      # 缓解比例
SMS_PARTY_FACTOR = 1.2   # 若参与聚会，对短信压力的额外倍率
IS_PARTY = False         # 是否已赴约的全局标记

# ========== 工具函数：清屏 & 绘制界面 ==========

def clear_console():
    print("\033[2J\033[H", end="")


def draw_gba_frame(title, scene_idx, total_scenes, task_idx, total_tasks, current_stress, current_time):
    """
    模拟GBA风格的文字界面，显示标题、场景进度、压力、剩余时间等信息
    你可以根据个人审美/需求进行修饰
    """
    # 构建一个文本进度条（示例）
    scene_progress_bar = build_progress_bar(scene_idx, total_scenes, bar_length=20)
    task_progress_bar  = build_progress_bar(task_idx, total_tasks, bar_length=20)

    print("┌" + "─" * 50 + "┐")
    print(f"│{title.center(50)}│")
    print("├" + "─" * 50 + "┤")
    print(f"│ 场景进度: {scene_idx}/{total_scenes}  {scene_progress_bar} │")
    print(f"│ 任务进度: {task_idx}/{total_tasks}   {task_progress_bar} │")
    print(f"│ 当前压力: {current_stress:<6}  剩余时间: {current_time:<6}      │")
    print("└" + "─" * 50 + "┘")

def build_progress_bar(current, total, bar_length=20):
    """
    构建一个简单的ASCII进度条，如 [====      ]
    """
    if total <= 0:
        return "[Invalid/No Task]"
    ratio = float(current) / total
    filled = int(ratio * bar_length)
    return "[" + "=" * filled + " " * (bar_length - filled) + "]"

def pause_and_wait():
    """模拟老式游戏中的“按任意键继续”"""
    input("\n(按回车键继续...)")

# ========== 普通任务类 ==========
class Task:
    def __init__(self, description, options, importance=1):
        """
        description: 描述，如"是否吃早餐"
        options: dict, 例如：
          {
            "A. 吃": {"time_cost": 0.5, "prob": 0.8, "stress_change": 5},
            "B. 不吃": {"time_cost": 0.25, "prob": 0.2, "stress_change": 3}
          }
        importance: （可选）重要性
        """
        self.description = description
        self.options = options
        self.importance = importance

    def make_choice_manual(self, scene_idx, total_scenes, task_idx, total_tasks, current_stress, current_time):
        """
        手动模式：让玩家选择一个选项
        新增参数（scene_idx / total_scenes / task_idx / total_tasks / current_stress / current_time）
        用于展示界面时一起显示。
        """
        while True:
            # 每次进入选择前先清屏 & 绘制GBA边框
            clear_console()
            draw_gba_frame(
                f"任务: {self.description}",
                scene_idx,
                total_scenes,
                task_idx,
                total_tasks,
                current_stress,
                current_time
            )

            # 显示可选项
            option_names = list(self.options.keys())
            for i, opt_name in enumerate(option_names):
                opt_data = self.options[opt_name]
                print(f"{i}. {opt_name}")
                print(f"   - 压力变化: {opt_data['stress_change']}, 时间消耗: {opt_data['time_cost']}")
                print(f"   - 预设概率(仅参考): {opt_data['prob']}\n")

            choice_str = input("请输入选项编号: ").strip()
            if choice_str.isdigit():
                choice_idx = int(choice_str)
                if 0 <= choice_idx < len(option_names):
                    chosen_option = option_names[choice_idx]
                    data = self.options[chosen_option]
                    return chosen_option, data["stress_change"], data["time_cost"]
            # 如果输入不合法，就继续循环

    def make_choice_auto(self):
        """概率模式：根据prob随机选取一个选项"""
        option_names = list(self.options.keys())
        weights = [self.options[opt]["prob"] for opt in option_names]
        chosen_option = random.choices(option_names, weights=weights, k=1)[0]
        data = self.options[chosen_option]
        return chosen_option, data["stress_change"], data["time_cost"]

# ========== 特殊场景类：PartyScene ==========
class PartyScene:
    def __init__(self, name, tasks):
        self.name = name
        self.tasks = tasks

    def play_scene_manual(self, current_stress, current_time, scene_idx, total_scenes):
        scene_stress = 0
        total_tasks = len(self.tasks)
        for i, task in enumerate(self.tasks):
            if current_time <= 0:
                break
            chosen_option, stress_change, time_cost = task.make_choice_manual(
                scene_idx, total_scenes, i+1, total_tasks, current_stress+scene_stress, current_time
            )
            # 计算结果
            scene_stress += stress_change
            current_time -= time_cost

            # 如果在这里出现“欣然赴约”的选项，则全局标记 IS_PARTY = True
            if "欣然赴约" in chosen_option:
                global IS_PARTY
                IS_PARTY = True

            # 做完选择后，清屏显示一下结果，再等待玩家按键继续
            clear_console()
            draw_gba_frame(
                f"[{self.name}] 完成选择: {chosen_option}",
                scene_idx,
                total_scenes,
                i+1,
                total_tasks,
                current_stress+scene_stress,
                current_time
            )
            print(f"你选择了: {chosen_option}, 当前场景压力增加: {stress_change}, 时间消耗: {time_cost}")
            if "欣然赴约" in chosen_option:
                print("已答应赴约，后续短信压力可能会上调")
            pause_and_wait()

        return scene_stress, current_time

    def play_scene_auto(self, current_stress, current_time):
        scene_stress = 0
        for task in self.tasks:
            if current_time <= 0:
                break
            chosen_option, stress_change, time_cost = task.make_choice_auto()
            if "欣然赴约" in chosen_option:
                global IS_PARTY
                IS_PARTY = True
            scene_stress += stress_change
            current_time -= time_cost
        return scene_stress, current_time

# ========== 特殊短信任务类 ==========
class SMSTask:
    def __init__(self, description, stress_change=10, prob=1.0):
        """
        这里假设短信任务只有一个选项，即“接受短信”。
        stress_change: 默认给定的压力增量
        prob: 用于概率模式时，是否激活或者如何选的权重
        """
        self.description = description
        self.stress_change = stress_change
        self.prob = prob
        self.active = True

    def make_choice_manual(self, relieve=False):
        """
        手动模式下，这里并没有多选项，只有一个“接受短信”。
        如果参数relieve=True，则有概率进行缓解。
        """
        final_stress = self.stress_change
        if relieve and random.random() < RELIEVE_PROB:
            final_stress -= final_stress * RELIEVE_RATIO
        return final_stress

    def make_choice_auto(self, relieve=False):
        """
        概率模式下，也假设这条短信一定会“触发”，
        只是如果relieve=True，则可能出现缓解。
        """
        final_stress = self.stress_change
        if relieve and random.random() < RELIEVE_PROB:
            final_stress -= final_stress * RELIEVE_RATIO
        return final_stress

# ========== 场景五示例：下班后加班 ==========
class OvertimeScene:
    def __init__(self, name, reply_task, sms_tasks):
        self.name = name
        self.reply_task = reply_task   # 普通Task，决定是否回复短信
        self.sms_tasks = sms_tasks     # 一组SMSTask

    def play_scene_manual(self, current_stress, current_time, scene_idx, total_scenes):
        scene_stress = 0
        # 1) 先判断是否回复短信（手动选择）
        #   由于这是该场景的第1个任务，所以 task_idx=1, total_tasks = 1(决定短信回复) + len(sms_tasks)
        total_tasks = 1 + len(self.sms_tasks)

        chosen_option, reply_stress, time_cost = self.reply_task.make_choice_manual(
            scene_idx, total_scenes, 1, total_tasks, current_stress, current_time
        )
        scene_stress += reply_stress
        current_time -= time_cost

        # 是否触发缓解
        is_reply = ("回复" in chosen_option)

        # 显示本次结果
        clear_console()
        draw_gba_frame(
            f"[{self.name}] 决策: {chosen_option}",
            scene_idx,
            total_scenes,
            1,
            total_tasks,
            current_stress + scene_stress,
            current_time
        )
        print(f"是否回复短信 -> 你选择: {chosen_option}, 压力变动: +{reply_stress}, 耗时: {time_cost}")
        pause_and_wait()

        # 2) 激活的短信任务（这里为了演示，假设都激活）
        #    从 task_idx=2 开始遍历
        for i, sms in enumerate(self.sms_tasks, start=2):
            if sms.active:
                final_stress = sms.make_choice_manual(relieve=is_reply)
                if IS_PARTY:
                    final_stress *= SMS_PARTY_FACTOR
                scene_stress += final_stress

                clear_console()
                draw_gba_frame(
                    f"[{self.name}] {sms.description}",
                    scene_idx,
                    total_scenes,
                    i,
                    total_tasks,
                    current_stress + scene_stress,
                    current_time
                )
                print(f"短信: {sms.description}, 压力变动: +{final_stress:.2f}")
                if is_reply:
                    print("（你已选择回复短信，可能触发缓解）")
                if IS_PARTY:
                    print("（你已参加聚会，短信压力额外上调）")
                pause_and_wait()

        return scene_stress, current_time

    def play_scene_auto(self, current_stress, current_time):
        scene_stress = 0
        chosen_option, reply_stress, time_cost = self.reply_task.make_choice_auto()
        scene_stress += reply_stress
        current_time -= time_cost
        is_reply = ("回复" in chosen_option)

        for sms in self.sms_tasks:
            if sms.active:
                final_stress = sms.make_choice_auto(relieve=is_reply)
                if IS_PARTY:
                    final_stress *= SMS_PARTY_FACTOR
                scene_stress += final_stress
        return scene_stress, current_time

# ========== 普通场景示例 ==========
class Scene:
    def __init__(self, name, tasks):
        self.name = name
        self.tasks = tasks

    def play_scene_manual(self, current_stress, current_time, scene_idx, total_scenes):
        scene_stress = 0
        total_tasks = len(self.tasks)
        for i, task in enumerate(self.tasks):
            if current_time <= 0:
                break
            chosen_option, stress_change, time_cost = task.make_choice_manual(
                scene_idx, total_scenes, i+1, total_tasks, current_stress+scene_stress, current_time
            )
            scene_stress += stress_change
            current_time -= time_cost

            # 做完选择后，清屏显示一下结果，再等待
            clear_console()
            draw_gba_frame(
                f"[{self.name}] 完成选择: {chosen_option}",
                scene_idx,
                total_scenes,
                i+1,
                total_tasks,
                current_stress + scene_stress,
                current_time
            )
            print(f"  -> 你选择了: {chosen_option}, 压力变化: +{stress_change}, 耗时: {time_cost}")
            pause_and_wait()
        return scene_stress, current_time

    def play_scene_auto(self, current_stress, current_time):
        scene_stress = 0
        for task in self.tasks:
            if current_time <= 0:
                break
            chosen_option, stress_change, time_cost = task.make_choice_auto()
            scene_stress += stress_change
            current_time -= time_cost
        return scene_stress, current_time

# ========== 构建游戏场景 ==========
def build_game_scenes():
    """手动创建一些场景和任务，所有压力变化值与prob都提前手动设置。"""
    # 场景1
    task_breakfast = Task(
        "是否吃早餐",
        {
            "A. 吃": {"time_cost": 0.5, "prob": 0.8, "stress_change": 5},
            "B. 不吃": {"time_cost": 0.25, "prob": 0.2, "stress_change": 10}
        },
        importance=1
    )
    scene1 = Scene("场景1：出门上班", [task_breakfast])

    # 场景2
    task_boss = Task(
        "老板无理由斥责",
        {
            "A. 默默承受": {"time_cost": 0.5, "prob": 0.5, "stress_change": 8},
            "B. 表达不满": {"time_cost": 0.5, "prob": 0.5, "stress_change": 15}
        },
        importance=1
    )
    scene2 = Scene("场景2：老板骂人", [task_boss])

    # 场景3
    task_work1 = Task(
        "重复高压工作1",
        {
            "A. 完成任务": {"time_cost": 1, "prob": 0.5, "stress_change": 12},
            "B. 任务失败": {"time_cost": 1, "prob": 0.5, "stress_change": 20}
        },
        importance=1
    )
    task_work2 = Task(
        "重复高压工作2",
        {
            "A. 完成任务": {"time_cost": 1, "prob": 0.5, "stress_change": 12},
            "B. 任务失败": {"time_cost": 1, "prob": 0.5, "stress_change": 20}
        },
        importance=1
    )
    scene3 = Scene("场景3：开始工作", [task_work1, task_work2])

    # 场景4 (特殊场景：PartyScene)
    task_party = Task(
        "朋友邀约",
        {
            "A. 欣然赴约": {"time_cost": 1, "prob": 0.5, "stress_change": 5},
            "B. 先不去": {"time_cost": 1, "prob": 0.5, "stress_change": 2}
        },
        importance=3
    )
    scene4 = PartyScene("场景4：下班后，朋友聚餐", [task_party])

    # 场景5 (特殊场景：下班加班)
    reply_task = Task(
        "是否回复老板短信",
        {
            "A. 回复": {"time_cost": 0.5, "prob": 0.5, "stress_change": 5},
            "B. 不回复": {"time_cost": 0.5, "prob": 0.5, "stress_change": 10}
        },
        importance=2
    )
    sms1 = SMSTask("老板短信1", stress_change=10, prob=1.0)
    sms2 = SMSTask("老板短信2", stress_change=15, prob=1.0)
    sms3 = SMSTask("老板短信3", stress_change=8, prob=1.0)
    sms4 = SMSTask("老板短信4", stress_change=6, prob=1.0)
    scene5 = OvertimeScene("场景5：下班后加班", reply_task, [sms1, sms2, sms3, sms4])

    return [scene1, scene2, scene3, scene4, scene5]

# ========== 运行游戏(手动) ==========
def run_game_manual():
    """模式A：手动模式——玩家亲自为每个任务做选择，带有GBA风格的刷新界面"""
    global IS_PARTY
    IS_PARTY = False

    scenes = build_game_scenes()
    total_scenes = len(scenes)

    current_stress = 0
    current_time = 10  # 假设今天只有10小时可用

    for scene_idx, scene in enumerate(scenes, start=1):
        # 进入新的场景前先清屏 & 显示场景标题
        clear_console()
        draw_gba_frame(
            f"进入{scene.name}",
            scene_idx,
            total_scenes,
            0,
            0,  # 还没开始做任务
            current_stress,
            current_time
        )
        pause_and_wait()

        # 根据不同的场景类型，调用不同的play函数
        if isinstance(scene, PartyScene):
            scene_stress, current_time = scene.play_scene_manual(
                current_stress, current_time, scene_idx, total_scenes
            )
        elif isinstance(scene, OvertimeScene):
            scene_stress, current_time = scene.play_scene_manual(
                current_stress, current_time, scene_idx, total_scenes
            )
        else:
            scene_stress, current_time = scene.play_scene_manual(
                current_stress, current_time, scene_idx, total_scenes
            )
        current_stress += scene_stress

    # 最后进入场景6: 睡前 & 结局
    clear_console()
    draw_gba_frame("场景6：一天结束，睡前", total_scenes, total_scenes, 1, 1, current_stress, current_time)
    if current_stress >= 60:
        print("结局：坏结局（压力过高）")
    else:
        print("结局：好结局（压力正常）")
    pause_and_wait()

    # 场景7: Ending
    clear_console()
    draw_gba_frame("场景7：Ending", total_scenes, total_scenes, 1, 1, current_stress, current_time)
    print("本日结束，游戏结束。")
    pause_and_wait()

# ========== 运行游戏(自动) ==========
def run_game_auto(num_simulations=1000):
    """
    模式B：概率模式——为每个选项预先设定概率，通过多次重复模拟估计压力分布
    （此模式不展示“GBA风格界面”，仅做自动仿真）
    """
    global IS_PARTY

    final_stress_list = []
    for _ in range(num_simulations):
        IS_PARTY = False
        scenes = build_game_scenes()
        current_stress = 0
        current_time = 10
        for scene in scenes:
            if isinstance(scene, PartyScene):
                scene_stress, current_time = scene.play_scene_auto(current_stress, current_time)
            elif isinstance(scene, OvertimeScene):
                scene_stress, current_time = scene.play_scene_auto(current_stress, current_time)
            else:
                scene_stress, current_time = scene.play_scene_auto(current_stress, current_time)
            current_stress += scene_stress
        final_stress_list.append(current_stress)

    # 简单绘制一下分布
    plt.figure()
    plt.hist(final_stress_list, bins=30, edgecolor='black')
    plt.xlabel("最终压力")
    plt.ylabel("出现次数")
    plt.title(f"重复 {num_simulations} 次后的最终压力分布")
    plt.show()
    print(f"模拟完成。平均压力: {sum(final_stress_list)/len(final_stress_list):.2f}")

# ========== 主程序入口 ==========
if __name__ == "__main__":
    print("===== 模式A：手动模式（GBA风格） =====")
    run_game_manual()

    print("\n===== 模式B：概率模式（重复模拟1000次）=====")
    run_game_auto(num_simulations=1000)
