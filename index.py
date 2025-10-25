from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# Data storage using defaultdict for in-memory storage
rates = defaultdict(lambda: {'buy': 0.0, 'sell': 0.0})  # Currency rates
cash_register = defaultdict(float)  # Available balances per currency
history = []  # List of all transactions

def initialize_default_data():
    """Initialize with some default example data"""
    # Set up some default rates
    rates['USD'] = {'buy': 87.5, 'sell': 87.0}
    rates['EUR'] = {'buy': 95.0, 'sell': 94.5}
    rates['SOM'] = {'buy': 0.01, 'sell': 0.009}
    
    # Set up some default cash balances
    cash_register['USD'] = 1000.0
    cash_register['EUR'] = 500.0
    cash_register['SOM'] = 100000.0

def log_transaction(transaction_type, currency, amount, profit=0.0):
    """Log a transaction to history"""
    transaction = {
        'date': datetime.now().isoformat(),
        'type': transaction_type,
        'currency': currency.upper(),
        'amount': amount,
        'profit': profit
    }
    history.append(transaction)

def validate_currency(currency):
    """Validate if currency exists in our rates"""
    return currency.upper() in rates

def validate_amount(amount_str):
    """Validate and convert amount to float"""
    try:
        amount = float(amount_str)
        if amount <= 0:
            return None
        return amount
    except (ValueError, TypeError):
        return None

def validate_rate(rate_str):
    """Validate and convert rate to float"""
    try:
        rate = float(rate_str)
        if rate <= 0:
            return None
        return rate
    except (ValueError, TypeError):
        return None

def validate_date(date_str):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@app.route('/')
def home():
    """Home route showing available endpoints"""
    endpoints = {
        "endpoints": {
            "/change_rate": "Updates buy/sell rate for currency. Params: currency, type (buy/sell), new_rate",
            "/sell": "Sells currency. Params: currency, amount",
            "/buy": "Buys currency. Params: currency, amount", 
            "/profit": "Returns profit. Optional params: currency, from (YYYY-MM-DD), to (YYYY-MM-DD)",
            "/amount": "Returns amounts. Optional param: currency"
        },
        "example_requests": {
            "change_rate": "/change_rate?currency=usd&type=buy&new_rate=87.6",
            "sell": "/sell?currency=usd&amount=50",
            "buy": "/buy?currency=usd&amount=50",
            "profit": "/profit?currency=usd",
            "amount": "/amount?currency=som"
        }
    }
    return jsonify(endpoints)

@app.route('/change_rate')
def change_rate():
    """Updates the buy or sell rate for the given currency"""
    try:
        currency = request.args.get('currency', '').upper()
        rate_type = request.args.get('type', '').lower()
        new_rate_str = request.args.get('new_rate', '')
        
        # Validate parameters
        if not currency or not rate_type or not new_rate_str:
            return jsonify({"error": "oshibka"})
        
        if rate_type not in ['buy', 'sell']:
            return jsonify({"error": "oshibka"})
        
        new_rate = validate_rate(new_rate_str)
        if new_rate is None:
            return jsonify({"error": "oshibka"})
        
        # Update the rate
        rates[currency][rate_type] = new_rate
        
        return jsonify({
            "message": f"Successfully updated {rate_type} rate for {currency} to {new_rate}",
            "currency": currency,
            "type": rate_type,
            "new_rate": new_rate
        })
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/sell')
def sell():
    """Sells currency - converts from specified currency to base currency"""
    try:
        currency = request.args.get('currency', '').upper()
        amount_str = request.args.get('amount', '')
        
        # Validate parameters
        if not currency or not amount_str:
            return jsonify({"error": "oshibka"})
        
        amount = validate_amount(amount_str)
        if amount is None:
            return jsonify({"error": "oshibka"})
        
        if not validate_currency(currency):
            return jsonify({"error": "oshibka"})
        
        # Check if we have enough balance
        if cash_register[currency] < amount:
            return jsonify({"error": "oshibka"})
        
        # Calculate conversion using sell rate
        sell_rate = rates[currency]['sell']
        converted_amount = amount * sell_rate
        
        # Update balances
        cash_register[currency] -= amount
        cash_register['SOM'] += converted_amount  # Assuming base currency is SOM
        
        # Calculate profit (difference between buy and sell rates)
        buy_rate = rates[currency]['buy']
        profit = amount * (buy_rate - sell_rate)
        
        # Log transaction
        log_transaction('sell', currency, amount, profit)
        
        return jsonify({
            "message": f"Successfully sold {amount} {currency}",
            "amount_sold": amount,
            "currency": currency,
            "converted_to_som": converted_amount,
            "profit": profit,
            "remaining_balance": cash_register[currency]
        })
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/buy')
def buy():
    """Buys currency - converts from base currency to specified currency"""
    try:
        currency = request.args.get('currency', '').upper()
        amount_str = request.args.get('amount', '')
        
        # Validate parameters
        if not currency or not amount_str:
            return jsonify({"error": "oshibka"})
        
        amount = validate_amount(amount_str)
        if amount is None:
            return jsonify({"error": "oshibka"})
        
        if not validate_currency(currency):
            return jsonify({"error": "oshibka"})
        
        # Calculate required SOM amount using buy rate
        buy_rate = rates[currency]['buy']
        required_som = amount * buy_rate
        
        # Check if we have enough SOM balance
        if cash_register['SOM'] < required_som:
            return jsonify({"error": "oshibka"})
        
        # Update balances
        cash_register['SOM'] -= required_som
        cash_register[currency] += amount
        
        # Calculate profit (difference between buy and sell rates)
        sell_rate = rates[currency]['sell']
        profit = amount * (sell_rate - buy_rate)
        
        # Log transaction
        log_transaction('buy', currency, amount, profit)
        
        return jsonify({
            "message": f"Successfully bought {amount} {currency}",
            "amount_bought": amount,
            "currency": currency,
            "som_spent": required_som,
            "profit": profit,
            "remaining_som_balance": cash_register['SOM']
        })
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

@app.route('/profit')
def profit():
    """Returns profit information"""
    try:
        currency = request.args.get('currency', '').upper()
        from_date = request.args.get('from', '')
        to_date = request.args.get('to', '')
        
        # Filter transactions based on parameters
        filtered_history = history.copy()
        
        # Filter by currency if specified
        if currency:
            if not validate_currency(currency):
                return jsonify({"error": "oshibka"})
            filtered_history = [t for t in filtered_history if t['currency'] == currency]
        
        # Filter by date range if specified
        if from_date and to_date:
            if not validate_date(from_date) or not validate_date(to_date):
                return jsonify({"error": "oshibka"})
            
            from_dt = datetime.strptime(from_date, '%Y-%m-%d')
            to_dt = datetime.strptime(to_date, '%Y-%m-%d')
            
            filtered_history = [
                t for t in filtered_history 
                if from_dt <= datetime.fromisoformat(t['date'].split('T')[0]) <= to_dt
            ]
        
        # Calculate total profit
        total_profit = sum(transaction['profit'] for transaction in filtered_history)
        
        response = {
            "total_profit": total_profit,
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
    """Returns amount information for currencies"""
    try:
        currency = request.args.get('currency', '').upper()
        
        if currency:
            # Return amount for specific currency
            if not validate_currency(currency):
                return jsonify({"error": "oshibka"})
            
            return jsonify({
                "currency": currency,
                "amount": cash_register[currency]
            })
        else:
            # Return amounts for all currencies
            amounts = {curr: balance for curr, balance in cash_register.items() if balance > 0}
            return jsonify({
                "amounts": amounts,
                "total_currencies": len(amounts)
            })
        
    except Exception as e:
        return jsonify({"error": "oshibka"})

if __name__ == '__main__':
    # Initialize with default data
    initialize_default_data()
    app.run(port=5002, debug=True)