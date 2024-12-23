import traceback

from flask import Flask, render_template, request, redirect, url_for, flash
import pandas as pd
import os
from werkzeug.utils import secure_filename
from datetime import datetime
import json
import logging

# Configure logging
logging.basicConfig(level=logging.INFO)


app = Flask(__name__)
app.secret_key = 'your_secret_key'  # Replace with your actual secret key

# Configuration
RESULTS_CSV = 'results_summary.csv'
UPLOAD_FOLDER = 'uploads'
ALLOWED_EXTENSIONS = {'csv'}

app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER
app.config['MAX_CONTENT_LENGTH'] = 16 * 1024 * 1024  # 16 MB upload limit

# Ensure the upload folder exists
os.makedirs(UPLOAD_FOLDER, exist_ok=True)


def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS


# Initialize results file if it does not exist
if not os.path.isfile(RESULTS_CSV):
    df = pd.DataFrame(columns=['avg_profit', 'total_trades', 'total_profit', 'winning_trades', 'losing_trades'])
    df.to_csv(RESULTS_CSV, index=False)

if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

@app.route('/', methods=['GET', 'POST'])
def manage_files():
    if request.method == 'POST':
        action = request.form.get('action')
        app.logger.info(f"Action received: {action}")

        if action == 'upload':
            # Handle file uploads
            if 'file' not in request.files:
                flash('No file part in the request.', 'danger')
                return redirect(url_for('manage_files'))
            files = request.files.getlist('file')
            if not files or files[0].filename == '':
                flash('No files selected for uploading.', 'warning')
                return redirect(url_for('manage_files'))
            for file in files:
                if file and allowed_file(file.filename):
                    filename = secure_filename(file.filename)
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        flash(f'File "{filename}" already exists.', 'warning')
                        continue
                    try:
                        # Validate CSV file
                        df = pd.read_csv(file)
                        file.seek(0)  # Reset file pointer
                        file.save(file_path)
                        flash(f'File "{filename}" uploaded successfully.', 'success')
                        app.logger.info(f'File "{filename}" uploaded successfully.')
                    except Exception as e:
                        flash(f'Invalid CSV file "{filename}": {e}', 'danger')
                        app.logger.error(f'Error processing file "{filename}": {e}')
                else:
                    flash(f'Invalid file type for "{file.filename}". Only CSV files are allowed.', 'danger')
            return redirect(url_for('manage_files'))

        elif action == 'delete_selected':
            # Handle deletion of selected files
            selected_files = request.form.getlist('selected_files')
            if not selected_files:
                flash('No files selected for deletion.', 'warning')
            else:
                for filename in selected_files:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    if os.path.exists(file_path):
                        try:
                            os.remove(file_path)
                            flash(f'File "{filename}" deleted successfully.', 'success')
                            app.logger.info(f'File "{filename}" deleted successfully.')
                        except Exception as e:
                            flash(f'Error deleting file "{filename}": {e}', 'danger')
                            app.logger.error(f'Error deleting file "{filename}": {e}')
                    else:
                        flash(f'File "{filename}" does not exist.', 'warning')
            return redirect(url_for('manage_files'))

        elif action == 'delete_all':
            # Handle deletion of all files
            uploaded_files = [f for f in os.listdir(app.config['UPLOAD_FOLDER']) if allowed_file(f)]
            if not uploaded_files:
                flash('No files to delete.', 'warning')
            else:
                for filename in uploaded_files:
                    file_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
                    try:
                        os.remove(file_path)
                        app.logger.info(f'File "{filename}" deleted successfully.')
                    except Exception as e:
                        flash(f'Error deleting file "{filename}": {e}', 'danger')
                        app.logger.error(f'Error deleting file "{filename}": {e}')
                flash('All files have been deleted.', 'success')
            return redirect(url_for('manage_files'))

        else:
            flash('Invalid action.', 'danger')
            app.logger.error(f'Invalid action: {action}')
            return redirect(url_for('manage_files'))

    # Handle GET request: Display the manage_files page
    uploaded_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                df = pd.read_csv(filepath)
                rows, columns = df.shape
                uploaded_files.append({
                    'name': filename,
                    'rows': rows,
                    'columns': columns
                })
                app.logger.info(f'Loaded file "{filename}" with {rows} rows and {columns} columns')
            except Exception as e:
                flash(f'Error processing file "{filename}": {e}', 'danger')
                app.logger.error(f'Error processing file "{filename}": {e}')
                continue

    return render_template('manage_files.html', uploaded_files=uploaded_files)
@app.route('/index')
def index():
    # Load existing summary data
    if os.path.exists(RESULTS_CSV):
        summary_data = pd.read_csv(RESULTS_CSV)
    else:
        summary_data = pd.DataFrame()

    # List all CSV files in the upload folder and gather metadata
    uploaded_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                df = pd.read_csv(filepath)
                rows, columns = df.shape
                uploaded_files.append({
                    'name': filename,
                    'rows': rows,
                    'columns': columns
                })
            except Exception as e:
                # If there's an error reading the CSV, skip the file and optionally log the error
                flash(f'Error processing file "{filename}": {e}')
                continue

    return render_template('index.html',
                           reports=summary_data.to_dict(orient='records'),
                           uploaded_files=uploaded_files)


@app.route('/upload', methods=['POST'])
def upload():
    if 'file' not in request.files:
        flash('No file part in the request.')
        return redirect(url_for('index'))

    files = request.files.getlist('file')
    if not files or files[0].filename == '':
        flash('No files selected for uploading.')
        return redirect(url_for('index'))

    for file in files:
        if file and allowed_file(file.filename):
            filename = secure_filename(file.filename)
            save_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            try:
                file.save(save_path)
                flash(f'File "{filename}" uploaded successfully.')

                # Process the uploaded CSV file
                orders_df = pd.read_csv(save_path)

                # Drop 'Balance' column if it exists
                if 'Balance' in orders_df.columns:
                    orders_df = orders_df.drop(columns=['Balance'])
                else:
                    flash(f'File "{filename}" does not contain a "Balance" column. Skipping this file.')
                    continue  # Skip processing this file if 'Balance' column is missing

                # Calculate metrics
                avg_profit = orders_df['P&L'].mean()
                total_trades = len(orders_df)
                total_profit = orders_df['P&L'].sum()
                winning_trades = len(orders_df.loc[orders_df['P&L'] >= 0])
                losing_trades = len(orders_df.loc[orders_df['P&L'] < 0])

                # Append metrics to the summary CSV
                new_entry = {
                    'avg_profit': avg_profit,
                    'total_trades': total_trades,
                    'total_profit': total_profit,
                    'winning_trades': winning_trades,
                    'losing_trades': losing_trades
                }
                summary_df = pd.read_csv(RESULTS_CSV)
                summary_df = summary_df.append(new_entry, ignore_index=True)
                summary_df.to_csv(RESULTS_CSV, index=False)

            except Exception as e:
                flash(f'An error occurred while processing file "{filename}": {e}')
                continue
        else:
            flash(f'File "{file.filename}" is not a supported CSV file.')

    return redirect(url_for('index'))


@app.route('/orders', methods=['GET', 'POST'])
def orders():
    uploaded_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            uploaded_files.append(filename)

    selected_file = None
    table_data = None

    if request.method == 'POST':
        selected_file = request.form.get('csv_file')
        if selected_file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)

                    if 'MagicNumber' not in df.columns:
                        df['MagicNumber'] = '#N/A'

                    # Sort by the first column
                    first_column = df.columns[0]
                    df = df.sort_values(by=first_column)

                    table_data = df.to_dict(orient='records')
                    headers = df.columns.tolist()
                    return render_template('orders.html',
                                           uploaded_files=uploaded_files,
                                           selected_file=selected_file,
                                           headers=headers,
                                           table_data=table_data)
                except Exception as e:
                    flash(f'Error reading file "{selected_file}": {e}')
            else:
                flash(f'File "{selected_file}" does not exist.')

    return render_template('orders.html',
                           uploaded_files=uploaded_files,
                           selected_file=selected_file,
                           table_data=table_data)


@app.route('/mam_orders', methods=['GET', 'POST'])
def mam_orders():
    selected_file = 'mam-history-orders-5630165.csv'
    table_data = None

    if selected_file:
        file_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
        if os.path.exists(file_path):
            try:
                df = pd.read_csv(file_path)


                # Sort by the first column
                first_column = df.columns[0]
                df = df.sort_values(by=first_column)
                df = df.loc[df.OrderType.isin(['Sell', 'Buy'])]
                if 'Comments' in df.columns:
                    df.drop(columns=['Comments'], inplace=True)

                table_data = df.to_dict(orient='records')
                headers = df.columns.tolist()
                return render_template('mam_orders.html',
                                       selected_file=selected_file,
                                       headers=headers,
                                       table_data=table_data)
            except Exception as e:
                flash(f'Error reading file "{selected_file}": {e}')
        else:
            flash(f'File "{selected_file}" does not exist.')

    return render_template('mam_orders.html',
                           selected_file=selected_file,
                           table_data=table_data)

# app.py
@app.route('/mam_summary', methods=['GET', 'POST'])
def mam_summary():
    dates, balances, open_dates, open_orders, rentabilidades = [], [], [], [], []
    rentabilidad_last_dates, rentabilidad_last_values = [], []
    magic_numbers = []

    uploaded_files = []

    selected_file = None
    summary_table_symbol = None
    summary_table_side = None
    initial_balance = 100000.00  # Default initial balance

    # Mapping OrderType to side
    order_type_mapping = {
        'Buy': 'buy',
        'Sell': 'sell'
    }

    selected_file = 'mam-history-orders-5630165.csv'
    initial_balance_input = request.form.get('initial_balance')

    file_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
    if os.path.exists(file_path):
        try:
            # df = pd.read_csv(os.path.join('./dashboard/uploads', selected_file))
            df = pd.read_csv(file_path)

            # Check required columns
            required_columns = ['OrderTicket', 'OrderType', 'OrderStatus', 'Symbol', 'Volume', 'OpenPrice',
                                'OpenTime', 'ClosePrice', 'CloseTime', 'Profit']
            if not all(col in df.columns for col in required_columns):
                flash(f'File "{selected_file}" is missing required columns.')
                return redirect(url_for('mam_summary'))

            # Handle missing Symbol entries by filling with 'Unknown'
            df['Symbol'] = df['Symbol'].fillna('Unknown')

            initial_balance = df.loc[df.OrderTypeInt==6]['Profit'].sum()
            initial_balance = 0

            # Compute 'G/P' based on 'Profit'
            df['G/P'] = df['Profit'].apply(lambda x: 'G' if x >= 0 else 'P')

            # Map 'OrderType' to 'side'
            df['side'] = df['OrderType'].map(order_type_mapping).fillna('Unknown')

            # Convert 'OpenTime' to datetime
            df['OpenTime'] = pd.to_datetime(df['OpenTime'], format='%Y.%m.%d %H:%M', errors='coerce')

            # Convert 'CloseTime' to datetime, handling 'N/A' values
            df['CloseTime'] = pd.to_datetime(df['CloseTime'], format='%Y.%m.%d %H:%M', errors='coerce')

            # For open orders, set 'CloseTime_Adjusted' to current time
            df['CloseTime_Adjusted'] = df['CloseTime']
            df.loc[df['CloseTime'].isna(), 'CloseTime_Adjusted'] = pd.Timestamp.now()

            # Calculate 'Duración' in minutes
            df['Duración'] = (df['CloseTime_Adjusted'] - df['OpenTime']).dt.total_seconds() / 60

            # -----
            # For balance operations (OrderTypeInt == 6)
            df_balance_ops = df[df['OrderTypeInt'] == 6][['OpenTime', 'Profit']].copy()
            df_balance_ops = df_balance_ops.rename(columns={'OpenTime': 'Time'})

            # For closed 'sell' or 'buy' orders
            df_closed_orders = df[
                df['side'].isin(['sell', 'buy']) & df['CloseTime'].notnull()
                ][['CloseTime', 'Profit']].copy()
            df_closed_orders = df_closed_orders.rename(columns={'CloseTime': 'Time'})

            # Combine both DataFrames
            balance_changes = pd.concat([df_balance_ops, df_closed_orders], ignore_index=True)
            # Sort by Time
            balance_changes = balance_changes.sort_values('Time')
            # Calculate cumulative balance
            balance_changes['Cumulative_Balance'] = initial_balance + balance_changes['Profit'].cumsum()
            # Sort the original DataFrame by OpenTime
            df = df.sort_values('OpenTime')

            # Merge cumulative balance
            df = pd.merge_asof(
                df,
                balance_changes[['Time', 'Cumulative_Balance']],
                left_on='OpenTime',
                right_on='Time',
                direction='backward'
            )

            # Handle division by zero
            df['Rentabilidad'] = df.apply(
                lambda row: row['Profit'] / row['Cumulative_Balance'] if row['Cumulative_Balance'] != 0 else 0,
                axis=1
            )
            # -----

            # First Summary: Group by 'Symbol' and 'G/P'
            grouped_symbol = df.loc[(df['side'].isin(['sell', 'buy'])) & (df['OrderStatus']=='Closed')] \
                        .groupby(['Symbol', 'G/P']).agg(
                Count_id=('OrderTicket', 'count'),
                Average_P_L=('Profit', 'mean'),
                Average_Duración=('Duración', 'mean'),
                Sum_P_L=('Profit', 'sum'),
                Rentabilidad=('Rentabilidad', 'mean')
            ).reset_index()

            # Exclude rows where Symbol is 'Unknown'
            grouped_symbol = grouped_symbol[grouped_symbol['Symbol'] != 'Unknown']

            # Calculate total count per symbol for percentage calculations
            total_counts_symbol = grouped_symbol.groupby('Symbol')['Count_id'].transform('sum')

            # Calculate % Rentabilidad and %
            grouped_symbol['% Rentabilidad'] = (grouped_symbol['Rentabilidad']) * 100
            grouped_symbol['%'] = (grouped_symbol['Count_id'] / total_counts_symbol) * 100
            grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Sum_P_L']

            # Replace NaN values with 0
            grouped_symbol['% Rentabilidad'] = grouped_symbol['% Rentabilidad'].fillna(0)
            grouped_symbol['%'] = grouped_symbol['%'].fillna(0)
            grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Beneficio_Esperado'].fillna(0)

            # Round numerical values for better readability
            grouped_symbol['Average_P_L'] = grouped_symbol['Average_P_L'].round(2)
            grouped_symbol['Average_Duración'] = grouped_symbol['Average_Duración'].round(2)
            grouped_symbol['Sum_P_L'] = grouped_symbol['Sum_P_L'].round(2)
            grouped_symbol['% Rentabilidad'] = grouped_symbol['% Rentabilidad'].round(2)
            grouped_symbol['%'] = grouped_symbol['%'].round(2)
            grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Beneficio_Esperado'].round(2)

            # Prepare summary table data for Symbol
            summary_table_symbol = grouped_symbol.to_dict(orient='records')

            # Calculate total result for Symbol
            total_count_symbol = grouped_symbol['Count_id'].sum()
            total_sum_p_l_symbol = grouped_symbol['Sum_P_L'].sum().round(2)
            total_beneficio_esperado_symbol = grouped_symbol['Beneficio_Esperado'].sum().round(2)

            total_result_symbol = {
                'Symbol': 'Total Result',
                'G/P': '',
                'Count_id': total_count_symbol,
                'Average_P_L': '',
                'Average_Duración': '',
                'Sum_P_L': total_sum_p_l_symbol,
                '% Rentabilidad': '',
                '%': '',
                'Beneficio_Esperado': total_beneficio_esperado_symbol
            }

            summary_table_symbol.append(total_result_symbol)

            # Second Summary: Group by 'side' and 'G/P'
            grouped_side = df.groupby(['side', 'G/P']).agg(
                Count_id=('OrderTicket', 'count'),
                Average_P_L=('Profit', 'mean'),
                Average_Duración=('Duración', 'mean'),
                Sum_P_L=('Profit', 'sum'),
                Rentabilidad=('Rentabilidad', 'mean')
            ).reset_index()

            # Exclude rows where side is 'Unknown'
            grouped_side = grouped_side[grouped_side['side'] != 'Unknown']

            # Calculate total count per side for percentage calculations
            total_counts_side = grouped_side.groupby('side')['Count_id'].transform('sum')

            # Calculate % Rentabilidad and %
            grouped_side['% Rentabilidad'] = (grouped_side['Rentabilidad']) * 100
            grouped_side['%'] = (grouped_side['Count_id'] / total_counts_side) * 100
            grouped_side['Beneficio_Esperado'] = grouped_side['Sum_P_L']

            # Replace NaN values with 0
            grouped_side['% Rentabilidad'] = grouped_side['% Rentabilidad'].fillna(0)
            grouped_side['%'] = grouped_side['%'].fillna(0)
            grouped_side['Beneficio_Esperado'] = grouped_side['Beneficio_Esperado'].fillna(0)

            # Round numerical values for better readability
            grouped_side['Average_P_L'] = grouped_side['Average_P_L'].round(2)
            grouped_side['Average_Duración'] = grouped_side['Average_Duración'].round(2)
            grouped_side['Sum_P_L'] = grouped_side['Sum_P_L'].round(2)
            grouped_side['% Rentabilidad'] = grouped_side['% Rentabilidad'].round(2)
            grouped_side['%'] = grouped_side['%'].round(2)
            grouped_side['Beneficio_Esperado'] = grouped_side['Beneficio_Esperado'].round(2)

            # Prepare summary table data for side
            summary_table_side = grouped_side.to_dict(orient='records')

            # Calculate total result for side
            total_count_side = grouped_side['Count_id'].sum()
            total_sum_p_l_side = grouped_side['Sum_P_L'].sum().round(2)
            total_beneficio_esperado_side = grouped_side['Beneficio_Esperado'].sum().round(2)

            total_result_side = {
                'side': 'Total Result',
                'G/P': '',
                'Count_id': total_count_side,
                'Average_P_L': '',
                'Average_Duración': '',
                'Sum_P_L': total_sum_p_l_side,
                '% Rentabilidad': '',
                '%': '',
                'Beneficio_Esperado': total_beneficio_esperado_side
            }

            summary_table_side.append(total_result_side)

            # Profit over time
            df['% Rentabilidad'] = (df['Rentabilidad']) * 100
            df_orders = df[df['side'].isin(['sell', 'buy'])].copy()

            if not df_orders.empty:
                # Extract date from OpenTime
                df_orders['OpenDate'] = df_orders['OpenTime'].dt.date

                # Group by 'OpenDate' and compute average of '% Rentabilidad'
                daily_rentabilidad = df_orders.groupby('OpenDate')['% Rentabilidad'].mean().reset_index()

                # Create a complete date range
                min_date = df_orders['OpenDate'].min()
                max_date = df_orders['OpenDate'].max()
                date_range = pd.date_range(start=min_date, end=max_date)
                all_dates_df = pd.DataFrame({'OpenDate': date_range.date})

                # Merge to include all dates
                daily_rentabilidad = pd.merge(all_dates_df, daily_rentabilidad, on='OpenDate', how='left')

                # Fill missing '% Rentabilidad' values
                daily_rentabilidad['% Rentabilidad'].fillna(method='ffill', inplace=True)
                daily_rentabilidad['% Rentabilidad'].fillna(0, inplace=True)

                # Prepare data for plotting
                dates = daily_rentabilidad['OpenDate'].astype(str).tolist()

                rentabilidades = daily_rentabilidad['% Rentabilidad'].tolist()
            else:
                dates = []
                rentabilidades = []
            # ------------------------



            # Calculate Daily Open Orders for Bar Plot
            df['OpenDate'] = df['OpenTime'].dt.date
            df['CloseDate'] = df['CloseTime_Adjusted'].dt.date
            min_date = df['OpenDate'].min()
            max_date = df['CloseDate'].max()
            all_dates = pd.date_range(start=min_date, end=max_date, freq='D').date
            open_orders_daily = []
            for current_date in all_dates:
                open_orders_count = df[
                    (df['OpenDate'] <= current_date) &
                    (df['CloseDate'] >= current_date)
                ].shape[0]
                open_orders_daily.append({'Date': current_date.strftime('%Y-%m-%d'), 'Open_Orders': open_orders_count})
            open_orders_daily_df = pd.DataFrame(open_orders_daily)
            open_dates = open_orders_daily_df['Date'].tolist()
            open_orders = open_orders_daily_df['Open_Orders'].tolist()

            flash(f'File "{selected_file}" processed successfully. Initial Balance: ${initial_balance:,.2f}')
        except Exception as e:
            flash(f'Error processing file "{selected_file}": {e}')
            # Assign default values in case of error
            rentabilidades = []
            dates = []
            rentabilidad_last_dates = []
            rentabilidad_last_values = []
            print(f'Error: {e}')
            traceback.print_exc()
    else:
        flash(f'File "{selected_file}" does not exist.')
        # Assign default values
        rentabilidades = []
        dates = []
        rentabilidad_last_dates = []
        rentabilidad_last_values = []

    return render_template('mam_summary.html',
                           uploaded_files=uploaded_files,
                           selected_file=selected_file,
                           summary_table_symbol=summary_table_symbol,
                           summary_table_side=summary_table_side,
                           initial_balance=initial_balance,
                           dates=json.dumps(dates),
                           rentabilidades=json.dumps(rentabilidades),
                           balances=json.dumps(balances),
                           open_dates=json.dumps(open_dates),
                           open_orders=json.dumps(open_orders),
                           rentabilidad_last_dates=json.dumps(rentabilidad_last_dates),
                           rentabilidad_last_values=json.dumps(rentabilidad_last_values),
                           magic_numbers=magic_numbers
                           )

@app.route('/summary', methods=['GET', 'POST'])
def summary():
    dates, balances, open_dates, open_orders = [], [], [], []

    uploaded_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            uploaded_files.append(filename)

    selected_file = None
    summary_table_symbol = None
    summary_table_side = None
    initial_balance = 100000.00  # Default initial balance

    # Mapping OrderType to side
    order_type_mapping = {
        1: 'buy',
        6: 'sell'
    }

    if request.method == 'POST':
        selected_file = request.form.get('csv_file')
        initial_balance_input = request.form.get('initial_balance')

        # Validate initial balance
        try:
            initial_balance = float(initial_balance_input)
            if initial_balance <= 0:
                flash('Initial balance must be a number greater than 0.')
                initial_balance = 100000.00  # Reset to default if invalid
        except (ValueError, TypeError):
            flash('Invalid initial balance. Please enter a valid number greater than 0.')
            initial_balance = 100000.00  # Reset to default if invalid

        if selected_file:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)

                    # Check required columns
                    required_columns = ['OrderTicket', 'OrderType', 'Symbol', 'Volume', 'OpenPrice',
                                        'OpenTime', 'ClosePrice', 'CloseTime', 'Profit']
                    if not all(col in df.columns for col in required_columns):
                        flash(f'File "{selected_file}" is missing required columns.')
                        return redirect(url_for('summary'))

                    # Handle missing Symbol entries by filling with 'Unknown'
                    df['Symbol'] = df['Symbol'].fillna('Unknown')

                    # Compute 'G/P' based on 'Profit'
                    df['G/P'] = df['Profit'].apply(lambda x: 'G' if x >= 0 else 'P')

                    # Map 'OrderType' to 'side'
                    df['side'] = df['OrderType'].map(order_type_mapping).fillna('Unknown')

                    # Convert 'OpenTime' and 'CloseTime' to datetime
                    df['OpenTime'] = pd.to_datetime(df['OpenTime'], format='%Y.%m.%d %H:%M')
                    df['CloseTime'] = pd.to_datetime(df['CloseTime'], format='%Y.%m.%d %H:%M')

                    # Calculate 'Duración' in minutes
                    df['Duración'] = (df['CloseTime'] - df['OpenTime']).dt.total_seconds() / 60

                    # First Summary: Group by 'Symbol' and 'G/P'
                    grouped_symbol = df.groupby(['Symbol', 'G/P']).agg(
                        Count_id=('OrderTicket', 'count'),
                        Average_P_L=('Profit', 'mean'),
                        Average_Duración=('Duración', 'mean'),
                        Sum_P_L=('Profit', 'sum')
                    ).reset_index()

                    # Exclude rows where Symbol is 'Unknown'
                    grouped_symbol = grouped_symbol[grouped_symbol['Symbol'] != 'Unknown']

                    # Calculate total count per symbol for percentage calculations
                    total_counts_symbol = grouped_symbol.groupby('Symbol')['Count_id'].transform('sum')

                    # Calculate % Rentabilidad and %
                    grouped_symbol['% Rentabilidad'] = (grouped_symbol['Count_id'] * grouped_symbol['Average_P_L']) / initial_balance * 100
                    grouped_symbol['%'] = (grouped_symbol['Count_id'] / total_counts_symbol) * 100
                    grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Count_id'] * grouped_symbol['Average_P_L']

                    # Replace NaN values with 0
                    grouped_symbol['% Rentabilidad'] = grouped_symbol['% Rentabilidad'].fillna(0)
                    grouped_symbol['%'] = grouped_symbol['%'].fillna(0)
                    grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Beneficio_Esperado'].fillna(0)

                    # Round numerical values for better readability
                    grouped_symbol['Average_P_L'] = grouped_symbol['Average_P_L'].round(2)
                    grouped_symbol['Average_Duración'] = grouped_symbol['Average_Duración'].round(2)
                    grouped_symbol['Sum_P_L'] = grouped_symbol['Sum_P_L'].round(2)
                    grouped_symbol['% Rentabilidad'] = grouped_symbol['% Rentabilidad'].round(2)
                    grouped_symbol['%'] = grouped_symbol['%'].round(2)
                    grouped_symbol['Beneficio_Esperado'] = grouped_symbol['Beneficio_Esperado'].round(2)

                    # Prepare summary table data for Symbol
                    summary_table_symbol = grouped_symbol.to_dict(orient='records')

                    # Calculate total result for Symbol
                    total_count_symbol = grouped_symbol['Count_id'].sum()
                    total_avg_p_l_symbol = grouped_symbol['Average_P_L'].mean().round(2)
                    total_avg_duracion_symbol = grouped_symbol['Average_Duración'].mean().round(2)
                    total_sum_p_l_symbol = grouped_symbol['Sum_P_L'].sum().round(2)
                    total_beneficio_esperado_symbol = grouped_symbol['Beneficio_Esperado'].sum().round(2)

                    total_result_symbol = {
                        'Symbol': 'Total Result',
                        'G/P': '',
                        'Count_id': total_count_symbol,
                        'Average_P_L': '',
                        'Average_Duración': '',
                        'Sum_P_L': '',
                        '% Rentabilidad': '',
                        '%': '',
                        'Beneficio_Esperado': total_beneficio_esperado_symbol
                    }

                    summary_table_symbol.append(total_result_symbol)

                    # Second Summary: Group by 'side' and 'G/P'
                    grouped_side = df.groupby(['side', 'G/P']).agg(
                        Count_id=('OrderTicket', 'count'),
                        Average_P_L=('Profit', 'mean'),
                        Average_Duración=('Duración', 'mean'),
                        Sum_P_L=('Profit', 'sum')
                    ).reset_index()

                    # Exclude rows where side is 'Unknown'
                    grouped_side = grouped_side[grouped_side['side'] != 'Unknown']

                    # Calculate total count per side for percentage calculations
                    total_counts_side = grouped_side.groupby('side')['Count_id'].transform('sum')

                    # Calculate % Rentabilidad and %
                    grouped_side['% Rentabilidad'] = (grouped_side['Count_id'] * grouped_side['Average_P_L']) / initial_balance * 100
                    grouped_side['%'] = (grouped_side['Count_id'] / total_counts_side) * 100
                    grouped_side['Beneficio_Esperado'] = grouped_side['Count_id'] * grouped_side['Average_P_L']

                    # Replace NaN values with 0
                    grouped_side['% Rentabilidad'] = grouped_side['% Rentabilidad'].fillna(0)
                    grouped_side['%'] = grouped_side['%'].fillna(0)
                    grouped_side['Beneficio_Esperado'] = grouped_side['Beneficio_Esperado'].fillna(0)

                    # Round numerical values for better readability
                    grouped_side['Average_P_L'] = grouped_side['Average_P_L'].round(2)
                    grouped_side['Average_Duración'] = grouped_side['Average_Duración'].round(2)
                    grouped_side['Sum_P_L'] = grouped_side['Sum_P_L'].round(2)
                    grouped_side['% Rentabilidad'] = grouped_side['% Rentabilidad'].round(2)
                    grouped_side['%'] = grouped_side['%'].round(2)
                    grouped_side['Beneficio_Esperado'] = grouped_side['Beneficio_Esperado'].round(2)

                    # Prepare summary table data for side
                    summary_table_side = grouped_side.to_dict(orient='records')

                    # Calculate total result for side
                    total_count_side = grouped_side['Count_id'].sum()
                    total_avg_p_l_side = grouped_side['Average_P_L'].mean().round(2)
                    total_avg_duracion_side = grouped_side['Average_Duración'].mean().round(2)
                    total_sum_p_l_side = grouped_side['Sum_P_L'].sum().round(2)
                    total_beneficio_esperado_side = grouped_side['Beneficio_Esperado'].sum().round(2)

                    total_result_side = {
                        'side': 'Total Result',
                        'G/P': '',
                        'Count_id': total_count_side,
                        'Average_P_L': '',
                        'Average_Duración': '',
                        'Sum_P_L': '',
                        '% Rentabilidad': '',
                        '%': '',
                        'Beneficio_Esperado': total_beneficio_esperado_side
                    }

                    summary_table_side.append(total_result_side)

                    # Profit over time ------------------------------------------
                    df_sorted = df.sort_values(by='CloseTime')
                    df_sorted['CloseDate'] = df_sorted['CloseTime'].dt.date
                    daily_profit = df_sorted.groupby('CloseDate')['Profit'].sum().reset_index()
                    daily_profit['Cumulative_Profit'] = daily_profit['Profit'].cumsum()
                    daily_profit['Balance'] = initial_balance + daily_profit['Cumulative_Profit']
                    plot_data = daily_profit[['CloseDate', 'Balance']].copy()
                    plot_data['CloseDate'] = plot_data['CloseDate'].astype(str)
                    dates = plot_data['CloseDate'].tolist()
                    balances = plot_data['Balance'].tolist()

                    # New Code: Calculate Daily Open Orders for Bar Plot ------------------------
                    df_sorted['CloseDate_only'] = df_sorted['CloseTime'].dt.date
                    df_sorted['OpenDate_only'] = df_sorted['OpenTime'].dt.date
                    all_dates = pd.date_range(start=df_sorted['OpenDate_only'].min(),
                                              end=df_sorted['CloseDate'].max(),
                                              freq='D').date
                    open_orders_daily = []
                    for current_date in all_dates:
                        open_orders = df_sorted[
                            (df_sorted['OpenDate_only'] <= current_date) &
                            ((df_sorted['CloseDate_only'] > current_date) | (df_sorted['CloseDate_only'].isna()))
                        ]
                        open_orders_daily.append({'Date': current_date.strftime('%Y-%m-%d'), 'Open_Orders': open_orders.shape[0]})
                    open_orders_daily_df = pd.DataFrame(open_orders_daily)
                    open_dates = open_orders_daily_df['Date'].tolist()
                    open_orders = open_orders_daily_df['Open_Orders'].tolist()


                    flash(f'File "{selected_file}" processed successfully. Initial Balance: ${initial_balance:,.2f}')
                except Exception as e:
                    flash(f'Error processing file "{selected_file}": {e}')
            else:
                flash(f'File "{selected_file}" does not exist.')

    return render_template('summary.html',
                           uploaded_files=uploaded_files,
                           selected_file=selected_file,
                           summary_table_symbol=summary_table_symbol,
                           summary_table_side=summary_table_side,
                           initial_balance=initial_balance,
                           dates=json.dumps(dates),
                           balances=json.dumps(balances),
                           open_dates=json.dumps(open_dates),
                           open_orders=json.dumps(open_orders)
                       )


@app.route('/summary2', methods=['GET', 'POST'])
def summary2():
    uploaded_files = []
    for filename in os.listdir(app.config['UPLOAD_FOLDER']):
        if allowed_file(filename):
            uploaded_files.append(filename)

    summary_data = []
    initial_balance = 100000.00  # Default initial balance
    aggregated_metrics = {}
    corr_matrix_list = []

    if request.method == 'POST':
        initial_balance_input = request.form.get('initial_balance')

        try:
            initial_balance = float(initial_balance_input)
            if initial_balance <= 0:
                flash('Initial balance must be a number greater than 0.')
                initial_balance = 100000.00
        except (ValueError, TypeError):
            flash('Invalid initial balance. Please enter a valid number greater than 0.')
            initial_balance = 100000.00

        for selected_file in uploaded_files:
            file_path = os.path.join(app.config['UPLOAD_FOLDER'], selected_file)
            if os.path.exists(file_path):
                try:
                    df = pd.read_csv(file_path)

                    required_columns = ['OrderTicket', 'OrderType', 'Symbol', 'Volume', 'OpenPrice',
                                        'OpenTime', 'ClosePrice', 'CloseTime', 'Profit']
                    if not all(col in df.columns for col in required_columns):
                        flash(f'File "{selected_file}" is missing required columns.')
                        continue

                    df['Symbol'] = df['Symbol'].fillna('Unknown')
                    df['G/P'] = df['Profit'].apply(lambda x: 'G' if x >= 0 else 'P')
                    order_type_mapping = {
                        1: 'buy',
                        6: 'sell'
                    }
                    df['side'] = df['OrderType'].map(order_type_mapping).fillna('Unknown')
                    df['OpenTime'] = pd.to_datetime(df['OpenTime'], format='%Y.%m.%d %H:%M')
                    df['CloseTime'] = pd.to_datetime(df['CloseTime'], format='%Y.%m.%d %H:%M')
                    df['Duración'] = (df['CloseTime'] - df['OpenTime']).dt.total_seconds() / 60

                    ID = selected_file
                    operaciones = len(df)
                    p_l_promedio = df['Profit'].mean()
                    duracion_media = df['Duración'].mean()
                    rentabilidad = (df['Profit'].sum() / initial_balance) * 100

                    max_p_l_largos = df[df['side'] == 'buy']['Profit'].max()
                    if pd.isna(max_p_l_largos):
                        max_p_l_largos = 0

                    min_p_l_largos = df[df['side'] == 'buy']['Profit'].min()
                    if pd.isna(min_p_l_largos):
                        min_p_l_largos = 0

                    max_p_l_cortos = df[df['side'] == 'sell']['Profit'].max()
                    if pd.isna(max_p_l_cortos):
                        max_p_l_cortos = 0

                    min_p_l_cortos = df[df['side'] == 'sell']['Profit'].min()
                    if pd.isna(min_p_l_cortos):
                        min_p_l_cortos = 0

                    total_trades = len(df)
                    ganadoras = len(df[df['Profit'] > 0])
                    perdedoras = len(df[df['Profit'] < 0])
                    porcentaje_ganadoras = (ganadoras / total_trades) * 100 if total_trades > 0 else 0
                    porcentaje_perdedoras = (perdedoras / total_trades) * 100 if total_trades > 0 else 0

                    p_l_prom_ganadoras = df[df['Profit'] > 0]['Profit'].mean()
                    p_l_prom_ganadoras = p_l_prom_ganadoras if not pd.isna(p_l_prom_ganadoras) else 0

                    p_l_prom_perdedoras = df[df['Profit'] < 0]['Profit'].mean()
                    p_l_prom_perdedoras = p_l_prom_perdedoras if not pd.isna(p_l_prom_perdedoras) else 0

                    duracion_media_ganadoras = df[df['Profit'] > 0]['Duración'].mean()
                    duracion_media_ganadoras = duracion_media_ganadoras if not pd.isna(duracion_media_ganadoras) else 0

                    duracion_media_perdedoras = df[df['Profit'] < 0]['Duración'].mean()
                    duracion_media_perdedoras = duracion_media_perdedoras if not pd.isna(duracion_media_perdedoras) else 0

                    summary_data.append({
                        'ID': ID,
                        'Operaciones': operaciones,
                        'P_L_Promedio': round(p_l_promedio, 2),
                        'Duracion_Media': round(duracion_media, 2),
                        'Rentabilidad': round(rentabilidad, 2),
                        'Max_P_L_Largos': round(max_p_l_largos, 2),
                        'Min_P_L_Largos': round(min_p_l_largos, 2),
                        'Max_P_L_Cortos': round(max_p_l_cortos, 2),
                        'Min_P_L_Cortos': round(min_p_l_cortos, 2),
                        'Porcentaje_Ganadoras': round(porcentaje_ganadoras, 2),
                        'Porcentaje_Perdedoras': round(porcentaje_perdedoras, 2),
                        'P_L_Prom_Ganadoras': round(p_l_prom_ganadoras, 2),
                        'P_L_Prom_Perdedoras': round(p_l_prom_perdedoras, 2),
                        'Duracion_Media_Ganadoras': round(duracion_media_ganadoras, 2),
                        'Duracion_Media_Perdedoras': round(duracion_media_perdedoras, 2)
                    })
                except Exception as e:
                    flash(f'Error processing file "{selected_file}": {e}')
            else:
                flash(f'File "{selected_file}" does not exist.')

        if summary_data:
            df_summary = pd.DataFrame(summary_data)
            numeric_cols = ['Operaciones', 'P_L_Promedio', 'Duracion_Media', 'Rentabilidad',
                           'Max_P_L_Largos', 'Min_P_L_Largos', 'Max_P_L_Cortos', 'Min_P_L_Cortos',
                           'Porcentaje_Ganadoras', 'Porcentaje_Perdedoras',
                           'P_L_Prom_Ganadoras', 'P_L_Prom_Perdedoras',
                           'Duracion_Media_Ganadoras', 'Duracion_Media_Perdedoras']
            promedio = df_summary[numeric_cols].mean().round(2).to_dict()
            desv_t = df_summary[numeric_cols].std().round(2).to_dict()
            cv = (df_summary[numeric_cols].std() / df_summary[numeric_cols].mean()).round(3).to_dict()

            aggregated_metrics = {
                'Promedio': promedio,
                'Desv_T': desv_t,
                'CV': cv
            }

            corr_matrix = df_summary[numeric_cols].corr().round(3).to_dict()
            corr_matrix_list = []
            for row in numeric_cols:
                row_dict = {'Metric': row}
                for col in numeric_cols:
                    row_dict[col] = corr_matrix[row][col]
                corr_matrix_list.append(row_dict)

            return render_template('summary2.html',
                                   uploaded_files=uploaded_files,
                                   summary_data=summary_data,
                                   aggregated_metrics=aggregated_metrics,
                                   corr_matrix=corr_matrix_list,
                                   initial_balance=initial_balance)

    return render_template('summary2.html',
                           uploaded_files=uploaded_files,
                           summary_data=summary_data,
                           aggregated_metrics=aggregated_metrics,
                           corr_matrix=corr_matrix_list,
                           initial_balance=initial_balance)

if __name__ == "__main__":
    app.run(debug=True)
