# Part 3 Demo: LINTUL3 春小麦 氮+水双限
# 用法: cd D:\work\code\silicon1\pcse && python doc/downloads/run_lintul3.py
import os, warnings
warnings.filterwarnings('ignore')

from pcse.input import PCSEFileReader, ExcelWeatherDataProvider, YAMLAgroManagementReader
from pcse.base import ParameterProvider
from pcse.models import LINTUL3

data_dir = os.path.join(os.path.dirname(__file__), 'quickstart_part3')

crop   = PCSEFileReader(os.path.join(data_dir, 'lintul3_springwheat.crop'))
soil   = PCSEFileReader(os.path.join(data_dir, 'lintul3_springwheat.soil'))
site   = PCSEFileReader(os.path.join(data_dir, 'lintul3_springwheat.site'))
params = ParameterProvider(soildata=soil, cropdata=crop, sitedata=site)

wdp  = ExcelWeatherDataProvider(os.path.join(data_dir, 'nl1.xlsx'))
agro = YAMLAgroManagementReader(os.path.join(data_dir, 'lintul3_springwheat.agro'))

print('LINTUL3 春小麦 氮+水双限 运行中...')
model = LINTUL3(params, wdp, agro)
model.run_till_terminate()

output = model.get_output()
final = output[-1]

print(f'模拟: {len(output)}天  {output[0]["day"]} -> {final["day"]}')
print(f'DVS={final["DVS"]:.3f}  总生物量={final["TAGBM"]:.0f} kg/ha')
print(f'籽粒WSO={final["WSO"]:.0f}  死叶WLVD={final["WLVD"]:.0f}  活叶WLVG={final["WLVG"]:.0f}')
print(f'茎WST={final["WST"]:.0f}  根WRT={final["WRT"]:.0f}')
print(f'总蒸腾={final["TTRAN"]:.0f} mm  总降雨={final["TRAIN"]:.0f} mm')
