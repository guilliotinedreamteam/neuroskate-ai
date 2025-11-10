"""Physics calculations for skateboarding metrics"""

import numpy as np
from typing import List, Dict
import math


class PhysicsCalculator:
    """Calculates physical metrics from pose data"""
    
    # Average human proportions for estimation
    HUMAN_HEIGHT_PIXELS = 480  # Assume average height in frame
    HUMAN_HEIGHT_INCHES = 68   # Average human height
    
    def calculate_metrics(self, landmark_sequence: List[Dict]) -> Dict[str, float]:
        """
        Calculate physics-based performance metrics
        
        Args:
            landmark_sequence: Sequence of frames with pose landmarks
            
        Returns:
            Dictionary with rotation, height, stability, and style metrics
        """
        
        rotation = self._calculate_rotation(landmark_sequence)
        height = self._calculate_height(landmark_sequence)
        stability = self._calculate_landing_stability(landmark_sequence)
        style = self._calculate_style_score(landmark_sequence)
        
        return {
            'rotation_degrees': rotation,
            'height_inches': height,
            'landing_stability': stability,
            'style_score': style
        }
    
    def _calculate_rotation(self, landmark_sequence: List[Dict]) -> float:
        """
        Estimate board rotation by tracking body orientation changes
        """
        if len(landmark_sequence) < 2:
            return 0.0
        
        total_rotation = 0.0
        
        for i in range(1, len(landmark_sequence)):
            prev_landmarks = landmark_sequence[i-1]['landmarks']
            curr_landmarks = landmark_sequence[i]['landmarks']
            
            # Calculate shoulder angle change (proxy for body rotation)
            if len(prev_landmarks) >= 12 and len(curr_landmarks) >= 12:
                prev_angle = self._calculate_shoulder_angle(prev_landmarks)
                curr_angle = self._calculate_shoulder_angle(curr_landmarks)
                
                angle_diff = abs(curr_angle - prev_angle)
                if angle_diff < 180:  # Avoid wrap-around
                    total_rotation += angle_diff
        
        # Estimate board rotation (typically 1-2x body rotation for flips)
        estimated_rotation = total_rotation * 1.5
        
        # Round to nearest 180° for common trick rotations
        return round(estimated_rotation / 180) * 180
    
    def _calculate_shoulder_angle(self, landmarks: List[Dict]) -> float:
        """
        Calculate angle of shoulder line relative to horizontal
        """
        left_shoulder = landmarks[11]
        right_shoulder = landmarks[12]
        
        dx = right_shoulder['x'] - left_shoulder['x']
        dy = right_shoulder['y'] - left_shoulder['y']
        
        return math.degrees(math.atan2(dy, dx))
    
    def _calculate_height(self, landmark_sequence: List[Dict]) -> float:
        """
        Calculate maximum jump height in inches
        """
        ankle_positions = []
        
        for frame_data in landmark_sequence:
            landmarks = frame_data['landmarks']
            
            if len(landmarks) >= 28:
                # Average of both ankles
                left_ankle_y = landmarks[27]['y']
                right_ankle_y = landmarks[28]['y']
                avg_y = (left_ankle_y + right_ankle_y) / 2
                ankle_positions.append(avg_y)
        
        if not ankle_positions:
            return 0.0
        
        # Calculate vertical displacement (lower y = higher position)
        max_height = min(ankle_positions)  # Lowest y value = highest point
        min_height = max(ankle_positions)  # Highest y value = lowest point
        
        # Convert normalized coordinates to inches
        pixel_displacement = (min_height - max_height) * self.HUMAN_HEIGHT_PIXELS
        inch_displacement = (pixel_displacement / self.HUMAN_HEIGHT_PIXELS) * self.HUMAN_HEIGHT_INCHES
        
        return round(inch_displacement, 1)
    
    def _calculate_landing_stability(self, landmark_sequence: List[Dict]) -> float:
        """
        Calculate landing stability score (0-1)
        Based on pose confidence and body alignment during landing phase
        """
        # Look at last 30% of sequence (landing phase)
        landing_start = int(len(landmark_sequence) * 0.7)
        landing_frames = landmark_sequence[landing_start:]
        
        if not landing_frames:
            return 0.5
        
        stability_scores = []
        
        for frame_data in landing_frames:
            landmarks = frame_data['landmarks']
            
            # Calculate average visibility (confidence)
            visibilities = [lm['visibility'] for lm in landmarks]
            avg_visibility = np.mean(visibilities)
            
            # Calculate body alignment (hips to shoulders)
            if len(landmarks) >= 24:
                hip_center_x = (landmarks[23]['x'] + landmarks[24]['x']) / 2
                shoulder_center_x = (landmarks[11]['x'] + landmarks[12]['x']) / 2
                alignment = 1.0 - abs(hip_center_x - shoulder_center_x)
                
                # Combined score
                frame_stability = (avg_visibility * 0.6 + alignment * 0.4)
                stability_scores.append(frame_stability)
        
        return round(np.mean(stability_scores), 3) if stability_scores else 0.5
    
    def _calculate_style_score(self, landmark_sequence: List[Dict]) -> float:
        """
        Calculate style score based on movement smoothness and body control
        """
        if len(landmark_sequence) < 5:
            return 0.5
        
        # Calculate movement smoothness (lower jitter = higher style)
        hip_movements = []
        
        for frame_data in landmark_sequence:
            landmarks = frame_data['landmarks']
            if len(landmarks) >= 24:
                hip_x = (landmarks[23]['x'] + landmarks[24]['x']) / 2
                hip_y = (landmarks[23]['y'] + landmarks[24]['y']) / 2
                hip_movements.append((hip_x, hip_y))
        
        if len(hip_movements) < 2:
            return 0.5
        
        # Calculate jitter (second derivative of position)
        velocities = []
        for i in range(1, len(hip_movements)):
            dx = hip_movements[i][0] - hip_movements[i-1][0]
            dy = hip_movements[i][1] - hip_movements[i-1][1]
            velocities.append(math.sqrt(dx**2 + dy**2))
        
        # Smooth movement = low velocity variance
        velocity_variance = np.var(velocities) if velocities else 0
        
        # Convert to 0-1 score (lower variance = higher score)
        style_score = 1.0 / (1.0 + velocity_variance * 100)
        
        return round(style_score, 3)