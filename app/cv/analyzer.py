"""Main video analysis pipeline"""

import cv2
import numpy as np
from typing import Dict, List, Any
import logging

from app.cv.pose_detector import PoseDetector
from app.cv.trick_classifier import TrickClassifier
from app.cv.physics import PhysicsCalculator

logger = logging.getLogger(__name__)


class VideoAnalyzer:
    """Analyzes skateboarding videos for trick detection and performance metrics"""
    
    def __init__(self):
        self.pose_detector = PoseDetector()
        self.trick_classifier = TrickClassifier()
        self.physics_calc = PhysicsCalculator()
        
    async def analyze_video(self, video_path: str) -> Dict[str, Any]:
        """
        Analyze a skateboarding video
        
        Args:
            video_path: Path to video file
            
        Returns:
            Dictionary containing trick analysis results
        """
        logger.info(f"Analyzing video: {video_path}")
        
        # Open video
        cap = cv2.VideoCapture(video_path)
        if not cap.isOpened():
            raise ValueError(f"Could not open video: {video_path}")
        
        fps = cap.get(cv2.CAP_PROP_FPS)
        frame_count = int(cap.get(cv2.CAP_PROP_FRAME_COUNT))
        duration = frame_count / fps
        
        # Extract pose landmarks from all frames
        all_landmarks = []
        frame_idx = 0
        
        while cap.isOpened():
            ret, frame = cap.read()
            if not ret:
                break
            
            # Detect pose
            landmarks = self.pose_detector.detect(frame)
            if landmarks:
                all_landmarks.append({
                    'frame': frame_idx,
                    'timestamp': frame_idx / fps,
                    'landmarks': landmarks
                })
            
            frame_idx += 1
        
        cap.release()
        
        if not all_landmarks:
            raise ValueError("No pose detected in video")
        
        logger.info(f"Detected pose in {len(all_landmarks)}/{frame_count} frames")
        
        # Classify trick
        trick_result = self.trick_classifier.classify(all_landmarks)
        
        # Calculate physics metrics
        physics_metrics = self.physics_calc.calculate_metrics(all_landmarks)
        
        # Generate performance score
        score = self._calculate_score(
            trick_result['confidence'],
            physics_metrics
        )
        
        # Generate AI feedback
        feedback = self._generate_feedback(
            trick_result['trick_name'],
            physics_metrics,
            all_landmarks
        )
        
        return {
            'trick_name': trick_result['trick_name'],
            'category': trick_result['category'],
            'confidence': trick_result['confidence'],
            'score': score,
            'metrics': {
                'rotation': physics_metrics['rotation_degrees'],
                'height': physics_metrics['height_inches'],
                'landing_stability': physics_metrics['landing_stability'],
                'style': physics_metrics['style_score']
            },
            'feedback': feedback,
            'frame_count': len(all_landmarks),
            'duration': duration,
            'landmarks': all_landmarks[:10]  # Store first 10 frames for visualization
        }
    
    def _calculate_score(self, confidence: float, metrics: Dict) -> float:
        """
        Calculate overall performance score (0-100)
        
        Weights:
        - Confidence: 30%
        - Landing stability: 30%
        - Height: 20%
        - Style: 20%
        """
        score = (
            confidence * 30 +
            metrics['landing_stability'] * 30 +
            min(metrics['height_inches'] / 24, 1.0) * 20 +  # Normalize to 24" max
            metrics['style_score'] * 20
        )
        return round(score, 2)
    
    def _generate_feedback(self, trick_name: str, metrics: Dict, landmarks: List) -> List[str]:
        """
        Generate AI coaching feedback
        """
        feedback = []
        
        # Height feedback
        if metrics['height_inches'] < 12:
            feedback.append("Try to pop harder off your back foot for more height")
        elif metrics['height_inches'] > 20:
            feedback.append("Excellent pop! Great height on this trick")
        
        # Landing stability feedback
        if metrics['landing_stability'] < 0.7:
            feedback.append("Focus on keeping your shoulders aligned over the board when landing")
        elif metrics['landing_stability'] > 0.9:
            feedback.append("Perfect landing! Great balance and control")
        
        # Rotation feedback for flip tricks
        if 'flip' in trick_name.lower():
            if abs(metrics['rotation_degrees'] - 360) > 45:
                feedback.append(f"Board rotation was {metrics['rotation_degrees']:.0f}°. Aim for cleaner 360° flip")
            else:
                feedback.append("Clean rotation! Board flipped perfectly")
        
        # Style feedback
        if metrics['style_score'] < 0.6:
            feedback.append("Try to keep your movements more fluid and controlled")
        
        return feedback


# Global analyzer instance
analyzer = VideoAnalyzer()


async def analyze_video(video_path: str) -> Dict[str, Any]:
    """Convenience function for video analysis"""
    return await analyzer.analyze_video(video_path)