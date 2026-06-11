# PCSE 三套 Demo 一键运行 + 对比输出
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/run_all_demos.py
import os, sys, warnings
warnings.filterwarnings('ignore')

BASE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.dirname(BASE))

results = {}

# ============================================================
# Part 1: WOFOST + Demo 数据库
# ============================================================
print('=' * 60)
print('  正在运行 Part 1: WOFOST 冬小麦 (Demo 数据库)')
print('=' * 60)
import pcse
w1 = pcse.start_wofost(grid=31031, crop=1, year=2000, mode='wlp')
w1.run_till_terminate()
out1 = w1.get_output()
results['Part1'] = {
    'name': 'WOFOST + Demo DB 冬小麦 (西班牙)',
    'days': len(out1), 'start': out1[0]['day'], 'end': out1[-1]['day'],
    'DVS': out1[-1]['DVS'], 'TAGP': out1[-1]['TAGP'], 'TWSO': out1[-1]['TWSO'],
    'LAI_max': max(d['LAI'] or 0 for d in out1), 'SM': out1[-1]['SM'],
}

# ============================================================
# Part 2: WOFOST + NASA 天气 + 本地 CABO 文件
# ============================================================
print('\n正在从 NASA Power 拉取天气数据...')
from pcse.input import NASAPowerWeatherDataProvider, CABOFileReader, YAMLAgroManagementReader, WOFOST72SiteDataProvider
from pcse.base import ParameterProvider
from pcse.models import Wofost72_WLP_CWB

data2 = os.path.join(BASE, 'quickstart_part2')
wdp2  = NASAPowerWeatherDataProvider(latitude=52, longitude=5)
params2 = ParameterProvider(
    cropdata=CABOFileReader(os.path.join(data2, 'sug0601.crop')),
    soildata=CABOFileReader(os.path.join(data2, 'ec3.soil')),
    sitedata=WOFOST72SiteDataProvider(WAV=10))
agro2 = YAMLAgroManagementReader(os.path.join(data2, 'sugarbeet_calendar.agro'))

print('=' * 60)
print('  正在运行 Part 2: WOFOST 糖用甜菜 (NASA 天气)')
print('=' * 60)
w2 = Wofost72_WLP_CWB(params2, wdp2, agro2)
w2.run_till_terminate()
out2 = w2.get_output()
results['Part2'] = {
    'name': 'WOFOST + NASA 甜菜 (荷兰)',
    'days': len(out2), 'start': out2[0]['day'], 'end': out2[-1]['day'],
    'DVS': out2[-1]['DVS'], 'TAGP': out2[-1]['TAGP'], 'TWSO': out2[-1]['TWSO'],
    'LAI_max': max(d['LAI'] or 0 for d in out2), 'SM': out2[-1]['SM'],
}

# ============================================================
# Part 3: LINTUL3 + Excel 实测天气
# ============================================================
print('\n' + '=' * 60)
print('  正在运行 Part 3: LINTUL3 春小麦 (Excel 实测天气)')
print('=' * 60)
from pcse.input import PCSEFileReader, ExcelWeatherDataProvider
from pcse.models import LINTUL3

data3 = os.path.join(BASE, 'quickstart_part3')
params3 = ParameterProvider(
    cropdata=PCSEFileReader(os.path.join(data3, 'lintul3_springwheat.crop')),
    soildata=PCSEFileReader(os.path.join(data3, 'lintul3_springwheat.soil')),
    sitedata=PCSEFileReader(os.path.join(data3, 'lintul3_springwheat.site')))
wdp3  = ExcelWeatherDataProvider(os.path.join(data3, 'nl1.xlsx'))
agro3 = YAMLAgroManagementReader(os.path.join(data3, 'lintul3_springwheat.agro'))

w3 = LINTUL3(params3, wdp3, agro3)
w3.run_till_terminate()
out3 = w3.get_output()
results['Part3'] = {
    'name': 'LINTUL3 + Excel 春小麦 (荷兰)',
    'days': len(out3), 'start': out3[0]['day'], 'end': out3[-1]['day'],
    'DVS': out3[-1]['DVS'], 'TAGBM': out3[-1]['TAGBM'], 'WSO': out3[-1]['WSO'],
}

# ============================================================
# 对比汇总
# ============================================================
print('\n')
print('╔' + '═' * 58 + '╗')
print('║  三套 Demo 对比汇总' + ' ' * 38 + '║')
print('╠' + '═' * 58 + '╣')

headers = ['', 'Part 1', 'Part 2', 'Part 3']
rows = [
    ('模型', 'WOFOST 7.2', 'WOFOST 7.2', 'LINTUL3'),
    ('生产层级', '水限 WLP', '水限 WLP', '氮+水双限 NWLP'),
    ('作物', '冬小麦', '糖用甜菜', '春小麦'),
    ('地点', '西班牙 Sevilla', '荷兰 Wageningen', '荷兰 Wageningen'),
    ('天气', 'CGMS 数据库', 'NASA Power 在线', '本地 Excel 实测'),
    ('模拟天数', str(results['Part1']['days']), str(results['Part2']['days']), str(results['Part3']['days'])),
    ('日期范围', f'{results["Part1"]["start"]}→{results["Part1"]["end"]}',
                f'{results["Part2"]["start"]}→{results["Part2"]["end"]}',
                f'{results["Part3"]["start"]}→{results["Part3"]["end"]}'),
    ('DVS (发育阶段)', f'{results["Part1"]["DVS"]:.2f}', f'{results["Part2"]["DVS"]:.2f}', f'{results["Part3"]["DVS"]:.2f}'),
]

# Calc column widths
for label, p1, p2, p3 in rows:
    print(f'║  {label:<15s} │ {str(p1):>16s} │ {str(p2):>16s} │ {str(p3):>16s} ║')

print('╠' + '═' * 58 + '╣')
print(f'║  产量指标' + ' ' * 49 + '║')
p1_yield = f'籽粒 TWSO={results["Part1"]["TWSO"]:,.0f} kg/ha'
p2_yield = f'籽粒 TWSO={results["Part2"]["TWSO"]:,.0f} kg/ha'
p3_yield = f'籽粒 WSO={results["Part3"]["WSO"]:,.0f} kg/ha'
print(f'║  {p1_yield:<40s} ║')
print(f'║  {p2_yield:<40s} ║')
print(f'║  {p3_yield:<40s} ║')
print('╚' + '═' * 58 + '╝')
