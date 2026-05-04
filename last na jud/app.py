import os
import webbrowser
import threading

try:
    from flask import Flask, jsonify, request, session, render_template
except ImportError:
    print("=" * 50)
    print("ERROR: Flask is not installed.")
    print("Run the following command and try again:")
    print("    pip install flask")
    print("=" * 50)
    exit(1)

from database import Database


app = Flask(__name__)
app.secret_key = os.urandom(24)
db = Database()  
@app.route('/api/check_session')
def api_check_session():
    if 'user_id' in session:
        return jsonify({
            'logged_in': True,
            'user': {
                'username': session['username'],
                'email': session['email'],
                'user_id': session['user_id']
            }
        })
    return jsonify({'logged_in': False})

@app.route('/api/login', methods=['POST'])
def api_login():
    data = request.json
    user = db.authenticate_user(data.get('username_or_email'), data.get('password'))
    if user:
        session['user_id'] = user[0]
        session['username'] = user[1]
        session['email'] = user[2]
        return jsonify({'success': True, 'user': {'username': user[1], 'email': user[2], 'user_id': user[0]}})
    return jsonify({'success': False, 'error': 'Invalid credentials!'})

@app.route('/api/signup', methods=['POST'])
def api_signup():
    data = request.json
    user_id = db.create_user(data['username'], data['email'], data['password'])
    if user_id:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Username or email already exists!'})

@app.route('/api/logout', methods=['POST'])
def api_logout():
    session.clear()
    return jsonify({'success': True})

@app.route('/api/dashboard_data')
def api_dashboard_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    uid = session['user_id']
    total_exp, entries = db.get_total_expenses(uid)
    return jsonify({
        'total_income': db.get_total_income(uid),
        'total_expenses': total_exp,
        'total_entries': entries,
        'wallet_balance': db.get_total_income(uid) - total_exp,
        'net_savings': db.get_total_income(uid) - total_exp,
        'expenses_by_category': dict(db.get_expenses_by_category(uid)),
        'savings_goals': db.get_savings_goals(uid)
    })

@app.route('/api/expenses_data')
def api_expenses_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    uid = session['user_id']
    filter_by = request.args.get('filter', 'all')
    expenses = db.get_expenses(uid, None if filter_by == 'all' else filter_by)
    total, count = db.get_total_expenses(uid)
    return jsonify({
        'expenses': expenses,
        'total_expenses': total,
        'total_entries': count,
        'avg_expense': total / count if count else 0
    })

@app.route('/api/add_expense', methods=['POST'])
def api_add_expense():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    db.add_expense(session['user_id'], data['title'], data['amount'], data['category'], data['date'], data.get('notes', ''))
    return jsonify({'success': True})

@app.route('/api/income_data')
def api_income_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    uid = session['user_id']
    return jsonify({'income': db.get_income(uid), 'total_income': db.get_total_income(uid)})

@app.route('/api/add_income', methods=['POST'])
def api_add_income():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    db.add_income(session['user_id'], data['source'], data['amount'], data['date'], data['time'], data.get('notes', ''))
    return jsonify({'success': True})

@app.route('/api/savings_data')
def api_savings_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    uid = session['user_id']
    goals = db.get_savings_goals(uid)
    total_income = db.get_total_income(uid)
    total_exp = db.get_total_expenses(uid)[0]
    return jsonify({
        'savings_goals': goals,
        'total_income': total_income,
        'total_expenses': total_exp,
        'net_savings': total_income - total_exp,
        'total_saved': sum(g[3] for g in goals),
        'total_target': sum(g[2] for g in goals)
    })

@app.route('/api/add_savings_goal', methods=['POST'])
def api_add_savings_goal():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    db.add_savings_goal(session['user_id'], data['goal_name'], data['target_amount'])
    return jsonify({'success': True})

@app.route('/api/update_savings', methods=['POST'])
def api_update_savings():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    data = request.json
    db.update_savings(session['user_id'], data['goal_id'], data['amount'])
    return jsonify({'success': True})

@app.route('/api/settings_data')
def api_settings_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    uid = session['user_id']
    return jsonify({
        'user_info': db.get_user_info(uid),
        'login_history': db.get_login_history(uid)
    })

@app.route('/api/delete_all_data', methods=['POST'])
def api_delete_all_data():
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    db.delete_all_user_data(session['user_id'])
    return jsonify({'success': True})

@app.route('/')
def index():
    return render_template('main.html')

# ----- DELETE ENDPOINTS -----
@app.route('/api/delete_expense/<int:expense_id>', methods=['DELETE'])
def api_delete_expense(expense_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM expenses WHERE id = ? AND user_id = ?", (expense_id, session['user_id']))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    if deleted:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Expense not found'}), 404

@app.route('/api/delete_income/<int:income_id>', methods=['DELETE'])
def api_delete_income(income_id):
    if 'user_id' not in session:
        return jsonify({'error': 'Not logged in'}), 401
    conn = db.get_connection()
    cursor = conn.cursor()
    cursor.execute("DELETE FROM income WHERE id = ? AND user_id = ?", (income_id, session['user_id']))
    conn.commit()
    deleted = cursor.rowcount > 0
    conn.close()
    if deleted:
        return jsonify({'success': True})
    return jsonify({'success': False, 'error': 'Income not found'}), 404

if __name__ == '__main__':
    # Only open the browser in the main (non-reloader) process
    if not os.environ.get("WERKZEUG_RUN_MAIN"):
        threading.Timer(1.5, lambda: webbrowser.open('http://127.0.0.1:5000')).start()
    app.run(debug=True)