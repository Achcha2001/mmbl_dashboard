import os
import re
from datetime import datetime
from flask import (
    Flask, render_template, request, redirect,
    url_for, abort, jsonify, flash
)
from flask_login import (
    LoginManager, UserMixin,
    login_user, logout_user, current_user, login_required
)
from flask_sqlalchemy import SQLAlchemy
import pandas as pd

# --- Flask app setup ---
app = Flask(
    __name__,
    template_folder=os.path.join(os.path.dirname(__file__), 'templates'),
    static_folder=os.path.join(os.path.dirname(__file__), 'static')
)
app.secret_key = 'your-secret-key'
app.config['UPLOAD_FOLDER'] = os.path.join(os.path.dirname(__file__), 'uploads')

# --- SQLite + SQLAlchemy ---
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///app.db'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
db = SQLAlchemy(app)

# --- Models ---
class Upload(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)

class CountrywiseData(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    filename = db.Column(db.String(256), nullable=False)
    uploaded_at = db.Column(db.DateTime, default=datetime.utcnow)
    country = db.Column(db.String(100), nullable=False)
    year = db.Column(db.Integer, nullable=True)
    month = db.Column(db.Integer, nullable=True)
    value = db.Column(db.Float, nullable=True)

# --- Auth setup ---
login_manager = LoginManager(app)
login_manager.login_view = 'login'

USERS = {
    'admin': {'password': 'mmbl@123', 'is_admin': True}
}

class User(UserMixin):
    def __init__(self, username):
        self.id = username
        self.is_admin = USERS[username]['is_admin']

@login_manager.user_loader
def load_user(user_id):
    return User(user_id) if user_id in USERS else None

# --- App folder init ---
os.makedirs(app.config['UPLOAD_FOLDER'], exist_ok=True)
COUNTRY_UPLOADS_FOLDER = os.path.join(app.config['UPLOAD_FOLDER'], 'countrywise')
os.makedirs(COUNTRY_UPLOADS_FOLDER, exist_ok=True)
with app.app_context():
    db.create_all()

# --- Pages ---
@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        u = request.form.get('username')
        p = request.form.get('password')
        if u in USERS and USERS[u]['password'] == p:
            login_user(User(u))
            nxt = request.args.get('next') or url_for('view_transactions')
            return redirect(nxt)
        flash('Invalid credentials', 'danger')
    return render_template('login.html')

@app.route('/logout')
@login_required
def logout():
    logout_user()
    return redirect(url_for('login'))

@app.route('/')
@login_required
def view_transactions():
    return render_template('view_transactions.html')

@app.route('/subagents')
@login_required
def view_subagents():
    return render_template('view_subagents.html')

@app.route('/district_map')
@login_required
def district_map():
    return render_template('district_map.html')

@app.route('/settings')
@login_required
def settings():
    return render_template('settings.html')

@app.route('/country_analyze')
@login_required
def country_analyze():
    return render_template('country_analyze.html')

# --- Upload + Delete Management ---
@app.route('/upload', methods=['GET', 'POST'])
@login_required
def upload_file():
    if not current_user.is_admin:
        abort(403)

    if request.method == 'POST':
        for f in request.files.getlist('files[]'):
            dest = os.path.join(app.config['UPLOAD_FOLDER'], f.filename)
            f.save(dest)
            db.session.add(Upload(filename=f.filename))
            if 'country' in f.filename.lower():
                dest_cw = os.path.join(COUNTRY_UPLOADS_FOLDER, f.filename)
                if not os.path.exists(dest_cw):
                    with open(dest, 'rb') as src, open(dest_cw, 'wb') as out:
                        out.write(src.read())
                # Also: process & insert into CountrywiseData
                ext = os.path.splitext(dest_cw)[1].lower()
                try:
                    if ext in ('.xls', '.xlsx'):
                        df = pd.read_excel(dest_cw)
                    else:
                        df = pd.read_csv(dest_cw)
                except Exception as ex:
                    continue

                # Parse year/month from filename for fallback
                fname_match = re.search(r'(\d{4})\s+([A-Za-z]+)', f.filename)
                year = None
                month = None
                if fname_match:
                    year = int(fname_match.group(1))
                    try:
                        month = [
                            'January','February','March','April','May','June','July',
                            'August','September','October','November','December'
                        ].index(fname_match.group(2).capitalize()) + 1
                    except ValueError:
                        month = None

                # Remove previous if any
                CountrywiseData.query.filter_by(filename=f.filename).delete()

                # Wide format: Country | Jan-24 | Feb-24 ...
                if any(re.match(r'^[A-Za-z]{3}-\d{2}$', str(col)) for col in df.columns):
                    for _, row in df.iterrows():
                        country = row['Country']
                        for col in df.columns:
                            m = re.match(r'^([A-Za-z]{3})-(\d{2})$', str(col))
                            if not m:
                                continue
                            col_month = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(m.group(1).capitalize()) + 1
                            col_year = int('20' + m.group(2))
                            val = row[col]
                            db.session.add(CountrywiseData(
                                filename=f.filename,
                                country=country,
                                year=col_year,
                                month=col_month,
                                value=float(val) if pd.notna(val) else None
                            ))
                else:
                    # Long format (Country, Amount, Date)
                    for _, row in df.iterrows():
                        country = row['Country'] if 'Country' in row else None
                        val = row['Amount'] if 'Amount' in row else None
                        row_year, row_month = year, month
                        date_col = next((c for c in df.columns if 'date' in c.lower()), None)
                        if date_col and pd.notna(row[date_col]):
                            try:
                                dt = pd.to_datetime(row[date_col])
                                row_year, row_month = dt.year, dt.month
                            except Exception:
                                pass
                        db.session.add(CountrywiseData(
                            filename=f.filename,
                            country=country,
                            year=row_year,
                            month=row_month,
                            value=float(val) if pd.notna(val) else None
                        ))
        db.session.commit()
        flash('File(s) uploaded successfully', 'success')
        return redirect(request.args.get('next') or url_for('view_transactions'))

    uploads = Upload.query.order_by(Upload.uploaded_at.desc()).all()
    return render_template('upload.html', uploads=uploads)

@app.route('/upload/delete/<int:upload_id>', methods=['POST'])
@login_required
def delete_file(upload_id):
    if not current_user.is_admin:
        abort(403)
    record = Upload.query.get_or_404(upload_id)
    fname = os.path.basename(record.filename)
    CountrywiseData.query.filter_by(filename=fname).delete()
    if '/' in record.filename:
        path = os.path.join(app.config['UPLOAD_FOLDER'], record.filename)
    else:
        path = os.path.join(app.config['UPLOAD_FOLDER'], record.filename)
    if os.path.exists(path):
        try:
            os.remove(path)
        except Exception as e:
            flash(f"Error deleting file on disk: {e}", "warning")
    db.session.delete(record)
    db.session.commit()
    flash(f"Deleted {record.filename}", "success")
    return redirect(request.args.get('next') or url_for('upload_file'))

# --- JSON API ---
@app.route('/api/summary')
@login_required
def api_summary():
    from utils.processor import summarize_uploads
    return jsonify(summarize_uploads(app.config['UPLOAD_FOLDER']))

# ----------- FORECAST API using model -----------
from utils.forecast import get_forecast

@app.route('/api/forecast')
@login_required
def forecast_api():
    periods = int(request.args.get('periods', 6))
    try:
        result = get_forecast(periods)
        return jsonify(result)
    except Exception as e:
        return jsonify({'error': str(e)}), 500

@app.route('/api/country_summary')
@login_required
def api_country_summary():
    # Query database, aggregate as needed
    from collections import defaultdict
    records = CountrywiseData.query.all()
    monthly_by_country = defaultdict(dict)
    country_counts = defaultdict(float)
    annual_avg = {}
    for rec in records:
        if rec.country and rec.year and rec.month:
            key = f"{rec.year:04d}-{rec.month:02d}"
            monthly_by_country[rec.country][key] = monthly_by_country[rec.country].get(key, 0) + (rec.value or 0)
            country_counts[rec.country] += (rec.value or 0)
    for country, mmap in monthly_by_country.items():
        if mmap:
            avg = sum(mmap.values()) / len(mmap)
            annual_avg[country] = round(avg, 2)
    return jsonify({
        'country_counts': dict(country_counts),
        'monthly_by_country': dict(monthly_by_country),
        'annual_avg': annual_avg
    })

@app.route('/api/countrywise_files')
@login_required
def api_countrywise_files():
    files = [u.filename for u in Upload.query.order_by(Upload.uploaded_at.desc()).all()
             if 'country' in u.filename.lower()]
    files = [f.replace('countrywise/', '') if f.startswith('countrywise/') else f for f in files]
    return jsonify(files)

@app.route('/api/countrywise_stats')
@login_required
def api_countrywise_stats():
    fname = request.args.get('file')
    if not fname:
        return jsonify({'error': 'No file specified'}), 400
    stats = {}
    return jsonify(stats)

# --- MAIN ---
if __name__ == '__main__':
    app.run(debug=True)
