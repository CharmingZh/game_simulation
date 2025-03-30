import random
import math
import matplotlib.pyplot as plt

plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体显示中文
plt.rcParams["axes.unicode_minus"] = False    # 正常显示负号

# 全局参数
DESIRED_MEAN = 100
DESIRED_STD = 25
SMS_a = 5
SMS_b = 3
RELIEVE_PROB = 0.7
RELIEVE_RATIO = 0.2
SMS_PARTY_FACTOR = 1.2

# ================= 普通任务类 =================
class Task:
    def __init__(self, description, options, importance=1):
        self.description = description
        self.options = options
        self.importance = importance

    def auto_set_stress(self, V):
        if len(self.options) != 2:
            raise ValueError("自动设置压力值只支持2个选项的任务。")
        option_names = list(self.options.keys())
        p_raw = self.options[option_names[0]]["prob"]
        total = p_raw + self.options[option_names[1]]["prob"]
        p = p_raw / total
        stress1 = math.sqrt(V * (1 - p) / p)
        stress2 = -math.sqrt(V * p / (1 - p))
        self.options[option_names[0]]["stress_change"] = stress1
        self.options[option_names[1]]["stress_change"] = stress2

    def make_choice(self):
        option_names = list(self.options.keys())
        weights = [self.options[opt]["prob"] for opt in option_names]
        chosen_option = random.choices(option_names, weights=weights, k=1)[0]
        data = self.options[chosen_option]
        return chosen_option, data["stress_change"], data["time_cost"]

# ================= 场景类 =================
class Scene:
    def __init__(self, name, tasks):
        self.name = name
        self.tasks = tasks

    def play_scene(self, current_stress, current_time, log_lines):
        log_lines.append(f"=== 进入场景：{self.name} ===")
        scene_stress = 0
        scene_time = 0
        for task in self.tasks:
            if current_time <= 0:
                log_lines.append("  - 剩余时间不足，无法继续任务！")
                break
            chosen_option, stress_change, time_cost = task.make_choice()
            log_lines.append(f"任务: {task.description} -> 选择: {chosen_option} "
                             f"(压力变化: {stress_change:.2f}, 时间消耗: {time_cost} 小时)")
            scene_stress += stress_change
            scene_time += time_cost
            current_time -= time_cost
        log_lines.append(f"场景 {self.name}结束，总压力变化: {scene_stress:.2f}, 总时间消耗: {scene_time} 小时")
        log_lines.append("")
        return scene_stress, current_time

# ================= 特殊场景类：PartyScene =================
class PartyScene(Scene):
    def play_scene(self, current_stress, current_time, log_lines):
        global IS_PARTY
        log_lines.append(f"=== 进入场景：{self.name} ===")
        scene_stress = 0
        scene_time = 0
        for task in self.tasks:
            if current_time <= 0:
                log_lines.append("  - 剩余时间不足，无法继续任务！")
                break
            chosen_option, stress_change, time_cost = task.make_choice()
            log_lines.append(f"任务: {task.description} -> 选择: {chosen_option} "
                             f"(压力变化: {stress_change:.2f}, 时间消耗: {time_cost} 小时)")
            if "朋友邀约" in task.description and "欣然赴约" in chosen_option:
                IS_PARTY = True
                log_lines.append("  -> 已答应赴约，IS_PARTY 置为 True")
            scene_stress += stress_change
            scene_time += time_cost
            current_time -= time_cost
        log_lines.append(f"场景 {self.name}结束，总压力变化: {scene_stress:.2f}, 总时间消耗: {scene_time} 小时")
        log_lines.append("")
        return scene_stress, current_time

# ================= 特殊短信任务类 =================
# ================= 特殊短信任务类 =================
class SMSTask:
    def __init__(self, index, importance=1, a=SMS_a, b=SMS_b):
        self.description = f"老板短信 {index}"
        self.options = {"A. 接受短信": {"time_cost": 0, "prob": 1}}
        self.importance = importance
        self.index = index
        self.a = a
        self.b = b
        self.active = False
        self.assigned_V = None  # 保存全局分配的目标方差

    def auto_set_stress(self, V):
        self.assigned_V = V  # 保存目标方差
        base = self.a + (self.index - 1) * self.b
        if base == 0:
            computed = 0
        else:
            k = math.sqrt(V) / abs(base)
            computed = k * base
        self.options["A. 接受短信"]["stress_change"] = computed if self.active else 0

    def make_choice(self, relieve=False):
        stress_change = self.options["A. 接受短信"]["stress_change"]
        if relieve and stress_change != 0:
            if random.random() < RELIEVE_PROB:
                relief = stress_change * RELIEVE_RATIO
                stress_change -= relief
        return "老板短信", stress_change, 0



# ================= 场景五：下班后加班 =================
def build_overtime_tasks():
    """
    构建场景五的特殊任务：
      1. 回复短信决策任务（普通 Task）
      2. 4个 SMSTask（老板短信），总共存在4个，但稍后随机激活2~4个。
    返回列表。
    """
    reply_task = Task(
        "加班短信回复",
        {
            "A. 回复": {"time_cost": 0.5, "prob": 0.5},
            "B. 不回复": {"time_cost": 0.5, "prob": 0.5}
        },
        importance=2
    )
    # 4个短信任务，重要性各设为1
    sms_tasks = [SMSTask(i, importance=1) for i in range(1, 5)]
    return [reply_task] + sms_tasks

def play_scene5(overtime_tasks, current_time, log_lines, is_party):
    """
    场景五：下班后加班，融入全局任务计算：
      - 执行“回复短信决策”任务（位于 overtime_tasks 的第一个元素）
      - 对剩下的 SMSTask（老板短信）直接使用传入的任务列表，
        这里任务已全局分配好目标方差（assigned_V 不为 None）。
      - 根据是否回复和 is_party 状态调整短信任务压力；
      - 如果选择回复，则以 RELIEVE_PROB 的概率缓解部分压力。
    """
    log_lines.append("=== 进入场景：下班后加班 ===")
    scene_stress = 0
    scene_time = 0

    # 第一步：执行回复短信决策任务（普通 Task）
    reply_task = overtime_tasks[0]
    # 此处 reply_task 已在全局分配时调用了 auto_set_stress
    reply_choice, reply_stress, reply_time = reply_task.make_choice()
    log_lines.append(f"任务: {reply_task.description} -> 选择: {reply_choice} "
                     f"(压力变化: {reply_stress:.2f}, 时间消耗: {reply_time} 小时)")
    scene_stress += reply_stress
    scene_time += reply_time
    current_time -= reply_time
    reply = True if "回复" in reply_choice else False

    # 第二步：对短信任务进行处理。overtime_tasks[1:] 为 4 个 SMSTask
    # 随机决定激活的短信条数（2~4条）
    sms_count = random.randint(2, 4)
    log_lines.append(f"随机激活老板短信条数：{sms_count}")
    for i, sms_task in enumerate(overtime_tasks[1:], start=1):
        sms_task.active = (i <= sms_count)
        # 重新调用 auto_set_stress，传入该任务已分配好的目标方差
        sms_task.auto_set_stress(sms_task.assigned_V)
    # 遍历短信任务，打印计算结果并根据 is_party 调整
    for sms_task in overtime_tasks[1:]:
        log_lines.append(f"{sms_task.description} (active={sms_task.active})：计算后压力变化 = {sms_task.options['A. 接受短信'].get('stress_change', 0):.2f}")
        if is_party and sms_task.active:
            original = sms_task.options["A. 接受短信"]["stress_change"]
            sms_task.options["A. 接受短信"]["stress_change"] = original * SMS_PARTY_FACTOR
            log_lines.append(f"  因已赴约，上调后压力变化 = {sms_task.options['A. 接受短信']['stress_change']:.2f}")
    # 累加短信任务的压力变化（并考虑回复时的缓解）
    sms_total = 0
    for sms_task in overtime_tasks[1:]:
        stress = sms_task.make_choice(relieve=reply)[1]
        sms_total += stress
    log_lines.append(f"场景五短信任务累计压力变化 = {sms_total:.2f}")
    scene_stress += sms_total

    log_lines.append(f"场景 五：下班后加班结束，总压力变化: {scene_stress:.2f}")
    log_lines.append("")
    return scene_stress, current_time


# ================= 主仿真函数 =================
def run_single_simulation(desired_mean=DESIRED_MEAN, desired_std=DESIRED_STD):
    """
    运行单次仿真，返回累计压力（最终得分 = desired_mean + 累计压力）。
    普通任务与特殊分支任务均参与全局重要性计算，目标方差根据各任务 importance 分配。
    """
    initial_stress = 0
    current_time = 999  # 足够大

    global IS_PARTY
    IS_PARTY = False

    log_lines = []

    # ----------------- 场景一：出门上班 -----------------
    task_1 = Task(
        "是否吃早餐",
        {
            "A. 吃": {"time_cost": 0.5, "prob": 0.8},
            "B. 不吃": {"time_cost": 0.25, "prob": 0.2}
        },
        importance=1
    )
    scene1 = Scene("场景一：出门上班", [task_1])

    # ----------------- 场景二：老板骂人 -----------------
    task_2 = Task(
        "老板无理由斥责",
        {
            "A. 默默承受": {"time_cost": 0.5, "prob": 0.5},
            "B. 表达不满": {"time_cost": 0.5, "prob": 0.5}
        },
        importance=1
    )
    scene2 = Scene("场景二：老板骂人", [task_2])

    # ----------------- 场景三：开始工作（动态任务生成） -----------------
    base_task1 = Task(
        "重复高压工作 1",
        {
            "A. 任务完成！": {"time_cost": 1, "prob": 0.5},
            "B. 任务失败！": {"time_cost": 1, "prob": 0.5}
        },
        importance=1
    )
    base_task2 = Task(
        "重复高压工作 2",
        {
            "A. 任务完成！": {"time_cost": 1, "prob": 0.5},
            "B. 任务失败！": {"time_cost": 1, "prob": 0.5}
        },
        importance=1
    )
    tasks_scene3 = [base_task1, base_task2]
    # 额外任务（每个以50%概率加入，最多2个）
    if random.random() < 0.5:
        extra_task = Task(
            "重复高压工作 3",
            {
                "A. 任务完成！": {"time_cost": 1, "prob": 0.5},
                "B. 任务失败！": {"time_cost": 1, "prob": 0.5}
            },
            importance=1
        )
        tasks_scene3.append(extra_task)
    if random.random() < 0.5:
        extra_task = Task(
            "重复高压工作 4",
            {
                "A. 任务完成！": {"time_cost": 1, "prob": 0.5},
                "B. 任务失败！": {"time_cost": 1, "prob": 0.5}
            },
            importance=1
        )
        tasks_scene3.append(extra_task)
    scene3 = Scene("场景三：开始工作", tasks_scene3)

    # ----------------- 场景四：下班后，朋友聚餐 -----------------
    party_task = Task(
        "朋友邀约",
        {
            "A. 欣然赴约": {"time_cost": 1, "prob": 0.5},
            "B. 先不去": {"time_cost": 1, "prob": 0.5}
        },
        importance=3
    )
    scene4 = PartyScene("场景四：下班后，朋友聚餐", [party_task])

    # ----------------- 场景五：下班后加班 -----------------
    overtime_tasks = build_overtime_tasks()  # 返回列表：[reply_task, sms_task1, sms_task2, sms_task3, sms_task4]
    scene5 = Scene("场景五：下班后加班", overtime_tasks)

    # ----------------- 场景六：一天结束，睡前 -----------------
    scene6 = Scene("场景六：一天结束，睡前", [])
    # ----------------- 场景七：Ending -----------------
    scene7 = Scene("场景七：Ending", [])

    # 将所有场景组合（场景5为普通场景，这里后续用特殊函数处理其逻辑）
    scenes = [scene1, scene2, scene3, scene4, scene5]
    total_importance = sum(task.importance for scene in scenes for task in scene.tasks)
    for scene in scenes:
        for task in scene.tasks:
            V_i = (task.importance / total_importance) * (desired_std ** 2)
            if isinstance(task, SMSTask):
                task.auto_set_stress(V_i)
            else:
                task.auto_set_stress(V_i)

    # 依次执行场景1-4
    cumulative_stress = initial_stress
    for scene in [scene1, scene2, scene3, scene4]:
        scene_stress, current_time = scene.play_scene(cumulative_stress, current_time, log_lines)
        cumulative_stress += scene_stress

    # 执行场景5：下班后加班，特殊逻辑封装在 play_scene5 中
    scene5_stress, current_time = play_scene5(scene5.tasks, current_time, log_lines, IS_PARTY)
    cumulative_stress += scene5_stress

    # 场景六：结局判定
    log_lines.append("=== 进入场景：一天结束，睡前 ===")
    log_lines.append(f"累计压力为 {cumulative_stress:.2f}")
    if cumulative_stress > 100:
        log_lines.append("结局：坏结局")
    else:
        log_lines.append("结局：好结局")
    log_lines.append("场景 六结束\n")
    # 场景七：Ending
    log_lines.append("=== 进入场景：Ending ===")
    log_lines.append("重置每日基础压力，进入下一日（模拟结束）")
    log_lines.append("场景 七结束\n")

    final_score = desired_mean + cumulative_stress
    log_lines.append(f"最终累计压力: {cumulative_stress:.2f}, 最终得分: {final_score:.2f}")

    for line in log_lines:
        print(line)

    return cumulative_stress, scenes

def print_tasks_stress_info(scenes):
    """
    遍历所有场景中的任务，打印每个任务各选项对应的压力变化信息
    """
    print("\n===== 每个任务的压力值变化 =====")
    for scene in scenes:
        print(f"【场景：{scene.name}】")
        for task in scene.tasks:
            print(f"任务: {task.description} (重要性: {task.importance})")
            for option, data in task.options.items():
                stress_change = data.get("stress_change", None)
                if stress_change is not None:
                    print(f"  {option} -> 压力变化: {stress_change:.2f}")
                else:
                    print(f"  {option} -> 未设置压力变化")
            print("")
    print("=================================\n")

def run_simulations_and_plot(simulation_rounds=1000, desired_mean=DESIRED_MEAN, desired_std=DESIRED_STD):
    """
    运行 simulation_rounds 次仿真，记录累计压力并绘制直方图，
    同时输出所有任务的压力变化信息。
    """
    results = []
    # 先执行一次单次仿真以获取场景和任务信息（用于打印）
    _, scenes = run_single_simulation(desired_mean, desired_std)
    for _ in range(simulation_rounds):
        stress, _ = run_single_simulation(desired_mean, desired_std)
        results.append(stress)
    plt.figure(figsize=(8,6))
    plt.hist(results, bins=30, edgecolor='black')
    plt.xlabel("累计压力")
    plt.ylabel("次数")
    plt.title(f"{simulation_rounds} 次仿真累计压力分布")
    plt.axvline(x=0, color='red', linestyle='dashed', linewidth=1, label="理论期望0")
    plt.legend()
    plt.tight_layout()
    plt.savefig("simulation_results.png")
    plt.show()
    print("绘图已保存为 simulation_results.png")
    print_tasks_stress_info(scenes)

if __name__ == "__main__":
    run_simulations_and_plot(simulation_rounds=100000, desired_mean=150, desired_std=25)
