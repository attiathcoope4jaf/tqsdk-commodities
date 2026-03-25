# tqsdk-commodities 商品期货策略库

> 基于 [TqSdk（天勤量化）](https://doc.shinnytech.com/tqsdk/latest/) 的商品期货量化策略集合。  
> 涵盖金属、农产品、能源化工等板块的趋势跟踪、均值回归、跨品种对冲等多类策略。

---

## 📋 策略列表

| 编号 | 文件名 | 策略名称 | 品种 | 核心思路 | 上线日期 |
|------|--------|----------|------|----------|----------|
| 01 | [01_cu_trend_follow.py](strategies/01_cu_trend_follow.py) | 铜趋势跟踪策略 | 铜 Cu | 双均线趋势跟踪，10/30日均线金叉死叉 | 2026-03-02 |
| 02 | [02_m_mean_reversion.py](strategies/02_m_mean_reversion.py) | 豆粕均值回归策略 | 豆粕 m | 布林带均值回归，价格触及下轨买入 | 2026-03-02 |
| 03 | [03_sc_trend.py](strategies/03_sc_trend.py) | 原油趋势策略 | 原油 SC | 基于MACD的趋势跟随 | 2026-03-03 |
| 04 | [04_m_breakout.py](strategies/04_m_breakout.py) | 豆粕突破策略 | 豆粕 m | 布林带突破策略 | 2026-03-03 |
| 05 | [05_cu_triple_ma.py](strategies/05_cu_triple_ma.py) | 铜三重均线策略 | 铜 Cu | 三均线过滤趋势交易 | 2026-03-04 |
| 06 | [06_sr_boll_breakout.py](strategies/06_sr_boll_breakout.py) | 铁矿石布林突破 | 铁矿石 i | 布林带+ATR双重过滤突破 | 2026-03-04 |
| 07 | [07_cf_trend_follow.py](strategies/07_cf_trend_follow.py) | 棉花趋势跟踪 | 棉花 CF | ATR动态止损趋势策略 | 2026-03-04 |
| 08 | [08_c_range.py](strategies/08_c_range.py) | 玉米区间策略 | 玉米 C | 价格区间突破策略 | 2026-03-04 |
| 09 | [09_cu_inter_temporal.py](strategies/09_cu_inter_temporal.py) | 铜跨周期策略 | 铜 Cu | 日线+4H共振趋势 | 2026-03-04 |
| 10 | [10_y_p_spread.py](strategies/10_y_p_spread.py) | 豆油-棕榈油跨品种策略 | 豆油/棕榈油 | 产业链跨品种对冲 | 2026-03-04 |
| 11 | [11_ag_mean_reversion.py](strategies/11_ag_mean_reversion.py) | 白银均值回归 | 白银 AG | RSI超卖均值回归 | 2026-03-05 |
| 12 | [12_sc_multi_timeframe.py](strategies/12_sc_multi_timeframe.py) | 原油多周期策略 | 原油 SC | 日线+4H+1H三周期 | 2026-03-05 |
| 13 | [13_al_boll_breakout.py](strategies/13_al_boll_breakout.py) | 铝布林突破 | 铝 AL | 布林带突破+成交量确认 | 2026-03-06 |
| 14 | [14_zn_breakout.py](strategies/14_zn_breakout.py) | 锌突破策略 | 锌 ZN | 趋势线突破策略 | 2026-03-06 |
| 15 | [15_sr_boll_band.py](strategies/15_sr_boll_band.py) | 铁矿石布林带策略 | 铁矿石 SR | 布林带宽度收缩突破 | 2026-03-09 |
| 16 | [16_cf_ma_crossover.py](strategies/16_cf_ma_crossover.py) | 棉花均线交叉 | 棉花 CF | 均线交叉趋势策略 | 2026-03-09 |
| 17 | [17_i_boll_trend.py](strategies/17_i_boll_trend.py) | 铁矿石布林趋势 | 铁矿石 I | 布林带中轨趋势跟踪 | 2026-03-11 |
| 17 | [17_zn_ma_crossover.py](strategies/17_zn_ma_crossover.py) | 锌均线交叉 | 锌 ZN | 多均线交叉策略 | 2026-03-11 |
| 18 | [18_cf_momentum.py](strategies/18_cf_momentum.py) | 棉花动量策略 | 棉花 CF | 动量指标交易策略 | 2026-03-11 |
| 18 | [18_ru_rsi_strategy.py](strategies/18_ru_rsi_strategy.py) | 橡胶RSI策略 | 橡胶 RU | RSI超买超卖交易 | 2026-03-11 |
| 19 | [19_rb_hc_spread.py](strategies/19_rb_hc_spread.py) | 螺纹-热卷跨品种对冲 | 螺纹钢/热卷 | 螺纹钢-热卷跨品种套利 | 2026-03-13 |
| 20 | [20_ru_multi_factor.py](strategies/20_ru_multi_factor.py) | 橡胶多因子策略 | 橡胶 RU | 多因子综合打分策略 | 2026-03-13 |
| 21 | [21_rb_i_spread.py](strategies/21_rb_i_spread.py) | 螺纹-铁矿套利 | 螺纹钢/铁矿 | 产业链跨品种套利 | 2026-03-16 |
| 22 | [22_rb_three_factor.py](strategies/22_rb_three_factor.py) | 螺纹钢三因子策略 | 螺纹钢 RB | 动量+波动率+趋势三因子 | 2026-03-16 |
| 23 | [23_rb_cross_sectional_momentum.py](strategies/23_rb_cross_sectional_momentum.py) | 螺纹钢截面动量策略 | 黑色系5品种 | 截面动量，做多最强做空最弱 | 2026-03-17 |
| 24 | [24_metal_hedge.py](strategies/24_metal_hedge.py) | 金属板块跨品种对冲 | 铜/铝/锌/镍 | 金属板块协整套利 | 2026-03-17 |
| 25 | [25_agri_multi_timeframe.py](strategies/25_agri_multi_timeframe.py) | 农产品跨周期动量策略 | 豆粕/玉米/棉花 | 日线+4H双周期共振动量 | 2026-03-18 |
| 26 | [26_commodity_multi_factor.py](strategies/26_commodity_multi_factor.py) | 商品期货多因子截面策略 | 6品种综合 | 动量+低波+趋势三因子截面排序 | 2026-03-18 |
| 27 | [27_cu_al_zn_calendar_spread.py](strategies/27_cu_al_zn_calendar_spread.py) | 有色金属跨期价差与Carry套利策略 | 铜/铝/锌 | 近远月价差z-score均值回归，三品种跨期套利 | 2026-03-23 |
| 28 | [28_energy_agri_intermarket_hedge.py](strategies/28_energy_agri_intermarket_hedge.py) | 能源-农产品跨市场对冲策略 | 原油/燃料油/豆油/棕榈油 | 板块动量排名轮动+原油豆油替代逻辑对冲 | 2026-03-23 |
| 31 | [31_chem_cross_momentum_term_structure.py](strategies/31_chem_cross_momentum_term_structure.py) | 化工系截面动量与期限结构择时策略 | 甲醇/塑料/PP/PTA/沥青 | 双维度截面打分：动量因子(60%)+期限结构因子(40%)，每周截面排名调仓 | 2026-03-25 |
| 32 | [32_agri_climate_inventory_hedge.py](strategies/32_agri_climate_inventory_hedge.py) | 农产品气候因子与库存周期对冲策略 | 豆粕/豆油/玉米/棉花/白糖 | 三因子等权打分：动量+库存周期代理+布林宽度，每周截面排名调仓 | 2026-03-25 |

---

## 🏗️ 仓库结构

```
tqsdk-commodities/
├── README.md                        # 本文档
└── strategies/                      # 策略文件目录
    ├── 01_cu_trend_follow.py        # 铜趋势跟踪
    ├── 23_rb_cross_sectional_momentum.py  # 截面动量策略
    └── 26_commodity_multi_factor.py      # 多因子截面策略
```

---

## ⚙️ 使用方法

### 安装依赖

```bash
pip install tqsdk pandas numpy
```

### 运行策略（模拟账户）

```bash
python strategies/01_cu_trend_follow.py
```

### 切换实盘账户

将策略文件中的 `TqSim()` 替换为真实账户：

```python
from tqsdk import TqAccount
api = TqApi(
    account=TqAccount("期货公司名称", "账号", "密码"),
    auth=TqAuth("天勤用户名", "天勤密码")
)
```

---

## ⚠️ 风险提示

> **本仓库内策略仅供学习研究使用，不构成任何投资建议。**  
> 期货交易存在较高风险，请在充分了解品种特性和策略逻辑后，  
> 先通过**模拟账户**或**历史回测**验证，再考虑实盘运行。  
> 实盘亏损由交易者自行承担，作者不对任何损失负责。

---

## 📅 更新日志

| 日期 | 变更 |
|------|------|
| 2026-03-25 | 新增第31、32号策略：化工系截面动量期限结构策略、农产品气候因子库存周期对冲策略 |
| 2026-03-23 | 新增第27、28号策略：跨期价差Carry套利策略、能源农产品跨市场对冲策略 |
| 2026-03-18 | 新增第25、26号策略：农产品跨周期动量策略、商品期货多因子截面策略 |
| 2026-03-17 | 新增第23、24号策略：截面动量策略、金属板块对冲策略 |
| 2026-03-16 | 新增第21、22号策略：螺纹铁矿套利、三因子策略 |
| 2026-03-13 | 新增第19、20号策略：螺纹热卷对冲、橡胶多因子 |
| 2026-03-11 | 新增第17、18号策略：布林趋势、RSI策略 |
| 2026-03-09 | 新增第15、16号策略：布林带策略、均线交叉 |
| 2026-03-06 | 新增第13、14号策略：铝布林突破、锌突破 |
| 2026-03-05 | 新增第11、12号策略：白银均值回归、原油多周期 |
| 2026-03-04 | 新增第9、10号策略：跨周期策略、豆油棕榈油对冲 |
| 2026-03-03 | 新增第3、4号策略：原油趋势、豆粕突破 |
| 2026-03-02 | 初始化仓库，上传趋势跟踪和均值回归基础策略 |

---

*Powered by [TqSdk](https://doc.shinnytech.com/tqsdk/latest/) · 天勤量化*
