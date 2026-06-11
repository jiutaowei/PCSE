# 作物种植模型数据库设计

> 设计目标：数据库可完整支撑种植方案输出——从品种选择、播期确定、水肥管理到产量预测的全链路参数化。

---

## 目录

1. [设计原则](#1-设计原则)
2. [ER 总览](#2-er-总览)
3. [表结构详细设计](#3-表结构详细设计)
   - [A. 作物与品种](#a-作物与品种-crop--variety)
   - [B. 物候学](#b-物候学-phenology)
   - [C. 光合同化](#c-光合同化-assimilation)
   - [D. 干物质分配](#d-干物质分配-partitioning)
   - [E1. 叶片动态](#e1-叶片动态-leaf-dynamics)
   - [E2. 茎动态](#e2-茎动态-stem-dynamics)
   - [E3. 根系动态](#e3-根系动态-root-dynamics)
   - [E4. 贮存器官动态](#e4-贮存器官动态-storage-organ-dynamics)
   - [F. 维持呼吸](#f-维持呼吸-respiration)
   - [G. 蒸散与水分](#g-蒸散与水分-evapotranspiration)
   - [H. 转换效率 & 再分配](#h-转换效率--再分配-conversion-efficiencies--reallocation)
   - [I. 春化参数](#i-春化参数-vernalisation)
   - [J. 土壤](#j-土壤-soil)
   - [K. 气象](#k-气象-weather)
   - [L. 农事管理](#l-农事管理-agromanagement)
   - [M. 模型配置](#m-模型配置-model-configuration)
   - [N. 模拟结果](#n-模拟结果-simulation-results)
   - [O. 通用插值表 (Afgen)](#o-通用插值表-afgen)
   - [P. NPK 养分动态](#p-npk-养分动态-nutrient-dynamics)
   - [Q. SNOMIN 土壤碳氮平衡](#q-snomin-土壤碳氮平衡)
   - [R. 站点参数](#r-站点参数-site-parameters)
   - [S. 信号日志](#s-信号日志-signal-log)
   - [T. LINTUL3 专用参数](#t-lintul3-专用参数)
   - [U. ALCEPAS 洋葱模型参数](#u-alcepas-洋葱模型参数)
4. [种植方案生成流程](#4-种植方案生成流程)
5. [种子数据清单](#5-种子数据清单)
6. [附录：变量依赖关系图](#附录-变量依赖关系图)

---

## 数据表总览

| 分组 | 表名 | 说明 | 来源模块 |
|------|------|------|-----------|
| **A** | `crops` | 作物种类 (小麦/玉米/水稻…) | — |
| **A** | `varieties` | 品种 (FK → crops) | — |
| **B** | `phenology_parameters` | 物候发育参数 (TSUM1/TSUM2/IDSL…) | `crop/phenology.py` |
| **B** | `phenology_stages` | 生育期阶段定义 (出苗/营养/生殖/成熟) | — |
| **C** | `assimilation_parameters` | 光合同化参数 (AMAX/EFF/KDIF…) | `crop/assimilation.py` |
| **C** | `photosynthesis_constants` | 光合物理常数 (SCV/CH2O_CO2) | `crop/assimilation.py` |
| **D** | `partitioning_factors` | 干物质分配系数 (FR/FL/FS/FO per DVS) | `crop/partitioning.py` |
| **E1** | `leaf_dynamics_parameters` | 叶片动态 (RGRLAI/SPAN/SLATB/PERDL…) | `crop/leaf_dynamics.py` |
| **E2** | `stem_dynamics_parameters` | 茎动态 (RDRSTB/SSATB…) | `crop/stem_dynamics.py` |
| **E3** | `root_dynamics_parameters` | 根系动态 (RDI/RRI/RDMCR/RDRRTB…) | `crop/root_dynamics.py` |
| **E4** | `storage_organ_parameters` | 贮存器官动态 (SPA/TDWI) | `crop/storage_organ_dynamics.py` |
| **F** | `respiration_parameters` | 维持呼吸 (Q10/RMR/RML/RMS/RMO/RFSETB) | `crop/respiration.py` |
| **G** | `evapotranspiration_parameters` | 蒸散参数 (CFET/DEPNR/KDIFTB/IOX…) | `crop/evapotranspiration.py` |
| **H** | `conversion_efficiencies` | 同化物→器官转换效率 + 再分配 (CVL/CVO/CVR/CVS + REALLOC_*) | `crop/wofost72.py`, `crop/wofost81.py` |
| **I** | `vernalisation_parameters` | 春化参数 (VERNSAT/VERNBASE/VERNRTB/VERNDVS) | `crop/phenology.py` (IDSL≥2) |
| **J** | `soil_profiles` | 土壤类型 (含 pF 参数) | `soil/soil_profile.py` |
| **J** | `soil_layers` | 土壤层属性 (SMFCF/SMW/SM0/K0…) | `soil/soil_profile.py` |
| **J** | `soil_layer_afgen` | 土层↔水力特性插值表关联 (SMfromPF/CONDfromPF) | `soil/soil_profile.py` |
| **K** | `weather_stations` | 气象站点 (经纬度/海拔/ET模型) | `base/weather.py` |
| **K** | `weather_daily` | 逐日气象数据 (TMAX/TMIN/IRRAD/RAIN/ET0…) | `base/weather.py` |
| **L** | `sites` | 站点 (站点→气象站+土壤+CO₂浓度) | `conf/*.conf` |
| **L** | `planting_plans` | 种植计划 (品种/土壤/站点/起止日期) | `agromanager.py` |
| **L** | `timed_events` | 定时农事事件 (按日期灌溉/施肥) | `agromanager.py` → `TimedEventsDispatcher` |
| **L** | `state_events` | 状态事件 (零交叉: DVS/SM/NNI 阈值触发) | `agromanager.py` → `StateEventsDispatcher` |
| **L** | `snomin_fertilizer_events` | SNOMIN 有机肥事件 (C:N比/有机质比例/深度) | `soil/snomin.py` |
| **M** | `model_configurations` | 模型配置 (19种: PP/WLP/NWLP × FD/CWB/MLWB…) | `conf/*.conf` |
| **N** | `simulation_runs` | 模拟运行记录 (plan+config→status) | `engine.py` |
| **N** | `simulation_daily_output` | 逐日模拟输出 (DVS/LAI/TAGP/HI/NNI/NPKI/SNOMIN…) | `engine.py` → `_save_output()` |
| **N** | `simulation_summary_output` | 每季总结 (最终产量/收获指数/物候日期/N吸收) | `engine.py` → `_save_summary_output()` |
| **N** | `simulation_terminal_output` | 终端输出 (总蒸散/径流/渗漏/灌溉/降水) | `engine.py` → `_save_terminate_output()` |
| **O** | `afgen_tables` | Afgen 插值表元数据 (~40 张: DTSMTB/SLATB/KDIFTB…) | `util.py` → `Afgen` |
| **O** | `afgen_points` | Afgen 插值点 (X→Y 数据对) | `util.py` → `Afgen` |
| **P** | `npk_demand_uptake_parameters` | NPK 需求与吸收 (NMAX*/RNUPTAKEMAX/TCNT/DVS_NPK_STOP…) | `crop/nutrients/npk_demand_uptake.py` |
| **P** | `npk_stress_parameters` | NPK 胁迫 (NCRIT_FR/NLUE_NPK → NNI/PNI/KNI/NPKI/RFNPK) | `crop/nutrients/npk_stress.py` |
| **P** | `npk_translocation_parameters` | NPK 转运 (残留浓度/NPK_TRANSLRT_FR) | `crop/nutrients/npk_translocation.py` |
| **P** | `n_stress_parameters` | N 胁迫 — WOFOST 8.1 N only (NMAXLV_TB/NSLLV_TB…) | `crop/nutrients/n_stress.py` |
| **Q** | `snomin_parameters` | SNOMIN 全局 C/N 参数 (A0SOM/KDENIT_REF/KNIT_REF…) | `soil/snomin.py` |
| **Q** | `snomin_layer_initial` | SNOMIN 逐层初始 NH₄/NO₃ | `soil/snomin.py` |
| **R** | `classic_site_parameters` | 经典 WOFOST 站点参数 (IFUNRN/NOTINF/SSMAX/NAVAILI…) | `conf/*.conf` |
| **S** | `signal_log` | 信号日志 (crop_start/irrigate/apply_n/terminate…) | `engine.py` + `agromanager.py` |
| **T** | `lintul3_parameters` | LINTUL3 专用参数 (LUE/K/RGRL/NLAI/NLUE/TRANCO…) | `crop/lintul3.py` |
| **T** | `lintul3_partitioning_factors` | LINTUL3 分配系数表 (FLV/FRT/FSO/FST per DVS) | `crop/lintul3.py` |
| **U** | `alcepas_parameters` | ALCEPAS 洋葱参数 (ASRQ*/BOL50/FALL50/AGE系列/GTSLA…) | `crop/alcepas.py` |

> **共 43 张表，21 个分组 (A-U)**。参数表均以 `variety_id` 或 `site_id` 为外键关联到作物/站点；模拟输出表以 `run_id` 关联到模拟运行。

---

## 1. 设计原则

### 数据来源

全部参数定义来源于源码中的 ParamTemplate / StatesTemplate / RatesTemplate 类定义，保留原始命名、类型、单位和默认值。

### 核心抽象

| 源码概念 | 数据库映射 | 说明 |
|-----------|-----------|------|
| `ParamTemplate` | `*_parameters` 表 | 静态参数，品种/土壤一经确定即不变 |
| `StatesTemplate` | `simulation_daily_states` | 每日状态变量，模拟输出 |
| `RatesTemplate` | `simulation_daily_rates` | 每日速率变量，模拟输出 |
| `AfgenTrait` (插值表) | `afgen_tables` + `afgen_points` | X→Y 分段线性插值，统一存储 |
| `VariableKiosk` | 表间外键关联 | 模块间通过变量名关联（如 DVS, LAI, SM） |
| `SimulationObject` | `model_configurations` | 模块组合可配置 |
| `signal/dispatcher` | `signal_log` | 事件驱动的农事操作日志 |

### Afgen 处理策略

带 `TB` 后缀的参数均为 Afgen 插值表（例：`SLATB` = SLA as function of DVS）。统一拆分为：

- `afgen_tables`：记录表名、所属模块、X 变量名、Y 变量名、X 单位、Y 单位
- `afgen_points`：逐行 X, Y 数据对

查询时按 `(table_id, x_value)` 做分段线性插值即可还原 Afgen 表的分段线性插值。

---

## 2. ER 总览

```
┌──────────┐     ┌──────────────┐     ┌────────────────────────────┐
│  crops   │────→│  varieties   │────→│ phenology_params            │
└──────────┘     └──────────────┘     │ assim_params                │
                                      │ partition_tables            │
┌──────────┐     ┌──────────────┐     │ leaf_dynamics_params        │
│  soils   │────→│ soil_layers  │     │ stem_dynamics_params        │
└──────────┘     └──────────────┘     │ root_dynamics_params        │
                                      │ storage_organ_params        │
┌──────────────┐  ┌──────────────┐     │ respiration_params          │
│ weather_stns │─→│weather_records│    │ evap_params                 │
└──────────────┘  └──────────────┘     │ vernalisation_params        │
                                      │ conversion_effs             │
┌──────────────────┐                   │ npk_demand_uptake_params    │ (P)
│ site_parameters  │                   │ npk_stress_params           │ (P)
│ snomin_params    │ (Q)               │ npk_translocation_params    │ (P)
└──────────────────┘                   └────────────────────────────┘
                                                  │
┌──────────────────┐                               │
│ planting_plans   │                               │
│ timed_events     │                               │
│ state_events     │                               │
│ snomin_fert_evts │ (Q)                           │
└──────────────────┘                               │
        │                                          │
        └────────────────┬─────────────────────────┘
                         │
                  ┌──────▼────────┐
                  │ sim_runs      │
                  │ sim_daily_out │
                  │ sim_summary   │
                  │ signal_log    │ (S)
                  └───────────────┘

┌──────────────┐
│ afgen_tables │ ←── 所有插值表的元数据 (~50 张表)
│ afgen_points │ ←── X,Y 数据对
└──────────────┘
```

### 核心实体关系

```
crop ──< variety ──< phenology_params
variety ──< assim_params
variety ──< leaf_dynamics_params
variety ──< stem_dynamics_params
variety ──< root_dynamics_params
variety ──< storage_organ_params
variety ──< respiration_params
variety ──< evap_params
variety ──< conversion_effs
variety ──< vernalisation_params
variety ──< npk_demand_uptake_params
variety ──< npk_stress_params
variety ──< npk_translocation_params

soil_profile ──< soil_layer

site ──< site_parameters
site ──< snomin_site_parameters

weather_station ──< weather_daily

planting_plan ──< timed_event
planting_plan ──< state_event
planting_plan ──< snomin_fertilizer_event

sim_run ── variety, soil, weather_station, planting_plan, site
sim_run ──< sim_daily_output
sim_run ──< signal_log
```

---

## 3. 表结构详细设计

### A. 作物与品种 (crop / variety)

#### crops — 作物种类

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | 主键 |
| `crop_code` | VARCHAR(32) | UNIQUE, NOT NULL | 作物代码 (wheat, maize, potato, rice, onion...) |
| `crop_name_zh` | VARCHAR(64) | NOT NULL | 中文名 |
| `crop_name_en` | VARCHAR(64) | NOT NULL | 英文名 |
| `crop_name_la` | VARCHAR(128) | | 拉丁学名 |
| `model_class` | VARCHAR(64) | NOT NULL | 模型类 (Wofost72/Wofost73/Wofost81/LINGRA/LINTUL3/ALCEPAS) |
| `crop_type` | ENUM | NOT NULL | 作物类型: `cereal`(谷类), `root_tuber`(根茎), `legume`(豆类), `vegetable`(蔬菜), `grass`(牧草) |
| `is_perennial` | BOOLEAN | DEFAULT FALSE | 是否多年生 |
| `base_temperature` | DECIMAL(5,2) | DEFAULT 10.0 | 基础温度 T_base (°C)，默认 10°C |
| `description` | TEXT | | 描述 |
| `created_at` | DATETIME | DEFAULT NOW() | |
| `updated_at` | DATETIME | ON UPDATE NOW() | |

#### varieties — 品种

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | |
| `crop_id` | INT | FK → crops.id, NOT NULL | 所属作物 |
| `variety_code` | VARCHAR(64) | NOT NULL | 品种代码 (winter-wheat-001, fodder-maize-002...) |
| `variety_name` | VARCHAR(128) | NOT NULL | 品种名称 |
| `is_active` | BOOLEAN | DEFAULT TRUE | 是否启用 |
| `source` | VARCHAR(256) | | 参数来源 (论文/官方/实测) |
| `notes` | TEXT | | 备注 |
| `created_at` | DATETIME | DEFAULT NOW() | |
| `updated_at` | DATETIME | ON UPDATE NOW() | |

UNIQUE KEY: `(crop_id, variety_code)`

---

### B. 物候学 (phenology)

> 来源: Phenology 模块
> 模型选项: 0=仅温度驱动, 1=+光周期修正, 2=+春化(Wang & Engel 1998)

#### phenology_parameters — 物候发育参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK, AUTO_INCREMENT | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | 所属品种 | |
| `tsumem` | DECIMAL(8,2) | NOT NULL | 播种→出苗积温 (°C·d) | `TSUMEM` |
| `tbasem` | DECIMAL(5,2) | NOT NULL | 出苗基础温度 (°C) | `TBASEM` |
| `teffmx` | DECIMAL(5,2) | NOT NULL | 出苗最高有效温度 (°C) | `TEFFMX` |
| `tsum1` | DECIMAL(8,2) | NOT NULL | 出苗→开花积温 (°C·d) | `TSUM1` |
| `tsum2` | DECIMAL(8,2) | NOT NULL | 开花→成熟积温 (°C·d) | `TSUM2` |
| `idsl` | TINYINT | NOT NULL, DEFAULT 0 | 物候选项: 0=仅温度, 1=+光周期, 2=+春化 | `IDSL` |
| `dlo` | DECIMAL(5,2) | | 最适日长 (hr), IDSL≥1 时有效 | `DLO` |
| `dlc` | DECIMAL(5,2) | | 临界日长 (hr), IDSL≥1 时有效 | `DLC` |
| `dvsi` | DECIMAL(4,3) | NOT NULL, DEFAULT 0 | 初始 DVS (出苗时), 通常为 0 | `DVSI` |
| `dvsend` | DECIMAL(4,3) | NOT NULL, DEFAULT 2.0 | 最终 DVS (成熟时) | `DVSEND` |
| `crop_start_type` | ENUM('sowing','emergence') | NOT NULL | 模拟起点类型 | `CROP_START_TYPE` |
| `crop_end_type` | ENUM('maturity','harvest','earliest') | NOT NULL | 模拟终点类型 | `CROP_END_TYPE` |
| `dtsmtb_afgen_id` | INT | FK → afgen_tables.id | 温度→发育速率响应曲线 | `DTSMTB` |

#### phenology_stages — 生育期阶段定义

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `crop_id` | INT | FK → crops.id | 作物 |
| `stage_code` | VARCHAR(16) | NOT NULL | 阶段代码: emerging/vegetative/reproductive/mature |
| `stage_name_zh` | VARCHAR(32) | NOT NULL | 中文名 (出苗期/营养生长期/生殖生长期/成熟期) |
| `stage_order` | TINYINT | NOT NULL | 阶段顺序 (0/1/2/3) |
| `dvs_start` | DECIMAL(5,3) | NOT NULL | DVS 起始值 |
| `dvs_end` | DECIMAL(5,3) | NOT NULL | DVS 结束值 |
| `gdd_fraction` | DECIMAL(4,3) | | 此阶段占全生育期积温比例 (经验值) |

---

### C. 光合同化 (assimilation)

> 来源: Assimilation 模块
>
> 三个版本: `WOFOST72_Assimilation` (基础), `WOFOST73_Assimilation` (+CO₂), `WOFOST81_Assimilation` (+叶片氮驱动 AMAX)
> 算法: 3 点高斯积分 × 冠层深度 (GRAI) → 日总同化量 (PGASS)

#### assimilation_parameters — 光合参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK, AUTO_INCREMENT | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `version` | ENUM('7.2','7.3','8.1') | NOT NULL | WOFOST 版本 | |
| `amaxtb_afgen_id` | INT | FK → afgen_tables.id | AMAX (DVS) — 7.2/7.3 用 | `AMAXTB` |
| `efftb_afgen_id` | INT | FK → afgen_tables.id | 光能利用效率 (日平均温度) | `EFFTB` |
| `kdif_tb_afgen_id` | INT | FK → afgen_tables.id | 散射光消光系数 (DVS) | `KDIFTB` |
| `tmpf_tb_afgen_id` | INT | FK → afgen_tables.id | AMAX 温度校正因子 (日平均温度) | `TMPFTB` |
| `tmnf_tb_afgen_id` | INT | FK → afgen_tables.id | AMAX 低温校正因子 (7日最低温均值) | `TMNFTB` |
| `co2_amax_tb_afgen_id` | INT | FK → afgen_tables.id | CO₂→AMAX 校正 (7.3/8.1) | `CO2AMAXTB` |
| `co2_eff_tb_afgen_id` | INT | FK → afgen_tables.id | CO₂→EFF 校正 (7.3/8.1) | `CO2EFFTB` |
| `co2_concentration` | DECIMAL(6,1) | DEFAULT 420.0 | 大气 CO₂ 浓度 (ppm) — 7.3/8.1 | `CO2` |
| `amax_lnb` | DECIMAL(8,4) | | 无光合活性的最低比叶氮 (kg/ha) — 8.1 | `AMAX_LNB` |
| `amax_ref` | DECIMAL(8,4) | | 参考条件下最大 CO₂ 同化率 (kg/ha/hr) — 8.1 | `AMAX_REF` |
| `amax_slp` | DECIMAL(10,6) | | AMAX 对 SLN 线性响应斜率 (kg/hr/kg) — 8.1 | `AMAX_SLP` |
| `kn` | DECIMAL(5,3) | | 冠层氮消光系数 — 8.1 | `KN` |

#### photosynthesis_constants — 光合物理常数

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | INT | PK |
| `constant_name` | VARCHAR(32) | 常数名 (SCV) |
| `constant_value` | DECIMAL(10,6) | 值 |
| `description` | VARCHAR(256) | 含义 |

> 默认数据: `SCV` = 0.2 (散射系数), `CH2O_CO2_ratio` = 0.6818 (30/44)

---

### D. 干物质分配 (partitioning)

> 来源: Partitioning 模块
>
> N 版增加了水分胁迫修正: `FR = min(0.6, FRTB(DVS) * max(1, 1/(RFTRA+0.5)))`

**存储策略**：分配系数 DVS 节点通常较少 (5~15 个点)，直接存为品种级数据表。

#### partitioning_factors — 分配系数

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | |
| `variety_id` | INT | FK → varieties.id, NOT NULL | |
| `dvs` | DECIMAL(5,3) | NOT NULL | 发育阶段 DVS (0.00 ~ 2.00) |
| `fr` | DECIMAL(5,4) | NOT NULL | 向根的分配比例 | `FRTB(DVS)` |
| `fl` | DECIMAL(5,4) | NOT NULL | 向叶的分配比例 (地上部占比) | `FLTB(DVS)` |
| `fs` | DECIMAL(5,4) | NOT NULL | 向茎的分配比例 (地上部占比) | `FSTB(DVS)` |
| `fo` | DECIMAL(5,4) | NOT NULL | 向贮存器官的分配比例 (地上部占比) | `FOTB(DVS)` |
| `sort_order` | INT | NOT NULL | DVS 排序 |

UNIQUE KEY: `(variety_id, dvs)`

**校验约束**：`FR + (FL+FS+FO) × (1-FR) ≈ 1.0` (±0.0001)

---

### E1. 叶片动态 (leaf dynamics)

> 来源: Leaf Dynamics 模块
>
> 核心数据结构: 叶片作为 deque (双端队列)，新生叶从左加入，衰老从右移除。
> 4 条死亡路径: DSLV1(水分胁迫)、DSLV2(自遮荫, LAICR=3.2/KDIFTB)、DSLV3(霜冻)、DSLV4(养分胁迫, N版)

#### leaf_dynamics_parameters — 叶片动态参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `rgrlai` | DECIMAL(6,4) | NOT NULL | LAI 最大相对增长率 (ha/ha/d) | `RGRLAI` |
| `span` | DECIMAL(5,1) | NOT NULL | 35°C 下叶片寿命 (d) | `SPAN` |
| `tbase` | DECIMAL(5,2) | NOT NULL | 叶片衰老下限温度 (°C) | `TBASE` |
| `perdl` | DECIMAL(6,4) | NOT NULL | 水分胁迫最大相对死亡率 | `PERDL` |
| `tdwi` | DECIMAL(10,4) | NOT NULL | 初始总干物重 (kg/ha) | `TDWI` |
| `slatb_afgen_id` | INT | FK → afgen_tables.id | 比叶面积 (DVS) — ha/kg | `SLATB` |
| `kdif_tb_afgen_id` | INT | FK → afgen_tables.id | 散射光消光系数 (DVS) | `KDIFTB` |
| `rgrlai_min` | DECIMAL(6,4) | | 最大 N 胁迫下最小 RGRLAI (N版) | `RGRLAI_MIN` |

---

### E2. 茎动态 (stem dynamics)

> 来源: Stem Dynamics 模块

#### stem_dynamics_parameters — 茎动态参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `tdwi` | DECIMAL(10,4) | NOT NULL | 初始总干物重 (kg/ha) | `TDWI` |
| `rdrstb_afgen_id` | INT | FK → afgen_tables.id | 茎相对死亡率 (DVS) | `RDRSTB` |
| `ssatb_afgen_id` | INT | FK → afgen_tables.id | 比茎面积 (DVS) — ha/kg | `SSATB` |

---

### E3. 根系动态 (root dynamics)

> 来源: Root Dynamics 模块
>
> 重要设计: 根系伸长期独立于同化物供应量 (避免干旱条件下模型不稳定)
> 根深 = min(RDM-RD, RRI), 当 FR=0 或 RD=RDM 时停止

#### root_dynamics_parameters — 根系动态参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `rdi` | DECIMAL(7,2) | NOT NULL | 初始根深 (cm) | `RDI` |
| `rri` | DECIMAL(5,2) | NOT NULL | 每日根深增长速率 (cm/d) | `RRI` |
| `rdmcr` | DECIMAL(7,2) | NOT NULL | 作物最大根深 (cm) | `RDMCR` |
| `tdwi` | DECIMAL(10,4) | NOT NULL | 初始总干物重 (kg/ha) | `TDWI` |
| `iairdu` | TINYINT | DEFAULT 0 | 根系是否有通气组织 (0/1) | `IAIRDU` |
| `rdrrtb_afgen_id` | INT | FK → afgen_tables.id | 根相对死亡率 (DVS) | `RDRRTB` |

---

### E4. 贮存器官动态 (storage organ dynamics)

> 来源: Storage Organ Dynamics 模块

#### storage_organ_parameters — 贮存器官参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `spa` | DECIMAL(6,4) | NOT NULL | 比荚面积 (ha/kg) | `SPA` |
| `tdwi` | DECIMAL(10,4) | NOT NULL | 初始总干物重 (kg/ha) | `TDWI` |

---

### F. 维持呼吸 (respiration)

> 来源: Respiration 模块
>
> 公式: `PMRES = Σ(RMi × Wi) × RFSETB(DVS) × Q10^((TEMP-25)/10)`
> 实际 MRES = min(GASS, PMRES)

#### respiration_parameters — 维持呼吸参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `q10` | DECIMAL(4,2) | NOT NULL | 温度每升高 10°C 呼吸速率相对增加量 | `Q10` |
| `rmr` | DECIMAL(8,6) | NOT NULL | 根的相对维持呼吸速率 (kg CH₂O/kg/d) | `RMR` |
| `rml` | DECIMAL(8,6) | NOT NULL | 叶的相对维持呼吸速率 | `RML` |
| `rms` | DECIMAL(8,6) | NOT NULL | 茎的相对维持呼吸速率 | `RMS` |
| `rmo` | DECIMAL(8,6) | NOT NULL | 贮存器官的相对维持呼吸速率 | `RMO` |
| `rfsetb_afgen_id` | INT | FK → afgen_tables.id | 衰老校正因子 (DVS) | `RFSETB` |

---

### G. 蒸散与水分 (evapotranspiration)

> 来源: Evapotranspiration 模块
>
> 三个版本: `Evapotranspiration` (基础), `EvapotranspirationCO2` (+CO₂), `EvapotranspirationWrapper` (CO₂+分层土壤)
> SWEAF(ET0, DEPNR) 硬编码参数: A=0.76, B=1.5, DEPNR<3 有额外修正

#### evapotranspiration_parameters — 蒸散参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `cfet` | DECIMAL(5,3) | NOT NULL | 潜在蒸腾校正因子 | `CFET` |
| `depnr` | DECIMAL(3,1) | NOT NULL | 作物干旱敏感性编号 (1=敏感, 5=耐旱) | `DEPNR` |
| `kdif_tb_afgen_id` | INT | FK → afgen_tables.id | 散射光消光系数 (DVS) | `KDIFTB` |
| `iairdu` | TINYINT | DEFAULT 0 | 根系是否有通气组织 | `IAIRDU` |
| `iox` | TINYINT | DEFAULT 0 | 是否启用氧胁迫 (0/1) | `IOX` |
| `crairc` | DECIMAL(5,4) | | 根系呼吸临界空气含量 (m³/m³) | `CRAIRC` |
| `co2_tratb_afgen_id` | INT | FK → afgen_tables.id | CO₂→蒸腾校正 (CO₂版) | `CO2TRATB` |
| `co2` | DECIMAL(6,1) | | 大气 CO₂ 浓度 ppm (CO₂版) | `CO2` |

---

### H. 转换效率 & 再分配 (conversion efficiencies & reallocation)

> 源码:
> 来源: Conversion Efficiencies / Reallocation (Wofost72/Wofost81)
>
> 加权转换效率: `CVF = 1 / ((FL/CVL + FS/CVS + FO/CVO) × (1-FR) + FR/CVR)`
>
> 再分配 (WOFOST 8.1): 当 DVS ≥ REALLOC_DVS，茎叶贮存的干物质按比例转移到贮存器官，考虑 CVL/CVS→CVO 折算和效率损失

#### conversion_efficiencies — 同化物→器官转换效率

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `cvl` | DECIMAL(6,4) | NOT NULL | 同化物→叶转换效率 (kg/kg CH₂O) | `CVL` |
| `cvo` | DECIMAL(6,4) | NOT NULL | 同化物→贮存器官转换效率 | `CVO` |
| `cvr` | DECIMAL(6,4) | NOT NULL | 同化物→根转换效率 | `CVR` |
| `cvs` | DECIMAL(6,4) | NOT NULL | 同化物→茎转换效率 | `CVS` |
| `realloc_dvs` | DECIMAL(4,3) | DEFAULT 2.0 | 再分配起始 DVS (8.1) | `REALLOC_DVS` |
| `realloc_leaf_fraction` | DECIMAL(4,3) | DEFAULT 0 | 可再分配叶干物质比例 (8.1) | `REALLOC_LEAF_FRACTION` |
| `realloc_stem_fraction` | DECIMAL(4,3) | DEFAULT 0 | 可再分配茎干物质比例 (8.1) | `REALLOC_STEM_FRACTION` |
| `realloc_leaf_rate` | DECIMAL(6,4) | DEFAULT 0 | 叶再分配相对速率 (8.1) | `REALLOC_LEAF_RATE` |
| `realloc_stem_rate` | DECIMAL(6,4) | DEFAULT 0 | 茎再分配相对速率 (8.1) | `REALLOC_STEM_RATE` |
| `realloc_efficiency` | DECIMAL(5,4) | DEFAULT 0 | 再分配效率 (8.1) | `REALLOC_EFFICIENCY` |

---

### I. 春化参数 (vernalisation)

> 来源: Vernalisation 模块
> 仅当 `IDSL ≥ 2` 时启用 (Wang & Engel 1998 模型)
> 春化减速因子: `VERNFAC = limit(0, 1, (VERN-VERNBASE) / (VERNSAT-VERNBASE))`

#### vernalisation_parameters — 春化参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `vernsat` | DECIMAL(6,1) | NOT NULL | 饱和春化需求 (d) | `VERNSAT` |
| `vernbase` | DECIMAL(6,1) | NOT NULL | 基础春化需求 (d) | `VERNBASE` |
| `vernrtb_afgen_id` | INT | FK → afgen_tables.id | 温度→春化速率响应曲线 | `VERNRTB` |
| `verndvs` | DECIMAL(4,2) | NOT NULL | 春化效应停止的临界 DVS | `VERNDVS` |

---

### J. 土壤 (soil)

> 源码:
> 来源: Soil 模块

#### soil_profiles — 土壤类型

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `soil_code` | VARCHAR(32) | UNIQUE, NOT NULL | 土壤代码 (loam, clay, sandy_loam...) |
| `soil_name_zh` | VARCHAR(64) | NOT NULL | 中文名 |
| `soil_name_en` | VARCHAR(64) | NOT NULL | 英文名 |
| `soil_class` | VARCHAR(32) | | USDA 分类 |
| `is_layered` | BOOLEAN | DEFAULT FALSE | 是否分层土壤 |
| `water_balance_model` | VARCHAR(64) | NOT NULL | 水分平衡模型 (WaterbalancePP/FD, WaterBalanceLayered, WaterBalanceLayered_PP) |
| `pf_field_capacity` | DECIMAL(4,2) | | 田间持水量对应 pF 值 (默认 2.0) | `PFFieldCapacity` |
| `pf_wilting_point` | DECIMAL(4,2) | | 萎蔫点对应 pF 值 (默认 4.2) | `PFWiltingPoint` |
| `surface_conductivity` | DECIMAL(8,2) | | 地表最大入渗速率 (cm/d) | `SurfaceConductivity` |
| `ground_water` | DECIMAL(8,2) | | 地下水深 (cm)，NULL=无地下水 | `GroundWater` |
| `sub_soil_type` | VARCHAR(32) | | 底土类型代码 (NULL=无底土，最后一层无限延伸) | `SubSoilType` |
| `description` | TEXT | | |

#### soil_layers — 土壤层属性

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `soil_id` | INT | FK → soil_profiles.id, NOT NULL | | |
| `layer_index` | INT | NOT NULL | 层序号 (从表层=0 开始) | |
| `thickness` | DECIMAL(7,2) | NOT NULL | 层厚度 (cm) | `Thickness` |
| `smfcf` | DECIMAL(5,4) | NOT NULL | 田间持水量 (m³/m³) | `SMFCF` |
| `smw` | DECIMAL(5,4) | NOT NULL | 萎蔫点含水量 (m³/m³) | `SMW` |
| `sm0` | DECIMAL(5,4) | NOT NULL | 饱和含水量/孔隙度 (m³/m³) | `SM0` |
| `crairc` | DECIMAL(5,4) | | 根系呼吸临界空气含量 (m³/m³) | `CRAIRC` |
| `k0` | DECIMAL(8,4) | | 饱和导水率 (cm/d) | `KO` |
| `sope` | DECIMAL(6,3) | | 水力传导曲线坡度 | `SOPE` |
| `k_sub` | DECIMAL(6,2) | | 底层最大渗漏速率 (cm/d) | `KSUB` |
| `rdmsol` | DECIMAL(7,2) | | 土壤允许最大根深 (cm) | `RDMSOL` |
| `rhod` | DECIMAL(7,1) | | 容重 (kg/m³) — 多层/SNOMIN | `RHOD` |
| `fsomi` | DECIMAL(5,4) | | 初始有机质含量比例 — SNOMIN | `FSOMI` |
| `cn_ratio_somi` | DECIMAL(5,2) | | 初始有机质 C:N 比 — SNOMIN | `CNRatioSOMI` |
| `ph` | DECIMAL(4,2) | | 土壤 pH — SNOMIN | `pH` |

UNIQUE KEY: `(soil_id, layer_index)`

#### soil_layer_afgen — 土层水力特性插值表

> 每层的 SMfromPF 和 CONDfromPF 是独立的 pFCurve（Afgen 表）。此关联表将土层与对应的 Afgen 表关联。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `layer_id` | INT | FK → soil_layers.id, NOT NULL | |
| `afgen_table_id` | INT | FK → afgen_tables.id, NOT NULL | |
| `curve_type` | VARCHAR(16) | NOT NULL | 曲线类型: SMfromPF / CONDfromPF |

UNIQUE KEY: `(layer_id, curve_type)`

对于非分层土壤 (WaterbalanceFD classical)，只有一层。

**多层土壤水分平衡特点**:
- 向下/向上水流基于基质通量势 (Matric Flux Potential)
- 干流 (基质势梯度) + 湿流 (重力+导水率)
- 输出逐层变量: WC (水量 cm), SM (体积含水率)

---

### K. 气象 (weather)

> 来源: Weather 模块

#### weather_stations — 气象站点

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `station_code` | VARCHAR(32) | UNIQUE | 站点代码 |
| `station_name` | VARCHAR(128) | NOT NULL | 站点名 |
| `latitude` | DECIMAL(8,5) | NOT NULL | 纬度 (deg) |
| `longitude` | DECIMAL(8,5) | NOT NULL | 经度 (deg) |
| `elevation` | DECIMAL(7,2) | NOT NULL | 海拔 (m) |
| `et_model` | VARCHAR(8) | DEFAULT 'PM' | 参考蒸散模型 (PM=Penman-Monteith) |
| `data_source` | VARCHAR(128) | | 数据来源 (NASA POWER, OpenMeteo, station...) |
| `date_from` | DATE | | 数据起始日期 |
| `date_to` | DATE | | 数据截止日期 |

#### weather_daily — 逐日气象数据

| 列名 | 类型 | 约束 | 说明 | 单位 |
|------|------|------|------|------|
| `id` | BIGINT | PK | | |
| `station_id` | INT | FK → weather_stations.id, NOT NULL | | |
| `record_date` | DATE | NOT NULL | 日期 | |
| `irrad` | DECIMAL(10,2) | NOT NULL | 日总入射短波辐射 | J/m²/d |
| `tmin` | DECIMAL(5,2) | NOT NULL | 日最低气温 | °C |
| `tmax` | DECIMAL(5,2) | NOT NULL | 日最高气温 | °C |
| `vap` | DECIMAL(6,2) | NOT NULL | 日平均水汽压 | hPa |
| `rain` | DECIMAL(6,2) | NOT NULL | 日降水量 | cm/d |
| `wind` | DECIMAL(6,2) | NOT NULL | 2m 高处日平均风速 | m/s |
| `e0` | DECIMAL(6,4) | NOT NULL | 开阔水面蒸发量 | cm/d |
| `es0` | DECIMAL(6,4) | NOT NULL | 裸土蒸发量 | cm/d |
| `et0` | DECIMAL(6,4) | NOT NULL | 参考作物蒸散量 | cm/d |
| `temp` | DECIMAL(5,2) | | 日均气温 (默认 = (TMAX+TMIN)/2) | °C |
| `snow_depth` | DECIMAL(6,2) | | 积雪深度 | cm |

UNIQUE KEY: `(station_id, record_date)`

运行时派生变量 (不在表中存储):
- `DTEMP = (TEMP + TMAX) / 2` — 日间平均温度
- `TMINRA` — 7 日滑动平均最低温

---

### L. 农事管理 (agromanagement)

> 来源: Agromanager 模块

#### planting_plans — 种植计划

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `plan_code` | VARCHAR(64) | UNIQUE, NOT NULL | 方案代码 |
| `plan_name` | VARCHAR(128) | NOT NULL | 方案名称 |
| `variety_id` | INT | FK → varieties.id, NOT NULL | 选用品种 |
| `soil_id` | INT | FK → soil_profiles.id | 目标土壤 |
| `station_id` | INT | FK → weather_stations.id | 参考气象站点 |
| `site_id` | INT | FK → sites.id | 站点参数 (含 SNOMIN) |
| `crop_start_date` | DATE | NOT NULL | 种植开始日期 |
| `crop_start_type` | ENUM('sowing','emergence') | NOT NULL | 起点类型 |
| `crop_end_date` | DATE | | 计划收获日期 |
| `crop_end_type` | ENUM('maturity','harvest','earliest') | NOT NULL | 终点类型 |
| `max_duration` | INT | NOT NULL | 最大生育天数 |
| `is_active` | BOOLEAN | DEFAULT TRUE | |
| `description` | TEXT | | |
| `created_at` | DATETIME | DEFAULT NOW() | |

#### timed_events — 定时事件 (按日期触发)

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `plan_id` | INT | FK → planting_plans.id, NOT NULL | |
| `event_signal` | VARCHAR(32) | NOT NULL | 信号名: `irrigate`, `apply_n`, `apply_p`, `apply_k`, `apply_n_snomin`, `mow`, `spray` |
| `event_name` | VARCHAR(64) | | 事件名称 |
| `event_date` | DATE | NOT NULL | 触发日期 |
| `irrigation_amount` | DECIMAL(8,2) | | 灌水量 (cm) |
| `irrigation_efficiency` | DECIMAL(4,3) | | 灌溉效率 |
| `n_amount` | DECIMAL(8,2) | | 施氮量 (kg/ha) — `apply_n` |
| `n_recovery` | DECIMAL(4,3) | | 氮回收率 — `apply_n` |
| `p_amount` | DECIMAL(8,2) | | 施磷量 (kg/ha) — `apply_p` |
| `k_amount` | DECIMAL(8,2) | | 施钾量 (kg/ha) — `apply_k` |
| `comment` | TEXT | | |

#### state_events — 状态事件 (按模型状态触发)

零交叉检测 (rising/falling/either) 确保阈值附近不振荡触发。

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `plan_id` | INT | FK → planting_plans.id, NOT NULL | |
| `event_signal` | VARCHAR(32) | NOT NULL | 触发的信号名 |
| `event_state` | VARCHAR(32) | NOT NULL | 触发状态变量 (DVS, SM, LAI, NNI, NPKI...) |
| `zero_condition` | ENUM('rising','falling','either') | NOT NULL | 零交叉方向 |
| `trigger_value` | DECIMAL(10,4) | NOT NULL | 触发阈值 |
| `n_amount` | DECIMAL(8,2) | | 施氮量 (kg/ha) |
| `n_recovery` | DECIMAL(4,3) | | 氮回收率 |
| `irrigation_amount` | DECIMAL(8,2) | | 灌水量 (cm) |
| `p_amount` | DECIMAL(8,2) | | 施磷量 |
| `k_amount` | DECIMAL(8,2) | | 施钾量 |
| `comment` | TEXT | | |

**状态事件典型用法**:
| 信号 | 状态变量 | 零条件 | 示例 | 含义 |
|------|----------|--------|------|------|
| `apply_n` | DVS | rising | DVS=0.3 施基肥, DVS=1.12 施穗肥 | 按生育期施肥 |
| `irrigate` | SM | falling | SM=0.15 时灌水 2cm | 土壤水分不足时灌溉 |
| `apply_n` | NNI | falling | NNI<0.9 时追肥 | 氮营养指数不足时追肥 |
| `apply_n` | NPKI | falling | NPKI<0.8 时追肥 | NPK 综合营养不足 |

#### snomin_fertilizer_events — SNOMIN 有机肥事件

> 来源: SNOMIN 模块
> 信号: `apply_n_snomin`，按层施加有机肥/化肥，含 C:N 比和有机质比例

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `plan_id` | INT | FK → planting_plans.id, NOT NULL | |
| `event_date` | DATE | NOT NULL | 施肥日期 |
| `amount` | DECIMAL(10,2) | NOT NULL | 施肥量 (kg material/ha) |
| `application_depth` | DECIMAL(6,2) | NOT NULL | 施肥深度 (cm) |
| `cn_ratio` | DECIMAL(6,2) | NOT NULL | 有机质 C:N 比 (kg C/kg N) |
| `f_orgmat` | DECIMAL(5,4) | NOT NULL | 有机质含量分数 |
| `f_nh4n` | DECIMAL(5,4) | NOT NULL | NH₄-N 分数 |
| `f_no3n` | DECIMAL(5,4) | NOT NULL | NO₃-N 分数 |
| `initial_age` | DECIMAL(8,2) | DEFAULT 0 | 有机质初始表观年龄 (d) |
| `comment` | TEXT | | |

---

### M. 模型配置 (model configuration)

> 19 个模型配置文件定义了模型→土壤→农事管理的组装方式。

#### model_configurations — 模型配置

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `config_name` | VARCHAR(64) | UNIQUE, NOT NULL | 配置名 |
| `production_level` | ENUM('potential','water_limited','nutrient_limited') | NOT NULL | 生产水平 |
| `crop_module` | VARCHAR(128) | NOT NULL | 作物模拟类路径 |
| `soil_module` | VARCHAR(128) | | 土壤模块路径 (无则为 NULL) |
| `has_co2` | BOOLEAN | DEFAULT FALSE | 是否包含 CO₂ 效应 |
| `has_nitrogen` | BOOLEAN | DEFAULT FALSE | 是否包含氮素动态 (N_Crop_Dynamics) |
| `has_npk` | BOOLEAN | DEFAULT FALSE | 是否包含 NPK 全养分 (NPK_Demand_Uptake + NPK_Stress + NPK_Translocation) |
| `has_vernalisation` | BOOLEAN | DEFAULT FALSE | 是否包含春化模块 |
| `has_frost_kill` | BOOLEAN | DEFAULT FALSE | 是否包含霜冻致死 |
| `has_snow` | BOOLEAN | DEFAULT FALSE | 是否包含积雪模块 |
| `has_snomin` | BOOLEAN | DEFAULT FALSE | 是否包含 SNOMIN 土壤 C/N |
| `water_balance_type` | ENUM('PP','FD','CWB','MLWB','MLWB_SNOMIN') | NOT NULL | 水分平衡类型 |
| `config_yaml` | TEXT | | 原始配置内容 (asset) |

**完整模型配置清单** (19 个):

| config_name | production_level | crop_module | soil_module | 特性 |
|-------------|-----------------|-------------|-------------|------|
| `Wofost72_PP` | potential | Wofost72 | WaterbalancePP | 基础潜在产量 |
| `Wofost72_WLP_FD` | water_limited | Wofost72 | WaterbalanceFD | 经典单层自由排水 |
| `Wofost72_WLP_CWB` | water_limited | Wofost72 | WaterbalanceCWB | 经典+闭合水量平衡 |
| `Wofost72_Pheno` | potential | Wofost72 | WaterbalancePP | 仅物候驱动 |
| `Wofost73_PP` | potential | Wofost73 | WaterbalancePP | +CO₂效应 |
| `Wofost73_WLP_CWB` | water_limited | Wofost73 | WaterbalanceCWB | +CO₂+闭合WB |
| `Wofost73_WLP_MLWB` | water_limited | Wofost73 | MLWB | +CO₂+多层WB |
| `Wofost81_PP` | potential | Wofost81 | WaterbalancePP | +N再分配 |
| `Wofost81_WLP_CWB` | water_limited | Wofost81 | WaterbalanceCWB | +N+闭合WB |
| `Wofost81_WLP_MLWB` | water_limited | Wofost81 | MLWB | +N+多层WB |
| `Wofost81_NWLP_CWB_CNB` | nutrient_limited | Wofost81 | SoilModuleWrapper_NWLP_CWB_CNB | +NPK+C/N土壤 |
| `Wofost81_NWLP_MLWB_CNB` | nutrient_limited | Wofost81 | SoilModuleWrapper_NWLP_MLWB_CNB | +NPK+多层+CN |
| `Wofost81_NWLP_MLWB_SNOMIN` | nutrient_limited | Wofost81 | SoilModuleWrapper_NWLP_MLWB_SNOMIN | +NPK+多层+SNOMIN(全特性) |
| `Wofost_winterkill` | water_limited | Wofost72 | WaterbalanceFD | +霜冻致死 |
| `Lintul3` | water_limited | Lintul3 | Lintul3Soil | LINTUL3水稻/小麦 |
| `Lingra_PP` | potential | LINGRA | WaterbalancePP | 牧草潜在产量 |
| `Lingra_WLP_FD` | water_limited | LINGRA | WaterbalanceFD | 牧草水分限制 |
| `Lingra_NWLP_FD` | nutrient_limited | LINGRA | WaterbalanceFD+NPK | 牧草养分限制 |
| `Alcepas10_PP` | potential | ALCEPAS | 无 | 洋葱潜在产量 |
| `FAO_WRSI` | water_limited | WRSI | 无 | FAO水分满足指数 |

---

### N. 模拟结果 (simulation results)

#### simulation_runs — 模拟运行记录

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `plan_id` | INT | FK → planting_plans.id | 关联种植方案 |
| `model_config_id` | INT | FK → model_configurations.id | 使用的模型配置 |
| `simulation_start` | DATE | NOT NULL | 模拟起始日期 |
| `simulation_end` | DATE | NOT NULL | 模拟结束日期 |
| `status` | ENUM('pending','running','completed','failed') | DEFAULT 'pending' | |
| `error_message` | TEXT | | 如果失败，记录错误信息 |
| `created_at` | DATETIME | DEFAULT NOW() | |
| `completed_at` | DATETIME | | |

#### simulation_daily_output — 逐日模拟输出

每日保存 Published 的 State/Rate 变量值。

| 列名 | 类型 | 说明 | 参数名 |
|------|------|------|---------|
| `id` | BIGINT | PK | |
| `run_id` | INT | FK → simulation_runs.id, NOT NULL | |
| `record_date` | DATE | NOT NULL | 模拟日期 |
| `dvs` | DECIMAL(5,3) | 发育阶段 | `DVS` (S) |
| `stage` | VARCHAR(16) | 生育期 | `STAGE` (S) |
| `lai` | DECIMAL(7,3) | 叶面积指数 | `LAI` (S) |
| `lai_max` | DECIMAL(7,3) | 全生育期最大 LAI | `LAIMAX` (S) |
| `wlv` | DECIMAL(12,3) | 活叶干重 (kg/ha) | `WLV` (S) |
| `wst` | DECIMAL(12,3) | 活茎干重 (kg/ha) | `WST` (S) |
| `wrt` | DECIMAL(12,3) | 活根干重 (kg/ha) | `WRT` (S) |
| `wso` | DECIMAL(12,3) | 活贮存器官干重 (kg/ha) | `WSO` (S) |
| `twlv` | DECIMAL(12,3) | 总叶干重 (kg/ha) | `TWLV` (S) |
| `twst` | DECIMAL(12,3) | 总茎干重 (kg/ha) | `TWST` (S) |
| `twrt` | DECIMAL(12,3) | 总根干重 (kg/ha) | `TWRT` (S) |
| `twso` | DECIMAL(12,3) | 总贮存器官干重 (kg/ha) | `TWSO` (S) |
| `tagp` | DECIMAL(12,3) | 总地上部生物量 (kg/ha) | `TAGP` (S) |
| `rd` | DECIMAL(7,2) | 当前根深 (cm) | `RD` (S) |
| `sai` | DECIMAL(7,3) | 茎面积指数 | `SAI` (S) |
| `pai` | DECIMAL(7,3) | 荚面积指数 | `PAI` (S) |
| `sm` | DECIMAL(5,4) | 土壤体积含水量 (单层) | `SM` (S) |
| `wc` | DECIMAL(10,4) | 土壤总水量 cm (多层逐层为数组) | `WC` (S) |
| `fr` | DECIMAL(5,4) | 根分配比例 | `FR` (S) |
| `fl` | DECIMAL(5,4) | 叶分配比例 | `FL` (S) |
| `fs` | DECIMAL(5,4) | 茎分配比例 | `FS` (S) |
| `fo` | DECIMAL(5,4) | 贮存器官分配比例 | `FO` (S) |
| `tra` | DECIMAL(8,4) | 实际蒸腾 (cm/d) | `TRA` (R) |
| `tramx` | DECIMAL(8,4) | 最大蒸腾 (cm/d) | `TRAMX` (R) |
| `rftra` | DECIMAL(5,4) | 蒸腾削减因子 | `RFTRA` (R) |
| `evwmx` | DECIMAL(8,4) | 最大水面蒸发 (cm/d) | `EVWMX` (R) |
| `evsmx` | DECIMAL(8,4) | 最大土面蒸发 (cm/d) | `EVSMX` (R) |
| `evs` | DECIMAL(8,4) | 实际土壤蒸发 (cm/d) | `EVS` (R) |
| `gasst` | DECIMAL(12,3) | 累积总同化量 (kg CH₂O/ha) | `GASST` (S) |
| `mrest` | DECIMAL(12,3) | 累积维持呼吸量 | `MREST` (S) |
| `ctrat` | DECIMAL(8,2) | 累积作物蒸腾 (cm) | `CTRAT` (S) |
| `cevst` | DECIMAL(8,2) | 累积土壤蒸发 (cm) | `CEVST` (S) |
| `dmi` | DECIMAL(10,3) | 总干物质增量 (kg/ha/d) | `DMI` (R) |
| `admi` | DECIMAL(10,3) | 地上部干物质增量 (kg/ha/d) | `ADMI` (R) |
| `realloc_lv` | DECIMAL(8,3) | 叶再分配速率 (8.1) | `REALLOC_LV` (R) |
| `realloc_st` | DECIMAL(8,3) | 茎再分配速率 (8.1) | `REALLOC_ST` (R) |
| `realloc_so` | DECIMAL(8,3) | 贮存器官再分配增量 (8.1) | `REALLOC_SO` (R) |
| `hi` | DECIMAL(5,4) | 收获指数 (TWSO/TAGP) | `HI` (S) |
| `nni` | DECIMAL(5,4) | 氮营养指数 (N版/8.1) | `NNI` |
| `npki` | DECIMAL(5,4) | NPK 综合营养指数 (8.1) | `NPKI` |
| `n_amount_lv` | DECIMAL(10,3) | 叶实际 N 量 kg/ha (8.1) | `NamountLV` (S) |
| `n_amount_st` | DECIMAL(10,3) | 茎实际 N 量 kg/ha (8.1) | `NamountST` (S) |
| `n_amount_rt` | DECIMAL(10,3) | 根实际 N 量 kg/ha (8.1) | `NamountRT` (S) |
| `n_amount_so` | DECIMAL(10,3) | 贮存器官实际 N 量 kg/ha (8.1) | `NamountSO` (S) |
| `n_uptake_total` | DECIMAL(10,3) | 累积 N 吸收量 (kg/ha) | `NuptakeTotal` (S) |
| `n_demand` | DECIMAL(10,3) | N 需求量 (kg/ha/d) | `Ndemand` (R) |
| `n_avail` | DECIMAL(10,3) | 土壤有效 N (kg/ha) — SNOMIN | `NAVAIL` (S) |
| `nh4` | DECIMAL(10,3) | 土壤 NH₄-N (kg/ha) 总量 — SNOMIN | `NH4T` (S) |
| `no3` | DECIMAL(10,3) | 土壤 NO₃-N (kg/ha) 总量 — SNOMIN | `NO3T` (S) |
| `n_loss_cum` | DECIMAL(10,3) | 累积 N 损失 (kg/ha) — SNOMIN | `NLOSSCUM` (S) |
| `orgmat_total` | DECIMAL(10,3) | 土壤有机质总量 (kg/ha) — SNOMIN | `ORGMATT` (S) |
| `c_org_total` | DECIMAL(10,3) | 土壤有机碳总量 (kg/ha) — SNOMIN | `CORGT` (S) |
| `n_org_total` | DECIMAL(10,3) | 土壤有机氮总量 (kg/ha) — SNOMIN | `NORGT` (S) |
| `r_min_total` | DECIMAL(10,3) | 累积净矿化量 (kg/ha) — SNOMIN | `RMINT` (S) |
| `irrig` | DECIMAL(8,2) | 灌溉量 (cm) | `RIRR` |
| `extra_json` | JSON | | 拓展字段，存逐层数据 (NH4/NO3/WC per layer) |

UNIQUE KEY: `(run_id, record_date)`

(S) = State 变量, (R) = Rate 变量

> **注意**: 当使用 SNOMIN 或多层土壤时，逐层数据 (NH4, NO3, WC, SM, AGE, ORGMAT, CORG, NORG per layer) 建议存在 `extra_json` JSON 字段中，避免为每个可能的土壤层数创建大量列。每个模拟的层数是配置决定的。

#### simulation_summary_output — 每季总结输出

在 `crop_finish` 时触发，写入季节汇总数据。

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | INT | PK |
| `run_id` | INT | FK → simulation_runs.id, UNIQUE |
| `dvs_end` | DECIMAL(5,3) | 最终 DVS |
| `tagp_end` | DECIMAL(12,3) | 最终地上部总生物量 (kg/ha) |
| `twso_end` | DECIMAL(12,3) | 最终贮存器官总重 (kg/ha) |
| `twlv_end` | DECIMAL(12,3) | 最终总叶重 (kg/ha) |
| `twst_end` | DECIMAL(12,3) | 最终总茎重 (kg/ha) |
| `twrt_end` | DECIMAL(12,3) | 最终总根重 (kg/ha) |
| `hi` | DECIMAL(5,4) | 收获指数 (TWSO/TAGP) |
| `lai_max` | DECIMAL(7,3) | 全生育期最大 LAI |
| `total_transpiration` | DECIMAL(8,2) | 全生育期总蒸腾 (cm) = CTRAT |
| `total_evaporation` | DECIMAL(8,2) | 全生育期总土蒸 (cm) = CEVST |
| `total_assimilation` | DECIMAL(12,3) | 全生育期总同化 (kg CH₂O/ha) = GASST |
| `days_with_water_stress` | INT | 水分胁迫天数 |
| `days_with_oxygen_stress` | INT | 氧胁迫天数 |
| `duration_days` | INT | 实际生育期天数 |
| `finish_type` | VARCHAR(32) | 结束类型: maturity/harvest/max_duration |
| `sow_date` | DATE | 播种日期 (DOS) |
| `emergence_date` | DATE | 出苗日期 (DOE) |
| `anthesis_date` | DATE | 开花日期 (DOA) |
| `maturity_date` | DATE | 成熟日期 (DOM) |
| `harvest_date` | DATE | 收获日期 (DOH) |
| `n_uptake_total` | DECIMAL(10,3) | 全生育期总 N 吸收 (kg/ha) |
| `n_amount_so_end` | DECIMAL(10,3) | 最终贮存器官 N 量 (kg/ha) |

#### simulation_terminal_output — 终端输出 (TERMINATE 信号)

在 `terminate` 信号时触发，写入终端统计。

| 列名 | 类型 | 说明 |
|------|------|------|
| `id` | INT | PK |
| `run_id` | INT | FK → simulation_runs.id, UNIQUE |
| `wt_rat` | DECIMAL(8,2) | 总蒸腾累积 (cm) |
| `ev_st` | DECIMAL(8,2) | 总土面蒸发累积 (cm) |
| `ev_wt` | DECIMAL(8,2) | 总水面蒸发累积 (cm) |
| `tsr` | DECIMAL(8,2) | 总地表径流 (cm) |
| `rain_t` | DECIMAL(8,2) | 总降水 (cm) |
| `tot_inf` | DECIMAL(8,2) | 总下渗 (cm) |
| `tot_irr` | DECIMAL(8,2) | 总灌溉 (cm) |
| `perc_t` | DECIMAL(8,2) | 总深层渗漏 (cm) |
| `loss_t` | DECIMAL(8,2) | 总水分损失 (cm) |

---

### O. 通用插值表 (Afgen)

> Afgen = Arbitrary Function Generator (分段线性插值)
> Afgen = Arbitrary Function Generator (分段线性插值)

#### afgen_tables — 插值表定义

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | |
| `table_code` | VARCHAR(64) | UNIQUE, NOT NULL | 表代码 |
| `table_name` | VARCHAR(128) | NOT NULL | 可读名 |
| `module` | VARCHAR(64) | NOT NULL | 所属模块 (phenology/assimilation/leaf/...) |
| `param_name` | VARCHAR(32) | NOT NULL | 参数名 (如 DTSMTB, SLATB) |
| `x_variable` | VARCHAR(32) | NOT NULL | X 轴变量名 (如 TEMP, DVS) |
| `x_unit` | VARCHAR(32) | | X 轴单位 (如 °C, -) |
| `y_variable` | VARCHAR(64) | NOT NULL | Y 轴变量名 |
| `y_unit` | VARCHAR(32) | | Y 轴单位 |
| `description` | TEXT | | |

#### afgen_points — 插值点

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK, AUTO_INCREMENT | |
| `table_id` | INT | FK → afgen_tables.id, NOT NULL | |
| `x_value` | DECIMAL(10,5) | NOT NULL | X 值 |
| `y_value` | DECIMAL(12,6) | NOT NULL | Y 值 |
| `sort_order` | INT | NOT NULL | X 排序 |

UNIQUE KEY: `(table_id, x_value)`

**Afgen 表完整清单** (~40 张):

| 参数名 | X 变量 | Y 变量 | 模块 | 所属模型 |
|--------|--------|--------|------|---------|
| `DTSMTB` | TEMP (°C) | 发育速率增量 (°C) | phenology | All WOFOST/LINGRA |
| `VERNRTB` | TEMP (°C) | 春化速率 | phenology (IDSL=2) | 冬小麦/冬大麦 |
| `AMAXTB` | DVS | 最大同化率 (kg/ha/hr) | assimilation (7.2/7.3) | WOFOST 7.2/7.3 |
| `EFFTB` | DTEMP (°C) | 光能利用效率 | assimilation | All WOFOST |
| `KDIFTB` | DVS | 散射消光系数 | assimilation / leaf / evap | All WOFOST |
| `TMPFTB` | DTEMP (°C) | AMAX 温度校正 | assimilation | All WOFOST |
| `TMNFTB` | TMINRA (°C) | AMAX 低温校正 | assimilation | All WOFOST |
| `CO2AMAXTB` | CO2 (ppm) | AMAX 校正因子 | assimilation (7.3/8.1) | WOFOST 7.3/8.1 |
| `CO2EFFTB` | CO2 (ppm) | EFF 校正因子 | assimilation (7.3/8.1) | WOFOST 7.3/8.1 |
| `CO2TRATB` | CO2 (ppm) | 蒸腾校正因子 | evapotranspiration | WOFOST 7.3/8.1 |
| `FRTB` | DVS | 根分配比例 | partitioning | All WOFOST |
| `FLTB` | DVS | 叶分配比例 | partitioning | All WOFOST |
| `FSTB` | DVS | 茎分配比例 | partitioning | All WOFOST |
| `FOTB` | DVS | 贮存器官分配比例 | partitioning | All WOFOST |
| `SLATB` | DVS | 比叶面积 (ha/kg) | leaf_dynamics | All WOFOST |
| `RDRSTB` | DVS | 茎相对死亡率 | stem_dynamics | All WOFOST |
| `SSATB` | DVS | 比茎面积 (ha/kg) | stem_dynamics | All WOFOST |
| `RDRRTB` | DVS | 根相对死亡率 | root_dynamics | All WOFOST |
| `RFSETB` | DVS | 呼吸衰老校正因子 | respiration | All WOFOST |

**多层土壤水力特性 Afgen (per-layer pFCurve):**

| 参数名 | X 变量 | Y 变量 | 模块 |
|--------|--------|--------|------|
| `SMfromPF` | pF (log₁₀ cm suction) | 土壤体积含水率 (m³/m³) | soil_profile / soiln_profile |
| `CONDfromPF` | pF (log₁₀ cm suction) | log₁₀ 非饱和导水率 (cm/d) | soil_profile / soiln_profile |

> 注: SMfromPF 和 CONDfromPF 是 per-layer 插值表，存储在 `soil_layer_afgen` 关联表中（`layer_id` → `afgen_tables.id`）。pF 是土壤吸力的 10 进制对数（pF 2.0 = 100 cm, pF 4.2 = 15849 cm）。SMfromPF 的 X 值通常从 -1.0 (pF=-1 即 0.1 cm 吸力 ≈ 饱和) 开始。每层由自己的 SMfromPF 曲线推导 SM0 (pF=-1)、SMFCF (pF=PFFieldCapacity)、SMW (pF=PFWiltingPoint)。CONDfromPF 的 Y 值是 log₁₀ 值，使用前需 10^y 转换。MFPfromPF (基质通量势) 由 SMfromPF + CONDfromPF 数值积分生成，是导出量不存储。

**WOFOST 8.1 / NPK 专用 Afgen:**

| 参数名 | X 变量 | Y 变量 | 模块 |
|--------|--------|--------|------|
| `NMAXLV_TB` | DVS | 叶最大 N 浓度 (kg N/kg DM) | n_dynamics / npk_demand_uptake / npk_stress |
| `PMAXLV_TB` | DVS | 叶最大 P 浓度 (kg P/kg DM) | npk_demand_uptake / npk_stress |
| `KMAXLV_TB` | DVS | 叶最大 K 浓度 (kg K/kg DM) | npk_demand_uptake / npk_stress |
| `NSLLV_TB` | NstressIndexDLV | N 胁迫叶衰老因子 | n_stress |

**LINTUL3 专用 Afgen:**

| 参数名 | X 变量 | Y 变量 | 模块 |
|--------|--------|--------|------|
| `FLVTB` | DVS | 叶分配系数 | lintul3 |
| `FRTTB` | DVS | 根分配系数 | lintul3 |
| `FSOTB` | DVS | 贮存器官分配系数 | lintul3 |
| `FSTTB` | DVS | 茎分配系数 | lintul3 |
| `NMXLV` | DVS | 叶最大 N 浓度 (kg N/kg DM) | lintul3 |
| `RDRT` | DAVTMP (°C) | 叶相对死亡率 (1/d) | lintul3 |
| `SLACF` | DVS | 比叶面积校正因子 | lintul3 |

**ALCEPAS 专用 Afgen:**

| 参数名 | X 变量 | Y 变量 | 模块 |
|--------|--------|--------|------|
| `AMDVST` | DVS | AMAX 校正因子 | alcepas.assimilation |
| `AMTMPT` | DTEMP (°C) | AMAX 温度校正 | alcepas.assimilation |
| `FLVTB` | DVS | 叶对地上部分配比 | alcepas.partitioning |
| `FSHTB` | DVS | 地上部对总分配比 | alcepas.partitioning |
| `DAGTB` | DAYL (hr) | 日长修正因子 | alcepas.phenology |
| `RVRTB` | RFR | 辐射截获修正 | alcepas.phenology |
| `MSOTB` | DVS | 贮存器官维持呼吸 | alcepas.respiration |
| `MLVTB` | DVS | 叶维持呼吸 | alcepas.respiration |
| `MRTTB` | DVS | 根维持呼吸 | alcepas.respiration |
| `SLANTB` | NPL (株密度) | 叶面积线型参数 N | alcepas.leaf |
| `SLARTB` | NPL (株密度) | 叶面积线型参数 R | alcepas.leaf |

> 注: 分配系数 (FRTB/FLTB/FSTB/FOTB) 在 `partitioning_factors` 表中直接展开，不用单独的 Afgen 表。同样，LINTUL3 的 FLVTB/FRTTB/FSOTB/FSTTB 因为 DVS 节点少，可在对应参数表中展开。

---

### P. NPK 养分动态 (nutrient dynamics)

> 源码:
> 来源: Nutrient Dynamics 模块

#### P1. npk_demand_uptake_parameters — NPK 需求与吸收参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `nmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | 叶最大 N 浓度 (DVS) | `NMAXLV_TB` |
| `pmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | 叶最大 P 浓度 (DVS) | `PMAXLV_TB` |
| `kmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | 叶最大 K 浓度 (DVS) | `KMAXLV_TB` |
| `nmaxrt_fr` | DECIMAL(5,4) | NOT NULL | 根最大 N 浓度 (占叶比例) | `NMAXRT_FR` |
| `pmaxrt_fr` | DECIMAL(5,4) | NOT NULL | 根最大 P 浓度 (占叶比例) | `PMAXRT_FR` |
| `kmaxrt_fr` | DECIMAL(5,4) | NOT NULL | 根最大 K 浓度 (占叶比例) | `KMAXRT_FR` |
| `nmaxst_fr` | DECIMAL(5,4) | NOT NULL | 茎最大 N 浓度 (占叶比例) | `NMAXST_FR` |
| `pmaxst_fr` | DECIMAL(5,4) | NOT NULL | 茎最大 P 浓度 (占叶比例) | `PMAXST_FR` |
| `kmaxst_fr` | DECIMAL(5,4) | NOT NULL | 茎最大 K 浓度 (占叶比例) | `KMAXST_FR` |
| `nmaxso` | DECIMAL(8,6) | NOT NULL | 贮存器官最大 N 浓度 (kg/kg) | `NMAXSO` |
| `pmaxso` | DECIMAL(8,6) | NOT NULL | 贮存器官最大 P 浓度 (kg/kg) | `PMAXSO` |
| `kmaxso` | DECIMAL(8,6) | NOT NULL | 贮存器官最大 K 浓度 (kg/kg) | `KMAXSO` |
| `tcnt` | DECIMAL(5,1) | NOT NULL | N 转运时间系数 (d) | `TCNT` |
| `tcpt` | DECIMAL(5,1) | NOT NULL | P 转运时间系数 (d) | `TCPT` |
| `tckt` | DECIMAL(5,1) | NOT NULL | K 转运时间系数 (d) | `TCKT` |
| `nfix_fr` | DECIMAL(5,4) | NOT NULL | 生物固 N 比例 | `NFIX_FR` |
| `rnuptakemax` | DECIMAL(8,2) | NOT NULL | 最大 N 吸收速率 (kg/ha/d) | `RNUPTAKEMAX` |
| `rpuptakemax` | DECIMAL(8,2) | NOT NULL | 最大 P 吸收速率 (kg/ha/d) | `RPUPTAKEMAX` |
| `rkuptakemax` | DECIMAL(8,2) | NOT NULL | 最大 K 吸收速率 (kg/ha/d) | `RKUPTAKEMAX` |
| `dvs_n_transl` | DECIMAL(4,3) | | N 转运起始 DVS (N版) | `DVS_N_TRANSL` |
| `dvs_npk_stop` | DECIMAL(4,3) | DEFAULT -99.0 | NPK 吸收停止 DVS (负值=不停止) | `DVS_NPK_STOP` |

#### P2. npk_stress_parameters — NPK 胁迫参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `ncrit_fr` | DECIMAL(5,4) | NOT NULL | 临界 N 浓度 (占最大浓度比例) | `NCRIT_FR` |
| `pcrit_fr` | DECIMAL(5,4) | NOT NULL | 临界 P 浓度 (占最大浓度比例) | `PCRIT_FR` |
| `kcrit_fr` | DECIMAL(5,4) | NOT NULL | 临界 K 浓度 (占最大浓度比例) | `KCRIT_FR` |
| `nresidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 N 浓度 (kg/kg) | `NRESIDLV` |
| `nresidst` | DECIMAL(8,6) | NOT NULL | 茎残留 N 浓度 (kg/kg) | `NRESIDST` |
| `presidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 P 浓度 (kg/kg) | `PRESIDLV` |
| `presidst` | DECIMAL(8,6) | NOT NULL | 茎残留 P 浓度 (kg/kg) | `PRESIDST` |
| `kresidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 K 浓度 (kg/kg) | `KRESIDLV` |
| `kresidst` | DECIMAL(8,6) | NOT NULL | 茎残留 K 浓度 (kg/kg) | `KRESIDST` |
| `nlue_npk` | DECIMAL(5,4) | NOT NULL | NPK 胁迫下 RUE 削减系数 | `NLUE_NPK` |
| `nmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | (复用) 叶最大 N 浓度 | `NMAXLV_TB` |
| `pmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | (复用) 叶最大 P 浓度 | `PMAXLV_TB` |
| `kmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | (复用) 叶最大 K 浓度 | `KMAXLV_TB` |
| `nmaxrt_fr` | DECIMAL(5,4) | NOT NULL | (复用) 根最大 N 浓度比例 | `NMAXRT_FR` |
| `nmaxst_fr` | DECIMAL(5,4) | NOT NULL | (复用) 茎最大 N 浓度比例 | `NMAXST_FR` |
| `pmaxrt_fr` | DECIMAL(5,4) | NOT NULL | (复用) 根最大 P 浓度比例 | `PMAXRT_FR` |
| `pmaxst_fr` | DECIMAL(5,4) | NOT NULL | (复用) 茎最大 P 浓度比例 | `PMAXST_FR` |
| `kmaxrt_fr` | DECIMAL(5,4) | NOT NULL | (复用) 根最大 K 浓度比例 | `KMAXRT_FR` |
| `kmaxst_fr` | DECIMAL(5,4) | NOT NULL | (复用) 茎最大 K 浓度比例 | `KMAXST_FR` |

**NPK 胁迫指数计算**:
- `NNI = (N_actual - N_residual) / (N_critical - N_residual)`, limit(0.001, 1.0)
- `PNI`, `KNI` 同理
- `NPKI = min(NNI, PNI, KNI)`
- `RFNPK = 1 - NLUE_NPK × (1.0001 - NPKI)²` (同化削减因子)

**N only 胁迫 (WOFOST 8.1 N_Stress) 额外输出**:
- `NSLLV` (N 胁迫叶衰老乘数因子): 当 N_amount_ABG_max / N_amount_ABG_actual 超出 1~2 范围，加速叶片衰老
- `RFRGRL` (指数生长期 LAI 增长削减因子)

#### P3. npk_translocation_parameters — NPK 转运参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `nresidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 N 浓度 (kg/kg) | `NRESIDLV` |
| `nresidst` | DECIMAL(8,6) | NOT NULL | 茎残留 N 浓度 (kg/kg) | `NRESIDST` |
| `nresidrt` | DECIMAL(8,6) | NOT NULL | 根残留 N 浓度 (kg/kg) | `NRESIDRT` |
| `presidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 P 浓度 (kg/kg) | `PRESIDLV` |
| `presidst` | DECIMAL(8,6) | NOT NULL | 茎残留 P 浓度 (kg/kg) | `PRESIDST` |
| `presidrt` | DECIMAL(8,6) | NOT NULL | 根残留 P 浓度 (kg/kg) | `PRESIDRT` |
| `kresidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 K 浓度 (kg/kg) | `KRESIDLV` |
| `kresidst` | DECIMAL(8,6) | NOT NULL | 茎残留 K 浓度 (kg/kg) | `KRESIDST` |
| `kresidrt` | DECIMAL(8,6) | NOT NULL | 根残留 K 浓度 (kg/kg) | `KRESIDRT` |
| `npk_translrt_fr` | DECIMAL(5,4) | NOT NULL | 根转运占茎叶转运比例 | `NPK_TRANSLRT_FR` |

**转运逻辑**: 可转运量 = 器官当前 NPK 量 - 器官干重 × 残留浓度。按 TCNT/TCPT/TCKT 时间系数向贮存器官转运。

#### P4. n_stress_parameters — N 胁迫参数 (WOFOST 8.1 N only)

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `nmaxlv_tb_afgen_id` | INT | FK → afgen_tables.id | 叶最大 N 浓度 (DVS) | `NMAXLV_TB` |
| `nsllv_tb_afgen_id` | INT | FK → afgen_tables.id | N 胁迫叶衰老因子 | `NSLLV_TB` |
| `nmaxrt_fr` | DECIMAL(5,4) | NOT NULL | 根最大 N 浓度比例 | `NMAXRT_FR` |
| `nmaxst_fr` | DECIMAL(5,4) | NOT NULL | 茎最大 N 浓度比例 | `NMAXST_FR` |
| `nmaxso` | DECIMAL(8,6) | NOT NULL | 贮存器官最大 N 浓度 | `NMAXSO` |
| `nresidlv` | DECIMAL(8,6) | NOT NULL | 叶残留 N 浓度 | `NRESIDLV` |
| `nresidst` | DECIMAL(8,6) | NOT NULL | 茎残留 N 浓度 | `NRESIDST` |
| `rgrlai_min` | DECIMAL(6,4) | NOT NULL | 最大 N 胁迫下最小 RGRLAI | `RGRLAI_MIN` |
| `rgrlai` | DECIMAL(6,4) | NOT NULL | (复用) LAI 相对增长率 | `RGRLAI` |

---

### Q. SNOMIN 土壤碳氮平衡

> 来源: SNOMIN 模块
> 论文: Berghuijs et al. (2024) European Journal of Agronomy 154
>
> 分层土壤 C/N 模型，处理有机质分解（矿化/固定）、铵态氮硝化、硝酸盐反硝化、氨挥发、雨水沉降、层间水流交换、作物吸收。

#### Q1. snomin_parameters — SNOMIN 全局参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `site_id` | INT | FK → sites.id, UNIQUE | 关联站点 | |
| `a0som` | DECIMAL(5,2) | NOT NULL | 初始土壤有机质年龄 (y) | `A0SOM` |
| `cn_ratio_bio` | DECIMAL(5,2) | NOT NULL | 微生物生物量 C:N 比 (kg/kg) | `CNRatioBio` |
| `fasdis` | DECIMAL(5,4) | NOT NULL | 同化→异化分配比例 | `FASDIS` |
| `kdenit_ref` | DECIMAL(8,6) | NOT NULL | 参考反硝化一级速率常数 (d⁻¹) | `KDENIT_REF` |
| `knit_ref` | DECIMAL(8,6) | NOT NULL | 参考硝化一级速率常数 (d⁻¹) | `KNIT_REF` |
| `ksorp` | DECIMAL(8,6) | NOT NULL | 铵态氮吸附系数 (m³水/kg土) | `KSORP` |
| `mrcdiss` | DECIMAL(8,6) | NOT NULL | 反硝化 Michaelis-Menten 常数 (kg C/m²/d) | `MRCDIS` |
| `no3_conc_r` | DECIMAL(6,4) | NOT NULL | 雨水 NO₃-N 浓度 (mg N/L) | `NO3ConcR` |
| `nh4_conc_r` | DECIMAL(6,4) | NOT NULL | 雨水 NH₄-N 浓度 (mg N/L) | `NH4ConcR` |
| `wfps_crit` | DECIMAL(5,4) | NOT NULL | 反硝化临界充水孔隙度 (m³/m³) | `WFPS_CRIT` |

#### Q2. snomin_layer_initial — SNOMIN 逐层初始值

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `site_id` | INT | FK → sites.id, NOT NULL | | |
| `layer_index` | INT | NOT NULL | 层序号 | |
| `no3_i` | DECIMAL(10,3) | NOT NULL | 初始 NO₃-N (kg N/ha) | `NO3I[i]` |
| `nh4_i` | DECIMAL(10,3) | NOT NULL | 初始 NH₄-N (kg N/ha) | `NH4I[i]` |

UNIQUE KEY: `(site_id, layer_index)`

#### Q3. SNOMIN 变量语义

**状态变量** (每层×每 amendment):
- `AGE` — 有机添加物表观年龄 (d)，决定分解速率
- `ORGMAT` — 有机质含量 (kg OM/ha)
- `CORG` — 有机碳含量 (kg C/ha)
- `NORG` — 有机氮含量 (kg N/ha)

**状态变量** (每层):
- `NH4` — 铵态氮 (kg NH₄-N/ha)
- `NO3` — 硝态氮 (kg NO₃-N/ha)

**发布状态** (每日输出):
- `NAVAIL` — 根系层有效 N 总量 (kg N/ha)，驱动作物 N 吸收
- `ORGMATT` — 全剖面有机质总量 (kg/ha)
- `CORGT` — 全剖面有机碳总量 (kg/ha)
- `NORGT` — 全剖面有机氮总量 (kg/ha)
- `NLOSSCUM` — 累积 N 损失 (反硝化+NH₄淋溶+NO₃淋溶) (kg N/ha)

**关键速率**:
- `RNH4MIN` — 净矿化速率 (kg NH₄-N/ha/d)
- `RNH4NITR` — 硝化速率 (kg NH₄-N→NO₃-N/ha/d)
- `RNO3DENITR` — 反硝化速率 (kg NO₃-N→N₂/ha/d)
- `RNH4UP` / `RNO3UP` — 作物吸收速率 (kg N/ha/d)
- `RNH4IN/OUT` / `RNO3IN/OUT` — 层间水流交换速率

**质量平衡检查** (SNOMIN 内部):
- 有机质: `sum(ΔORGMAT) = -sum(RORGMATDIS) + sum(RORGMATAM)`
- NH₄-N: `sum(ΔNH4) = sum(RNH4AM + RNH4MIN + RNH4DEPOS - RNH4NITR - RNH4UP + RNH4IN - RNH4OUT)`
- NO₃-N: `sum(ΔNO3) = sum(RNO3AM + RNO3NITR + RNO3DEPOS - RNO3DENITR - RNO3UP + RNO3IN - RNO3OUT)`

---

### R. 站点参数 (site parameters)

> 站点参数集合了土壤初始化以外、与地理位置/管理相关的全局参数。
> 不同模型需要不同的站点参数子集。

#### sites — 站点

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | INT | PK | |
| `site_code` | VARCHAR(32) | UNIQUE, NOT NULL | 站点代码 |
| `site_name` | VARCHAR(128) | NOT NULL | 站点名称 |
| `station_id` | INT | FK → weather_stations.id | 默认气象站 |
| `soil_id` | INT | FK → soil_profiles.id | 默认土壤 |
| `co2_concentration` | DECIMAL(6,1) | DEFAULT 420.0 | 大气 CO₂ 浓度 (ppm) |
| `description` | TEXT | | |

#### classic_site_parameters — 经典 WOFOST 站点参数

> 用于 Wofost72/73 WLP 配置 (classic_waterbalance + SNOMIN free 之前)

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `site_id` | INT | FK → sites.id, UNIQUE | | |
| `ifunrn` | TINYINT | NOT NULL, DEFAULT 1 | 是否使用非均匀根分布 (0/1) | `IFUNRN` |
| `notinf` | DECIMAL(5,2) | NOT NULL | 最大非下渗降雨分数 | `NOTINF` |
| `ssmax` | DECIMAL(6,2) | NOT NULL | 地表最大蓄水量 (cm) | `SSMAX` |
| `ssi` | DECIMAL(6,4) | NOT NULL | 初始地表蓄水量 (cm) | `SSI` |
| `wav` | DECIMAL(6,2) | NOT NULL | 初始可用水量 (cm) | `WAV` |
| `smlim` | DECIMAL(5,4) | NOT NULL | 根伸长下限含水量 | `SMLIM` |
| `nsoilbase` | DECIMAL(8,2) | | 土壤基础 N 供应 (kg/ha) — N limited | `NSOILBASE` |
| `navaili` | DECIMAL(8,2) | | 初始有效 N (kg/ha) — N limited | `NAVAILI` |
| `bg_n_supply` | DECIMAL(8,2) | | 背景 N 矿化速率 (kg/ha/d) — NPK | `BG_N_SUPPLY` |
| `bg_p_supply` | DECIMAL(8,2) | | 背景 P 矿化速率 (kg/ha/d) — NPK | `BG_P_SUPPLY` |
| `bg_k_supply` | DECIMAL(8,2) | | 背景 K 矿化速率 (kg/ha/d) — NPK | `BG_K_SUPPLY` |

#### snomin_site_parameters — SNOMIN 站点参数

> SNOMIN 全局参数已在上方 §Q1 定义。此表记录与站点其他配置的关联。

同 `snomin_parameters` (Q1) 表，外键 `site_id`。

---

### S. 信号日志 (signal log)

> 记录模拟过程中所有分发的信号，用于审计和回溯。

#### signal_log — 信号日志

| 列名 | 类型 | 约束 | 说明 |
|------|------|------|------|
| `id` | BIGINT | PK | |
| `run_id` | INT | FK → simulation_runs.id, NOT NULL | |
| `signal_date` | DATE | NOT NULL | 信号触发日期 |
| `signal_name` | VARCHAR(32) | NOT NULL | 信号名 |
| `signal_source` | VARCHAR(64) | | 信号来源 (TIMED/STATE/PHENOLOGY/SOIL) |
| `signal_params` | JSON | | 信号携带的参数 (JSON) |
| `created_at` | DATETIME | DEFAULT NOW() | |

INDEX: `(run_id, signal_date)`

**全部信号类型**:

| 信号名 | 说明 | 来源 |
|--------|------|------|
| `crop_start` | 作物开始 | AgroManager/CropCalendar |
| `crop_finish` | 作物结束 | Phenology/CropCalendar (maturity/harvest/earliest) |
| `crop_emerged` | 出苗 | Phenology |
| `terminate` | 模拟终止 | Engine/AgroManager |
| `output` | 输出每日数据 | Engine (按 OUTPUT_INTERVAL) |
| `summary_output` | 输出季节总结 | Engine (crop_finish 时) |
| `terminal_output` | 输出终端统计 | Engine (terminate 时) |
| `irrigate` | 灌溉 | TimedEvents/StateEvents/AgroManager |
| `apply_n` | 施氮 | TimedEvents/StateEvents (→ N_Demand_Uptake) |
| `apply_p` | 施磷 | TimedEvents/StateEvents (→ NPK_Demand_Uptake) |
| `apply_k` | 施钾 | TimedEvents/StateEvents (→ NPK_Demand_Uptake) |
| `apply_n_snomin` | SNOMIN 有机肥/C:N 施用 | TimedEvents/StateEvents (→ SNOMIN) |
| `mow` | 刈割 (牧草) | TimedEvents (→ LINGRA) |
| `spray` | 喷药 | TimedEvents |

---

### T. LINTUL3 专用参数

> 来源: LINTUL3 模块
>
> LINTUL3 是光能利用效率 (LUE) 模型，与 WOFOST 的光合-呼吸模型不同。含氮胁迫，不含水分胁迫 (水稻模型)。

#### lintul3_parameters — LINTUL3 专用参数

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `lue` | DECIMAL(6,4) | NOT NULL | 光能利用效率 (g DM/MJ PAR) | `LUE` |
| `k` | DECIMAL(5,3) | NOT NULL | 冠层消光系数 (m²/m²) | `K` |
| `slac` | DECIMAL(6,4) | NOT NULL | 比叶面积常数 (m²/g) | `SLAC` |
| `rgrl` | DECIMAL(6,4) | NOT NULL | 指数期 LAI 相对增长率 (°C/d) | `RGRL` |
| `rootdm` | DECIMAL(5,2) | NOT NULL | 最大根深 (m) | `ROOTDM` |
| `rrdmax` | DECIMAL(5,2) | NOT NULL | 最大根深日增率 (m/d) | `RRDMAX` |
| `tbase` | DECIMAL(5,2) | NOT NULL | 基础温度 (°C) | `TBASE` |
| `tsumag` | DECIMAL(7,1) | NOT NULL | 叶片衰老温度累积 (°C·d) | `TSUMAG` |
| `laicr` | DECIMAL(5,2) | NOT NULL | 自遮荫临界 LAI | `LAICR` |
| `rdrshm` | DECIMAL(6,4) | NOT NULL | 遮荫致死最大相对速率 (1/d) | `RDRSHM` |
| `rdrns` | DECIMAL(6,4) | NOT NULL | N 胁迫叶死亡相对速率 (1/d) | `RDRNS` |
| `rdrrt` | DECIMAL(6,4) | NOT NULL | 根死亡相对速率 (1/d) | `RDRRT` |
| `dvsdr` | DECIMAL(4,3) | NOT NULL | 叶/根死亡起始 DVS | `DVSDR` |
| `dvsnlt` | DECIMAL(4,3) | NOT NULL | 养分吸收停止 DVS | `DVSNLT` |
| `dvsnt` | DECIMAL(4,3) | NOT NULL | N 转运起始 DVS | `DVSNT` |
| `fntrt` | DECIMAL(5,4) | NOT NULL | 根 N 转运占总转运比例 | `FNTRT` |
| `frnx` | DECIMAL(5,4) | NOT NULL | 临界/最大 N 浓度比 | `FRNX` |
| `lrnr` | DECIMAL(5,4) | NOT NULL | 根最大 N 浓度(占叶比例) | `LRNR` |
| `lsnr` | DECIMAL(5,4) | NOT NULL | 茎最大 N 浓度(占叶比例) | `LSNR` |
| `nmaxso` | DECIMAL(6,4) | NOT NULL | 贮存器官最大 N 浓度 (g/g) | `NMAXSO` |
| `nlai` | DECIMAL(5,4) | NOT NULL | N 胁迫 LAI 削减系数 | `NLAI` |
| `nlue` | DECIMAL(5,4) | NOT NULL | N 胁迫 LUE 削减系数 | `NLUE` |
| `npart` | DECIMAL(5,4) | NOT NULL | N 胁迫分配修正系数 | `NPART` |
| `nsla` | DECIMAL(5,4) | NOT NULL | N 胁迫 SLA 削减系数 | `NSLA` |
| `rnflv` | DECIMAL(6,4) | NOT NULL | 叶残留 N 浓度 (g/g) | `RNFLV` |
| `rnfrt` | DECIMAL(6,4) | NOT NULL | 根残留 N 浓度 (g/g) | `RNFRT` |
| `rnfst` | DECIMAL(6,4) | NOT NULL | 茎残留 N 浓度 (g/g) | `RNFST` |
| `tcnt` | DECIMAL(5,2) | NOT NULL | N 转运时间系数 (d) | `TCNT` |
| `tranco` | DECIMAL(6,2) | NOT NULL | 蒸腾常数 (mm/d) | `TRANCO` |
| `wcfc` | DECIMAL(5,4) | NOT NULL | 田间持水量 (m³/m³) | `WCFC` |
| `wcst` | DECIMAL(5,4) | NOT NULL | 饱和含水量 (m³/m³) | `WCST` |
| `wcwet` | DECIMAL(5,4) | NOT NULL | 氧胁迫临界含水量 (m³/m³) | `WCWET` |
| `wcwp` | DECIMAL(5,4) | NOT NULL | 萎蔫点 (m³/m³) | `WCWP` |
| `wmfac` | BOOLEAN | DEFAULT FALSE | 淹水管理 (0=灌溉至FC, 1=灌溉至饱和) | `WMFAC` |
| `rnmin` | DECIMAL(6,4) | NOT NULL | 土壤矿化速率 (g N/m²/d) | `RNMIN` |
| `rootdi` | DECIMAL(5,2) | NOT NULL | 初始根深 (m) | `ROOTDI` |
| `wci` | DECIMAL(5,4) | NOT NULL | 初始土壤含水量 (m³/m³) | `WCI` |
| `nfrlvi` | DECIMAL(6,4) | NOT NULL | 叶初始 N 浓度 (g N/g DM) | `NFRLVI` |
| `nfrrti` | DECIMAL(6,4) | NOT NULL | 根初始 N 浓度 (g N/g DM) | `NFRRTI` |
| `nfrsti` | DECIMAL(6,4) | NOT NULL | 茎初始 N 浓度 (g N/g DM) | `NFRSTI` |
| `wlvgi` | DECIMAL(8,2) | NOT NULL | 初始绿叶重 (g/m²) | `WLVGI` |
| `wsti` | DECIMAL(8,2) | NOT NULL | 初始茎重 (g/m²) | `WSTI` |
| `wrtli` | DECIMAL(8,2) | NOT NULL | 初始根重 (g/m²) | `WRTLI` |
| `wsoi` | DECIMAL(8,2) | NOT NULL | 初始贮存器官重 (g/m²) | `WSOI` |

#### lintul3_partitioning_factors — LINTUL3 分配系数

> LINTUL3 的分配系数变量名和语义与 WOFOST 不同（FLV/FRT/FSO/FST vs FR/FL/FS/FO），需独立存储。

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, NOT NULL | | |
| `dvs` | DECIMAL(5,3) | NOT NULL | 发育阶段 DVS | |
| `flv` | DECIMAL(5,4) | NOT NULL | 叶分配系数 | `FLVTB(DVS)` |
| `frt` | DECIMAL(5,4) | NOT NULL | 根分配系数 | `FRTTB(DVS)` |
| `fso` | DECIMAL(5,4) | NOT NULL | 贮存器官分配系数 | `FSOTB(DVS)` |
| `fst` | DECIMAL(5,4) | NOT NULL | 茎分配系数 | `FSTTB(DVS)` |
| `sort_order` | INT | NOT NULL | DVS 排序 |

UNIQUE KEY: `(variety_id, dvs)`

**LINTUL3 关键公式**:
- 光截获: `PARINT = 0.5 × DTR × (1 - exp(-K × LAI))`
- 总生长: `RGROWTH = LUE × PARINT × min(TRANRF, exp(-NLUE×(1-NNI)))`
- NNI: `(N_concentration - N_residual) / (N_critical - N_residual)`
- 根深增长: `RROOTD = min(RRDMAX, ROOTDM - ROOTD)` if WC > WCWP

**LINTUL3 与 WOFOST 对比**:
- 无光合-呼吸模块（LUE 替代）
- 无 Afgen 驱动的 AMAX/EFF 参数
- 干物质分配用 4 条 Afgen (FLVTB/FRTTB/FSOTB/FSTTB) 而非 WOFOST 的 FRTB/FLTB/FSTB/FOTB
- 土壤水分模块简化 (Lintul3Soil)
- N 矿化只有背景速率 RNMIN，无 SNOMIN 完整的 C/N 动力学

---

### U. ALCEPAS 洋葱模型参数

> 来源: ALCEPAS 模块
> 论文: De Visser (1994) Journal of Horticultural Science
>
> ALCEPAS 是 SUCROS87 衍生模型，专门用于洋葱潜在产量模拟。包含 7 个子模块。

#### alcepas_parameters — ALCEPAS 专用参数

**顶层参数 (ALCEPAS.Parameters)**:

| 列名 | 类型 | 约束 | 说明 | 参数名 |
|------|------|------|------|---------|
| `id` | INT | PK | | |
| `variety_id` | INT | FK → varieties.id, UNIQUE | | |
| `asrqso` | DECIMAL(6,4) | NOT NULL | 同化物→鳞茎需求 (kg CH₂O/kg DM) | `ASRQSO` |
| `asrqrt` | DECIMAL(6,4) | NOT NULL | 同化物→根需求 (kg CH₂O/kg DM) | `ASRQRT` |
| `asrqlv` | DECIMAL(6,4) | NOT NULL | 同化物→叶需求 (kg CH₂O/kg DM) | `ASRQLV` |

**物候 (alcepas.Phenology)**:

| 列名 | 说明 | 参数名 |
|------|------|---------|
| `tbas` | 发育基础温度 (°C) | `TBAS` |
| `bol50` | 营养期→生殖期积温 (°C·d) | `BOL50` |
| `fall50` | 生殖期→成熟积温 (°C·d) | `FALL50` |
| `tsopk` | 播种→出苗积温 (°C·d) | `TSOPK` |
| `tbase` | 出苗基础温度 (°C) | `TBASE` |
| `crop_start_type` | 起点类型 | `CROP_START_TYPE` |
| `crop_end_type` | 终点类型 | `CROP_END_TYPE` |

> ALCEPAS 物候独特之处: 营养期 DVR 含光周期 (DAGTB) 和辐射截获 (RVRTB) 修正; 用 Bolting/Flowering 双阶段积温阈值

**光合 (alcepas.Assimilation)**:

| 列名 | 说明 | 参数名 |
|------|------|---------|
| `amx` | 最大同化率 (kg CO₂/ha/hr) | `AMX` |
| `eff` | 光能利用效率 (kg CO₂/J) | `EFF` |
| `kdif` | 散射光消光系数 | `KDIF` |

**叶片 (alcepas.LeafDynamics)** — 含 15+ 独特参数 (AGE 系列/LA0/NPL/SLAN/SLAR/GTSLA 等):

| 列名 | 说明 | 参数名 |
|------|------|---------|
| `nagecor` | 生理年龄校正因子 | `AGECOR` |
| `nmetcor` | 代谢校正因子 | `METCOR` |
| `agea` | 叶片寿命公式参数 A | `AGEA` |
| `ageb` | 叶片寿命公式参数 B | `AGEB` |
| `agec` | 叶片寿命公式参数 C | `AGEC` |
| `aged` | 叶片寿命公式参数 D | `AGED` |
| `lagr` | 指数→线性 LAI 转换临界值 | `LAGR` |
| `gegr` | LAGR 对应的总干物重 (kg/ha) | `GEGR` |
| `la0` | 单株出苗 LAI | `LA0` |
| `npl` | 植株密度 (plants/m²) | `NPL` |
| `rgrl` | LAI 指数增长相对速率 | `RGRL` |
| `gtsla` | SLA 随 DVS 变化的曲率因子 | `GTSLA` |
| `ttop` | 最大光合有效温度 (°C) | `TTOP` |
| `tbase` | 叶片衰老基础温度 (°C) | `TBASE` |
| `corfac` | 日长对叶龄校正因子 | `CORFAC` |
| `tbas` | 发育基础温度 (复用) | `TBAS` |

**呼吸 (alcepas.Respiration)** — Q10 基准温度为 20°C (不同于 WOFOST 的 25°C)

**独特状态**:
- `BULBSUM` — 鳞茎形成积温累积 (°C·d)
- `BULB` — 鳞茎指数 (0-100, Gompertz 函数)
- `DOB50` / `DOF50` — 50% bolting/flowering 日期

---

## 4. 种植方案生成流程

基于上述数据库，生成一份完整种植方案的查询链路：

```
┌─────────────────────────────────────────────────────────┐
│ Step 1: 选择作物和品种                                     │
│  crops JOIN varieties → 确定品种参数集                      │
│                                                         │
│ Step 2: 确定生育期                                         │
│  phenology_parameters → TSUM1/TSUM2/IDSL/TBASEM         │
│  结合 weather_daily → 逐日积温 → 预测各生育期日期            │
│                                                         │
│ Step 3: 制定水肥方案                                       │
│  planting_plans + timed_events + state_events            │
│  + snomin_fertilizer_events                              │
│  → 播种日期 + 灌溉时间表 + 施肥时间表 (无机+有机)            │
│                                                         │
│ Step 4: 输入土壤 & 站点参数                                 │
│  soil_profiles + soil_layers → SMFCF/SMW/SM0/RDMSOL     │
│  site_parameters → IFUNRN/NOTINF/SSMAX/SMLIM/CO2        │
│  snomin_parameters (+ layer_initial) → C/N 循环参数      │
│                                                         │
│ Step 5: 选择模型配置                                        │
│  model_configurations → 配置模型类 → 组装模块               │
│  传入: 品种参数 + 土壤 + 气象 + 农事 + 站点 → 启动逐日模拟    │
│                                                         │
│ Step 6: 运行模拟 → 逐日输出                                  │
│  模拟写入 signal_log + simulation_daily_output            │
│                                                         │
│ Step 7: 输出种植方案                                       │
│  播种日期 / 出苗日期 / 开花日期 / 成熟日期                   │
│  + 各阶段灌水计划 (+ 灌溉量)                                │
│  + 各阶段施肥计划 (N/P/K 用量 + 时间 + 有机肥C:N)           │
│  + 预期产量 (TWSO / TAGP / HI)                           │
│  + 风险提示 (水分胁迫天数 / 氧胁迫天数 / NNI / NPKI / N损失)  │
│  + 土壤碳氮变化 (有机质分解 / 矿化 / 反硝化 / 淋溶)          │
└─────────────────────────────────────────────────────────┘
```

### 每日模拟核心循环 (对标 Engine._run)

```
① 气象驱动 → weather_daily (TMAX/TMIN/IRRAD/RAIN/ET0...)
② 物候 → calc DVR, integrate DVS → 判定 STAGE (emerging/vegetative/reproductive/mature)
③ 光合同化 → totass(DVS, LAI, ...) → PGASS (或 LINTUL3: LUE×PARINT → RGROWTH)
④ 蒸散 → EVWMX/EVSMX/TRAMX → RFTRA → TRA
⑤ 水胁迫 → GASS = PGASS × RFTRA (WOFOST) 或 TRANRF (LINTUL3)
⑥ 维持呼吸 → PMRES = f(WRT,WLV,WST,WSO, TEMP) → MRES = min(GASS, PMRES)
⑦ 净同化物 → ASRC = GASS - MRES (LINTUL3 跳过⑥⑦)
⑧ NPK 胁迫 → NPK_Stress: NNI/PNI/KNI/NPKI → RFNPK → 修正 LAI/LUE (8.1/LINTUL3)
⑨ 分配 → DMI = CVF × ASRC → ADMI = (1-FR) × DMI
⑩ 器官增长 → GRRT/GRST/GRLV/GRSO → integrate WRT/WST/WLV/WSO
⑪ 叶片衰老 → DSLV1(水)/DSLV2(遮荫)/DSLV3(霜冻)/DSLV4(养分)/DALV(年龄) → DRLV
⑫ 根系下扎 → RD += RR (受 RDM 上限约束)
⑬ 土壤水分 → WC/SM update (降雨 + 灌溉 - 蒸散 - 深层渗漏 - 层间流)
⑭ NPK 吸收/转运 → N/P/K demand→uptake(从 NAVAIL/PAVAIL/KAVAIL)→translocation→SO
⑮ SNOMIN C/N → organic dissimilation(+AGE) → mineralisation → nitrification → denitrification → leaching
⑯ 农事管理 → crop_calendar + timed_events + state_events
⑰ 信号记录 → INSERT signal_log
⑱ 输出保存 → INSERT simulation_daily_output
```

---

## 5. 种子数据清单

### 5.1 作物 (crops)

| crop_code | 中文名 | model_class | crop_type | base_temperature |
|-----------|--------|-------------|-----------|-----------------|
| wheat | 小麦 | Wofost72 | cereal | 0.0 |
| maize | 玉米 | Wofost72 | cereal | 8.0 |
| potato | 马铃薯 | Wofost72 | root_tuber | 4.0 |
| barley | 大麦 | Wofost72 | cereal | 0.0 |
| rice | 水稻 | Wofost72 | cereal | 10.0 |
| soybean | 大豆 | Wofost72 | legume | 6.0 |
| sugar_beet | 甜菜 | Wofost72 | root_tuber | 3.0 |
| sunflower | 向日葵 | Wofost72 | cereal | 6.0 |
| ryegrass | 黑麦草 | LINGRA | grass | 0.0 |
| spring_wheat | 春小麦 | LINTUL3 | cereal | 0.0 |
| onion | 洋葱 | ALCEPAS | vegetable | 6.0 |
| tomato | 番茄 | Wofost72 | vegetable | 10.0 |

### 5.2 生育期阶段 (phenology_stages)

每个作物预设 4 个阶段：emerging / vegetative / reproductive / mature

### 5.3 土壤 (soil_profiles)

| soil_code | 中文名 | SMFCF | SMW | SM0 |
|-----------|--------|-------|-----|-----|
| coarse_sand | 粗砂 | 0.15 | 0.02 | 0.40 |
| loamy_sand | 壤砂 | 0.20 | 0.04 | 0.42 |
| sandy_loam | 砂壤 | 0.28 | 0.08 | 0.45 |
| silt_loam | 粉砂壤 | 0.35 | 0.12 | 0.48 |
| loam | 壤土 | 0.32 | 0.10 | 0.46 |
| clay_loam | 粘壤 | 0.38 | 0.15 | 0.50 |
| clay | 粘土 | 0.42 | 0.20 | 0.55 |

### 5.4 光合常数 (photosynthesis_constants)

| constant_name | value | description |
|---------------|-------|-------------|
| SCV | 0.2 | 散射系数 (可见光叶片散射) |
| CH2O_CO2_ratio | 0.6818 | 转换系数 (30/44 = kg CH₂O per kg CO₂) |

### 5.5 模型配置 (model_configurations)

所有 19 个配置见上方 §M 完整清单。

### 5.6 信号 (signal_types)

14 种信号类型见上方 §S。

---

## 附录: 变量依赖关系图

```
DVS ──→ AMAXTB, KDIFTB, SLATB, SSATB, RDRSTB, RDRRTB, RFSETB, FRTB, FLTB, FSTB, FOTB
        NMAXLV_TB, PMAXLV_TB, KMAXLV_TB, NSLLV_TB
        (物候驱动几乎所有其他模块)

LAI ──→ EVWMX, EVSMX, TRAMX, Assimilation, DSLV2(自遮荫死亡), PARINT(LINTUL3)

SM  ──→ RFWS, RFTRA, TRA
WC  ──→ TRAN(LINTUL3), 多层WB层间流, SNOMIN硝化/反硝化(WFPS)

TRA + TRAMX ──→ RFTRA ──→ GASS(水胁迫同化) + DSLV1(叶水胁迫死亡)

ADMI ──→ GRST, GRLV, GRSO (地上部器官增长)
DMI  ──→ GRRT (根系增长)

WRT, WLV, WST, WSO ──→ PMRES (维持呼吸)
GASS, PMRES ──→ ASRC ──→ DMI ──→ 循环

FR ──→ GRRT + 地上/地下分配
FL ──→ ADMI 叶部分
FS ──→ ADMI 茎部分
FO ──→ ADMI 贮存器官部分

NamountLV,NamountST,NamountSO,NamountRT ──→ NNI,PNI,KNI ──→ NPKI ──→ RFNPK
NAVAIL ──→ RNuptake ──→ NamountLV/ST/RT/SO
NamountLV/ST/RT (above residual) ──→ Ntranslocatable ──→ RNuptakeSO

NH4, NO3, SM, TEMP ──→ RNH4MIN, RNH4NITR, RNO3DENITR ──→ NAVAIL (SNOMIN)
CORG, NORG ──→ RCORGDIS, RNORGDIS ──→ CO₂ emission, NH4 mineralisation
```

---

*文档版本: 2.0*
*文档版本: 2.1*
*新增: NPK 养分动态 (P), SNOMIN C/N 平衡 (Q), 站点参数 (R), 信号日志 (S), LINTUL3 (T), ALCEPAS (U)*
