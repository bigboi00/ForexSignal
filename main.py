import MetaTrader5 as mt5
import pandas as pd
import time

# Initialize connection
mt5.initialize()

# Parameters
symbol = 'AUDUSD'
timeframe = mt5.TIMEFRAME_M15  # Entry timeframe
higher_timeframe = mt5.TIMEFRAME_H1  # Higher timeframe for trend confirmation
lot_size = 0.01  # Fixed lot size of 0.01
slippage = 3
take_profit_pips = 15
stop_loss_pips = 30
moving_average_long = 50
moving_average_short = 10
rsi_period = 14
atr_period = 14
risk_percentage = 0.02  # Risk 2% per trade

# Account Equity
account_equity = mt5.account_info().equity

# Get market data
def get_data(symbol, timeframe, n=100):
    rates = mt5.copy_rates_from_pos(symbol, timeframe, 0, n)
    rates_frame = pd.DataFrame(rates)
    rates_frame['time'] = pd.to_datetime(rates_frame['time'], unit='s')
    return rates_frame

# Calculate Moving Average, RSI, ATR
def calculate_indicators(data):
    data['MA_long'] = data['close'].rolling(window=moving_average_long).mean()
    data['MA_short'] = data['close'].rolling(window=moving_average_short).mean()
    data['RSI'] = 100 - (100 / (1 + (data['close'].diff().where(lambda x: x > 0, 0).rolling(window=rsi_period).mean() / 
                                data['close'].diff().where(lambda x: x < 0, 0).rolling(window=rsi_period).mean())))
    data['ATR'] = data['high'].subtract(data['low']).rolling(window=atr_period).mean()
    return data

# Get broker's minimum volume, step size, and price step
def get_volume_constraints(symbol):
    symbol_info = mt5.symbol_info(symbol)
    if symbol_info is None:
        print(f"Symbol {symbol} not found!")
        return None, None, None
    return symbol_info.volume_min, symbol_info.volume_step, symbol_info.point

# Round value to 2 decimal places
def round_to_2_decimal_places(value):
    return round(value, 5)

# Signal Generation with Multiple Timeframes
def signal_generator(data, higher_data):
    last_row = data.iloc[-1]
    higher_last_row = higher_data.iloc[-1]
    
    if last_row['close'] > last_row['MA_long'] and last_row['RSI'] > 50 and last_row['MA_short'] > last_row['MA_long'] and higher_last_row['close'] > higher_last_row['MA_long']:
        return 'buy'
    elif last_row['close'] < last_row['MA_long'] and last_row['RSI'] < 50 and last_row['MA_short'] < last_row['MA_long'] and higher_last_row['close'] < higher_last_row['MA_long']:
        return 'sell'
    else:
        return 'hold'

# Trailing Stop Logic
def trailing_stop(symbol, action, entry_price, stop_loss, atr_value):
    if action == 'buy':
        new_stop_loss = entry_price - atr_value * 0.0001
    elif action == 'sell':
        new_stop_loss = entry_price + atr_value * 0.0001
    
    return new_stop_loss

# Place Trade
def place_trade(symbol, action, stop_loss, take_profit, lot_size):
    price = mt5.symbol_info_tick(symbol).ask if action == 'buy' else mt5.symbol_info_tick(symbol).bid

    # Round stop loss and take profit to 2 decimal places
    sl_price = round_to_2_decimal_places(price - stop_loss * 0.0001) if action == 'buy' else round_to_2_decimal_places(price + stop_loss * 0.0001)
    tp_price = round_to_2_decimal_places(price + take_profit * 0.0001) if action == 'buy' else round_to_2_decimal_places(price - take_profit * 0.0001)
    
    request = {
        "action": mt5.TRADE_ACTION_DEAL,
        "symbol": symbol,
        "volume": lot_size,
        "type": mt5.ORDER_TYPE_BUY if action == 'buy' else mt5.ORDER_TYPE_SELL,
        "price": price,
        "sl": sl_price,
        "tp": tp_price,
        "deviation": slippage,
        "magic": 234000,
        "comment": "Optimized Trend Following",
        "type_filling": mt5.ORDER_FILLING_FOK,
        "type_time": mt5.ORDER_TIME_GTC,
    }
    
    # Debug the TradeRequest before sending
    print("TradeRequest:", request)
    
    result = mt5.order_send(request)
    return result

# Main loop
def main():
    while True:
        data = get_data(symbol, timeframe)
        higher_data = get_data(symbol, higher_timeframe)
        data = calculate_indicators(data)
        higher_data = calculate_indicators(higher_data)
        
        signal = signal_generator(data, higher_data)
        atr_value = data['ATR'].iloc[-1]
        price = mt5.symbol_info_tick(symbol).ask
        
        stop_loss = stop_loss_pips  # You can dynamically adjust based on ATR
        take_profit = take_profit_pips  # You can adjust this based on a risk-reward ratio
        
        # Fixed lot size of 0.01
        position_size = lot_size
        
        if signal == 'buy':
            print("Buy signal detected!")
            result = place_trade(symbol, 'buy', stop_loss, take_profit, position_size)
            print("Trade result:", result)
        elif signal == 'sell':
            print("Sell signal detected!")
            result = place_trade(symbol, 'sell', stop_loss, take_profit, position_size)
            print("Trade result:", result)
        else:
            print("No signal, holding position.")
        
        time.sleep(60 * 15)  # Wait 15 minutes for the next check

# Run the script
if __name__ == '__main__':
    main()
