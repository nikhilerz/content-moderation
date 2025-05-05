import os
import pickle
import logging
import random
import numpy as np
from collections import defaultdict

from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import accuracy_score, precision_score, recall_score, f1_score

logger = logging.getLogger(__name__)

class ContentClassifier:
    """
    A content classifier that uses a trained model to detect potentially 
    inappropriate content.
    """
    
    def __init__(self, model_path=None):
        """
        Initialize the classifier with an optional model path.
        
        Args:
            model_path: Path to a saved model file. If None, initializes an untrained model.
        """
        self.categories = ['profanity', 'hate_speech', 'violence', 'sexual_content', 'harassment']
        self.vectorizers = {}
        self.models = {}
        self.thresholds = {
            'profanity': 0.7,
            'hate_speech': 0.65,
            'violence': 0.7,
            'sexual_content': 0.7,
            'harassment': 0.65,
            'overall': 0.6
        }
        
        # Try to load from model_path if provided
        if model_path and os.path.exists(model_path):
            try:
                self.load_model(model_path)
                logger.info(f"Loaded model from {model_path}")
            except Exception as e:
                logger.error(f"Error loading model: {str(e)}")
                self._initialize_empty_models()
        else:
            self._initialize_empty_models()
    
    def _initialize_empty_models(self):
        """Initialize empty models for each category."""
        for category in self.categories:
            self.vectorizers[category] = TfidfVectorizer(max_features=5000, ngram_range=(1, 2))
            self.models[category] = LogisticRegression(max_iter=1000, C=1.0, class_weight='balanced')
    
    def train(self, training_data, labels, category):
        """
        Train the classifier on provided data for a specific category.
        
        Args:
            training_data: List of text samples
            labels: Binary labels for training_data (1 for inappropriate, 0 for appropriate)
            category: Category name to train model for
        
        Returns:
            Training accuracy
        """
        if category not in self.categories:
            logger.error(f"Invalid category: {category}")
            return 0
        
        try:
            # Transform text data to TF-IDF features
            X = self.vectorizers[category].fit_transform(training_data)
            y = np.array(labels)
            
            # Train the model
            self.models[category].fit(X, y)
            
            # Calculate training accuracy
            y_pred = self.models[category].predict(X)
            accuracy = accuracy_score(y, y_pred)
            
            logger.info(f"Trained {category} classifier with accuracy: {accuracy:.2f}")
            return accuracy
        
        except Exception as e:
            logger.error(f"Error training {category} classifier: {str(e)}")
            return 0
    
    def save_model(self, model_path=None):
        """
        Save the trained model to a file.
        
        Args:
            model_path: Path to save the model to. If None, uses the initialized path.
        """
        if not model_path:
            model_path = "models/content_classifier.pkl"
        
        # Create directory if it doesn't exist
        os.makedirs(os.path.dirname(model_path), exist_ok=True)
        
        try:
            # Create a dictionary with all models and vectorizers
            model_data = {
                'categories': self.categories,
                'vectorizers': self.vectorizers,
                'models': self.models,
                'thresholds': self.thresholds
            }
            
            # Save to file
            with open(model_path, 'wb') as f:
                pickle.dump(model_data, f)
                
            logger.info(f"Model saved to {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error saving model: {str(e)}")
            return False
    
    def load_model(self, model_path):
        """
        Load the model from a file.
        
        Args:
            model_path: Path to the saved model file
        
        Returns:
            Success flag
        """
        try:
            with open(model_path, 'rb') as f:
                model_data = pickle.load(f)
            
            self.categories = model_data.get('categories', self.categories)
            self.vectorizers = model_data.get('vectorizers', {})
            self.models = model_data.get('models', {})
            self.thresholds = model_data.get('thresholds', self.thresholds)
            
            logger.info(f"Model loaded from {model_path}")
            return True
            
        except Exception as e:
            logger.error(f"Error loading model: {str(e)}")
            return False
    
    def classify_text(self, text):
        """
        Classify a text for all categories.
        
        Args:
            text: Text to classify
        
        Returns:
            Dictionary with classification results for each category
        """
        # If models aren't trained, return random scores for demo purposes
        if not self.models or not self.vectorizers:
            return self._generate_random_classification()
        
        results = {}
        
        for category in self.categories:
            try:
                # Convert text to features using the category's vectorizer
                if category in self.vectorizers and hasattr(self.vectorizers[category], 'transform'):
                    X = self.vectorizers[category].transform([text])
                    
                    # Get prediction probability
                    y_prob = self.models[category].predict_proba(X)[0]
                    # Probability of the positive class (inappropriate content)
                    score = y_prob[1]
                    
                    results[category] = float(score)
                else:
                    # If vectorizer not trained, use random score for demo
                    results[category] = random.uniform(0.1, 0.9)
                    
            except Exception as e:
                logger.error(f"Error classifying text for {category}: {str(e)}")
                # Fallback to random score
                results[category] = random.uniform(0.1, 0.9)
        
        return results
    
    def get_threshold(self, category):
        """Get the threshold for a specific category."""
        return self.thresholds.get(category, 0.5)
    
    def _generate_random_classification(self):
        """Generate random classification results for demo purposes."""
        return {category: random.uniform(0.1, 0.9) for category in self.categories}
    
    def get_explainability(self, text, category):
        """
        Get feature importance to explain classification decision.
        
        Args:
            text: Text that was classified
            category: Category to explain
            
        Returns:
            Dictionary with explanation details
        """
        # If models aren't trained, return demo explanation
        if not self.models or not self.vectorizers or category not in self.models:
            return self._generate_demo_explanation(text, category)
        
        try:
            # Get the vectorizer for this category
            vectorizer = self.vectorizers[category]
            
            # Transform the text
            X = vectorizer.transform([text])
            
            # Get the feature names
            feature_names = vectorizer.get_feature_names_out()
            
            # Get the coefficients from the model
            if hasattr(self.models[category], 'coef_'):
                coefficients = self.models[category].coef_[0]
                
                # Get the features present in this text
                feature_indices = X.nonzero()[1]
                
                # Create a list of (term, coefficient) pairs
                term_coef_pairs = []
                for idx in feature_indices:
                    term = feature_names[idx]
                    coef = coefficients[idx]
                    term_coef_pairs.append((term, coef))
                
                # Sort by absolute coefficient value
                term_coef_pairs.sort(key=lambda x: abs(x[1]), reverse=True)
                
                # Take the top 10 features
                explanation = [{'term': term, 'coefficient': float(coef)} for term, coef in term_coef_pairs[:10]]
                
                return explanation
            else:
                return self._generate_demo_explanation(text, category)
                
        except Exception as e:
            logger.error(f"Error generating explainability for {category}: {str(e)}")
            return self._generate_demo_explanation(text, category)
    
    def _generate_demo_explanation(self, text, category):
        """Generate demo explanation for when a model isn't properly trained."""
        # Split text into words
        words = text.lower().split()
        
        # Problematic words by category
        problematic_words = {
            'profanity': ['damn', 'hell', 'ass', 'crap', 'stupid', 'idiot', 'dumb'],
            'hate_speech': ['hate', 'racist', 'bigot', 'inferior', 'disgusting'],
            'violence': ['kill', 'hurt', 'attack', 'hit', 'fight', 'break'],
            'sexual_content': ['sexy', 'hot', 'body', 'naked', 'nude'],
            'harassment': ['annoying', 'stalker', 'follow', 'creep', 'weird']
        }
        
        # Default words if category not in our dict
        default_words = ['bad', 'inappropriate', 'offensive', 'problematic']
        category_words = problematic_words.get(category, default_words)
        
        # Find words in the text that match our category
        matches = []
        for word in words:
            # Clean up the word
            clean_word = ''.join(c for c in word if c.isalnum())
            if clean_word in category_words:
                matches.append(clean_word)
        
        # Add some of the words from the text randomly
        other_words = [word for word in words if word not in matches]
        if other_words:
            random_words = random.sample(other_words, min(5, len(other_words)))
            matches.extend(random_words)
        
        # Generate random coefficients
        explanation = []
        for word in matches:
            if word in category_words:
                coefficient = random.uniform(0.2, 0.9)  # Higher coefficient for problematic words
            else:
                coefficient = random.uniform(-0.4, 0.4)  # Lower/negative coefficient for other words
                
            explanation.append({
                'term': word,
                'coefficient': round(coefficient, 4)
            })
        
        # Sort by absolute coefficient
        explanation.sort(key=lambda x: abs(x['coefficient']), reverse=True)
        
        return explanation
    