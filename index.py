from flask import Flask, request, jsonify
from flask_cors import CORS
from collections import defaultdict
from datetime import datetime
import json

app = Flask(__name__)
CORS(app)

# In-memory data storage
rates = defaultdict(lambda: {'buy': 0.0, 'sell': 0.0})  # stores current buy/sell rates per currency
cash_register = defaultdict(float)  # stores available currency balances
history = []  # list of operations with timestamps

# Initialize with some sample data
def initialize_data():
    """Initialize the system with sample currency data"""
    # Sample rates
    rates['usd'] = {'buy': 85.0, 'sell': 87.0}
    rates['eur'] = {'buy': 95.0, 'sell': 97.0}
    rates['som'] = {'buy': 0.01, 'sell': 0.011}
    
    # Sample cash register balances
    cash_register['usd'] = 1000.0
    cash_register['eur'] = 500.0
    cash_register['som'] = 100000.0

def get_error_response():
    """Return standardized error response"""
    return jsonify({"error": "oshibka"}), 400

def validate_currency(currency):
    """Validate if currency exists in our system"""
    return currency.lower() in rates

def validate_amount(amount_str):
    """Validate and convert amount to float"""
    try:
        amount = float(amount_str)
        return amount > 0, amount
    except (ValueError, TypeError):
        return False, 0

def validate_rate(rate_str):
    """Validate and convert rate to float"""
    try:
        rate = float(rate_str)
        return rate > 0, rate
    except (ValueError, TypeError):
        return False, 0

def validate_date(date_str):
    """Validate date format YYYY-MM-DD"""
    try:
        datetime.strptime(date_str, '%Y-%m-%d')
        return True
    except ValueError:
        return False

@app.route('/change_rate', methods=['GET'])
def change_rate():
    """
    Updates the buy or sell rate for the given currency.
    /change_rate?currency=usd&type=buy&new_rate=87.6
    """
    try:
        currency = request.args.get('currency', '').lower()
        rate_type = request.args.get('type', '').lower()
        new_rate_str = request.args.get('new_rate', '')
        
        # Validate parameters
        if not currency or not rate_type or not new_rate_str:
            return get_error_response()
        
        if rate_type not in ['buy', 'sell']:
            return get_error_response()
        
        valid_rate, new_rate = validate_rate(new_rate_str)
        if not valid_rate:
            return get_error_response()
        
        # Update the rate
        rates[currency][rate_type] = new_rate
        
        return jsonify({
            "message": f"Successfully updated {rate_type} rate for {currency.upper()} to {new_rate}",
            "currency": currency.upper(),
            "type": rate_type,
            "new_rate": new_rate
        })
    
    except Exception:
        return get_error_response()

@app.route('/sell', methods=['GET'])
def sell():
    """
    Sells currency.
    /sell?currency=usd&amount=50
    """
    try:
        currency = request.args.get('currency', '').lower()
        amount_str = request.args.get('amount', '')
        
        # Validate parameters
        if not currency or not amount_str:
            return get_error_response()
        
        if not validate_currency(currency):
            return get_error_response()
        
        valid_amount, amount = validate_amount(amount_str)
        if not valid_amount:
            return get_error_response()
        
        # Check if we have sufficient balance
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

@app.route('/profit', methods=['GET'])
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
        
        # Filter transactions based on parameters
        filtered_transactions = history.copy()
        
        # Filter by currency if specified
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

@app.route('/amount', methods=['GET'])
def amount():
    """
    Returns the total amount in the specified currency.
    /amount?currency=som
    """
    try:
        currency = request.args.get('currency', '').lower()
        
        if not currency:
            return get_error_response()
        
        if not validate_currency(currency):
            return get_error_response()
        
        total_amount = cash_register[currency]
        
        return jsonify({
            "currency": currency.upper(),
            "amount": total_amount
        })
    
    except Exception:
        return get_error_response()

@app.route('/status', methods=['GET'])
def status():
    """
    Additional endpoint to check system status and all data
    """
    return jsonify({
        "rates": dict(rates),
        "cash_register": dict(cash_register),
        "recent_transactions": history[-10:] if history else [],
        "total_transactions": len(history)
    })

@app.route('/', methods=['GET'])
def home():
    """Home endpoint with API documentation"""
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
    print("Currency Exchanger API initialized with sample data")
    print("Available currencies:", list(rates.keys()))
    print("Starting server on port 5002...")
    app.run(port=5002, debug=True)