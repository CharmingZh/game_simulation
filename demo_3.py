import random
import math
import statistics
import matplotlib.pyplot as plt

# plt.rcParams["font.sans-serif"] = ["SimHei"]  # 使用黑体显示中文
plt.rcParams["axes.unicode_minus"] = False

# ===== 全局可调参数 =====
DESIRED_MEAN = 100
DESIRED_STD = 25

RELIEVE_PROB = 0.7  # 回复短信时有70%概率触发缓解
RELIEVE_RATIO = 0.2  # 缓解成功时减少20%压力
SMS_PARTY_FACTOR = 1.2  # 如果已赴约，则短信压力×1.2

# 1) SCENES: 每个任务用 'appear_prob','options'(每个选项 prob,time_cost),以及 var_ratio(重要性).
SCENES = [
    {
        "name": "场景一：出门上班",
        "tasks": [
            {
                "name": "是否吃早餐",
                "appear_prob": 1.0,  # 一定出现
                "var_ratio": 1.0,  # importance
                "options": [
                    {"label": "A. 吃", "prob": 0.8, "time_cost": 0.5},
                    {"label": "B. 不吃", "prob": 0.2, "time_cost": 0.25}
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
                "var_ratio": 1.0,
                "options": [
                    {"label": "A. 默默承受", "prob": 0.5, "time_cost": 0.5},
                    {"label": "B. 表达不满", "prob": 0.5, "time_cost": 0.5}
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
                "var_ratio": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1}
                ]
            },
            {
                "name": "重复高压工作 2",
                "appear_prob": 1.0,
                "var_ratio": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1}
                ]
            },
            # 3.3 额外任务 (50%出现)
            {
                "name": "重复高压工作 3",
                "appear_prob": 0.5,
                "var_ratio": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1}
                ]
            },
            # 3.4 额外任务 (50%出现)
            {
                "name": "重复高压工作 4",
                "appear_prob": 0.5,
                "var_ratio": 1.0,
                "options": [
                    {"label": "A. 任务完成！", "prob": 0.5, "time_cost": 1},
                    {"label": "B. 任务失败！", "prob": 0.5, "time_cost": 1}
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
                "var_ratio": 3.0,  # importance更高
                "options": [
                    {"label": "A. 欣然赴约", "prob": 0.5, "time_cost": 1},
                    {"label": "B. 先不去", "prob": 0.5, "time_cost": 1}
                ]
            }
        ]
    },
    # 场景五：下班后加班 => 近似为一个合并任务, 统一分配
    {
        "name": "场景五：下班后加班(合并)",
        "tasks": [
            {
                "name": "加班短信(合并)",
                # appear_prob=1 => 认为每天都可能进入加班场景
                "appear_prob": 1.0,
                # var_ratio可适度加大,表示其影响更大
                "var_ratio": 2.0,
                # 两选项: A= 回复, B= 不回复
                # prob=? (比如0.5)
                # time_cost=? 先随意0.5
                # “stress”由自动公式计算
                "options": [
                    {"label": "A. 回复", "prob": 0.5, "time_cost": 0.5},
                    {"label": "B. 不回复", "prob": 0.5, "time_cost": 0.5}
                ]
            }
        ]
    },
]


def auto_assign_stress_two_options(p_i, var_i):
    """
    给定选项A概率 p_i, 该任务出现时的方差 var_i.
    返回 (xA, xB), 使得 期望=0, Var= var_i.
      xA= + sqrt(var_i*(1-p_i)/p_i)
      xB= - sqrt(var_i*p_i/(1-p_i))
    """
    # 防止极端p=0或p=1
    if p_i < 1e-9 or p_i > 1 - 1e-9:
        return (0, 0)
    xA = math.sqrt(var_i * (1 - p_i) / p_i)
    xB = -math.sqrt(var_i * p_i / (1 - p_i))
    return (xA, xB)


def auto_set_stress_all_tasks(scenes, desired_std=25):
    """
    1) 汇总所有任务 => sum var_ratio => 根据 appear_prob, var_ratio 分配 var_i
    2) 用 auto_assign_stress_two_options() 计算 xA,xB
    3) 将结果写回 "stressA","stressB"
    """
    # 收集任务
    tasks = []
    for sc in scenes:
        for t in sc["tasks"]:
            tasks.append(t)
    sum_ratio = sum(t["var_ratio"] for t in tasks)
    # 计算 \sum_i r_i * Var_i = (desired_std)^2
    # => Var_i = ( var_ratio_i / sum_ratio ) * (desired_std^2 ) / r_i
    for t in tasks:
        r_i = t["appear_prob"]
        ratio = t["var_ratio"]
        # 任务只有2个选项 => pA= t["options"][0]["prob"]
        # (假定第1个选项是"A",第2是"B", sum=1.0)
        # compute local_var
        if r_i < 1e-9:
            # 不出现 => no stress
            for i, opt in enumerate(t["options"]):
                opt["stressA"] = 0
                opt["stressB"] = 0
            continue
        pA = t["options"][0]["prob"]
        local_var = (ratio / sum_ratio) * (desired_std ** 2) / r_i
        # xA, xB
        xA, xB = auto_assign_stress_two_options(pA, local_var)
        # 写回
        t["options"][0]["stress"] = xA
        t["options"][1]["stress"] = xB


def run_single_day():
    """
    按顺序执行场景1~5, 再结局(场景6,7)
    基础压力=100
    """
    log_lines = []
    current_stress = 0
    current_time = 999
    is_party = False

    # 依次执行场景1~5
    for sc_index, sc_data in enumerate(SCENES, start=1):
        sc_name = sc_data["name"]
        tasks = sc_data["tasks"]
        log_lines.append(f"=== 进入{sc_name} ===")
        scene_stress = 0
        scene_time = 0
        for tdata in tasks:
            # appear_prob
            if random.random() < tdata["appear_prob"]:
                # 二选一
                # 0 => A, 1 => B
                # weights= [ opt["prob"]... ]
                chosen_opt = random.choices(tdata["options"],
                                            weights=[o["prob"] for o in tdata["options"]],
                                            k=1)[0]
                sc_stress = chosen_opt["stress"]
                tcost = chosen_opt["time_cost"]
                scene_stress += sc_stress
                scene_time += tcost
                current_time -= tcost

                log_lines.append(f"任务:{tdata['name']} => {chosen_opt['label']} (压力:{sc_stress:.2f},耗时:{tcost}h)")

                # 如果是"朋友邀约"且选了"A.欣然赴约"
                if tdata["name"] == "朋友邀约" and chosen_opt["label"] == "A. 欣然赴约":
                    is_party = True
                    log_lines.append(" -> 已答应赴约 (is_party=True)")

                # 如果是"加班短信(合并)" 还可能细分 "回复/不回复", "2~4条", is_party => 这里仅近似:
                if tdata["name"] == "加班短信(合并)":
                    # 这里实际还可以做2~4条, multiply 1.2, etc.
                    # 但已经自动分配了, 纯粹做为"一次抽选"
                    # 如果想真实随机,可再加自定义
                    pass
            else:
                log_lines.append(f"任务:{tdata['name']} 未出现.")

        current_stress += scene_stress
        log_lines.append(f"{sc_name}结束, scene_stress={scene_stress:.2f}, scene_time={scene_time}\n")

    # ============ 场景6: 一天结束,睡前 => 结局
    log_lines.append("=== 进入场景：一天结束，睡前 ===")
    log_lines.append(f"累计压力={current_stress:.2f}")
    if current_stress > 100:
        log_lines.append("结局:坏结局")
    else:
        log_lines.append("结局:好结局")
    # 场景7: Ending
    log_lines.append("=== 进入场景：Ending ===\n")

    final_score = DESIRED_MEAN + current_stress
    log_lines.append(f"最终累计压力:{current_stress:.2f}, 最终得分:{final_score:.2f}")
    for line in log_lines:
        print(line)
    return current_stress


def run_simulations_and_plot(rounds=1000):
    results = []
    for _ in range(rounds):
        stress = run_single_day()
        results.append(stress)
    avg = statistics.mean(results)
    std = statistics.pstdev(results)
    c_in = sum(1 for r in results if 75 <= r <= 125)
    ratio_in = c_in / len(results) * 100
    print(f"{rounds}次仿真 => mean={avg:.2f}, std={std:.2f}, {ratio_in:.2f}%在[75,125]")
    # 绘制
    plt.figure(figsize=(8, 6))
    for i, _ in enumerate(results):
        results[i] += DESIRED_MEAN
    plt.hist(results, bins=30, edgecolor='black')
    plt.axvline(x=50, color='red', linestyle='--')
    plt.axvline(x=150, color='red', linestyle='--')
    plt.title(f"mean={avg:.2f}, std={std:.2f}, {ratio_in:.2f}% in [75,125]")
    plt.tight_layout()
    plt.savefig("simulation_results.png")
    plt.show()
    print("已保存 simulation_results.png")


# def run_simulations_and_plot(rounds=1000):
#     results = []
#     for _ in range(rounds):
#         final_stress = run_single_day()  # 假设这个函数返回单次模拟的最终压力
#         results.append(final_stress)
#
#     # 这里统计均值、标准差等可选
#     import statistics
#     mean_stress = statistics.mean(results)
#     std_stress = statistics.pstdev(results)
#
#     # ========= 把这段原先的直方图替换为散点图 ========
#     plt.figure(figsize=(8,6))
#
#     # x轴：模拟的索引；y轴：最终压力
#     x_values = range(len(results))  # [0,1,2,...,rounds-1]
#     plt.scatter(x_values, results, alpha=0.7, s=10)
#
#     plt.xlabel("Simulation Index")
#     plt.ylabel("Final Stress")
#     plt.title(f"散点图示例: rounds={rounds}, mean={mean_stress:.2f}, std={std_stress:.2f}")
#
#     # 如果想突出一些参考线，比如设100为理想值，可以加一条红线
#     plt.axhline(y=100, color='red', linestyle='dashed', linewidth=1, label="基准压力=100")
#
#     plt.legend()
#     plt.tight_layout()
#     plt.savefig("simulation_scatter.png")
#     plt.show()
#     print("散点图已保存为 simulation_scatter.png")



if __name__ == "__main__":
    # 1) 首先对SCENES中的所有任务做自动分配 => xA, xB
    auto_set_stress_all_tasks(SCENES, desired_std=DESIRED_STD)
    # 2) 多次仿真
    run_simulations_and_plot(rounds=5000)
