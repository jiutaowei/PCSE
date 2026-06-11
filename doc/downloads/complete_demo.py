# ============================================================
# PCSE 完整示例 — 输入数据定义 + 模拟运行
# 包含: 天气 / 土壤 / 场地 / 作物参数 / 品种参数 / 农事操作 / 模拟输出
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/complete_demo.py
# ============================================================
import warnings, os, json
warnings.filterwarnings('ignore')

from datetime import date
from pcse.input import (
    NASAPowerWeatherDataProvider,
    YAMLAgroManagementReader,
    WOFOST72SiteDataProvider,
)
from pcse.base import ParameterProvider
from pcse.models import Wofost72_WLP_CWB

BASE = os.path.dirname(os.path.abspath(__file__))

# ============================================================
# 1. 天气数据 — 从 NASA Power 在线拉取
# ============================================================
print("=" * 64)
print("  1. 天气数据 (NASA Power API)")
print("=" * 64)
print(f"  经纬度: lat=37.64, lon=-6.09 (西班牙 Sevilla)")
wdp = NASAPowerWeatherDataProvider(latitude=37.64, longitude=-6.09)
print(f"  可用天气记录: {len(wdp.export())} 天")
exported = wdp.export()
temps = [d["TMAX"] for d in exported if d.get("TMAX") is not None]
rains = [d["RAIN"] for d in exported if d.get("RAIN") is not None]
print(f"  温度范围: {min(temps):.0f} ~ {max(temps):.0f} C")
print(f"  年降雨量: {sum(rains):.0f} cm")

# 打印前5天天气作为示例
print(f"\n  示例天气记录 (前5天):")
print(f"  {'日期':>12s}  {'Tmax':>6s}  {'Tmin':>6s}  {'降雨':>6s}  {'辐射':>6s}")
for w in exported[:5]:
    print(f"  {w['DAY']}  {w['TMAX']:6.1f}  {w['TMIN']:6.1f}  {w['RAIN']:6.1f}  {w['IRRAD']/1e6:6.2f}")

# ============================================================
# 2. 土壤参数
# ============================================================
print(f"\n{'=' * 64}")
print(f"  2. 土壤参数 (通用壤土)")
print(f"{'=' * 64}")

soil_data = {
    "SMFCF": 0.3175,    # 田间持水量 (cm3/cm3)
    "SM0":   0.4155,    # 饱和含水量 (cm3/cm3)
    "SMW":   0.1515,    # 萎蔫点含水量 (cm3/cm3)
    "CRAIRC": 0.06,     # 临界空气含量 (cm3/cm3)
    "K0":    10.0,      # 饱和导水率 (cm/day)
    "SOPE":  10.0,      # 根区最大渗透率 (cm/day)
    "KSUB":  10.0,      # 底土最大渗透率 (cm/day)
    "RDMSOL": 60.0,     # 最大根区深度 (cm)
}

for k, v in soil_data.items():
    name_map = {
        "SMFCF": "田间持水量", "SM0": "饱和含水量", "SMW": "萎蔫点",
        "CRAIRC": "临界空气含量", "K0": "饱和导水率",
        "SOPE": "根区渗透率", "KSUB": "底土渗透率", "RDMSOL": "最大根深"
    }
    unit = "cm3/cm3" if k.startswith("S") or k == "CRAIRC" else ("cm/day" if k in ("K0","SOPE","KSUB") else "cm")
    print(f"  {k:8s} = {v:8.4f}  {name_map.get(k,'')} ({unit})")

# ============================================================
# 3. 场地参数
# ============================================================
print(f"\n{'=' * 64}")
print(f"  3. 场地参数")
print(f"{'=' * 64}")

site_data = {
    "IFUNRN": 0,    # 径流方案 (0=不计算地表径流)
    "SSMAX":  0,     # 最大地表蓄水 (cm)
    "NOTINF": 0,     # 非入渗比例 (0-1)
    "SSI":    0,     # 初始地表蓄水 (cm)
    "WAV":    10,    # 初始有效水分 (cm)
    "SMLIM":  0.25,  # 土壤水分下限 (cm3/cm3)
}

for k, v in site_data.items():
    desc = {
        "IFUNRN": "径流方案", "SSMAX": "最大地表蓄水", "NOTINF": "非入渗比例",
        "SSI": "初始地表蓄水", "WAV": "初始有效水分", "SMLIM": "土壤水分下限"
    }
    print(f"  {k:8s} = {v:8.2f}  {desc.get(k,'')}")

# ============================================================
# 4. 作物参数 (冬小麦)
#   从 Demo DB 提取，但显式列出完整参数集
# ============================================================
print(f"\n{'=' * 64}")
print(f"  4. 作物参数 (冬小麦 Winter Wheat)")
print(f"{'=' * 64}")

# 使用 demo DB 读取完整参数
import sqlite3, sys
sys.path.insert(0, os.path.join(BASE, '..', '..'))
from collections import namedtuple
def ntfactory(cursor, row):
    fields = [col[0] for col in cursor.description]
    return namedtuple("Row", fields)._make(row)

DBconn = sqlite3.connect(os.path.expanduser("~/.pcse/pcse.db"))
DBconn.row_factory = ntfactory

crop_params = {}  # Will hold all params

# 标量参数
scalar_params = [
    ("TBASEM", "出苗前基础温度", "C"),
    ("TBASE",  "出苗后基础温度", "C"),
    ("TEFFMX", "最高有效温度", "C"),
    ("TSUMEM", "播种→出苗积温", "C.d"),
    ("TSUM1",  "出苗→开花积温", "C.d"),
    ("TSUM2",  "开花→成熟积温", "C.d"),
    ("DVSI",   "初始发育阶段", "-"),
    ("DVSEND", "成熟发育阶段", "-"),
    ("TDWI",   "初始总干物重", "kg/ha"),
    ("LAIEM",  "出苗时LAI", "m2/m2"),
    ("RGRLAI", "LAI最大相对增长率", "C-1.d-1"),
    ("SLATB",  "比叶面积", "ha/kg"),
    ("SPA",    "根区最小有效水", "cm"),
    ("SPAN",   "生命周期吸氮量", "kg N/ha"),
    ("EFF",    "初始光能利用效率", "kg/ha.h/(J/m2.s)"),
    ("KDIF",   "散射光滑减系数", "-"),
    ("AMAXTB", "最大CO2同化速率", "kg/ha.h"),
    ("RDI",    "初始根深", "cm"),
    ("RRI",    "根深日最大增长", "cm/day"),
    ("RDMCR",  "最大根深", "cm"),
    ("CVL",    "叶片同化物转化效率", "kg/kg"),
    ("CVO",    "储存器官转化效率", "kg/kg"),
    ("CVR",    "根系转化效率", "kg/kg"),
    ("CVS",    "茎秆转化效率", "kg/kg"),
    ("Q10",    "呼吸温度系数", "-"),
    ("RML",    "叶片维持呼吸", "kg/kg.d"),
    ("RMO",    "储存器官维持呼吸", "kg/kg.d"),
    ("RMR",    "根系维持呼吸", "kg/kg.d"),
    ("RMS",    "茎秆维持呼吸", "kg/kg.d"),
    ("PERDL",  "叶片最大相对死亡率", "-"),
    ("RDRRTB", "根系相对死亡率表", "-"),
    ("RDRSTB", "茎秆相对死亡率表", "-"),
    ("FLTB",   "叶片分配系数表", "-"),
    ("FSTB",   "茎秆分配系数表", "-"),
    ("FOTB",   "储存器官分配系数表", "-"),
    ("FRTB",   "根系分配系数表", "-"),
    ("RFSETB", "根冠降低因子表", "-"),
    ("DTSMTB", "日均温影响系数表", "-"),
    ("TMNFTB", "最低温度影响表", "-"),
    ("TMPFTB", "霜冻致死温度表", "-"),
]

# Get params from DB
from pcse.tests.db_input import fetch_cropdata
cropd = fetch_cropdata(DBconn, grid=31031, year=2000, crop=1)

# Database has TSUMEM=0 for some crops which causes division-by-zero in emergence phase.
# Override with a reasonable value (winter wheat emergence typically needs 50-120 C.d).
if cropd.get("TSUMEM", 0) == 0:
    cropd["TSUMEM"] = 70.0
    print(f"  (TSUMEM 在DB中为0，已修正为 {cropd['TSUMEM']} C.d)")

print(f"  共 {len(cropd)} 个参数 (含标量和表格参数)")
print(f"\n  核心标量参数:")
for code, desc, unit in scalar_params[:20]:
    if code in cropd:
        val = cropd[code]
        if isinstance(val, (list, tuple)):
            val = f"[{len(val)}点表格]"
        else:
            val = f"{val:8.3f}"
        print(f"    {code:8s} = {val:>15s}  {desc} ({unit})")

print(f"  ... (其余标量+表格参数省略, 完整共{len(cropd)}个)")

# ============================================================
# 5. 农事操作 (YAML)
# ============================================================
print(f"\n{'=' * 64}")
print(f"  5. 农事操作")
print(f"{'=' * 64}")

agro_file = os.path.join(BASE, "complete_demo.agro")
# YAMLAgroManagementReader 内部默认编码不兼容中文注释，手动加载
import yaml
with open(agro_file, encoding='utf-8') as f:
    raw_agro = yaml.safe_load(f)['AgroManagement']
agro = type('AgroManagement', (list,), {})(raw_agro)

print(f"  文件: complete_demo.agro")
print(f"  活动数: {len(agro)}")
for i, campaign in enumerate(agro):
    start_date = list(campaign.keys())[0]
    events = campaign[start_date]
    cc = events.get('CropCalendar')
    if cc:
        print(f"  Activity {i+1}: {start_date}  {cc['crop_name']} "
              f"({cc['crop_start_type']} {cc['crop_start_date']}, "
              f"end={cc['crop_end_type']}, max={cc['max_duration']}d)")
        te = events.get('TimedEvents')
        if te:
            for t in te:
                cnt = len(t.get('events_table', []))
                print(f"           TimedEvents: {t.get('name','')} ({cnt} events)")
        se = events.get('StateEvents')
        if se:
            for s in se:
                cnt = len(s.get('events_table', []))
                print(f"           StateEvents: {s.get('name','')} "
                      f"(state={s['event_state']}, cond={s['zero_condition']}, {cnt} triggers)")
    else:
        print(f"  Activity {i+1}: {start_date}  [休耕/结束]")

# ============================================================
# 6. 组装参数 → 运行模拟
# ============================================================
print(f"\n{'=' * 64}")
print(f"  6. 运行模型 (WOFOST 7.2 水限 WLP)")
print(f"{'=' * 64}")

# 用 WOFOST72SiteDataProvider 处理场地参数
from pcse.input import WOFOST72SiteDataProvider as SiteProvider
# 直接传 dict 给 ParameterProvider
parvalues = ParameterProvider(sitedata=site_data, soildata=soil_data, cropdata=cropd)

model = Wofost72_WLP_CWB(parvalues, wdp, agro)
print(f"  模型初始化完成, 模拟从 {model.agromanager.start_date} 到 {model.agromanager.end_date}")
model.run_till_terminate()

output = model.get_output()
summary = model.get_summary_output()

# ============================================================
# 7. 输出结果
# ============================================================
print(f"\n{'=' * 64}")
print(f"  7. 模拟结果")
print(f"{'=' * 64}")

# Separate output by crop presence: find crop-active periods
def find_crop_growing_periods(output):
    """Find continuous periods where DVS > 0 (crop is actively growing)."""
    periods = []
    start = None
    for d in output:
        dvs = d.get("DVS") or 0
        if dvs > 0 and start is None:
            start = d
        elif dvs == 0 and start is not None:
            periods.append((start, d))
            start = None
    if start is not None:
        periods.append((start, output[-1]))
    return periods

crop_periods = find_crop_growing_periods(output)
# Build crop name mapping from agromanagement data (skip fallow campaigns)
crop_names = []
for campaign in raw_agro:
    start_date = list(campaign.keys())[0]
    camp = campaign[start_date]
    cc = camp.get('CropCalendar')
    if cc and cc.get('crop_name'):
        crop_names.append(cc['crop_name'])

sim_start = str(output[0]['day'])
sim_end = str(output[-1]['day'])

print(f"\n  模拟区间: {sim_start} -> {sim_end} ({len(output)} 天)")

# Per-campaign summary table
print(f"\n  {'─' * 80}")
print(f"  {'轮作季概览':^76s}")
print(f"  {'─' * 80}")
print(f"  {'作物(阶段)':<20s} {'播种':>12s} {'出苗':>12s} {'开花':>12s} {'成熟':>12s} {'产量':>10s}")
print(f"  {'─' * 80}")

for i, s in enumerate(summary):
    cn = crop_names[i] if i < len(crop_names) and crop_names[i] else f"休耕期{i+1}"
    dos = str(s.get("DOS", "")) or "N/A"
    doe = str(s.get("DOE", "")) or "N/A"
    doa = str(s.get("DOA", "")) or "N/A"
    dom = str(s.get("DOM", "")) or "N/A"
    twso = s.get("TWSO", 0) or 0
    tagp = s.get("TAGP", 0) or 0
    hi = twso / tagp if tagp > 0 else 0
    lai = s.get("LAIMAX", 0) or 0
    print(f"  {cn:<20s} {dos:>12s} {doe:>12s} {doa:>12s} {dom:>12s} {twso:>8,.0f} kg/ha")
    if twso > 0:
        print(f"  {'':20s}  {'生物量 TAGP':>12s}: {tagp:>8,.0f} kg/ha  HI: {hi:.2f}  LAImax: {lai:.2f}")
    print()

# 关键阶段快照
print(f"\n  逐日输出节选 (每30天):")
print(f"  {'Day':>12s}  {'DVS':>6s}  {'LAI':>6s}  {'TAGP':>8s}  {'TWSO':>8s}  {'SM':>6s}  {'RFTRA':>6s}")
for d in output[::30]:
    tagp = d.get("TAGP") or 0
    twso = d.get("TWSO") or 0
    sm = d.get("SM") or 0
    rftra = d.get("RFTRA") or 1.0
    lai = d.get("LAI") or 0
    dvs = d.get("DVS") or 0
    print(f"  {str(d['day']):>12s}  {dvs:6.3f}  {lai:6.2f}  {tagp:8,.0f}  {twso:8,.0f}  {sm:6.3f}  {rftra:6.3f}")

DBconn.close()
print(f"\n  完成。")
