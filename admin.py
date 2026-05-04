from flask import Blueprint, render_template, request, redirect, url_for, send_file, flash, current_app
from flask_login import login_required, current_user
from models import Poll, PollOption, db
from utils import verify_ledger, LEDGER_PATH, decrypt_vote
from datetime import datetime
from markupsafe import escape
import os
import io
import csv
import logging

admin = Blueprint("admin", __name__)
logger = logging.getLogger(__name__)

# Validation constants
POLL_QUESTION_MIN_LENGTH = 5
POLL_QUESTION_MAX_LENGTH = 300
POLL_OPTION_MIN_LENGTH = 1
POLL_OPTION_MAX_LENGTH = 200
MIN_OPTIONS = 2
MAX_OPTIONS = 10

def admin_only(func):
    """Decorator to ensure user is authenticated and is an admin."""
    def wrapper(*args, **kwargs):
        if not current_user.is_authenticated or not current_user.is_admin:
            flash("Admin access required.", "error")
            return redirect(url_for("index")), 403
        return func(*args, **kwargs)
    wrapper.__name__ = func.__name__
    return wrapper

def validate_poll_question(question):
    """
    Validate poll question.
    Returns (is_valid, error_message)
    """
    question = question.strip() if question else ""
    if not question or len(question) < POLL_QUESTION_MIN_LENGTH:
        return False, f"Question must be at least {POLL_QUESTION_MIN_LENGTH} characters"
    if len(question) > POLL_QUESTION_MAX_LENGTH:
        return False, f"Question must be less than {POLL_QUESTION_MAX_LENGTH} characters"
    return True, None

def validate_poll_options(options):
    """
    Validate poll options list.
    Returns (is_valid, error_message, cleaned_options)
    """
    # Filter empty options and clean them
    cleaned = [escape(opt.strip()) for opt in options if opt.strip()]
    
    if len(cleaned) < MIN_OPTIONS:
        return False, f"Poll must have at least {MIN_OPTIONS} options", []
    if len(cleaned) > MAX_OPTIONS:
        return False, f"Poll can have at most {MAX_OPTIONS} options", []
    
    for opt in cleaned:
        if len(opt) < POLL_OPTION_MIN_LENGTH or len(opt) > POLL_OPTION_MAX_LENGTH:
            return False, f"Each option must be between {POLL_OPTION_MIN_LENGTH} and {POLL_OPTION_MAX_LENGTH} characters", []
    
    return True, None, cleaned

def validate_poll_times(start_time_raw, end_time_raw):
    """
    Validate and parse poll start/end times.
    Returns (is_valid, error_message, start_time, end_time)
    """
    start_time = None
    end_time = None
    
    try:
        if start_time_raw:
            start_time = datetime.fromisoformat(start_time_raw)
        if end_time_raw:
            end_time = datetime.fromisoformat(end_time_raw)
        
        # If both times provided, validate end is after start
        if start_time and end_time and end_time <= start_time:
            return False, "End time must be after start time", None, None
        
        return True, None, start_time, end_time
    except ValueError as e:
        return False, "Invalid datetime format", None, None

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
        question = request.form.get("question", "").strip()
        options = request.form.getlist("options")
        start_time_raw = request.form.get("start_time")
        end_time_raw = request.form.get("end_time")
        
        # Validate question
        valid, error_msg = validate_poll_question(question)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.new_poll")), 400
        
        # Validate options
        valid, error_msg, cleaned_options = validate_poll_options(options)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.new_poll")), 400
        
        # Validate times
        valid, error_msg, start_time, end_time = validate_poll_times(start_time_raw, end_time_raw)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.new_poll")), 400
        
        # Create poll
        poll = Poll(question=escape(question), start_time=start_time, end_time=end_time)
        db.session.add(poll)
        db.session.flush()
        
        # Add options
        for text in cleaned_options:
            db.session.add(PollOption(poll_id=poll.id, text=text))
        
        db.session.commit()
        flash(f"Poll '{question}' created successfully!", "success")
        return redirect(url_for("admin.dashboard"))
    
    return render_template("admin_edit_poll.html", poll=None)

@admin.route("/admin/edit_poll/<int:poll_id>", methods=["GET", "POST"])
@login_required
@admin_only
def edit_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    
    if request.method == "POST":
        question = request.form.get("question", "").strip()
        options = request.form.getlist("options")
        start_time_raw = request.form.get("start_time")
        end_time_raw = request.form.get("end_time")
        
        # Validate question
        valid, error_msg = validate_poll_question(question)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.edit_poll", poll_id=poll_id)), 400
        
        # Validate options
        valid, error_msg, cleaned_options = validate_poll_options(options)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.edit_poll", poll_id=poll_id)), 400
        
        # Validate times
        valid, error_msg, start_time, end_time = validate_poll_times(start_time_raw, end_time_raw)
        if not valid:
            flash(error_msg, "error")
            return redirect(url_for("admin.edit_poll", poll_id=poll_id)), 400
        
        # Update poll
        poll.question = escape(question)
        poll.start_time = start_time
        poll.end_time = end_time
        
        # Update options
        existing_options = poll.options
        for i, text in enumerate(cleaned_options):
            if i < len(existing_options):
                existing_options[i].text = text
            else:
                poll.options.append(PollOption(poll_id=poll.id, text=text))
        
        # Remove extra options
        while len(existing_options) > len(cleaned_options):
            db.session.delete(existing_options[-1])
        
        db.session.commit()
        flash(f"Poll updated successfully!", "success")
        return redirect(url_for("admin.dashboard"))
    
    return render_template("admin_edit_poll.html", poll=poll)

@admin.route("/admin/delete/<int:poll_id>")
@login_required
@admin_only
def delete_poll(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    question = poll.question
    db.session.delete(poll)
    db.session.commit()
    flash(f"Poll '{question}' deleted successfully!", "success")
    return redirect(url_for("admin.dashboard"))

@admin.route("/admin/export_poll/<int:poll_id>")
@login_required
@admin_only
def export_poll(poll_id):
    """Export poll results to CSV (admin only)."""
    poll = Poll.query.get_or_404(poll_id)
    output = io.StringIO()
    writer = csv.writer(output)
    writer.writerow(["Option", "Vote Count", "Voter ID (if any)"])
    
    for option in poll.options:
        vote_count = len(option.votes)
        for vote in option.votes:
            voter_id = vote.user_id if vote.user_id else "Anonymous"
            writer.writerow([option.text, vote_count, voter_id])
    
    output.seek(0)
    return send_file(
        io.BytesIO(output.getvalue().encode()),
        mimetype="text/csv",
        as_attachment=True,
        download_name=f"poll_{poll.id}_results.csv"
    )

@admin.route("/admin/ledger/download")
@login_required
@admin_only
def download_ledger():
    """Download the vote ledger (admin only)."""
    if not os.path.exists(LEDGER_PATH):
        flash("Ledger not found.", "error")
        return redirect(url_for("admin.dashboard")), 404
    
    return send_file(LEDGER_PATH, as_attachment=True, download_name="ledger.jsonl")

@admin.route("/admin/ledger_verify")
@login_required
@admin_only
def verify_ledger_route():
    """Verify the integrity of the vote ledger (admin only)."""
    try:
        ok, reason = verify_ledger()
        if ok:
            flash("✅ Ledger integrity verified successfully!", "success")
            return redirect(url_for("admin.dashboard")), 200
        else:
            # Log the error internally, show generic message to user
            logger.error(f"Ledger verification failed: {reason}")
            flash("❌ Ledger integrity check failed. Please contact support.", "error")
            return redirect(url_for("admin.dashboard")), 500
    except Exception as e:
        logger.error(f"Error verifying ledger: {str(e)}")
        flash("❌ An error occurred while verifying the ledger.", "error")
        return redirect(url_for("admin.dashboard")), 500
