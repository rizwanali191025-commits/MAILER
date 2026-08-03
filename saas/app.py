"""Flask application factory for the multi-tenant SaaS mailer.

Run with ``python run_saas.py`` (repo root) or ``flask --app saas.app run``.
Routes are grouped as: marketing (public), auth, dashboard/campaigns, billing.
"""

from __future__ import annotations

import os
from pathlib import Path

from flask import (
    Flask, flash, g, jsonify, redirect, render_template, request, session, url_for
)

from saas import auth, db, models
from saas.plans import get_plan, ordered_plans, PLANS
from saas.sending import QuotaExceeded, render_preview, send_campaign


def create_app(database: str | None = None) -> Flask:
    app = Flask(__name__, template_folder="templates", static_folder="static")
    app.config["SECRET_KEY"] = os.environ.get("SAAS_SECRET_KEY", "dev-saas-key-change-me")
    app.config["DATABASE"] = database or os.environ.get(
        "SAAS_DATABASE", str(Path(__file__).resolve().parent.parent / "data" / "saas.db")
    )

    db.init_app(app)

    @app.context_processor
    def inject_globals():
        user = auth.current_user()
        ctx = {"current_user": user, "plans": ordered_plans()}
        if user is not None:
            plan = get_plan(user["plan_id"])
            used = models.sends_this_month(user["id"])
            ctx.update(
                user_plan=plan,
                usage_used=used,
                usage_limit=plan.monthly_send_limit,
                usage_pct=min(100, round(used / plan.monthly_send_limit * 100)) if plan.monthly_send_limit else 0,
            )
        return ctx

    # ── marketing ────────────────────────────────────────────────────────────
    @app.route("/")
    def landing():
        if auth.current_user():
            return redirect(url_for("dashboard"))
        return render_template("landing.html")

    @app.route("/pricing")
    def pricing():
        return render_template("pricing.html")

    # ── auth ──────────────────────────────────────────────────────────────────
    @app.route("/signup", methods=["GET", "POST"])
    def signup():
        if request.method == "POST":
            email = request.form.get("email", "").strip().lower()
            password = request.form.get("password", "")
            if not auth.valid_email(email):
                flash("Please enter a valid email address.", "error")
            elif len(password) < 8:
                flash("Password must be at least 8 characters.", "error")
            elif models.get_user_by_email(email):
                flash("An account with that email already exists.", "error")
            else:
                uid = models.create_user(email, password)
                auth.login_user(uid)
                flash("Welcome aboard! Your account is on the Free plan.", "success")
                return redirect(url_for("dashboard"))
        return render_template("signup.html")

    @app.route("/login", methods=["GET", "POST"])
    def login():
        if request.method == "POST":
            email = request.form.get("email", "")
            password = request.form.get("password", "")
            user = models.verify_credentials(email, password)
            if user:
                auth.login_user(user["id"])
                return redirect(url_for("dashboard"))
            flash("Invalid email or password.", "error")
        return render_template("login.html")

    @app.route("/logout")
    def logout():
        auth.logout_user()
        return redirect(url_for("landing"))

    # ── dashboard & campaigns ─────────────────────────────────────────────────
    @app.route("/dashboard")
    @auth.login_required
    def dashboard():
        user = auth.current_user()
        return render_template(
            "dashboard.html",
            campaigns=models.list_campaigns(user["id"]),
            events=models.recent_send_events(user["id"], limit=15),
            can_create=models.can_create_campaign(user),
        )

    @app.route("/settings", methods=["POST"])
    @auth.login_required
    def settings():
        user = auth.current_user()
        models.update_sender_settings(
            user["id"],
            request.form.get("sender_email", ""),
            request.form.get("sender_names", ""),
        )
        flash("Sender settings saved.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/campaigns/new", methods=["POST"])
    @auth.login_required
    def campaign_new():
        user = auth.current_user()
        if not models.can_create_campaign(user):
            plan = get_plan(user["plan_id"])
            flash(f"Your {plan.name} plan allows {plan.campaign_limit_label()} "
                  f"campaigns. Upgrade for more.", "error")
            return redirect(url_for("pricing"))
        cid = models.create_campaign(user["id"], request.form.get("name", ""))
        return redirect(url_for("campaign_edit", campaign_id=cid))

    @app.route("/campaigns/<int:campaign_id>", methods=["GET", "POST"])
    @auth.login_required
    def campaign_edit(campaign_id):
        user = auth.current_user()
        campaign = models.get_campaign(user["id"], campaign_id)
        if campaign is None:
            flash("Campaign not found.", "error")
            return redirect(url_for("dashboard"))

        if request.method == "POST":
            models.update_campaign(
                user["id"], campaign_id,
                name=request.form.get("name", ""),
                subject_tmpl=request.form.get("subject_tmpl", ""),
                body_tmpl=request.form.get("body_tmpl", ""),
                recipients_csv=request.form.get("recipients_csv", ""),
                attach_pptx=request.form.get("attach_pptx") == "on",
            )
            flash("Campaign saved.", "success")
            return redirect(url_for("campaign_edit", campaign_id=campaign_id))

        return render_template("campaign_edit.html", campaign=campaign)

    @app.route("/campaigns/<int:campaign_id>/delete", methods=["POST"])
    @auth.login_required
    def campaign_delete(campaign_id):
        user = auth.current_user()
        models.delete_campaign(user["id"], campaign_id)
        flash("Campaign deleted.", "success")
        return redirect(url_for("dashboard"))

    @app.route("/campaigns/<int:campaign_id>/preview", methods=["POST"])
    @auth.login_required
    def campaign_preview(campaign_id):
        user = auth.current_user()
        # preview from the (possibly unsaved) form values, falling back to stored
        stored = models.get_campaign(user["id"], campaign_id)
        if stored is None:
            return jsonify({"error": "Campaign not found."}), 404
        draft = dict(stored)
        draft["subject_tmpl"] = request.form.get("subject_tmpl", stored["subject_tmpl"])
        draft["body_tmpl"] = request.form.get("body_tmpl", stored["body_tmpl"])
        draft["recipients_csv"] = request.form.get("recipients_csv", stored["recipients_csv"])
        result = render_preview(draft, user, int(request.form.get("index", 1)))
        code = 400 if "error" in result else 200
        return jsonify(result), code

    @app.route("/campaigns/<int:campaign_id>/send", methods=["POST"])
    @auth.login_required
    def campaign_send(campaign_id):
        user = auth.current_user()
        campaign = models.get_campaign(user["id"], campaign_id)
        if campaign is None:
            return jsonify({"error": "Campaign not found."}), 404

        dry_run = request.form.get("dry_run") == "1"
        remaining = models.remaining_quota(user)
        try:
            results = send_campaign(
                campaign, user, dry_run=dry_run, remaining_quota=remaining
            )
        except QuotaExceeded as e:
            return jsonify({"error": str(e), "quota": True}), 402

        if not results:
            return jsonify({"error": "No valid recipients (need an 'email' column)."}), 400

        models.record_send_events(user["id"], campaign_id, results)
        sent = sum(1 for r in results if r["status"] == "sent")
        simulated = sum(1 for r in results if r["status"] == "dry_run")
        errors = sum(1 for r in results if r["status"] == "error")
        return jsonify({
            "ok": True,
            "sent": sent,
            "dry_run": simulated,
            "errors": errors,
            "total": len(results),
            "remaining": models.remaining_quota(user),
            "results": results[:100],
        })

    # ── billing ───────────────────────────────────────────────────────────────
    @app.route("/billing")
    @auth.login_required
    def billing():
        return render_template("billing.html")

    @app.route("/billing/change", methods=["POST"])
    @auth.login_required
    def billing_change():
        user = auth.current_user()
        plan_id = request.form.get("plan_id", "")
        if plan_id not in PLANS:
            flash("Unknown plan.", "error")
            return redirect(url_for("pricing"))
        models.update_user_plan(user["id"], plan_id)
        plan = get_plan(plan_id)
        # In production this is where Stripe Checkout would be invoked.
        if plan.is_free:
            flash("Switched to the Free plan.", "success")
        else:
            flash(f"You're now on {plan.name} — ${plan.price_monthly}/mo. "
                  f"(Demo mode: no card charged.)", "success")
        return redirect(url_for("dashboard"))

    return app
