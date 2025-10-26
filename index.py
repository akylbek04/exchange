from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from datetime import datetime

app = Flask(__name__)
CORS(app)

rates = defaultdict(lambda: {'buy': 0.0, 'sell': 0.0})
cash_register = defaultdict(float) 
history = []  

def log_transaction(transaction_type, currency, amount, profit=0.0):
    transaction = {
        'date': datetime.now().strftime('%Y-%m-%d'),
        'type': transaction_type,
        'currency': currency,
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
    return endpoints

@app.route('/cash_register')
def cash_register_route():
    try:
        currency, amount = get_params('currency', 'amount')
        amount = float(amount)
        
        if not currency or not amount:return 'Enter all parameters'
        if amount <= 0:return 'Invalid amount'
        
        cash_register[currency] += amount
        return f"Successfully added {amount} {currency} to cash register"
    except Exception as e:
        return jsonify({"error": e})

@app.route('/change_rate')
def change_rate():
    try:
        currency, rate_type, new_rate = get_params('currency', 'type', 'new_rate')
        new_rate = float(new_rate)
        
        if not currency or not rate_type or not new_rate:return 'Enter all parameters'
        if rate_type not in ['buy', 'sell']:return 'Invalid rate type'
        if new_rate <= 0:return 'Invalid rate'
        
        rates[currency][rate_type] = new_rate

        message = "updated" if currency in rates else "added"
        
        return f"Successfully {message} {rate_type} rate for {currency} to {new_rate}"
    except Exception as e:
        return jsonify({"error": e})

@app.route('/sell')
def sell():
    try:
        currency, amount = get_params('currency', 'amount')
        currency = currency.lower()
        amount = float(amount)
        
        if not currency or not amount:return 'Enter all parameters'
        if amount <= 0:return 'Invalid amount'
        if currency not in rates:return 'Invalid currency'
        
        if cash_register[currency] < amount:return 'Insufficient balance'
        
        sell_rate = rates[currency]['sell']
        converted_amount = amount * sell_rate
        
        cash_register[currency] += amount
        cash_register['som'] -= converted_amount 
        
        log_transaction('sell', currency, amount)
        
        return f"Client successfully sold {amount} {currency}"
    except Exception as e:
        return jsonify({"error": e})

@app.route('/buy')
def buy():
    try:
        currency, amount = get_params('currency', 'amount')
        currency = currency.lower()
        amount = float(amount)

        print(currency)
        
        if not currency or not amount:return 'Enter all parameters'
        if amount <= 0:return 'Invalid amount'
        if currency not in rates:return 'Invalid currency'

        buy_rate = rates[currency]['buy']
        required_som = amount * buy_rate
        
        if cash_register['som'] < required_som:return 'Insufficient balance'
        
        cash_register['som'] += required_som
        cash_register[currency] -= amount
        
        sell_rate = rates[currency]['sell']
        profit = amount * (buy_rate - sell_rate)
        cash_register['som'] += profit
        
        log_transaction('buy', currency, amount, profit)
    
        return f"Client successfully bought {amount} {currency}"
        
    except Exception as e:
        return jsonify({"error":e})

@app.route('/profit')
def profit():
    try:
        currency, from_date, to_date = get_params('currency', 'from', 'to')
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
            "profit": f'{total_profit} soms',
            "transaction_count": len(filtered_history)
        }
        
        if currency:
            response["currency"] = currency
        if from_date and to_date:
            response["date_range"] = {"from": from_date, "to": to_date}
        
        return jsonify(response)
        
    except Exception as e:
        return jsonify({"error": e})

@app.route('/amount')
def amount():
    try:
        currency = get_params('currency')
        
        if currency:
            if currency not in rates:return 'Invalid currency'
            return f"Currency: {currency}, Amount: {cash_register[currency]}"
        return cash_register
    except Exception as e:
        return jsonify({"error": e})

if __name__ == '__main__':
    app.run(port=5000, debug=True) 