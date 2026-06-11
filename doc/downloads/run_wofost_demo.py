# Part 1 Demo: WOFOST 7.2 冬小麦 水限生产 (内置 Demo 数据库)
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/run_wofost_demo.py
import warnings
warnings.filterwarnings('ignore')

import pcse

# 启动 WOFOST — 冬小麦, 西班牙 Sevilla, 2000年, 水限
print("WOFOST 7.2 冬小麦 水限生产 (Demo 数据库)")
print(f"地点: lat=37.64, lon=-6.09 (西班牙 Sevilla)")
print(f"天气: CGMS MARS 网格数据 (1999-12 → 2001-01)")
print()

w = pcse.start_wofost(grid=31031, crop=1, year=2000, mode='wlp')
w.run_till_terminate()

output = w.get_output()
final  = output[-1]
summary = w.get_summary_output()[0]

print('=' * 55)
print('  逐日输出结果')
print('=' * 55)
print(f'  模拟天数: {len(output)}  起始: {output[0]["day"]}  结束: {final["day"]}')
print(f'  发育阶段 DVS:      {final["DVS"]:.3f}')
print(f'  总地上生物量 TAGP:  {final["TAGP"]:,.0f} kg/ha')
print(f'  籽粒产量 TWSO:     {final["TWSO"]:,.0f} kg/ha')
print(f'  叶片干重 TWLV:     {final["TWLV"]:,.0f} kg/ha')
print(f'  茎秆干重 TWST:     {final["TWST"]:,.0f} kg/ha')
print(f'  根系干重 TWRT:     {final["TWRT"]:,.0f} kg/ha')
print(f'  最大叶面积 LAI_max: {max(d["LAI"] or 0 for d in output):.2f}')
print(f'  最大根深 RD:        {final["RD"]:.1f} cm')
print(f'  最终土壤水分 SM:    {final["SM"]:.4f}')
print(f'  水分胁迫 RFTRA:     {final["RFTRA"]:.4f} (1=无胁迫)')

print()
print('=' * 55)
print('  全季摘要输出')
print('=' * 55)
for k, v in summary.items():
    print(f'  {k:8s}: {v}')
