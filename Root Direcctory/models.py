from datetime import datetime
from app import db
from flask_login import UserMixin
from sqlalchemy.dialects.postgresql import JSONB

class User(UserMixin, db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(64), unique=True, nullable=False)
    email = db.Column(db.String(120), unique=True, nullable=False)
    # ensure password hash field has length of at least 256
    password_hash = db.Column(db.String(256))
    is_admin = db.Column(db.Boolean, default=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationship with moderation actions
    actions = db.relationship('ModerationAction', backref='user', lazy='dynamic')
    
    def __repr__(self):
        return f'<User {self.username}>'

class Content(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)
    content_type = db.Column(db.String(50), nullable=False)  # text, image_text, etc.
    content_text = db.Column(db.Text, nullable=False)
    original_content = db.Column(db.Text, nullable=False)  # Store the original content for reference
    content_metadata = db.Column(JSONB, nullable=True)  # Store additional metadata like source, context, etc.
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    # Relationships
    moderation_status = db.relationship('ModerationStatus', backref='content', uselist=False, cascade="all, delete-orphan")
    flags = db.relationship('ContentFlag', backref='content', lazy='dynamic', cascade="all, delete-orphan")
    actions = db.relationship('ModerationAction', backref='content', lazy='dynamic', cascade="all, delete-orphan")
    
    def __repr__(self):
        return f'<Content {self.id} - Type: {self.content_type}>'

class ModerationStatus(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    status = db.Column(db.String(20), nullable=False, default='pending')  # pending, approved, rejected
    moderation_score = db.Column(db.Float, nullable=True)  # Overall score of moderation
    is_automated = db.Column(db.Boolean, default=True)  # Was this moderation automated or manual
    last_updated = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    processing_time = db.Column(db.Float, nullable=True)  # Time taken to process in seconds
    
    def __repr__(self):
        return f'<ModerationStatus {self.content_id} - {self.status}>'

class ContentFlag(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    flag_type = db.Column(db.String(50), nullable=False)  # profanity, hate_speech, violence, etc.
    flag_score = db.Column(db.Float, nullable=False)  # Confidence score for this flag
    flag_details = db.Column(JSONB, nullable=True)  # Additional details about the flag
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ContentFlag {self.content_id} - {self.flag_type}: {self.flag_score}>'

class ModerationAction(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    content_id = db.Column(db.Integer, db.ForeignKey('content.id'), nullable=False)
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=True)  # Null if automated
    action_type = db.Column(db.String(50), nullable=False)  # approve, reject, escalate
    action_notes = db.Column(db.Text, nullable=True)
    previous_status = db.Column(db.String(20), nullable=True)  # The status before this action
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModerationAction {self.content_id} - {self.action_type}>'

class ModerationSetting(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    setting_name = db.Column(db.String(100), unique=True, nullable=False)
    setting_value = db.Column(db.String(255), nullable=False)
    setting_description = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    updated_at = db.Column(db.DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModerationSetting {self.setting_name}: {self.setting_value}>'

class ModerationMetric(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    metric_date = db.Column(db.Date, nullable=False)
    metric_type = db.Column(db.String(50), nullable=False)  # daily_processed, flag_distribution, etc
    metric_value = db.Column(JSONB, nullable=False)
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    
    def __repr__(self):
        return f'<ModerationMetric {self.metric_date} - {self.metric_type}>'

