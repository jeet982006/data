from flask import (
    Flask,
    render_template,
    request,
    redirect,
    url_for,
    session,
    Response,
    jsonify
)

import sqlite3
import io
import re
import json
import secrets
from datetime import datetime

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import (
    SimpleDocTemplate,
    Table,
    TableStyle,
    Paragraph,
    Spacer,
    PageBreak
)


# =========================================================
# APP
# =========================================================

app = Flask(__name__)

app.secret_key = "business_website_secret_key_2026"


# =========================================================
# LOGIN
# =========================================================

USERNAME = "sp"
PASSWORD = "SPPB2004"


# =========================================================
# DATABASE
# =========================================================

DATABASE = "business.db"


def get_db():

    conn = sqlite3.connect(DATABASE)

    conn.row_factory = sqlite3.Row

    return conn


# =========================================================
# FINANCIAL YEAR HELPERS
# =========================================================

def get_current_financial_year():

    today = datetime.today()

    if today.month >= 4:

        start_year = today.year

    else:

        start_year = today.year - 1

    return (
        f"{start_year}-"
        f"{str(start_year + 1)[-2:]}"
    )


def get_financial_year_range(financial_year):

    match = re.fullmatch(
        r"(\d{4})-(\d{2})",
        financial_year
    )

    if not match:

        raise ValueError(
            "Invalid financial year."
        )

    start_year = int(
        match.group(1)
    )

    end_two = int(
        match.group(2)
    )

    expected_end = (
        (start_year + 1) % 100
    )

    if end_two != expected_end:

        raise ValueError(
            "Invalid financial year."
        )

    return (
        f"{start_year:04d}-04-01",
        f"{start_year + 1:04d}-03-31"
    )


def get_previous_financial_year(
    financial_year
):

    start_year = int(
        financial_year[:4]
    )

    previous_year = (
        start_year - 1
    )

    return (
        f"{previous_year}-"
        f"{str(previous_year + 1)[-2:]}"
    )


def normalize_financial_year(
    financial_year
):
    """
    Normalize FY input to the internal YYYY-YY format.
    Accepts:
      2027-28
      01/04/2027 - 31/03/2028
    """
    value = (financial_year or "").strip()

    label_match = re.fullmatch(
        r"(\d{2})/(\d{2})/(\d{4})\s*-\s*(\d{2})/(\d{2})/(\d{4})",
        value
    )

    if label_match:
        start_day, start_month, start_year, end_day, end_month, end_year = label_match.groups()

        if (
            start_day == "01"
            and start_month == "04"
            and end_day == "31"
            and end_month == "03"
            and int(end_year) == int(start_year) + 1
        ):
            value = (
                f"{start_year}-{str(int(start_year) + 1)[-2:]}"
            )

    get_financial_year_range(value)
    return value


def financial_year_to_label(
    financial_year
):

    try:

        start_year = int(
            financial_year[:4]
        )

        return (
            f"01/04/{start_year} - "
            f"31/03/{start_year + 1}"
        )

    except Exception:

        return financial_year


app.add_template_global(
    financial_year_to_label,
    "financial_year_to_label"
)


# =========================================================
# DATABASE INITIALIZATION
# =========================================================

def init_db():

    conn = get_db()

    # -----------------------------------------------------
    # BUSINESS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS businesses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            name TEXT NOT NULL UNIQUE,

            is_deleted INTEGER NOT NULL DEFAULT 0

        )
    """)

    # Upgrade old databases which do not have is_deleted.
    business_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(businesses)"
        ).fetchall()
    ]

    if "is_deleted" not in business_columns:
        conn.execute("""
            ALTER TABLE businesses
            ADD COLUMN is_deleted INTEGER NOT NULL DEFAULT 0
        """)


    # -----------------------------------------------------
    # BILL ENTRIES
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS entries (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            business_id INTEGER NOT NULL,

            entry_date TEXT NOT NULL,

            bill_amount REAL NOT NULL DEFAULT 0,

            FOREIGN KEY (business_id)
            REFERENCES businesses(id)

        )
    """)


    # -----------------------------------------------------
    # RECEIVED ENTRIES
    # -----------------------------------------------------

    conn.execute(
    """
    CREATE TABLE IF NOT EXISTS received_entries (
        id INTEGER PRIMARY KEY AUTOINCREMENT,
        business_id INTEGER NOT NULL,
        received_date TEXT NOT NULL,
        amount_received REAL NOT NULL DEFAULT 0,
        note TEXT,
        FOREIGN KEY (business_id) REFERENCES businesses(id)
    )
"""
)

    # Ensure note column exists if table was created earlier without it
    received_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(received_entries)"
        ).fetchall()
    ]
    if "note" not in received_columns:
        conn.execute("""
            ALTER TABLE received_entries
            ADD COLUMN note TEXT
        """)


    # -----------------------------------------------------
    # FINANCIAL YEARS
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS financial_years (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            financial_year TEXT NOT NULL UNIQUE,

            created_at DATETIME DEFAULT CURRENT_TIMESTAMP

        )
    """)

    # Upgrade financial_years table if missing created_at column
    fy_columns = [
        row["name"]
        for row in conn.execute(
            "PRAGMA table_info(financial_years)"
        ).fetchall()
    ]

    if "created_at" not in fy_columns:
        conn.execute("""
            ALTER TABLE financial_years
            ADD COLUMN created_at DATETIME DEFAULT CURRENT_TIMESTAMP
        """)


    # -----------------------------------------------------
    # BUSINESS YEAR DATA
    # -----------------------------------------------------

    conn.execute("""
        CREATE TABLE IF NOT EXISTS business_years (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            business_id INTEGER NOT NULL,

            financial_year TEXT NOT NULL,

            close_amount REAL NOT NULL DEFAULT 0,

            UNIQUE(
                business_id,
                financial_year
            ),

            FOREIGN KEY (business_id)
            REFERENCES businesses(id)

        )
    """)


    # -----------------------------------------------------
    # OLD DATABASE:
    # If entries still contains amount_received,
    # migrate those values once.
    # -----------------------------------------------------

    entry_columns = [

        row["name"]

        for row in conn.execute(
            "PRAGMA table_info(entries)"
        ).fetchall()

    ]


    if "amount_received" in entry_columns:

        conn.execute("""
            CREATE TABLE IF NOT EXISTS system_settings (

                key TEXT PRIMARY KEY,

                value TEXT

            )
        """)


        migration_done = conn.execute("""
            SELECT value
            FROM system_settings
            WHERE key = 'old_received_migration_done'
        """).fetchone()


        if not migration_done:

            old_rows = conn.execute("""
                SELECT

                    business_id,

                    entry_date,

                    amount_received

                FROM entries

                WHERE amount_received > 0

                ORDER BY id ASC

            """).fetchall()


            for row in old_rows:

                conn.execute("""
                    INSERT INTO received_entries
                    (
                        business_id,
                        received_date,
                        amount_received
                    )

                    VALUES (?, ?, ?)

                """, (
                    row["business_id"],
                    row["entry_date"],
                    row["amount_received"]
                ))


            conn.execute("""
                INSERT OR REPLACE INTO
                system_settings
                (key, value)

                VALUES
                (
                    'old_received_migration_done',
                    '1'
                )
            """)


    # -----------------------------------------------------
    # CURRENT YEAR ONLY BY DEFAULT
    # -----------------------------------------------------

    current_year = (
        get_current_financial_year()
    )


    conn.execute("""
        INSERT OR IGNORE INTO
        financial_years
        (financial_year, created_at)

        VALUES (?, CURRENT_TIMESTAMP)

    """, (
        current_year,
    ))


    conn.commit()
    conn.close()

    ensure_recovery_tables()


# =========================================================
# DATE HELPERS
# =========================================================

def normalize_date(date_text):

    if not date_text:

        return None


    try:

        date_obj = datetime.strptime(
            date_text.strip(),
            "%d/%m/%Y"
        )

        return date_obj.strftime(
            "%Y-%m-%d"
        )

    except (
        ValueError,
        TypeError
    ):

        return None


@app.template_filter("dmy")
def format_date_dmy(value):

    if not value:

        return ""


    try:

        date_obj = datetime.strptime(
            value,
            "%Y-%m-%d"
        )

        return date_obj.strftime(
            "%d/%m/%Y"
        )

    except (
        ValueError,
        TypeError
    ):

        return value


# =========================================================
# INR
# =========================================================

@app.template_filter("inr")
def format_inr(value):

    try:

        number = float(
            value or 0
        )

    except (
        ValueError,
        TypeError
    ):

        number = 0.0


    formatted = f"{number:.2f}"

    integer_part, decimal_part = (
        formatted.split(".")
    )


    negative = False


    if integer_part.startswith("-"):

        negative = True

        integer_part = integer_part[1:]


    if len(integer_part) <= 3:

        result = integer_part

    else:

        last_three = integer_part[-3:]

        remaining = integer_part[:-3]

        groups = []


        while len(remaining) > 2:

            groups.insert(
                0,
                remaining[-2:]
            )

            remaining = remaining[:-2]


        if remaining:

            groups.insert(
                0,
                remaining
            )


        result = ",".join(
            groups + [last_three]
        )


    if negative:

        result = "-" + result


    return (
        f"₹ {result}.{decimal_part}"
    )


# =========================================================
# GET ALL YEARS
# =========================================================

def get_financial_years():

    current_year = (
        get_current_financial_year()
    )

    conn = get_db()

    rows = conn.execute("""
        SELECT financial_year

        FROM financial_years

        ORDER BY financial_year DESC

    """).fetchall()

    conn.close()


    years = [
        row["financial_year"]
        for row in rows
    ]


    if current_year not in years:

        years.insert(
            0,
            current_year
        )


    return years


# =========================================================
# ENSURE BUSINESS YEAR
# =========================================================

def ensure_business_year(
    business_id,
    financial_year
):

    conn = get_db()


    existing = conn.execute("""
        SELECT
            close_amount

        FROM business_years

        WHERE

            business_id = ?

            AND financial_year = ?

    """, (
        business_id,
        financial_year
    )).fetchone()


    if existing:

        conn.close()

        return float(
            existing["close_amount"] or 0
        )


    close_amount = 0.0


    previous_year = (
        get_previous_financial_year(
            financial_year
        )
    )


    try:

        previous_start, previous_end = (
            get_financial_year_range(
                previous_year
            )
        )


        previous_year_row = conn.execute("""
            SELECT

                close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business_id,
            previous_year
        )).fetchone()


        previous_close = 0.0


        if previous_year_row:

            previous_close = float(
                previous_year_row[
                    "close_amount"
                ] or 0
            )


        previous_bill = conn.execute("""
            SELECT

                COALESCE(
                    SUM(bill_amount),
                    0
                ) AS total

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

        """, (
            business_id,
            previous_start,
            previous_end
        )).fetchone()


        previous_received = conn.execute("""
            SELECT

                COALESCE(
                    SUM(amount_received),
                    0
                ) AS total

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

        """, (
            business_id,
            previous_start,
            previous_end
        )).fetchone()


        previous_bill_total = float(
            previous_bill["total"] or 0
        )


        previous_received_total = float(
            previous_received["total"] or 0
        )


        close_amount = (
            previous_bill_total
            + previous_close
            - previous_received_total
        )


    except ValueError:

        close_amount = 0.0


    if close_amount < 0:

        close_amount = 0.0


    conn.execute("""
        INSERT INTO business_years
        (
            business_id,
            financial_year,
            close_amount
        )

        VALUES (?, ?, ?)

    """, (
        business_id,
        financial_year,
        close_amount
    ))


    conn.commit()

    conn.close()


    return close_amount


# =========================================================
# LOGIN
# =========================================================

@app.route(
    "/",
    methods=["GET", "POST"]
)
def login():

    if session.get("logged_in"):

        return redirect(
            url_for("dashboard")
        )


    error = None


    if request.method == "POST":

        username = request.form.get(
            "username",
            ""
        ).strip()


        password = request.form.get(
            "password",
            ""
        )


        if (
            username == USERNAME
            and password == PASSWORD
        ):

            session["logged_in"] = True

            session["username"] = username

            return redirect(
                url_for("dashboard")
            )


        error = (
            "Invalid username or password."
        )


    return render_template(
        "login.html",
        error=error
    )


# =========================================================
# BUSINESS LIST
# =========================================================

def get_businesses(
    selected_year,
    keyword=None
):

    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    conn = get_db()


    if keyword:

        rows = conn.execute("""
            SELECT

                b.id,

                b.name

            FROM businesses b

            WHERE b.is_deleted = 0
              AND b.name LIKE ?

            ORDER BY b.id ASC

        """, (
            "%" + keyword + "%",
        )).fetchall()

    else:

        rows = conn.execute("""
            SELECT

                b.id,

                b.name

            FROM businesses b

            WHERE b.is_deleted = 0

            ORDER BY b.id ASC

        """).fetchall()


    result = []


    for business in rows:

        ensure_business_year(
            business["id"],
            selected_year
        )


        year_row = conn.execute("""
            SELECT

                close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business["id"],
            selected_year
        )).fetchone()


        close_amount = float(
            year_row["close_amount"]
            if year_row
            else 0
        )


        bill_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(bill_amount),
                    0
                ) AS total

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

        """, (
            business["id"],
            start_date,
            end_date
        )).fetchone()


        received_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(amount_received),
                    0
                ) AS total

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

        """, (
            business["id"],
            start_date,
            end_date
        )).fetchone()


        total_sale = float(
            bill_row["total"] or 0
        )


        amount_received = float(
            received_row["total"] or 0
        )


        net_amount = (
            total_sale
            + close_amount
            - amount_received
        )


        result.append({

            "id":
                business["id"],

            "name":
                business["name"],

            "close_amount":
                close_amount,

            "total_sale":
                total_sale,

            "amount_received":
                amount_received,

            "net_amount":
                net_amount

        })


    conn.close()


    return result


# =========================================================
# DASHBOARD
# =========================================================

@app.route("/dashboard")
def dashboard():

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    current_year = (
        get_current_financial_year()
    )


    selected_year = request.args.get(
        "year",
        current_year
    ).strip()


    available_years = (
        get_financial_years()
    )


    if selected_year not in available_years:

        selected_year = current_year


    businesses = get_businesses(
        selected_year
    )


    return render_template(

        "dashboard.html",

        businesses=businesses,

        username=session.get(
            "username"
        ),

        selected_year=selected_year,

        current_year=current_year,

        financial_years=available_years,

        search_keyword="",

        search_mode=False,

        recovery=None,

        recovery_not_found=False

    )


# =========================================================
# ADD YEAR
# =========================================================

@app.route(
    "/add-year",
    methods=["POST"]
)
def add_year():

    if not session.get("logged_in"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    raw_value = request.form.get("financial_year", "").strip()

    try:
        financial_year = normalize_financial_year(raw_value)
    except ValueError:
        return jsonify({
            "success": False,
            "message": "Please enter like: 01/04/2027 - 31/03/2028"
        }), 400

    current_year = get_current_financial_year()

    conn = get_db()
    exists = conn.execute(
        "SELECT 1 FROM financial_years WHERE financial_year = ?",
        (financial_year,)
    ).fetchone()

    if exists:
        conn.close()
        return jsonify({
            "success": False,
            "message": "This financial year already exists."
        }), 400

    conn.execute(
        "INSERT INTO financial_years (financial_year, created_at) VALUES (?, CURRENT_TIMESTAMP)",
        (financial_year,)
    )
    conn.commit()
    conn.close()

    return jsonify({
        "success": True,
        "year": financial_year,
        "label": financial_year_to_label(financial_year),
        "message": "Financial year added successfully."
    })


# =========================================================
# ADD NAME
# =========================================================

@app.route(
    "/add-name",
    methods=["POST"]
)
def add_name():

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    name = request.form.get(
        "name",
        ""
    ).strip()


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    if name:

        conn = get_db()


        try:

            cursor = conn.execute("""
                INSERT INTO businesses
                (
                    name
                )

                VALUES (?)

            """, (
                name,
            ))


            business_id = cursor.lastrowid


            conn.commit()


        except sqlite3.IntegrityError:

            existing = conn.execute("""
                SELECT id
                FROM businesses
                WHERE name = ?
            """, (
                name,
            )).fetchone()


            business_id = (
                existing["id"]
                if existing
                else None
            )


        conn.close()


        if business_id:

            ensure_business_year(
                business_id,
                selected_year
            )


    return redirect(
        url_for(
            "dashboard",
            year=selected_year
        )
    )


# =========================================================
# SEARCH
# =========================================================

@app.route("/search")
def search():

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    keyword = request.args.get(
        "q",
        ""
    ).strip()

    current_year = get_current_financial_year()

    selected_year = request.args.get(
        "year",
        current_year
    ).strip()

    financial_years = get_financial_years()

    if selected_year not in financial_years:
        selected_year = current_year

    if not keyword:
        return redirect(
            url_for(
                "dashboard",
                year=selected_year
            )
        )

    if keyword.upper().startswith("REC-"):
        try:
            restored = restore_recovery_backup(
                keyword
            )

            if restored is None:
                restored = restore_legacy_recovery(
                    keyword
                )

            if restored is not None:
                restore_year = (
                    restored.get("year")
                    or selected_year
                )

                return redirect(
                    url_for(
                        "dashboard",
                        year=restore_year
                    )
                )

        except Exception as exc:
            return render_template(
                "dashboard.html",
                businesses=[],
                username=session.get("username"),
                selected_year=selected_year,
                current_year=current_year,
                financial_years=get_financial_years(),
                search_keyword=keyword,
                search_mode=True,
                recovery=None,
                recovery_not_found=True,
                recovery_error=str(exc)
            )

    businesses = get_businesses(
        selected_year,
        keyword
    )

    return render_template(
        "dashboard.html",
        businesses=businesses,
        username=session.get("username"),
        selected_year=selected_year,
        current_year=current_year,
        financial_years=financial_years,
        search_keyword=keyword,
        search_mode=True,
        recovery=None,
        recovery_not_found=False
    )


# =========================================================
# BUSINESS ENTRY
# =========================================================

@app.route(
    "/business/<int:business_id>"
)
def business_entry(business_id):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    current_year = (
        get_current_financial_year()
    )


    selected_year = request.args.get(
        "year",
        current_year
    ).strip()


    financial_years = (
        get_financial_years()
    )


    if selected_year not in financial_years:

        selected_year = current_year


    close_amount = ensure_business_year(
        business_id,
        selected_year
    )


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    conn = get_db()


    business = conn.execute("""
        SELECT

            id,

            name

        FROM businesses

        WHERE id = ?
          AND is_deleted = 0

    """, (
        business_id,
    )).fetchone()


    if not business:

        conn.close()

        return redirect(
            url_for("dashboard")
        )


    entries = conn.execute("""
        SELECT

            id,

            entry_date,

            bill_amount

        FROM entries

        WHERE

            business_id = ?

            AND entry_date >= ?

            AND entry_date <= ?

        ORDER BY

            entry_date ASC,

            id ASC

    """, (
        business_id,

        start_date,

        end_date

    )).fetchall()


    received_entries = conn.execute("""
        SELECT

            id,

            received_date,

            amount_received,

            note

        FROM received_entries

        WHERE

            business_id = ?

            AND received_date >= ?

            AND received_date <= ?

        ORDER BY

            received_date ASC,

            id ASC

    """, (
        business_id,

        start_date,

        end_date

    )).fetchall()


    conn.close()


    total_bill = sum(
        float(
            row["bill_amount"] or 0
        )
        for row in entries
    )


    total_received = sum(
        float(
            row["amount_received"] or 0
        )
        for row in received_entries
    )


    total_with_close = (
        total_bill
        + close_amount
    )


    net_amount = (
        total_with_close
        - total_received
    )


    previous_year = (
        get_previous_financial_year(
            selected_year
        )
    )


    previous_close = 0.0


    try:

        previous_start, previous_end = (
            get_financial_year_range(
                previous_year
            )
        )


        conn = get_db()


        previous_year_row = conn.execute("""
            SELECT

                close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business_id,
            previous_year
        )).fetchone()


        previous_close_value = (
            float(
                previous_year_row[
                    "close_amount"
                ] or 0
            )
            if previous_year_row
            else 0
        )


        previous_bill_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(bill_amount),
                    0
                ) AS total

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

        """, (
            business_id,

            previous_start,

            previous_end

        )).fetchone()


        previous_received_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(amount_received),
                    0
                ) AS total

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

        """, (
            business_id,

            previous_start,

            previous_end

        )).fetchone()


        previous_bill_total = float(
            previous_bill_row["total"] or 0
        )


        previous_received_total = float(
            previous_received_row["total"] or 0
        )


        previous_close = (
            previous_bill_total
            +
            previous_close_value
            -
            previous_received_total
        )


        conn.close()


    except ValueError:

        previous_close = 0.0


    return render_template(

        "business_entry.html",

        business={
            "id": business["id"],
            "name": business["name"],
            "close_amount": close_amount
        },

        entries=entries,

        received_entries=received_entries,

        total_bill=total_bill,

        total_received=total_received,

        total_with_close=total_with_close,

        net_amount=net_amount,

        selected_year=selected_year,

        current_year=current_year,

        financial_years=financial_years,

        previous_year=previous_year,

        previous_close=previous_close

    )


# =========================================================
# SET CLOSE AMOUNT
# =========================================================

@app.route(
    "/business/<int:business_id>/set-close-amount",
    methods=["POST"]
)
def set_close_amount(business_id):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    value = request.form.get(
        "close_amount",
        ""
    ).strip()


    try:

        close_amount = (
            float(value)
            if value
            else 0.0
        )


        if close_amount < 0:

            close_amount = 0.0


    except ValueError:

        close_amount = 0.0


    ensure_business_year(
        business_id,
        selected_year
    )


    conn = get_db()


    conn.execute("""
        UPDATE business_years

        SET close_amount = ?

        WHERE

            business_id = ?

            AND financial_year = ?

    """, (
        close_amount,

        business_id,

        selected_year

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# ADD BILL
# =========================================================

@app.route(
    "/business/<int:business_id>/add-entry",
    methods=["POST"]
)
def add_entry(business_id):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    entry_date = request.form.get(
        "entry_date",
        ""
    ).strip()


    bill_amount = request.form.get(
        "bill_amount",
        ""
    ).strip()


    normalized_date = normalize_date(
        entry_date
    )


    if (
        not normalized_date
        or not bill_amount
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    if not (
        start_date
        <= normalized_date
        <= end_date
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    try:

        bill = float(
            bill_amount
        )


        if bill < 0:

            raise ValueError


    except ValueError:

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    ensure_business_year(
        business_id,
        selected_year
    )


    conn = get_db()


    conn.execute("""
        INSERT INTO entries
        (
            business_id,

            entry_date,

            bill_amount
        )

        VALUES (?, ?, ?)

    """, (
        business_id,

        normalized_date,

        bill

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# UPDATE BILL
# =========================================================

@app.route(
    "/business/<int:business_id>/update-entry/<int:entry_id>",
    methods=["POST"]
)
def update_entry(
    business_id,
    entry_id
):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    entry_date = request.form.get(
        "entry_date",
        ""
    ).strip()


    bill_amount = request.form.get(
        "bill_amount",
        ""
    ).strip()


    normalized_date = normalize_date(
        entry_date
    )


    if (
        not normalized_date
        or not bill_amount
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    if not (
        start_date
        <= normalized_date
        <= end_date
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    try:

        bill = float(
            bill_amount
        )


        if bill < 0:

            raise ValueError


    except ValueError:

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    conn = get_db()


    existing = conn.execute("""
        SELECT id

        FROM entries

        WHERE

            id = ?

            AND business_id = ?

    """, (
        entry_id,

        business_id

    )).fetchone()


    if not existing:

        conn.close()

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    conn.execute("""
        UPDATE entries

        SET

            entry_date = ?,

            bill_amount = ?

        WHERE

            id = ?

            AND business_id = ?

    """, (
        normalized_date,

        bill,

        entry_id,

        business_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# DELETE BILL
# =========================================================

@app.route(
    "/business/<int:business_id>/delete-entry/<int:entry_id>",
    methods=["POST"]
)
def delete_entry(
    business_id,
    entry_id
):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    conn = get_db()


    conn.execute("""
        DELETE FROM entries

        WHERE

            id = ?

            AND business_id = ?

    """, (
        entry_id,

        business_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# ADD RECEIVED
# =========================================================

@app.route(
    "/business/<int:business_id>/add-received",
    methods=["POST"]
)
def add_received(business_id):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    received_date = request.form.get(
        "received_date",
        ""
    ).strip()


    amount_received = request.form.get(
        "amount_received",
        ""
    ).strip()

    note = request.form.get(
        "note",
        ""
    ).strip()


    normalized_date = normalize_date(
        received_date
    )


    if (
        not normalized_date
        or not amount_received
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    if not (
        start_date
        <= normalized_date
        <= end_date
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    try:

        amount = float(
            amount_received
        )


        if amount < 0:

            raise ValueError


    except ValueError:

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    ensure_business_year(
        business_id,
        selected_year
    )


    conn = get_db()


    conn.execute("""
        INSERT INTO received_entries
        (
            business_id,

            received_date,

            amount_received,

            note
        )

        VALUES (?, ?, ?, ?)

    """, (
        business_id,

        normalized_date,

        amount,

        note

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# UPDATE RECEIVED
# =========================================================

@app.route(
    "/business/<int:business_id>/update-received/<int:received_id>",
    methods=["POST"]
)
def update_received(
    business_id,
    received_id
):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    received_date = request.form.get(
        "received_date",
        ""
    ).strip()


    amount_received = request.form.get(
        "amount_received",
        ""
    ).strip()

    note = request.form.get(
        "note",
        ""
    ).strip()


    normalized_date = normalize_date(
        received_date
    )


    if (
        not normalized_date
        or not amount_received
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    if not (
        start_date
        <= normalized_date
        <= end_date
    ):

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    try:

        amount = float(
            amount_received
        )


        if amount < 0:

            raise ValueError


    except ValueError:

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    conn = get_db()


    existing = conn.execute("""
        SELECT id

        FROM received_entries

        WHERE

            id = ?

            AND business_id = ?

    """, (
        received_id,

        business_id

    )).fetchone()


    if not existing:

        conn.close()

        return redirect(
            url_for(
                "business_entry",
                business_id=business_id,
                year=selected_year
            )
        )


    conn.execute("""
        UPDATE received_entries

        SET

            received_date = ?,

            amount_received = ?,

            note = ?

        WHERE

            id = ?

            AND business_id = ?

    """, (
        normalized_date,

        amount,

        note,

        received_id,

        business_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# DELETE RECEIVED
# =========================================================

@app.route(
    "/business/<int:business_id>/delete-received/<int:received_id>",
    methods=["POST"]
)
def delete_received(
    business_id,
    received_id
):

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()


    conn = get_db()


    conn.execute("""
        DELETE FROM received_entries

        WHERE

            id = ?

            AND business_id = ?

    """, (
        received_id,

        business_id

    ))


    conn.commit()

    conn.close()


    return redirect(
        url_for(
            "business_entry",
            business_id=business_id,
            year=selected_year
        )
    )


# =========================================================
# DELETE BUSINESS
# =========================================================

@app.route(
    "/delete-business/<int:business_id>",
    methods=["POST"]
)
def delete_business(business_id):

    if not session.get("logged_in"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    mode = request.form.get(
        "mode",
        "all"
    ).strip()

    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()

    conn = get_db()

    business = conn.execute("""
        SELECT id, name, is_deleted
        FROM businesses
        WHERE id = ?
    """, (business_id,)).fetchone()

    if not business:
        conn.close()
        return jsonify({
            "success": False,
            "message": "Business not found."
        }), 404

    try:
        if mode == "name-only":
            snapshot = capture_business_name_snapshot(
                business_id
            )

            recovery_id = save_recovery_backup(
                "BUSINESS_NAME",
                business["name"],
                selected_year,
                snapshot
            )

            conn.execute("""
                UPDATE businesses
                SET is_deleted = 1
                WHERE id = ?
            """, (business_id,))

        elif mode == "data-only":
            snapshot = capture_business_year_snapshot(
                business_id,
                selected_year
            )

            recovery_id = save_recovery_backup(
                "BUSINESS_YEAR",
                business["name"],
                selected_year,
                snapshot
            )

            start_date, end_date = get_financial_year_range(
                selected_year
            )

            conn.execute("""
                DELETE FROM entries
                WHERE business_id = ?
                  AND entry_date >= ?
                  AND entry_date <= ?
            """, (
                business_id,
                start_date,
                end_date
            ))

            conn.execute("""
                DELETE FROM received_entries
                WHERE business_id = ?
                  AND received_date >= ?
                  AND received_date <= ?
            """, (
                business_id,
                start_date,
                end_date
            ))

            conn.execute("""
                DELETE FROM business_years
                WHERE business_id = ?
                  AND financial_year = ?
            """, (
                business_id,
                selected_year
            ))

        else:
            snapshot = capture_business_snapshot(
                business_id
            )

            recovery_id = save_recovery_backup(
                "BUSINESS",
                business["name"],
                selected_year,
                snapshot
            )

            conn.execute("""
                DELETE FROM entries
                WHERE business_id = ?
            """, (business_id,))

            conn.execute("""
                DELETE FROM received_entries
                WHERE business_id = ?
            """, (business_id,))

            conn.execute("""
                DELETE FROM business_years
                WHERE business_id = ?
            """, (business_id,))

            conn.execute("""
                DELETE FROM businesses
                WHERE id = ?
            """, (business_id,))

        conn.commit()

    except Exception as exc:
        conn.rollback()
        conn.close()
        return jsonify({
            "success": False,
            "message": str(exc)
        }), 500

    conn.close()

    return jsonify({
        "success": True,
        "recovery_id": recovery_id,
        "year": selected_year,
        "name": business["name"],
        "mode": mode
    })


# =========================================================
# RECOVERY TABLES
# =========================================================

def ensure_recovery_tables():

    conn = get_db()


    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_records (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recovery_id TEXT NOT NULL UNIQUE,

            clear_year TEXT NOT NULL,

            created_at TEXT NOT NULL

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_businesses (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recovery_id TEXT NOT NULL,

            business_name TEXT NOT NULL,

            close_amount REAL NOT NULL DEFAULT 0

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_bills (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recovery_id TEXT NOT NULL,

            business_name TEXT NOT NULL,

            entry_date TEXT NOT NULL,

            bill_amount REAL NOT NULL DEFAULT 0

        )
    """)


    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_received (

            id INTEGER PRIMARY KEY AUTOINCREMENT,

            recovery_id TEXT NOT NULL,

            business_name TEXT NOT NULL,

            received_date TEXT NOT NULL,

            amount_received REAL NOT NULL DEFAULT 0

        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_delete_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recovery_id TEXT NOT NULL UNIQUE,
            recovery_type TEXT NOT NULL,
            recovery_name TEXT,
            clear_year TEXT,
            created_at TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            restored INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.execute("""
        CREATE TABLE IF NOT EXISTS recovery_clear_backups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            recovery_id TEXT NOT NULL UNIQUE,
            recovery_type TEXT NOT NULL,
            recovery_name TEXT,
            clear_year TEXT,
            created_at TEXT NOT NULL,
            snapshot_json TEXT NOT NULL,
            restored INTEGER NOT NULL DEFAULT 0
        )
    """)

    conn.commit()

    conn.close()


# =========================================================
# FLEXIBLE RECOVERY SYSTEM
# =========================================================

def make_recovery_id(year=None):
    year = year or get_current_financial_year()
    prefix = year[:4] if re.fullmatch(r"\d{4}-\d{2}", year) else "DATA"

    conn = get_db()
    try:
        while True:
            recovery_id = f"REC-{prefix}-{secrets.token_hex(4).upper()}"
            exists = False

            for table in ("recovery_delete_backups", "recovery_clear_backups"):
                if conn.execute(
                    f"SELECT 1 FROM {table} WHERE recovery_id = ?",
                    (recovery_id,)
                ).fetchone():
                    exists = True
                    break

            if not exists:
                try:
                    if conn.execute(
                        "SELECT 1 FROM recovery_backups WHERE recovery_id = ?",
                        (recovery_id,)
                    ).fetchone():
                        exists = True
                except sqlite3.OperationalError:
                    pass

            if not exists:
                return recovery_id
    finally:
        conn.close()


def save_recovery_backup(
    recovery_type,
    recovery_name,
    clear_year,
    snapshot
):
    ensure_recovery_tables()
    recovery_id = make_recovery_id(clear_year)

    table = (
        "recovery_clear_backups"
        if recovery_type == "ALL"
        else "recovery_delete_backups"
    )

    conn = get_db()
    conn.execute(
        f"""
        INSERT INTO {table}
        (recovery_id, recovery_type, recovery_name, clear_year,
         created_at, snapshot_json, restored)
        VALUES (?, ?, ?, ?, ?, ?, 0)
        """,
        (
            recovery_id,
            recovery_type,
            recovery_name,
            clear_year,
            datetime.now().isoformat(timespec="seconds"),
            json.dumps(snapshot, ensure_ascii=False)
        )
    )
    conn.commit()
    conn.close()
    return recovery_id


def _rows_to_dicts(rows):
    return [
        dict(row)
        for row in rows
    ]


def capture_business_name_snapshot(
    business_id
):
    conn = get_db()

    business = conn.execute("""
        SELECT id, name, is_deleted
        FROM businesses
        WHERE id = ?
    """, (business_id,)).fetchone()

    conn.close()

    if not business:
        raise ValueError("Business not found.")

    return {
        "business": dict(business)
    }


def capture_business_year_snapshot(
    business_id,
    selected_year
):
    start_date, end_date = get_financial_year_range(
        selected_year
    )

    conn = get_db()

    business = conn.execute("""
        SELECT id, name, is_deleted
        FROM businesses
        WHERE id = ?
    """, (business_id,)).fetchone()

    year_row = conn.execute("""
        SELECT business_id, financial_year, close_amount
        FROM business_years
        WHERE business_id = ?
          AND financial_year = ?
    """, (
        business_id,
        selected_year
    )).fetchone()

    bills = conn.execute("""
        SELECT entry_date, bill_amount
        FROM entries
        WHERE business_id = ?
          AND entry_date >= ?
          AND entry_date <= ?
        ORDER BY entry_date ASC, id ASC
    """, (
        business_id,
        start_date,
        end_date
    )).fetchall()

    received = conn.execute("""
        SELECT received_date, amount_received, note
        FROM received_entries
        WHERE business_id = ?
          AND received_date >= ?
          AND received_date <= ?
        ORDER BY received_date ASC, id ASC
    """, (
        business_id,
        start_date,
        end_date
    )).fetchall()

    conn.close()

    if not business:
        raise ValueError("Business not found.")

    return {
        "business": dict(business),
        "financial_year": selected_year,
        "business_year": (
            dict(year_row)
            if year_row else None
        ),
        "entries": _rows_to_dicts(bills),
        "received_entries": _rows_to_dicts(received)
    }


def capture_business_snapshot(
    business_id
):
    conn = get_db()

    business = conn.execute("""
        SELECT id, name, is_deleted
        FROM businesses
        WHERE id = ?
    """, (business_id,)).fetchone()

    years = conn.execute("""
        SELECT business_id, financial_year, close_amount
        FROM business_years
        WHERE business_id = ?
        ORDER BY financial_year ASC
    """, (business_id,)).fetchall()

    bills = conn.execute("""
        SELECT entry_date, bill_amount
        FROM entries
        WHERE business_id = ?
        ORDER BY entry_date ASC, id ASC
    """, (business_id,)).fetchall()

    received = conn.execute("""
        SELECT received_date, amount_received, note
        FROM received_entries
        WHERE business_id = ?
        ORDER BY received_date ASC, id ASC
    """, (business_id,)).fetchall()

    conn.close()

    if not business:
        raise ValueError("Business not found.")

    return {
        "business": dict(business),
        "business_years": _rows_to_dicts(years),
        "entries": _rows_to_dicts(bills),
        "received_entries": _rows_to_dicts(received)
    }


def capture_year_snapshot(
    selected_year
):
    start_date, end_date = get_financial_year_range(
        selected_year
    )

    conn = get_db()

    year_exists = conn.execute("""
        SELECT financial_year
        FROM financial_years
        WHERE financial_year = ?
    """, (selected_year,)).fetchone()

    business_years = conn.execute("""
        SELECT business_id, financial_year, close_amount
        FROM business_years
        WHERE financial_year = ?
        ORDER BY business_id ASC
    """, (selected_year,)).fetchall()

    bills = conn.execute("""
        SELECT business_id, entry_date, bill_amount
        FROM entries
        WHERE entry_date >= ?
          AND entry_date <= ?
        ORDER BY business_id ASC, entry_date ASC, id ASC
    """, (
        start_date,
        end_date
    )).fetchall()

    received = conn.execute("""
        SELECT business_id, received_date, amount_received, note
        FROM received_entries
        WHERE received_date >= ?
          AND received_date <= ?
        ORDER BY business_id ASC, received_date ASC, id ASC
    """, (
        start_date,
        end_date
    )).fetchall()

    conn.close()

    if not year_exists:
        raise ValueError("Financial year not found.")

    return {
        "financial_year": selected_year,
        "business_years": _rows_to_dicts(business_years),
        "entries": _rows_to_dicts(bills),
        "received_entries": _rows_to_dicts(received)
    }


def capture_all_data_snapshot():
    conn = get_db()

    financial_years = conn.execute("""
        SELECT financial_year
        FROM financial_years
        ORDER BY financial_year ASC
    """).fetchall()

    business_years = conn.execute("""
        SELECT business_id, financial_year, close_amount
        FROM business_years
        ORDER BY business_id ASC, financial_year ASC
    """).fetchall()

    bills = conn.execute("""
        SELECT business_id, entry_date, bill_amount
        FROM entries
        ORDER BY business_id ASC, entry_date ASC, id ASC
    """).fetchall()

    received = conn.execute("""
        SELECT business_id, received_date, amount_received, note
        FROM received_entries
        ORDER BY business_id ASC, received_date ASC, id ASC
    """).fetchall()

    conn.close()

    return {
        "financial_years": [
            row["financial_year"]
            for row in financial_years
        ],
        "business_years": _rows_to_dicts(business_years),
        "entries": _rows_to_dicts(bills),
        "received_entries": _rows_to_dicts(received)
    }


def restore_recovery_backup(
    recovery_id
):
    ensure_recovery_tables()

    conn = get_db()

    recovery_key = recovery_id.upper().strip()
    row = None
    source_table = None

    for table in ("recovery_delete_backups", "recovery_clear_backups"):
        row = conn.execute(
            f"""
            SELECT recovery_id, recovery_type, recovery_name, clear_year,
                   snapshot_json, restored
            FROM {table}
            WHERE recovery_id = ?
            """,
            (recovery_key,)
        ).fetchone()
        if row:
            source_table = table
            break

    if not row:
        try:
            row = conn.execute("""
                SELECT recovery_id, recovery_type, recovery_name, clear_year,
                       snapshot_json, restored
                FROM recovery_backups
                WHERE recovery_id = ?
            """, (recovery_key,)).fetchone()
            if row:
                source_table = "recovery_backups"
        except sqlite3.OperationalError:
            row = None

    if not row:
        conn.close()
        return None

    if row["restored"]:
        conn.close()
        return {
            "success": True,
            "already_restored": True,
            "year": row["clear_year"],
            "name": row["recovery_name"]
        }

    try:
        snapshot = json.loads(
            row["snapshot_json"]
        )
        recovery_type = row["recovery_type"]

        if recovery_type == "BUSINESS_NAME":
            business = snapshot["business"]

            conn.execute("""
                UPDATE businesses
                SET is_deleted = 0
                WHERE id = ?
            """, (business["id"],))

            if conn.total_changes == 0:
                existing = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE name = ?
                """, (business["name"],)).fetchone()

                if existing:
                    conn.execute("""
                        UPDATE businesses
                        SET is_deleted = 0
                        WHERE id = ?
                    """, (existing["id"],))
                else:
                    conn.execute("""
                        INSERT INTO businesses
                        (name, is_deleted)
                        VALUES (?, 0)
                    """, (business["name"],))

        elif recovery_type == "BUSINESS_YEAR":
            business = snapshot["business"]
            selected_year = snapshot["financial_year"]

            business_row = conn.execute("""
                SELECT id
                FROM businesses
                WHERE id = ?
            """, (business["id"],)).fetchone()

            if not business_row:
                existing = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE name = ?
                """, (business["name"],)).fetchone()

                if existing:
                    target_business_id = existing["id"]
                else:
                    cursor = conn.execute("""
                        INSERT INTO businesses
                        (name, is_deleted)
                        VALUES (?, 0)
                    """, (business["name"],))
                    target_business_id = cursor.lastrowid
            else:
                target_business_id = business["id"]

            start_date, end_date = get_financial_year_range(
                selected_year
            )

            conn.execute("""
                DELETE FROM entries
                WHERE business_id = ?
                  AND entry_date >= ?
                  AND entry_date <= ?
            """, (
                target_business_id,
                start_date,
                end_date
            ))

            conn.execute("""
                DELETE FROM received_entries
                WHERE business_id = ?
                  AND received_date >= ?
                  AND received_date <= ?
            """, (
                target_business_id,
                start_date,
                end_date
            ))

            conn.execute("""
                DELETE FROM business_years
                WHERE business_id = ?
                  AND financial_year = ?
            """, (
                target_business_id,
                selected_year
            ))

            conn.execute("""
                INSERT INTO business_years
                (business_id, financial_year, close_amount)
                VALUES (?, ?, ?)
            """, (
                target_business_id,
                selected_year,
                float(
                    (snapshot["business_year"] or {}).get(
                        "close_amount", 0
                    )
                )
            ))

            for item in snapshot["entries"]:
                conn.execute("""
                    INSERT INTO entries
                    (business_id, entry_date, bill_amount)
                    VALUES (?, ?, ?)
                """, (
                    target_business_id,
                    item["entry_date"],
                    float(item["bill_amount"] or 0)
                ))

            for item in snapshot["received_entries"]:
                conn.execute("""
                    INSERT INTO received_entries
                    (business_id, received_date, amount_received, note)
                    VALUES (?, ?, ?, ?)
                """, (
                    target_business_id,
                    item["received_date"],
                    float(item["amount_received"] or 0),
                    item.get("note", "")
                ))

        elif recovery_type == "BUSINESS":
            business = snapshot["business"]

            existing = conn.execute("""
                SELECT id
                FROM businesses
                WHERE name = ?
            """, (business["name"],)).fetchone()

            if existing:
                target_business_id = existing["id"]
                conn.execute("""
                    DELETE FROM entries
                    WHERE business_id = ?
                """, (target_business_id,))
                conn.execute("""
                    DELETE FROM received_entries
                    WHERE business_id = ?
                """, (target_business_id,))
                conn.execute("""
                    DELETE FROM business_years
                    WHERE business_id = ?
                """, (target_business_id,))
                conn.execute("""
                    DELETE FROM businesses
                    WHERE id = ?
                """, (target_business_id,))

            cursor = conn.execute("""
                INSERT INTO businesses
                (name, is_deleted)
                VALUES (?, 0)
            """, (business["name"],))
            target_business_id = cursor.lastrowid

            for item in snapshot["business_years"]:
                conn.execute("""
                    INSERT INTO business_years
                    (business_id, financial_year, close_amount)
                    VALUES (?, ?, ?)
                """, (
                    target_business_id,
                    item["financial_year"],
                    float(item["close_amount"] or 0)
                ))

            for item in snapshot["entries"]:
                conn.execute("""
                    INSERT INTO entries
                    (business_id, entry_date, bill_amount)
                    VALUES (?, ?, ?)
                """, (
                    target_business_id,
                    item["entry_date"],
                    float(item["bill_amount"] or 0)
                ))

            for item in snapshot["received_entries"]:
                conn.execute("""
                    INSERT INTO received_entries
                    (business_id, received_date, amount_received, note)
                    VALUES (?, ?, ?, ?)
                """, (
                    target_business_id,
                    item["received_date"],
                    float(item["amount_received"] or 0),
                    item.get("note", "")
                ))

        elif recovery_type == "YEAR":
            selected_year = snapshot["financial_year"]

            conn.execute("""
                INSERT OR IGNORE INTO financial_years
                (financial_year, created_at)
                VALUES (?, CURRENT_TIMESTAMP)
            """, (selected_year,))

            start_date, end_date = get_financial_year_range(
                selected_year
            )

            conn.execute("""
                DELETE FROM entries
                WHERE entry_date >= ?
                  AND entry_date <= ?
            """, (start_date, end_date))

            conn.execute("""
                DELETE FROM received_entries
                WHERE received_date >= ?
                  AND received_date <= ?
            """, (start_date, end_date))

            conn.execute("""
                DELETE FROM business_years
                WHERE financial_year = ?
            """, (selected_year,))

            for item in snapshot["business_years"]:
                business_id = item["business_id"]

                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (business_id,)).fetchone()

                if exists:
                    target_business_id = business_id
                else:
                    target_business_id = None

                if target_business_id is not None:
                    conn.execute("""
                        INSERT INTO business_years
                        (business_id, financial_year, close_amount)
                        VALUES (?, ?, ?)
                    """, (
                        target_business_id,
                        item["financial_year"],
                        float(item["close_amount"] or 0)
                    ))

            for item in snapshot["entries"]:
                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (item["business_id"],)).fetchone()

                if exists:
                    conn.execute("""
                        INSERT INTO entries
                        (business_id, entry_date, bill_amount)
                        VALUES (?, ?, ?)
                    """, (
                        item["business_id"],
                        item["entry_date"],
                        float(item["bill_amount"] or 0)
                    ))

            for item in snapshot["received_entries"]:
                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (item["business_id"],)).fetchone()

                if exists:
                    conn.execute("""
                        INSERT INTO received_entries
                        (business_id, received_date, amount_received, note)
                        VALUES (?, ?, ?, ?)
                    """, (
                        item["business_id"],
                        item["received_date"],
                        float(item["amount_received"] or 0),
                        item.get("note", "")
                    ))

        elif recovery_type == "ALL":
            for financial_year in snapshot["financial_years"]:
                conn.execute("""
                    INSERT OR IGNORE INTO financial_years
                    (financial_year, created_at)
                    VALUES (?, CURRENT_TIMESTAMP)
                """, (financial_year,))

            conn.execute("DELETE FROM entries")
            conn.execute("DELETE FROM received_entries")
            conn.execute("DELETE FROM business_years")

            for item in snapshot["business_years"]:
                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (item["business_id"],)).fetchone()

                if exists:
                    conn.execute("""
                        INSERT INTO business_years
                        (business_id, financial_year, close_amount)
                        VALUES (?, ?, ?)
                    """, (
                        item["business_id"],
                        item["financial_year"],
                        float(item["close_amount"] or 0)
                    ))

            for item in snapshot["entries"]:
                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (item["business_id"],)).fetchone()

                if exists:
                    conn.execute("""
                        INSERT INTO entries
                        (business_id, entry_date, bill_amount)
                        VALUES (?, ?, ?)
                    """, (
                        item["business_id"],
                        item["entry_date"],
                        float(item["bill_amount"] or 0)
                    ))

            for item in snapshot["received_entries"]:
                exists = conn.execute("""
                    SELECT id
                    FROM businesses
                    WHERE id = ?
                """, (item["business_id"],)).fetchone()

                if exists:
                    conn.execute("""
                        INSERT INTO received_entries
                        (business_id, received_date, amount_received, note)
                        VALUES (?, ?, ?, ?)
                    """, (
                        item["business_id"],
                        item["received_date"],
                        float(item["amount_received"] or 0),
                        item.get("note", "")
                    ))

        else:
            raise ValueError(
                "Unknown recovery type."
            )

        conn.execute(
            f"""UPDATE {source_table}
                SET restored = 1
                WHERE recovery_id = ?""",
            (recovery_key,)
        )

        conn.commit()

        return {
            "success": True,
            "already_restored": False,
            "year": row["clear_year"],
            "name": row["recovery_name"]
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


def restore_legacy_recovery(
    recovery_id
):
    ensure_recovery_tables()

    conn = get_db()

    record = conn.execute("""
        SELECT recovery_id, clear_year
        FROM recovery_records
        WHERE recovery_id = ?
    """, (
        recovery_id.upper().strip(),
    )).fetchone()

    if not record:
        conn.close()
        return None

    selected_year = record["clear_year"]
    start_date, end_date = get_financial_year_range(
        selected_year
    )

    try:
        conn.execute("""
            INSERT OR IGNORE INTO financial_years
            (financial_year, created_at)
            VALUES (?, CURRENT_TIMESTAMP)
        """, (selected_year,))

        business_rows = conn.execute("""
            SELECT business_name, close_amount
            FROM recovery_businesses
            WHERE recovery_id = ?
            ORDER BY id ASC
        """, (record["recovery_id"],)).fetchall()

        name_to_id = {}

        for item in business_rows:
            existing = conn.execute("""
                SELECT id
                FROM businesses
                WHERE name = ?
            """, (item["business_name"],)).fetchone()

            if existing:
                business_id = existing["id"]
                conn.execute("""
                    UPDATE businesses
                    SET is_deleted = 0
                    WHERE id = ?
                """, (business_id,))
            else:
                cursor = conn.execute("""
                    INSERT INTO businesses
                    (name, is_deleted)
                    VALUES (?, 0)
                """, (item["business_name"],))
                business_id = cursor.lastrowid

            name_to_id[item["business_name"]] = business_id

            conn.execute("""
                INSERT OR REPLACE INTO business_years
                (business_id, financial_year, close_amount)
                VALUES (?, ?, ?)
            """, (
                business_id,
                selected_year,
                float(item["close_amount"] or 0)
            ))

        conn.execute("""
            DELETE FROM entries
            WHERE entry_date >= ?
              AND entry_date <= ?
        """, (start_date, end_date))

        conn.execute("""
            DELETE FROM received_entries
            WHERE received_date >= ?
              AND received_date <= ?
        """, (start_date, end_date))

        bills = conn.execute("""
            SELECT business_name, entry_date, bill_amount
            FROM recovery_bills
            WHERE recovery_id = ?
            ORDER BY id ASC
        """, (record["recovery_id"],)).fetchall()

        for item in bills:
            business_id = name_to_id.get(
                item["business_name"]
            )

            if business_id is not None:
                conn.execute("""
                    INSERT INTO entries
                    (business_id, entry_date, bill_amount)
                    VALUES (?, ?, ?)
                """, (
                    business_id,
                    item["entry_date"],
                    float(item["bill_amount"] or 0)
                ))

        received = conn.execute("""
            SELECT business_name, received_date, amount_received
            FROM recovery_received
            WHERE recovery_id = ?
            ORDER BY id ASC
        """, (record["recovery_id"],)).fetchall()

        for item in received:
            business_id = name_to_id.get(
                item["business_name"]
            )

            if business_id is not None:
                conn.execute("""
                    INSERT INTO received_entries
                    (business_id, received_date, amount_received)
                    VALUES (?, ?, ?)
                """, (
                    business_id,
                    item["received_date"],
                    float(item["amount_received"] or 0)
                ))

        conn.commit()

        return {
            "success": True,
            "already_restored": False,
            "year": selected_year
        }

    except Exception:
        conn.rollback()
        raise

    finally:
        conn.close()


# =========================================================
# CREATE RECOVERY ID
# =========================================================

def create_recovery_snapshot(
    selected_year
):

    ensure_recovery_tables()


    conn = get_db()


    recovery_id = (
        "REC-" +
        selected_year[:4] +
        "-" +
        datetime.now().strftime(
            "%H%M%S"
        ) +
        "-" +
        datetime.now().strftime(
            "%d%m"
        )
    )


    while conn.execute("""
        SELECT 1
        FROM recovery_records
        WHERE recovery_id = ?
    """, (
        recovery_id,
    )).fetchone():

        recovery_id += "X"


    conn.execute("""
        INSERT INTO recovery_records
        (
            recovery_id,

            clear_year,

            created_at
        )

        VALUES (?, ?, ?)

    """, (
        recovery_id,

        selected_year,

        datetime.now().isoformat()
    ))


    businesses = conn.execute("""
        SELECT

            id,

            name

        FROM businesses

        ORDER BY id ASC

    """).fetchall()


    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    for business in businesses:

        business_id = business["id"]

        name = business["name"]


        ensure_business_year(
            business_id,
            selected_year
        )


        year_row = conn.execute("""
            SELECT close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business_id,

            selected_year
        )).fetchone()


        close_amount = float(
            year_row["close_amount"]
            if year_row
            else 0
        )


        conn.execute("""
            INSERT INTO recovery_businesses
            (
                recovery_id,

                business_name,

                close_amount
            )

            VALUES (?, ?, ?)

        """, (
            recovery_id,

            name,

            close_amount
        ))


        bills = conn.execute("""
            SELECT

                entry_date,

                bill_amount

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

            ORDER BY

                entry_date ASC,

                id ASC

        """, (
            business_id,

            start_date,

            end_date

        )).fetchall()


        for bill in bills:

            conn.execute("""
                INSERT INTO recovery_bills
                (
                    recovery_id,

                    business_name,

                    entry_date,

                    bill_amount
                )

                VALUES (?, ?, ?, ?)

            """, (
                recovery_id,

                name,

                bill["entry_date"],

                float(
                    bill["bill_amount"] or 0
                )
            ))


        received = conn.execute("""
            SELECT

                received_date,

                amount_received,

                note

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

            ORDER BY

                received_date ASC,

                id ASC

        """, (
            business_id,

            start_date,

            end_date

        )).fetchall()


        for item in received:

            conn.execute("""
                INSERT INTO recovery_received
                (
                    recovery_id,

                    business_name,

                    received_date,

                    amount_received
                )

                VALUES (?, ?, ?, ?)

            """, (
                recovery_id,

                name,

                item["received_date"],

                float(
                    item["amount_received"] or 0
                )
            ))


    conn.commit()

    conn.close()


    return recovery_id


# =========================================================
# DELETE FINANCIAL YEAR
# =========================================================

@app.route(
    "/delete-year",
    methods=["POST"]
)
def delete_year():

    if not session.get("logged_in"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    selected_year = request.form.get(
        "year",
        ""
    ).strip()

    if not selected_year:
        return jsonify({
            "success": False,
            "message": "Financial year is required."
        }), 400

    try:
        selected_year = normalize_financial_year(
            selected_year
        )
    except Exception:
        try:
            get_financial_year_range(selected_year)
        except ValueError:
            return jsonify({
                "success": False,
                "message": "Invalid financial year."
            }), 400

    current_year = get_current_financial_year()

    if selected_year == current_year:
        return jsonify({
            "success": False,
            "message": "Current financial year cannot be deleted."
        }), 400

    conn = get_db()

    year_exists = conn.execute(
        "SELECT 1 FROM financial_years WHERE financial_year = ?",
        (selected_year,)
    ).fetchone()

    conn.close()

    if not year_exists:
        return jsonify({
            "success": False,
            "message": "Financial year not found."
        }), 404

    try:
        snapshot = capture_year_snapshot(
            selected_year
        )

        recovery_id = save_recovery_backup(
            "YEAR",
            None,
            selected_year,
            snapshot
        )

        start_date, end_date = get_financial_year_range(
            selected_year
        )

        conn = get_db()

        conn.execute("""
            DELETE FROM entries
            WHERE entry_date >= ? AND entry_date <= ?
        """, (start_date, end_date))

        conn.execute("""
            DELETE FROM received_entries
            WHERE received_date >= ? AND received_date <= ?
        """, (start_date, end_date))

        conn.execute("""
            DELETE FROM business_years
            WHERE financial_year = ?
        """, (selected_year,))

        conn.execute("""
            DELETE FROM financial_years
            WHERE financial_year = ?
        """, (selected_year,))

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "recovery_id": recovery_id,
            "year": selected_year
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "message": str(exc)
        }), 500


# =========================================================
# CLEAR ALL SELECTED YEAR
# =========================================================

@app.route(
    "/clear-all",
    methods=["POST"]
)
def clear_all():

    if not session.get("logged_in"):
        return jsonify({
            "success": False,
            "message": "Please login first."
        }), 401

    selected_year = request.form.get(
        "year",
        get_current_financial_year()
    ).strip()

    try:
        snapshot = capture_all_data_snapshot()

        recovery_id = save_recovery_backup(
            "ALL",
            None,
            selected_year,
            snapshot
        )

        conn = get_db()

        conn.execute("DELETE FROM entries")
        conn.execute("DELETE FROM received_entries")
        conn.execute("DELETE FROM business_years")

        conn.commit()
        conn.close()

        return jsonify({
            "success": True,
            "recovery_id": recovery_id,
            "year": selected_year
        })

    except Exception as exc:
        return jsonify({
            "success": False,
            "message": str(exc)
        }), 500


# =========================================================
# SAVE ALL ONE PDF
# =========================================================

def create_all_business_pdf(
    selected_year
):

    start_date, end_date = (
        get_financial_year_range(
            selected_year
        )
    )


    conn = get_db()


    businesses = conn.execute("""
        SELECT

            id,

            name

        FROM businesses

        WHERE is_deleted = 0

        ORDER BY id ASC

    """).fetchall()


    buffer = io.BytesIO()


    document = SimpleDocTemplate(
        buffer,

        pagesize=A4,

        rightMargin=30,

        leftMargin=30,

        topMargin=35,

        bottomMargin=35
    )


    styles = getSampleStyleSheet()


    title_style = styles["Title"]

    title_style.alignment = (
        TA_CENTER
    )


    name_style = styles["Heading1"]

    name_style.alignment = (
        TA_CENTER
    )


    section_heading = styles["Heading3"]


    story = []


    # =====================================================
    # PAGE 1 - INDEX
    # =====================================================

    story.append(
        Paragraph(
            "Business Manager",
            title_style
        )
    )


    story.append(
        Spacer(
            1,
            8
        )
    )


    story.append(
        Paragraph(
            "Financial Year: " +
            financial_year_to_label(
                selected_year
            ),
            section_heading
        )
    )


    story.append(
        Spacer(
            1,
            15
        )
    )


    index_data = [

        [
            "No.",
            "Name",
            "Total Sale",
            "Received",
            "Net Amount"
        ]

    ]


    for index, business in enumerate(
        businesses,
        start=1
    ):

        ensure_business_year(
            business["id"],
            selected_year
        )


        year_row = conn.execute("""
            SELECT close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business["id"],

            selected_year
        )).fetchone()


        close_amount = float(
            year_row["close_amount"]
            if year_row
            else 0
        )


        bill_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(bill_amount),
                    0
                ) AS total

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

        """, (
            business["id"],

            start_date,

            end_date

        )).fetchone()


        received_row = conn.execute("""
            SELECT

                COALESCE(
                    SUM(amount_received),
                    0
                ) AS total

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

        """, (
            business["id"],

            start_date,

            end_date

        )).fetchone()


        total_sale = float(
            bill_row["total"] or 0
        )


        total_received = float(
            received_row["total"] or 0
        )


        net_amount = (
            total_sale
            + close_amount
            - total_received
        )


        index_data.append([

            str(index),

            str(
                business["name"]
            ),

            f"Rs. {total_sale:,.2f}",

            f"Rs. {total_received:,.2f}",

            f"Rs. {net_amount:,.2f}"

        ])


    if len(index_data) == 1:

        index_data.append([
            "-",
            "No businesses",
            "Rs. 0.00",
            "Rs. 0.00",
            "Rs. 0.00"
        ])


    index_table = Table(
        index_data,

        colWidths=[
            40,
            180,
            100,
            100,
            100
        ],

        repeatRows=1
    )


    index_table.setStyle(
        TableStyle([

            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor(
                    "#667eea"
                )
            ),

            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),

            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),

            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),

            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),

            (
                "VALIGN",
                (0, 0),
                (-1, -1),
                "MIDDLE"
            ),

            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),

            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )

        ])
    )


    story.append(
        index_table
    )


    # =====================================================
    # EACH BUSINESS = NEW PAGE
    # =====================================================

    for business in businesses:

        business_id = business["id"]

        name = business["name"]


        ensure_business_year(
            business_id,
            selected_year
        )


        year_row = conn.execute("""
            SELECT close_amount

            FROM business_years

            WHERE

                business_id = ?

                AND financial_year = ?

        """, (
            business_id,

            selected_year

        )).fetchone()


        close_amount = float(
            year_row["close_amount"]
            if year_row
            else 0
        )


        bill_entries = conn.execute("""
            SELECT

                entry_date,

                bill_amount

            FROM entries

            WHERE

                business_id = ?

                AND entry_date >= ?

                AND entry_date <= ?

            ORDER BY

                entry_date ASC,

                id ASC

        """, (
            business_id,

            start_date,

            end_date

        )).fetchall()


        received_entries = conn.execute("""
            SELECT

                received_date,

                amount_received,

                note

            FROM received_entries

            WHERE

                business_id = ?

                AND received_date >= ?

                AND received_date <= ?

            ORDER BY

                received_date ASC,

                id ASC

        """, (
            business_id,

            start_date,

            end_date

        )).fetchall()


        total_bill = sum(
            float(
                row["bill_amount"] or 0
            )
            for row in bill_entries
        )


        total_received = sum(
            float(
                row["amount_received"] or 0
            )
            for row in received_entries
        )


        total_with_close = (
            total_bill
            + close_amount
        )


        net_amount = (
            total_with_close
            - total_received
        )


        story.append(
            PageBreak()
        )


        story.append(
            Paragraph(
                str(name),
                name_style
            )
        )


        story.append(
            Spacer(
                1,
                5
            )
        )


        story.append(
            Paragraph(
                financial_year_to_label(
                    selected_year
                ),
                section_heading
            )
        )


        story.append(
            Spacer(
                1,
                15
            )
        )


        # -------------------------------------------------
        # BILL TABLE
        # -------------------------------------------------

        story.append(
            Paragraph(
                "Bill Entries",
                section_heading
            )
        )


        story.append(
            Spacer(
                1,
                6
            )
        )


        bill_data = [
            [
                "No.",
                "Date",
                "Bill Amount"
            ]
        ]


        for index, entry in enumerate(
            bill_entries,
            start=1
        ):

            bill_data.append([
                str(index),

                format_date_dmy(
                    entry["entry_date"]
                ),

                f"Rs. {float(entry['bill_amount']):,.2f}"
            ])


        if len(bill_data) == 1:

            bill_data.append([
                "-",
                "-",
                "Rs. 0.00"
            ])


        bill_table = Table(
            bill_data,

            colWidths=[
                55,
                150,
                200
            ],

            repeatRows=1
        )


        bill_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#667eea"
                    )
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                )

            ])
        )


        story.append(
            bill_table
        )


        story.append(
            Spacer(
                1,
                18
            )
        )


        # -------------------------------------------------
        # RECEIVED TABLE
        # -------------------------------------------------

        story.append(
            Paragraph(
                "Amount Received",
                section_heading
            )
        )


        story.append(
            Spacer(
                1,
                6
            )
        )


        received_data = [
            [
                "No.",
                "Date",
                "Amount Received",
                "Note"
            ]
        ]


        for index, item in enumerate(
            received_entries,
            start=1
        ):

            received_data.append([
                str(index),

                format_date_dmy(
                    item["received_date"]
                ),

                f"Rs. {float(item['amount_received']):,.2f}",

                str(item["note"] or "")
            ])


        if len(received_data) == 1:

            received_data.append([
                "-",
                "-",
                "Rs. 0.00",
                "-"
            ])


        received_table = Table(
            received_data,

            colWidths=[
                40,
                110,
                130,
                125
            ],

            repeatRows=1
        )


        received_table.setStyle(
            TableStyle([

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, 0),
                    colors.HexColor(
                        "#10b981"
                    )
                ),

                (
                    "TEXTCOLOR",
                    (0, 0),
                    (-1, 0),
                    colors.white
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (-1, 0),
                    "Helvetica-Bold"
                ),

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "ALIGN",
                    (0, 0),
                    (-1, -1),
                    "CENTER"
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    7
                )

            ])
        )


        story.append(
            received_table
        )


        story.append(
            Spacer(
                1,
                18
            )
        )


        # -------------------------------------------------
        # SUMMARY
        # -------------------------------------------------

        summary_data = [

            [
                "Total Bill Amount",
                f"Rs. {total_bill:,.2f}"
            ],

            [
                "Close Amount",
                f"Rs. {close_amount:,.2f}"
            ],

            [
                "Total Bill + Close Amount",
                f"Rs. {total_with_close:,.2f}"
            ],

            [
                "Total Amount Received",
                f"Rs. {total_received:,.2f}"
            ],

            [
                "Net Amount",
                f"Rs. {net_amount:,.2f}"
            ]

        ]


        summary_table = Table(
            summary_data,

            colWidths=[
                260,
                195
            ]
        )


        summary_table.setStyle(
            TableStyle([

                (
                    "GRID",
                    (0, 0),
                    (-1, -1),
                    0.5,
                    colors.grey
                ),

                (
                    "FONTNAME",
                    (0, 0),
                    (0, -1),
                    "Helvetica-Bold"
                ),

                (
                    "ALIGN",
                    (1, 0),
                    (1, -1),
                    "RIGHT"
                ),

                (
                    "BACKGROUND",
                    (0, 0),
                    (-1, -1),
                    colors.HexColor(
                        "#f5f7fb"
                    )
                ),

                (
                    "TOPPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                ),

                (
                    "BOTTOMPADDING",
                    (0, 0),
                    (-1, -1),
                    8
                )

            ])
        )


        story.append(
            summary_table
        )


    conn.close()


    document.build(
        story
    )


    buffer.seek(0)


    filename = (
        "Business_Manager_" +
        selected_year +
        ".pdf"
    )


    return (
        buffer,
        filename
    )


# =========================================================
# VIEW ALL PDF
# =========================================================

@app.route(
    "/view-all"
)
def view_all():

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    selected_year = request.args.get(
        "year",
        get_current_financial_year()
    ).strip()

    try:
        buffer, filename = create_all_business_pdf(
            selected_year
        )
    except Exception:
        return (
            "Unable to create PDF.",
            500
        )

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
                (
                    "inline; "
                    f'filename="{filename}"'
                ),
            "Content-Length":
                str(len(buffer.getvalue())),
            "Cache-Control":
                "no-cache"
        }
    )


# =========================================================
# SAVE ALL PDF
# =========================================================

@app.route(
    "/save-all"
)
def save_all():

    if not session.get("logged_in"):

        return redirect(
            url_for("login")
        )


    selected_year = request.args.get(
        "year",
        get_current_financial_year()
    ).strip()


    try:

        buffer, filename = (
            create_all_business_pdf(
                selected_year
            )
        )

    except Exception as error:

        print(
            "SAVE ALL PDF ERROR:",
            error
        )

        return (
            "Unable to create PDF.",
            500
        )


    return Response(

        buffer.getvalue(),

        mimetype="application/pdf",

        headers={

            "Content-Type":
                "application/pdf",

            "Content-Disposition":
                (
                    "attachment; "
                    f'filename="{filename}"'
                ),

            "Content-Length":
                str(
                    len(
                        buffer.getvalue()
                    )
                ),

            "Cache-Control":
                "no-cache"

        }

    )


# =========================================================
# SINGLE SAVE
# =========================================================

@app.route(
    "/save-file/<int:business_id>"
)
def save_file(business_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    selected_year = request.args.get(
        "year",
        get_current_financial_year()
    ).strip()

    try:
        buffer, filename = create_single_business_pdf(
            business_id,
            selected_year
        )
    except Exception:
        return (
            "Unable to create PDF.",
            500
        )

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
                (
                    "attachment; "
                    f'filename="{filename}"'
                ),
            "Content-Length":
                str(len(buffer.getvalue())),
            "Cache-Control":
                "no-cache"
        }
    )


# =========================================================
# SINGLE PDF GENERATOR
# =========================================================

def create_single_business_pdf(
    business_id,
    selected_year
):
    start_date, end_date = get_financial_year_range(
        selected_year
    )

    conn = get_db()

    business = conn.execute("""
        SELECT id, name
        FROM businesses
        WHERE id = ?
          AND is_deleted = 0
    """, (business_id,)).fetchone()

    if not business:
        conn.close()
        raise ValueError("Business not found.")

    bills = conn.execute("""
        SELECT entry_date, bill_amount
        FROM entries
        WHERE business_id = ?
          AND entry_date >= ?
          AND entry_date <= ?
        ORDER BY entry_date ASC, id ASC
    """, (
        business_id,
        start_date,
        end_date
    )).fetchall()

    received = conn.execute("""
        SELECT received_date, amount_received, note
        FROM received_entries
        WHERE business_id = ?
          AND received_date >= ?
          AND received_date <= ?
        ORDER BY received_date ASC, id ASC
    """, (
        business_id,
        start_date,
        end_date
    )).fetchall()

    year_row = conn.execute("""
        SELECT close_amount
        FROM business_years
        WHERE business_id = ?
          AND financial_year = ?
    """, (
        business_id,
        selected_year
    )).fetchone()

    conn.close()

    close_amount = float(
        year_row["close_amount"]
        if year_row else 0
    )

    total_bill = sum(
        float(row["bill_amount"] or 0)
        for row in bills
    )

    total_received = sum(
        float(row["amount_received"] or 0)
        for row in received
    )

    total_with_close = (
        total_bill + close_amount
    )

    net_amount = (
        total_with_close - total_received
    )

    buffer = io.BytesIO()

    document = SimpleDocTemplate(
        buffer,
        pagesize=A4,
        rightMargin=55,
        leftMargin=55,
        topMargin=42,
        bottomMargin=42
    )

    styles = getSampleStyleSheet()

    name_style = styles["Heading2"]
    name_style.alignment = TA_CENTER
    name_style.fontSize = 15
    name_style.leading = 18

    year_style = styles["Heading3"]
    year_style.fontSize = 10
    year_style.leading = 13

    section_style = styles["Heading3"]
    section_style.fontSize = 10
    section_style.leading = 13
    section_style.spaceAfter = 4

    story = [
        Paragraph(
            str(business["name"]),
            name_style
        ),
        Spacer(1, 5),
        Paragraph(
            financial_year_to_label(selected_year),
            year_style
        ),
        Spacer(1, 14),
        Paragraph(
            "Bill Entries",
            section_style
        ),
        Spacer(1, 5)
    ]

    bill_data = [
        ["No.", "Date", "Bill Amount"]
    ]

    for index, row in enumerate(
        bills,
        start=1
    ):
        bill_data.append([
            str(index),
            format_date_dmy(row["entry_date"]),
            f"Rs. {float(row['bill_amount'] or 0):,.2f}"
        ])

    if len(bill_data) == 1:
        bill_data.append([
            "-",
            "-",
            "Rs. 0.00"
        ])

    bill_table = Table(
        bill_data,
        colWidths=[55, 150, 205],
        repeatRows=1
    )

    bill_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#667eea")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(bill_table)
    story.append(Spacer(1, 18))

    story.append(
        Paragraph(
            "Amount Received",
            section_style
        )
    )
    story.append(Spacer(1, 5))

    received_data = [
        ["No.", "Date", "Amount Received", "Note"]
    ]

    for index, row in enumerate(
        received,
        start=1
    ):
        received_data.append([
            str(index),
            format_date_dmy(row["received_date"]),
            f"Rs. {float(row['amount_received'] or 0):,.2f}",
            str(row["note"] or "")
        ])

    if len(received_data) == 1:
        received_data.append([
            "-",
            "-",
            "Rs. 0.00",
            "-"
        ])

    received_table = Table(
        received_data,
        colWidths=[40, 110, 130, 130],
        repeatRows=1
    )

    received_table.setStyle(
        TableStyle([
            (
                "BACKGROUND",
                (0, 0),
                (-1, 0),
                colors.HexColor("#10b981")
            ),
            (
                "TEXTCOLOR",
                (0, 0),
                (-1, 0),
                colors.white
            ),
            (
                "FONTNAME",
                (0, 0),
                (-1, 0),
                "Helvetica-Bold"
            ),
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "ALIGN",
                (0, 0),
                (-1, -1),
                "CENTER"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                6
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                6
            )
        ])
    )

    story.append(received_table)
    story.append(Spacer(1, 18))

    summary = [
        [
            "Total Bill Amount",
            f"Rs. {total_bill:,.2f}"
        ],
        [
            "Close Amount",
            f"Rs. {close_amount:,.2f}"
        ],
        [
            "Total Bill + Close Amount",
            f"Rs. {total_with_close:,.2f}"
        ],
        [
            "Total Amount Received",
            f"Rs. {total_received:,.2f}"
        ],
        [
            "Net Amount",
            f"Rs. {net_amount:,.2f}"
        ]
    ]

    summary_table = Table(
        summary,
        colWidths=[265, 145]
    )

    summary_table.setStyle(
        TableStyle([
            (
                "GRID",
                (0, 0),
                (-1, -1),
                0.5,
                colors.grey
            ),
            (
                "FONTNAME",
                (0, 0),
                (0, -1),
                "Helvetica-Bold"
            ),
            (
                "ALIGN",
                (1, 0),
                (1, -1),
                "RIGHT"
            ),
            (
                "TOPPADDING",
                (0, 0),
                (-1, -1),
                7
            ),
            (
                "BOTTOMPADDING",
                (0, 0),
                (-1, -1),
                7
            )
        ])
    )

    story.append(summary_table)

    document.build(story)

    buffer.seek(0)

    safe_name = (
        str(business["name"])
        .replace(" ", "_")
        .replace("/", "_")
        .replace("\\", "_")
    )

    filename = (
        safe_name +
        "_" +
        selected_year +
        ".pdf"
    )

    return buffer, filename


# =========================================================
# VIEW FILE
# =========================================================

@app.route(
    "/view-file/<int:business_id>"
)
def view_file(business_id):

    if not session.get("logged_in"):
        return redirect(
            url_for("login")
        )

    selected_year = request.args.get(
        "year",
        get_current_financial_year()
    ).strip()

    try:
        buffer, filename = create_single_business_pdf(
            business_id,
            selected_year
        )
    except Exception:
        return (
            "Unable to create PDF.",
            500
        )

    return Response(
        buffer.getvalue(),
        mimetype="application/pdf",
        headers={
            "Content-Disposition":
                (
                    "inline; "
                    f'filename="{filename}"'
                ),
            "Content-Length":
                str(len(buffer.getvalue())),
            "Cache-Control":
                "no-cache"
        }
    )


# =========================================================
# SHARE FILE
# =========================================================

@app.route(
    "/share-file/<int:business_id>"
)
def share_file(business_id):

    if not session.get("logged_in"):

        return jsonify({
            "success": False,
            "message":
                "Please login first."
        }), 401


    response = save_file(
        business_id
    )


    return response


# =========================================================
# LOGOUT
# =========================================================

@app.route("/logout")
def logout():

    session.clear()

    return redirect(
        url_for("login")
    )


# =========================================================
# START
# =========================================================

if __name__ == "__main__":

    init_db()

    ensure_recovery_tables()

    app.run(
        debug=True,
        host="127.0.0.1",
        port=5000
    )