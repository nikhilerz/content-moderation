from datetime import datetime, timedelta
import logging
from flask import Blueprint, render_template, request, redirect, url_for, flash, abort
from flask_login import login_required, current_user
from sqlalchemy import func, desc

from app import db
from models import Content, ModerationStatus, ContentFlag, ModerationAction, ModerationMetric, ModerationSetting
from moderation.utils import get_moderation_metrics
from moderation.processor import ContentProcessor

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
admin_bp = Blueprint('admin', __name__)

@admin_bp.route('/')
@admin_bp.route('/dashboard')
@login_required
def dashboard():
    """Admin dashboard with overview of moderation stats."""
    try:
        # Get statistics for the dashboard
        pending_count = ModerationStatus.query.filter_by(status='pending').count()
        approved_count = ModerationStatus.query.filter_by(status='approved').count()
        rejected_count = ModerationStatus.query.filter_by(status='rejected').count()
        
        # Get recent flagged content
        recent_flagged = db.session.query(Content, ModerationStatus)\
            .join(ModerationStatus)\
            .filter(ModerationStatus.status == 'pending')\
            .order_by(Content.created_at.desc())\
            .limit(10)\
            .all()
        
        # Get metrics for the past 7 days
        metrics = get_moderation_metrics(days=7)
        
        return render_template(
            'admin/dashboard.html',
            pending_count=pending_count,
            approved_count=approved_count,
            rejected_count=rejected_count,
            recent_flagged=recent_flagged,
            metrics=metrics
        )
    except Exception as e:
        logger.error(f"Error in dashboard route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return render_template('admin/dashboard.html', error=str(e))

@admin_bp.route('/flagged')
@login_required
def flagged_content():
    """List all flagged content for review."""
    try:
        page = request.args.get('page', 1, type=int)
        
        # Get filter parameters
        flag_type = request.args.get('flag_type')
        score_min = request.args.get('score_min', 0.0, type=float)
        
        # Build the query
        query = db.session.query(Content, ModerationStatus)\
            .join(ModerationStatus)\
            .filter(ModerationStatus.status == 'pending')
        
        # Apply filters
        if flag_type:
            content_ids = db.session.query(ContentFlag.content_id)\
                .filter(ContentFlag.flag_type == flag_type)\
                .subquery()
            query = query.filter(Content.id.in_(content_ids))
        
        if score_min > 0:
            query = query.filter(ModerationStatus.moderation_score >= score_min)
        
        # Get paginated results
        flagged_items = query.order_by(Content.created_at.desc()).paginate(
            page=page, per_page=20, error_out=False
        )
        
        # Get available flag types for the filter dropdown
        flag_types = db.session.query(ContentFlag.flag_type)\
            .distinct()\
            .order_by(ContentFlag.flag_type)\
            .all()
        flag_types = [f[0] for f in flag_types]
        
        # Current filters for display and pagination
        current_filters = {
            'flag_type': flag_type,
            'score_min': score_min
        }
        
        return render_template(
            'admin/flagged_content.html',
            flagged_content=flagged_items,
            flag_types=flag_types,
            current_filters=current_filters
        )
    except Exception as e:
        logger.error(f"Error in flagged_content route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return render_template('admin/flagged_content.html')

@admin_bp.route('/review/<int:content_id>')
@login_required
def review_content(content_id):
    """Review a specific piece of content."""
    try:
        content = Content.query.get_or_404(content_id)
        status = ModerationStatus.query.filter_by(content_id=content_id).first_or_404()
        flags = ContentFlag.query.filter_by(content_id=content_id).all()
        actions = ModerationAction.query.filter_by(content_id=content_id).order_by(ModerationAction.created_at.desc()).all()
        
        return render_template(
            'admin/review.html',
            content=content,
            status=status,
            flags=flags,
            actions=actions
        )
    except Exception as e:
        logger.error(f"Error in review_content route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('admin.flagged_content'))

@admin_bp.route('/update_status/<int:content_id>', methods=['POST'])
@login_required
def update_status(content_id):
    """Update the moderation status of content."""
    try:
        status = request.form.get('status')
        notes = request.form.get('notes', '')
        redirect_to = request.form.get('redirect_to', 'flagged')
        
        if status not in ['approved', 'rejected']:
            flash("Invalid status provided", "error")
            return redirect(url_for('admin.review_content', content_id=content_id))
        
        processor = ContentProcessor()
        result = processor.update_moderation_status(
            content_id=content_id,
            status=status,
            user_id=current_user.id,
            notes=notes
        )
        
        if result:
            flash(f"Content has been {status}", "success")
            if redirect_to == 'review':
                return redirect(url_for('admin.review_content', content_id=content_id))
            else:
                return redirect(url_for('admin.flagged_content'))
        else:
            flash("Failed to update status", "error")
            return redirect(url_for('admin.review_content', content_id=content_id))
    except Exception as e:
        logger.error(f"Error in update_status route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('admin.review_content', content_id=content_id))

@admin_bp.route('/batch_action', methods=['POST'])
@login_required
def batch_action():
    """Perform batch actions on multiple content items."""
    try:
        action = request.form.get('action')
        notes = request.form.get('notes', 'Batch action')
        content_ids = request.form.getlist('content_ids')
        
        if not content_ids:
            flash("No items selected", "warning")
            return redirect(url_for('admin.flagged_content'))
        
        if action not in ['approve', 'reject']:
            flash("Invalid action", "error")
            return redirect(url_for('admin.flagged_content'))
        
        processor = ContentProcessor()
        success_count = 0
        
        for content_id in content_ids:
            try:
                result = processor.update_moderation_status(
                    content_id=int(content_id),
                    status=f"{action}d", # approved or rejected
                    user_id=current_user.id,
                    notes=notes
                )
                if result:
                    success_count += 1
            except Exception as e:
                logger.error(f"Error processing content ID {content_id}: {str(e)}")
        
        flash(f"Successfully {action}d {success_count} of {len(content_ids)} items", "success")
        return redirect(url_for('admin.flagged_content'))
    except Exception as e:
        logger.error(f"Error in batch_action route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return redirect(url_for('admin.flagged_content'))

@admin_bp.route('/stats')
@login_required
def stats():
    """Detailed statistics page."""
    try:
        days = request.args.get('days', 7, type=int)
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        metrics = get_moderation_metrics(days=days)
        
        return render_template(
            'admin/stats.html',
            metrics=metrics,
            days=days,
            start_date=start_date,
            end_date=end_date
        )
    except Exception as e:
        logger.error(f"Error in stats route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return render_template('admin/stats.html')

@admin_bp.route('/settings')
@login_required
def settings():
    """Moderation settings page."""
    try:
        # Get current settings from database
        settings = ModerationSetting.query.all()
        settings_dict = {s.setting_name: s.setting_value for s in settings}
        
        return render_template('admin/settings.html', settings=settings_dict)
    except Exception as e:
        logger.error(f"Error in settings route: {str(e)}")
        flash(f"An error occurred: {str(e)}", "error")
        return render_template('admin/settings.html')
    