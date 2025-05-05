import os
import csv
import random
import logging
import pandas as pd
from datetime import datetime
from sklearn.model_selection import train_test_split

from moderation.classifier import ContentClassifier

logger = logging.getLogger(__name__)

def train_from_csv(csv_file_path, test_size=0.2, random_state=42):
    """
    Train a moderation model from a CSV file.
    
    Args:
        csv_file_path: Path to the CSV file with training data
        test_size: Portion of data to use for testing (0.0 to 1.0)
        random_state: Random seed for reproducibility
        
    Returns:
        Dictionary with training results
    """
    try:
        # Check if file exists
        if not os.path.exists(csv_file_path):
            return {
                'success': False,
                'error': f'File not found: {csv_file_path}'
            }
        
        # Read CSV file
        df = pd.read_csv(csv_file_path)
        
        # Check required columns
        required_columns = ['text', 'category', 'label']
        missing_columns = [col for col in required_columns if col not in df.columns]
        
        if missing_columns:
            return {
                'success': False,
                'error': f'Missing required columns: {", ".join(missing_columns)}'
            }
        
        # Initialize classifier
        classifier = ContentClassifier()
        
        # Group by category and train model for each category
        results = {}
        
        for category, category_df in df.groupby('category'):
            # Check if category is valid
            if category not in classifier.categories:
                logger.warning(f'Skipping unknown category: {category}')
                continue
                
            # Get text and labels
            texts = category_df['text'].tolist()
            labels = category_df['label'].astype(int).tolist()
            
            # Split into train and test sets
            X_train, X_test, y_train, y_test = train_test_split(
                texts, labels, test_size=test_size, random_state=random_state
            )
            
            # Train the model
            train_accuracy = classifier.train(X_train, y_train, category)
            
            # Evaluate on test set
            test_results = evaluate_category(classifier, category, X_test, y_test)
            
            # Store results
            results[category] = {
                'train_size': len(X_train),
                'test_size': len(X_test),
                'train_accuracy': train_accuracy,
                'test_accuracy': test_results['accuracy'],
                'precision': test_results['precision'],
                'recall': test_results['recall'],
                'f1_score': test_results['f1_score']
            }
        
        # Save the trained model
        model_path = 'models/content_classifier.pkl'
        save_success = classifier.save_model(model_path)
        
        # Return results
        return {
            'success': True,
            'message': 'Model trained successfully',
            'model_path': model_path if save_success else None,
            'categories': list(results.keys()),
            'results': results
        }
        
    except Exception as e:
        logger.error(f"Error training model: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }

def create_sample_training_data(output_path, num_samples=100):
    """
    Create a sample training data CSV file.
    
    Args:
        output_path: Path to save the CSV file
        num_samples: Number of sample rows to generate
        
    Returns:
        Success status
    """
    try:
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(output_path), exist_ok=True)
        
        # Categories to generate samples for
        categories = ['profanity', 'hate_speech', 'violence', 'sexual_content', 'harassment']
        
        # Sample texts by category
        sample_texts = {
            'profanity': [
                "This is a normal sentence without any issues.",
                "I hate when people use bad words like d**n and f**k.",
                "What the heck is going on with this service?",
                "This product is really great, I love it!",
                "You are such an idiot for making this decision.",
                "This stupid app keeps crashing on my phone.",
                "Are you out of your mind with these prices?",
                "The customer service was actually quite helpful.",
                "That's complete garbage and you know it.",
                "These new features are really cool and useful."
            ],
            'hate_speech': [
                "I believe all people deserve equal treatment and respect.",
                "People from that country are always causing problems.",
                "Different cultural perspectives enrich our community.",
                "I can't stand how those people always behave.",
                "We should learn from diverse experiences and backgrounds.",
                "Why do they let those kind of people work here?",
                "Everyone has unique talents to contribute to society.",
                "Those people don't belong in our neighborhood.",
                "It's important to understand different viewpoints.",
                "I don't want my kids around people like that."
            ],
            'violence': [
                "Let's discuss this issue calmly and find a solution.",
                "I'm going to punch you if you say that again.",
                "The movie had some intense action scenes.",
                "I'll break your face if you don't back off.",
                "The sports team really crushed their opponents yesterday.",
                "I want to kill whoever designed this user interface.",
                "The debate was heated but remained respectful.",
                "Someone should take a bat to that car.",
                "Please handle this delicate situation with care.",
                "I'm going to destroy anyone who stands in my way."
            ],
            'sexual_content': [
                "The restaurant offers a lovely atmosphere for dining.",
                "She looked so hot in that outfit last night.",
                "The weather forecast predicts warm temperatures tomorrow.",
                "That's a very provocative and revealing photo.",
                "The art exhibit features various landscape paintings.",
                "This movie has too many naked scenes for my taste.",
                "The new coffee shop has a cozy, welcoming interior.",
                "I want to see you without those clothes on later.",
                "The hiking trail offers beautiful scenic views.",
                "Your body looks amazing in that swimsuit photo."
            ],
            'harassment': [
                "Please let me know if you need any assistance.",
                "I'm going to keep messaging you until you respond.",
                "I respect your decision and won't pressure you further.",
                "Why do you keep ignoring me? Answer me now!",
                "Thank you for your time and consideration.",
                "I know where you live and I'll find you.",
                "Let's schedule a meeting at your convenience.",
                "You can't avoid me forever, I'll make sure of that.",
                "I understand this isn't a good time, I'll check back later.",
                "I'm watching everything you do online."
            ]
        }
        
        # Generate rows for the CSV
        rows = []
        
        # Header row
        rows.append(['text', 'category', 'label'])
        
        # Generate random samples
        for i in range(num_samples):
            # Choose a random category
            category = random.choice(categories)
            
            # Get random text from the category
            samples = sample_texts[category]
            text = random.choice(samples)
            
            # Determine label (70% chance of matching category to text)
            if random.random() < 0.7:
                # Appropriate label for the text
                if text == samples[0] or text == samples[3] or text == samples[7] or text == samples[9]:
                    label = 0  # Safe content
                else:
                    label = 1  # Inappropriate content
            else:
                # Random label
                label = random.choice([0, 1])
            
            # Add row
            rows.append([text, category, label])
        
        # Write to CSV
        with open(output_path, 'w', newline='') as f:
            writer = csv.writer(f)
            writer.writerows(rows)
        
        return True
        
    except Exception as e:
        logger.error(f"Error creating sample training data: {str(e)}")
        return False

def evaluate_category(classifier, category, texts, labels):
    """Evaluate classifier performance on a specific category."""
    try:
        # Get predictions
        predictions = []
        for text in texts:
            result = classifier.classify_text(text)
            score = result.get(category, 0)
            prediction = 1 if score >= classifier.get_threshold(category) else 0
            predictions.append(prediction)
        
        # Calculate metrics
        correct = sum(1 for p, l in zip(predictions, labels) if p == l)
        accuracy = correct / len(texts) if texts else 0
        
        # Calculate precision, recall, and F1 score
        true_positives = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 1)
        false_positives = sum(1 for p, l in zip(predictions, labels) if p == 1 and l == 0)
        false_negatives = sum(1 for p, l in zip(predictions, labels) if p == 0 and l == 1)
        
        precision = true_positives / (true_positives + false_positives) if (true_positives + false_positives) > 0 else 0
        recall = true_positives / (true_positives + false_negatives) if (true_positives + false_negatives) > 0 else 0
        f1_score = 2 * precision * recall / (precision + recall) if (precision + recall) > 0 else 0
        
        return {
            'accuracy': accuracy,
            'precision': precision,
            'recall': recall,
            'f1_score': f1_score
        }
        
    except Exception as e:
        logger.error(f"Error evaluating category {category}: {str(e)}")
        return {
            'accuracy': 0,
            'precision': 0,
            'recall': 0,
            'f1_score': 0
        }

def evaluate_model_performance():
    """
    Evaluate the current model performance.
    
    Returns:
        Dictionary with model metrics
    """
    try:
        # Initialize classifier
        classifier = ContentClassifier()
        
        # Get all categories
        categories = classifier.categories
        
        # Get model path
        model_path = 'models/content_classifier.pkl'
        
        # Check if model file exists
        model_exists = os.path.exists(model_path)
        
        # Get model last modified time
        if model_exists:
            last_modified = datetime.fromtimestamp(os.path.getmtime(model_path)).isoformat()
        else:
            last_modified = None
        
        # Return model info
        return {
            'success': True,
            'model_exists': model_exists,
            'model_path': model_path if model_exists else None,
            'last_modified': last_modified,
            'categories': categories,
            'thresholds': {category: classifier.get_threshold(category) for category in categories}
        }
        
    except Exception as e:
        logger.error(f"Error evaluating model performance: {str(e)}")
        return {
            'success': False,
            'error': str(e)
        }
    