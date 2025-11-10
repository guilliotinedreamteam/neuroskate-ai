"""Pose detection using MediaPipe"""

import cv2
import mediapipe as mp
import numpy as np
from typing import Optional, List, Dict


class PoseDetector:
    """Detects human pose using MediaPipe Pose"""
    
    def __init__(self, min_detection_confidence=0.5, min_tracking_confidence=0.5):
        self.mp_pose = mp.solutions.pose
        self.pose = self.mp_pose.Pose(
            static_image_mode=False,
            model_complexity=2,
            min_detection_confidence=min_detection_confidence,
            min_tracking_confidence=min_tracking_confidence
        )
        
    def detect(self, frame: np.ndarray) -> Optional[List[Dict]]:
        """
        Detect pose landmarks in a frame
        
        Args:
            frame: BGR image array
            
        Returns:
            List of 33 landmarks with x, y, z, visibility, or None if no pose detected
        """
        # Convert BGR to RGB
        rgb_frame = cv2.cvtColor(frame, cv2.COLOR_BGR2RGB)
        
        # Process frame
        results = self.pose.process(rgb_frame)
        
        if not results.pose_landmarks:
            return None
        
        # Extract landmarks
        landmarks = []
        for landmark in results.pose_landmarks.landmark:
            landmarks.append({
                'x': landmark.x,
                'y': landmark.y,
                'z': landmark.z,
                'visibility': landmark.visibility
            })
        
        return landmarks
    
    def get_landmark_positions(self, landmarks: List[Dict], frame_shape) -> Dict[str, tuple]:
        """
        Convert normalized landmarks to pixel coordinates
        
        Args:
            landmarks: Normalized landmarks
            frame_shape: (height, width) of the frame
            
        Returns:
            Dictionary mapping landmark names to (x, y) pixel coordinates
        """
        h, w = frame_shape[:2]
        
        # MediaPipe landmark indices
        landmark_map = {
            'nose': 0,
            'left_ankle': 27,
            'right_ankle': 28,
            'left_hip': 23,
            'right_hip': 24,
            'left_knee': 25,
            'right_knee': 26,
            'left_wrist': 15,
            'right_wrist': 16,
            'left_shoulder': 11,
            'right_shoulder': 12
        }
        
        positions = {}
        for name, idx in landmark_map.items():
            if idx < len(landmarks):
                lm = landmarks[idx]
                positions[name] = (int(lm['x'] * w), int(lm['y'] * h))
        
        return positions
    
    def __del__(self):
        """Clean up MediaPipe resources"""
        if hasattr(self, 'pose'):
            self.pose.close()