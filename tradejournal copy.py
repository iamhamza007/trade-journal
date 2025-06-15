import streamlit as st
from fpdf import FPDF
from PIL import Image
import os
import json
import datetime
import streamlit_authenticator as stauth

# --- 1. HARDCODED HASHED PASSWORDS (DON'T HASH AT RUNTIME) ---
# Generate these securely using: stauth.Hasher(["your_password"]).generate()
# You only do this ONCE and paste the output here. These are example hashes:
hashed_passwords = [
    '$2b$12$3m5KcXSBf6mSBPeS97NwrOd7gX8NKTj7Ao8ApwFQ7ROHcDh2e7xMK',  # 1234
    '$2b$12$nFJJeS02LvhysKW6ZKvneOrEQuvhYAmMKdZh/mCT2aCE17M4T3Mhe',  # 5678
    '$2b$12$MXnbwQuGnTLgPVltjk7H0OWUJRGV1LKR4DEfKa3OULFDG4PtFuVke',  # abcd
    '$2b$12$Y/urYvFyb0P6GV.2pRfsUeknQyJv9yyNFuQG9AtbghG7zNSEVYUXi',  # xyz123
]

# --- 2. USER INFO ---
users = {
    "usernames": {
        "hamza": {
            "name": "Hamza Feroz",
            "password": hashed_passwords[0]
        },
        "ali": {
            "name": "Ali Raza",
            "password": hashed_passwords[1]
        },
        "sara": {
            "name": "Sara Khan",
            "password": hashed_passwords[2]
        },
        "john": {
            "name": "John Doe",
            "password": hashed_passwords[3]
        },
    }
}

# --- 3. PAGE CONFIG ---
st.set_page_config(page_title="Trade Journal", layout="centered")

# --- 4. AUTHENTICATION SETUP ---
authenticator = stauth.Authenticate(
    users["usernames"], "trade_journal_app", "abcdef", cookie_expiry_days=30
)

name, auth_status, username = authenticator.login("Login", "main")

if auth_status is False:
    st.error("Invalid username or password")
    st.stop()
elif auth_status is None:
    st.warning("Please enter your credentials")
    st.stop()

authenticator.logout("Logout", "sidebar")
st.sidebar.success(f"Logged in as {name}")

# --- 5. USER FOLDER SETUP ---
user_pdf_folder = os.path.join("output_pdfs", username)
user_data_folder = os.path.join("trade_data", username)
os.makedirs(user_pdf_folder, exist_ok=True)
os.makedirs(user_data_folder, exist_ok=True)
os.makedirs("logos", exist_ok=True)

# --- 6. SYMBOL MANAGEMENT ---
def load_symbols():
    try:
        with open("symbols.json", "r") as f:
            return json.load(f)
    except FileNotFoundError:
        return ["XAUUSD", "BTCUSD", "EURUSD", "USDJPY"]

def save_symbols(symbols):
    with open("symbols.json", "w") as f:
        json.dump(symbols, f)

symbols = load_symbols()

# --- 7. SIDEBAR SYMBOL MANAGEMENT ---
with st.sidebar:
    st.header("🔧 Manage Symbols")
    new_symbol = st.text_input("Add new symbol")
    if st.button("➕ Add Symbol") and new_symbol:
        if new_symbol not in symbols:
            symbols.append(new_symbol)
            save_symbols(symbols)
            st.success(f"{new_symbol} added!")
    if st.button("💾 Save Symbol List"):
        save_symbols(symbols)
    if st.button("♻️ Clear All Symbols"):
        symbols = []
        save_symbols(symbols)
        st.warning("All symbols removed.")

# --- 8. TRADE FORM ---
st.title("📘 Trade Journal Creator")
st.subheader("📝 Enter Trade Details")

with st.form("trade_form"):
    symbol = st.selectbox("Symbol/Pair", symbols)
    position = st.selectbox("Position", ["Long", "Short"])
    entry = st.number_input("Entry Price", format="%.2f")
    exit = st.number_input("Exit Price", format="%.2f")
    lot_size = st.number_input("Lot Size", format="%.2f")
    commission = st.number_input("Commission ($)", format="%.2f")
    trade_number = st.text_input("Trade Number")
    position_id = st.text_input("Position ID")
    pdf_name = st.text_input("Custom PDF Name (optional)")
    notes = st.text_area("Notes")
    rating = st.slider("Trade Rating", 1, 5, 3)
    screenshot = st.file_uploader("📸 Upload Screenshot", type=["png", "jpg", "jpeg"])
    combine = st.checkbox("📂 Add to Combined Journal")

    st.markdown("### Entry Time")
    entry_time = datetime.datetime(
        st.selectbox("Day", list(range(1, 32)), key="ed"),
        st.selectbox("Month", list(range(1, 13)), key="em"),
        st.selectbox("Year", list(range(2025, 2101)), key="ey"),
        st.selectbox("Hour", list(range(0, 24)), key="eh"),
        st.selectbox("Minute", list(range(0, 60)), key="emin"),
        st.selectbox("Second", list(range(0, 60)), key="esec"),
    )

    st.markdown("### Exit Time")
    exit_time = datetime.datetime(
        st.selectbox("Day", list(range(1, 32)), key="xd"),
        st.selectbox("Month", list(range(1, 13)), key="xm"),
        st.selectbox("Year", list(range(2025, 2101)), key="xy"),
        st.selectbox("Hour", list(range(0, 24)), key="xh"),
        st.selectbox("Minute", list(range(0, 60)), key="xmin"),
        st.selectbox("Second", list(range(0, 60)), key="xsec"),
    )

    duration = exit_time - entry_time
    duration_str = f"{duration.days}d {duration.seconds//3600}h {(duration.seconds//60)%60}m"

    multipliers = {
        "XAUUSD": 100,
        "BTCUSD": 1,
        "EURUSD": 100000,
        "USDJPY": 100000
    }
    multiplier = multipliers.get(symbol.upper(), 1)
    pos_size = lot_size * multiplier

    pnl = (exit - entry if position == "Long" else entry - exit) * pos_size - commission
    pnl_color = "green" if pnl >= 0 else "red"
    st.markdown(f"### 💰 Estimated PnL: <span style='color:{pnl_color}; font-size:20px;'>${pnl:.2f}</span>", unsafe_allow_html=True)

    submitted = st.form_submit_button("✅ Save Trade")

# --- 9. SAVE TRADE & GENERATE PDF ---
if submitted:
    timestamp = datetime.datetime.now().strftime("%Y%m%d%H%M%S")
    screenshot_file = f"screenshot_{timestamp}.png" if screenshot else None

    trade = {
        "symbol": symbol,
        "position": position,
        "entry": entry,
        "exit": exit,
        "lot_size": lot_size,
        "commission": commission,
        "pnl": round(pnl, 2),
        "position_id": f"#{position_id}",
        "rating": rating,
        "entry_time": entry_time.strftime("%d/%m/%Y %H:%M:%S"),
        "exit_time": exit_time.strftime("%d/%m/%Y %H:%M:%S"),
        "duration": duration_str,
        "trade_number": trade_number,
        "notes": notes,
        "screenshot": screenshot_file,
        "time": timestamp
    }

    if screenshot:
        img = Image.open(screenshot)
        img.save(os.path.join(user_data_folder, screenshot_file))

    if combine:
        with open(os.path.join(user_data_folder, f"trade_{timestamp}.json"), "w") as f:
            json.dump(trade, f)
        st.success("✅ Trade added to combined journal")
    else:
        pdf = FPDF()
        pdf.add_page()
        pdf.set_font("Arial", size=12)

        logo_path = f"logos/{symbol}.png"
        if os.path.exists(logo_path):
            pdf.image(logo_path, x=85, y=10, w=30)
        pdf.ln(45)

        pdf.set_font("Arial", 'B', size=14)
        pdf.cell(200, 10, txt=f"Trade Journal - {symbol}", ln=True, align='C')
        pdf.ln(10)
        pdf.set_font("Arial", size=12)

        for key in ["symbol", "position", "entry", "exit", "lot_size", "commission"]:
            pdf.cell(200, 10, txt=f"{key.replace('_', ' ').capitalize()}: {trade[key]}", ln=True)

        pdf.set_text_color(0, 128, 0) if pnl >= 0 else pdf.set_text_color(255, 0, 0)
        pdf.set_font("Arial", style='U', size=14)
        pdf.cell(200, 10, txt=f"PnL: ${pnl:.2f}", ln=True)
        pdf.set_text_color(0)
        pdf.set_font("Arial", size=12)

        pdf.cell(200, 10, txt=f"Screenshot: {trade['screenshot'] or 'None'}", ln=True)
        pdf.cell(200, 10, txt=f"Entry time: {trade['entry_time']}", ln=True)
        pdf.cell(200, 10, txt=f"Exit time: {trade['exit_time']}", ln=True)
        pdf.cell(200, 10, txt=f"Duration: {trade['duration']}", ln=True)
        pdf.cell(200, 10, txt=f"Trade number: {trade['trade_number']}", ln=True)
        pdf.set_text_color(0, 0, 255)
        pdf.cell(200, 10, txt=f"Position ID: {trade['position_id']}", ln=True)
        pdf.set_text_color(0)
        pdf.cell(200, 10, txt=f"Rating: {trade['rating']}/5", ln=True)

        if trade['screenshot']:
            pdf.image(os.path.join(user_data_folder, trade['screenshot']), x=10, w=100)

        pdf.ln(5)
        pdf.multi_cell(0, 10, txt=f"Notes: {trade['notes']}")

        filename = os.path.join(user_pdf_folder, f"{pdf_name if pdf_name else f'{symbol}_{timestamp}'}.pdf")
        pdf.output(filename)
        st.success(f"📄 PDF saved: `{filename}`")
