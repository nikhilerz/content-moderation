import time
import logging
from datetime import datetime

from app import db
from models import Content, ModerationStatus, ContentFlag, ModerationAction
from moderation.classifier import ContentClassifier
from moderation.utils import preprocess_text

logger = logging.getLogger(__name__)

class ContentProcessor:
    """
    Processes content through the moderation pipeline.
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the content processor with a classifier.
        
        Args:
            model_path: Path to the trained classifier model
        """
        self.classifier = ContentClassifier(model_path)
        logger.info("ContentProcessor initialized")
    
    def process_content(self, content_text, content_type='text', user_id=None, metadata=None):
        """
        Process new content through the moderation pipeline.
        
        Args:
            content_text: The content to moderate (text string or base64 data for media)
            content_type: Type of content ('text', 'image', or 'video')
            user_id: ID of the user who submitted the content
            metadata: Additional content metadata
            
        Returns:
            The processed content record with moderation results
        """
        try:
            start_time = time.time()
            
            # Store original content (might be truncated for large files)
            if content_type in ('image', 'video') and len(content_text) > 1000:
                # For media files, we don't store the entire base64 in original_content,
                # just a reference to the file
                original_content = f"[{content_type.upper()} content]"
                if metadata and 'filename' in metadata:
                    original_content += f" - {metadata['filename']}"
            else:
                original_content = content_text
            
            # For text content, preprocess it
            if content_type == 'text':
                preprocessed_text = preprocess_text(content_text)
            else:
                # For image/video, we'll use the placeholder text for now
                # In a real implementation, we would extract text from the image/video
                # or use a dedicated image/video classification model
                preprocessed_text = f"Analyzing {content_type} content"
                if metadata and 'filename' in metadata:
                    preprocessed_text += f": {metadata['filename']}"
            
            # Create Content record
            content = Content(
                user_id=user_id,
                content_type=content_type,
                content_text=content_text[:1000] if len(content_text) > 1000 else content_text,  # Limit text size
                original_content=original_content,
                content_metadata=metadata
            )
            db.session.add(content)
            db.session.flush()  # Get the ID without committing
            
            # Classification logic based on content type
            if content_type == 'text':
                # Use text classifier
                classification = self.classifier.classify_text(preprocessed_text)
            elif content_type == 'image':
                # For demonstration, generate mock classification
                # In a real implementation, you would use an image classification model
                classification = self._generate_media_classification('image', metadata)
            elif content_type == 'video':
                # For demonstration, generate mock classification
                # In a real implementation, you would use a video analysis model
                classification = self._generate_media_classification('video', metadata)
            else:
                # Default to text classification for unknown types
                classification = self.classifier.classify_text(preprocessed_text)
            
            # Calculate overall moderation score (highest flag score)
            moderation_score = 0
            for category, score in classification.items():
                moderation_score = max(moderation_score, score)
            
            # Determine initial status based on score thresholds
            status = 'pending'
            if moderation_score > 0.8:  # High confidence that content is inappropriate
                status = 'rejected'
            elif moderation_score < 0.3:  # High confidence that content is appropriate
                status = 'approved'
            
            # Create moderation status
            processing_time = time.time() - start_time
            moderation_status = ModerationStatus(
                content_id=content.id,
                status=status,
                moderation_score=moderation_score,
                is_automated=True,
                processing_time=processing_time
            )
            db.session.add(moderation_status)
            
            # Create content flags
            flags = []
            for category, score in classification.items():
                if score > 0.3:  # Only create flags with meaningful scores
                    # Get explainability for this category
                    explanation = self.classifier.get_explainability(preprocessed_text, category)
                    
                    flag = ContentFlag(
                        content_id=content.id,
                        flag_type=category,
                        flag_score=score,
                        flag_details={'explanation': explanation}
                    )
                    db.session.add(flag)
                    flags.append(flag)
            
            # Create initial moderation action
            action = ModerationAction(
                content_id=content.id,
                user_id=None,  # Automated action
                action_type=f'automated_{status}',
                action_notes=f'Automated {status} with score {moderation_score:.2f}'
            )
            db.session.add(action)
            
            # Commit all changes
            db.session.commit()
            
            # Return the processed content data
            return {
                'content': content,
                'status': moderation_status,
                'flags': flags,
                'action': action
            }
            
        except Exception as e:
            logger.error(f"Error processing content: {str(e)}")
            db.session.rollback()
            return None
    
    def batch_process(self, content_list):
        """
        Process a batch of content items.
        
        Args:
            content_list: List of dictionaries with content details
            
        Returns:
            List of processed content records
        """
        results = []
        
        for content_item in content_list:
            result = self.process_content(
                content_text=content_item['content_text'],
                content_type=content_item.get('content_type', 'text'),
                user_id=content_item.get('user_id'),
                metadata=content_item.get('metadata')
            )
            
            if result:
                results.append(result)
        
        return results
    
    def update_moderation_status(self, content_id, status, user_id=None, notes=None):
        """
        Update the moderation status of a content item.
        
        Args:
            content_id: ID of the content to update
            status: New status (approved, rejected)
            user_id: ID of the admin performing the update
            notes: Optional notes for the action
            
        Returns:
            Updated moderation status
        """
        try:
            # Get the content and current status
            content = Content.query.get(content_id)
            if not content:
                logger.error(f"Content not found for ID: {content_id}")
                return None
                
            current_status = ModerationStatus.query.filter_by(content_id=content_id).first()
            if not current_status:
                logger.error(f"Moderation status not found for content ID: {content_id}")
                return None
                
            # Store previous status
            previous_status = current_status.status
            
            # Update the status
            current_status.status = status
            current_status.is_automated = False
            current_status.last_updated = datetime.utcnow()
            
            # Create action record
            action = ModerationAction(
                content_id=content_id,
                user_id=user_id,
                action_type=status,
                action_notes=notes,
                previous_status=previous_status
            )
            db.session.add(action)
            
            # Commit changes
            db.session.commit()
            
            return current_status
            
        except Exception as e:
            logger.error(f"Error updating moderation status: {str(e)}")
            db.session.rollback()
            return None
            
    def _generate_media_classification(self, media_type, metadata=None):
        """
        Generate classification results for media content.
        In a real implementation, this would call external APIs or models.
        
        Args:
            media_type: Type of media ('image' or 'video')
            metadata: File metadata like filename, size, etc.
            
        Returns:
            Dictionary with classification results for different categories
        """
        # This is a demo implementation that generates plausible
        # flags for different media types
        
        classification = {}
        
        # Common categories for all media types
        classification['violence'] = max(0.05, min(0.95, float(hash(str(metadata)) % 100) / 100))
        classification['adult_content'] = max(0.05, min(0.95, float(hash(str(metadata) + '1') % 100) / 100))
        
        if media_type == 'image':
            # Image-specific categories
            classification['graphic_violence'] = max(0.05, min(0.95, float(hash(str(metadata) + '2') % 100) / 100))
            classification['sexual_content'] = max(0.05, min(0.95, float(hash(str(metadata) + '3') % 100) / 100))
            classification['hate_symbols'] = max(0.05, min(0.95, float(hash(str(metadata) + '4') % 100) / 100))
        
        elif media_type == 'video':
            # Video-specific categories
            classification['graphic_violence'] = max(0.05, min(0.95, float(hash(str(metadata) + '5') % 100) / 100))
            classification['sexual_content'] = max(0.05, min(0.95, float(hash(str(metadata) + '6') % 100) / 100))
            classification['dangerous_activity'] = max(0.05, min(0.95, float(hash(str(metadata) + '7') % 100) / 100))
            classification['hate_speech'] = max(0.05, min(0.95, float(hash(str(metadata) + '8') % 100) / 100))
        
        # In a real implementation, you would check content against
        # policies and generate accurate classifications
        
        return classification
    