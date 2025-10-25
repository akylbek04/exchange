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

def initialize_data():
    rates['usd'] = {'buy': 85.0, 'sell': 87.0}
    rates['eur'] = {'buy': 95.0, 'sell': 97.0}
    rates['som'] = {'buy': 0.01, 'sell': 0.011}
    
    cash_register['usd'] = 1000.0
    cash_register['eur'] = 500.0
    cash_register['som'] = 100000.0

def get_error_response():
    return jsonify({"error": "oshibka"}), 400

def validate_currency(currency):
    return currency.lower() in rates

def validate_amount(amount_str):
    try:
        amount = float(amount_str)
        return amount > 0, amount
    except (ValueError, TypeError):
        return False, 0

def validate_rate(rate_str):
    try:
        rate = float(rate_str)
        return rate > 0, rate
    except (ValueError, TypeError):
        return False, 0

def validate_date(date_str):
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@app.route('/change_rate')
def change_rate():
    try:
        currency = request.args.get('currency', '').lower()
        rate_type = request.args.get('type', '').lower()
        new_rate_str = request.args.get('new_rate', '')
        
        if not currency or not rate_type or not new_rate_str:return get_error_response()
        if rate_type not in ['buy', 'sell']:return get_error_response()
        
        valid_rate, new_rate = validate_rate(new_rate_str)
        if not valid_rate:return get_error_response()
        
        rates[currency][rate_type] = new_rate
        
        return  f"Successfully updated {rate_type} rate for {currency.upper()} to {new_rate}"
    except Exception:
        return get_error_response()

@app.route('/sell')
def sell():
    try:
        currency = request.args.get('currency', '').lower()
        amount_str = request.args.get('amount', '')
        
        if not currency or not amount_str:
            return get_error_response()
        
        if not validate_currency(currency):
            return get_error_response()
        
        valid_amount, amount = validate_amount(amount_str)
        if not valid_amount:
            return get_error_response()
        
        if cash_register[currency] < amount:
            return get_error_response()
        
        # Calculate profit (difference between buy and sell rates)
        buy_rate = rates[currency]['buy']
        sell_rate = rates[currency]['sell']
        profit = (sell_rate - buy_rate) * amount
        
        # Update cash register
        cash_register[currency] -= amount
        
        # Record transaction in history
        transaction = {
            'timestamp': datetime.now().isoformat(),
            'type': 'sell',
            'currency': currency.upper(),
            'amount': amount,
            'rate': sell_rate,
            'profit': profit
        }
        history.append(transaction)
        
        return jsonify({
            "message": f"Successfully sold {amount} {currency.upper()}",
            "currency": currency.upper(),
            "amount": amount,
            "rate": sell_rate,
            "profit": profit,
            "remaining_balance": cash_register[currency]
        })
    
    except Exception:
        return get_error_response()

@app.route('/profit')
def profit():
    """
    Returns profit information.
    /profit - total profit across all currencies
    /profit?currency=usd - profit only for USD
    /profit?from=YYYY-MM-DD&to=YYYY-MM-DD - profit in date range
    """
    try:
        currency = request.args.get('currency', '').lower()
        from_date = request.args.get('from', '')
        to_date = request.args.get('to', '')
        
        filtered_transactions = history.copy()
        
        if currency:
            if not validate_currency(currency):
                return get_error_response()
            filtered_transactions = [t for t in filtered_transactions if t['currency'].lower() == currency]
        
        # Filter by date range if specified
        if from_date and to_date:
            if not validate_date(from_date) or not validate_date(to_date):
                return get_error_response()
            
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            
            filtered_transactions = [
                t for t in filtered_transactions 
                if from_dt <= datetime.fromisoformat(t['timestamp'].replace('Z', '+00:00')) <= to_dt
            ]
        elif from_date or to_date:
            # If only one date is provided, it's an error
            return get_error_response()
        
        # Calculate total profit
        total_profit = sum(transaction['profit'] for transaction in filtered_transactions)
        
        # Group by currency for detailed breakdown
        profit_by_currency = defaultdict(float)
        for transaction in filtered_transactions:
            profit_by_currency[transaction['currency']] += transaction['profit']
        
        response = {
            "total_profit": total_profit,
            "profit_by_currency": dict(profit_by_currency),
            "transaction_count": len(filtered_transactions)
        }
        
        if currency:
            response["currency"] = currency.upper()
        
        if from_date and to_date:
            response["date_range"] = {
                "from": from_date,
                "to": to_date
            }
        return jsonify(response)
    except Exception:
        return get_error_response()

@app.route('/amount')
def amount():
    try:
        currency = request.args.get('currency', '').lower()
        
        if not currency: return 'Currency is required'
        if currency not in rates: return 'Currency not found'
        
        return jsonify({
            "currency": currency,
            "amount": cash_register[currency]
        })
    except Exception:
        return get_error_response()

@app.route('/')
def home():
    return jsonify({
        "message": "Currency Exchanger REST API",
        "endpoints": {
            "change_rate": "GET /change_rate?currency=usd&type=buy&new_rate=87.6",
            "sell": "GET /sell?currency=usd&amount=50",
            "profit": "GET /profit or /profit?currency=usd or /profit?from=2024-01-01&to=2024-12-31",
            "amount": "GET /amount?currency=som",
            "status": "GET /status"
        }
    })

if __name__ == '__main__':
    initialize_data()
    app.run(port=5002, debug=True)