"""Trick classification using temporal features"""

import numpy as np
from typing import List, Dict
import logging

logger = logging.getLogger(__name__)


class TrickClassifier:
    """Classifies skateboarding tricks from pose landmarks"""
    
    # Supported tricks (in production, this would be a trained neural network)
    TRICKS = {
        'ollie': {'category': 'basic', 'rotation': 0},
        'kickflip': {'category': 'flip', 'rotation': 360},
        'heelflip': {'category': 'flip', 'rotation': 360},
        'pop_shuvit': {'category': 'shuvit', 'rotation': 180},
        '360_flip': {'category': 'flip', 'rotation': 360},
        'impossible': {'category': 'flip', 'rotation': 360},
        'nollie': {'category': 'basic', 'rotation': 0},
        'manual': {'category': 'balance', 'rotation': 0},
        'boardslide': {'category': 'grind', 'rotation': 0},
        '50-50': {'category': 'grind', 'rotation': 0},
    }
    
    def __init__(self):
        # In production, load trained model here
        # self.model = torch.load('models/trick_classifier.pth')
        pass
    
    def classify(self, landmark_sequence: List[Dict]) -> Dict[str, any]:
        """
        Classify trick from sequence of pose landmarks
        
        Args:
            landmark_sequence: List of frames with landmarks
            
        Returns:
            Dictionary with trick_name, category, and confidence
        """
        
        # Extract features from landmark sequence
        features = self._extract_features(landmark_sequence)
        
        # Analyze movement patterns
        trick_scores = self._analyze_patterns(features)
        
        # Get highest confidence trick
        best_trick = max(trick_scores.items(), key=lambda x: x[1])
        trick_name, confidence = best_trick
        
        return {
            'trick_name': trick_name,
            'category': self.TRICKS[trick_name]['category'],
            'confidence': confidence,
            'all_predictions': trick_scores
        }
    
    def _extract_features(self, landmark_sequence: List[Dict]) -> Dict:
        """
        Extract temporal and spatial features from landmarks
        """
        features = {
            'duration': len(landmark_sequence),
            'vertical_movement': [],
            'rotation_detected': False,
            'foot_movement': [],
            'body_angle_changes': []
        }
        
        for frame_data in landmark_sequence:
            landmarks = frame_data['landmarks']
            
            # Calculate vertical movement (jump height indicator)
            if len(landmarks) >= 28:
                avg_ankle_y = (landmarks[27]['y'] + landmarks[28]['y']) / 2
                features['vertical_movement'].append(avg_ankle_y)
            
            # Calculate body angle
            if len(landmarks) >= 24:
                hip_y = (landmarks[23]['y'] + landmarks[24]['y']) / 2
                shoulder_y = (landmarks[11]['y'] + landmarks[12]['y']) / 2
                features['body_angle_changes'].append(abs(hip_y - shoulder_y))
        
        return features
    
    def _analyze_patterns(self, features: Dict) -> Dict[str, float]:
        """
        Analyze features to determine trick probabilities
        
        NOTE: In production, this would use a trained LSTM/CNN model
        For demo purposes, using heuristic analysis
        """
        scores = {}
        
        # Calculate vertical displacement
        if features['vertical_movement']:
            vert_movement = np.array(features['vertical_movement'])
            max_height = np.max(vert_movement)
            min_height = np.min(vert_movement)
            displacement = max_height - min_height
            
            # Simple heuristic classification (would be ML model in production)
            if displacement > 0.15:  # Significant air time
                if len(features['body_angle_changes']) > 15:
                    scores['kickflip'] = 0.85
                    scores['heelflip'] = 0.75
                    scores['360_flip'] = 0.65
                else:
                    scores['ollie'] = 0.90
                    scores['nollie'] = 0.70
            else:  # Ground tricks
                scores['manual'] = 0.80
                scores['50-50'] = 0.75
                scores['boardslide'] = 0.70
        
        # Ensure all tricks have a score
        for trick in self.TRICKS:
            if trick not in scores:
                scores[trick] = 0.1
        
        # Normalize scores
        total = sum(scores.values())
        if total > 0:
            scores = {k: v/total for k, v in scores.items()}
        
        return scores