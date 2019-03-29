import time
import datetime
import json
import csv
import linecache
import numpy as np
import pandas as pd
from scipy.stats import norm
import talib
from APIcalls import CryptoCompare
from APIcalls import Bittrex
from TradeAlgo import TradeAlgo
import os

CC = CryptoCompare()
Algo = TradeAlgo()

def minuteData(exchange, coin, base, interval, limit):
    mClose = []
    mOpen = []
    mVolTo = []
    mvolfrom = []
    mHigh = []
    mLow = []
    data = (CC.minuteHist(exchange, coin, base, interval, limit)).json()
    df = pd.DataFrame(index=[0])
    df['time'] = data['TimeTo']
    for i in range(0, len(data['Data'])):
        mClose.append(float((data['Data'][i]['close'])))
        mOpen.append(float((data['Data'][i]['open'])))
        mVolTo.append(float((data['Data'][i]['volumeto'])))
        mvolfrom.append(float((data['Data'][i]['volumefrom'])))
        mHigh.append(float((data['Data'][i]['high'])))
        mLow.append(float((data['Data'][i]['low'])))
    mOpen = np.asarray(mOpen)
    mClose = np.asarray(mClose)
    mHigh = np.asarray(mHigh)
    mLow = np.asarray(mLow)
    mVolTo = np.asarray(mVolTo)
    mvorlfrom = np.asarray(mvolfrom)
    df['dema5'] = talib.DEMA(mClose, 5)[-1]
    df['dema10'] = talib.DEMA(mClose, 10)[-1]
    df['ema5'] = talib.EMA(mClose, 5)[-1]
    df['ema10'] = talib.EMA(mClose, 10)[-1]
    df['macd sl'] = talib.MACD(mClose, 26, 10, 9)[0][-1]
    df['rsi'] = talib.RSI(mClose)[-1]
    df['uosc'] = talib.ULTOSC(mHigh, mLow, mClose)[-1]
    df['adx'] = talib.ADX(mHigh, mLow, mClose)[-1]
    df['w14'] = talib.WILLR(mHigh, mLow, mClose)[-1]
    df['aroon'] = talib.AROON(mHigh, mLow)[0][-1]
    df['di+'] = talib.PLUS_DI(mHigh, mLow, mClose)[-1]
    df['di-'] = talib.MINUS_DI(mHigh, mLow, mClose)[-1]
    return df


def hourData(exchange, coin, base, interval, limit):
    hclose = []
    hhigh = []
    hlow = []
    data = (CC.hourHist(exchange, coin, base, interval, limit)).json()
    df = pd.DataFrame(index=[0])
    df['time'] = data['TimeTo']
    for i in range(0, len(data['Data'])):
        # logger(fname,data['Data'][i])
        hclose.append(float((data['Data'][i]['close'])))
        hhigh.append(float((data['Data'][i]['high'])))
        hlow.append(float((data['Data'][i]['low'])))
    hclose = np.asarray(hclose)
    hhigh = np.asarray(hhigh)
    hlow = np.asarray(hlow)
    df['w14'] = talib.WILLR(hhigh, hlow, hclose)[-1]
    return df


def roundDown(n, d):
    d = int('1' + ('0' * d))
    return np.floor(n * d) / d


def logger(fName, text, printer=True):
    f = open(fName, 'a')
    f.write(str(text))
    f.write('\n')
    f.flush()
    f.close()
    if(printer == True):
        print(text)

def datatocsv(csvfile, mindata, hdata):
    print('placeholder')


            
def restore_record (target, record, coin):    
    num_lines = sum(1 for line in open('records_'+coin))
    for i in range(7, num_lines + 1):
        temp = str(linecache.getline('records', i)).rstrip("\n\r")
        if (temp == target):
            for j in range(i+1, num_lines + 1):
                temp = str(linecache.getline('records_'+coin, j)).rstrip("\n\r")
                if(temp != ''):
                    temp = np.fromstring(temp, dtype=float, sep=',')
                    if (len(temp) == 8):
                        record = np.vstack([record, temp])
                    else:
                        break
                else:
                    break
            return record

def addRow(target, data):
    df = target.copy()
    df.loc[len(df)] = data
    return df

def deleteRows(target):
    target = df.copy() 
    return df[df.Delete != 'True'].reset_index(drop=True)


def c2bBearTradeExecute(fName, btcOffset, coinOffset, coinReserved, coinbtc, targetCoin, minSize):
    global fee
    global c2bRecordBear
    coin = 0

    # check and update balance
    try:
        coin = bitcon.get_balance(targetCoin)
        if (coin['success'] == True):
            coin = float(coin['result']['Available']) + coinOffset
            coin = roundDown(coin, 6)
        else:
            logger(fName, 'balance request success is false')
            coin = 0
    except Exception as e:
        logger(fName, 'balance try failed')
        coin = 0

    # if we have enough eth
    if (coin - coinReserved > minSize):
        try:
            data = bitcon.get_orderbook('BTC-' + targetCoin, 'buy')
        except Exception as e:
            logger(fName, 'order book try failed')
            logger(fName, e)
            data = '{"success": "False"}'
            data = json.loads(data)
        # iteratively scan order book
        if (data['success'] == True):
            for i in range(0, len(data['result'])):
                bidRate = np.round(float(data['result'][i]['Rate']), 5)
                bidAmount = roundDown(float(data['result'][i]['Quantity']), 6)
                # if order book is close to our target
                if (bidRate / coinbtc > 0.99 and coin - coinReserved > minSize):
                    # if bid amount is more than the amount of eth available, sell all eth
                    if (coin - coinReserved < bidAmount):
                        # execute trade
                        logger(fName, 'selling all coin')
                        amount = roundDown((coin - coinReserved), 6)
                        try:
                            order = bitcon.sell_limit('BTC-' + targetCoin, amount, bidRate)
                        except Exception as e:
                            logger(fName, 'order try failed')
                            logger(fName, e)
                            order = '{"success": "False"}'
                            order = json.loads(order)
                        if (order['success'] == True):
                            temp = ['False', 0, time.time(), amount, bidRate, order['result']['uuid'], 'False']
                            # [confirmation , reserved btc 1, time 2, amount 3, rate 4, id 5, delete 6]
                            c2bRecordBear = addRow(c2bRecordBear, temp)
                        else:
                            logger(fName, 'c2b bear order failed')
                            logger(fName, order)
                    # if bid amount is less than the available eth, sell some eth
                    else:
                        logger(fName, 'selling some coin')
                        try:
                            order = bitcon.sell_limit('BTC-' + targetCoin, bidAmount, bidRate)
                        except Exception as e:
                            logger(fName, 'order  try failed')
                            logger(fName, e)
                            order = '{"success": "False"}'
                            order = json.loads(order)
                        if (order['success'] == True):
                            temp = ['False', 0, time.time(), bidAmount, bidRate, order['result']['uuid'], 'False']
                            # [confirmation 0, reserved btc 1, time 2, amount 3, rate 4, id 5, delete 6]
                            print(c2bRecordBear)
                            c2bRecordBear = addRow(c2bRecordBear, temp)
                        else:
                            logger(fName, 'c2b bear order failed')
                            logger(fName, order)
                else:
                    logger(fName, 'order book not close enough')
                    break
    else:
        logger(fName, 'not enough coin')


def c2bConfirmCancelOrders(fName, timeLimit):
    global c2bRecordBear
    global fee

    for i in range(0, len(c2bRecordBear)):
        # begin checking all unconfirmed orders
        if (c2bRecordBear["Confirmation"][i] == 'False'):
            try:
                temp = bitcon.get_order(c2bRecordBear['ID'][i])
            except Exception as e:
                logger(fName, 'order book try failed')
                logger(fName, e)
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            print(temp)
            if (temp['success'] == True):
                print("result is true")
                print(temp['result']['IsOpen'])
                orderTime = temp['result']['Opened']
                orderTime = time.mktime(datetime.datetime.strptime(orderTime, '%Y-%m-%dT%H:%M:%S.%f').timetuple())
                # if order was fully filled
                if (temp['result']['IsOpen'] == False and temp['result']['CancelInitiated'] == False):
                    c2bRecordBear['Confirmation'][i] = 'True'
                    c2bRecordBear["Reserved"][i] = c2bRecordBear['Amount'][i] * c2bRecordBear['Rate'][i] * (1 - fee)
                    logger(fName, 'filled c2b bear trade has been confirmed')
                # if order is still open
                if (temp['result']['IsOpen'] == True and temp['result']['CancelInitiated'] == False):
                    #if unfilled order has been open for too long (determined by timeLimit), canceled said order
                    if (time.time() - int(orderTime) > timeLimit):
                        try:
                            temp = bitcon.cancel(c2bRecordBear["ID"][i])
                        except Exception as e:
                            temp = '{"success": "False"}'
                            temp = json.loads(temp)
                        if (temp['success'] == True):
                            try:
                                temp = bitcon.get_order(c2bRecordBear["ID"][i])
                            except Exception as e:
                                temp = '{"success": "False"}'
                                temp = json.loads(temp)
                            if (temp["success"] == True):
                                # if order was completely unfilled
                                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                                    c2bRecordBear["Delete"][i] = "True"
                                    logger(fName, 'canceled bammer order')
                                else:
                                    c2bRecordBear["Amount"][i] = float(temp['result']['Quantity']) - float(
                                        temp['result']['QuantityRemaining'])
                                    c2bRecordBear["Delete"][i] = "True"
                                    c2bRecordBear["Reserved"][i] = c2bRecordBear["Amount"][i] * c2bRecordBear["Rate"][i] * (
                                            1 - fee)
                                    logger(fName, 'canceled partially filled b2c bear order')
                            else:
                                c2bRecordBear["Confirmation"][i] = "Fail"
                                logger(fName, 'c2b bear order status (2nd round) failed')
                        # if canceling order fails, reserve full amount of btc just in case
                        else:
                            logger(fName, 'canceling b2c bear order failed')
                            c2bRecordBear["Reserved"][i] = c2bRecordBear["Amount"][i] * c2bRecordBear["Rate"][i] * (1 - fee)


        if (c2bRecordBear["Confirmation"][i] == "Fail"):
            try:
                temp = bitcon.get_order(c2bRecordBear['ID'][i])
            except Exception as e:
                logger(fName, 'order book try failed')
                logger(fName, e)
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            if (temp["success"] == True):
                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                    c2bRecordBear["Delete"][i] = "True"
                    logger(fName, 'canceled bammer order')
                else:
                    c2bRecordBear["Amount"][i] = float(temp['result']['Quantity']) - float(temp['result']['QuantityRemaining'])
                    c2bRecordBear["Confirmation"][i] = "True"
                    c2bRecordBear["Reserved"][i] = c2bRecordBear["Amount"][i] * c2bRecordBear["Rate"][i] * (1 - fee)
                    logger(fName, 'canceled partially filled c2b bear order')
            else:
                logger(fName, 'c2b bear order status failed')

    c2bRecordBear = deleteRows(c2bRecordBear)

def b2cBearTradeExecute(fName, coinbtc, targetCoin, fastMinuteResults):
    global c2bRecordBear
    global b2cRecordBear
    global averageBearTradeTime
    global stdBearTradeTime

    for i in range(0, len(c2bRecordBear)):
        # if c2b order is confirmed, check for trade back signal
        if(c2bRecordBear['Confirmation'][i] == 'True'):
            # check for signal
            b2c = Algo.btc2ethSignalWithGrowthBear(fName, coinbtc, c2bRecordBear['Amount'][i],
                                                       c2bRecordBear['Rate'][i], time.time() - c2bRecordBear['Time'][i],
                                                   fastMinuteResults, averageBearTradeTime, averageBearTradeTime + stdBearTradeTime )
            if (b2c):
                logger(fName, 'coin 2 eth bear signal')
                # swap back to eth
                try:
                    order = bitcon.buy_limit('BTC-' + targetCoin, c2bRecordBear["Amount"][i], coinbtc)
                except Exception as e:
                    order = '{"success": "False"}'
                    order = json.loads(order)
                if (order['result'] == True):
                    logger(fName, order)
                    temp = ["False", Algo.rateNeededBear(float(c2bRecordBear["Amount"][i]), float(coinbtc)), time.time(), c2bRecordBear["Amount"][i], coinbtc, order['result']['uuid'], 0, c2bRecordBear['Time'][i]]
                    # [confirmation 0,  rn 1, time 2, amount 3, rate 4, id 5, delete 6,  pair time 7]
                    b2cRecordBear = addRow((b2cRecordBear, temp))
                    c2bRecordBear['Delete'][i] = 'True'
                else:
                    logger(fName, 'b2c bear trade failed')

    c2bRecordBear = deleteRows(c2bRecordBear)

def b2cConfirmCancelUpdateOrders(fName, coinbtc, targetCoin, fastMinuteResults):
    global b2cRecordBear
    global graveyardRecordBear
    global tradeTimeBear
    global averageBearTradeTime
    global stdBearTradeTime

    for i in range(0, len(b2cRecordBear)):
        try:
            temp = bitcon.get_order(b2cRecordBear["ID"][i])
        except Exception as e:
            temp = '{"success": "False"}'
            temp = json.loads(temp)
        if (temp['success'] == True):
            if (temp['result']['IsOpen'] == False and temp['result']['CancelInitiated'] == False):
                b2cRecordBear['Confirmation'][i] = 'True'
                b2cRecordBear['Delete'][i] = 'True'
                tradeTimeBear = np.roll(tradeTimeBear, -1)
                tradeTimeBear[-1] = time.time() - b2cRecordBear['Pair Time'][i]
                logger(fName, 'filled b2c bear trade has been confirmed')
            if (temp['result']['IsOpen'] == True and temp['result']['CancelInitiated'] == False):
                rate = Algo.rateLinearGrowth(fName, b2cRecordBear['Rate'][i],
                                             time.time() - b2cRecordBear['Pair Time'][i], averageBearTradeTime,
                                             averageBearTradeTime + stdBearTradeTime, fastMinuteResults, coinbtc)
                if (rate != float(b2cRecordBear['Rate'][i])):
                    try:
                        temp = bitcon.cancel(b2cRecordBear["ID"][i])
                    except Exception as e:
                        temp = '{"success": "False"}'
                        temp = json.loads(temp)
                    if (temp['success'] == True):
                        logger(fName, 'canceled b2c bear trade for new rate')
                        try:
                            temp = bitcon.get_order(b2cRecordBear["ID"][i])
                        except Exception as e:
                            temp = '{"success": "False"}'
                            temp = json.loads(temp)
                        if (temp['success'] == True):
                            logger(fName, temp)
                            amount = temp['result']['QuantityRemaining']
                            if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                                try:
                                    order = bitcon.buy_limit('BTC-' + targetCoin, amount, rate)
                                    logger(fName, order)
                                except Exception as e:
                                    order = '{"success": "False"}'
                                    order = json.loads(order)
                                b2cRecordBear['Delete'][i] = 'True'
                            else:
                                try:
                                    order = bitcon.buy_limit('BTC-' + targetCoin,
                                                             amount, rate)
                                    logger(fName, order)
                                except Exception as e:
                                    order = '{"success": "False"}'
                                    order = json.loads(order)
                                logger(fName, order)
                                b2cRecordBear['Delete'][i] = 'True'
                            if (order['success'] == True):
                                logger(fName, order)
                                temp = ["False", b2cRecordBear['Rate Needed'][i], b2cRecordBear['Time'][i],
                                        amount, rate,
                                        order['result']['uuid'], 'False', b2cRecordBear['Pair Time'][i]]
                                b2cRecordBear = addRow(b2cRecordBear, temp)
                            else:
                                logger(fName, order)
                                logger(fName, 'placing new rate order failed')
                                temp = ["False", b2cRecordBear['Rate Needed'][i], b2cRecordBear['Time'][i],
                                        b2cRecordBear['Amount'][i], rate,
                                        int(order['order_id']), 'False', b2cRecordBear['Pair Time'][i]]
                                graveyardRecordBear = addRow(graveyardRecordBear, temp)
                        else:
                            b2cRecordBear["Confirmation"][i] = "Fail"
                            temp = b2cRecordBear.iloc[i, :]
                            graveyardRecordBear = addRow(graveyardRecordBear, temp)
                            b2cRecordBear["Delete"][i] = "True"
                            logger(fName, 'b2c bear order status failed after new rate')
                    else:
                        logger(fName, 'canceling b2c bear record for new rate failed')
        else:
            logger(fName, 'b2c record bear order status failed')

    b2cRecordBear = deleteRows(b2cRecordBear)

def sweepBearGraveyard(fName, coinbtc, targetCoin, fastMinuteResults):
    global graveyardRecordBear
    global b2cRecordBear
    global averageBearTradeTime
    global stdBearTradeTime

    for i in range(0, len(graveyardRecordBear)):
        if (graveyardRecordBear['Confirmation'][i] == 'False'):
            rate = Algo.rateLinearGrowth(fName, graveyardRecordBear['Rate Needed'][i],
                                         time.time() - graveyardRecordBear['Pair Time'][i], averageBearTradeTime,
                                         averageBearTradeTime + stdBearTradeTime, fastMinuteResults, coinbtc)
            try:
                order = bitcon.buy_limit('BTC-'+targetCoin, graveyardRecordBear["Amount"][i], rate)
            except Exception as e:
                order = '{"success": "False"}'
                order = json.loads(order)
            if (order['success'] == True):
                graveyardRecordBear['ID'][i] = order['result']['uuid']
                b2cRecordBear = addRow(b2cRecordBear, graveyardRecordBear.iloc[[i]])
                graveyardRecordBear['Delete'][i] = "True"
                logger(fName, 'graveyard bear order resurrected')
            else:
                logger(fName, order)
                logger(fName, 'graveyard bear order failed')
        if (graveyardRecordBear['Confirmation'][i] == 'Fail'):
            rate = Algo.rateLinearGrowth(fName, graveyardRecordBear['Rate Needed'][i],
                                         time.time() - graveyardRecordBear['Pair Time'][i], averageBearTradeTime,
                                         averageBearTradeTime + stdBearTradeTime, fastMinuteResults, coinbtc)
            try:
                temp = bitcon.get_order(graveyardRecordBear["ID"][i])
            except Exception as e:
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            if (temp['success'] == True):
                amount = temp['result']['QuantityRemaining']
                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                    try:
                        order = bitcon.buy_limit('BTC-' + targetCoin, amount, rate)
                    except Exception as e:
                        order = '{"success": "False"}'
                        order = json.loads(order)
                    graveyardRecordBear["Delete"][i] = "True"
                    logger(fName, order)
                else:
                    try:
                        order = bitcon.buy_limit('BTC-' + targetCoin, amount, rate)
                    except Exception as e:
                        order = '{"success": "False"}'
                        order = json.loads(order)
                    logger(fName, order)
                if (order['success'] == True):
                    graveyardRecordBear["Delete"][i] = "True"
                    temp = ["False", graveyardRecordBear['Rate Needed'][i], graveyardRecordBear['Time'][i], amount, rate, order['result']['uuid'], 'False', graveyardRecordBear['Pair Time'][i]]
                    b2cRecordBear = addRow(b2cRecordBear, temp)
                    logger(fName, 'graveyard bear order resurrected')

                else:
                    logger(fName, order)
                    logger(fName, 'graveyard bear order failed')
            else:
                logger(fName, 'graveyard bear order status failed')

    graveyardRecordBear = deleteRows(graveyardRecordBear)

def b2cBullTradeExecute(fName, btcOffset, btcRation, btcReserved, coinbtc, targetCoin):
    global fee
    global b2cRecordBull

    # check and update balance
    try:
        btc = bitcon.get_balance('BTC')
        if (btc['success'] == True):
            btc = (float(btc['result']['Available']) + btcOffset) * btcRation
        else:
            logger(fName, 'balance request success is false')
            btc = 0
    except Exception as e:
        logger(fName, 'balance try failed')
        btc = 0

    # if we have enough eth
    if (btc - btcReserved > 0.00001):
        try:
            data = bitcon.get_orderbook('BTC-' + targetCoin, 'sell')
        except Exception as e:
            logger(fName, 'order book try failed')
            logger(fName, e)
            data = '{"success": "False"}'
            data = json.loads(data)
        # iteratively scan order book
        if (data['success'] == True):
            for i in range(0, len(data['result'])):
                askRate = np.round(float(data['result'][i]['Rate']), 5)
                askAmount = roundDown(float(data['result'][i]['Quantity']), 6)
                # if order book is close to our target
                if (askRate / coinbtc <= 1.01):
                    total = np.round((askRate * askAmount * (1 + fee)), 5)
                    # if bid amount is more than the amount of eth available, sell all eth
                    if (btc - btcReserved < total):
                        # execute trade
                        logger(fName, 'selling all btc')
                        amount = ((btc - btcReserved) * (1 - fee)) / (askRate)
                        amount = roundDown(amount, 6)
                        try:
                            order = bitcon.buy_limit('BTC-' + targetCoin, amount, askRate)
                        except Exception as e:
                            logger(fName, 'order try failed')
                            logger(fName, e)
                            order = '{"success": "False"}'
                            order = json.loads(order)
                        if (order['success'] == True):
                            temp = ['False', 0, time.time(), amount, askRate, order['result']['uuid'], 'False']
                            # [confirmation , reserved btc 1, time 2, amount 3, rate 4, id 5, delete 6]
                            b2cRecordBull = addRow(b2cRecordBull, temp)
                        else:
                            logger(fName, 'c2b bear order failed')
                            logger(fName, order)
                    # if bid amount is less than the available eth, sell some eth
                    else:
                        logger(fName, 'selling some btc')
                        try:
                            order = bitcon.sell_limit('BTC-' + targetCoin, askAmount, askRate)
                        except Exception as e:
                            logger(fName, 'order  try failed')
                            logger(fName, e)
                            order = '{"success": "False"}'
                            order = json.loads(order)
                        if (order['success'] == True):
                            temp = ['False', 0, time.time(), askAmount, askRate, order['result']['uuid'], 'False']
                            # [confirmation 0, reserved btc 1, time 2, amount 3, rate 4, id 5, delete 6]
                            b2cRecordBull = addRow(b2cRecordBull, temp)
                        else:
                            logger(fName, 'b2c bull order failed')
                            logger(fName, order)
                else:
                    logger(fName, 'order book not close enough')
                    break
    else:
        logger(fName, 'not enough btc')

def b2cConfirmCancelOrders(fName, timeLimit):
    global b2cRecordBull
    global fee

    for i in range(0, len(b2cRecordBull)):
        # begin checking all unconfirmed orders
        if (b2cRecordBull["Confirmation"][i] == 'False'):
            try:
                temp = bitcon.get_order(b2cRecordBull['ID'][i])
            except Exception as e:
                logger(fName, 'order book try failed')
                logger(fName, e)
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            if (temp["success"] == True):
                orderTime = temp['result']['Opened']
                orderTime = time.mktime(datetime.datetime.strptime(orderTime, '%Y-%m-%dT%H:%M:%S.%f').timetuple())
                # if order was fully filled
                if (temp['result']['IsOpen'] == False and temp['result']['CancelInitiated'] == False):
                    b2cRecordBull['Confirmation'][i] = 'True'
                    b2cRecordBull["Reserved"][i] = b2cRecordBull['Amount'][i]
                    logger(fName, 'filled c2b bear trade has been confirmed')
                # if order is still open
                if (temp['result']['IsOpen'] == True and temp['result']['CancelInitiated'] == False):
                    #if unfilled order has been open for too long (determined by timeLimit), canceled said order
                    if (time.time() - int(orderTime) > timeLimit):
                        try:
                            temp = bitcon.cancel(b2cRecordBull["ID"][i])
                        except Exception as e:
                            temp = '{"success": "False"}'
                            temp = json.loads(temp)
                        if (temp['success'] == True):
                            try:
                                temp = bitcon.get_order(b2cRecordBull["ID"][i])
                            except Exception as e:
                                temp = '{"success": "False"}'
                                temp = json.loads(temp)
                            if (temp["success"] == True):
                                # if order was completely unfilled
                                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                                    b2cRecordBull["Delete"][i] = "True"
                                    logger(fName, 'canceled bammer order')
                                else:
                                    b2cRecordBull["Amount"][i] = float(temp['result']['Quantity']) - float(
                                        temp['result']['QuantityRemaining'])
                                    b2cRecordBull["Delete"][i] = "True"
                                    b2cRecordBull["Reserved"][i] = float(temp['result']['Quantity']) - float(temp['result']['QuantityRemaining'])
                                    logger(fName, 'canceled partially filled b2c bull order')
                            else:
                                b2cRecordBull["Confirmation"][i] = "Fail"
                                logger(fName, 'c2b bear order status (2nd round) failed')
                        # if canceling order fails, reserve full amount of btc just in case
                        else:
                            logger(fName, 'canceling b2c bull order failed')
                            b2cRecordBull["Reserved"][i] = b2cRecordBull["Amount"][i]


        if (b2cRecordBull["Confirmation"][i] == "Fail"):
            try:
                temp = bitcon.get_order(b2cRecordBull['ID'][i])
            except Exception as e:
                logger(fName, 'order book try failed')
                logger(fName, e)
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            if (temp["success"] == True):
                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                    b2cRecordBull["Delete"][i] = "True"
                    logger(fName, 'canceled bammer order')
                else:
                    b2cRecordBull["Amount"][i] = float(temp['result']['Quantity']) - float(temp['result']['QuantityRemaining'])
                    b2cRecordBull["Confirmation"][i] = "True"
                    b2cRecordBull["Reserved"][i] = b2cRecordBull["Amount"][i]
                    logger(fName, 'canceled partially filled c2b bear order')
            else:
                logger(fName, 'c2b bull order status failed')

    b2cRecordBull = deleteRows(b2cRecordBull)

def c2bBullTradeExecute(fName, coinbtc, targetCoin, fastMinuteResults):
    global b2cRecordBull
    global c2bRecordBull
    global averageBullTradeTime
    global stdBullTradeTime

    for i in range(0, len(b2cRecordBull)):
        # if c2b order is confirmed, check for trade back signal
        if(b2cRecordBull['Confirmation'][i] == 'True'):
            # check for signal
            c2b = Algo.eth2btcSignalWithDecayBull(fName, coinbtc, b2cRecordBull['Amount'][i],
                                                  b2cRecordBull['Rate'][i], time.time() - b2cRecordBull['Time'][i],
                                                  fastMinuteResults, averageBullTradeTime,
                                                  averageBullTradeTime + stdBullTradeTime)
            if (c2b):
                logger(fName, 'coin 2 btc bull signal')
                # swap back to eth
                try:
                    order = bitcon.sell_limit('BTC-' + targetCoin, b2cRecordBull["Amount"][i], coinbtc)
                except Exception as e:
                    order = '{"success": "False"}'
                    order = json.loads(order)
                if (order['result'] == True):
                    logger(fName, order)
                    temp = ["False", Algo.rateNeededBull(float(b2cRecordBull["Amount"][i]), float(coinbtc)), time.time(), b2cRecordBull["Amount"][i], coinbtc, order['result']['uuid'], 0, b2cRecordBull['Time'][i]]
                    # [confirmation 0,  rn 1, time 2, amount 3, rate 4, id 5, delete 6,  pair time 7]
                    c2bRecordBull = addRow(c2bRecordBull, temp)
                    b2cRecordBull['Delete'][i] = 'True'
                else:
                    logger(fName, 'c2b bull trade failed')

    b2cRecordBull = deleteRows(b2cRecordBull)

def c2bConfirmCancelUpdateOrders(fName, coinbtc, targetCoin, fastMinuteResults):
    global c2bRecordBull
    global graveyardRecordBull
    global tradeTimeBull
    global averageBullTradeTime
    global stdBullTradeTime

    for i in range(0, len(c2bRecordBull)):
        try:
            temp = bitcon.get_order(c2bRecordBull["ID"][i])
        except Exception as e:
            temp = '{"success": "False"}'
            temp = json.loads(temp)
        if (temp['success'] == True):
            if (temp['result']['IsOpen'] == False and temp['result']['CancelInitiated'] == False):
                c2bRecordBull['Confirmation'][i] = 'True'
                c2bRecordBull['Delete'][i] = 'True'
                tradeTimeBull = np.roll(tradeTimeBull, -1)
                tradeTimeBull[-1] = time.time() - c2bRecordBull['Pair Time'][i]
                logger(fName, 'filled c2b bull trade has been confirmed')
            if (temp['result']['IsOpen'] == True and temp['result']['CancelInitiated'] == False):
                c2bRecordBull['Confirmation'][i] = 'True'
                logger(fName, 'c2b bull trade has been confirmed')
            if (c2bRecordBull['Confirmation'][i] == 'True' and c2bRecordBull['Delete'][i] == 'False'):
                rate = Algo.rateLinearDecay(fName, c2bRecordBull['Rate Needed'][i], time.time() - c2bRecordBull['Pair Time'][i], averageBullTradeTime, averageBullTradeTime + stdBullTradeTime, fastMinuteResults, coinbtc)
                if (rate != float(c2bRecordBull['Rate'][i])):
                    try:
                        temp = bitcon.cancel(c2bRecordBull['ID'][i])
                    except Exception as e:
                        temp = '{"success": "False"}'
                        temp = json.loads(temp)
                    if (temp['success'] == True):
                        try:
                            temp = bitcon.get_order(c2bRecordBull["ID"][i])
                        except Exception as e:
                            temp = '{"success": "False"}'
                            temp = json.loads(temp)
                        if (temp['success'] == True):
                            amount = temp['result']['QuantityRemaining']
                            logger(fName, temp)
                            if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                                try:
                                    order = bitcon.sell_limit('BTC-' + targetCoin, amount, rate)
                                except Exception as e:
                                    order = '{"success": "False"}'
                                    order = json.loads(order)
                                c2bRecordBull["Delete"][i] = "True"
                            else:
                                try:
                                    order = bitcon.sell_limit('BTC-' + targetCoin, amount,
                                                              rate)
                                except Exception as e:
                                    order = '{"success": "False"}'
                                    order = json.loads(order)
                                c2bRecordBull["Delete"][i] = "True"
                            if (order['success'] == True):
                                temp = ["False", c2bRecordBull['Rate Needed'][i], c2bRecordBull['Time'][i], amount, rate,
                                        order['result']['uuid'], 'False', c2bRecordBull['Pair Time'][i]]
                                c2bRecordBull = addRow(c2bRecordBull, temp)
                            else:
                                logger(fName, 'placing new rate bull order failed')
                                temp = ["False", c2bRecordBull['Rate Needed'][i], c2bRecordBull['Time'][i], amount, rate,
                                        order['result']['uuid'], 'False', c2bRecordBull['Pair Time'][i]]
                                graveyardRecordBull = addRow(graveyardRecordBull, temp)
                        else:
                            c2bRecordBull["Confirmation"][i] = "Fail"
                            temp = c2bRecordBull.iloc[i, :]
                            graveyardRecordBull = addRow(graveyardRecordBull, temp)
                            c2bRecordBull["Delete"][i] = "True"
                            logger(fName, 'c2b bull order status failed after new rate')
                    else:
                        logger(fName, 'canceling c2b bull record for new rate failed')
        else:
            logger(fName, 'c2b record bull order status failed')

    c2bRecordBull = deleteRows(c2bRecordBull)

def sweepBullGraveyard(fName, coinbtc, targetCoin, fastMinuteResults):
    global graveyardRecordBull
    global b2cRecordBull
    global averageBullTradeTime
    global stdBullTradeTime

    for i in range(0, len(graveyardRecordBull)):
        if (graveyardRecordBull['Confirmation'][i] == 'False'):
            rate = Algo.rateLinearDecay(fName, graveyardRecordBull['Rate Needed'][i],
                                         time.time() - graveyardRecordBull['Pair Time'][i], averageBullTradeTime,
                                         averageBullTradeTime + stdBullTradeTime, fastMinuteResults, coinbtc)
            try:
                order = bitcon.sell_limit('BTC-'+targetCoin, graveyardRecordBull["Amount"][i], rate)
            except Exception as e:
                order = '{"success": "False"}'
                order = json.loads(order)
            if (order['success'] == True):
                graveyardRecordBull['ID'][i] = order['result']['uuid']
                b2cRecordBear = addRow(b2cRecordBear, graveyardRecordBull.iloc[[i]])
                graveyardRecordBull['Delete'][i] = "True"
                logger(fName, 'graveyard bear order resurrected')
            else:
                logger(fName, order)
                logger(fName, 'graveyard bear order failed')
        if (graveyardRecordBull['Confirmation'][i] == 'Fail'):
            rate = Algo.rateLinearDecay(fName, graveyardRecordBull['Rate Needed'][i],
                                         time.time() - graveyardRecordBull['Pair Time'][i], averageBullTradeTime,
                                         averageBullTradeTime + stdBullTradeTime, fastMinuteResults, coinbtc)
            try:
                temp = bitcon.get_order(graveyardRecordBull["ID"][i])
            except Exception as e:
                temp = '{"success": "False"}'
                temp = json.loads(temp)
            if (temp['success'] == True):
                amount = temp['result']['QuantityRemaining']
                if (temp['result']['Quantity'] == temp['result']['QuantityRemaining']):
                    try:
                        order = bitcon.sell_limit('BTC-' + targetCoin, amount, rate)
                    except Exception as e:
                        order = '{"success": "False"}'
                        order = json.loads(order)
                        graveyardRecordBull["Delete"][i] = "True"
                    logger(fName, order)
                else:
                    try:
                        order = bitcon.buy_limit('BTC-' + targetCoin, amount, rate)
                    except Exception as e:
                        order = '{"success": "False"}'
                        order = json.loads(order)
                    logger(fName, order)
                if (order['success'] == True):
                    graveyardRecordBull["Delete"][i] = "True"
                    temp = ["False", graveyardRecordBull['Rate Needed'][i], graveyardRecordBull['Time'][i], amount, rate, order['result']['uuid'], 'False', graveyardRecordBull['Pair Time'][i]]
                    b2cRecordBear = addRow(b2cRecordBear, temp)
                    logger(fName, 'graveyard bear order resurrected')

                else:
                    logger(fName, order)
                    logger(fName, 'graveyard bear order failed')
            else:
                logger(fName, 'graveyard bear order status failed')

    graveyardRecordBull = deleteRows(graveyardRecordBull)

            
def run(fName, targetCoin, minSize, btcOffset, btcRation, coinOffset, minuteTimeScale, hourTimeScale, fastMinuteTimeScale, timeLimit):
    
    nowtime = time.strftime('%H:%M:%S')
    nowtime2 = time.time()
    logger(fName, nowtime2)
    
    lockout = False

    global lastMinuteTime
    global lastHourTime
    global lastFastMinuteTime

    global minuteResults
    global fastMinuteResults
    global hourResults

    if (np.count_nonzero(tradeTimeBear) == 0):
        averageBearTradeTime, stdBearTradeTime = norm.fit(tradeTimeBear)
    if (np.count_nonzero(tradeTimeBull) == 0):
        averageBullTradeTime, stdBullTradeTime = norm.fit(tradeTimeBull)

    timeScale = hourTimeScale  # in hours
    if (time.time() >= lastHourTime + timeScale * 3600):
        try:
            hourResults = hourData('Bittrex', targetCoin, "BTC", str(timeScale), '500')
            logger(fName, 'new ' + targetCoin + ' hour data!')
            lastHourTime = hourResults.loc[0, 'time']
        except Exception as e:
            logger(fName, targetCoin + ' hour data try failed')
            logger(fName, e)
            lockout = True
    timeScale = minuteTimeScale  # in minutes
    if (time.time() >= lastMinuteTime + timeScale * 60):
        try:
            minuteResults = minuteData('Bittrex', targetCoin, "BTC", str(timeScale), '500')
            lastMinuteTime = minuteResults.loc[0, 'time']
            logger(fName, 'new ' + targetCoin + ' minute data!')
        except Exception as e:
            lockout = True
            logger(fName, 'ethbtc minute data try failed')
            logger(fName, e)
    timeScale = fastMinuteTimeScale  # in minutes
    if (time.time() >= lastFastMinuteTime + timeScale * 60):
        try:
            fastMinuteResults = minuteData('Bittrex', targetCoin, "BTC", str(timeScale), '500')
            lastFastMinuteTime = fastMinuteResults.loc[0, 'time']
            logger(fName, 'new ' + targetCoin + ' fast minute data!')
        except Exception as e:
            lockout = True
            logger(fName, 'ethbtc fast minute data try failed')
            logger(fName, e)

    try:
        coinbtc = bitcon.get_marketsummary('BTC-'+targetCoin)['result'][0]['Last']
    except Exception as e:
        lockout = True


    if(lockout != True):
        coinReserved = b2cRecordBull["Reserved"].sum()
        # core sequence
        e2bSig = Algo.eth2BtcSignalBear(fName, coinbtc, minuteResults, hourResults)
        logger(fName, 'bear e2bsig is ' + str(e2bSig))
        if (e2bSig):
            c2bBearTradeExecute(fName, btcOffset, coinOffset, coinReserved, coinbtc, targetCoin, minSize)
        c2bConfirmCancelOrders(fName, timeLimit)
        b2cBearTradeExecute(fName, coinbtc, targetCoin, fastMinuteResults)
        b2cConfirmCancelUpdateOrders(fName, coinbtc, targetCoin, fastMinuteResults)
        sweepBearGraveyard(fName, coinbtc, targetCoin, fastMinuteResults)
        
        loggger(fName, "Bear Records: ")
        loggger(fName, c2bRecordBear)
        loggger(fName, b2cRecordBear)
        loggger(fName, graveyardRecordBear)
        loggger(fName, "")
        
        time.sleep(2)
        btcReserved = c2bRecordBear["Reserved"].sum()
        b2esig = Algo.btc2EthSignalBull(fName, coinbtc, minuteResults, hourResults)
        if(b2esig):
            b2cBullTradeExecute(fName, btcOffset, btcRation, btcReserved, coinbtc, targetCoin)
        b2cConfirmCancelOrders(fName, timeLimit)
        c2bBullTradeExecute(fName, coinbtc, targetCoin, fastMinuteResults)     
        c2bConfirmCancelUpdateOrders(fName, coinbtc, targetCoin, fastMinuteResults) 
        sweepBullGraveyard(fName, coinbtc, targetCoin, fastMinuteResults)
        
        loggger(fName, "Bull Records: ")
        loggger(fName, b2cRecordBull)
        loggger(fName, c2bRecordBull)
        loggger(fName, graveyardRecordBull)
        loggger(fName, "")
        
        

    else:
        logger(fName, "lockout is active!")
    
    time.sleep(3)



            
            

#gemcon = Gemini()




global c2bRecordBear
global b2cRecordBear
global graveyardRecordBear
global b2cRecordBull
global c2bRecordBull
global graveyardRecordBull
global tradeTimeBear
global tradeTimeBull
global averageBearTradeTime
global stdBearTradeTime
global averageBullTradeTime
global stdBullTradeTime
global lastMinuteTime
global lastFastMinuteTime
global lastFastMinuteTime
global minuteResults
global fastMinuteResults
global hourResults
global fee

c2bRecordBear = pd.DataFrame(
    columns=['Confirmation', 'Reserved', 'Time', 'Amount', 'Rate', 'ID', 'Delete'])
b2cRecordBear = pd.DataFrame(
    columns=['Confirmation', 'Rate Needed', 'Time', 'Amount', 'Rate', 'ID', 'Delete', 'Pair Time'])
graveyardRecordBear = b2cRecordBear.copy()
b2cRecordBull = c2bRecordBear.copy()
c2bRecordBull = b2cRecordBear.copy()
graveyardRecordBull = c2bRecordBull.copy()

averageBearTradeTime = float(linecache.getline('settings.cfg', 11).rstrip("\n\r"))
stdBearTradeTime = float(linecache.getline('settings.cfg', 13).rstrip("\n\r"))
tradeTimeBear = np.asarray([0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0])
tradeTimeBull = tradeTimeBear
tradeTimeBear[-1] = averageBearTradeTime

averageBullTradeTime = float(linecache.getline('settings.cfg', 15).rstrip("\n\r"))
stdBullTradeTime = float(linecache.getline('settings.cfg', 17).rstrip("\n\r"))
tradeTimeBull[-1] = averageBullTradeTime

lastMinuteTime = 0
lastHourTime = 0
lastFastMinuteTime = 0
fName = ""
btcOffset = 0
coinOffset = 0
minuteResults = 0
fastMinuteResults = 0
hourResults = 0
fee = 0.0025

# Bittrex
api_key = linecache.getline('settings.cfg', 3).rstrip("\n\r")
secret_key = linecache.getline('settings.cfg', 5).rstrip("\n\r")
bitcon = Bittrex(api_key, secret_key)

   
print('Starting Bittrex Bot')
global active
active = True
start = int(time.time())


#coins = np.array(['ETH','XRP','ARK','PAY'])
#ration = np.array([1,0,0,0])
coins = np.array(["ETH"])
ration = np.array([1])
if( len(ration)!= len(coins) or sum(ration)!=1):
    print("Incorrect ration array")
    quit()


### SETUP ALL VARIABLES FOR EACH COIN ###
for i in range(0, len(coins)):
    print(coins[i])
    exec("fName"+coins[i] + "= 'log_" + coins[i] + "_BTC_" +str(start) + ".txt'")
    exec("f = open(fName"+coins[i]+", 'w+')")
    f.close()
    temp = str(linecache.getline('settings.cfg', 13)).rstrip("\n\r")
    if (temp == 'true'):
        exec("logger(fName"+coins[i]+", 'not restoring "+coins[i]+" records')")
        #restore_records(coins[i])
    else:
        exec("logger(fName"+coins[i]+", 'restoring "+coins[i]+" records')")
        
    exec("csvName"+coins[i]+" = 'results_bittrex_"+coins[i]+"_" + str(start) + ".csv'")

    temp = bitcon.get_markets()
    for j in range(0, len(temp['result'])):
        if(temp['result'][j]['MarketCurrency'] == coins[i] and temp['result'][j]['BaseCurrency'] == 'BTC'):
            print('BINGO')
            exec("minSize"+coins[i]+" = float(temp['result'][i]['MinTradeSize'])")
            print("logger(fName"+coins[i]+", 'minSize"+coins[i]+"  is: ' + str(minSize"+coins[i]+"))")
            exec("logger(fName"+coins[i]+", 'minSize"+coins[i]+"  is: ' + str(minSize"+coins[i]+"))")
            

        
    exec("lastMinuteTime"+coins[i]+" = 0")
    exec("lastHourTime"+coins[i]+" = 0")
    exec("lastFastMinuteTime"+coins[i]+" = 0")
    exec("minuteResults"+coins[i]+" = 0")
    exec("hourResults"+coins[i]+" = 0")
    exec("fastMinuteResults"+coins[i]+" = 0")

    
    exec("c2bRecordBear"+coins[i]+" = c2bRecordBear.copy()")
    exec("b2cRecordBear"+coins[i]+" = b2cRecordBear.copy()")
    exec("graveyardRecordBear"+coins[i]+" = graveyardRecordBear.copy()")
    
    exec("c2bRecordBull"+coins[i]+" = c2bRecordBull.copy()")
    exec("b2cRecordBull"+coins[i]+" = b2cRecordBull.copy()")
    exec("graveyardRecordBull"+coins[i]+" = graveyardRecordBull.copy()")
    
    
    exec("tradeTimeBear"+coins[i]+" = tradeTimeBear")
    exec("averageBearTradeTime"+coins[i]+" = averageBearTradeTime")
    exec("stdBearTradeTime"+coins[i]+" = stdBearTradeTime")

    exec("tradeTimeBull"+coins[i]+" = tradeTimeBull")
    exec("averageBullTradeTime"+coins[i]+" = averageBullTradeTime")
    exec("stdBullTradeTime"+coins[i]+" = stdBullTradeTime")

    hola = False;

while (True):
    for i in range(0, len(coins)):
###     LOAD COIN SPECIFIC VARIABLES INTO GENERIC VARIABLES          ###
        exec("lastMinuteTime = lastMinuteTime"+coins[i])
        exec("lastHourTime = lastHourTime"+coins[i])
        exec("lastFastMinuteTime = lastFastMinuteTime" + coins[i])
        exec("minuteResults = minuteResults"+coins[i])
        exec("hourResults = hourResults"+coins[i])
        exec("fastMinuteResults = fastMinuteResults" + coins[i])
        exec("minSize = minSize"+coins[i])
        exec("fName = fName"+coins[i])
        exec("csvName = csvName"+coins[i])

        btcRation = ration[i]
        minuteTimeScale = 15
        hourTimeScale = 1
        fastMinuteTimeScale = 3
        timeLimit = 900

        exec("c2bRecordBear = c2bRecordBear" + coins[i] + ".copy()")
        exec("b2cRecordBear = b2cRecordBear" + coins[i] + ".copy()")
        exec("graveyardRecordBear = graveyardRecordBear" + coins[i] + ".copy()")

        exec("c2bRecordBull = c2bRecordBull" + coins[i] + ".copy()")
        exec("b2cRecordBull = b2cRecordBull" + coins[i] + ".copy()")
        exec("graveyardRecordBull = graveyardRecordBull" + coins[i] + ".copy()")

        exec("tradeTimeBear = tradeTimeBear" + coins[i])
        exec("averageBearTradeTime = averageBearTradeTime" + coins[i])
        exec("stdBearTradeTime = stdBearTradeTime" + coins[i])

        exec("tradeTimeBull = tradeTimeBull" + coins[i])
        exec("averageBullTradeTime = averageBullTradeTime" + coins[i])
        exec("stdBullTradeTime = stdBullTradeTime" + coins[i])
        


###-----------------CHOOSE BULL AND BEAR ALGORITHIMS-----------------###
        algo_coin2btc_bear = Algo.alwaysFalse
        algo_btc2coin_bear = Algo.alwaysFalse
        algo_btc2coin_bull = Algo.alwaysFalse
        algo_coin2btc_bull = Algo.alwaysFalse
###-----------------------RUN TRADE LOGIC----------------------------###


        run(fName, coins[i], minSize, btcOffset, btcRation, coinOffset, minuteTimeScale, hourTimeScale, fastMinuteTimeScale, timeLimit)



# LOAD BACK INTO COIN SPECIFIC VARIABLES #


        exec("c2bRecordBear" + coins[i] + " = c2bRecordBear.copy()")
        exec("b2cRecordBear" + coins[i] + " = b2cRecordBear.copy()")
        exec("graveyardRecordBear" + coins[i] + " = graveyardRecordBear.copy()")

        exec("c2bRecordBull" + coins[i] + " = c2bRecordBull.copy()")
        exec("b2cRecordBull" + coins[i] + " = b2cRecordBull.copy()")
        exec("graveyardRecordBull" + coins[i] + " = graveyardRecordBull.copy()")

        exec("lastMinuteTime" + coins[i] + " = lastMinuteTime")
        exec("lastHourTime" + coins[i] + " = lastHourTime")
        exec("lastFastMinuteTime" + coins[i] + " = lastFastMinuteTime")
        exec("minuteResults" + coins[i] + " = minuteResults")
        exec("hourResults" + coins[i] + " = hourResults")
        exec("fastMinuteResults" + coins[i] + " = fastMinuteResults")

        exec("tradeTimeBear" + coins[i] + " = tradeTimeBear")
        exec("averageBearTradeTime" + coins[i] + " = averageBearTradeTime")
        exec("stdBearTradeTime" + coins[i] + " = stdBearTradeTime")

        exec("tradeTimeBull" + coins[i] + " = tradeTimeBull")
        exec("averageBullTradeTime" + coins[i] + " = averageBullTradeTime")
        exec("stdBullTradeTime" + coins[i] + " = stdBullTradeTime")
    
        

        
        
        
        














