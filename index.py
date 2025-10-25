from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

rates = defaultdict(lambda: {'buy': 0.0, 'sell': 0.0})
cash_register = defaultdict(float) 
history = []  

def initialize_default_data():
    rates['USD'] = {'buy': 87.5, 'sell': 87.0}
    rates['EUR'] = {'buy': 95.0, 'sell': 94.5}
    rates['SOM'] = {'buy': 0.01, 'sell': 0.009}

    cash_register['USD'] = 1000.0
    cash_register['EUR'] = 500.0
    cash_register['SOM'] = 100000.0

def log_transaction(transaction_type, currency, amount, profit=0.0):
    transaction = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': transaction_type,
        'currency': currency.upper(),
        'amount': amount,
        'profit': profit
    }
    history.append(transaction)

def get_params(*args):
    return [request.args.get(arg, '') for arg in args]

@app.route('/')
def home():
    endpoints = {
        'rates': rates,
        'cash_register': cash_register,
        'history': history,
        "endpoints": {
            "/change_rate": "Updates buy/sell rate for currency. Params: currency, type (buy/sell), new_rate",
            "/sell": "Sells currency. Params: currency, amount",
            "/buy": "Buys currency. Params: currency, amount", 
            "/profit": "Returns profit. Optional params: currency, from (YYYY-MM-DD), to (YYYY-MM-DD)",
            "/amount": "Returns amounts. Optional param: currency"
        }
    }
    return jsonify(endpoints)

@app.route('/change_rate')
def change_rate():
    try:
        currency = request.args.get('currency', '').upper()
        rate_type = request.args.get('type', '').lower()
        new_rate = float(request.args.get('new_rate', ''))
        
        if not currency or not rate_type or not new_rate:return 'Enter all parameters'
        if rate_type not in ['buy', 'sell']:return 'Invalid rate type'
        if new_rate <= 0:return 'Invalid rate'
        
        rates[currency][rate_type] = new_rate
        
        return f"Successfully updated {rate_type} rate for {currency} to {new_rate}"
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/sell')
def sell():
    try:
        currency = request.args.get('currency', '').upper()
        amount = float(request.args.get('amount', ''))
        
        if not currency or not amount:return 'Enter all parameters'
        if amount <= 0:return 'Invalid amount'
        if currency not in rates:return 'Invalid currency'
        
        if cash_register[currency] < amount:return 'Insufficient balance'
        
        sell_rate = rates[currency]['sell']
        converted_amount = amount * sell_rate
        
        cash_register[currency] += amount
        cash_register['SOM'] -= converted_amount 

        profit = 0.0
        
        log_transaction('sell', currency, amount, profit)
        
        return f"Client successfully sold {amount} {currency}"
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/buy')
def buy():
    try:
        currency = request.args.get('currency', '').upper()
        amount = float(request.args.get('amount', ''))
        
        if not currency or not amount:return 'Enter all parameters'
        if amount <= 0:return 'Invalid amount'
        if currency not in rates:return 'Invalid currency'

        buy_rate = rates[currency]['buy']
        required_som = amount * buy_rate
        
        if cash_register['SOM'] < required_som:return 'Insufficient balance'
        
        cash_register['SOM'] += required_som
        cash_register[currency] -= amount
        
        sell_rate = rates[currency]['sell']
        profit = amount * (buy_rate - sell_rate)
        
        log_transaction('buy', currency, amount, profit)
    
        return f"Client successfully bought {amount} {currency}"
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/profit')
def profit():
    try:
        currency = request.args.get('currency', '').upper()
        from_date = request.args.get('from', '')
        to_date = request.args.get('to', '')
        
        filtered_history = history.copy()
        
        if currency:
            if currency not in rates:return 'Invalid currency'
            filtered_history = [t for t in filtered_history if t['currency'] == currency]
        
        if from_date and to_date:
            filtered_history = [
                t for t in filtered_history 
                if from_date <= t['date'] <= to_date
            ]
        
        total_profit = sum(transaction['profit'] for transaction in filtered_history)
        
        response = {
            "profit": total_profit,
            "transaction_count": len(filtered_history)
        }
        
        if currency:
            response["currency"] = currency
        if from_date and to_date:
            response["date_range"] = {"from": from_date, "to": to_date}
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/amount')
def amount():
    try:
        currency = request.args.get('currency', '').upper()
        
        if currency:
            if currency not in rates:return 'Invalid currency'
            return f"Currency: {currency}, Amount: {cash_register[currency]}"
        return cash_register
    except Exception as e:
        return jsonify({"error": "oshibka"})

if __name__ == '__main__':
    initialize_default_data()
    app.run(port=5000, debug=True) 