"""
策略34: 化工系产业链跨品种协整均值回归策略
Chemical Sector Inter-Commodity Cointegration Mean Reversion Strategy
- 使用协整检验识别化工产业链品种对
- 计算价差的z-score，当偏离均值超过阈值时入场
- 品种: SC(原油), BU(沥青), P(棕榈油), L(塑料), PP(聚丙烯), MA(甲醇), TA(PTA), EG(乙二醇)
- 策略类型: 统计套利/均值回归
- 更新时间: 2026-03-26
"""
import numpy as np
import pandas as pd
from tqsdk import TqApi, TqAuth, TargetPosTask, TqSim
from datetime import datetime, timedelta
import statsmodels.api as sm

# ========== 配置区 ==========
# 产业链配对 (可以根据实际产业链关系调整)
PAIRS = [
    ("SHFE.sc", "DCE.bu"),   # 原油-沥青产业链
    ("DCE.bu", "DCE.l"),     # 沥青-塑料产业链
    ("DCE.l", "DCE.pp"),     # 塑料-聚丙烯产业链
    ("CZCE.ma", "CZCE.ta"),  # 甲醇-PTA产业链
    ("DCE.p", "DCE.eg"),     # 棕榈油-乙二醇(能源化工)
    ("SHFE.sc", "DCE.p"),    # 原油-棕榈油
]

# 策略参数
COINTEGRATION_WINDOW = 60    # 协整检验窗口
ZSCORE_ENTRY = 2.0          # 入场Z-score阈值
ZSCORE_EXIT = 0.5           # 出场Z-score阈值
ZSCORE_STOP = 3.0           # 止损Z-score阈值
HEDGE_RATIO_WINDOW = 20      # 对冲比率计算窗口
REBALANCE_FREQ = 5           # 套利对重新校准频率(天)
KLINE_DURATION =86400       # 日线

# 风控参数
MAX_PAIRS_ACTIVE = 3         # 最大同时活跃套利对数
MAX_POSITION_PER_LEG = 0.20 # 每条腿最大仓位
PAIR_RISK_LIMIT = 0.05      # 单对套利最大亏损(账户比例)


def zscore(series: pd.Series) -> pd.Series:
    """计算滚动Z-score"""
    mean = series.rolling(COINTEGRATION_WINDOW).mean()
    std = series.rolling(COINTEGRATION_WINDOW).std()
    return (series - mean) / (std + 1e-8)


def calculate_hedge_ratio(y: pd.Series, x: pd.Series, window: int) -> float:
    """使用滚动OLS计算对冲比率"""
    if len(y) < window or len(x) < window:
        return 1.0
    y_vals = y.iloc[-window:].values
    x_vals = x.iloc[-window:].values
    X = sm.add_constant(x_vals)
    try:
        model = sm.OLS(y_vals, X).fit()
        return model.params[1] if not np.isnan(model.params[1]) else 1.0
    except Exception:
        return 1.0


def calculate_spread_zscore(pair: tuple, price_dict: dict) -> tuple:
    """
    计算配对的价差Z-score
    返回: (spread_value, zscore_value, hedge_ratio)
    """
    sym_a, sym_b = pair
    if sym_a not in price_dict or sym_b not in price_dict:
        return None, None, None
    
    series_a = price_dict[sym_a]
    series_b = price_dict[sym_b]
    
    if len(series_a) < COINTEGRATION_WINDOW or len(series_b) < COINTEGRATION_WINDOW:
        return None, None, None
    
    # 对齐数据
    common_idx = series_a.index.intersection(series_b.index)
    if len(common_idx) < COINTEGRATION_WINDOW:
        return None, None, None
    
    s_a = series_a.loc[common_idx]
    s_b = series_b.loc[common_idx]
    
    # 计算对冲比率
    hedge_ratio = calculate_hedge_ratio(s_a, s_b, HEDGE_RATIO_WINDOW)
    
    # 计算价差
    spread = s_a - hedge_ratio * s_b
    
    # 计算Z-score
    z = zscore(spread)
    current_z = z.iloc[-1] if len(z) > 0 else 0
    current_spread = spread.iloc[-1] if len(spread) > 0 else 0
    
    return float(current_spread), float(current_z), float(hedge_ratio)


def check_cointegration_stability(pair: tuple, price_dict: dict) -> bool:
    """检验配对的协整稳定性"""
    sym_a, sym_b = pair
    if sym_a not in price_dict or sym_b not in price_dict:
        return False
    if len(price_dict[sym_a]) < COINTEGRATION_WINDOW:
        return False
    
    common_idx = price_dict[sym_a].index.intersection(price_dict[sym_b].index)
    if len(common_idx) < COINTEGRATION_WINDOW:
        return False
    
    s_a = price_dict[sym_a].loc[common_idx].values
    s_b = price_dict[sym_b].loc[common_idx].values
    
    try:
        # Engle-Granger两步法协整检验
        model = sm.OLS(s_a, sm.add_constant(s_b)).fit()
        residuals = model.resid
        # 对残差进行ADF检验
        adf_result = sm.tsa.stattools.adfuller(residuals, maxlag=1)
        # p-value < 0.05 表示协整关系显著
        return adf_result[1] < 0.05
    except Exception:
        return False


def main():
    api = TqApi(TqSim(), auth=TqAuth("YOUR_ACCOUNT", "YOUR_PASSWORD"))
    
    # 订阅所有相关合约
    all_symbols = list(set([s for pair in PAIRS for s in pair]))
    quotes = {sym: api.get_quote(sym) for sym in all_symbols}
    klines = {sym: api.get_kline_serial(sym, duration_day=1, data_length=100) 
              for sym in all_symbols}
    
    print(f"[{datetime.now()}] 策略34启动: 化工系产业链协整套利策略")
    
    position_manager = TargetPosTask(api)
    last_calibration_date = None
    pair_states = {}  # {(sym_a, sym_b): {"position": str, "entry_z": float, "hedge_ratio": float}}
    
    # 价格历史
    price_history = {sym: pd.Series(dtype=float) for sym in all_symbols}
    # 缓存的对冲比率
    cached_hedge_ratios = {pair: 1.0 for pair in PAIRS}
    # 活跃配对
    active_pairs = set()
    pair_pnl = {pair: 0.0 for pair in PAIRS}
    
    while True:
        api.wait_update()
        
        # 更新价格历史
        for sym in all_symbols:
            kl = klines[sym]
            if len(kl) > 0:
                dt = pd.Timestamp(kl.iloc[-1]['datetime']).normalize()
                price_history[sym] = pd.concat([
                    price_history[sym],
                    pd.Series({dt: float(kl.iloc[-1]['close'])})
                ])
                if len(price_history[sym]) > COINTEGRATION_WINDOW + 20:
                    price_history[sym] = price_history[sym].iloc[-(COINTEGRATION_WINDOW + 20):]
        
        now = datetime.now()
        current_date = now.date()
        
        # 定期重新校准对冲比率
        should_calibrate = (
            last_calibration_date is None or 
            (current_date - last_calibration_date).days >= REBALANCE_FREQ
        )
        
        if should_calibrate and len(list(price_history.values())[0]) > COINTEGRATION_WINDOW:
            print(f"[{now}] 开始协整套利对校准...")
            for pair in PAIRS:
                sym_a, sym_b = pair
                # 协整检验
                is_cointegrated = check_cointegration_stability(pair, price_history)
                
                if is_cointegrated:
                    spread, z, hedge = calculate_spread_zscore(pair, price_history)
                    if z is not None:
                        cached_hedge_ratios[pair] = hedge
                        print(f"[{now}] 配对 {sym_a}-{sym_b}: 协整通过, hedge={hedge:.4f}, z={z:.2f}")
                else:
                    print(f"[{now}] 配对 {sym_a}-{sym_b}: 协整不稳定，跳过")
            
            last_calibration_date = current_date
        
        # 检查套利信号并管理仓位
        for pair in PAIRS:
            sym_a, sym_b = pair
            if sym_a not in price_history or sym_b not in price_history:
                continue
            if len(price_history[sym_a]) < COINTEGRATION_WINDOW:
                continue
            
            spread, z, hedge = calculate_spread_zscore(pair, price_history)
            if z is None:
                continue
            
            pair_key = (sym_a, sym_b)
            state = pair_states.get(pair_key, {})
            current_pos_a = state.get("pos_a", 0)
            current_pos_b = state.get("pos_b", 0)
            entry_z = state.get("entry_z", 0)
            
            account = api.get_account()
            account_value = account.balance
            
            # 入场逻辑: Z-score超过阈值
            if abs(z) > ZSCORE_ENTRY and len(active_pairs) < MAX_PAIRS_ACTIVE:
                if pair_key not in active_pairs:
                    # 确定方向: z > 0 做空价差(空A多B), z < 0 做多价差(多A空B)
                    if z > 0:
                        # 价差过高，做空价差: 空sym_a, 多sym_b
                        pos_a = -1
                        pos_b = 1
                    else:
                        # 价差过低，做多价差: 多sym_a, 空sym_b
                        pos_a = 1
                        pos_b = -1
                    
                    # 设置仓位
                    position_manager.set_target_volume(sym_a, pos_a)
                    position_manager.set_target_volume(sym_b, pos_b)
                    
                    pair_states[pair_key] = {
                        "pos_a": pos_a,
                        "pos_b": pos_b,
                        "entry_z": z,
                        "hedge_ratio": hedge,
                        "entry_spread": spread
                    }
                    active_pairs.add(pair_key)
                    pair_pnl[pair_key] = 0.0
                    print(f"[{now}] 入场 {sym_a}-{sym_b}: z={z:.2f}, 方向={'做空价差' if z>0 else '做多价差'}, "
                          f"hedge={hedge:.4f}, spread={spread:.4f}")
            
            # 出场逻辑: Z-score回归
            elif pair_key in active_pairs and abs(z) < ZSCORE_EXIT:
                position_manager.set_target_volume(sym_a, 0)
                position_manager.set_target_volume(sym_b, 0)
                
                pnl = pair_pnl.get(pair_key, 0)
                print(f"[{now}] 出场 {sym_a}-{sym_b}: z={z:.2f}, PnL={pnl:.2f}")
                
                active_pairs.discard(pair_key)
                pair_states.pop(pair_key, None)
                pair_pnl[pair_key] = 0.0
            
            # 止损逻辑: Z-score继续扩大
            elif pair_key in active_pairs and abs(z) > ZSCORE_STOP:
                position_manager.set_target_volume(sym_a, 0)
                position_manager.set_target_volume(sym_b, 0)
                
                pnl = pair_pnl.get(pair_key, 0)
                print(f"[{now}] 止损 {sym_a}-{sym_b}: z={z:.2f} 超过{ZSCORE_STOP}, PnL={pnl:.2f}")
                
                active_pairs.discard(pair_key)
                pair_states.pop(pair_key, None)
                pair_pnl[pair_key] = 0.0
            
            # 更新PnL
            if pair_key in active_pairs:
                state = pair_states.get(pair_key, {})
                entry_spread = state.get("entry_spread", spread)
                hedge_ratio = state.get("hedge_ratio", hedge)
                if spread is not None:
                    pair_pnl[pair_key] = -(spread - entry_spread)  # 负号表示价差方向
            
            # 风控: 单对亏损超限
            if pair_key in active_pairs:
                pnl_val = pair_pnl.get(pair_key, 0)
                if abs(pnl_val) > PAIR_RISK_LIMIT * account_value:
                    position_manager.set_target_volume(sym_a, 0)
                    position_manager.set_target_volume(sym_b, 0)
                    print(f"[{now}] 风控止损 {sym_a}-{sym_b}: PnL={pnl_val:.2f} 超过阈值")
                    active_pairs.discard(pair_key)
                    pair_states.pop(pair_key, None)
                    pair_pnl[pair_key] = 0.0

    api.close()


if __name__ == "__main__":
    main()
