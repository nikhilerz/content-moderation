import os
import logging
import numpy as np
import pandas as pd
from sklearn.model_selection import train_test_split
from sklearn.metrics import classification_report, confusion_matrix
from moderation.classifier import ContentClassifier
from moderation.utils import preprocess_text

logger = logging.getLogger(__name__)

class ModelTrainer:
    """
    Train and evaluate content moderation models.
    """
    
    def __init__(self, model_path='models/content_classifier.pkl'):
        """
        Initialize the model trainer.
        
        Args:
            model_path: Path to save trained models
        """
        self.model_path = model_path
        self.classifier = ContentClassifier()
        
        # Create models directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        logger.info(f"Model trainer initialized. Models will be saved to {model_path}")
    
    def train_model(self, training_data_path, test_size=0.2, random_state=42):
        """
        Train a model using data from a CSV file.
        
        Args:
            training_data_path: Path to CSV with training data
            test_size: Fraction of data to use for testing
            random_state: Random seed for reproducibility
            
        Returns:
            Dict with training results
        """
        logger.info(f"Training model with data from {training_data_path}")
        
        try:
            # Load the training data
            if not os.path.exists(training_data_path):
                raise FileNotFoundError(f"Training data file not found: {training_data_path}")
                
            data = pd.read_csv(training_data_path)
            logger.info(f"Loaded training data with {len(data)} samples")
            
            # Check required columns
            required_columns = ['text'] + self.classifier.categories
            missing_columns = [col for col in required_columns if col not in data.columns]
            if missing_columns:
                raise ValueError(f"Missing required columns in training data: {missing_columns}")
            
            # Train model for each category
            results = {}
            for category in self.classifier.categories:
                logger.info(f"Training model for category: {category}")
                
                # Split data
                X = data['text'].values
                y = data[category].values
                
                X_train, X_test, y_train, y_test = train_test_split(
                    X, y, test_size=test_size, random_state=random_state, stratify=y
                )
                
                # Train the model
                train_score = self.classifier.train(X_train, y_train, category)
                
                # Evaluate on test data
                y_pred = self.classifier.model[category].predict(X_test)
                y_pred_proba = self.classifier.model[category].predict_proba(X_test)[:, 1]
                
                # Calculate metrics
                report = classification_report(y_test, y_pred, output_dict=True)
                cm = confusion_matrix(y_test, y_pred)
                
                results[category] = {
                    'train_score': train_score,
                    'test_score': report['accuracy'],
                    'precision': report['1']['precision'] if '1' in report else 0,
                    'recall': report['1']['recall'] if '1' in report else 0,
                    'f1_score': report['1']['f1-score'] if '1' in report else 0,
                    'confusion_matrix': cm.tolist(),
                    'samples_trained': len(X_train)
                }
                
                logger.info(f"Results for {category}: F1={results[category]['f1_score']:.4f}")
            
            # Save the trained model
            self.classifier.save_model(self.model_path)
            logger.info(f"Model saved to {self.model_path}")
            
            return results
            
        except Exception as e:
            logger.error(f"Error training model: {str(e)}")
            raise
    
    def evaluate_text(self, text):
        """
        Evaluate a piece of text with the current model.
        
        Args:
            text: Text to evaluate
            
        Returns:
            Classification results
        """
        try:
            # Preprocess the text
            processed_text = preprocess_text(text)
            
            # Get classification results
            results = self.classifier.classify_text(processed_text)
            
            # Get explanations for each category
            for category in results.keys():
                explanation = self.classifier.get_explainability(processed_text, category)
                results[category]['explanation'] = explanation.get('explanation', [])
            
            return results
            
        except Exception as e:
            logger.error(f"Error evaluating text: {str(e)}")
            return {'error': str(e)}
    
    def generate_sample_training_data(self, output_path='sample_training_data.csv', num_samples=100):
        """
        Generate a sample training data CSV with the expected format.
        
        Args:
            output_path: Path to save the CSV
            num_samples: Number of sample rows to generate
            
        Returns:
            Path to generated file
        """
        try:
            # Create a DataFrame with the required columns
            categories = self.classifier.categories
            
            df = pd.DataFrame({
                'text': [f"This is a sample text {i}" for i in range(num_samples)]
            })
            
            # Add a column for each category (with random binary values)
            for category in categories:
                df[category] = np.random.randint(0, 2, size=num_samples)
            
            # Save to CSV
            df.to_csv(output_path, index=False)
            logger.info(f"Sample training data saved to {output_path}")
            
            return output_path
            
        except Exception as e:
            logger.error(f"Error generating sample training data: {str(e)}")
            raise

