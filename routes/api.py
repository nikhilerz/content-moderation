import logging
import os
from datetime import datetime
from flask import Blueprint, request, jsonify
from flask_login import login_required
from werkzeug.utils import secure_filename

from app import db
from models import Content, ModerationStatus, ContentFlag
from moderation.processor import ContentProcessor
from moderation.utils import get_moderation_metrics, generate_daily_metrics
from moderation.train_model import create_sample_training_data, train_from_csv, evaluate_model_performance

# Set up logger
logger = logging.getLogger(__name__)

# Create blueprint
api_bp = Blueprint('api', __name__)

@api_bp.route('/moderate', methods=['POST'])
def moderate_content():
    """
    API endpoint to moderate content.
    
    Expected JSON format:
    {
        "content": "Text to moderate",
        "content_type": "text",
        "user_id": 123,
        "metadata": {...}
    }
    """
    try:
        data = request.json
        
        if not data or 'content' not in data:
            return jsonify({'success': False, 'error': 'Missing required content field'}), 400
            
        processor = ContentProcessor()
        result = processor.process_content(
            content_text=data['content'],  # API accepts 'content' but internally uses 'content_text'
            content_type=data.get('content_type', 'text'),
            user_id=data.get('user_id'),
            metadata=data.get('metadata')
        )
        
        if not result:
            return jsonify({'success': False, 'error': 'Failed to process content'}), 500
            
        # Format response
        response = {
            'success': True,
            'content_id': result['content'].id,
            'status': result['status'].status,
            'moderation_score': result['status'].moderation_score,
            'processing_time': result['status'].processing_time,
            'flags': []
        }
        
        # Add flag details
        for flag in result['flags']:
            response['flags'].append({
                'flag_type': flag.flag_type,
                'score': flag.flag_score
            })
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in moderate_content endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/batch_moderate', methods=['POST'])
def batch_moderate():
    """
    API endpoint to moderate multiple content items in batch.
    
    Expected JSON format:
    {
        "items": [
            {
                "content": "Text to moderate",
                "content_type": "text",
                "user_id": 123,
                "metadata": {...}
            },
            ...
        ]
    }
    """
    try:
        data = request.json
        
        if not data or 'items' not in data or not isinstance(data['items'], list):
            return jsonify({'success': False, 'error': 'Missing or invalid items field'}), 400
            
        processor = ContentProcessor()
        batch_items = []
        
        # Convert to list of dictionaries expected by batch_process
        for item in data['items']:
            if 'content' not in item:
                continue
                
            batch_items.append({
                'content_text': item['content'],
                'content_type': item.get('content_type', 'text'),
                'user_id': item.get('user_id'),
                'metadata': item.get('metadata')
            })
            
        # Process batch
        results = processor.batch_process(batch_items)
        
        if not results:
            return jsonify({'success': False, 'error': 'Failed to process batch'}), 500
            
        # Format response
        response = {
            'success': True,
            'processed_count': len(results),
            'results': []
        }
        
        # Add individual results
        for result in results:
            item_response = {
                'content_id': result['content'].id,
                'status': result['status'].status,
                'moderation_score': result['status'].moderation_score,
                'flags': [{'flag_type': f.flag_type, 'score': f.flag_score} for f in result['flags']]
            }
            response['results'].append(item_response)
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in batch_moderate endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/content/<int:content_id>', methods=['GET'])
@login_required
def get_content(content_id):
    """
    API endpoint to get moderation details for a specific content item.
    """
    try:
        content = Content.query.get(content_id)
        
        if not content:
            return jsonify({'success': False, 'error': 'Content not found'}), 404
            
        status = ModerationStatus.query.filter_by(content_id=content_id).first()
        flags = ContentFlag.query.filter_by(content_id=content_id).all()
        
        # Format response
        response = {
            'success': True,
            'content': {
                'id': content.id,
                'user_id': content.user_id,
                'content_type': content.content_type,
                'content_text': content.content_text,
                'created_at': content.created_at.isoformat()
            },
            'status': {
                'status': status.status if status else 'unknown',
                'moderation_score': status.moderation_score if status else None,
                'is_automated': status.is_automated if status else True,
                'processing_time': status.processing_time if status else None,
                'last_updated': status.last_updated.isoformat() if status and status.last_updated else None
            },
            'flags': []
        }
        
        # Add flag details
        for flag in flags:
            response['flags'].append({
                'flag_type': flag.flag_type,
                'score': flag.flag_score,
                'details': flag.flag_details
            })
            
        return jsonify(response)
    except Exception as e:
        logger.error(f"Error in get_content endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/metrics', methods=['GET'])
@login_required
def get_metrics():
    """
    API endpoint to get moderation metrics.
    """
    try:
        days = request.args.get('days', 7, type=int)
        metrics = get_moderation_metrics(days=days)
        
        return jsonify({'success': True, 'metrics': metrics})
    except Exception as e:
        logger.error(f"Error in get_metrics endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/generate_metrics', methods=['POST'])
@login_required
def trigger_metrics_generation():
    """
    API endpoint to trigger metrics generation.
    """
    try:
        metrics = generate_daily_metrics()
        
        return jsonify({'success': True, 'metrics': metrics})
    except Exception as e:
        logger.error(f"Error in trigger_metrics_generation endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/sample_training_data', methods=['GET'])
@login_required
def get_sample_training_data():
    """
    API endpoint to get sample training data.
    """
    try:
        # Get the path to the sample data file
        # If it doesn't exist, create it
        data_dir = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'data')
        output_path = os.path.join(data_dir, 'sample_training_data.csv')
        
        if not os.path.exists(output_path):
            create_sample_training_data(output_path, num_samples=100)
            
        if not os.path.exists(output_path):
            return jsonify({'success': False, 'error': 'Failed to generate sample training data'}), 500
            
        # Set headers for file download
        return jsonify({'success': True, 'file_path': output_path})
    except Exception as e:
        logger.error(f"Error in get_sample_training_data endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/train_model', methods=['POST'])
@login_required
def train_model():
    """
    API endpoint to train the model with uploaded data.
    """
    try:
        # Check if file was uploaded
        if 'training_file' not in request.files:
            return jsonify({'success': False, 'error': 'No file uploaded'}), 400
            
        file = request.files['training_file']
        
        if file.filename == '':
            return jsonify({'success': False, 'error': 'No file selected'}), 400
            
        if file:
            # Save uploaded file to a temporary location
            filename = secure_filename(file.filename)
            upload_dir = os.path.join(os.path.abspath(os.path.dirname(os.path.dirname(__file__))), 'data', 'uploads')
            
            # Create upload directory if it doesn't exist
            os.makedirs(upload_dir, exist_ok=True)
            
            file_path = os.path.join(upload_dir, filename)
            file.save(file_path)
            
            # Get parameters
            test_size = request.form.get('test_size', 0.2, type=float)
            
            # Train model
            result = train_from_csv(file_path, test_size=test_size)
            
            # Clean up the uploaded file
            # os.remove(file_path)  # Uncomment to delete after training
            
            if not result['success']:
                return jsonify(result), 400
                
            return jsonify(result)
    except Exception as e:
        logger.error(f"Error in train_model endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500

@api_bp.route('/model_info', methods=['GET'])
@login_required
def get_model_info():
    """
    API endpoint to get information about the current model.
    """
    try:
        model_info = evaluate_model_performance()
        
        return jsonify(model_info)
    except Exception as e:
        logger.error(f"Error in get_model_info endpoint: {str(e)}")
        return jsonify({'success': False, 'error': str(e)}), 500
    