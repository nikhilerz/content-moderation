import json
from datetime import datetime

def register_filters(app):
    """Register custom Jinja2 filters with the Flask app"""
    
    @app.template_filter('to_json')
    def to_json(value):
        """Convert a Python object to a JSON string for use in JavaScript"""
        return json.dumps(value)
    
    @app.template_filter('format_date')
    def format_date(value, format='%Y-%m-%d'):
        """Format a date"""
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)
    
    @app.template_filter('format_timestamp')
    def format_timestamp(value, format='%Y-%m-%d %H:%M:%S'):
        """Format a timestamp"""
        if not value:
            return ''
        if isinstance(value, str):
            try:
                value = datetime.fromisoformat(value)
            except ValueError:
                return value
        return value.strftime(format)
    
    @app.template_filter('truncate_text')
    def truncate_text(text, length=100, suffix='...'):
        """Truncate text to a specific length"""
        if not text:
            return ''
        if len(text) <= length:
            return text
        return text[:length].rstrip() + suffix
    
    @app.template_filter('format_flag_type')
    def format_flag_type(flag_type):
        """Format a flag type to be more readable"""
        if not flag_type:
            return ''
        # Replace underscores with spaces and capitalize each word
        return ' '.join(word.capitalize() for word in flag_type.split('_'))
    
    @app.template_filter('flag_color')
    def flag_color(score):
        """Return appropriate color class based on flag score"""
        if not score and score != 0:
            return 'text-secondary'
        score = float(score)
        if score >= 0.8:
            return 'text-danger'
        elif score >= 0.5:
            return 'text-warning'
        elif score >= 0.3:
            return 'text-info'
        else:
            return 'text-success'
    
    @app.template_filter('status_color')
    def status_color(status):
        """Return appropriate color class based on moderation status"""
        if not status:
            return 'text-secondary'
        status = status.lower()
        if status == 'approved':
            return 'text-success'
        elif status == 'rejected':
            return 'text-danger'
        elif status == 'pending':
            return 'text-warning'
        else:
            return 'text-info'
    
    @app.template_filter('now')
    def now(format='%Y-%m-%d'):
        """Get current date/time in the specified format"""
        return datetime.utcnow().strftime(format)
    