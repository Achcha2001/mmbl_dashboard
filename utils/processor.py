import pandas as pd
import glob
import os
import re

def summarize_uploads(upload_folder):
    """
    Reads all CSV/Excel files in upload_folder, concatenates them,
    and returns JSON‐serializable summaries:
      - daily_counts:    { 'YYYY-MM-DD': count, ... }
      - daily_amounts:   { 'YYYY-MM-DD': total_amount, ... }
      - bank_counts:     { bank_name: { 'YYYY-MM-DD': count, ... }, ... }
      - district_decline:{ district: { 'YYYY-MM-DD': pct_change, ... }, ... }
      - rep_counts:      { rep_name: total_count, ... }
      - visit_info:      { rep_name: { first: ISO, last: ISO }, ... }
      - monthly_country_counts: { country: { 'YYYY-MM': value, ... }, ... } (if wide format)
      - senders_country_counts: { country: count, ... }
      - transaction_status_counts: { status: count, ... }
      - daily_senders_country_counts: { 'YYYY-MM-DD': { country: count, ... }, ... }
      - daily_status_counts: { 'YYYY-MM-DD': { status: count, ... }, ... }
    """
    frames = []
    for path in glob.glob(os.path.join(upload_folder, '*')):
        ext = os.path.splitext(path)[1].lower()
        try:
            if ext == '.csv':
                df = pd.read_csv(path)
            elif ext in ('.xls', '.xlsx'):
                df = pd.read_excel(path)
            else:
                continue
            frames.append(df)
        except Exception:
            continue

    if not frames:
        return {
            'daily_counts': {},
            'daily_amounts': {},
            'bank_counts': {},
            'district_decline': {},
            'rep_counts': {},
            'visit_info': {},
            'monthly_country_counts': {},
            'senders_country_counts': {},
            'transaction_status_counts': {},
            'daily_senders_country_counts': {},
            'daily_status_counts': {}
        }

    full = pd.concat(frames, ignore_index=True)

    # --- Detect wide (Mon-YY) format columns ---
    month_pat = re.compile(r'^([A-Za-z]{3})-(\d{2})$')
    month_cols = [col for col in full.columns if month_pat.match(str(col))]
    monthly_country_counts = {}

    if 'Country' in full.columns and month_cols:
        # Wide format! (e.g., D2B Country Wise Stats)
        for _, row in full.iterrows():
            country = row['Country']
            for col in month_cols:
                m = month_pat.match(str(col))
                if not m:
                    continue
                month_str, year2 = m.groups()
                month_num = ['Jan','Feb','Mar','Apr','May','Jun','Jul','Aug','Sep','Oct','Nov','Dec'].index(month_str.title()) + 1
                year_full = int('20' + year2)
                ym_key = f"{year_full}-{month_num:02d}"
                value = row[col]
                if country not in monthly_country_counts:
                    monthly_country_counts[country] = {}
                monthly_country_counts[country][ym_key] = float(value) if pd.notna(value) else 0
        # Return only monthly summary for these wide-format files
        return {
            'daily_counts': {},
            'daily_amounts': {},
            'bank_counts': {},
            'district_decline': {},
            'rep_counts': {},
            'visit_info': {},
            'monthly_country_counts': monthly_country_counts,
            'senders_country_counts': {},
            'transaction_status_counts': {},
            'daily_senders_country_counts': {},
            'daily_status_counts': {}
        }

    # --- Else: fallback to original logic for long format files ---
    # --- Normalize Date ---
    if 'Date and Time' in full.columns:
        full['Date'] = pd.to_datetime(full['Date and Time'].astype(str).str[:10], errors='coerce')
    elif 'Date' in full.columns:
        full['Date'] = pd.to_datetime(full['Date'], errors='coerce')
    else:
        # No valid date column, return empty/partial
        return {
            'daily_counts': {},
            'daily_amounts': {},
            'bank_counts': {},
            'district_decline': {},
            'rep_counts': {},
            'visit_info': {},
            'monthly_country_counts': {},
            'senders_country_counts': {},
            'transaction_status_counts': {},
            'daily_senders_country_counts': {},
            'daily_status_counts': {}
        }
    full = full.dropna(subset=['Date'])
    full['DateOnly'] = full['Date'].dt.date

    # --- Daily Counts ---
    daily_series = full.groupby('DateOnly').size()
    daily_counts = {d.isoformat(): int(c) for d, c in daily_series.items()}

    # --- Daily Amounts ---
    if 'Transfer Amount' in full.columns:
        amt_series = full.groupby('DateOnly')['Transfer Amount'].sum()
        daily_amounts = {d.isoformat(): float(a) for d, a in amt_series.items()}
    else:
        daily_amounts = {}

    # --- Bank Counts ---
    bank_counts = {}
    if 'Bank Name' in full.columns:
        pivot = full.pivot_table(
            index='Bank Name',
            columns='DateOnly',
            aggfunc='size',
            fill_value=0
        ).sort_index(axis=1)
        for bank, row in pivot.iterrows():
            bank_counts[bank] = {d.isoformat(): int(cnt) for d, cnt in row.items()}

    # --- District % Change ---
    district_decline = {}
    if 'District' in full.columns:
        piv = full.pivot_table(
            index='District',
            columns='DateOnly',
            aggfunc='size',
            fill_value=0
        ).sort_index(axis=1)
        for dist, row in piv.iterrows():
            prev = None
            pct_map = {}
            for d, cnt in row.items():
                key = d.isoformat()
                pct_map[key] = round((cnt - prev) / prev * 100, 2) if prev and prev > 0 else None
                prev = cnt
            district_decline[dist] = pct_map

    # --- Representative Counts & Visit Info ---
    rep_counts = {}
    visit_info = {}
    if 'Representative' in full.columns:
        rep_counts = {r: int(c) for r, c in full.groupby('Representative').size().items()}
        visits = full.groupby('Representative')['Date and Time'].agg(['min', 'max'])
        for rep, times in visits.iterrows():
            first = pd.to_datetime(times['min'], errors='coerce')
            last  = pd.to_datetime(times['max'], errors='coerce')
            visit_info[rep] = {
                'first': first.isoformat() if not pd.isna(first) else None,
                'last':  last.isoformat()  if not pd.isna(last)  else None
            }

    # --- Sender's Country Counts (global) ---
    senders_country_counts = {}
    sender_col = None
    for col in full.columns:
        if str(col).lower().replace(' ', '').replace("'", "") in ["senderscountry", "sendercountry"]:
            sender_col = col
            break
    if sender_col:
        senders_country_counts = (
            full[sender_col].value_counts(dropna=True).to_dict()
        )

    # --- Transaction Status Counts (global) ---
    transaction_status_counts = {}
    status_col = None
    for col in full.columns:
        if 'status' in str(col).lower():
            status_col = col
            break
    if status_col:
        transaction_status_counts = (
            full[status_col].value_counts(dropna=True).to_dict()
        )

    # --- Sender's Country Daily Breakdown (filter-aware) ---
    daily_senders_country_counts = {}
    if sender_col:
        g = full.groupby(['DateOnly', sender_col]).size()
        for (date, country), cnt in g.items():
            date_str = date.isoformat()
            daily_senders_country_counts.setdefault(date_str, {})
            daily_senders_country_counts[date_str][country] = int(cnt)

    # --- Transaction Status Daily Breakdown (filter-aware) ---
    daily_status_counts = {}
    if status_col:
        g = full.groupby(['DateOnly', status_col]).size()
        for (date, status), cnt in g.items():
            date_str = date.isoformat()
            daily_status_counts.setdefault(date_str, {})
            daily_status_counts[date_str][status] = int(cnt)

    return {
        'daily_counts':     daily_counts,
        'daily_amounts':    daily_amounts,
        'bank_counts':      bank_counts,
        'district_decline': district_decline,
        'rep_counts':       rep_counts,
        'visit_info':       visit_info,
        'monthly_country_counts': {},
        'senders_country_counts': senders_country_counts,
        'transaction_status_counts': transaction_status_counts,
        'daily_senders_country_counts': daily_senders_country_counts,
        'daily_status_counts': daily_status_counts
    }
