from flask import Blueprint, render_template, request, redirect, url_for, send_file
from flask_login import login_required, current_user
from models import Poll, PollOption, db
from utils import verify_ledger, LEDGER_PATH,decrypt_vote
from datetime import datetime
import os
import io
import csv

admin = Blueprint("admin", __name__)

def admin_only(func):
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            return "Admins only!"
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

@admin.route("/admin/dashboard")
@login_required
@admin_only
def dashboard():
    polls = Poll.query.order_by(Poll.start_time.desc()).all()
    return render_template("admin_dashboard.html", polls=polls)


@admin.route("/admin/new_poll", methods=["GET", "POST"])
@login_required
@admin_only
def new_poll():
    if request.method == "POST":
        question = request.form["question"]
        options = request.form.getlist("options")
        # parse optional ISO datetime inputs (local HTML datetime-local -> treat as UTC)
        start_time_raw = request.form.get("start_time")
        end_time_raw = request.form.get("end_time")
        start_time = datetime.fromisoformat(start_time_raw) if start_time_raw else None
        end_time = datetime.fromisoformat(end_time_raw) if end_time_raw else None

        poll = Poll(question=question, start_time=start_time, end_time=end_time)
        db.session.add(poll)
        db.session.flush()
        for text in options:
            if text.strip():
                db.session.add(PollOption(poll_id=poll.id, text=text))
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_edit_poll.html", poll=None)

@admin.route("/admin/edit_poll/<int:poll_id>", methods=["GET","POST"])
@login_required
@admin_only
def edit_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    if request.method == "POST":
        poll.question = request.form["question"]
        start_time_raw = request.form.get("start_time")
        end_time_raw = request.form.get("end_time")
        poll.start_time = datetime.fromisoformat(start_time_raw) if start_time_raw else None
        poll.end_time = datetime.fromisoformat(end_time_raw) if end_time_raw else None

        # Update options
        new_options = request.form.getlist("options")
        existing_options = poll.options
        for i, text in enumerate(new_options):
            if i < len(existing_options):
                existing_options[i].text = text
            else:
                poll.options.append(PollOption(text=text))
        db.session.commit()
        return redirect(url_for("admin.dashboard"))
    return render_template("admin_edit_poll.html", poll=poll)

@admin.route("/admin/delete/<int:poll_id>")
@login_required
@admin_only
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    db.session.delete(poll)
    db.session.commit()
    return redirect(url_for("index"))

@admin.route("/admin/export_poll/<int:poll_id>")
@login_required
@admin_only
def export_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Option", "Vote Count", "Voter ID (if any)", "Encrypted Vote"])
    for option in poll.options:
        for vote in option.votes:
            decrypted_vote = decrypt_vote(vote.encrypted_vote)
            writer.writerow([option.text, len(option.votes), vote.user_id, decrypted_vote])
    output.seek(0)
    return send_file(io.BytesIO(output.getvalue().encode()), mimetype="text/csv",
                     as_attachment=True, download_name=f"poll_{poll.id}_results.csv")

@admin.route("/admin/ledger/download")
@login_required
@admin_only
def download_ledger():
    if not os.path.exists(LEDGER_PATH):
        return "Ledger not found.", 404
    return send_file(LEDGER_PATH, as_attachment=True)

@admin.route("/admin/ledger_verify")
@login_required
@admin_only
def verify_ledger_route():
    ok, reason = verify_ledger()
    if ok:
        return "Ledger OK — chain is valid."
    else:
        return f"Ledger verification FAILED: {reason}", 500
