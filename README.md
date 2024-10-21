# CSV Orders Processing App

This Flask web application allows users to upload and process CSV files containing order data. It calculates various metrics, generates summaries based on trading performance, and provides data visualizations.

## Features
- Upload CSV files containing order data.
- Process and summarize metrics such as average profit, total trades, total profit, winning and losing trades.
- Visualize profit over time and open orders daily.
- Group and summarize data by trading symbols and sides (buy/sell).
- Supports calculation of expected profitability and other key metrics.

## Prerequisites
- Python 3.x
- Flask
- Pandas
- Werkzeug

## Installation

1. Clone the repository:
    ```bash
    git clone <repo-url>
    cd <repo-directory>
    ```

2. Install dependencies:
    ```bash
    pip install -r req.txt
    ```

3. Run the Flask app:
    ```bash
    python app.py
    ```

4. Navigate to `http://127.0.0.1:5000/` in your browser to access the app.

## Folder Structure
- **uploads/**: Directory where uploaded CSV files are stored.
- **results_summary.csv**: Summary file that tracks key metrics across multiple uploads.

## File Upload Format
Uploaded CSV files must contain the following columns:
- `OrderTicket`
- `OrderType` (1 for buy, 6 for sell)
- `Symbol`
- `Volume`
- `OpenPrice`
- `OpenTime` (in the format `YYYY.MM.DD HH:MM`)
- `ClosePrice`
- `CloseTime` (in the format `YYYY.MM.DD HH:MM`)
- `Profit`

## Configuration
- Default initial balance: `$100,000.00`
- Modify the `initial_balance` in the `/summary` and `/summary2` routes as needed.

## License
This project is licensed under the MIT License.

