import random
import math
import matplotlib.pyplot as plt

# ===== 全局可调参数 =====
DESIRED_MEAN = 100
DESIRED_STD = 25

SMS_a = 5            # 第1条短信的基础压力
SMS_b = 3            # 每条短信比前一条多3
RELIEVE_PROB = 0.7   # 回复短信时有70%概率触发缓解
RELIEVE_RATIO = 0.2  # 缓解成功时减少20%压力
SMS_PARTY_FACTOR = 1.2  # 如果已赴约，则短信压力×1.2

# 我们可以把所有场景与任务的配置信息写在一个结构里：
SCENES = [
    {
        "name": "场景一：出门上班",
        "tasks": [
            {
                "name": "是否吃早餐",
                "appear_prob": 1.0,  # 一定出现
                "options": [
                    {"label": "A. 吃", "prob": 0.8, "time_cost": 0.5, "stress": 5},
                    {"label": "B. 不吃", "prob": 0.2, "time_cost": 0.25, "stress": -2}
                ]
            }
        ]
    },
    {
        "name": "场景二：老板骂人",
        "tasks": [
            {
                "name": "老板无理由斥责",
                "appear_prob": 1.0,
                "options": [
                    {"label": "A. 默默承受", "prob": 0.5, "time_cost": 0.5, "stress": 10},
                    {"label": "B. 表达不满", "prob": 0.5, "time_cost": 0.5, "stress": 15}
                ]
            }
        ]
    },
    {
        "name": "场景三：开始工作",
        "tasks": [
            {
                "name": "重复高压工作 1",
                "appear_prob": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1, "stress": 8},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1, "stress": 15}
                ]
            },
            {
                "name": "重复高压工作 2",
                "appear_prob": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1, "stress": 6},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1, "stress": 12}
                ]
            },
            # 3.3 额外任务 (50%出现)
            {
                "name": "重复高压工作 3",
                "appear_prob": 0.5,  # 50%
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1, "stress": 5},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1, "stress": 9}
                ]
            },
            # 3.4 额外任务 (50%出现)
            {
                "name": "重复高压工作 4",
                "appear_prob": 0.5,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1, "stress": 5},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1, "stress": 9}
                ]
            },
        ]
    },
    {
        "name": "场景四：下班后，朋友聚餐",
        "tasks": [
            {
                "name": "朋友邀约",
                "appear_prob": 1.0,
                "options": [
                    {"label": "A. 欣然赴约", "prob": 0.5, "time_cost": 1, "stress": 3},
                    {"label": "B. 先不去",   "prob": 0.5, "time_cost": 1, "stress": -1}
                ]
            }
        ]
    },
    # 场景五：下班后加班，采用自定义处理
]

def run_single_day():
    """
    按顺序执行场景1~4，之后执行场景5（加班短信），再做场景6(结局)和7(Ending)。
    返回最终压力值。
    """
    log_lines = []
    current_stress = 0
    current_time = 999  # 大量可支配时间
    is_party = False    # 是否已答应聚餐

    # ============ 依次执行场景1~4 ============
    for scene_data in SCENES:
        scene_name = scene_data["name"]
        tasks_data = scene_data["tasks"]

        log_lines.append(f"=== 进入{scene_name} ===")
        scene_stress = 0
        scene_time = 0
        for tdata in tasks_data:
            # 先判断任务是否出现
            if random.random() < tdata["appear_prob"]:
                # 从options中抽选一个
                chosen_option = random.choices(
                    tdata["options"],
                    weights=[opt["prob"] for opt in tdata["options"]],
                    k=1
                )[0]
                # 更新压力与时间
                stress_change = chosen_option["stress"]
                time_cost = chosen_option["time_cost"]
                scene_stress += stress_change
                scene_time += time_cost
                current_time -= time_cost

                log_lines.append(
                    f"任务: {tdata['name']} -> 选择: {chosen_option['label']}"
                    f" (压力变化: {stress_change}, 时间消耗: {time_cost} 小时)"
                )
                # 如果是朋友邀约且选了“欣然赴约”，更新 is_party
                if tdata["name"] == "朋友邀约" and chosen_option["label"] == "A. 欣然赴约":
                    is_party = True
                    log_lines.append("  -> 已答应赴约 (is_party = True)")
            else:
                log_lines.append(f"任务: {tdata['name']} 未出现")

        current_stress += scene_stress
        log_lines.append(f"{scene_name}结束，总压力变化: {scene_stress}, 总时间消耗: {scene_time} 小时\n")

    # ============ 场景五：下班后加班 (特殊) ============
    scene_stress, current_time = play_overtime_scene(current_stress, current_time, log_lines, is_party)
    current_stress += scene_stress

    # ============ 场景六：一天结束，睡前 ============
    log_lines.append("=== 进入场景：一天结束，睡前 ===")
    log_lines.append(f"累计压力为 {current_stress:.2f}")
    if current_stress > 100:
        log_lines.append("结局：坏结局")
    else:
        log_lines.append("结局：好结局")
    log_lines.append("场景 六结束\n")

    # ============ 场景七：Ending ============
    log_lines.append("=== 进入场景：Ending ===")
    log_lines.append("重置每日基础压力，进入下一日（模拟结束）")
    log_lines.append("场景 七结束\n")

    final_score = DESIRED_MEAN + current_stress
    log_lines.append(f"最终累计压力: {current_stress:.2f}, 最终得分: {final_score:.2f}")

    # 输出日志
    for line in log_lines:
        print(line)

    return current_stress


def play_overtime_scene(current_stress, current_time, log_lines, is_party):
    """
    场景五：下班后加班
      - 先执行“加班短信回复”任务
      - 随后随机激活2~4条短信
      - 如果已赴约(is_party=True)，短信压力×1.2
      - 如果回复，则有概率减少 (RELIEVE_RATIO)
    """
    log_lines.append("=== 进入场景：下班后加班 ===")
    scene_stress = 0
    scene_time = 0

    # 任务5.1: 加班短信回复
    # 自定义选项
    reply_options = [
        {"label": "A. 回复", "prob": 0.5, "time_cost": 0.5, "stress": 5},
        {"label": "B. 不回复", "prob": 0.5, "time_cost": 0.5, "stress": 8}
    ]
    # 抽选加班短信回复
    choice = random.choices(reply_options, weights=[o["prob"] for o in reply_options], k=1)[0]
    scene_stress += choice["stress"]
    scene_time += choice["time_cost"]
    current_time -= choice["time_cost"]
    log_lines.append(f"任务: 加班短信回复 -> 选择: {choice['label']} (压力变化: {choice['stress']}, "
                     f"时间消耗: {choice['time_cost']} 小时)")

    replied = (choice["label"] == "A. 回复")

    # 老板短信 2~4 条
    sms_count = random.randint(2, 4)
    log_lines.append(f"随机激活老板短信条数：{sms_count}")
    total_sms_stress = 0
    for i in range(1, sms_count+1):
        base_stress = SMS_a + (i-1)*SMS_b
        # 如果已赴约 => 压力×1.2
        if is_party:
            base_stress *= SMS_PARTY_FACTOR
        # 如果已回复 => 有概率缓解
        if replied:
            if random.random() < RELIEVE_PROB:
                reduce_val = base_stress * RELIEVE_RATIO
                base_stress -= reduce_val

        log_lines.append(f"  第{i}条短信: 压力 = {base_stress:.2f}")
        total_sms_stress += base_stress

    scene_stress += total_sms_stress
    scene_time += 0  # 短信不额外消耗时间(可选)

    log_lines.append(f"场景 五：下班后加班结束，总压力变化: {scene_stress:.2f}\n")
    return scene_stress, current_time


# ============ 多次仿真并绘图 =============
def run_simulations_and_plot(rounds=1000):
    results = []
    for _ in range(rounds):
        final_stress = run_single_day()
        results.append(final_stress)

    # 绘制压力分布直方图
    import matplotlib.pyplot as plt
    plt.figure(figsize=(8,6))
    plt.hist(results, bins=30, edgecolor='black')
    plt.xlabel("累计压力")
    plt.ylabel("次数")
    plt.title(f"{rounds} 次仿真累计压力分布")
    plt.axvline(x=0, color='red', linestyle='dashed', linewidth=1, label="0 压力线")
    plt.legend()
    plt.tight_layout()
    plt.savefig("simulation_results.png")
    plt.show()
    print("绘图已保存为 simulation_results.png")


if __name__ == "__main__":
    # 运行多次仿真
    run_simulations_and_plot(rounds=10000)
