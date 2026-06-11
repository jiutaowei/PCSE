# PCSE 种植方案对比器
# 基于数据库多作物/多品种模拟结果，输出种植方案建议
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/planting_advisor.py
import warnings
warnings.filterwarnings('ignore')

import pcse

print("=" * 62)
print("  PCSE 种植方案对比 — 基于 Grid 31031 (西班牙 Sevilla)")
print("=" * 62)

# ── 核心问题：如果我有这块地，种什么？怎么种？ ──
# 从数据库读取所有可用作物/品种，逐模拟对比。

crop_list = [
    (1, "冬小麦", "wlp"),
    (2, "玉米", "wlp"),
    (3, "春大麦", "wlp"),
    (7, "马铃薯", "wlp"),
    (10, "冬油菜", "wlp"),
    (11, "向日葵", "wlp"),
]

results = []

for crop_no, name_cn, mode in crop_list:
    print(f"\n正在模拟 {name_cn} (crop={crop_no})...", end=" ", flush=True)
    try:
        w = pcse.start_wofost(grid=31031, crop=crop_no, year=2000, mode=mode)
        w.run_till_terminate()
        out = w.get_output()
        final = out[-1]
        summary = w.get_summary_output()[0]

        # 提取关键指标
        emergence_day = out[0]["day"]
        maturity_day = final["day"]
        duration = len(out)
        dvs_final = final["DVS"]

        # 找开花日期 (DVS 首次 >= 1.0)
        anthesis_day = None
        for d in out:
            if d["DVS"] is not None and d["DVS"] >= 1.0:
                anthesis_day = d["day"]
                break

        # 水分胁迫评估 (RFTRA < 1.0 表示受胁迫)
        stress_days = sum(1 for d in out if d.get("RFTRA") is not None and d["RFTRA"] < 0.95)
        rftra_final = final.get("RFTRA", 1.0)

        results.append({
            "crop_name": name_cn,
            "crop_no": crop_no,
            "twso": final["TWSO"],  # 籽粒/储存器官产量
            "tagp": final["TAGP"],  # 总地上生物量
            "lai_max": max(d["LAI"] or 0 for d in out),
            "duration": duration,
            "emergence": emergence_day,
            "anthesis": anthesis_day,
            "maturity": maturity_day,
            "dvs": dvs_final,
            "stress_days": stress_days,
            "rftra": rftra_final,
            "hi": final["TWSO"] / final["TAGP"] if final["TAGP"] > 0 else 0,
        })
        print(f"完成 (产量={final['TWSO']:,.0f} kg/ha, {duration}天)")
    except Exception as e:
        print(f"失败: {e}")
        continue

# ── 对比输出 ──
if not results:
    print("\n无可用模拟结果")
    exit()

# 按产量排序
results.sort(key=lambda r: r["twso"], reverse=True)

print("\n")
print("╔" + "═" * 60 + "╗")
print("║" + "  种植方案对比报告 — Grid 31031, 2000 年 (水限 WLP)".center(50) + "║")
print("╠" + "═" * 60 + "╣")

# 表头
header = f"║ {'作物':8s} │ {'产量':>8s} │ {'生物量':>8s} │ {'HI':>4s} │ {'天数':>4s} │ {'胁迫天':>5s} ║"
sep = "╠" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 10 + "┼" + "─" * 6 + "┼" + "─" * 6 + "┼" + "─" * 7 + "╣"
print(header)
print(sep)

for r in results:
    line = f"║ {r['crop_name']:8s} │ {r['twso']:8,.0f} │ {r['tagp']:8,.0f} │ {r['hi']:.2f} │ {r['duration']:4d}天 │ {r['stress_days']:5d}天 ║"
    print(line)

print("╠" + "═" * 60 + "╣")

# 推荐
best = results[0]
print(f"║  ** 推荐方案 **".ljust(59) + "║")
print(f"║  作物: {best['crop_name']}".ljust(59) + "║")
print(f"║  预期产量: {best['twso']:,.0f} kg/ha".ljust(59) + "║")
print(f"║  生长期: {best['emergence']} → {best['maturity']}".ljust(59) + "║")
print(f"║  全生育期: {best['duration']} 天".ljust(59) + "║")
if best['anthesis']:
    print(f"║  开花期: {best['anthesis']}".ljust(59) + "║")
print("╚" + "═" * 60 + "╝")

# ── 种植方案详解 ──
print(f"""
┌─────────────────────────────────────────────────────────────┐
│                    种植方案建议详解                            │
├─────────────────────────────────────────────────────────────┤
│                                                             │
│  【地块信息】                                                │
│    位置: 西班牙 Sevilla (lat=37.64, lon=-6.09)               │
│    土壤: 单层 60cm, 田间持水量 0.3175, 萎蔫点 0.1515        │
│    初始有效水分: 10 cm                                       │
│                                                             │
│  【方案排序依据】                                            │
│    1. 籽粒产量 (TWSO) — 经济效益第一指标                     │
│    2. 收获指数 (HI) — 光合产物向收获器官的转化效率           │
│    3. 水分胁迫天数 — 反映灌溉需求和水风险                    │
│    4. 生育期长度 — 与后续轮作安排的兼容性                    │
│                                                             │
│  【数据库能力边界】                                          │
│    PCSE 能做:                                                │
│      [v] 多作物横向对比 (6 种作物, 238 个品种)               │
│      [v] 播种窗口优化 (改 crop_start_date 跑多场景)          │
│      [v] 品种筛选 (同作物不同 TSUM1/TSUM2 对比)              │
│      [v] 灌溉需求预估 (从水分胁迫天数和 RFTRA 推算)           │
│      [v] 关键物候期预测 (出苗->开花->成熟日期)               │
│                                                             │
│    PCSE 不能做的 (大田模型固有局限):                          │
│      [x] 施肥方案 (WOFOST 不计养分)                          │
│      [x] 病虫害预警 (无植保模块)                             │
│      [x] 市场价格/经济分析 (纯农学模型)                      │
│      [x] 实时调控建议 (离线模拟，非在线推理)                  │
│      [x] 温室环境控制 (开放大田假设, 非设施农业)             │
│                                                             │
│  【品种级优化示例】                                          │
│    数据库含 50 个冬小麦品种，TSUM1 (出苗→开花需积温)         │
│    从 518 到 852°C·d 不等。选择策略:                         │
│      - 早熟品种 (TSUM1<600): 避开后期干旱, 但产量偏低        │
│      - 晚熟品种 (TSUM1>800): 充分利用生长季, 但水分需求大    │
│      - 中熟品种 (600-750): 平衡产量与风险                     │
│    具体需根据品种级模拟对比确定最优。                         │
│                                                             │
└─────────────────────────────────────────────────────────────┘
""")
