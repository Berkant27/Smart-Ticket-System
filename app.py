from flask import Flask, render_template, request, redirect, url_for, session, flash
import sqlite3
from utils import hash_password, verify_password
import os

app = Flask(__name__)
app.secret_key = "gizli_anahtar"  # Üretimde .env dosyasından alınmalı

DATABASE = "database.db"

def get_db_connection():
    conn = sqlite3.connect(DATABASE)
    conn.row_factory = sqlite3.Row
    return conn

@app.before_request
def ensure_db_exists():
    if not os.path.exists(DATABASE):
        from init_db import init_db
        init_db()

@app.route("/")
def index():
    conn = get_db_connection()
    tickets = conn.execute("""
        SELECT tickets.*, users.email
        FROM tickets
        JOIN users ON tickets.user_id = users.id
        ORDER BY created_at DESC
    """).fetchall()
    conn.close()
    return render_template("index.html", tickets=tickets)

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        existing_users = conn.execute("SELECT id FROM users").fetchall()
        is_admin = 1 if len(existing_users) == 0 else 0  # İlk kullanıcı admin olur

        try:
            conn.execute(
                "INSERT INTO users (email, password, is_admin) VALUES (?, ?, ?)",
                (email, hash_password(password), is_admin)
            )
            conn.commit()
            flash("Kayıt başarılı. Giriş yapabilirsiniz.", "success")
            if is_admin:
                flash("Bu hesap ilk kayıt olduğu için admin olarak atandı.", "info")
            return redirect(url_for("login"))
        except sqlite3.IntegrityError:
            flash("Bu e-posta zaten kayıtlı.", "danger")
        finally:
            conn.close()

    return render_template("register.html")

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        password = request.form["password"]

        conn = get_db_connection()
        user = conn.execute("SELECT * FROM users WHERE email = ?", (email,)).fetchone()
        conn.close()

        if user and verify_password(password, user["password"]):
            session["user_id"] = user["id"]
            session["user_email"] = user["email"]
            session["is_admin"] = user["is_admin"]
            flash("Giriş başarılı.", "success")
            return redirect(url_for("index"))
        else:
            flash("E-posta veya şifre yanlış.", "danger")

    return render_template("login.html")

@app.route("/logout")
def logout():
    session.clear()
    flash("Çıkış yapıldı.", "info")
    return redirect(url_for("login"))

@app.route("/add", methods=["GET", "POST"])
def add_ticket():
    if "user_id" not in session:
        flash("Lütfen giriş yapın.", "warning")
        return redirect(url_for("login"))

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form.get("category")
        budget = request.form.get("budget")
        priority = request.form.get("priority")

        conn = get_db_connection()
        conn.execute("""
            INSERT INTO tickets (user_id, title, description, category, budget, priority)
            VALUES (?, ?, ?, ?, ?, ?)
        """, (session["user_id"], title, description, category, budget, priority))
        conn.commit()
        conn.close()

        flash("Ticket oluşturuldu.", "success")
        return redirect(url_for("index"))

    categories = ["Yazılım", "Donanım", "Genel", "Diğer"]
    priorities = ["Düşük", "Orta", "Yüksek"]
    return render_template("add_ticket.html", categories=categories, priorities=priorities)

@app.route("/update/<int:ticket_id>", methods=["GET", "POST"])
def update_ticket(ticket_id):
    if not session.get("is_admin"):
        flash("Bu işlem sadece adminlere açıktır.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    ticket = conn.execute("SELECT * FROM tickets WHERE id = ?", (ticket_id,)).fetchone()

    if request.method == "POST":
        title = request.form["title"]
        description = request.form["description"]
        category = request.form.get("category")
        budget = request.form.get("budget")
        priority = request.form.get("priority")
        status = request.form.get("status")

        conn.execute("""
            UPDATE tickets
            SET title = ?, description = ?, category = ?, budget = ?, priority = ?, status = ?
            WHERE id = ?
        """, (title, description, category, budget, priority, status, ticket_id))
        conn.commit()
        conn.close()

        flash("Ticket güncellendi.", "success")
        return redirect(url_for("index"))

    categories = ["Yazılım", "Donanım", "Genel", "Diğer"]
    priorities = ["Düşük", "Orta", "Yüksek"]
    statuses = ["Open", "In Progress", "Closed"]
    conn.close()

    return render_template("update_ticket.html", ticket=ticket, categories=categories, priorities=priorities, statuses=statuses)

@app.route("/delete/<int:ticket_id>", methods=["POST"])
def delete_ticket(ticket_id):
    if not session.get("is_admin"):
        flash("Bu işlem sadece adminlere açıktır.", "danger")
        return redirect(url_for("index"))

    conn = get_db_connection()
    conn.execute("DELETE FROM tickets WHERE id = ?", (ticket_id,))
    conn.commit()
    conn.close()

    flash("Ticket silindi.", "info")
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(debug=True)
