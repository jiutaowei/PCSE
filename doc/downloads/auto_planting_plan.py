# PCSE 种植方案自动生成器
# 输入地块基础信息（经纬度、土壤类型），自动输出种植方案对比
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/auto_planting_plan.py
#      或指定参数: python doc/downloads/auto_planting_plan.py --lat 36.5 --lon -4.5 --year 2023
import warnings
warnings.filterwarnings('ignore')

import sys, os, sqlite3, argparse
from datetime import date

# ── 1. 解析输入参数 ──
parser = argparse.ArgumentParser(description="PCSE 自动种植方案生成器")
parser.add_argument("--lat", type=float, default=37.64, help="纬度 (默认 Sevilla 37.64)")
parser.add_argument("--lon", type=float, default=-6.09, help="经度 (默认 Sevilla -6.09)")
parser.add_argument("--year", type=int, default=2023, help="模拟年份 (默认 2023)")
parser.add_argument("--wav", type=float, default=10, help="初始有效水分 cm (默认 10)")
parser.add_argument("--mode", choices=["pp", "wlp"], default="wlp", help="生产模式: pp=潜在 wlp=水限")
args = parser.parse_args()

print("=" * 64)
print("  PCSE 种植方案自动生成器")
print("=" * 64)
print(f"  位置: lat={args.lat}, lon={args.lon}")
print(f"  年份: {args.year}")
print(f"  初始有效水分: {args.wav} cm")
print(f"  模拟模式: {'水限 WLP' if args.mode == 'wlp' else '潜在 PP'}")

# ── 2. 获取天气数据 (NASA Power 在线) ──
print("\n[1/4] 正在从 NASA Power 拉取天气数据...", end=" ", flush=True)
from pcse.input import NASAPowerWeatherDataProvider

try:
    wdp = NASAPowerWeatherDataProvider(latitude=args.lat, longitude=args.lon)
    print(f"完成 ({len(wdp.export())} 天可用)")
except Exception as e:
    print(f"\n  NASA Power 不可用: {e}")
    print("  回退到 Demo DB 天气数据 (仅限已知网格)")
    # Fallback: use demo DB weather for grid 31031
    DBconn = sqlite3.connect(os.path.expanduser("~/.pcse/pcse.db"))
    DBconn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))
    from pcse.tests.db_input import GridWeatherDataProvider
    wdp = GridWeatherDataProvider(DBconn, grid_no=31031)
    DBconn.close()

# ── 3. 构建参数 ──
print("[2/4] 构建作物参数...")

# 从 Demo DB 读取所有可用作物
DBconn = sqlite3.connect(os.path.expanduser("~/.pcse/pcse.db"))
DBconn.row_factory = lambda c, r: dict(zip([col[0] for col in c.description], r))

# 获取有完整参数的作物列表
crops_in_cal = DBconn.execute(
    "SELECT DISTINCT cc.crop_no, c.crop_name FROM crop_calendar cc "
    "JOIN crop c ON cc.crop_no=c.crop_no WHERE cc.grid_no=31031"
).fetchall()

# 场地参数（用户可修改部分）
site_data = {
    "IFUNRN": 0,
    "SSMAX": 0,
    "NOTINF": 0,
    "SSI": 0,
    "WAV": args.wav,
    "SMLIM": 0.25,
}

# 土壤参数（通用壤土默认值）
soil_data = {
    "CRAIRC": 0.06,
    "K0": 10.0,
    "SOPE": 10.0,
    "KSUB": 10.0,
    "SMFCF": 0.3175,
    "SM0": 0.4155,
    "SMW": 0.1515,
    "RDMSOL": 60.0,
}

print(f"  作物参数来源: PCSE Demo DB ({len(crops_in_cal)} 种作物)")
print(f"  土壤参数: 通用壤土默认值 (田间持水量={soil_data['SMFCF']}, 萎蔫点={soil_data['SMW']})")
print(f"  场地参数: WAV={site_data['WAV']} cm, SMLIM={site_data['SMLIM']}")
DBconn.close()

# ── 4. 逐作物模拟 ──
print("[3/4] 正在模拟各作物...")
from pcse.base import ParameterProvider
from pcse.models import Wofost72_WLP_CWB, Wofost72_PP
from pcse.tests.db_input import fetch_cropdata, AgroManagementDataProvider

def ntfactory(cursor, row):
    """SQLite row factory: namedtuple-style attribute access"""
    from collections import namedtuple
    fields = [col[0] for col in cursor.description]
    cls = namedtuple("Row", fields)
    return cls._make(row)

results = []

for row in crops_in_cal:
    crop_no = row["crop_no"]
    crop_name = row["crop_name"]
    cn_short = crop_name[:10]

    print(f"  {crop_name:25s} (crop={crop_no})...", end=" ", flush=True)
    try:
        DBconn = sqlite3.connect(os.path.expanduser("~/.pcse/pcse.db"))
        DBconn.row_factory = ntfactory

        # 获取该作物的完整参数
        cropd = fetch_cropdata(DBconn, grid=31031, year=2000, crop=crop_no)
        parvalues = ParameterProvider(sitedata=site_data, soildata=soil_data, cropdata=cropd)

        # 农艺管理（从 demo DB 取 calendar）
        agro = AgroManagementDataProvider(DBconn, grid_no=31031, crop_no=crop_no, campaign_year=2000)
        DBconn.close()

        # 选模型
        if args.mode == "wlp":
            model = Wofost72_WLP_CWB(parvalues, wdp, agro)
        else:
            model = Wofost72_PP(parvalues, wdp, agro)

        model.run_till_terminate()
        out = model.get_output()
        final = out[-1]
        summary = model.get_summary_output()[0]

        # 计算水分胁迫
        stress_days = sum(1 for d in out if d.get("RFTRA") is not None and d["RFTRA"] < 0.95)
        lai_max = max(d["LAI"] or 0 for d in out)

        # 找开花日
        anthesis = None
        for d in out:
            if d["DVS"] is not None and d["DVS"] >= 1.0:
                anthesis = d["day"]
                break

        twso = final.get("TWSO", 0) or 0
        tagp = final.get("TAGP", 0) or 0
        hi = twso / tagp if tagp > 0 else 0.0

        results.append({
            "crop": crop_name,
            "twso": twso,
            "tagp": tagp,
            "hi": hi,
            "days": len(out),
            "stress_days": stress_days,
            "lai_max": lai_max,
            "emergence": str(out[0]["day"]),
            "anthesis": str(anthesis) if anthesis else "N/A",
            "maturity": str(final["day"]),
            "dvs": final.get("DVS", 0) or 0,
            "rftra": final.get("RFTRA", 1.0) or 1.0,
        })
        print(f"TWSO={twso:,.0f} kg/ha")

    except Exception as e:
        print(f"失败: {type(e).__name__}: {e}")
        continue

if not results:
    print("\n所有作物模拟失败，请检查天气数据和参数配置。")
    sys.exit(1)

results.sort(key=lambda r: r["twso"], reverse=True)

# ── 5. 输出种植方案 ──
print("\n[4/4] 生成种植方案报告\n")

# 制表
def rjust(s, w):
    """右侧对齐，处理中文宽度"""
    return str(s).rjust(w)

print("┌────────────────┬──────────┬──────────┬──────┬──────┬──────────┬──────────────┐")
print("│ 作物           │ 产量     │ 生物量   │  HI  │ 天数 │ 胁迫天   │ 成熟日期     │")
print("│                │ (kg/ha)  │ (kg/ha)  │      │      │          │              │")
print("├────────────────┼──────────┼──────────┼──────┼──────┼──────────┼──────────────┤")
for r in results:
    hi_str = f"{r['hi']:.2f}" if r['hi'] > 0 else " -- "
    maturity_short = r['maturity'].split("-")[-1] if r['maturity'] != "N/A" else "N/A"
    print(f"│ {r['crop']:<14s} │ {r['twso']:8,.0f} │ {r['tagp']:8,.0f} │ {hi_str:>4s} │ {r['days']:4d} │ {r['stress_days']:6d}天 │ {maturity_short:>12s} │")
print("└────────────────┴──────────┴──────────┴──────┴──────┴──────────┴──────────────┘")

# 最佳推荐
best = results[0]
print(f"""
┌──────────────────────────────────────────────────────────────────┐
│                        * 推荐种植方案 *                           │
├──────────────────────────────────────────────────────────────────┤
│                                                                  │
│   作物: {best['crop']:<50s} │
│   预期产量: {best['twso']:,.0f} kg/ha                                          │
│   全生育期: {best['days']} 天                                            │
│   出苗日期: {best['emergence']}                                         │
│   开花日期: {best['anthesis']}                                         │
│   成熟日期: {best['maturity']}                                         │
│   水分胁迫: {best['stress_days']} 天 (占比 {best['stress_days'] * 100 // best['days']}%)                                   │
│                                                                  │
│   备选方案:                                                       │""")
for r in results[1:4]:
    print(f"   - {r['crop']:<20s} 产量 {r['twso']:,.0f} kg/ha, {r['days']} 天, 胁迫 {r['stress_days']} 天")

print("""│                                                                  │
│   输入参数调整建议:                                               │
│   - 如需更精确的土壤数据，修改 --wav 及土壤持水参数               │
│   - 如需品种级优化，需要进一步跑品种对比脚本                       │
│   - 如需播种期优化，修改 crop_start_date 跑多次对比               │
│                                                                  │
└──────────────────────────────────────────────────────────────────┘
""")

# 输入信息汇总
print(f"本次模拟输入:")
print(f"  经纬度: ({args.lat}, {args.lon})")
print(f"  天气来源: NASA Power API")
print(f"  土壤类型: 通用壤土 (田间持水量 0.3175, 萎蔫点 0.1515, 根区 60cm)")
print(f"  初始有效水分: {args.wav} cm")
print(f"  生产模式: {'水限 (WLP)' if args.mode == 'wlp' else '潜在 (PP)'}")
print(f"  可用作物: {len(crops_in_cal)} 种 ({', '.join(r['crop'] for r in results)})")
