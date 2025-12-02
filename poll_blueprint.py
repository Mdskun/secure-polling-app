from flask import Blueprint, render_template, request, redirect, url_for, abort, make_response
from flask_login import current_user
from models import Poll, PollOption, Vote, db
from utils import encrypt_vote, append_ledger_entry
from datetime import datetime

polls = Blueprint("polls", __name__)

@polls.route("/poll/<int:poll_id>")
def poll_detail(poll_id):
    poll = Poll.query.get_or_404(poll_id)
    # Determine voting status and user-voted flag
    user_voted = False
    if current_user.is_authenticated:
        user_voted = Vote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first() is not None
    else:
        # Check anonymous cookie
        user_voted = request.cookies.get(f"poll_{poll_id}_voted") is not None

    return render_template("poll_detail.html", poll=poll, user_voted=user_voted, now_utc=datetime.utcnow())

@polls.route("/vote/<int:poll_id>", methods=["POST"])
def vote(poll_id):
    poll = Poll.query.get_or_404(poll_id)

    now = datetime.utcnow()
    if poll.start_time and now < poll.start_time:
        return "Poll has not started yet.", 403
    if poll.end_time and now > poll.end_time:
        return "Poll has already ended.", 403
    
    option_id = request.form.get("option")
    option = PollOption.query.filter_by(id=option_id, poll_id=poll_id).first()
    if not option:
        abort(400)
        
     # Check if user already voted (if logged in)
    if current_user.is_authenticated:
        existing_vote = Vote.query.filter_by(poll_id=poll_id, user_id=current_user.id).first()
        if existing_vote:
            return "❌ You have already voted in this poll!"

    # If user isn't logged in, prevent per-IP or per-cookie cheating
    if not current_user.is_authenticated:
        if request.cookies.get(f"poll_{poll_id}_voted"):
            return "❌ Anonymous users can only vote once!"
        
    # Ip-chekking
    user_ip = request.remote_addr
    existing_ip_vote = Vote.query.filter_by(poll_id=poll_id, ip_address=user_ip).first()
    if existing_ip_vote and not current_user.is_authenticated:
        return "❌ You already voted!"
    
    option = PollOption.query.filter_by(id=option_id, poll_id=poll_id).first_or_404()

    encrypted = encrypt_vote(str(option.id))
    vote = Vote(poll_id=poll.id, option_id=option.id, encrypted_vote=encrypted)
    if current_user.is_authenticated:
        vote.user_id = current_user.id
        ip_addr = request.remote_addr
        vote.ip_address = ip_addr
    else:
        ip_addr = request.remote_addr
        vote.ip_address = ip_addr

    db.session.add(vote)
    db.session.commit()

    # Append to ledger for audit trail
    append_ledger_entry(encrypted_vote=encrypted,
                        poll_id=poll.id,
                        option_id=option.id,
                        user_id=(current_user.id if current_user.is_authenticated else None),
                        ip_address=ip_addr)

    # Set cookie for anonymous users to prevent re-vote from same browser
    response = make_response(redirect(url_for("polls.poll_detail", poll_id=poll_id)))
    if not current_user.is_authenticated:
        response.set_cookie(f"poll_{poll_id}_voted", "true", max_age=60*60*24*7)
    return redirect(url_for("polls.poll_detail", poll_id=poll_id))
