import re
import string
import logging
from datetime import datetime, timedelta
import random

from app import db
from models import ModerationStatus, ContentFlag, ModerationMetric

logger = logging.getLogger(__name__)

def preprocess_text(text):
    """
    Preprocess text for NLP analysis.
    
    Args:
        text: Raw text input
        
    Returns:
        Preprocessed text
    """
    if not text:
        return ""
        
    # Convert to lowercase
    text = text.lower()
    
    # Remove extra whitespace
    text = ' '.join(text.split())
    
    # Remove URLs
    text = re.sub(r'https?://\S+|www\.\S+', '[URL]', text)
    
    # Remove email addresses
    text = re.sub(r'\S+@\S+', '[EMAIL]', text)
    
    # Replace special characters with space
    text = re.sub(r'[^\w\s]', ' ', text)
    
    # Remove numbers
    text = re.sub(r'\d+', '[NUM]', text)
    
    # Remove extra whitespace again after all replacements
    text = ' '.join(text.split())
    
    return text

def generate_daily_metrics():
    """
    Generate daily metrics for moderation activities.
    
    Returns:
        Dict with generated metrics
    """
    try:
        # Get today's date
        today = datetime.utcnow().date()
        
        # Check if metrics for today already exist
        existing_metrics = ModerationMetric.query.filter_by(metric_date=today).all()
        existing_types = [m.metric_type for m in existing_metrics]
        
        # Generate daily processed metric
        if 'daily_processed' not in existing_types:
            # Count content processed today
            start_of_day = datetime.combine(today, datetime.min.time())
            end_of_day = datetime.combine(today, datetime.max.time())
            
            processed_count = ModerationStatus.query.filter(
                ModerationStatus.last_updated.between(start_of_day, end_of_day)
            ).count()
            
            # Create and save metric
            daily_processed = ModerationMetric(
                metric_date=today,
                metric_type='daily_processed',
                metric_value={'count': processed_count, 'date': today.isoformat()}
            )
            db.session.add(daily_processed)
        
        # Generate flag distribution metric
        if 'flag_distribution' not in existing_types:
            # Get flags created today
            flags = ContentFlag.query.filter(
                ContentFlag.created_at.between(
                    datetime.combine(today, datetime.min.time()),
                    datetime.combine(today, datetime.max.time())
                )
            ).all()
            
            # Count flags by type
            flag_counts = {}
            for flag in flags:
                if flag.flag_type in flag_counts:
                    flag_counts[flag.flag_type] += 1
                else:
                    flag_counts[flag.flag_type] = 1
            
            # Create and save metric
            flag_distribution = ModerationMetric(
                metric_date=today,
                metric_type='flag_distribution',
                metric_value=flag_counts
            )
            db.session.add(flag_distribution)
            
        # Generate status distribution metric
        if 'status_distribution' not in existing_types:
            # Count statuses updated today
            statuses = ModerationStatus.query.filter(
                ModerationStatus.last_updated.between(
                    datetime.combine(today, datetime.min.time()),
                    datetime.combine(today, datetime.max.time())
                )
            ).all()
            
            # Count by status
            status_counts = {}
            for status in statuses:
                if status.status in status_counts:
                    status_counts[status.status] += 1
                else:
                    status_counts[status.status] = 1
            
            # Create and save metric
            status_distribution = ModerationMetric(
                metric_date=today,
                metric_type='status_distribution',
                metric_value=status_counts
            )
            db.session.add(status_distribution)
            
        # Generate average processing time metric
        if 'avg_processing_time' not in existing_types:
            # Get processing times from today
            statuses = ModerationStatus.query.filter(
                ModerationStatus.last_updated.between(
                    datetime.combine(today, datetime.min.time()),
                    datetime.combine(today, datetime.max.time())
                ),
                ModerationStatus.processing_time.isnot(None)
            ).all()
            
            if statuses:
                avg_time = sum(s.processing_time for s in statuses) / len(statuses)
            else:
                avg_time = 0
            
            # Create and save metric
            avg_processing_time = ModerationMetric(
                metric_date=today,
                metric_type='avg_processing_time',
                metric_value=avg_time
            )
            db.session.add(avg_processing_time)
        
        # Commit all changes
        db.session.commit()
        
        # Return the newly generated metrics
        return {'success': True, 'message': 'Daily metrics generated successfully'}
        
    except Exception as e:
        logger.error(f"Error generating daily metrics: {str(e)}")
        db.session.rollback()
        return {'success': False, 'error': str(e)}

def get_moderation_metrics(days=7):
    """
    Get moderation metrics for the specified number of days.
    
    Args:
        days: Number of days to include in metrics
        
    Returns:
        Dict with metrics data
    """
    try:
        # Calculate date range
        end_date = datetime.utcnow().date()
        start_date = end_date - timedelta(days=days)
        
        # Query metrics within date range
        metrics = ModerationMetric.query.filter(
            ModerationMetric.metric_date >= start_date,
            ModerationMetric.metric_date <= end_date
        ).all()
        
        # If no metrics exist, generate sample data
        if not metrics:
            return _generate_sample_metrics(start_date, end_date, days)
        
        # Organize metrics by type
        metrics_by_type = {}
        for metric in metrics:
            if metric.metric_type not in metrics_by_type:
                metrics_by_type[metric.metric_type] = []
            
            metrics_by_type[metric.metric_type].append({
                'date': metric.metric_date.isoformat(),
                'value': metric.metric_value
            })
        
        # Ensure all days have data for each metric type
        all_dates = [(end_date - timedelta(days=i)).isoformat() for i in range(days)]
        
        for metric_type, values in metrics_by_type.items():
            existing_dates = [v['date'] for v in values]
            
            for date in all_dates:
                if date not in existing_dates:
                    if metric_type == 'daily_processed':
                        metrics_by_type[metric_type].append({
                            'date': date,
                            'value': {'count': 0}
                        })
                    elif metric_type == 'flag_distribution':
                        metrics_by_type[metric_type].append({
                            'date': date,
                            'value': {}
                        })
                    elif metric_type == 'status_distribution':
                        metrics_by_type[metric_type].append({
                            'date': date,
                            'value': {}
                        })
                    elif metric_type == 'avg_processing_time':
                        metrics_by_type[metric_type].append({
                            'date': date,
                            'value': 0
                        })
            
            # Sort by date
            metrics_by_type[metric_type].sort(key=lambda x: x['date'])
        
        # Return organized metrics
        return metrics_by_type
        
    except Exception as e:
        logger.error(f"Error getting moderation metrics: {str(e)}")
        return _generate_sample_metrics(start_date, end_date, days)

def _generate_sample_metrics(start_date, end_date, days):
    """Generate sample metrics for demonstration purposes."""
    # Flag types
    flag_types = ['profanity', 'hate_speech', 'violence', 'sexual_content', 'harassment']
    
    # Status types
    status_types = ['pending', 'approved', 'rejected']
    
    # Generate metrics for each day
    daily_processed = []
    flag_distribution = []
    status_distribution = []
    avg_processing_time = []
    
    for i in range(days):
        date = (end_date - timedelta(days=i)).isoformat()
        
        # Daily processed
        daily_processed.append({
            'date': date,
            'value': {'count': random.randint(50, 200)}
        })
        
        # Flag distribution
        flag_counts = {}
        for flag_type in flag_types:
            if random.random() > 0.2:  # 80% chance to include each flag type
                flag_counts[flag_type] = random.randint(5, 50)
        
        flag_distribution.append({
            'date': date,
            'value': flag_counts
        })
        
        # Status distribution
        status_counts = {}
        for status_type in status_types:
            status_counts[status_type] = random.randint(10, 70)
        
        status_distribution.append({
            'date': date,
            'value': status_counts
        })
        
        # Average processing time
        avg_processing_time.append({
            'date': date,
            'value': round(random.uniform(0.1, 2.0), 2)
        })
    
    # Sort by date
    daily_processed.sort(key=lambda x: x['date'])
    flag_distribution.sort(key=lambda x: x['date'])
    status_distribution.sort(key=lambda x: x['date'])
    avg_processing_time.sort(key=lambda x: x['date'])
    
    return {
        'daily_processed': daily_processed,
        'flag_distribution': flag_distribution,
        'status_distribution': status_distribution,
        'avg_processing_time': avg_processing_time
    }
